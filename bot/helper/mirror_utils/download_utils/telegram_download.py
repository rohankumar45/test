from asyncio import Lock
from logging import getLogger, ERROR
from pyrogram import Client
from time import time

from bot import bot, download_dict, download_dict_lock, non_queued_dl, queue_dict_lock, config_dict, LOGGER
from bot.helper.ext_utils.bot_utils import get_readable_file_size, is_media
from bot.helper.ext_utils.fs_utils import check_storage_threshold
from bot.helper.ext_utils.task_manager import is_queued, stop_duplicate_check
from bot.helper.mirror_utils.status_utils.queue_status import QueueStatus
from bot.helper.mirror_utils.status_utils.telegram_status import TelegramStatus
from bot.helper.telegram_helper.message_utils import sendStatusMessage


global_lock = Lock()
GLOBAL_GID = set()
getLogger('pyrogram').setLevel(ERROR)


class TelegramDownloadHelper:

    def __init__(self, listener):
        self.name = ''
        self.__processed_bytes = 0
        self.__start_time = time()
        self.__listener = listener
        self.__id = ''
        self.__is_cancelled = False
        self.__client: Client = bot

    @property
    def speed(self):
        return self.__processed_bytes / (time() - self.__start_time)

    @property
    def processed_bytes(self):
        return self.__processed_bytes

    async def __onDownloadStart(self, name, size, file_id, from_queue):
        async with global_lock:
            GLOBAL_GID.add(file_id)
        self.name = name
        self.size = size
        self.__id = file_id
        async with download_dict_lock:
            download_dict[self.__listener.uid] = TelegramStatus(self, self.__listener, size, file_id[:12], 'dl')
        async with queue_dict_lock:
            non_queued_dl.add(self.__listener.uid)
        if not from_queue:
            await self.__listener.onDownloadStart()
            await sendStatusMessage(self.__listener.message)
            LOGGER.info(f'Download from Telegram: {name}')
        else:
            LOGGER.info(f'Start Queued Download from Telegram: {name}')

    async def __onDownloadProgress(self, current, total):
        if self.__is_cancelled:
            self.__client.stop_transmission()
            return
        self.__processed_bytes = current

    async def __onDownloadError(self, error, listfile=None,  ename=None):
        async with global_lock:
            try:
                GLOBAL_GID.remove(self.__id)
            except:
                pass
        await self.__listener.onDownloadError(error, listfile, ename)

    async def __onDownloadComplete(self):
        await self.__listener.onDownloadComplete()
        async with global_lock:
            GLOBAL_GID.remove(self.__id)

    async def __download(self, message, path):
        try:
            if self.__client != bot:
                download = await self.__client.download_media(message, file_name=path, progress=self.__onDownloadProgress)
            else:
                download = await message.download(file_name=path, progress=self.__onDownloadProgress)
            if self.__is_cancelled:
                await self.__onDownloadError('Cancelled by user!', ename=self.name)
                return
        except Exception as e:
            LOGGER.error(str(e))
            self.__onDownloadError(str(e))
            return
        if download:
            await self.__onDownloadComplete()
        elif not self.__is_cancelled:
            await self.__onDownloadError('Internal error occurred')

    async def add_download(self, message, path, filename, tg_client: Client=None):
        if tg_client and tg_client != bot:
            self.__client = tg_client
        if media:= is_media(message):
            async with global_lock:
                # For avoiding locking the thread lock for long time unnecessarily
                download = media.file_unique_id not in GLOBAL_GID
            if download:
                if filename == '':
                    name = media.file_name if hasattr(media, 'file_name') else 'None'
                else:
                    name = filename
                    path = path + name
                size = media.file_size
                gid = media.file_unique_id
                if (storage := config_dict['STORAGE_THRESHOLD']) and not \
                    await check_storage_threshold(size, any([self.__listener.isZip, self.__listener.isLeech, self.__listener.extract])):
                    await self.__onDownloadError(f'Need {storage}GB free storage. File size is {get_readable_file_size(size)}', ename=name)
                    return
                file, sname = await stop_duplicate_check(name, self.__listener)
                if file:
                    LOGGER.info('File/folder already in Drive!')
                    await self.__onDownloadError('File already in Drive!', file, sname)
                    return
                added_to_queue, event = await is_queued(self.__listener.uid)
                if added_to_queue:
                    LOGGER.info(f"Added to Queue/Download: {name}")
                    async with download_dict_lock:
                        download_dict[self.__listener.uid] = QueueStatus(name, size, gid, self.__listener, 'dl')
                    await self.__listener.onDownloadStart()
                    await sendStatusMessage(self.__listener.message)
                    await event.wait()
                    async with download_dict_lock:
                        if self.__listener.uid not in download_dict:
                            return
                    from_queue = True
                else:
                    from_queue = False
                await self.__onDownloadStart(name, size, media.file_unique_id, from_queue)
                LOGGER.info(f'Downloading Telegram file with id: {media.file_unique_id}')
                await self.__download(message, path)
            else:
                await self.__onDownloadError('File already being downloaded!')
        else:
            await self.__onDownloadError('No document from given link!' if tg_client else 'No document in the replied message')

    async def cancel_download(self):
        self.__is_cancelled = True
        LOGGER.info(f'Cancelling download on user request: name: {self.name} id: {self.__id}')
