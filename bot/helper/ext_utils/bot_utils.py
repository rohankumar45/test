from aiofiles import open as aiopen
from aiohttp import ClientSession
from asyncio import create_subprocess_shell, create_subprocess_exec, sleep, run_coroutine_threadsafe
from asyncio.subprocess import PIPE
from concurrent.futures import ThreadPoolExecutor
from functools import partial, wraps
from html import escape
from psutil import virtual_memory, cpu_percent, disk_usage, net_io_counters
from pyrogram.types import Message
from pytz import timezone
from re import match as re_match, search as re_search
from requests import head as rhead
from time import time
from urllib.request import urlopen

from bot import bot, bot_name, bot_loop, download_dict, download_dict_lock, botStartTime, user_data, config_dict, DATABASE_URL, LOGGER
from bot.helper.ext_utils.db_handler import DbManger
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker

THREADPOOL = ThreadPoolExecutor(max_workers=1000)

MAGNET_REGEX = r'magnet:\?xt=urn:(btih|btmh):[a-zA-Z0-9]*\s*'

URL_REGEX = r'^(?!\/)(rtmps?:\/\/|mms:\/\/|rtsp:\/\/|https?:\/\/|ftp:\/\/)?([^\/:]+:[^\/@]+@)?(www\.)?(?=[^\/:\s]+\.[^\/:\s]+)([^\/:\s]+\.[^\/:\s]+)(:\d+)?(\/[^#\s]*[\s\S]*)?(\?[^#\s]*)?(#.*)?$'

SIZE_UNITS = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']

STATUS_START = 0
PAGES = 1
PAGE_NO = 1


class MirrorStatus:
    STATUS_UPLOADING = 'Uploading'
    STATUS_UPLOADINGTOGO = 'Uploading'
    STATUS_DOWNLOADING = 'Downloading'
    STATUS_CLONING = 'Cloning'
    STATUS_QUEUEDL = 'QueueDl'
    STATUS_QUEUEUP = 'QueueUl'
    STATUS_PAUSED = 'Paused'
    STATUS_ARCHIVING = 'Archiving'
    STATUS_EXTRACTING = 'Extracting'
    STATUS_SPLITTING = 'Splitting'
    STATUS_MERGING= 'Merging'
    STATUS_CHECKING = 'CheckingUp'
    STATUS_SEEDING = 'Seeding'

class EngineStatus:
    STATUS_ARIA = 'Aria2'
    STATUS_GD = 'Google API'
    STATUS_MEGA = 'Negasdk'
    STATUS_GFILE = 'GoFile'
    STATUS_QB = 'qBittorrent'
    STATUS_TG = 'Pyrogram'
    STATUS_YT = 'YT-DLP'
    STATUS_EXT = 'p7zip'
    STATUS_SPLIT = 'FFmpeg'
    STATUS_CONVERT = 'FFmpeg'
    STATUS_ZIP = 'p7zip'
    STATUS_QUEUE = 'QSystem'
    STATUS_RCLONE = 'RClone'


class setInterval:
    def __init__(self, interval, action):
        self.interval = interval
        self.action = action
        self.task = bot_loop.create_task(self.__set_interval())

    async def __set_interval(self):
        while True:
            await sleep(self.interval)
            await self.action()

    def cancel(self):
        self.task.cancel()


class UserDaily:
    def __init__(self, user_id):
        self.__user_id = user_id

    async def get_daily_limit(self):
        await self.__check_status()
        if user_data[self.__user_id]['daily_limit'] >= config_dict['DAILY_LIMIT_SIZE'] * 1024**3:
            return True
        return False

    async def set_daily_limit(self, size):
        await self.__check_status()
        data = user_data[self.__user_id]['daily_limit'] + size
        await update_user_ldata(self.__user_id, 'daily_limit', data)

    async def __check_status(self):
        user_dict = user_data.get(self.__user_id, {})
        if not user_dict.get('daily_limit'):
            await self.__reset()
        if user_data[self.__user_id]['reset_limit'] - time() <= 0:
            await self.__reset()

    async def __reset(self):
        await update_user_ldata(self.__user_id, 'daily_limit', 1)
        await update_user_ldata(self.__user_id, 'reset_limit', time() + 86400)


def get_readable_file_size(size_in_bytes):
    if not size_in_bytes:
        return '0B'
    index = 0
    while size_in_bytes >= 1024 and index < len(SIZE_UNITS) - 1:
        size_in_bytes /= 1024
        index += 1
    return f'{size_in_bytes:.2f}{SIZE_UNITS[index]}' if index > 0 else f'{size_in_bytes:.2f}B'


async def getDownloadByGid(gid):
    async with download_dict_lock:
        return next((dl for dl in download_dict.values() if dl.gid() == gid), None)


