from aiofiles import open as aiopen
from aiofiles.os import path as aiopath
from asyncio import create_subprocess_exec, create_subprocess_shell
from os import environ
from pyrogram import Client

from bot import bot_dict, aria2, aria2_options, config_dict, kwargs, user_data, download_dict, status_reply_dict_lock, images, Interval, drive_dict, \
                LOGGER, GLOBAL_EXTENSION_FILTER, DEFAULT_SPLIT_SIZE, DRIVES_IDS, DRIVES_NAMES, INDEX_URLS, SHORTENER_APIS, SHORTENERES
from bot.helper.ext_utils.bot_utils import setInterval, sync_to_async
from bot.helper.ext_utils.db_handler import DbManger
from bot.helper.ext_utils.task_manager import start_from_queued
from bot.helper.mirror_utils.rclone_utils.serve import rclone_serve_booter
from bot.helper.telegram_helper.message_utils import update_all_messages
from bot.modules.torrent_search import initiate_search_tools


default_values = {'AUTO_DELETE_MESSAGE_DURATION': 30,
                  'AUTO_DELETE_UPLOAD_MESSAGE_DURATION': 0,
                  'DOWNLOAD_DIR': '/usr/src/app/downloads/',
                  'DISABLE_MIRROR_LEECH': '',
                  'USER_SESSION_STRING': '',
                  'LEECH_SPLIT_SIZE': DEFAULT_SPLIT_SIZE,
                  'RSS_DELAY': 900,
                  'STATUS_UPDATE_INTERVAL': 10,
                  'SEARCH_LIMIT': 0,
                  'STATUS_LIMIT': 10,
                  'RSS_DELAY': 900,
                  'GCLONE_URL': 'https://td.allindex.workers.dev/0:/gclone',
                  'UPSTREAM_BRANCH': 'master',
                  'FSUB_BUTTON_NAME': 'Join Channel',
                  'CHANNEL_USERNAME': 'R4ndom_Releases',
                  'AUTHOR_NAME': 'Anonim',
                  'AUTHOR_URL': 'https://t.me/MyLastAcc',
                  'DRIVE_SEARCH_TITLE': 'Drive Search',
                  'GD_INFO': 'By @LuckM4n',
                  'PROG_FINISH': '⬢',
                  'PROG_UNFINISH': '⬡',
                  'SOURCE_LINK_TITLE': 'Source Link',
                  'TIME_ZONE': 'Asia/Jakarta',
                  'TIME_ZONE_TITLE': 'UTC+7',
                  'NONPREMIUM_LIMIT': 5,
                  'DAILY_LIMIT_SIZE': 50,
                  'TSEARCH_TITLE': 'Torrent Search',
                  'IMAGE_ARIA': 'https://graph.org/file/24e3bbaa805d49823eddd.png',
                  'IMAGE_AUTH': 'https://graph.org/file/e6bfb75ad099e7d3664e0.png',
                  'IMAGE_BOLD': 'https://graph.org/file/d81b39cf4bf75b15c536b.png',
                  'IMAGE_BYE': 'https://graph.org/file/95530c7749ebc00c5c6ed.png',
                  'IMAGE_CANCEL': 'https://graph.org/file/86c4c933b7f106ed5edd8.png',
                  'IMAGE_CAPTION': 'https://graph.org/file/b430ad0a09dd01895cc1a.png',
                  'IMAGE_COMPLETE': images,
                  'IMAGE_CONEDIT': 'https://graph.org/file/46b769fc94f22e97c0abd.png',
                  'IMAGE_CONPRIVATE': 'https://graph.org/file/8de9925ed509c9307e267.png',
                  'IMAGE_CONSET': 'https://graph.org/file/25ea7ae75e9ceac315826.png',
                  'IMAGE_CONVIEW': 'https://graph.org/file/ab51c10fb28ef66482a1b.png',
                  'IMAGE_DUMID': 'https://graph.org/file/ea990868f925440392ba7.png',
                  'IMAGE_FSUB': 'https://graph.org/file/672ade2552f8b3e9e1a73.png',
                  'IMAGE_GD': 'https://graph.org/file/f1ebf50425a0fcb2bd01a.png',
                  'IMAGE_HELP': 'https://graph.org/file/f75791f8ea5b7239d556d.png',
                  'IMAGE_HTML': 'https://graph.org/file/ea4997ce8dd4500f6d488.png',
                  'IMAGE_IMDB': 'https://telegra.ph/file/a8125cb4d68f7d185c760.png',
                  'IMAGE_INFO': 'https://telegra.ph/file/9582c7742e7d12381947c.png',
                  'IMAGE_ITALIC': 'https://graph.org/file/c956e4c553717a214903d.png',
                  'IMAGE_LIMIT': 'https://graph.org/file/a2afdc815eda7ac91d9de.png',
                  'IMAGE_LOGS': 'https://graph.org/file/51cb3c085a5287d909009.png',
                  'IMAGE_MEDINFO': 'https://graph.org/file/62b0667c1ebb0a2f28f82.png',
                  'IMAGE_MONO': 'https://graph.org/file/b7c1ebd3ff72ef262af4c.png',
                  'IMAGE_NORMAL': 'https://graph.org/file/e9786dbca02235e9a6899.png',
                  'IMAGE_OWNER': 'https://graph.org/file/7d3c014629529d26f9587.png',
                  'IMAGE_PAUSE': 'https://graph.org/file/e82080dcbd9ae6b0e62ef.png',
                  'IMAGE_PM': 'https://graph.org/file/0a74be6c5e3172c638adc.png',
                  'IMAGE_PRENAME': 'https://graph.org/file/4923724fea2d858b6eb1e.png',
                  'IMAGE_QBIT': 'https://graph.org/file/0ff0d45c17ac52fe38298.png',
                  'IMAGE_RCLONE': 'https://telegra.ph/file/e6daed8fd63e772a7ca10.png',
                  'IMAGE_REMNAME': 'https://graph.org/file/dd4854271072ae2eabc59.png',
                  'IMAGE_RSS': 'https://graph.org/file/564aee8a05d3d30bbf53d.png',
                  'IMAGE_SEARCH': 'https://graph.org/file/8a3ae9d84662b5e163e7e.png',
                  'IMAGE_STATS': 'https://telegra.ph/file/52d8dc6a50799c96b8b89.png',
                  'IMAGE_STATUS': 'https://graph.org/file/75e449cbf201ad364ce39.png',
                  'IMAGE_SUFNAME': 'https://graph.org/file/e1e2a6afdabbce19aa0f0.png',
                  'IMAGE_TXT': 'https://graph.org/file/ec2fbca54b9e41081fade.png',
                  'IMAGE_UNAUTH': 'https://graph.org/file/06bdd8695368b8ee9edec.png',
                  'IMAGE_UNKNOW': 'https://telegra.ph/file/b4af9bed9b588bcd331ab.png',
                  'IMAGE_USER': 'https://graph.org/file/989709a50ac468c3a4953.png',
                  'IMAGE_USETIINGS': 'https://graph.org/file/4e358b9a735492726a887.png',
                  'IMAGE_WEL': 'https://graph.org/file/d053d5ca7fa71913aa575.png',
                  'IMAGE_WIBU': 'https://graph.org/file/f0247d41171f08fe60288.png',
                  'IMAGE_YT': 'https://graph.org/file/3755f52bc43d7e0ce061b.png',
                  'IMAGE_YT': 'https://graph.org/file/3755f52bc43d7e0ce061b.png'}

