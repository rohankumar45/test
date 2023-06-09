from aiofiles.os import path as aiopath
from aiohttp import ClientSession
from argparse import ArgumentParser
from asyncio import wait_for, Event, wrap_future
from functools import partial
from os import path as ospath
from pyrogram import Client
from pyrogram.filters import command, regex, user
from pyrogram.handlers import CallbackQueryHandler, MessageHandler
from pyrogram.types import CallbackQuery, Message
from time import time
from yt_dlp import YoutubeDL

from bot import bot, config_dict, user_data, DOWNLOAD_DIR, LOGGER
from bot.helper.ext_utils.bot_utils import get_readable_file_size, is_url, is_premium_user, is_media, UserDaily, sync_to_async, new_task, is_rclone_path, get_multiid, get_readable_time, new_thread
from bot.helper.ext_utils.force_mode import ForceMode
from bot.helper.ext_utils.multi import run_multi, run_bulk, MultiSelect
from bot.helper.listeners.tasks_listener import MirrorLeechListener
from bot.helper.mirror_utils.download_utils.yt_dlp_download import YoutubeDLHelper
from bot.helper.mirror_utils.rclone_utils.list import RcloneList
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage, auto_delete_message, deleteMessage, sendingMessage


class YtSelection:
    def __init__(self, client: Client, message: Message, user_id: int):
        self.__message = message
        self.__user_id = user_id
        self.__client = client
        self.__is_m4a = False
        self.__time = time()
        self.__timeout = 120
        self.__is_playlist = False
        self.__main_buttons = None
        self.is_cancelled = False
        self.event = Event()
        self.formats = {}
        self.qual = None

    @new_thread
    async def __event_handler(self):
        pfunc = partial(select_format, obj=self)
        handler = self.__client.add_handler(CallbackQueryHandler(pfunc, filters=regex('^ytq') & user(self.__user_id)), group=-1)
        try:
            await wait_for(self.event.wait(), timeout=self.__timeout)
        except:
            await editMessage('Timed Out. Task has been cancelled!', self.__message)
            self.qual = None
            self.is_cancelled = True
            self.event.set()
        finally:
            self.__client.remove_handler(*handler)

    async def get_quality(self, result):
        future = self.__event_handler()
        buttons = ButtonMaker()
        if 'entries' in result:
            self.__is_playlist = True
            for i in ['144', '240', '360', '480', '720', '1080', '1440', '2160']:
                video_format = f'bv*[height<=?{i}][ext=mp4]+ba[ext=m4a]/b[height<=?{i}]'
                b_data = f'{i}|mp4'
                self.formats[b_data] = video_format
                buttons.button_data(f'{i}-mp4', f'ytq {b_data}')
                video_format = f'bv*[height<=?{i}][ext=webm]+ba/b[height<=?{i}]'
                b_data = f'{i}|webm'
                self.formats[b_data] = video_format
                buttons.button_data(f'{i}-webm', f'ytq {b_data}')
            buttons.button_data('MP3', 'ytq mp3')
            buttons.button_data('Audio Formats', 'ytq audio')
            buttons.button_data('Best Videos', 'ytq bv*+ba/b')
            buttons.button_data('Best Audios', 'ytq ba/b')
            buttons.button_data('Cancel', 'ytq cancel', 'footer')
            self.__main_buttons = buttons.build_menu(3)
            msg = f'Choose Available Playlist Videos Quality:\n\n<i>Timeout: {get_readable_time(self.__timeout - (time()-self.__time))}</i>'
        else:
            format_dict = result.get('formats')
            if format_dict is not None:
                for item in format_dict:
                    if item.get('tbr'):
                        format_id = item['format_id']

                        if item.get('filesize'):
                            size = item['filesize']
                        elif item.get('filesize_approx'):
                            size = item['filesize_approx']
                        else:
                            size = 0

                        if item.get('video_ext') == 'none' and item.get('acodec') != 'none':
                            if item.get('audio_ext') == 'm4a':
                                self.__is_m4a = True
                            b_name = f"{item['acodec']}-{item['ext']}"
                            v_format = f'ba[format_id={format_id}]'
                        elif item.get('height'):
                            height = item['height']
                            ext = item['ext']
                            fps = item['fps'] if item.get('fps') else ''
                            b_name = f'{height}p{fps}-{ext}'
                            ba_ext = '[ext=m4a]' if self.__is_m4a and ext == 'mp4' else ''
                            v_format = f'bv*[format_id={format_id}]+ba{ba_ext}/b[height=?{height}]'
                        else:
                            continue

                        self.formats.setdefault(b_name, {})[f"{item['tbr']}"] = [
                            size, v_format]

                for b_name, tbr_dict in self.formats.items():
                    if len(tbr_dict) == 1:
                        tbr, v_list = next(iter(tbr_dict.items()))
                        buttonName = f'{b_name} ({get_readable_file_size(v_list[0])})'
                        buttons.button_data(buttonName, f'ytq sub {b_name} {tbr}')
                    else:
                        buttons.button_data(b_name, f'ytq dict {b_name}')
            buttons.button_data('MP3', 'ytq mp3')
            buttons.button_data('Audio Formats', 'ytq audio')
            buttons.button_data('Best Video', 'ytq bv*+ba/b')
            buttons.button_data('Best Audio', 'ytq ba/b')
            buttons.button_data('Cancel', 'ytq cancel', 'footer')
            self.__main_buttons = buttons.build_menu(2)
            msg = f'Choose Available Video Quality:\n\n<i>Timeout: {get_readable_time(self.__timeout - (time() - self.__time))}</i>'
        await editMessage(msg, self.__message, self.__main_buttons)
        await wrap_future(future)
        return self.qual

    async def back_to_main(self):
        time_out = f'<i>Timeout: {get_readable_time(self.__timeout - (time()-  self.__time))}</i>'
        if self.__is_playlist:
            msg = f'Choose Available Playlist Videos Quality:\n\n{time_out}'
        else:
            msg = f'Choose Available Video Quality:\n\n{time_out}'
        await editMessage(msg, self.__message, self.__main_buttons)

    async def qual_subbuttons(self, b_name):
        buttons = ButtonMaker()
        tbr_dict = self.formats[b_name]
        for tbr, d_data in tbr_dict.items():
            button_name = f'{tbr}K ({get_readable_file_size(d_data[0])})'
            buttons.button_data(button_name, f'ytq sub {b_name} {tbr}')
        buttons.button_data('Back', 'ytq back', 'footer')
        buttons.button_data('Cancel', 'ytq cancel', 'footer')
        msg = f'Choose available Bit rate for <b>{b_name}</b>:\n\n<i>Timeout: {get_readable_time(self.__timeout - (time() - self.__time))}</i>'
        await editMessage(msg, self.__message, buttons.build_menu(2))

    async def mp3_subbuttons(self):
        i = 's' if self.__is_playlist else ''
        buttons = ButtonMaker()
        audio_qualities = [64, 128, 320]
        for q in audio_qualities:
            audio_format = f'ba/b-mp3-{q}'
            buttons.button_data(f'{q}K-mp3', f'ytq {audio_format}')
        buttons.button_data('Back', 'ytq back')
        buttons.button_data('Cancel', 'ytq cancel')
        msg = f'Choose mp3 Audio{i} Bitrate:\n\n<i>Timeout: {get_readable_time(self.__timeout - (time() - self.__time))}</i>'
        await editMessage(msg, self.__message, buttons.build_menu(3))

    async def audio_format(self):
        i = 's' if self.__is_playlist else ''
        buttons = ButtonMaker()
        for frmt in ['aac', 'alac', 'flac', 'm4a', 'opus', 'vorbis', 'wav']:
            audio_format = f'ba/b-{frmt}-'
            buttons.button_data(frmt, f'ytq aq {audio_format}')
        buttons.button_data('Back', 'ytq back', 'footer')
        buttons.button_data('Cancel', 'ytq cancel', 'footer')
        msg = f'Choose Audio{i} Format:\n\n<b>Timeout: {get_readable_time(self.__timeout - (time() - self.__time))}</b>'
        await editMessage(msg, self.__message, buttons.build_menu(3))

    async def audio_quality(self, format):
        i = 's' if self.__is_playlist else ''
        buttons = ButtonMaker()
        for qual in range(11):
            audio_format = f'{format}{qual}'
            buttons.button_data(qual, f'ytq {audio_format}')
        buttons.button_data('Back', 'ytq aq back')
        buttons.button_data('Cancel', 'ytq aq cancel')
        subbuttons = buttons.build_menu(5)
        msg = f'Choose Audio{i} Qaulity:\n0 is best and 10 is worst\n\n<b>Timeout: {get_readable_time(self.__timeout - (time() - self.__time))}</b>'
        await editMessage(msg, self.__message, subbuttons)