async def getAllDownload(req_status: str):
    async with download_dict_lock:
        if req_status == 'all':
            return list(download_dict.values())
        return [dl for dl in download_dict.values() if dl.status() == req_status]


def bt_selection_buttons(id_: int):
    gid = id_[:12] if len(id_) > 20 else id_
    pincode = ''.join([n for n in id_ if n.isdigit()][:4])
    buttons = ButtonMaker()
    BASE_URL = config_dict['BASE_URL']
    if config_dict['WEB_PINCODE']:
        buttons.button_link('Select Files', f'{BASE_URL}/app/files/{id_}')
        buttons.button_data('Pincode', f'btsel pin {gid} {pincode}')
    else:
        buttons.button_link('Select Files', f'{BASE_URL}/app/files/{id_}?pin_code={pincode}')
    buttons.button_data('Done Selecting', f'btsel done {gid} {id_}')
    buttons.button_data('Cancel', f'btsel canc {gid} {id_}')
    return buttons.build_menu(2)


async def get_user_task(user_id: int):
    async with download_dict_lock:
        uid = [dl.message.from_user.id for dl in list(download_dict.values())]
    return uid.count(user_id)


def get_progress_bar_string(pct: str):
    pct = float(pct.strip('%'))
    p = min(max(pct, 0), 100)
    cFull = int(p // 8)
    p_str = config_dict['PROG_FINISH'] * cFull
    p_str += config_dict['PROG_UNFINISH'] * (12 - cFull)
    return str(p_str)


def action(message: str) -> str:
    acts = message.text.split(maxsplit=1)[0]
    return acts.replace('/','#').replace(f'@{bot_name}', '').replace(str(config_dict['CMD_SUFFIX']), '').lower()


def presuf_remname_name(user_dict: int, name: str):
    if name:
        if prename:= user_dict.get('user_prename'):
            name = f'{prename} {name}'
        if sufname:= user_dict.get('user_sufname'):
            try:
                fname, ext = str(name).rsplit('.', maxsplit=1)
                name = f'{fname} {sufname}.{ext}'
            except: pass
        if LEECH_FILENAME_PREFIX := config_dict['LEECH_FILENAME_PREFIX']:
            name = f'{LEECH_FILENAME_PREFIX} {name}'
        if remname:= user_dict.get('user_remname'):
            for x in remname.split('|'):
                name = str(name).replace(x, '')
    return name


def get_readable_message():
    msg = ''
    STATUS_LIMIT = config_dict['STATUS_LIMIT']
    tasks = len(download_dict)
    globals()['PAGES'] = (tasks + STATUS_LIMIT - 1) // STATUS_LIMIT
    if PAGE_NO > PAGES and PAGES != 0:
        globals()['STATUS_START'] = STATUS_LIMIT * (PAGES - 1)
        globals()['PAGE_NO'] = PAGES
    for download in list(download_dict.values())[STATUS_START:STATUS_LIMIT+STATUS_START]:
        message: Message = download.message
        isSuperGoup = message.chat.type.name in ['SUPERGROUP', 'CHANNEL']
        msg += f'<code>{escape(str(download.sname))}</code>'
        if isSuperGoup:
            reply_to = message.reply_to_message
            link = message.link if not reply_to or getattr(reply_to.from_user, 'is_bot', None) else reply_to.link
            msg += f'\n<b>┌ <a href="{link}"><i>{download.status()}...</i></a></b>'
        else:
            msg += f'\n<b>┌ <i>{download.status()}...</i></b>'
        extend_info = f'\n<b>├ Engine:<i> {download.eng()}</i></b>'
        if isSuperGoup:
            extend_info += f'\n<b>├ By:</b> <a href="https://t.me/{message.from_user.username}">{message.from_user.first_name}</a>'
        extend_info += f'\n<b>├ Action:</b> {action(message)}'
        if download.status() != MirrorStatus.STATUS_SEEDING:
            msg += f'\n<b>├ </b>{get_progress_bar_string(download.progress())}'
            msg += f'\n<b>├ Progress:</b> {download.progress()}'
            if download.status() == MirrorStatus.STATUS_SPLITTING and download.listener().isLeech:
                msg += f'\n<b>├ Split Size:</b> {get_readable_file_size(config_dict["LEECH_SPLIT_SIZE"])}'
            msg += f'\n<b>├ Processed:</b> {download.processed_bytes()}'
            msg += f'\n<b>├ Total Size:</b> {download.size()}'
            msg += f'\n<b>├ Speed:</b> {download.speed()}'
            msg += f'\n<b>├ ETA:</b> {download.eta() or "~"}'
            msg += f'\n<b>├ Elapsed: </b>{get_readable_time(time() - message.date.timestamp())}'
            if hasattr(download, 'seeders_num'):
                try:
                    msg += f'\n<b>├ S/L:</b> {download.seeders_num()}/{download.leechers_num()}'
                except:
                    pass
            msg += extend_info
        elif download.status() == MirrorStatus.STATUS_SEEDING:
            msg += f'\n<b>├ Size:</b> {download.size()}'
            msg += f'\n<b>├ Speed:</b> {download.upload_speed()}'
            msg += f'\n<b>├ Uploaded:</b> {download.uploaded_bytes()}'
            msg += f'\n<b>├ Ratio:</b> {download.ratio()}'
            msg += f'\n<b>├ Time:</b> {download.seeding_time()}'
            msg += f'\n<b>├ S/L:</b> {download.seeders_num()}/{download.leechers_num()}'
            msg += extend_info
        else:
            msg += f'\n<b>├ Size:</b> {download.size()}'
            msg += f'\n<b>├ Elapsed:</b> {get_readable_time(time() - message.date.timestamp())}'
            msg += extend_info
        msg += f'\n<b>└ </b><code>/{BotCommands.CancelMirror} {download.gid()}</code>\n\n'
    if not msg:
        return None, None
    bmsg = f'▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n'
    dl_speed = up_speed = 0
    for download in download_dict.values():
        tstatus = download.status()
        if tstatus == MirrorStatus.STATUS_DOWNLOADING:
            spd = download.speed()
            if 'K' in spd:
                dl_speed  += float(spd.split('K')[0]) * 1024
            elif 'M' in spd:
                dl_speed  += float(spd.split('M')[0]) * 1048576
        elif tstatus == MirrorStatus.STATUS_UPLOADING:
            spd = download.speed()
            if 'K' in spd:
                up_speed  += float(spd.split('K')[0]) * 1024
            elif 'M' in spd:
                up_speed  += float(spd.split('M')[0]) * 1048576
        elif tstatus == MirrorStatus.STATUS_SEEDING:
            spd = download.upload_speed()
            if 'K' in spd:
                up_speed  += float(spd.split('K')[0]) * 1024
            elif 'M' in spd:
                up_speed += float(spd.split('M')[0]) * 1048576
    bmsg += f'<b>CPU:</b> {cpu_percent()}% <b>| RAM:</b> {virtual_memory().percent}% <b>| FREE:</b> {get_readable_file_size(disk_usage(config_dict["DOWNLOAD_DIR"]).free)}\n'
    bmsg += f'<b>IN:</b> {get_readable_file_size(net_io_counters().bytes_recv)}<b> | OUT:</b> {get_readable_file_size(net_io_counters().bytes_sent)}\n'
    bmsg += f'<b>DL:</b> {get_readable_file_size(dl_speed)}/s<b> | UL:</b> {get_readable_file_size(up_speed)}/s <b>|</b> {get_readable_time(time() - botStartTime)}'
    buttons = ButtonMaker()
    if tasks > STATUS_LIMIT:
        msg += f'<b>Tasks:</b> {tasks}\n'
        buttons.button_data('<<', 'status pre')
        buttons.button_data(f'{PAGE_NO}/{PAGES}', 'status statistic')
        buttons.button_data('>>', 'status nex')
        buttons.button_data('Refresh', 'status refresh')
        buttons.button_data('Close', 'status close')
    else:
        buttons.button_data('Stats', 'status statistic')
        buttons.button_data('♻️', 'status refresh')
        buttons.button_data('Close', 'status close')
    return msg + bmsg, buttons.build_menu(3)


async def turn_page(data):
    STATUS_LIMIT = config_dict['STATUS_LIMIT']
    global STATUS_START, PAGE_NO
    async with download_dict_lock:
        if data[1] == "nex":
            if PAGE_NO == PAGES:
                STATUS_START = 0
                PAGE_NO = 1
            else:
                STATUS_START += STATUS_LIMIT
                PAGE_NO += 1
        elif data[1] == "pre":
            if PAGE_NO == 1:
                STATUS_START = STATUS_LIMIT * (PAGES - 1)
                PAGE_NO = PAGES
            else:
                STATUS_START -= STATUS_LIMIT
                PAGE_NO -= 1


def get_readable_time(seconds):
    periods = [('d', 86400), ('h', 3600), ('m', 60), ('s', 1)]
    result = ''
    for period_name, period_seconds in periods:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            result += f'{int(period_value)}{period_name} '
    return result


def is_media(message: Message):
    return message.document or message.photo or message.video or message.audio or \
            message.voice or message.video_note or message.sticker or message.animation or None


def is_magnet(url):
    return bool(re_match(MAGNET_REGEX, url))


def is_url(url: str):
    return bool(re_match(URL_REGEX, url))


def is_gdrive_link(url: str):
    return 'drive.google.com' in url


def is_sharar(url: str):
    if 'gdtot' in url:
        regex = r'(https?:\/\/.+\.gdtot\..+\/file\/\d+)'
    else:
        regex = r'(https?:\/\/(\S+)\..+\/file\/\S+)'
    return bool(re_match(regex, url))


def is_mega_link(url: str):
    return 'mega.nz' in url or 'mega.co.nz' in url


def is_tele_link(url: str):
    return url.startswith(('https://t.me/', 'tg://openmessage?user_id='))


def is_rclone_path(path):
    return bool(re_match(r'^(mrcc:)?(?!magnet:)(?![- ])[a-zA-Z0-9_\. -]+(?<! ):(?!.*\/\/).*$|^rcl$', path))


def is_premium_user(user_id: int):
    return user_data.get(user_id, {}).get('is_premium') or user_id == config_dict['OWNER_ID']


def get_date_time(message: Message):
    dt = message.date.astimezone(timezone(config_dict['TIME_ZONE']))
    return dt.strftime('%B %d, %Y'), dt.strftime('%H:%M:%S')


async def default_button(message: Message):
    try: message = await bot.get_messages(message.chat.id, message.id)
    except: pass
    try: del message.reply_markup.inline_keyboard[-1]
    except: pass
    if (markup:= message.reply_markup) and markup.inline_keyboard:
        return markup


def get_mega_link_type(url):
    return 'folder' if 'folder' in url or '/#F!' in url else 'file'


def get_multiid(user_id: int):
    multiid = ['Default', config_dict['GDRIVE_ID'], config_dict['INDEX_URL']]
    user_dict = user_data.get(user_id, {})
    cus_gdrive, cus_index = user_dict.get('cus_gdrive'), user_dict.get('cus_index')
    if cus_gdrive:
        index_url = ''
        if cus_gdrive and cus_index:
            index_url = cus_index
        multiid = ['Custom', cus_gdrive, index_url]
    return multiid



def get_content_type(link: str):
    try:
        res = rhead(link, allow_redirects=True, timeout=5, headers={'user-agent': 'Wget/1.12'})
        content_type = res.headers.get('content-type')
    except:
        try:
            res = urlopen(link, timeout=5)
            content_type = res.info().get_content_type()
        except:
            content_type = None
    return content_type


async def downlod_content(url: str, name: str):
    try:
        async with ClientSession() as session:
            async with session.get(url) as r:
                if r.status == 200:
                    async for data in r.content.iter_chunked(1024):
                        async with aiopen(name, 'ba') as f:
                            await f.write(data)
                    return True
                else:
                    LOGGER.error(f'Failed to download {name}, got respons {r.status}.')
    except Exception as e:
        LOGGER.error(e)


async def update_user_ldata(id_: int, key: str, value):
    user_data.setdefault(id_, {})
    user_data[id_][key] = value
    if DATABASE_URL and key not in ['thumb', 'rclone']:
        await DbManger().update_user_data(id_)


async def get_link(message: Message):
    link = ''
    pattern = r'https?:\/\/(www.)?\S+\.[a-z]{2,6}\b(\S*)|magnet:\?xt=urn:(btih|btmh):[-a-zA-Z0-9@:%_\+.~#?&//=]*\s*'
    if match:= re_search(pattern, message.text.strip()):
        link = match.group()
    if not link and (reply_to:= message.reply_to_message):
        if (media:= is_media(reply_to)):
            link = f'Source is media/file: {media.mime_type}' if not reply_to.photo else 'Source is image/photo'
        else:
            text = reply_to.text.split('\n', 1)[0].strip()
            link = text if is_magnet(text) or is_url(text) else ''
    return link


async def cmd_exec(cmd, shell=False):
    if shell:
        proc = await create_subprocess_shell(cmd, stdout=PIPE, stderr=PIPE)
    else:
        proc = await create_subprocess_exec(*cmd, stdout=PIPE, stderr=PIPE)
    stdout, stderr = await proc.communicate()
    stdout, stderr = stdout.decode().strip(), stderr.decode().strip()
    return stdout, stderr, proc.returncode


def new_task(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return bot_loop.create_task(func(*args, **kwargs))
    return wrapper


async def sync_to_async(func, *args, wait=True, **kwargs):
    '''Run sync function in async coroutine'''
    pfunc = partial(func, *args, **kwargs)
    future = bot_loop.run_in_executor(THREADPOOL, pfunc)
    return await future if wait else future


def async_to_sync(func, *args, wait=True, **kwargs):
    '''Run Async function in sync'''
    future = run_coroutine_threadsafe(func(*args, **kwargs), bot_loop)
    return future.result() if wait else future


def new_thread(func):
    @wraps(func)
    def wrapper(*args, wait=False, **kwargs):
        future = run_coroutine_threadsafe(func(*args, **kwargs), bot_loop)
        return future.result() if wait else future
    return wrapper