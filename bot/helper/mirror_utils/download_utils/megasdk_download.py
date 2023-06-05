from aiofiles.os import makedirs
from asyncio import Event
from mega import (MegaApi, MegaListener, MegaRequest, MegaTransfer, MegaError)
from random import SystemRandom
from string import ascii_letters, digits

from bot import config_dict, download_dict_lock, download_dict, non_queued_dl, queue_dict_lock, LOGGER
from bot.helper.ext_utils.bot_utils import get_mega_link_type, async_to_sync, sync_to_async, is_premium_user, get_readable_file_size, new_task
from bot.helper.ext_utils.fs_utils import check_storage_threshold
from bot.helper.ext_utils.task_manager import is_queued, stop_duplicate_check
from bot.helper.mirror_utils.status_utils.mega_download_status import MegaDownloadStatus
from bot.helper.mirror_utils.status_utils.queue_status import QueueStatus
from bot.helper.telegram_helper.message_utils import sendMessage, sendStatusMessage


class MegaAppListener(MegaListener):
    _NO_EVENT_ON = (MegaRequest.TYPE_LOGIN, MegaRequest.TYPE_FETCH_NODES)
    NO_ERROR = 'no error'

    def __init__(self, continue_event: Event, listener):
        self.continue_event = continue_event
        self.node = None
        self.public_node = None
        self.listener = listener
        self.is_cancelled = False
        self.error = None
        self.is_rename = ''
        self.__name = ''
        self.__bytes_transferred = 0
        self.__speed = 0
        super().__init__()

    @property
    def speed(self):
        return self.__speed

    @property
    def downloaded_bytes(self):
        return self.__bytes_transferred

    def onRequestFinish(self, api, request, error):
        if str(error).lower() != 'no error':
            self.error = error.copy()
            LOGGER.error(f'Mega onRequestFinishError: {self.error}')
            self.continue_event.set()
            return
        request_type = request.getType()
        if request_type == MegaRequest.TYPE_LOGIN:
            api.fetchNodes()
        elif request_type == MegaRequest.TYPE_GET_PUBLIC_NODE:
            self.public_node = request.getPublicMegaNode()
            self.__name = self.public_node.getName()
        elif request_type == MegaRequest.TYPE_FETCH_NODES:
            LOGGER.info('Fetching Root Node.')
            self.node = api.getRootNode()
            self.__name = self.node.getName()
            LOGGER.info(f'Node Name: {self.__name}')
        if request_type not in self._NO_EVENT_ON or self.node and 'cloud drive' not in self.__name.lower():
            self.continue_event.set()

    def onRequestTemporaryError(self, api, request, error: MegaError):
        LOGGER.error(f'Mega Request error in {error}')
        if not self.is_cancelled:
            self.is_cancelled = True
            async_to_sync(self.listener.onDownloadError, f'RequestTempError: {error.toString()}', ename=self.__name)
        self.error = error.toString()
        self.continue_event.set()

    def onTransferUpdate(self, api: MegaApi, transfer: MegaTransfer):
        if self.is_cancelled:
            api.cancelTransfer(transfer, None)
            self.continue_event.set()
            return
        self.__speed = transfer.getSpeed()
        self.__bytes_transferred = transfer.getTransferredBytes()

    def onTransferFinish(self, api: MegaApi, transfer: MegaTransfer, error):
        try:
            if self.is_cancelled:
                self.continue_event.set()
            elif transfer.isFinished() and (transfer.isFolderTransfer() or transfer.getFileName() == self.__name or self.is_rename):
                async_to_sync(self.listener.onDownloadComplete)
                self.continue_event.set()
        except Exception as e:
            LOGGER.error(e)

    def onTransferTemporaryError(self, api, transfer, error):
        state = transfer.getState()
        errStr = error.toString()
        LOGGER.error(f'Mega download error in file {transfer} {transfer.getFileName()}: {error}')
        if state in [1, 4] and not 'over quota' in errStr.lower():
            # Sometimes MEGA (offical client) can't stream a node either and raises a temp failed error.
            # Don't break the transfer queue if transfer's in queued (1) or retrying (4) state [causes seg fault]
            return

        self.error = errStr
        if not self.is_cancelled:
            self.is_cancelled = True
            async_to_sync(self.listener.onDownloadError, f'TransferTempError: {errStr}.', ename=self.__name)
            self.continue_event.set()

    async def cancel_download(self):
        self.is_cancelled = True
        await self.listener.onDownloadError('Download Canceled by user!', ename=self.__name)


class AsyncExecutor:
    def __init__(self):
        self.continue_event = Event()

    async def do(self, function, args):
        self.continue_event.clear()
        await sync_to_async(function, *args)
        await self.continue_event.wait()


