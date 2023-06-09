from aiofiles.os import path as aiopath
from argparse import ArgumentParser
from asyncio import sleep
from base64 import b64encode
from os import path as ospath
from pyrogram import Client
from pyrogram.filters import command
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message
from re import match as re_match
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
from bot.helper.mirror_utils.download_utils.megasdk_download import add_mega_download
from bot.helper.mirror_utils.download_utils.qbit_download import add_qb_torrent
from bot.helper.mirror_utils.download_utils.rclone_download import add_rclone_download
from bot.helper.mirror_utils.download_utils.telegram_download import TelegramDownloadHelper
from bot.helper.mirror_utils.rclone_utils.list import RcloneList
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage, auto_delete_message, deleteMessage, editMessage, sendingMessage, get_tg_link_content


@new_task
async def _mirror_leech(client: Client, message: Message, isQbit=False, isLeech=False, sameDir=None, bulk=[]):
    text = message.text.split('\n')
    input_list = text[0].split()
    try:
        args = parser.parse_args(input_list[1:])
    except:
        await sendMessage(f'Invalid argument, type /{BotCommands.HelpCommand} for more details.', message)
        return

    if len(text) > 1 and text[1].startswith('Tag: '):
        try:
            id_ = int(text[1].split()[-1])
            message.from_user = await client.get_users(id_)
            await message.unpin()
        except:
            pass

    tag = message.from_user.mention
    reply_to = message.reply_to_message
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
            await auto_delete_message(message, msg, reply_to)
            return

    select, seed, multi, isBulk, isGofile, compress, extract, join = args.select, args.seed, args.multi, args.bulk, args.goFile, args.zipPswd, args.extractPswd, args.join
    link, name, folder_name, up, rcf = ' '.join(args.link), ' '.join(args.newName), ' '.join(args.sameDir), ' '.join(args.upload), ' '.join(args.rcloneFlags)
    file_ = tg_client = ratio = seed_time = headers = None
    multiid = get_multiid(user_id)
    bulk_start = bulk_end = 0
    gdrive_sharer = False

    if isinstance(multi, list):
        multi = multi[0]

    if compress is not None:
        compress = ' '.join(compress)
    if extract is not None:
        extract = ' '.join(extract)

    if seed:
        dargs = seed.split(':')
        ratio = dargs[0] or None
        if len(dargs) == 2:
            seed_time = dargs[1] or None
        seed = True
    elif seed is None:
        seed = True

    if isBulk:
        dargs = isBulk.split(':')
        bulk_start = dargs[0] or None
        if len(dargs) == 2:
            bulk_end = dargs[1] or None
        isBulk = True
    elif isBulk is None:
        isBulk = True

    if folder_name and not isBulk:
        seed = False
        ratio = seed_time = None
        folder_name = f'/{folder_name}'
        if sameDir is None:
            sameDir = {'total': multi, 'tasks': set(), 'name': folder_name}
        sameDir['tasks'].add(message.id)

    if config_dict['PREMIUM_MODE'] and not is_premium_user(user_id) and (multi > 0 or isBulk):
        await sendMessage(f'Upss {tag}, multi/bulk mode for premium user only', message)
        return

    if isBulk:
        await run_bulk(_mirror_leech, client, message, input_list, bulk_start, bulk_end, isQbit, isLeech, sameDir, bulk)
        return

    if bulk:
        del bulk[0]

    run_multi(_mirror_leech, client, message, multi, input_list, folder_name, isQbit, isLeech, sameDir, bulk)

    path = f'{DOWNLOAD_DIR}{message.id}{folder_name}'

    editable = await sendMessage('<i>Checking request, please wait...</i>', message)

    if link and is_tele_link(link):
        try:
            await intialize_savebot(user_dict.get('user_string'), True, user_id)
            tg_client, reply_to = await get_tg_link_content(link, user_id)
        except Exception as e:
            await editMessage(f'ERROR: {e}', editable)
            return
    elif not link and reply_to and reply_to.text:
        reply_text = reply_to.text.split('\n', 1)[0].strip()
        if reply_text and is_tele_link(reply_text):
            try:
                await intialize_savebot(user_dict.get('user_string'), True, user_id)
                tg_client, reply_to = await get_tg_link_content(reply_text, user_id)
            except Exception as e:
                await editMessage(f'ERROR: {e}', editable)
                return

    if reply_to:
        if not reply_to.sender_chat and not getattr(reply_to.from_user, 'is_bot', None):
            tag = reply_to.from_user.mention
        file_ = is_media(reply_to)
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
            await deleteMessage(editable)
            await auto_delete_message(message, fmsg, reply_to)
            return
        msg = await editMessage(help_msg, editable)
        await auto_delete_message(message, msg)
        return

    if (not up or up != 'rcl') and config_dict['MULTI_GDID'] and not isLeech and multi == 0 and not user_dict.get('cus_gdrive'):
        multiid, isGofile = await MultiSelect(client, editable, message.from_user, isGofile).get_buttons()
    if not multiid:
        await editMessage('Task has been cancelled!', editable)
        return

    if link:
        LOGGER.info(link)

    if isGofile:
        await editMessage('<i>GoFile upload has been enabled!</i>', editable)
        await sleep(1)

    if not is_mega_link(link) and not isQbit and not is_magnet(link) and not is_rclone_path(link) \
        and not is_gdrive_link(link) and not link.endswith('.torrent') and not file_:
        gdrive_sharer = is_sharar(link)
        content_type = await get_content_type(link)
        if not content_type or re_match(r'text/html|text/plain', content_type):
            host = urlparse(link).netloc
            try:
                await editMessage(f'<i>Generating direct link from {host}, please wait...</i>', editable)
                if 'gofile.io' in host:
                    if link.startswith('https://gofile.io'):
                        link, headers = await sync_to_async(direct_link_generator, link)
                else:
                    link = await sync_to_async(direct_link_generator, link)
                LOGGER.info(f'Generated link: {link}')
                await editMessage(f"<i>Found {'drive' if 'drive.google.com' in link else 'direct'} link:</i>\n<code>{link}</code>", editable)
                await sleep(1)
            except DirectDownloadLinkException as e:
                if str(e).startswith('ERROR:'):
                    await editMessage(f'{tag}, {e}', editable)
                    return

    if not isLeech:
        if config_dict['DEFAULT_UPLOAD'] == 'rc' and not up or up == 'rc':
            up = config_dict['RCLONE_PATH']
        if not up and config_dict['DEFAULT_UPLOAD'] == 'gd':
            up = 'gd'
        if up == 'gd' and not config_dict['GDRIVE_ID'] and not user_dict.get('cus_gdrive'):
            await editMessage('GDRIVE_ID not provided!', editable)
            return
        elif not up:
            await editMessage('No RClone destination!', editable)
            return
        elif up not in ['rcl', 'gd']:
            if up.startswith('mrcc:'):
                config_path = ospath.join('rclone', f'{message.from_user.id}.conf')
            else:
                config_path = 'rclone.conf'
            if not await aiopath.exists(config_path):
                await editMessage(f'RClone config: {config_path} not exists!', editable)
                return
        if up != 'gd' and not is_rclone_path(up):
            await editMessage('Wrong Rclone Upload Destination!', editable)
            return

    if link == 'rcl':
        link = await RcloneList(client, editable, user_id).get_rclone_path('rcd')
        if not is_rclone_path(link):
            await editMessage(link, editable)
            return
    if up == 'rcl' and not isLeech:
        up = await RcloneList(client, editable, user_id).get_rclone_path('rcu')
        if not is_rclone_path(up):
            await editMessage(up, editable)
            return

    if not is_rclone_path(link) and not is_gdrive_link(link):
        await deleteMessage(editable)

    listener = MirrorLeechListener(message, compress, extract, isQbit, isLeech, isGofile, tag, select, seed, name, multiid, sameDir, rcf, up, join)

    if file_:
        await TelegramDownloadHelper(listener).add_download(reply_to, f'{path}/', name, tg_client)
    elif is_rclone_path(link):
        if link.startswith('mrcc:'):
            link = link.split('mrcc:', 1)[1]
            config_path = f'rclone/{message.from_user.id}.conf'
        else:
            config_path = 'rclone.conf'
        if not await aiopath.exists(config_path):
            await editMessage(f'Rclone Config: {config_path} not Exists!', editable)
            return
        await deleteMessage(editable)
        await add_rclone_download(link, config_path, f'{path}/', name, listener)
    elif is_gdrive_link(link):
        if compress is None and extract is None and not isLeech and up == 'gd':
            gmsg = f'Use /{BotCommands.CloneCommand} to clone Google Drive file/folder\n\n'
            gmsg += 'Use arg <code>-z</code> to make zip of Google Drive folder\n\n'
            gmsg += 'Use <code>-e</code> to extracts Google Drive archive folder/file'
            await editMessage(gmsg, editable)
            await auto_delete_message(message, editable, reply_to)
            return
        await deleteMessage(editable)
        await add_gd_download(link, path, listener, name, gdrive_sharer)
    elif is_mega_link(link):
        await add_mega_download(link, f'{path}/', listener, name)
    elif isQbit:
        await add_qb_torrent(link, path, listener, ratio, seed_time)
    else:
        ussr = ' '.join(args.auth_user)
        pssw = ' '.join(args.auth_pswd)
        if ussr or pssw:
            auth = f'{ussr}:{pssw}'
            auth = 'Basic ' + b64encode(auth.encode()).decode('ascii')
        else:
            auth = ''
        if 'static.romsget.io' in link:
            headers = 'Referer: https://www.romsget.io/'
        await add_aria2c_download(link, path, listener, name, auth, ratio, seed_time, headers)