async def load_config():
#============================ REQUIRED ================================
    BOT_TOKEN = environ.get('BOT_TOKEN', '')
    BOT_TOKEN = BOT_TOKEN if BOT_TOKEN else config_dict['BOT_TOKEN']

    TELEGRAM_API = environ.get('TELEGRAM_API', '')
    TELEGRAM_API = int(TELEGRAM_API) if TELEGRAM_API else config_dict['TELEGRAM_API']

    TELEGRAM_HASH = environ.get('TELEGRAM_HASH', '')
    TELEGRAM_HASH = TELEGRAM_HASH if TELEGRAM_HASH else config_dict['TELEGRAM_HASH']

    OWNER_ID = environ.get('OWNER_ID', '')
    OWNER_ID = int(OWNER_ID) if OWNER_ID else config_dict['OWNER_ID']

    DOWNLOAD_DIR = environ.get('DOWNLOAD_DIR', '/usr/src/app/downloads/')
    if not DOWNLOAD_DIR.endswith('/'):
        DOWNLOAD_DIR += '/'

    GDRIVE_ID = environ.get('GDRIVE_ID', '')
    RCLONE_PATH = environ.get('RCLONE_PATH', '')
    RCLONE_FLAGS = environ.get('RCLONE_FLAGS', '')

    DEFAULT_UPLOAD = environ.get('DEFAULT_UPLOAD', '')
    if DEFAULT_UPLOAD != 'rc':
        DEFAULT_UPLOAD = 'gd'
#======================================================================


#=========================== OPTIONALS ===============================
    AUTHORIZED_CHATS = environ.get('AUTHORIZED_CHATS', '')
    if AUTHORIZED_CHATS:
        aid = AUTHORIZED_CHATS.split()
        for id_ in aid:
            user_data[int(id_.strip())] = {'is_auth': True}

    SUDO_USERS = environ.get('SUDO_USERS', '')
    if SUDO_USERS:
        aid = SUDO_USERS.split()
        for id_ in aid:
            user_data[int(id_.strip())] = {'is_sudo': True}

    EXTENSION_FILTER = environ.get('EXTENSION_FILTER', '')
    if EXTENSION_FILTER:
        fx = EXTENSION_FILTER.split()
        for x in fx:
            if x.strip().startswith('.'):
                x = x.lstrip('.')
            GLOBAL_EXTENSION_FILTER.append(x.strip().lower())

    TORRENT_TIMEOUT = environ.get('TORRENT_TIMEOUT', '')
    downloads = aria2.get_downloads()
    if TORRENT_TIMEOUT:
        for download in downloads:
            if not download.is_complete:
                try:
                    await sync_to_async(aria2.client.change_option, download.gid, {'bt-stop-timeout': TORRENT_TIMEOUT})
                except Exception as e:
                    LOGGER.error(e)
        aria2_options['bt-stop-timeout'] = TORRENT_TIMEOUT
        if DATABASE_URL:
            await DbManger().update_aria2('bt-stop-timeout', TORRENT_TIMEOUT)
        TORRENT_TIMEOUT = int(TORRENT_TIMEOUT)
    else:
        for download in downloads:
            if not download.is_complete:
                try:
                    await sync_to_async(aria2.client.change_option, download.gid, {'bt-stop-timeout': '0'})
                except Exception as e:
                    LOGGER.error(e)
        aria2_options['bt-stop-timeout'] = '0'
        if DATABASE_URL:
            await DbManger().update_aria2('bt-stop-timeout', '0')
        TORRENT_TIMEOUT = ''

    QUEUE_ALL = environ.get('QUEUE_ALL', '')
    QUEUE_ALL = int(QUEUE_ALL) if QUEUE_ALL else ''

    QUEUE_DOWNLOAD = environ.get('QUEUE_DOWNLOAD', '')
    QUEUE_DOWNLOAD = int(QUEUE_DOWNLOAD) if QUEUE_DOWNLOAD else ''

    QUEUE_UPLOAD = environ.get('QUEUE_UPLOAD', '')
    QUEUE_UPLOAD = int(QUEUE_UPLOAD) if QUEUE_UPLOAD else ''

    QUEUE_COMPLETE = environ.get('QUEUE_COMPLETE', 'False').lower() == 'true'

    DISABLE_MIRROR_LEECH = environ.get('DISABLE_MIRROR_LEECH', '')
    GCLONE_URL = environ.get('GCLONE_URL', 'https://td.allindex.workers.dev/0:/gclone')
    INDEX_URL = environ.get('INDEX_URL', '').rstrip('/')
    USE_SERVICE_ACCOUNTS = environ.get('USE_SERVICE_ACCOUNTS', 'False').lower() == 'true'
    CMD_SUFFIX = environ.get('CMD_SUFFIX', '')
    DATABASE_URL = environ.get('DATABASE_URL', '')
    AUTO_THUMBNAIL = environ.get('AUTO_THUMBNAIL', 'False').lower() == 'true'
    PREMIUM_MODE = environ.get('PREMIUM_MODE', 'False').lower() == 'true'
    DAILY_MODE = environ.get('DAILY_MODE', 'False').lower() == 'true'
    MULTI_GDID = environ.get('MULTI_GDID', 'False').lower() == 'true'
    MEDIA_GROUP = environ.get('MEDIA_GROUP', 'False').lower() == 'true'
    STOP_DUPLICATE = environ.get('STOP_DUPLICATE', 'False').lower() == 'true'
    IS_TEAM_DRIVE = environ.get('IS_TEAM_DRIVE', 'False').lower() == 'true'
    MULTI_TIMEGAP = int(environ.get('MULTI_TIMEGAP', 5))
    AS_DOCUMENT = environ.get('AS_DOCUMENT', 'False').lower() == 'true'
    SAVE_MESSAGE = environ.get('SAVE_MESSAGE', 'False').lower() == 'true'
    LEECH_FILENAME_PREFIX = environ.get('LEECH_FILENAME_PREFIX', '')
    USER_SESSION_STRING = environ.get('USER_SESSION_STRING', '')
    SAVE_SESSION_STRING = environ.get('SAVE_SESSION_STRING', '')
    USERBOT_LEECH = environ.get('USERBOT_LEECH', 'False').lower() == 'true'
    AUTO_DELETE_MESSAGE_DURATION = int(environ.get('AUTO_DELETE_MESSAGE_DURATION', 30))
    AUTO_DELETE_UPLOAD_MESSAGE_DURATION = int(environ.get('AUTO_DELETE_UPLOAD_MESSAGE_DURATION', 0))
    YT_DLP_OPTIONS = environ.get('YT_DLP_OPTIONS', '')
    DAILY_LIMIT_SIZE = int(environ.get('DAILY_LIMIT_SIZE', 2))
    STATUS_UPDATE_INTERVAL = int(environ.get('STATUS_UPDATE_INTERVAL', 5))
    if len(download_dict) != 0:
        async with status_reply_dict_lock:
            if Interval:
                Interval[0].cancel()
                Interval.clear()
                Interval.append(setInterval(STATUS_UPDATE_INTERVAL, update_all_messages))

    INCOMPLETE_TASK_NOTIFIER = environ.get('INCOMPLETE_TASK_NOTIFIER', 'False').lower() == 'true'
    if not INCOMPLETE_TASK_NOTIFIER and DATABASE_URL:
        await DbManger().trunc_table('tasks')
