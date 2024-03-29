from aiofiles.os import path as aiopath
from asyncio import gather
from json import loads
from os import path as ospath
from pyrogram import Client
from pyrogram.filters import command
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message
from random import SystemRandom
from string import ascii_letters, digits
from urllib.parse import urlparse

from bot import bot, download_dict, download_dict_lock, config_dict, user_data, LOGGER
from bot.helper.ddl_bypass.direct_link_generator import direct_link_generator
from bot.helper.ext_utils.bot_utils import get_readable_file_size, is_gdrive_link, is_premium_user, is_sharar, sync_to_async, new_task, is_rclone_path, cmd_exec, is_url, get_multiid, arg_parser
from bot.helper.ext_utils.exceptions import DirectDownloadLinkException
from bot.helper.ext_utils.force_mode import ForceMode
from bot.helper.ext_utils.help_messages import HelpString
from bot.helper.ext_utils.multi import run_multi, run_bulk, MultiSelect
from bot.helper.ext_utils.task_manager import stop_duplicate_check
from bot.helper.listeners.tasks_listener import MirrorLeechListener
from bot.helper.mirror_utils.rclone_utils.list import RcloneList
from bot.helper.mirror_utils.rclone_utils.transfer import RcloneTransferHelper
from bot.helper.mirror_utils.status_utils.gdrive_status import GdriveStatus
from bot.helper.mirror_utils.status_utils.rclone_status import RcloneStatus
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import editMessage, sendMessage, deleteMessage, sendStatusMessage, auto_delete_message


arg_base = {'link': '', '-i': 0, '-b': False, '-n': '', '-up': '', '-rcf': ''}


async def rcloneNode(client, message, editable, user_id, link, dst_path, rcf, tag):
    if link == 'rcl':
        link = await RcloneList(client, editable, user_id).get_rclone_path('rcd')
        if not is_rclone_path(link):
            await editMessage(link, editable)
            return
    is_gdlink = is_gdrive_link(link)
    user_config = ospath.join('rclone', f'{user_id}.conf')
    if link.startswith('mrcc:'):
        link = link.split('mrcc:', 1)[1]
        config_path = user_config
    elif is_gdlink:
        config_path = ''
    else:
        config_path = 'rclone.conf'
    if not is_gdlink and not await aiopath.exists(config_path):
        await editMessage(f'Rclone Config: {config_path} not Exists!', editable)
        return
    if dst_path == 'rcl' or config_dict['RCLONE_PATH'] == 'rcl':
        dst_path = await RcloneList(client, editable, user_id).get_rclone_path('rcu', config_path)
        if not is_rclone_path(dst_path):
            await editMessage(dst_path, editable)
            return
    dst_path = (dst_path or config_dict['RCLONE_PATH']).strip('/')
    if not is_rclone_path(dst_path):
        await editMessage('Wrong Rclone Clone Destination!', editable)
        return
    if dst_path.startswith('mrcc:'):
        dst_path = dst_path.split('mrcc:', 1)[1]
        if is_gdlink:
            config_path = user_config
        if config_path != user_config:
            await editMessage('You should use same rclone.conf to clone between pathies!', editable)
            return
    elif not is_gdlink and config_path != 'rclone.conf':
        await editMessage('You should use same rclone.conf to clone between pathies!', editable)
        return
    else:
        config_path = 'rclone.conf'
    if is_gdlink:
        gd = GoogleDriveHelper()
        drive_id = await sync_to_async(gd.get_id, link)
        if not drive_id:
            await editMessage('Google Drive ID could not be found in the provided link', editable)
            return
        await editMessage(f'<i>Getting detail from</i>\n<code>{link}</code>', editable)
        name, mime_type, size, files, folders = await sync_to_async(gd.count, link)
        await deleteMessage(editable)
        if CLONE_LIMIT := config_dict['CLONE_LIMIT']:
            if size > CLONE_LIMIT * 1024**3:
                await listener.onDownloadError(f'Clone limit is {CLONE_LIMIT}GB. File/folder size is {get_readable_file_size(size)}.', ename=name, isClone=True)
                return
    else:
        remote, src_path = link.split(':', 1)
        src_path = src_path .strip('/')
        cmd = ['./gclone', 'lsjson', '--fast-list', '--stat', '--no-modtime', '--config', config_path, f'{remote}:{src_path}']
        res = await cmd_exec(cmd)
        if res[2] != 0:
            if res[2] != -9:
                msg = f'Error: While getting rclone stat. Path: {remote}:{src_path}. Stderr: {res[1][:4000]}'
                await editMessage(msg, editable)
            return
        await deleteMessage(editable)
        rstat = loads(res[0])
        if rstat['IsDir']:
            name = src_path.rsplit('/', 1)[-1] if src_path else remote
            dst_path += name if dst_path.endswith(':') else f'/{name}'
            mime_type = 'Folder'
        else:
            name = src_path.rsplit('/', 1)[-1]
            mime_type = rstat['MimeType']
    listener = MirrorLeechListener(message, tag=tag)
    await listener.onDownloadStart()
    RCTransfer = RcloneTransferHelper(listener, name)
    LOGGER.info(f'Clone Started: Name: {name} - Source: {link} - Destination: {dst_path}')
    gid = ''.join(SystemRandom().choices(ascii_letters + digits, k=12))
    async with download_dict_lock:
        download_dict[message.id] = RcloneStatus(RCTransfer, listener, gid, 'cl')
    await sendStatusMessage(message)
    if is_gdlink:
        link, destination = await RCTransfer.gclone(config_path, drive_id, dst_path, mime_type)
    else:
        link, destination = await RCTransfer.clone(config_path, remote, src_path, dst_path, rcf, mime_type)
    if not link:
        return
    LOGGER.info(f'Cloning Done: {name}')
    cmd1 = ['./gclone', 'lsf', '--fast-list', '-R', '--files-only', '--config', config_path, destination]
    cmd2 = ['./gclone', 'lsf', '--fast-list', '-R', '--dirs-only', '--config', config_path, destination]
    cmd3 = ['./gclone', 'size', '--fast-list', '--json', '--config', config_path, destination]
    res1, res2, res3 = await gather(cmd_exec(cmd1), cmd_exec(cmd2), cmd_exec(cmd3))
    if res1[2] != res2[2] != res3[2] != 0:
        if res1[2] == -9:
            return
        files = folders = None
        size = 0
        LOGGER.error(f'Error: While getting rclone stat. Path: {destination}. Stderr: {res1[1][:4000]}')
    else:
        files, folders = len(res1[0].split('\n')), len(res2[0].split('\n'))
        rsize = loads(res3[0])
        size = rsize['bytes']
    await listener.onUploadComplete(link, size, files, folders, mime_type, name, destination, True)


