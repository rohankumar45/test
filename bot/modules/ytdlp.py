from aiofiles.os import path as aiopath
from aiohttp import ClientSession
from asyncio import sleep
from os import path as ospath
from pyrogram import Client
from pyrogram.filters import command, regex
from pyrogram.handlers import CallbackQueryHandler, MessageHandler
from pyrogram.types import CallbackQuery, Message
from re import split as re_split
from yt_dlp import YoutubeDL

from bot import bot, config_dict, user_data, DOWNLOAD_DIR, LOGGER
from bot.helper.ext_utils.bot_utils import get_readable_file_size, is_url, is_premium_user, is_media, UserDaily, sync_to_async, new_task, is_rclone_path, get_multiid
from bot.helper.ext_utils.force_mode import ForceMode
from bot.helper.ext_utils.multi import run_multi, MultiSelect
from bot.helper.listeners.tasks_listener import MirrorLeechListener
from bot.helper.mirror_utils.download_utils.yt_dlp_download import YoutubeDLHelper
from bot.helper.mirror_utils.rclone_utils.list import RcloneList
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage, sendMessage, editMessage, auto_delete_message, deleteMessage, sendingMessage


listener_dict = {}


def extract_info(link):
    with YoutubeDL({'usenetrc': True, 'cookiefile': 'cookies.txt', 'playlist_items': '0'}) as ydl:
        result = ydl.extract_info(link, download=False)
        if result is None:
            raise ValueError('Info result is None')
        return result


async def _mdisk(link: str, name: str):
    key = link.split('/')[-1]
    async with ClientSession() as session:
        async with session.get(f'https://diskuploader.entertainvideo.com/v1/file/cdnurl?param={key}') as resp:
            if resp.status == 200:
                resp_json = await resp.json()
                link = resp_json['source']
                if not name:
                    name = resp_json['filename']
            return name, link

