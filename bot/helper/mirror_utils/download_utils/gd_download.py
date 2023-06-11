from aiofiles.os import path as aiopath
from random import SystemRandom
from string import ascii_letters, digits

from bot import download_dict, download_dict_lock, config_dict, non_queued_dl, queue_dict_lock, LOGGER
from bot.helper.ext_utils.bot_utils import get_readable_file_size, is_premium_user, sync_to_async
from bot.helper.ext_utils.fs_utils import check_storage_threshold
from bot.helper.ext_utils.task_manager import is_queued, stop_duplicate_check
from bot.helper.mirror_utils.status_utils.gdrive_status import GdriveStatus
from bot.helper.mirror_utils.status_utils.queue_status import QueueStatus
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.message_utils import sendMessage, sendStatusMessage


async def add_gd_download(link, path, listener, newname, gdrive_sharer):
    drive = GoogleDriveHelper()
    name, mime_type, size, _, _ = await sync_to_async(drive.count, link)
    if not mime_type:
        await sendMessage(name, listener.message)
        return
    name = newname or name
    file, sname = await stop_duplicate_check(name, listener)
    if file:
        LOGGER.info('File/folder already in Drive!')
        await listener.onDownloadError('File/folder already in Drive!', file, sname)
        return
    msgerr = None
    torddl, zuzdl, leechdl, storage = config_dict['TORRENT_DIRECT_LIMIT'], config_dict['ZIP_UNZIP_LIMIT'], config_dict['LEECH_LIMIT'], config_dict['STORAGE_THRESHOLD']
    if config_dict['PREMIUM_MODE'] and not is_premium_user(listener.user_id):
        torddl = zuzdl = leechdl = config_dict['NONPREMIUM_LIMIT']
    arch = any([listener.compress, listener.isLeech, listener.extract])
    if torddl and not arch and size >= torddl * 1024**3:
        msgerr = f'Torrent/direct limit is {torddl}GB'
    elif zuzdl and any([listener.compress, listener.extract]) and size >= zuzdl * 1024**3:
        msgerr = f'Zip/Unzip limit is {zuzdl}GB'
    elif leechdl and listener.isLeech and size >= leechdl * 1024**3:
        msgerr = f'Leech limit is {leechdl}GB'
    if storage and not await check_storage_threshold(size, arch):
        msgerr = f'Need {storage}GB free storage'
    if msgerr:
        LOGGER.info('File/folder size over the limit size!')
        await listener.onDownloadError(f'{msgerr}. File/folder size is {get_readable_file_size(size)}.', ename=name)
        return
    gid = ''.join(SystemRandom().choices(ascii_letters + digits, k=12))
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
                return
        from_queue = True
    else:
        from_queue = False
    drive = GoogleDriveHelper(name, path, listener)
    async with download_dict_lock:
        download_dict[listener.uid] = GdriveStatus(drive, size, listener, gid, 'dl')
    async with queue_dict_lock:
        non_queued_dl.add(listener.uid)
    if from_queue:
        LOGGER.info(f'Start Queued Download from GDrive: {name}')
    else:
        LOGGER.info(f'Download from GDrive: {name}')
        await listener.onDownloadStart()
        await sendStatusMessage(listener.message)
    await sync_to_async(drive.download, link)
    if gdrive_sharer:
        msg = await sync_to_async(drive.deletefile, link)
        LOGGER.info(f'{msg} (Sharer Link): {link}')
