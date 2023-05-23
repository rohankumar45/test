from aiofiles.os import path as aiopath
from asyncio import sleep
from base64 import b64encode
from os import path as ospath
from pyrogram import Client
from pyrogram.filters import command
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message
from re import match as re_match, split as re_split
from urllib.parse import urlparse

from bot import bot, config_dict, user_data, LOGGER, DOWNLOAD_DIR
from bot.helper.ddl_bypass.direct_link_generator import direct_link_generator
from bot.helper.ext_utils.bot_utils import is_url, is_magnet, is_media, is_mega_link, is_gdrive_link, is_sharar, get_content_type, \
     is_premium_user, UserDaily, sync_to_async, new_task, is_rclone_path, is_tele_link, get_multiid
from bot.helper.ext_utils.conf_loads import intialize_savebot
from bot.helper.ext_utils.exceptions import DirectDownloadLinkException
from bot.helper.ext_utils.force_mode import ForceMode
from bot.helper.ext_utils.multi import run_multi, run_bulk, MultiSelect
from bot.helper.listeners.tasks_listener import MirrorLeechListener
from bot.helper.mirror_utils.download_utils.aria2_download import add_aria2c_download
from bot.helper.mirror_utils.download_utils.gd_download import add_gd_download
from bot.helper.mirror_utils.download_utils.megarest_download import MegaDownloader
from bot.helper.mirror_utils.download_utils.megasdk_download import add_mega_download
from bot.helper.mirror_utils.download_utils.qbit_download import add_qb_torrent
from bot.helper.mirror_utils.download_utils.rclone_download import add_rclone_download
from bot.helper.mirror_utils.download_utils.telegram_download import TelegramDownloadHelper
from bot.helper.mirror_utils.rclone_utils.list import RcloneList
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage, auto_delete_message, deleteMessage, editMessage, sendMessage, sendingMessage, get_tg_link_content