@new_task
async def _ytdl(client: Client, message: Message, isZip=False, isLeech=False, sameDir={}):
    mssg = message.text
    msplit = message.text.split('\n')
    if len(msplit) > 1 and msplit[1].startswith('Tag: '):
        try:
            id_ = int(msplit[1].split()[-1])
            message.from_user = await client.get_users(id_)
            await message.unpin()
        except:
            pass
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
            await auto_delete_message(message, msg, reply_to)
            return
    msg_id = message.id
    tag = message.from_user.mention
    isSuperGroup = message.chat.type.name in ['SUPERGROUP', 'CHANNEL']
    qual = link = folder_name = ''
    select = isGofile = False
    multi, mi = 0, 1
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
    if user_dict.get('enable_pm') and isSuperGroup and not await fmode.ytdlp_pm_message:
        return
    if config_dict['DAILY_MODE']:
        if not is_premium_user(user_id) and await UserDaily(user_id).get_daily_limit():
            text = f'Upss, {tag} u have reach daily limit for today ({config_dict["DAILY_LIMIT_SIZE"]}GB), check ur status in /{BotCommands.UserSetCommand}'
            msg = await sendingMessage(text, message, config_dict['IMAGE_LIMIT'])
            await auto_delete_message(message, msg, reply_to)
            return

    args = mssg.split(maxsplit=4)
    args.pop(0)
    if len(args) > 0:
        index = 1
        for x in args:
            x = x.strip()
            if x == 's':
                select = True
                index += 1
            elif x == 'go':
                index += 1
                if not isLeech:
                    isGofile = True
            elif x.strip().isdigit():
                multi = int(x)
                mi = index
            elif x.startswith('m:'):
                marg = x.split('m:', 1)
                if len(marg) > 1:
                    folder_name = f"/{marg[1]}"
                    if not sameDir:
                        sameDir = set()
                    sameDir.add(message.id)
            else:
                break
        if multi == 0:
            args = mssg.split(maxsplit=index)
            if len(args) > index:
                x = args[index].strip()
                if not x.startswith(('n:', 'pswd:', 'up:', 'rcf:', 'opt:')):
                    link = re_split(r' opt: | pswd: | n: | rcf: | up: ', x)[0].strip()

    if config_dict['PREMIUM_MODE'] and not is_premium_user(user_id) and multi > 0:
        await sendMessage('Upss, multi mode for premium user only', message)
        return

    mlist = [client, message, multi, mi, folder_name]
    path = f'{DOWNLOAD_DIR}{msg_id}{folder_name}'

    if config_dict['AUTO_MUTE'] and isSuperGroup:
        if fmsg:= await fmode.auto_muted():
            await auto_delete_message(message, fmsg, reply_to)
            return

    name = mssg.split(' n: ', 1)
    name = re_split(' pswd: | opt: | up: | rcf: ', name[1])[0].strip() if len(name) > 1 else ''

    pswd = mssg.split(' pswd: ', 1)
    pswd = re_split(' n: | opt: | up: | rcf: ', pswd[1])[0] if len(pswd) > 1 else None

    opt = mssg.split(' opt: ', 1)
    opt = re_split(' n: | pswd: | up: | rcf: ', opt[1])[0].strip() if len(opt) > 1 else ''

    rcf = mssg.split(' rcf: ', 1)
    rcf = re_split(' n: | pswd: | up: | opt: ', rcf[1])[0].strip() if len(rcf) > 1 else None

    up = mssg.split(' up: ', 1)
    up = re_split(' n: | pswd: | rcf: | opt: ', up[1])[0].strip() if len(up) > 1 else None

    if reply_to and not is_media(reply_to) and len(link) == 0:
        link = reply_to.text.split('\n', 1)[0].strip()

    if not is_url(link):
        help_msg = f'Invalid argument, type /{BotCommands.HelpCommand} for more details.'
        if config_dict['AUTO_MUTE'] and isSuperGroup and (fmsg:= await fmode.auto_muted(help_msg)):
            await auto_delete_message(message, fmsg, reply_to)
            return
        msg = await sendMessage(help_msg, message)
        await auto_delete_message(message, msg)
        return

    check_ = await sendMessage(f'<i>Checking for <b>YT-DLP</b> link, please wait...</i>', message)

    if (not up or up != 'rcl') and config_dict['MULTI_GDID'] and not isLeech and multi == 0 and not user_dict.get('cus_gdrive'):
        multiid, isGofile = await MultiSelect(client, check_, message.from_user, isGofile).get_buttons()
    if not multiid:
        await editMessage('Task has been cancelled!', check_)
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

    if up == 'rcl' and not isLeech:
        up = await RcloneList(client, message).get_rclone_path('rcu')
        if not is_rclone_path(up):
            await editMessage(up, check_)
            return

    listener = MirrorLeechListener(message, isZip, isLeech=isLeech, isGofile=isGofile, pswd=pswd, tag=tag, newname=name, multiId=multiid, sameDir=sameDir, rcFlags=rcf, upPath=up)
    if 'mdisk.me' in link:
        name, link = await _mdisk(link, name)
    try:
        result = await sync_to_async(extract_info, link)
    except Exception as e:
        e = str(e).replace('<', ' ').replace('>', ' ')
        await editMessage(f'{tag} {e}', check_)
        run_multi(mlist, _ytdl, isZip, isLeech, sameDir)
        return
    run_multi(mlist, _ytdl, isZip, isLeech, sameDir)
    if not select:
        user_dict = user_data.get(user_id, {})
        if 'format:' in opt:
            opts = opt.split('|')
            for f in opts:
                if f.startswith('format:'):
                    qual = f.split('format:', 1)[1]
                    break
        elif user_dict.get('yt_ql'):
            qual = user_dict['yt_ql']
        else:
            qual = config_dict.get('YT_DLP_QUALITY')
    if qual:
        await deleteMessage(check_)
        playlist = 'entries' in result
        LOGGER.info(f'Downloading with YT-DLP: {link}')
        ydl = YoutubeDLHelper(listener)
        await ydl.add_download(link, path, name, qual, playlist, opt)
    else:
        buttons = ButtonMaker()
        best_video = 'bv*+ba/b'
        best_audio = 'ba/b'
        formats_dict = {}
        if 'entries' in result:
            for i in ['144', '240', '360', '480', '720', '1080', '1440', '2160']:
                video_format = f'bv*[height<=?{i}][ext=mp4]+ba[ext=m4a]/b[height<=?{i}]'
                b_data = f'{i}|mp4'
                formats_dict[b_data] = video_format
                buttons.button_data(f'{i}-mp4', f'qu {msg_id} {b_data} t')
                video_format = f'bv*[height<=?{i}][ext=webm]+ba/b[height<=?{i}]'
                b_data = f'{i}|webm'
                formats_dict[b_data] = video_format
                buttons.button_data(f'{i}-webm', f'qu {msg_id} {b_data} t')
            buttons.button_data('MP3', f'qu {msg_id} mp3 t')
            buttons.button_data('Best Videos', f'qu {msg_id} {best_video} t')
            buttons.button_data('Best Audios', f'qu {msg_id} {best_audio} t')
            buttons.button_data('Cancel', f'qu {msg_id} cancel')
            mbuttons = buttons.build_menu(3)
            await editMessage(f'{tag}, Choose Playlist Videos Quality:', check_, mbuttons)
        else:
            formats = result.get('formats')
            is_m4a = False
            if formats is not None:
                for frmt in formats:
                    if frmt.get('tbr'):

                        format_id = frmt['format_id']

                        if frmt.get('filesize'):
                            size = frmt['filesize']
                        elif frmt.get('filesize_approx'):
                            size = frmt['filesize_approx']
                        else:
                            size = 0

                        if frmt.get('video_ext') == 'none' and frmt.get('acodec') != 'none':
                            if frmt.get('audio_ext') == 'm4a':
                                is_m4a = True
                            b_name = f"{frmt['acodec']}-{frmt['ext']}"
                            v_format = f'ba[format_id={format_id}]'
                        elif frmt.get('height'):
                            height = frmt['height']
                            ext = frmt['ext']
                            fps = frmt['fps'] if frmt.get('fps') else ''
                            b_name = f'{height}p{fps}-{ext}'
                            ba_ext = '[ext=m4a]' if is_m4a and ext == 'mp4' else ''
                            v_format = f"bv*[format_id={format_id}]+ba{ba_ext}/b[height=?{height}]"
                        else:
                            continue

                        formats_dict.setdefault(b_name, {})[str(frmt['tbr'])] = [
                            size, v_format]

                for b_name, tbr_dict in formats_dict.items():
                    if len(tbr_dict) == 1:
                        tbr, v_list = next(iter(tbr_dict.items()))
                        buttonName = f'{b_name} ({get_readable_file_size(v_list[0])})'
                        buttons.button_data(buttonName, f'qu {msg_id} {b_name}|{tbr}')
                    else:
                        buttons.button_data(b_name, f'qu {msg_id} dict {b_name}')
            buttons.button_data('MP3', f'qu {msg_id} mp3')
            buttons.button_data('Best Video', f'qu {msg_id} {best_video}')
            buttons.button_data('Best Audio', f'qu {msg_id} {best_audio}')
            buttons.button_data('Cancel', f'qu {msg_id} cancel')
            mbuttons = buttons.build_menu(2)
            await editMessage(f'{tag}, Choose Video Quality:', check_, mbuttons)

        listener_dict[msg_id] = [listener, user_id, link, name, mbuttons, opt, formats_dict, path]
        _auto_cancel(check_, msg_id)