@new_task
async def select_format(_, query: CallbackQuery, obj: YtSelection):
    data = query.data.split()
    message = query.message
    await query.answer()

    if data[1] == 'dict':
        b_name = data[2]
        await obj.qual_subbuttons(b_name)
    elif data[1] == 'mp3':
        await obj.mp3_subbuttons()
    elif data[1] == 'audio':
        await obj.audio_format()
    elif data[1] == 'aq':
        if data[2] == 'back':
            await obj.audio_format()
        else:
            await obj.audio_quality(data[2])
    elif data[1] == 'back':
        await obj.back_to_main()
    elif data[1] == 'cancel':
        await editMessage('Task has been cancelled.', message)
        obj.qual = None
        obj.is_cancelled = True
        obj.event.set()
    else:
        if data[1] == 'sub':
            obj.qual = obj.formats[data[2]][data[3]][1]
        elif '|' in data[1]:
            obj.qual = obj.formats[data[1]]
        else:
            obj.qual = data[1]
        obj.event.set()


def extract_info(link, options):
    with YoutubeDL(options) as ydl:
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
async def _ytdl(client: Client, message: Message, isLeech=False, sameDir=None, bulk=[]):
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

    reply_to = message.reply_to_message
    user_id = message.from_user.id
    user_dict = user_data.get(user_id, {})
    tag = message.from_user.mention
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
    if user_dict.get('enable_pm') and isSuperGroup and not await fmode.ytdlp_pm_message:
        return
    if config_dict['DAILY_MODE']:
        if not is_premium_user(user_id) and await UserDaily(user_id).get_daily_limit():
            text = f'Upss, {tag} u have reach daily limit for today ({config_dict["DAILY_LIMIT_SIZE"]}GB), check ur status in /{BotCommands.UserSetCommand}'
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

    multi, isBulk, isGofile, select, compress = args.multi, args.bulk, args.goFile, args.select, args.zipPswd
    link, name, folder_name, up, rcf, opt = ' '.join(args.link), ' '.join(args.newName), ' '.join(args.sameDir), ' '.join(args.upload), ' '.join(args.rcloneFlags), ' '.join(args.options)
    multiid = get_multiid(user_id)
    bulk_start = bulk_end = 0
    qual = ''

    if config_dict['PREMIUM_MODE'] and not is_premium_user(user_id) and (multi > 0 or isBulk):
        await sendMessage('Upss, multi/bulk mode for premium user only', message)
        return

    if isBulk:
        await run_bulk(_ytdl, client, message, input_list, bulk_start, bulk_end, isLeech, sameDir, bulk)
        return

    if bulk:
        del bulk[0]

    path = f'{DOWNLOAD_DIR}{message.id}{folder_name}'

    if config_dict['AUTO_MUTE'] and isSuperGroup:
        if fmsg:= await fmode.auto_muted():
            await auto_delete_message(message, fmsg, reply_to)
            return

    opt = opt or config_dict['YT_DLP_OPTIONS']

    if not link and reply_to:
        if not reply_to.sender_chat and not getattr(reply_to.from_user, 'is_bot', None):
            tag = reply_to.from_user.mention
        if not is_media(reply_to) and len(link) == 0:
            link = reply_to.text.split('\n', 1)[0].strip()

    if not is_url(link):
        help_msg = f'Invalid argument, type /{BotCommands.HelpCommand} for more details.'
        if config_dict['AUTO_MUTE'] and isSuperGroup and (fmsg:= await fmode.auto_muted(help_msg)):
            await auto_delete_message(message, fmsg, reply_to)
            return
        msg = await sendMessage(help_msg, message)
        await auto_delete_message(message, msg)
        return

    editable = await sendMessage(f'<i>Checking for <b>YT-DLP</b> link, please wait...</i>', message)

    if (not up or up != 'rcl') and config_dict['MULTI_GDID'] and not isLeech and multi == 0 and not user_dict.get('cus_gdrive'):
        multiid, isGofile = await MultiSelect(client, editable, message.from_user, isGofile).get_buttons()
    if not multiid:
        await editMessage('Task has been cancelled!', editable)
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

    if up == 'rcl' and not isLeech:
        up = await RcloneList(client, message).get_rclone_path('rcu')
        if not is_rclone_path(up):
            await editMessage(up, editable)
            return

    listener = MirrorLeechListener(message, compress, isLeech=isLeech, isGofile=isGofile, tag=tag, newname=name, multiId=multiid, sameDir=sameDir, rcFlags=rcf, upPath=up)
    if 'mdisk.me' in link:
        name, link = await _mdisk(link, name)
    options = {'usenetrc': True, 'cookiefile': 'cookies.txt'}
    if opt:
        yt_opt = opt.split('|')
        for ytopt in yt_opt:
            key, value = map(str.strip, ytopt.split(':', 1))
            if value.startswith('^'):
                if '.' in value or value == '^inf':
                    value = float(value.split('^')[1])
                else:
                    value = int(value.split('^')[1])
            elif value.lower() == 'true':
                value = True
            elif value.lower() == 'false':
                value = False
            elif value.startswith(('{', '[', '(')) and value.endswith(('}', ']', ')')):
                value = eval(value)
            options[key] = value
        options['playlist_items'] = '0'
    try:
        result = await sync_to_async(extract_info, link, options)
    except Exception as e:
        e = str(e).replace('<', ' ').replace('>', ' ')
        await editMessage(f'{tag} {e}', editable)
        run_multi(ytdl, client, message, multi, input_list, folder_name, isLeech, sameDir, bulk)
        return
    run_multi(ytdl, client, message, multi, input_list, folder_name, isLeech, sameDir, bulk)
    if not select:
        user_dict = user_data.get(user_id, {})
        if 'format' in options:
            qual = options['format']
        elif user_dict.get('yt_opt'):
            qual = user_dict['yt_opt']

    if not qual:
        qual = await YtSelection(client, editable, user_id).get_quality(result)
        if not qual:
            return
    await deleteMessage(editable)
    LOGGER.info(f'Downloading with YT-DLP: {link}')
    playlist = 'entries' in result
    ydl = YoutubeDLHelper(listener)
    await ydl.add_download(link, path, name, qual, playlist, opt)


parser = ArgumentParser(description='YT-DLP args usage:', argument_default='')

parser.add_argument('link', nargs='*')
parser.add_argument('-s', action='store_true', default=False, dest='select')
parser.add_argument('-o', nargs='+', dest='options')
parser.add_argument('-m', nargs='+', dest='sameDir')
parser.add_argument('-i', nargs='+', default=0, dest='multi', type=int)
parser.add_argument('-b', nargs='?', default=False, dest='bulk')
parser.add_argument('-n', nargs='+', dest='newName')
parser.add_argument('-z', nargs='*', default=None, dest='zipPswd')
parser.add_argument('-gf', action='store_true', default=False, dest='goFile')
parser.add_argument('-up', nargs='+', dest='upload')
parser.add_argument('-rcf', nargs='+', dest='rcloneFlags')


async def ytdl(client, message):
    _ytdl(client, message)


async def ytdlleech(client, message):
    _ytdl(client, message, isLeech=True)


bot.add_handler(MessageHandler(ytdl, filters=command(BotCommands.YtdlCommand) & CustomFilters.authorized))
bot.add_handler(MessageHandler(ytdlleech, filters=command(BotCommands.YtdlLeechCommand) & CustomFilters.authorized))