#======================================================================

#============================= RCLONE =================================
    RCLONE_SERVE_URL = environ.get('RCLONE_SERVE_URL', '')
    RCLONE_SERVE_PORT = environ.get('RCLONE_SERVE_PORT', '')
    RCLONE_SERVE_USER = environ.get('RCLONE_SERVE_USER', '')
    RCLONE_SERVE_PASS = environ.get('RCLONE_SERVE_PASS', '')
#======================================================================

#============================== LOGS ==================================
    ONCOMPLETE_LEECH_LOG = environ.get('ONCOMPLETE_LEECH_LOG', 'True').lower() == 'true'
    LEECH_LOG = environ.get('LEECH_LOG', '')
    LEECH_LOG = int(LEECH_LOG) if LEECH_LOG else ''

    MIRROR_LOG = environ.get('MIRROR_LOG', '')
    MIRROR_LOG = int(MIRROR_LOG) if MIRROR_LOG else ''

    OTHER_LOG = environ.get('OTHER_LOG', '')
    OTHER_LOG = int(OTHER_LOG) if OTHER_LOG else ''

    LINK_LOG = environ.get('LINK_LOG', '')
    LINK_LOG = int(LINK_LOG) if LINK_LOG else ''

#======================================================================

#============================= LIMITS =================================
    EQUAL_SPLITS = environ.get('EQUAL_SPLITS', 'False').lower() == 'true'

    CLONE_LIMIT = environ.get('CLONE_LIMIT', '')
    CLONE_LIMIT = float(CLONE_LIMIT) if CLONE_LIMIT else ''

    LEECH_LIMIT = environ.get('LEECH_LIMIT', '')
    LEECH_LIMIT = float(LEECH_LIMIT) if LEECH_LIMIT else ''

    LEECH_SPLIT_SIZE = environ.get('LEECH_SPLIT_SIZE', '')
    LEECH_SPLIT_SIZE = int(LEECH_SPLIT_SIZE) if LEECH_SPLIT_SIZE else ''

    MEGA_LIMIT = environ.get('MEGA_LIMIT', '')
    MEGA_LIMIT = float(MEGA_LIMIT) if MEGA_LIMIT else ''

    NONPREMIUM_LIMIT = environ.get('NONPREMIUM_LIMIT', '5')
    NONPREMIUM_LIMIT = float(NONPREMIUM_LIMIT) if NONPREMIUM_LIMIT else ''

    STATUS_LIMIT = environ.get('STATUS_LIMIT', '')
    STATUS_LIMIT = int(STATUS_LIMIT) if STATUS_LIMIT else 10

    TORRENT_DIRECT_LIMIT = environ.get('TORRENT_DIRECT_LIMIT', '')
    TORRENT_DIRECT_LIMIT = float(TORRENT_DIRECT_LIMIT) if TORRENT_DIRECT_LIMIT else ''

    TOTAL_TASKS_LIMIT = environ.get('TOTAL_TASKS_LIMIT', '')
    TOTAL_TASKS_LIMIT = int(TOTAL_TASKS_LIMIT) if TOTAL_TASKS_LIMIT else ''

    USER_TASKS_LIMIT = environ.get('USER_TASKS_LIMIT', '')
    USER_TASKS_LIMIT = int(USER_TASKS_LIMIT) if USER_TASKS_LIMIT else ''

    ZIP_UNZIP_LIMIT = environ.get('ZIP_UNZIP_LIMIT', '')
    ZIP_UNZIP_LIMIT = float(ZIP_UNZIP_LIMIT) if ZIP_UNZIP_LIMIT else ''

    STORAGE_THRESHOLD = environ.get('STORAGE_THRESHOLD', '')
    STORAGE_THRESHOLD = float(STORAGE_THRESHOLD) if STORAGE_THRESHOLD else ''

    YTDL_LIMIT = environ.get('YTDL_LIMIT', '')
    YTDL_LIMIT = float(YTDL_LIMIT) if YTDL_LIMIT else ''

    MAX_YTPLAYLIST = environ.get('MAX_YTPLAYLIST', '')
    MAX_YTPLAYLIST = int(MAX_YTPLAYLIST) if MAX_YTPLAYLIST else ''
