from asyncio import gather
from json import loads
from random import SystemRandom
from string import ascii_letters, digits

from bot import config_dict, download_dict, download_dict_lock, queue_dict_lock, non_queued_dl, LOGGER
from bot.helper.ext_utils.bot_utils import cmd_exec, is_premium_user, get_readable_file_size
from bot.helper.ext_utils.fs_utils import check_storage_threshold
from bot.helper.ext_utils.task_manager import is_queued, stop_duplicate_check
from bot.helper.mirror_utils.rclone_utils.transfer import RcloneTransferHelper
from bot.helper.mirror_utils.status_utils.queue_status import QueueStatus
from bot.helper.mirror_utils.status_utils.rclone_status import RcloneStatus
from bot.helper.telegram_helper.message_utils import sendStatusMessage


async def add_rclone_download(rc_path, config_path, path, name, listener):
    cmd1 = ['./gclone', 'lsjson', '--fast-list', '--stat', '--no-mimetype', '--no-modtime', '--config', config_path, rc_path]
    cmd2 = ['./gclone', 'size', '--fast-list', '--json', '--config', config_path, rc_path]
    res1, res2 = await gather(cmd_exec(cmd1), cmd_exec(cmd2))
    if res1[2] or res2[2]:
        if res1[2] != -9:
            msg = f'Error: While getting rclone stat/size. Path: {rc_path}. Stderr: {res1[1] or res2[1]}'
            await listener.onDownloadError(msg, ename=name)
        return
    remote, rc_path = rc_path.split(':', 1)
    rc_path = rc_path.strip('/')
    rstat, rsize = loads(res1[0]), loads(res2[0])
    if rstat['IsDir']:
        if not name:
            name = rc_path.rsplit('/', 1)[-1] if rc_path else remote
        path += name
    else:
        name = rc_path.rsplit('/', 1)[-1]
    size = rsize['bytes']
    gid = ''.join(SystemRandom().choices(ascii_letters + digits, k=12))
    file, sname = await stop_duplicate_check(name, listener)
    if file:
        LOGGER.info('File/folder already in Drive!')
        await listener.onDownloadError('File/folder already in Drive!', file, sname)
        return
    torddl, zuzdl, leechdl, storage = config_dict['TORRENT_DIRECT_LIMIT'], config_dict['ZIP_UNZIP_LIMIT'], config_dict['LEECH_LIMIT'], config_dict['STORAGE_THRESHOLD']
    if any([torddl, zuzdl, leechdl, storage]):
        msgerr = None
        arch = any([listener.isZip, listener.isLeech, listener.extract])
        if config_dict['PREMIUM_MODE'] and not is_premium_user(listener.user_id):
            torddl = zuzdl = leechdl = config_dict['NONPREMIUM_LIMIT']
        if torddl and not arch and size >= torddl * 1024**3:
            msgerr = f'Torrent/direct limit is {torddl}GB'
        elif zuzdl and any([listener.isZip, listener.extract]) and size >= zuzdl * 1024**3:
            msgerr = f'Zip/Unzip limit is {zuzdl}GB'
        elif leechdl and listener.isLeech and size >= leechdl * 1024**3:
            msgerr = f'Leech limit is {leechdl}GB'
        if storage and not await check_storage_threshold(size, arch, True):
            msgerr = f'Need {storage}GB free storage'
        if msgerr:
            LOGGER.info('File/folder size over the limit size!')
            await listener.onDownloadError(f'{msgerr}. File/folder size is {get_readable_file_size(size)}.', ename=name)
            return
    added_to_queue, event = await is_queued(listener.uid)
    if added_to_queue:
        LOGGER.info(f"Added to Queue/Download: {name}")
        async with download_dict_lock:
            download_dict[listener.uid] = QueueStatus(
                name, size, gid, listener, 'dl')
        await listener.onDownloadStart()
        await sendStatusMessage(listener.message)
        await event.wait()
        async with download_dict_lock:
            if listener.uid not in download_dict:
                return
        from_queue = True
    else:
        from_queue = False

    RCTransfer = RcloneTransferHelper(listener, name)
    async with download_dict_lock:
        download_dict[listener.uid] = RcloneStatus(RCTransfer, listener, gid, 'dl')
    async with queue_dict_lock:
        non_queued_dl.add(listener.uid)

    if from_queue:
        LOGGER.info(f'Start Queued Download with rclone: {rc_path}')
    else:
        await listener.onDownloadStart()
        await sendStatusMessage(listener.message)
        LOGGER.info(f"Download with rclone: {rc_path}")

    await RCTransfer.download(remote, rc_path, config_path, path)
