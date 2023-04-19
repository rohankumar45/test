from logging import getLogger
from os import path as ospath, listdir
from random import SystemRandom
from re import search as re_search
from string import ascii_letters, digits
from yt_dlp import YoutubeDL, DownloadError

from bot import download_dict_lock, download_dict, non_queued_dl, queue_dict_lock, config_dict
from bot.helper.ext_utils.bot_utils import get_readable_file_size, is_premium_user, sync_to_async, async_to_sync
from bot.helper.ext_utils.fs_utils import check_storage_threshold
from bot.helper.ext_utils.task_manager import is_queued, stop_duplicate_check
from bot.helper.mirror_utils.status_utils.queue_status import QueueStatus
from bot.helper.mirror_utils.status_utils.yt_dlp_download_status import YtDlpDownloadStatus
from bot.helper.telegram_helper.message_utils import sendStatusMessage

LOGGER = getLogger(__name__)


class MyLogger:
    def __init__(self, obj):
        self.obj = obj

    def debug(self, msg):
        # Hack to fix changing extension
        if not self.obj.is_playlist:
            if match := re_search(r'.Merger..Merging formats into..(.*?).$', msg) or \
                        re_search(r'.ExtractAudio..Destination..(.*?)$', msg):
                LOGGER.info(msg)
                newname = match.group(1)
                newname = newname.rsplit('/', 1)[-1]
                self.obj.name = newname

    @staticmethod
    def warning(msg):
        LOGGER.warning(msg)

    @staticmethod
    def error(msg):
        if msg != 'ERROR: Cancelling...':
            LOGGER.error(msg)