async def gdcloneNode(client, message, editable, newname, multi, link, tag, isSuperGroup, gdrive_sharer):
    user_dict = user_data.get(message.from_user.id, {})
    multiid = get_multiid(message.from_user.id)
    if config_dict['MULTI_GDID'] and multi == 0 and not user_dict.get('cus_gdrive'):
        multiid, _ = await MultiSelect(client, editable, message.from_user, enable_go=False).get_buttons()
    if not multiid:
        await editMessage('Task has been cancelled!', editable)
        return
    if is_gdrive_link(link):
        gd = GoogleDriveHelper()
        name, mime_type, size, files, _ = await sync_to_async(gd.count, link)
        if not mime_type:
            await editMessage(name, editable)
            return
        listener = MirrorLeechListener(message, tag=tag, multiId=multiid, upPath='gd')
        if newname:
            name = newname
        file, _ = await stop_duplicate_check(name, listener)
        if file:
            await deleteMessage(editable)
            LOGGER.info('File/folder already in Drive!')
            await listener.onDownloadError('File/folder already in Drive!', file, name, True)
            return
        if CLONE_LIMIT := config_dict['CLONE_LIMIT']:
            if size > CLONE_LIMIT * 1024**3:
                await deleteMessage(editable)
                await listener.onDownloadError(f'Clone limit is {CLONE_LIMIT}GB. File/folder size is {get_readable_file_size(size)}.', ename=name, isClone=True)
                return
        await listener.onDownloadStart()
        LOGGER.info(f'Clone Started: Name: {name} - Source: {link}')
        drive = GoogleDriveHelper(name, listener=listener)
        if files <= 10:
            await editMessage(f'<i>Found GDrive link to clone...</i>\n<code>{link}</code>', editable)
            link, size, mime_type, files, folders = await sync_to_async(drive.clone, link, name, gdrive_sharer)
            await deleteMessage(editable)
        else:
            await deleteMessage(editable)
            gid = ''.join(SystemRandom().choices(ascii_letters + digits, k=12))
            async with download_dict_lock:
                download_dict[message.id] = GdriveStatus(drive, size, listener, gid, 'cl')
            await sendStatusMessage(message)
            link, size, mime_type, files, folders = await sync_to_async(drive.clone, link, name, gdrive_sharer)
        if not link:
            return
        elif is_url(link):
            LOGGER.info(f'Cloning Done: {name}')
            await listener.onUploadComplete(link, size, files, folders, mime_type, name, isClone=True)
        else:
            await sendMessage(link, message)
    else:
        if config_dict['AUTO_MUTE'] and isSuperGroup:
            await deleteMessage(editable)
            editable = await ForceMode(message).auto_muted(HelpString.CLONE)
        else:
            await editMessage(HelpString.CLONE, editable)
        await auto_delete_message(message, editable, message.reply_to_message)


