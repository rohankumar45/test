from aiofiles.os import path as aiopath
from asyncio import gather
from json import loads
from os import path as ospath
from pyrogram import Client
from pyrogram.filters import command
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message
from random import SystemRandom
from re import split as re_split
from string import ascii_letters, digits
from urllib.parse import urlparse

from bot import bot, download_dict, download_dict_lock, config_dict, user_data, LOGGER
from bot.helper.ddl_bypass.direct_link_generator import direct_link_generator
from bot.helper.ext_utils.bot_utils import get_readable_file_size, is_gdrive_link, is_media, is_premium_user, is_sharar, sync_to_async, new_task, is_rclone_path, cmd_exec, is_url, get_multiid
from bot.helper.ext_utils.exceptions import DirectDownloadLinkException
from bot.helper.ext_utils.force_mode import ForceMode
from bot.helper.ext_utils.help_messages import HelpString
from bot.helper.ext_utils.multi import run_multi, MultiSelect
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


async def rcloneNode(client, message, editable, user_id, link, dst_path, rcf, tag):
    if link == 'rcl':
        link = await RcloneList(client, editable, user_id).get_rclone_path('rcd')
        if not is_rclone_path(link):
            await editMessage(link, editable)
            return
    if link.startswith('mrcc:'):
        link = link.split('mrcc:', 1)[1]
        config_path = ospath.join('rclone', f'{user_id}.conf')
    else:
        config_path = 'rclone.conf'
    if not await aiopath.exists(config_path):
        await editMessage(f'Rclone Config: {config_path} not Exists!', editable)
        return
    if dst_path == 'rcl' or config_dict['RCLONE_PATH'] == 'rcl':
        dst_path = await RcloneList(client, editable, user_id).get_rclone_path('rcu', config_path)
        if not is_rclone_path(dst_path):
            await editMessage(dst_path, editable)
            return
    dst_path = (dst_path or config_dict['RCLONE_PATH']).strip('/')
    if dst_path.startswith('mrcc:'):
        if config_path != ospath.join('rclone', f'{user_id}.conf'):
            await editMessage('You should use same rclone.conf to clone between pathies!', editable)
            return
    elif config_path != 'rclone.conf':
        await editMessage('You should use same rclone.conf to clone between pathies!', editable)
        return
    is_gdlink = is_gdrive_link(link)
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
                await listener.onDownloadError(f'Clone limit is {CLONE_LIMIT}GB. {name} size is {get_readable_file_size(size)}.', ename=name, isClone=True)
                return
    else:
        remote, src_path = link.split(':', 1)
        src_path = src_path .strip('/')
        cmd = ['rclone', 'lsjson', '--fast-list', '--stat', '--no-modtime', '--config', config_path, f'{remote}:{src_path}']
        res = await cmd_exec(cmd)
        if res[2] != 0:
            if res[2] != -9:
                msg = f'Error: While getting rclone stat. Path: {remote}:{src_path}. Stderr: {res[1][:4000]}'
                await editMessage(msg, editable)
            return
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


async def gdcloneNode(client, message, editable, newname, multi, link, tag, isSuperGroup, sharer_link):
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
            await listener.onDownloadError(f'{name} already in Drive!', file, name, True)
            return
        if CLONE_LIMIT := config_dict['CLONE_LIMIT']:
            if size > CLONE_LIMIT * 1024**3:
                await deleteMessage(editable)
                await listener.onDownloadError(f'Clone limit is {CLONE_LIMIT}GB. {name} size is {get_readable_file_size(size)}.', ename=name, isClone=True)
                return
        await listener.onDownloadStart()
        LOGGER.info(f'Clone Started: Name: {name} - Source: {link}')
        drive = GoogleDriveHelper(name, listener=listener)
        if files <= 10:
            await editMessage(f'<i>Found GDrive link to clone...</i>\n<code>{link}</code>', editable)
            link, size, mime_type, files, folders = await sync_to_async(drive.clone, link, name, sharer_link)
            await deleteMessage(editable)
        else:
            await deleteMessage(editable)
            gid = ''.join(SystemRandom().choices(ascii_letters + digits, k=12))
            async with download_dict_lock:
                download_dict[message.id] = GdriveStatus(drive, size, listener, gid, 'cl')
            await sendStatusMessage(message)
            link, size, mime_type, files, folders = await sync_to_async(drive.clone, link, name, sharer_link)
        if not link:
            return
        elif is_url(link):
            LOGGER.info(f'Cloning Done: {name}')
            await listener.onUploadComplete(link, size, files, folders, mime_type, name, isClone=True)
        else:
            await sendMessage(link, message)
    else:
        if config_dict['AUTO_MUTE'] and isSuperGroup:
            msg = await ForceMode(message).auto_muted(HelpString.CLONE)
        else:
            msg = await editMessage(HelpString.CLONE, editable)
        await auto_delete_message(message, msg, message.reply_to_message)