class YoutubeDLHelper:
    def __init__(self, listener):
        self.__last_downloaded = 0
        self.__size = 0
        self.__progress = 0
        self.__downloaded_bytes = 0
        self.__download_speed = 0
        self.__eta = '~'
        self.__gid = ''
        self.__ext = ''
        self.__listener = listener
        self.__is_cancelled = False
        self.__downloading = False
        self.name = ''
        self.is_playlist = False
        self.playlist_index = 0
        self.playlist_count = 0
        self.opts = {'progress_hooks': [self.__onDownloadProgress],
                     'logger': MyLogger(self),
                     'usenetrc': True,
                     'cookiefile': 'cookies.txt',
                     'allow_multiple_video_streams': True,
                     'allow_multiple_audio_streams': True,
                     'noprogress': True,
                     'allow_playlist_files': True,
                     'overwrites': True,
                     'writethumbnail': True,
                     'trim_file_name': 220}

    @property
    def download_speed(self):
        return self.__download_speed

    @property
    def downloaded_bytes(self):
        return self.__downloaded_bytes

    @property
    def size(self):
        return self.__size

    @property
    def progress(self):
        return self.__progress

    @property
    def eta(self):
        return self.__eta

    def __onDownloadProgress(self, d):
        self.__downloading = True
        if self.__is_cancelled:
            raise ValueError('Cancelling...')
        if d['status'] == 'finished':
            if self.is_playlist:
                self.__last_downloaded = 0
        elif d['status'] == 'downloading':
            self.__download_speed = d['speed']
            if self.is_playlist:
                downloadedBytes = d['downloaded_bytes']
                chunk_size = downloadedBytes - self.__last_downloaded
                self.__last_downloaded = downloadedBytes
                self.__downloaded_bytes += chunk_size
                try:
                    self.playlist_index = d['info_dict']['playlist_index']
                except:
                    pass
            else:
                if d.get('total_bytes'):
                    self.__size = d['total_bytes']
                elif d.get('total_bytes_estimate'):
                    self.__size = d['total_bytes_estimate']
                self.__downloaded_bytes = d['downloaded_bytes']
                self.__eta = d.get('eta', '~')
            try:
                self.__progress = (self.__downloaded_bytes / self.__size) * 100
            except:
                pass

    async def __onDownloadStart(self, from_queue=False):
        async with download_dict_lock:
            download_dict[self.__listener.uid] = YtDlpDownloadStatus(self, self.__listener, self.__gid)
        if not from_queue:
            await self.__listener.onDownloadStart()
            await sendStatusMessage(self.__listener.message)

    def __onDownloadError(self, error, listfile=None, ename=None):
        self.__is_cancelled = True
        async_to_sync(self.__listener.onDownloadError, error, listfile, ename)

    def extractMetaData(self, link, name):
        if link.startswith(('rtmp', 'mms', 'rstp', 'rtmps')):
            self.opts['external_downloader'] = 'ffmpeg'
        with YoutubeDL(self.opts) as ydl:
            try:
                result = ydl.extract_info(link, download=False)
                if result is None:
                    raise ValueError('Info result is None')
            except Exception as e:
                self.__onDownloadError(str(e))
                return
            if self.is_playlist:
                self.playlist_count = result.get('playlist_count', 0)
            if 'entries' in result:
                self.name = name
                for entry in result['entries']:
                    if not entry:
                        continue
                    elif 'filesize_approx' in entry:
                        self.__size += entry['filesize_approx']
                    elif 'filesize' in entry:
                        self.__size += entry['filesize']
                    if not name:
                        outtmpl_ = '%(series,playlist_title,channel)s%(season_number& |)s%(season_number&S|)s%(season_number|)02d.%(ext)s'
                        name, ext = ospath.splitext(ydl.prepare_filename(entry, outtmpl=outtmpl_))
                        self.name = name
                        if not self.__ext:
                            self.__ext = ext
            else:
                outtmpl_ = '%(title,fulltitle,alt_title)s%(season_number& |)s%(season_number&S|)s%(season_number|)02d%(episode_number&E|)s%(episode_number|)02d%(height& |)s%(height|)s%(height&p|)s%(fps|)s%(fps&fps|)s%(tbr& |)s%(tbr|)d.%(ext)s'
                realName = ydl.prepare_filename(result, outtmpl=outtmpl_)
                ext = ospath.splitext(realName)[-1]
                self.name = f"{name}{ext}" if name else realName
                if not self.__ext:
                    self.__ext = ext
                if result.get('filesize'):
                    self.__size = result['filesize']
                elif result.get('filesize_approx'):
                    self.__size = result['filesize_approx']

    def __download(self, link, path):
        try:
            with YoutubeDL(self.opts) as ydl:
                try:
                    ydl.download([link])
                except DownloadError as e:
                    if not self.__is_cancelled:
                        self.__onDownloadError(str(e))
                    return
            if self.is_playlist and (not ospath.exists(path) or len(listdir(path)) == 0):
                self.__onDownloadError('No video available to download from this playlist. Check logs for more details')
                return
            if self.__is_cancelled:
                raise ValueError
            try:
                async_to_sync(self.__listener.onDownloadComplete)
            except Exception as e:
                self.__onDownloadError(str(e))
                return
        except ValueError:
            self.__onDownloadError('Stopped by user!', ename=self.name)

    async def add_download(self, link, path, name, qual, playlist, options):
        if playlist:
            self.opts['ignoreerrors'] = True
            self.is_playlist = True
        self.__gid = ''.join(SystemRandom().choices(ascii_letters + digits, k=10))
        await self.__onDownloadStart()
        self.opts['postprocessors'] = [{'add_chapters': True, 'add_infojson': 'if_exists', 'add_metadata': True, 'key': 'FFmpegMetadata'}]
        if qual.startswith('ba/b-'):
            mp3_info = qual.split('-')
            qual = mp3_info[0]
            rate = mp3_info[1]
            self.opts['postprocessors'].append({'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': rate})
            self.__ext = '.mp3'
        self.opts['format'] = qual
        if options:
            self.__set_options(options)
        await sync_to_async(self.extractMetaData, link, name)
        if self.__is_cancelled:
            return
        if self.is_playlist:
            self.opts['outtmpl'] = {'default': f"{path}/{self.name}/%(title,fulltitle,alt_title)s%(season_number& |)s%(season_number&S|)s%(season_number|)02d%(episode_number&E|)s%(episode_number|)02d%(height& |)s%(height|)s%(height&p|)s%(fps|)s%(fps&fps|)s%(tbr& |)s%(tbr|)d.%(ext)s",
                                    'thumbnail': f"{path}/yt-dlp-thumb/%(title,fulltitle,alt_title)s%(season_number& |)s%(season_number&S|)s%(season_number|)02d%(episode_number&E|)s%(episode_number|)02d%(height& |)s%(height|)s%(height&p|)s%(fps|)s%(fps&fps|)s%(tbr& |)s%(tbr|)d.%(ext)s"}
        elif not options:
            self.opts['outtmpl'] = {'default': f"{path}/{self.name}",
                                    'thumbnail': f"{path}/yt-dlp-thumb/%(title,fulltitle,alt_title)s%(season_number& |)s%(season_number&S|)s%(season_number|)02d%(episode_number&E|)s%(episode_number|)02d%(height& |)s%(height|)s%(height&p|)s%(fps|)s%(fps&fps|)s%(tbr& |)s%(tbr|)d.%(ext)s"}
        else:
            pure_name = ospath.splitext(self.name)[0]
            self.opts['outtmpl'] = {'default': f"{path}/{pure_name}/%(title,fulltitle,alt_title)s%(season_number& |)s%(season_number&S|)s%(season_number|)02d%(episode_number&E|)s%(episode_number|)02d%(height& |)s%(height|)s%(height&p|)s%(fps|)s%(fps&fps|)s%(tbr& |)s%(tbr|)d.%(ext)s",
                                    'thumbnail': f"{path}/yt-dlp-thumb/%(title,fulltitle,alt_title)s%(season_number& |)s%(season_number&S|)s%(season_number|)02d%(episode_number&E|)s%(episode_number|)02d%(height& |)s%(height|)s%(height&p|)s%(fps|)s%(fps&fps|)s%(tbr& |)s%(tbr|)d.%(ext)s"}
            self.name = pure_name

        if self.__listener.isLeech:
            self.opts['postprocessors'].append({'format': 'jpg', 'key': 'FFmpegThumbnailsConvertor', 'when': 'before_dl'})
        if self.__ext in ['.mp3', '.mkv', '.mka', '.ogg', '.opus', '.flac', '.m4a', '.mp4', '.mov']:
            self.opts['postprocessors'].append({'already_have_thumbnail': self.__listener.isLeech, 'key': 'EmbedThumbnail'})
        elif not self.__listener.isLeech:
            self.opts['writethumbnail'] = False

        file, sname = await stop_duplicate_check(self.name, self.__listener)
        if file:
            LOGGER.info('File/folder already in Drive!')
            self.__is_cancelled = True
            await self.__listener.onDownloadError(f'{sname} already in Drive!', file, sname)
            return
        msgerr = None
        arch = any([self.__listener.isZip, self.__listener.isLeech])
        ytdl, zuzdl, leechdl, storage, max_pyt = config_dict['YTDL_LIMIT'], config_dict['ZIP_UNZIP_LIMIT'], config_dict['LEECH_LIMIT'], config_dict['STORAGE_THRESHOLD'], config_dict['MAX_YTPLAYLIST']
        if config_dict['PREMIUM_MODE'] and not is_premium_user(self.__listener.user_id):
            ytdl = zuzdl = leechdl = config_dict['NONPREMIUM_LIMIT']
            max_pyt = 10
        if ytdl and not arch and self.__size >= ytdl * 1024**3:
            msgerr = f"Ytdl {'playlist' if self.is_playlist else 'video'} limit is {ytdl}GB"
        elif zuzdl and self.__listener.isZip and self.__size >= zuzdl * 1024**3:
            msgerr = f'Ytdlzip limit is {zuzdl}GB'
        elif leechdl and self.__listener.isLeech and self.__size >= leechdl * 1024**3:
            msgerr = f'Ytdl leech limit is {leechdl}GB'
        if max_pyt and self.is_playlist and (self.playlist_count > max_pyt):
            msgerr = f'Only {max_pyt} playlist allowed. {self.name} playlist is {self.playlist_count}.'
        if storage and not await check_storage_threshold(self.__size, arch):
            msgerr = f'Need {storage}GB free storage'
        if msgerr:
            if 'Only' not in msgerr:
                LOGGER.info('File/folder size over the limit size!')
                msgerr += f'. {self.name} size is {get_readable_file_size(self.__size)}.'
            self.__is_cancelled = True
            await self.__listener.onDownloadError(msgerr, ename=self.name)
            return
        added_to_queue, event = await is_queued(self.__listener.uid)
        if added_to_queue:
            LOGGER.info(f"Added to Queue/Download: {self.name}")
            async with download_dict_lock:
                download_dict[self.__listener.uid] = QueueStatus(self.name, self.__size, self.__gid, self.__listener, 'dl')
            await event.wait()
            async with download_dict_lock:
                if self.__listener.uid not in download_dict:
                    return
            LOGGER.info(f'Start Queued Download with YT_DLP: {self.name}')
            await self.__onDownloadStart(True)
        else:
            LOGGER.info(f'Download with YT_DLP: {self.name}')
        async with queue_dict_lock:
            non_queued_dl.add(self.__listener.uid)
        await sync_to_async(self.__download, link, path)

    async def cancel_download(self):
        self.__is_cancelled = True
        LOGGER.info(f'Cancelling Download: {self.name}')
        if not self.__downloading:
            await self.__listener.onDownloadError('Download Cancelled by User!', ename=self.name)

    def __set_options(self, options):
        options = options.split('|')
        for opt in options:
            kv = opt.split(':', 1)
            key = kv[0].strip()
            if key == 'format':
                continue
            value = kv[1].strip()
            if value.startswith('^'):
                value = float(value.split('^')[1])
            elif value.lower() == 'true':
                value = True
            elif value.lower() == 'false':
                value = False
            elif value.startswith(('{', '[', '(')) and value.endswith(('}', ']', ')')):
                value = eval(value)

            if key == 'postprocessors':
                if isinstance(value, list):
                    values = tuple(value)
                    self.opts[key].extend(values)
                elif isinstance(value, dict):
                    self.opts[key].append(value)
            else:
                self.opts[key] = value