@new_task
async def cloneNode(client: Client, message: Message, bulk=[]):
    input_list = message.text.split()
    args = arg_parser(input_list[1:], arg_base.copy())

    reply_to = message.reply_to_message
    tag = message.from_user.mention
    user_id = message.from_user.id
    user_dict = user_data.get(user_id, {})
    isSuperGroup = message.chat.type.name in ['SUPERGROUP', 'CHANNEL']

    fmode = ForceMode(message)
    if fmsg:= await fmode.run_force('fsub', 'funame', 'mute', pm_mode='clone_pm_message'):
        await auto_delete_message(message, fmsg, reply_to)
        return

    isBulk = args['-b']
    newname = args['-n']
    dst_path = args['-up']
    rcf = args['-rcf']
    link = args['link']
    bulk_start = bulk_end = 0

    try:
        multi = int(args['-i'])
    except:
        multi = 0

    if not isinstance(isBulk, bool):
        dargs = isBulk.split(':')
        bulk_start = dargs[0] or None
        if len(dargs) == 2:
            bulk_end = dargs[1] or None
        isBulk = True

    if config_dict['PREMIUM_MODE'] and not is_premium_user(user_id) and (multi > 0 or isBulk):
        await sendMessage('Upss, multi/bulk mode for premium user only', message)
        return

    if not (is_url(link) or is_rclone_path(link)) and reply_to and reply_to.text:
        if not reply_to.sender_chat and not getattr(reply_to.from_user, 'is_bot', None):
            tag = reply_to.from_user.mention
        link = reply_to.text.split('\n', 1)[0].strip()

    if isBulk:
        await run_bulk(cloneNode, client, message, input_list, bulk_start, bulk_end, bulk)
        return

    if bulk:
        del bulk[0]

    run_multi(cloneNode, client, message, multi, input_list, '', bulk)

    check_ = await sendMessage('<i>Checking request, please wait...</i>', message)
    gdrive_sharer = is_sharar(link)
    if is_sharar(link):
        await editMessage(f'<i>Checking {urlparse(link).netloc} link...</i>\n<code>{link}</code>', check_)
        try:
            link = await sync_to_async(direct_link_generator, link)
        except DirectDownloadLinkException as e:
            await editMessage(f'{tag}, {e}', check_)
            return
    if not is_url(link) and not is_rclone_path(link):
        if isSuperGroup and (fmsg:= await fmode.auto_muted(HelpString.CLONE)):
            await deleteMessage(check_)
            check_ = fmsg
        else:
            await editMessage(HelpString.CLONE, check_)
        await auto_delete_message(message, check_, reply_to)
    elif (is_rclone_path(link) and not newname) or (dst_path and is_gdrive_link(link) and await aiopath.exists('gclone')):
        if not await aiopath.exists('rclone.conf') and not await aiopath.exists(ospath.join('rclone', f'{user_id}.conf')):
            await editMessage('RClone config not exists!', check_)
            return
        if not config_dict['RCLONE_PATH'] and not dst_path:
            await editMessage('Destination not specified!', check_)
            return
        if link.startswith('up:'):
            await editMessage('Source not specified!', check_)
            return
        await rcloneNode(client, message, check_, user_id, link, dst_path, rcf, tag)
    else:
        if not config_dict['GDRIVE_ID'] and not user_dict.get('cus_gdrive'):
            await editMessage('GDRIVE_ID not Provided!', check_)
        else:
            await gdcloneNode(client, message, check_, newname, multi, link, tag, isSuperGroup, gdrive_sharer)


bot.add_handler(MessageHandler(cloneNode, filters=command(BotCommands.CloneCommand) & CustomFilters.authorized))