@new_task
async def add_mega_download(mega_link, path, listener, name):
    AUTHOR_NAME = config_dict['AUTHOR_NAME']
    MEGA_USERNAME, MEGA_PASSWORD = config_dict['MEGA_USERNAME'], config_dict['MEGA_PASSWORD']
    executor = AsyncExecutor()
    folder_api = None
    api = MegaApi(None, None, None, AUTHOR_NAME)
    mega_listener = MegaAppListener(executor.continue_event, listener)
    api.addListener(mega_listener)
    if MEGA_USERNAME and MEGA_PASSWORD:
        LOGGER.info('================= Trying to Login ====================')
        await executor.do(api.login, (MEGA_USERNAME, MEGA_PASSWORD))
        LOGGER.info('=============== Sucessfully Login ====================')
    mega_listener.is_rename = name
    mega_listener.type = get_mega_link_type(mega_link)
    if mega_listener.type == 'file':
        await executor.do(api.getPublicNode, (mega_link,))
        node = mega_listener.public_node
    else:
        folder_api = MegaApi(None, None, None, 'MLTB')
        folder_api.addListener(mega_listener)
        await executor.do(folder_api.loginToFolder, (mega_link,))
        node = await sync_to_async(folder_api.authorizeNode, mega_listener.node)
    if mega_listener.error:
        if not mega_listener.is_cancelled:
            await sendMessage(str(mega_listener.error), listener.message)
        await executor.do(api.logout, ())
        if folder_api:
            await executor.do(folder_api.logout, ())
        return
    name = name or node.getName()
    megadl, zuzdl, leechdl, storage = config_dict['MEGA_LIMIT'], config_dict['ZIP_UNZIP_LIMIT'], config_dict['LEECH_LIMIT'], config_dict['STORAGE_THRESHOLD']
    file, sname = await stop_duplicate_check(name, listener, mega_listener.type)
    if file:
        LOGGER.info("File/folder already in Drive!")
        await listener.onDownloadError('File/folder already in Drive!', file, sname)
        await executor.do(api.logout, ())
        if folder_api:
            await executor.do(folder_api.logout, ())
        return
    gid = ''.join(SystemRandom().choices(ascii_letters + digits, k=8))
    size = api.getSize(node)
    msgerr = None
    megadl, zuzdl, leechdl, storage = config_dict['MEGA_LIMIT'], config_dict['ZIP_UNZIP_LIMIT'], config_dict['LEECH_LIMIT'], config_dict['STORAGE_THRESHOLD']
    if config_dict['PREMIUM_MODE'] and not is_premium_user(listener.user_id):
        mdl = zuzdl = leechdl = config_dict['NONPREMIUM_LIMIT']
        if mdl < megadl:
            megadl = mdl
    if megadl and size >= megadl * 1024**3:
        msgerr = f'Mega limit is {megadl}GB'
    if not msgerr:
        if zuzdl and any([listener.isZip, listener.extract]) and size >= zuzdl * 1024**3:
            msgerr = f'Zip/Unzip limit is {zuzdl}GB'
        elif leechdl and listener.isLeech and size >= leechdl * 1024**3:
            msgerr = f'Leech limit is {leechdl}GB'
    if storage and not await check_storage_threshold(size, any([listener.isZip, listener.isLeech, listener.extract])):
        msgerr = f'Need {storage}GB free storage'
    if msgerr:
        LOGGER.info('File/folder size over the limit size!')
        await listener.onDownloadError(f'{msgerr}. File/folder size is {get_readable_file_size(size)}.', ename=name)
        if folder_api:
            await sync_to_async(folder_api.removeListener, mega_listener)
        return
    added_to_queue, event = await is_queued(listener.uid)
    if added_to_queue:
        LOGGER.info(f"Added to Queue/Download: {name}")
        async with download_dict_lock:
            download_dict[listener.uid] = QueueStatus(name, size, gid, listener, 'dl')
        await listener.onDownloadStart()
        await sendStatusMessage(listener.message)
        await event.wait()
        async with download_dict_lock:
            if listener.uid not in download_dict:
                await executor.do(api.logout, ())
                if folder_api:
                    await executor.do(folder_api.logout, ())
                return
        from_queue = True
        LOGGER.info(f'Start Queued Download from Mega: {name}')
    else:
        from_queue = False
    async with download_dict_lock:
        download_dict[listener.uid] = MegaDownloadStatus(name, size, gid, mega_listener, listener)
    async with queue_dict_lock:
        non_queued_dl.add(listener.uid)
    if from_queue:
        LOGGER.info(f'Start Queued Download from Mega: {name}')
    else:
        await listener.onDownloadStart()
        await sendStatusMessage(listener.message)
        LOGGER.info(f'Download from Mega: {name}')
    await makedirs(path, exist_ok=True)
    await executor.do(api.startDownload, (node, path, name, None, False, None))
    await executor.do(api.logout, ())
    if folder_api:
        await executor.do(folder_api.logout, ())