async def _qual_subbuttons(task_id: int, b_name: str, msg: Message):
    buttons = ButtonMaker()
    tbr_dict = listener_dict[task_id][6][b_name]
    for tbr, d_data in tbr_dict.items():
        button_name = f"{tbr}K ({get_readable_file_size(d_data[0])})"
        buttons.button_data(button_name, f"qu {task_id} {b_name}|{tbr}")
    buttons.button_data("Back", f"qu {task_id} back")
    buttons.button_data("Cancel", f"qu {task_id} cancel")
    await editMessage(f'Choose Bit rate for <b>{b_name}</b>:', msg, buttons.build_menu(2))


async def _mp3_subbuttons(task_id: str, msg: Message, playlist: bool=False):
    buttons = ButtonMaker()
    audio_qualities = [64, 128, 320]
    for q in audio_qualities:
        if playlist:
            i = 's'
            audio_format = f'ba/b-{q} t'
        else:
            i = ''
            audio_format = f'ba/b-{q}'
        buttons.button_data(f'{q}K-mp3', f'qu {task_id} {audio_format}')
    buttons.button_data('Back', f'qu {task_id} back')
    buttons.button_data('Cancel', f'qu {task_id} cancel')
    await editMessage(f'Choose Audio{i} Bitrate:', msg, buttons.build_menu(2))


