from aiofiles.os import path as aiopath
from asyncio import sleep
from html import escape
from megasdkrestclient import MegaSdkRestClient, constants
from pathlib import Path

from bot import download_dict, download_dict_lock, non_queued_dl, queue_dict_lock, config_dict, LOGGER
from bot.helper.ext_utils.bot_utils import get_readable_file_size, is_premium_user, sync_to_async, new_task
from bot.helper.ext_utils.fs_utils import check_storage_threshold
from bot.helper.ext_utils.task_manager import stop_duplicate_check, is_queued
from bot.helper.mirror_utils.status_utils.mega_download_status import MegaDownloadStatus
from bot.helper.mirror_utils.status_utils.queue_status import QueueStatus
from bot.helper.telegram_helper.message_utils import sendMessage, sendStatusMessage


class MegaDownloader:

    def __init__(self, listener):
        self.__listener = listener
        self.__name = ''
        self.__mega_client = MegaSdkRestClient('http://localhost:6090')
        self.__periodic = False
        self.__downloaded_bytes = 0
        self.__progress = 0
        self.__gid = None

    @property
    def progress(self):
        return self.__progress

    @property
    def downloaded_bytes(self):
        return self.__downloaded_bytes

    @property
    def speed(self):
        if self.__gid:
            return self.__mega_client.getDownloadInfo(self.__gid)['speed']

    @new_task
    async def __setInterval(self, func):
        while self.__periodic:
            await sleep(3)
            await func()

    async def __onDownloadStart(self, name, size, gid, from_queue):
        self.__name = name
        self.__gid = gid
        self.__setInterval(self.__onInterval)
        self.__periodic = True
        async with download_dict_lock:
            download_dict[self.__listener.uid] = MegaDownloadStatus(name, size, gid, self, self.__listener)
        async with queue_dict_lock:
            non_queued_dl.add(self.__listener.uid)
        if not from_queue:
            await self.__listener.onDownloadStart()
            await sendStatusMessage(self.__listener.message)
            LOGGER.info(f'Download from Mega: {self.__name}')
        else:
            LOGGER.info(f'Start Queued Download from Mega: {self.__name}')

    async def __onInterval(self):
        dlInfo = await sync_to_async(self.__mega_client.getDownloadInfo, self.__gid)
        state = dlInfo['state']
        if state in [constants.State.TYPE_STATE_COMPLETED, constants.State.TYPE_STATE_CANCELED, constants.State.TYPE_STATE_FAILED] and self.__periodic:
            self.__periodic = False
        if state == constants.State.TYPE_STATE_COMPLETED:
            await self.__listener.onDownloadComplete()
        elif state == constants.State.TYPE_STATE_CANCELED:
            await self.__onDownloadError('Download stopped by user!', ename=self.__name)
        elif state == constants.State.TYPE_STATE_FAILED:
            await self.__onDownloadError(dlInfo['error_string'], ename=self.__name)
        else:
            await self.__onDownloadProgress(dlInfo['completed_length'], dlInfo['total_length'])

    async def __onDownloadProgress(self, current, total):
        self.__downloaded_bytes = current
        try:
            self.__progress = current / total * 100
        except ZeroDivisionError:
            self.__progress = 0

    async def __onDownloadError(self, error, listfile=None, ename=None):
        await self.__listener.onDownloadError(error, listfile, ename)

    async def add_download(self, link: str, path: str):
        await sync_to_async(Path(path).mkdir, parents=True, exist_ok=True)
        try:
            dl = await sync_to_async(self.__mega_client.addDl, link, path)
        except Exception as err:
            LOGGER.error(err)
            await sendMessage(escape(str(err)), self.__listener.message)
            return
        gid = dl['gid']
        info = await sync_to_async(self.__mega_client.getDownloadInfo, gid)
        file_name, file_size = info['name'], info['total_length']
        file, sname = await stop_duplicate_check(file_name, self.__listener)
        if file:
            LOGGER.info('File/folder already in Drive!')
            await self.__onDownloadError('File/folder already in Drive!', file, sname)
            return
        msgerr = None
        megadl, zuzdl, leechdl, storage = config_dict['MEGA_LIMIT'], config_dict['ZIP_UNZIP_LIMIT'], config_dict['LEECH_LIMIT'], config_dict['STORAGE_THRESHOLD']
        if config_dict['PREMIUM_MODE'] and not is_premium_user(self.__listener.user_id):
            mdl = zuzdl = leechdl = config_dict['NONPREMIUM_LIMIT']
            if mdl < megadl:
                megadl = mdl
        if megadl and file_size >= megadl * 1024**3:
            msgerr = f'Mega limit is {megadl}GB'
        if not msgerr:
            if zuzdl and any([self.__listener.isZip, self.__listener.extract]) and file_size >= zuzdl * 1024**3:
                msgerr = f'Zip/Unzip limit is {zuzdl}GB'
            elif leechdl and self.__listener.isLeech and file_size >= leechdl * 1024**3:
                msgerr = f'Leech limit is {leechdl}GB'
        if storage and not await check_storage_threshold(file_size, any([self.__listener.isZip, self.__listener.isLeech, self.__listener.extract])):
            msgerr = f'Need {storage}GB free storage'
        if msgerr:
            LOGGER.info('File/folder size over the limit size!')
            await self.__onDownloadError(f'{msgerr}. File/folder size is {get_readable_file_size(file_size)}.', ename=file_name)
            return

        added_to_queue, event = await is_queued(self.__listener.uid)
        if added_to_queue:
            LOGGER.info(f"Added to Queue/Download: {file_name}")
            async with download_dict_lock:
                download_dict[self.__listener.uid] = QueueStatus(file_name, file_size, gid, self.__listener, 'dl')
            await self.__listener.onDownloadStart()
            await sendStatusMessage(self.__listener.message)
            await event.wait()
            async with download_dict_lock:
                if self.__listener.uid not in download_dict:
                    return
            from_queue = True
        else:
            from_queue = False

        await self.__onDownloadStart(file_name, file_size, gid, from_queue)

    async def cancel_download(self):
        LOGGER.info(f'Cancelling download on user request: {self.__gid}')
        await sync_to_async(self.__mega_client.cancelDl, self.__gid)