#======================================================================


#============================= GOFILE =================================
    GOFILE = environ.get('GOFILE', 'False').lower() == 'true'
    GOFILETOKEN = environ.get('GOFILETOKEN', '')
    GOFILEBASEFOLDER = environ.get('GOFILEBASEFOLDER', '')
    if not GOFILETOKEN or not GOFILEBASEFOLDER:
        GOFILE = False
#======================================================================


#============================= FORCE =================================
    # Auto Mute
    AUTO_MUTE = environ.get('AUTO_MUTE', 'False').lower() == 'true'
    MUTE_CHAT_ID = int(environ.get('MUTE_CHAT_ID', -1001768377379))
    AUTO_MUTE_DURATION = int(environ.get('AUTO_MUTE_DURATION', 30))
    # Username
    FUSERNAME = environ.get('FUSERNAME', 'False').lower() == 'true'
    # Subscribe
    FSUB = environ.get('FSUB', 'False').lower() == 'true'
    FSUB_CHANNEL_ID = int(environ.get('FSUB_CHANNEL_ID', -1001768377379))
    FSUB_BUTTON_NAME = environ.get('FSUB_BUTTON_NAME', 'Join Channel')
    CHANNEL_USERNAME = environ.get('CHANNEL_USERNAME', 'TrollReleases')
#======================================================================


#============================ STICKERS ================================
    STICKERID_COUNT = environ.get('STICKERID_COUNT', '')
    STICKERID_ERROR = environ.get('STICKERID_ERROR', '')
    STICKERID_LEECH = environ.get('STICKERID_LEECH', '')
    STICKERID_MIRROR = environ.get('STICKERID_MIRROR', '')
    STICKER_DELETE_DURATION = int(environ.get('STICKER_DELETE_DURATION', 0))
#======================================================================


#============================= IMAGES =================================
    ENABLE_IMAGE_MODE = environ.get('ENABLE_IMAGE_MODE', 'True').lower() == 'true'
    IMAGE_ARIA = environ.get('IMAGE_ARIA', 'https://graph.org/file/24e3bbaa805d49823eddd.png')
    IMAGE_AUTH = environ.get('IMAGE_AUTH', 'https://graph.org/file/e6bfb75ad099e7d3664e0.png')
    IMAGE_BOLD = environ.get('IMAGE_BOLD', 'https://graph.org/file/d81b39cf4bf75b15c536b.png')
    IMAGE_BYE = environ.get('IMAGE_BYE', 'https://graph.org/file/95530c7749ebc00c5c6ed.png')
    IMAGE_CANCEL = environ.get('IMAGE_CANCEL', 'https://graph.org/file/86c4c933b7f106ed5edd8.png')
    IMAGE_CAPTION = environ.get('IMAGE_CAPTION', 'https://graph.org/file/b430ad0a09dd01895cc1a.png')
    IMAGE_COMPLETE = environ.get('IMAGE_COMPLETE', images)
    IMAGE_CONEDIT = environ.get('IMAGE_CONEDIT', 'https://graph.org/file/46b769fc94f22e97c0abd.png')
    IMAGE_CONPRIVATE= environ.get('IMAGE_CONPRIVATE', 'https://graph.org/file/8de9925ed509c9307e267.png')
    IMAGE_CONSET = environ.get('IMAGE_CONSET', 'https://graph.org/file/25ea7ae75e9ceac315826.png')
    IMAGE_CONVIEW = environ.get('IMAGE_CONVIEW', 'https://graph.org/file/ab51c10fb28ef66482a1b.png')
    IMAGE_DUMID = environ.get('IMAGE_DUMID', 'https://graph.org/file/ea990868f925440392ba7.png')
    IMAGE_FSUB = environ.get('IMAGE_FSUB', 'https://graph.org/file/672ade2552f8b3e9e1a73.png')
    IMAGE_GD = environ.get('IMAGE_GD', 'https://graph.org/file/f1ebf50425a0fcb2bd01a.png')
    IMAGE_HELP = environ.get('IMAGE_HELP', 'https://graph.org/file/f75791f8ea5b7239d556d.png')
    IMAGE_HTML = environ.get('IMAGE_HTML', 'https://graph.org/file/ea4997ce8dd4500f6d488.png')
    IMAGE_IMDB = environ.get('IMAGE_IMDB', 'https://telegra.ph/file/a8125cb4d68f7d185c760.png')
    IMAGE_INFO = environ.get('IMAGE_INFO', 'https://telegra.ph/file/9582c7742e7d12381947c.png')
    IMAGE_ITALIC = environ.get('IMAGE_ITALIC', 'https://graph.org/file/c956e4c553717a214903d.png')
    IMAGE_LIMIT = environ.get('IMAGE_LIMIT', 'https://graph.org/file/a2afdc815eda7ac91d9de.png')
    IMAGE_LOGS = environ.get('IMAGE_LOGS', 'https://graph.org/file/51cb3c085a5287d909009.png')
    IMAGE_MEDINFO = environ.get('IMAGE_MEDINFO', 'https://graph.org/file/62b0667c1ebb0a2f28f82.png')
    IMAGE_MONO = environ.get('IMAGE_MONO', 'https://graph.org/file/b7c1ebd3ff72ef262af4c.png')
    IMAGE_NORMAL = environ.get('IMAGE_NORMAL', 'https://graph.org/file/e9786dbca02235e9a6899.png')
    IMAGE_OWNER = environ.get('IMAGE_OWNER', 'https://graph.org/file/7d3c014629529d26f9587.png')
    IMAGE_PAUSE = environ.get('IMAGE_PAUSE', 'https://graph.org/file/e82080dcbd9ae6b0e62ef.png')
    IMAGE_PM = environ.get('IMAGE_PM', 'https://graph.org/file/0a74be6c5e3172c638adc.png')
    IMAGE_PRENAME = environ.get('IMAGE_PRENAME', 'https://graph.org/file/9dbfc87c46c4b5d8834f4.png')
    IMAGE_QBIT = environ.get('IMAGE_QBIT', 'https://graph.org/file/0ff0d45c17ac52fe38298.png')
    IMAGE_RCLONE = environ.get('IMAGE_RCLONE', 'https://telegra.ph/file/e6daed8fd63e772a7ca10.png')
    IMAGE_REMNAME = environ.get('IMAGE_REMNAME', 'https://graph.org/file/9dbfc87c46c4b5d8834f4.png')
    IMAGE_RSS = environ.get('IMAGE_RSS', 'https://graph.org/file/564aee8a05d3d30bbf53d.png')
    IMAGE_SEARCH = environ.get('IMAGE_SEARCH', 'https://graph.org/file/8a3ae9d84662b5e163e7e.png')
    IMAGE_STATS = environ.get('IMAGE_STATS', 'https://graph.org/file/6026a8b1dfedfe646b39b.png')
    IMAGE_STATUS = environ.get('IMAGE_STATUS', 'https://graph.org/file/75e449cbf201ad364ce39.png')
    IMAGE_SUFNAME = environ.get('IMAGE_SUFNAME', 'https://graph.org/file/e1e2a6afdabbce19aa0f0.png')
    IMAGE_TXT = environ.get('IMAGE_TXT', 'https://graph.org/file/ec2fbca54b9e41081fade.png')
    IMAGE_UNAUTH = environ.get('IMAGE_UNAUTH', 'https://graph.org/file/06bdd8695368b8ee9edec.png')
    IMAGE_UNKNOW = environ.get('IMAGE_UNKNOW', 'https://telegra.ph/file/b4af9bed9b588bcd331ab.png')
    IMAGE_USER = environ.get('IMAGE_USER', 'https://graph.org/file/989709a50ac468c3a4953.png')
    IMAGE_USETIINGS = environ.get('IMAGE_USETIINGS', 'https://graph.org/file/4e358b9a735492726a887.png')
    IMAGE_WEL = environ.get('IMAGE_WEL', 'https://graph.org/file/d053d5ca7fa71913aa575.png')
    IMAGE_WIBU = environ.get('IMAGE_WIBU', 'https://graph.org/file/f0247d41171f08fe60288.png')
    IMAGE_YT = environ.get('IMAGE_YT', 'https://graph.org/file/3755f52bc43d7e0ce061b.png')
    IMAGE_ZIP = environ.get('IMAGE_ZIP', 'https://telegra.ph/file/4a1a17589798bc405b9c9.png')