parser = ArgumentParser(description='Mirror-Leech args usage:', argument_default='')

parser.add_argument('link', nargs='*')
parser.add_argument('-s', action='store_true', default=False, dest='select')
parser.add_argument('-d', nargs='?', default=False, dest='seed')
parser.add_argument('-m', nargs='+', dest='sameDir')
parser.add_argument('-i', nargs='+', default=0, dest='multi', type=int)
parser.add_argument('-b', nargs='?', default=False, dest='bulk')
parser.add_argument('-n', nargs='+', dest='newName')
parser.add_argument('-e', nargs='*', default=None, dest='extractPswd')
parser.add_argument('-z', nargs='*', default=None, dest='zipPswd')
parser.add_argument('-j', action='store_true', default=False, dest='join')
parser.add_argument('-up', nargs='+', dest='upload')
parser.add_argument('-gf', action='store_true', default=False, dest='goFile')
parser.add_argument('-rcf', nargs='+', dest='rcloneFlags')
parser.add_argument('-au', nargs='+', dest='auth_user')
parser.add_argument('-ap', nargs='+', dest='auth_pswd')


async def mirror(client, message):
    _mirror_leech(client, message)


async def qb_mirror(client, message):
    _mirror_leech(client, message, isQbit=True)


async def leech(client, message):
    _mirror_leech(client, message, isLeech=True)


async def qb_leech(client, message):
    _mirror_leech(client, message, isQbit=True, isLeech=True)


bot.add_handler(MessageHandler(mirror, filters=command(BotCommands.MirrorCommand) & CustomFilters.authorized))
bot.add_handler(MessageHandler(qb_mirror, filters=command(BotCommands.QbMirrorCommand) & CustomFilters.authorized))
bot.add_handler(MessageHandler(leech, filters=command(BotCommands.LeechCommand) & CustomFilters.authorized))
bot.add_handler(MessageHandler(qb_leech, filters=command(BotCommands.QbLeechCommand) & CustomFilters.authorized))