@new_task
async def _mirror_leech(client: Client, message: Message, isZip=False, extract=False, isQbit=False, isLeech=False, sameDir={}, bulk=[]):
    mesg = message.text.split('\n')
    message_args = mesg[0].split(maxsplit=1)
    if len(mesg) > 1 and mesg[1].startswith('Tag: '):
        try:
            id_ = int(mesg[1].split()[-1])
            message.from_user = await client.get_users(id_)
            await message.unpin()
        except:
            pass
    tag = message.from_user.mention
    reply_to = message.reply_to_message
    user_id = message.from_user.id
    user_dict = user_data.get(user_id, {})
    if mode:= str(config_dict['DISABLE_MIRROR_LEECH']):
        msg = None
        if mode == 'mirror' and not isLeech:
            msg = await sendMessage('Mirror mode has been disabled!', message)
        elif mode == 'leech' and isLeech:
            msg = await sendMessage('Leech mode has been disabled!', message)
        if msg:
            await auto_delete_message(message, msg, reply_to)
            return
    if isLeech and (ucid:= user_dict.get('dump_id')):
        try:
            await client.get_chat(ucid)
        except:
            msg = await sendMessage('U have enable leech dump feature but didn\'t add me to chat!', message)

    isSuperGroup = message.chat.type.name in ['SUPERGROUP', 'CHANNEL']
    select = seed = is_bulk = isGofile = gdrive_sharer = False
    mi = index = 1
    link = folder_name = ''
    multi = bulk_start = bulk_end = 0
    file_ = tg_client = ratio = seed_time = None
    multiid = get_multiid(user_id)

    fmode = ForceMode(message)
    if config_dict['FSUB'] and (fmsg:= await fmode.force_sub):
        await auto_delete_message(message, fmsg, reply_to)
        return
    if config_dict['FUSERNAME'] and (fmsg:= await fmode.force_username):
        await auto_delete_message(message, fmsg, reply_to)
        return
    if fmsg:= await fmode.task_limiter:
        await auto_delete_message(message, fmsg, reply_to)
        return
    if user_dict.get('enable_pm') and isSuperGroup and not await fmode.mirror_leech_pm_message:
        return
    if config_dict['AUTO_MUTE'] and isSuperGroup and (fmsg:= await fmode.auto_muted()):
        await auto_delete_message(message, fmsg, reply_to)
        return
    if config_dict['DAILY_MODE']:
        if not is_premium_user(user_id) and await UserDaily(user_id).get_daily_limit():
            text = f"Upss, {tag} u have reach daily limit for today ({config_dict['DAILY_LIMIT_SIZE']}GB), check ur status in /{BotCommands.UserSetCommand}"
            msg = await sendingMessage(text, message, config_dict['IMAGE_LIMIT'])
            await auto_delete_message(message, msg, reply_to)
            return

    if len(message_args) > 1:
        args = mesg[0].split(maxsplit=6)
        args.pop(0)
        for x in args:
            x = x.strip()
            if x == 's':
                select = True
                index += 1
            elif x == 'd':
                seed = True
                index += 1
            elif x == 'go':
                index += 1
                if not isLeech:
                    isGofile = True
            elif x.startswith('d:'):
                seed = True
                index += 1
                dargs = x.split(':')
                ratio = dargs[1] or None
                if len(dargs) == 3:
                    seed_time = dargs[2] or None
            elif x.isdigit():
                multi = int(x)
                mi = index
                index += 1
            elif x.startswith('m:'):
                marg = x.split('m:', 1)
                if len(marg) > 1:
                    folder_name = f"/{marg[1]}"
                    if not sameDir:
                        sameDir = set()
                    sameDir.add(message.id)
            elif x == 'b':
                is_bulk = True
                bi = index
                index += 1
            elif x.startswith('b:'):
                is_bulk = True
                bi = index
                index += 1
                dargs = x.split(':')
                bulk_start = dargs[1] or 0
                if len(dargs) == 3:
                    bulk_end = dargs[2] or 0
            else:
                break
        if multi == 0 or bulk:
            message_args = mesg[0].split(maxsplit=index)
            if len(message_args) > index:
                x = message_args[index].strip()
                if not x.startswith(('n:', 'pswd:', 'up:', 'rcf:')):
                    link = re_split(r' pswd: | n: | up: | rcf: ', x)[0].strip()

        if len(folder_name) > 0:
            seed = False
            ratio = seed_time = None

    if config_dict['PREMIUM_MODE'] and not is_premium_user(user_id) and (multi > 0 or is_bulk):
        await sendMessage(f'Upss {tag}, multi/bulk mode for premium user only', message)
        return

    LOGGER.info(bulk)

    if is_bulk:
        await run_bulk([client, message, index, bulk_start, bulk_end, bi], _mirror_leech, isZip, extract, isQbit, isLeech, sameDir, bulk)
        return

    if bulk:
        del bulk[0]

    run_multi([client, message, multi, index, mi, folder_name], _mirror_leech, isZip, extract, isQbit, isLeech, sameDir, bulk)

    path = f'{DOWNLOAD_DIR}{message.id}{folder_name}'

    name = mesg[0].split(' n: ', 1)
    name = re_split(' pswd: | rcf: | up: ', name[1])[0].strip() if len(name) > 1 else ''
    name = name.replace('/', '.')

    pswd = mesg[0].split(' pswd: ', 1)
    pswd = re_split(' n: | rcf: | up: ', pswd[1])[0] if len(pswd) > 1 else None

    rcf = mesg[0].split(' rcf: ', 1)
    rcf = re_split(' n: | pswd: | up: ', rcf[1])[0].strip() if len(rcf) > 1 else None

    up = mesg[0].split(' up: ', 1)
    up = re_split(' n: | pswd: | rcf: ', up[1])[0].strip() if len(up) > 1 else None

    check_ = await sendMessage('<i>Checking request, please wait...</i>', message)

    if link and is_tele_link(link):
        try:
            await intialize_savebot(user_dict.get('user_string'), True, user_id)
            tg_client, reply_to = await get_tg_link_content(link, user_id)
        except Exception as e:
            await editMessage(f'ERROR: {e}', check_)
            return
    elif not link and reply_to and reply_to.text:
        reply_text = reply_to.text.split('\n', 1)[0].strip()
        if reply_text and is_tele_link(reply_text):
            try:
                await intialize_savebot(user_dict.get('user_string'), True, user_id)
                tg_client, reply_to = await get_tg_link_content(reply_text, user_id)
            except Exception as e:
                await editMessage(f'ERROR: {e}', check_)
                return

    if reply_to:
        if not reply_to.sender_chat and not getattr(reply_to.from_user, 'is_bot', None):
            tag = reply_to.from_user.mention
        file_ = is_media(reply_to)
        if not is_url(link) and not is_magnet(link):
            if not file_:
                reply_text = reply_to.text.split('\n', 1)[0].strip()
                if is_url(reply_text) or is_magnet(reply_text):
                    link = reply_text
            elif reply_to.document and (file_.mime_type == 'application/x-bittorrent' or file_.file_name.endswith('.torrent')):
                link = await reply_to.download()
                file_ = None

    if not is_url(link) and not is_magnet(link) and not await aiopath.exists(link) and not is_rclone_path(link) and not file_:
        help_msg = f'Invalid argument, type /{BotCommands.HelpCommand} for more details.'
        if config_dict['AUTO_MUTE'] and isSuperGroup and (fmsg:= await fmode.auto_muted(help_msg)):
            await deleteMessage(check_)
            await auto_delete_message(message, fmsg, reply_to)
            return
        msg = await editMessage(help_msg, check_)
        await auto_delete_message(message, msg)
        return

    if (not up or up != 'rcl') and config_dict['MULTI_GDID'] and not isLeech and multi == 0 and not user_dict.get('cus_gdrive'):
        multiid, isGofile = await MultiSelect(client, check_, message.from_user, isGofile).get_buttons()
    if not multiid:
        await editMessage('Task has been cancelled!', check_)
        return

    if link:
        LOGGER.info(link)

    if isGofile:
        await editMessage('<i>GoFile upload has been enabled!</i>', check_)
        await sleep(1)

    if not is_mega_link(link) and not isQbit and not is_magnet(link) and not is_rclone_path(link) \
        and not is_gdrive_link(link) and not link.endswith('.torrent') and not file_:
        content_type = await sync_to_async(get_content_type, link)
        host = urlparse(link).netloc
        gdrive_sharer = is_sharar(link)
        if not content_type or re_match(r'text/html|text/plain', content_type):
            try:
                await editMessage(f'<i>Generating direct link from {host}, please wait...</i>', check_)
                if 'gofile.io' in host:
                    link, _headers = await sync_to_async(direct_link_generator, link)
                else:
                    link = await sync_to_async(direct_link_generator, link)
                LOGGER.info(f'Generated link: {link}')
                await editMessage(f"<i>Found {'drive' if 'drive.google.com' in link else 'direct'} link:</i>\n<code>{link}</code>", check_)
                await sleep(1)
            except DirectDownloadLinkException as e:
                if str(e).startswith('ERROR:'):
                    await editMessage(f'{tag}, {e}', check_)
                    return

    if not isLeech:
        if config_dict['DEFAULT_UPLOAD'] == 'rc' and up is None or up == 'rc':
            up = config_dict['RCLONE_PATH']
        if up is None and config_dict['DEFAULT_UPLOAD'] == 'gd':
            up = 'gd'
        if up == 'gd' and not config_dict['GDRIVE_ID'] and not user_dict.get('cus_gdrive'):
            await editMessage('GDRIVE_ID not provided!', check_)
            return
        elif not up:
            await editMessage('No RClone destination!', check_)
            return
        elif up not in ['rcl', 'gd']:
            if up.startswith('mrcc:'):
                config_path = ospath.join('rclone', f'{message.from_user.id}.conf')
            else:
                config_path = 'rclone.conf'
            if not await aiopath.exists(config_path):
                await editMessage(f'RClone config: {config_path} not exists!', check_)
                return

    if link == 'rcl':
        link = await RcloneList(client, check_, user_id).get_rclone_path('rcd')
        if not is_rclone_path(link):
            await editMessage(link, check_)
            return
    if up == 'rcl' and not isLeech:
        up = await RcloneList(client, check_, user_id).get_rclone_path('rcu')
        if not is_rclone_path(up):
            await editMessage(up, check_)
            return

    if not is_rclone_path(link) and not is_gdrive_link(link):
        await deleteMessage(check_)

    listener = MirrorLeechListener(message, isZip, extract, isQbit, isLeech, isGofile, pswd, tag, select, seed, name, multiid, sameDir, rcf, up)

    if file_:
        await TelegramDownloadHelper(listener).add_download(reply_to, f'{path}/', name, tg_client)
    elif is_rclone_path(link):
        if link.startswith('mrcc:'):
            link = link.split('mrcc:', 1)[1]
            config_path = f'rclone/{message.from_user.id}.conf'
        else:
            config_path = 'rclone.conf'
        if not await aiopath.exists(config_path):
            await editMessage(f'Rclone Config: {config_path} not Exists!', check_)
            return
        await deleteMessage(check_)
        await add_rclone_download(link, config_path, f'{path}/', name, listener)
    elif is_gdrive_link(link):
        if not isZip and not extract and not isLeech and up == 'gd':
            gmsg = f'Use /{BotCommands.CloneCommand} to clone Google Drive file/folder\n\n'
            gmsg += f'Use /{BotCommands.ZipMirrorCommand[0]} to make zip of Google Drive folder\n\n'
            gmsg += f'Use /{BotCommands.UnzipMirrorCommand[0]} to extracts Google Drive archive folder/file'
            await editMessage(gmsg, check_)
            await auto_delete_message(message, check_, reply_to)
            return
        await deleteMessage(check_)
        await add_gd_download(link, path, listener, name, gdrive_sharer)
    elif is_mega_link(link):
        if config_dict['ENABLE_MEGAREST']:
            if config_dict['MEGA_KEY']:
                LOGGER.info('Download mega link using Megarest client!')
                await MegaDownloader(listener).add_download(link, f'{path}/')
            else:
                await sendMessage('MEGA_API_KEY not Provided!', message)
        else:
            LOGGER.info('Download mega link using Megasdk client!')
            await add_mega_download(link, f'{path}/', listener, name)
    elif isQbit:
        await add_qb_torrent(link, path, listener, ratio, seed_time)
    else:
        if len(mesg) > 1 and not mesg[1].startswith('Tag:'):
            ussr = mesg[1]
            pssw = mesg[2] if len(mesg) > 2 else ''
            auth = f'{ussr}:{pssw}'
            auth = 'Basic ' + b64encode(auth.encode()).decode('ascii')
        else:
            auth = ''
        headers = None
        if 'gofile.io' in link:
            headers = _headers
        elif 'static.romsget.io' in link:
            headers = 'Referer: https://www.romsget.io/'
        await add_aria2c_download(link, path, listener, name, auth, ratio, seed_time, headers)