#======================================================================


#=========================== ACCOUNTS =================================
    # Mega
    MEGA_KEY = environ.get('MEGA_KEY', '')
    MEGA_USERNAME = environ.get('MEGA_USERNAME', '')
    MEGA_PASSWORD = environ.get('MEGA_PASSWORD', '')
    MEGA_STATUS = environ.get('MEGA_STATUS', '~')
    # Uptobox
    UPTOBOX_TOKEN = environ.get('UPTOBOX_TOKEN', '')
    UPTOBOX_STATUS = environ.get('UPTOBOX_STATUS', '~')
    # GDTot
    CRYPT_GDTOT = environ.get('CRYPT_GDTOT', '')
    # SharerPw
    SHARERPW_LARAVEL_SESSION = environ.get('SHARERPW_LARAVEL_SESSION', '')
    SHARERPW_XSRF_TOKEN = environ.get('SHARERPW_XSRF_TOKEN', '')
#======================================================================


#=========================== UPSTREAM =================================
    UPSTREAM_REPO = environ.get('UPSTREAM_REPO', '')
    UPSTREAM_BRANCH = environ.get('UPSTREAM_BRANCH', 'master')
    UPDATE_EVERYTHING =  environ.get('UPDATE_EVERYTHING', 'False').lower() == 'true'
#======================================================================


#============================== UI ====================================
    AUTHOR_NAME = environ.get('AUTHOR_NAME', 'Anonim')
    AUTHOR_URL = environ.get('AUTHOR_URL', 'https://t.me/TrollUser')
    DRIVE_SEARCH_TITLE = environ.get('DRIVE_SEARCH_TITLE', 'Drive Search')
    GD_INFO = environ.get('GD_INFO', 'Uploaded by Telegram Mirror Bot')
    PROG_FINISH = environ.get('PROG_FINISH', '⬢')
    PROG_UNFINISH = environ.get('PROG_UNFINISH', '⬡')
    SOURCE_LINK_TITLE = environ.get('SOURCE_LINK_TITLE', 'Source Link')
    TIME_ZONE = environ.get('TIME_ZONE', 'Asia/Jakarta')
    TIME_ZONE_TITLE = environ.get('TIME_ZONE_TITLE', 'UTC+7')
    TSEARCH_TITLE = environ.get('TSEARCH_TITLE', 'Torrent Search')
#======================================================================


#=========================== BUTTONS =================================
    SOURCE_LINK = environ.get('SOURCE_LINK', 'False').lower() == 'true'
    VIEW_LINK = environ.get('VIEW_LINK', 'False').lower() == 'true'
    BUTTON_FIVE_NAME = environ.get('BUTTON_FIVE_NAME', '')
    BUTTON_FIVE_URL = environ.get('BUTTON_FIVE_URL', '')
    BUTTON_FOUR_NAME = environ.get('BUTTON_FOUR_NAME', '')
    BUTTON_FOUR_URL = environ.get('BUTTON_FOUR_URL', '')
    BUTTON_SIX_NAME = environ.get('BUTTON_SIX_NAME', '')
    BUTTON_SIX_URL = environ.get('BUTTON_SIX_URL', '')
#======================================================================


#=========================== QBITTORRENT ==============================
    BASE_URL = environ.get('BASE_URL', '').rstrip('/')
    PORT = environ.get('PORT')
    await (await create_subprocess_exec('pkill', '-9', '-f', 'gunicorn')).wait()
    if BASE_URL:
        await create_subprocess_shell(f'gunicorn web.wserver:app --bind 0.0.0.0:{PORT} --worker-class gevent')

    WEB_PINCODE = environ.get('WEB_PINCODE', 'False').lower() == 'true'
#======================================================================