@new_task
async def cloneNode(client: Client, message: Message):
    user_id = message.from_user.id
    user_dict = user_data.get(user_id, {})
    isSuperGroup = message.chat.type.name in ['SUPERGROUP', 'CHANNEL']
    fmode = ForceMode(message)
    if config_dict['FSUB'] and (fmsg:= await fmode.force_sub):
        await auto_delete_message(message, fmsg, reply_to)
        return
    if config_dict['FUSERNAME'] and (fmsg:= await fmode.force_username):
        await auto_delete_message(message, fmsg, reply_to)
        return
    if user_dict.get('enable_pm') and isSuperGroup and not await fmode.clone_pm_message:
        return
    if config_dict['AUTO_MUTE'] and isSuperGroup and (fmsg:= await fmode.auto_muted()):
        await auto_delete_message(message, fmsg, reply_to)
        return
    reply_to = message.reply_to_message
    tag = message.from_user.mention
    multi, link = 0, ''
    text = message.text
    args = text.split(maxsplit=1)

    if len(args) > 1:
        link = args[1].strip()
        if not link.startswith(('up:', 'rcf:')):
            link = re_split(r' up: | rcf: ', link)[0].strip()
        if link.isdigit():
            multi = int(link)
            link = ''

    if config_dict['PREMIUM_MODE'] and not is_premium_user(user_id) and multi > 0:
        await sendMessage('Upss, multi mode for premium user only', message)
        return

    mlist = [client, message, multi, 1, '']

    if reply_to and not is_media(reply_to):
        link = reply_to.text.split('\n', 1)[0].strip()
        tag = reply_to.from_user.mention

    newname = text.split(' n: ', 1)
    newname = re_split(' rcf: | up: ', newname[1])[0].strip() if len(newname) > 1 else ''
    rcf = text.split(' rcf: ', 1)
    rcf = re_split(' up: ', rcf[1])[0].strip() if len(rcf) > 1 else None
    dst_path = text.split(' up: ', 1)
    dst_path = re_split(' rcf: ', dst_path[1])[0].strip() if len(dst_path) > 1 else None

    run_multi(mlist, cloneNode)

    check_ = await sendMessage('<i>Checking request, please wait...</i>', message)
    sharer_link = None
    if is_sharar(link):
        await editMessage(f'<i>Checking {urlparse(link).netloc} link...</i>\n<code>{link}</code>', check_)
        try:
            link = await sync_to_async(direct_link_generator, link)
            sharer_link = link
        except DirectDownloadLinkException as e:
            await editMessage(f'{tag}, {e}', check_)
            return
    if not link:
        if config_dict['AUTO_MUTE'] and isSuperGroup and (fmsg:= await fmode.auto_muted(HelpString.CLONE)):
            await auto_delete_message(message, fmsg, reply_to)
            return
        await editMessage(HelpString.CLONE, check_)
    elif (is_rclone_path(link) and not newname) or (dst_path and is_gdrive_link(link) and await aiopath.exists('gclone')):
        if not await aiopath.exists('rclone.conf') and not await aiopath.exists(ospath.join('rclone', f'{user_id}.conf')):
            await editMessage('RClone config not exists!', check_)
            return
        if not config_dict['RCLONE_PATH'] and not dst_path:
            await editMessage('Destinantion not specified!', check_)
            return
        await rcloneNode(client, message, check_, user_id, link, dst_path, rcf, tag)
    else:
        if not config_dict['GDRIVE_ID'] and not user_dict.get('cus_gdrive'):
            await editMessage('GDRIVE_ID not Provided!', check_)
        else:
            await gdcloneNode(client, message, check_, newname, multi, link, tag, isSuperGroup, sharer_link)


bot.add_handler(MessageHandler(cloneNode, filters=command(BotCommands.CloneCommand) & CustomFilters.authorized))