async def mirror(client, message):
    _mirror_leech(client, message)


async def unzip_mirror(client, message):
    _mirror_leech(client, message, extract=True)


async def zip_mirror(client, message):
    _mirror_leech(client, message, True)


async def qb_mirror(client, message):
    _mirror_leech(client, message, isQbit=True)


async def qb_unzip_mirror(client, message):
    _mirror_leech(client, message, extract=True, isQbit=True)


async def qb_zip_mirror(client, message):
    _mirror_leech(client, message, True, isQbit=True)


async def leech(client, message):
    _mirror_leech(client, message, isLeech=True)


async def unzip_leech(client, message):
    _mirror_leech(client, message, extract=True, isLeech=True)


async def zip_leech(client, message):
    _mirror_leech(client, message, True, isLeech=True)


async def qb_leech(client, message):
    _mirror_leech(client, message, isQbit=True, isLeech=True)


async def qb_unzip_leech(client, message):
    _mirror_leech(client, message, extract=True, isQbit=True, isLeech=True)


async def qb_zip_leech(client, message):
    _mirror_leech(client, message, True, isQbit=True, isLeech=True)


bot.add_handler(MessageHandler(mirror, filters=command(BotCommands.MirrorCommand) & CustomFilters.authorized))
bot.add_handler(MessageHandler(unzip_mirror, filters=command(BotCommands.UnzipMirrorCommand) & CustomFilters.authorized))
bot.add_handler(MessageHandler(zip_mirror, filters=command(BotCommands.ZipMirrorCommand) & CustomFilters.authorized))
bot.add_handler(MessageHandler(qb_mirror, filters=command(BotCommands.QbMirrorCommand) & CustomFilters.authorized))
bot.add_handler(MessageHandler(qb_unzip_mirror, filters=command(BotCommands.QbUnzipMirrorCommand) & CustomFilters.authorized))
bot.add_handler(MessageHandler(qb_zip_mirror, filters=command(BotCommands.QbZipMirrorCommand) & CustomFilters.authorized))
bot.add_handler(MessageHandler(leech, filters=command(BotCommands.LeechCommand) & CustomFilters.authorized))
bot.add_handler(MessageHandler(unzip_leech, filters=command(BotCommands.UnzipLeechCommand) & CustomFilters.authorized))
bot.add_handler(MessageHandler(zip_leech, filters=command(BotCommands.ZipLeechCommand) & CustomFilters.authorized))
bot.add_handler(MessageHandler(qb_leech, filters=command(BotCommands.QbLeechCommand) & CustomFilters.authorized))
bot.add_handler(MessageHandler(qb_unzip_leech, filters=command(BotCommands.QbUnzipLeechCommand) & CustomFilters.authorized))
bot.add_handler(MessageHandler(qb_zip_leech, filters=command(BotCommands.QbZipLeechCommand) & CustomFilters.authorized))