#=============================== RSS ==================================
    RSS_CHAT_ID = environ.get('RSS_CHAT_ID', '')
    RSS_CHAT_ID =  int(RSS_CHAT_ID) if RSS_CHAT_ID else ''

    RSS_DELAY = environ.get('RSS_DELAY', '')
    RSS_DELAY = int(RSS_DELAY) if RSS_DELAY else 900
#======================================================================


#============================ TORSEARCH ===============================
    SEARCH_LIMIT = int(environ.get('SEARCH_LIMIT', 20))
    SEARCH_API_LINK = environ.get('SEARCH_API_LINK', '').rstrip('/')
    SEARCH_PLUGINS = environ.get('SEARCH_PLUGINS', '')
#======================================================================


#============================= HEROKU =================================
    HEROKU_API_KEY = environ.get('HEROKU_API_KEY', '')
    HEROKU_APP_NAME = environ.get('HEROKU_APP_NAME', '')
#======================================================================

    DRIVES_IDS.clear()
    DRIVES_NAMES.clear()
    INDEX_URLS.clear()

    if GDRIVE_ID:
        DRIVES_NAMES.append('Main')
        DRIVES_IDS.append(GDRIVE_ID)
        INDEX_URLS.append(INDEX_URL)

    if await aiopath.exists('list_drives.txt'):
        async with aiopen('list_drives.txt', 'r+') as f:
            lines = await f.readlines()
            for line in lines:
                temp = line.strip().split()
                DRIVES_IDS.append(temp[1])
                DRIVES_NAMES.append(temp[0].replace('_', ' '))
                if len(temp) > 2:
                    INDEX_URLS.append(temp[2])
                else:
                    INDEX_URLS.append('')

    SHORTENERES.clear()
    SHORTENER_APIS.clear()
    if await aiopath.exists('shorteners.txt'):
        with open('shorteners.txt', 'r+') as f:
            lines = f.readlines()
            for line in lines:
                temp = line.strip().split()
                if len(temp) == 2:
                    SHORTENERES.append(temp[0])
                    SHORTENER_APIS.append(temp[1])

    if await aiopath.exists('multi_list.txt'):
        if GDRIVE_ID:
            drive_dict['Default'] = ['Default', GDRIVE_ID, INDEX_URL]
        async with aiopen('multi_list.txt', 'r') as f:
            lines = await f.readlines()
        for x in lines:
            x = x.strip().split()
            index = x[2].rstrip('/') if len(x) > 2 else ''
            drive_dict[x[0]] = [x[0], x[1], index]
            DRIVES_IDS.append(x[1])
            DRIVES_NAMES.append(x[0])
            INDEX_URLS.append(index)
    else:
        MULTI_GDID = False

    config_dict.update({'BOT_TOKEN': BOT_TOKEN,
                        'TELEGRAM_API': TELEGRAM_API,
                        'TELEGRAM_HASH': TELEGRAM_HASH,
                        'OWNER_ID': OWNER_ID,
                        'DATABASE_URL': DATABASE_URL,
                        'DEFAULT_UPLOAD': DEFAULT_UPLOAD,
                        'DOWNLOAD_DIR': DOWNLOAD_DIR,
                        'GDRIVE_ID': GDRIVE_ID,
                        # OPTIONALS
                        'DISABLE_MIRROR_LEECH': DISABLE_MIRROR_LEECH,
                        'AUTHORIZED_CHATS': AUTHORIZED_CHATS,
                        'SUDO_USERS': SUDO_USERS,
                        'EXTENSION_FILTER': EXTENSION_FILTER,
                        'GCLONE_URL': GCLONE_URL,
                        'INDEX_URL': INDEX_URL,
                        'TORRENT_TIMEOUT': TORRENT_TIMEOUT,
                        'INCOMPLETE_TASK_NOTIFIER': INCOMPLETE_TASK_NOTIFIER,
                        'USE_SERVICE_ACCOUNTS': USE_SERVICE_ACCOUNTS,
                        'CMD_SUFFIX': CMD_SUFFIX,
                        'STOP_DUPLICATE': STOP_DUPLICATE,
                        'IS_TEAM_DRIVE': IS_TEAM_DRIVE,
                        'MULTI_TIMEGAP': MULTI_TIMEGAP,
                        'AS_DOCUMENT': AS_DOCUMENT,
                        'SAVE_MESSAGE': SAVE_MESSAGE,
                        'LEECH_FILENAME_PREFIX': LEECH_FILENAME_PREFIX,
                        'USER_SESSION_STRING': USER_SESSION_STRING,
                        'SAVE_SESSION_STRING': SAVE_SESSION_STRING,
                        'USERBOT_LEECH': USERBOT_LEECH,
                        'AUTO_DELETE_MESSAGE_DURATION': AUTO_DELETE_MESSAGE_DURATION,
                        'AUTO_DELETE_UPLOAD_MESSAGE_DURATION': AUTO_DELETE_UPLOAD_MESSAGE_DURATION,
                        'STATUS_UPDATE_INTERVAL': STATUS_UPDATE_INTERVAL,
                        'YT_DLP_OPTIONS': YT_DLP_OPTIONS,
                        'AUTO_THUMBNAIL': AUTO_THUMBNAIL,
                        'PREMIUM_MODE': PREMIUM_MODE,
                        'DAILY_MODE': DAILY_MODE,
                        'MULTI_GDID': MULTI_GDID,
                        'MEDIA_GROUP': MEDIA_GROUP,
                        'QUEUE_ALL': QUEUE_ALL,
                        'QUEUE_DOWNLOAD': QUEUE_DOWNLOAD,
                        'QUEUE_UPLOAD': QUEUE_UPLOAD,
                        'QUEUE_COMPLETE': QUEUE_COMPLETE,
                        # RCLONE
                        'RCLONE_FLAGS': RCLONE_FLAGS,
                        'RCLONE_PATH': RCLONE_PATH,
                        'RCLONE_SERVE_URL': RCLONE_SERVE_URL,
                        'RCLONE_SERVE_PORT': RCLONE_SERVE_PORT,
                        'RCLONE_SERVE_USER': RCLONE_SERVE_USER,
                        'RCLONE_SERVE_PASS': RCLONE_SERVE_PASS,
                        # LOGS
                        'ONCOMPLETE_LEECH_LOG': ONCOMPLETE_LEECH_LOG,
                        'LEECH_LOG': LEECH_LOG,
                        'MIRROR_LOG': MIRROR_LOG,
                        'OTHER_LOG': OTHER_LOG,
                        'LINK_LOG': LINK_LOG,
                        # LIMITS
                        'EQUAL_SPLITS': EQUAL_SPLITS,
                        'DAILY_LIMIT_SIZE': DAILY_LIMIT_SIZE,
                        'CLONE_LIMIT': CLONE_LIMIT,
                        'LEECH_LIMIT': LEECH_LIMIT,
                        'LEECH_SPLIT_SIZE': LEECH_SPLIT_SIZE,
                        'MEGA_LIMIT': MEGA_LIMIT,
                        'NONPREMIUM_LIMIT': NONPREMIUM_LIMIT,
                        'STATUS_LIMIT': STATUS_LIMIT,
                        'TORRENT_DIRECT_LIMIT': TORRENT_DIRECT_LIMIT,
                        'TOTAL_TASKS_LIMIT': TOTAL_TASKS_LIMIT,
                        'USER_TASKS_LIMIT': USER_TASKS_LIMIT,
                        'ZIP_UNZIP_LIMIT': ZIP_UNZIP_LIMIT,
                        'STORAGE_THRESHOLD': STORAGE_THRESHOLD,
                        'YTDL_LIMIT': YTDL_LIMIT,
                        'MAX_YTPLAYLIST': MAX_YTPLAYLIST,
                        # GOFILE
                        'GOFILE': GOFILE,
                        'GOFILETOKEN': GOFILETOKEN,
                        'GOFILEBASEFOLDER': GOFILEBASEFOLDER,
                        # FMODE
                        'AUTO_MUTE': AUTO_MUTE,
                        'MUTE_CHAT_ID': MUTE_CHAT_ID,
                        'AUTO_MUTE_DURATION': AUTO_MUTE_DURATION,
                        'FUSERNAME': FUSERNAME,
                        'FSUB': FSUB,
                        'FSUB_CHANNEL_ID': FSUB_CHANNEL_ID,
                        'FSUB_BUTTON_NAME': FSUB_BUTTON_NAME,
                        'CHANNEL_USERNAME': CHANNEL_USERNAME,
                        # STICKERS
                        'STICKERID_COUNT': STICKERID_COUNT,
                        'STICKERID_ERROR': STICKERID_ERROR,
                        'STICKERID_LEECH': STICKERID_LEECH,
                        'STICKERID_MIRROR': STICKERID_MIRROR,
                        'STICKER_DELETE_DURATION': STICKER_DELETE_DURATION,
                        # IMAGES
                        'ENABLE_IMAGE_MODE': ENABLE_IMAGE_MODE,
                        'IMAGE_ARIA': IMAGE_ARIA,
                        'IMAGE_AUTH': IMAGE_AUTH,
                        'IMAGE_BOLD': IMAGE_BOLD,
                        'IMAGE_BYE': IMAGE_BYE,
                        'IMAGE_CANCEL': IMAGE_CANCEL,
                        'IMAGE_CAPTION': IMAGE_CAPTION,
                        'IMAGE_COMPLETE': IMAGE_COMPLETE,
                        'IMAGE_CONEDIT': IMAGE_CONEDIT,
                        'IMAGE_CONPRIVATE': IMAGE_CONPRIVATE,
                        'IMAGE_CONSET': IMAGE_CONSET,
                        'IMAGE_CONVIEW': IMAGE_CONVIEW,
                        'IMAGE_DUMID': IMAGE_DUMID,
                        'IMAGE_FSUB': IMAGE_FSUB,
                        'IMAGE_GD': IMAGE_GD,
                        'IMAGE_HELP': IMAGE_HELP,
                        'IMAGE_HTML': IMAGE_HTML,
                        'IMAGE_IMDB': IMAGE_IMDB,
                        'IMAGE_INFO': IMAGE_INFO,
                        'IMAGE_ITALIC': IMAGE_ITALIC,
                        'IMAGE_LIMIT': IMAGE_LIMIT,
                        'IMAGE_LOGS': IMAGE_LOGS,
                        'IMAGE_MEDINFO': IMAGE_MEDINFO,
                        'IMAGE_MONO': IMAGE_MONO,
                        'IMAGE_NORMAL': IMAGE_NORMAL,
                        'IMAGE_OWNER': IMAGE_OWNER,
                        'IMAGE_PAUSE': IMAGE_PAUSE,
                        'IMAGE_PM': IMAGE_PM,
                        'IMAGE_PRENAME': IMAGE_PRENAME,
                        'IMAGE_QBIT': IMAGE_QBIT,
                        'IMAGE_RCLONE': IMAGE_RCLONE,
                        'IMAGE_REMNAME': IMAGE_REMNAME,
                        'IMAGE_RSS': IMAGE_RSS,
                        'IMAGE_SEARCH': IMAGE_SEARCH,
                        'IMAGE_STATS': IMAGE_STATS,
                        'IMAGE_STATUS': IMAGE_STATUS,
                        'IMAGE_SUFNAME': IMAGE_SUFNAME,
                        'IMAGE_TXT': IMAGE_TXT,
                        'IMAGE_UNAUTH': IMAGE_UNAUTH,
                        'IMAGE_UNKNOW': IMAGE_UNKNOW,
                        'IMAGE_USER': IMAGE_USER,
                        'IMAGE_USETIINGS': IMAGE_USETIINGS,
                        'IMAGE_WEL': IMAGE_WEL,
                        'IMAGE_WIBU': IMAGE_WIBU,
                        'IMAGE_YT': IMAGE_YT,
                        'IMAGE_ZIP': IMAGE_ZIP,
                        # ACCOUNTS
                        'MEGA_KEY': MEGA_KEY,
                        'MEGA_USERNAME': MEGA_USERNAME,
                        'MEGA_PASSWORD': MEGA_PASSWORD,
                        'MEGA_STATUS': MEGA_STATUS,
                        'UPTOBOX_TOKEN': UPTOBOX_TOKEN,
                        'UPTOBOX_STATUS': UPTOBOX_STATUS,
                        'CRYPT_GDTOT': CRYPT_GDTOT,
                        'SHARERPW_LARAVEL_SESSION': SHARERPW_LARAVEL_SESSION,
                        'SHARERPW_XSRF_TOKEN': SHARERPW_XSRF_TOKEN,
                        # UPSTREAM
                        'UPSTREAM_REPO': UPSTREAM_REPO,
                        'UPSTREAM_BRANCH': UPSTREAM_BRANCH,
                        'UPDATE_EVERYTHING': UPDATE_EVERYTHING,
                        # UI
                        'AUTHOR_NAME': AUTHOR_NAME,
                        'AUTHOR_URL': AUTHOR_URL,
                        'DRIVE_SEARCH_TITLE': DRIVE_SEARCH_TITLE,
                        'GD_INFO': GD_INFO,
                        'PROG_FINISH': PROG_FINISH ,
                        'PROG_UNFINISH': PROG_UNFINISH ,
                        'SOURCE_LINK_TITLE': SOURCE_LINK_TITLE,
                        'TIME_ZONE': TIME_ZONE,
                        'TIME_ZONE_TITLE': TIME_ZONE_TITLE,
                        'TSEARCH_TITLE': TSEARCH_TITLE,
                        # BUTTONS
                        'SOURCE_LINK': SOURCE_LINK,
                        'VIEW_LINK': VIEW_LINK,
                        'BUTTON_FIVE_NAME': BUTTON_FIVE_NAME,
                        'BUTTON_FIVE_URL': BUTTON_FIVE_URL,
                        'BUTTON_FOUR_NAME': BUTTON_FOUR_NAME,
                        'BUTTON_FOUR_URL': BUTTON_FOUR_URL,
                        'BUTTON_SIX_NAME': BUTTON_SIX_NAME,
                        'BUTTON_SIX_URL': BUTTON_SIX_URL,
                        # QBITTORRENT
                        'BASE_URL': BASE_URL,
                        'WEB_PINCODE': WEB_PINCODE,
                        # RSS
                        'RSS_CHAT_ID': RSS_CHAT_ID,
                        'RSS_DELAY': RSS_DELAY,
                        # TORSEARCH
                        'SEARCH_API_LINK': SEARCH_API_LINK,
                        'SEARCH_PLUGINS': SEARCH_PLUGINS,
                        'SEARCH_LIMIT': SEARCH_LIMIT,
                        # HEROKU
                        'HEROKU_API_KEY': HEROKU_API_KEY,
                        'HEROKU_APP_NAME': HEROKU_APP_NAME})
    LOGGER.info('Config loaded!')
    if DATABASE_URL:
        await DbManger().update_config(config_dict)
        LOGGER.info('Config update in database!!')
    await intialize_userbot()
    await initiate_search_tools()
    await start_from_queued()
    await rclone_serve_booter()