@new_task
async def select_format(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    message = query.message
    data = query.data.split()
    task_id = int(data[1])
    try:
        task_info = listener_dict[task_id]
    except:
        await editMessage('This is an old task!', message)
        return
    uid = task_info[1]
    if user_id != uid and not await CustomFilters.sudo(client, query):
        await query.answer('This task is not for you!', show_alert=True)
        return
    elif data[2] == 'dict':
        await query.answer()
        b_name = data[3]
        await _qual_subbuttons(task_id, b_name, message)
        return
    elif data[2] == 'back':
        await query.answer()
        await editMessage('Choose Video Quality:', message, task_info[4])
        return
    elif data[2] == 'mp3':
        await query.answer()
        playlist = len(data) == 4
        await _mp3_subbuttons(task_id, message, playlist)
        return
    elif data[2] == 'cancel':
        await query.answer()
        await editMessage('Task has been cancelled!', message)
        del listener_dict[task_id]
    else:
        await query.answer()
        listener = task_info[0]
        link = task_info[2]
        name = task_info[3]
        opt = task_info[5]
        qual = data[2]
        path = task_info[7]
        if len(data) == 4:
            playlist = True
            if '|' in qual:
                qual = task_info[6][qual]
        else:
            playlist = False
            if '|' in qual:
                b_name, tbr = qual.split('|')
                qual = task_info[6][b_name][tbr][1]
        LOGGER.info(f'Downloading with YT-DLP: {link}')
        await deleteMessage(message)
        del listener_dict[task_id]
        ydl = YoutubeDLHelper(listener)
        await ydl.add_download(link, path, name, qual, playlist, opt)


@new_task
async def _auto_cancel(msg, task_id):
    await sleep(120)
    try:
        del listener_dict[task_id]
        await editMessage('Timed out! Task has been cancelled!', msg)
    except:
        pass


async def ytdl(client, message):
    _ytdl(client, message)


async def ytdlZip(client, message):
    _ytdl(client, message, True)


async def ytdlleech(client, message):
    _ytdl(client, message, isLeech=True)


async def ytdlZipleech(client, message):
    _ytdl(client, message, True, True)


bot.add_handler(MessageHandler(ytdl, filters=command(BotCommands.YtdlCommand) & CustomFilters.authorized))
bot.add_handler(MessageHandler(ytdlZip, filters=command(BotCommands.YtdlZipCommand) & CustomFilters.authorized))
bot.add_handler(MessageHandler(ytdlleech, filters=command(BotCommands.YtdlLeechCommand) & CustomFilters.authorized))
bot.add_handler(MessageHandler(ytdlZipleech, filters=command(BotCommands.YtdlZipLeechCommand) & CustomFilters.authorized))
bot.add_handler(CallbackQueryHandler(select_format, filters=regex('^qu')))