async def intialize_userbot(check=True):
    if check:
        userbot: Client = bot_dict['USERBOT']
        if userbot and userbot.is_connected:
            await userbot.stop()
            LOGGER.info('Userbot stopped.')
    bot_dict.update({'IS_PREMIUM': False, 'USERBOT': None, 'MAX_SPLIT_SIZE': DEFAULT_SPLIT_SIZE})
    if USER_SESSION_STRING:= config_dict['USER_SESSION_STRING']:
        try:
            userbot = await Client('user', config_dict['TELEGRAM_API'],
                                   config_dict['TELEGRAM_HASH'],
                                   session_string=USER_SESSION_STRING,
                                   no_updates=True, **kwargs).start()
            bot_dict['IS_PREMIUM'] = userbot.me.is_premium
            if bot_dict['IS_PREMIUM']:
                bot_dict['USERBOT'] = userbot
                LOGGER.info(f'Premium detected, 4GB leech enabled.')
                if not config_dict['LEECH_LOG']:
                    LOGGER.warning('Premium Leech required Leech Log!')
                bot_dict['MAX_SPLIT_SIZE'] = 4194304000
            else:
                await userbot.stop()
                LOGGER.info('Not detected premium from session string, using default client!')
        except Exception as e:
            LOGGER.error(e)
    LEECH_SPLIT_SIZE, MAX_SPLIT_SIZE = config_dict['LEECH_SPLIT_SIZE'], bot_dict['MAX_SPLIT_SIZE']
    if not LEECH_SPLIT_SIZE or LEECH_SPLIT_SIZE > MAX_SPLIT_SIZE or LEECH_SPLIT_SIZE == DEFAULT_SPLIT_SIZE:
        config_dict['LEECH_SPLIT_SIZE'] = MAX_SPLIT_SIZE
        if config_dict['DATABASE_URL']:
            await DbManger().update_config({'LEECH_SPLIT_SIZE': MAX_SPLIT_SIZE})
    LOGGER.info(f'Leech Split Size: {config_dict["LEECH_SPLIT_SIZE"]}.')


async def intialize_savebot(session_string=None, check=True, user_id=None):
    if session_string == config_dict['USER_SESSION_STRING'] and (userbot:= bot_dict.get('USERBOT')):
        bot_dict['SAVEBOT'] = userbot
        return
    elif user_id and session_string == user_data.get(user_id, {}).get('user_string', '') and (savebot:= bot_dict.get(user_id, {}).get('SAVEBOT')):
        bot_dict.setdefault(user_id, {})
        bot_dict[user_id]['SAVEBOT'] = savebot
        return
    if check:
        savebot: Client = bot_dict.get(user_id, {}).get('SAVEBOT') if user_id else bot_dict['SAVEBOT']
        if savebot and savebot.is_connected:
            await savebot.stop()
            LOGGER.info('Savebot stopped.')
    if user_id:
        bot_dict.setdefault(user_id, {})
        bot_dict[user_id]['SAVEBOT'] = None
    else:
        bot_dict['SAVEBOT'] = None
    if session_string:
        try:
            savebot = await Client(str(user_id) if user_id else 'savebot',
                                   config_dict['TELEGRAM_API'],
                                   config_dict['TELEGRAM_HASH'],
                                   session_string=session_string,
                                   no_updates=True, **kwargs).start()
            if user_id:
                bot_dict[user_id]['SAVEBOT'] = savebot
            else:
                bot_dict['SAVEBOT'] = savebot
            LOGGER.info('Save content mode enabled!')
        except Exception as e:
            LOGGER.error(e)