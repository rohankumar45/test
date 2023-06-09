from asyncio import sleep
from time import time

from bot import bot_loop, download_dict, download_dict_lock, QbInterval, config_dict, QbTorrents, qb_listener_lock, get_client, LOGGER
from bot.helper.ext_utils.bot_utils import get_readable_file_size, get_readable_time, getDownloadByGid, sync_to_async, is_premium_user, new_task
from bot.helper.ext_utils.fs_utils import check_storage_threshold, clean_unwanted
from bot.helper.ext_utils.task_manager import stop_duplicate_check
from bot.helper.mirror_utils.status_utils.qbit_status import QbittorrentStatus
from bot.helper.telegram_helper.message_utils import update_all_messages


async def __remove_torrent(client, hash_, tag):
    await sync_to_async(client.torrents_delete, torrent_hashes=hash_, delete_files=True)
    async with qb_listener_lock:
        if tag in QbTorrents:
            del QbTorrents[tag]
    await sync_to_async(client.torrents_delete_tags, tags=tag)


@new_task
async def __onDownloadError(err, tor, listfile=None, ename=None):
    LOGGER.info(f'Cancelling Download: {tor.name}')
    ext_hash = tor.hash
    download = await getDownloadByGid(ext_hash[:12])
    if hasattr(download, 'client'):
        listener = download.listener()
        client = download.client()
        await listener.onDownloadError(err, listfile, ename)
        await sleep(0.3)
        await __remove_torrent(client, ext_hash, tor.tags)


@new_task
async def __onSeedFinish(tor):
    ext_hash = tor.hash
    LOGGER.info(f'Cancelling Seed: {tor.name}')
    download = await getDownloadByGid(ext_hash[:12])
    if hasattr(download, 'client'):
        listener = download.listener()
        client = download.client()
        await listener.onUploadError(f'Seeding stopped with Ratio {round(tor.ratio, 3)} ({get_readable_time(tor.seeding_time)})', tor.name)
        await __remove_torrent(client, ext_hash, tor.tags)


@new_task
async def __stop_duplicate(tor):
    download = await getDownloadByGid(tor.hash[:12])
    if hasattr(download, 'listener'):
        listener = download.listener()
        name = tor.content_path.rsplit('/', 1)[-1].rsplit('.!qB', 1)[0]
        file, sname = await stop_duplicate_check(name, listener)
        if file:
            LOGGER.info('File/folder already in Drive!')
            __onDownloadError('File/folder already available in Drive.', tor, file, sname)


@new_task
async def __download_limits(tor, limits):
    download = await getDownloadByGid(tor.hash[:12])
    if hasattr(download, 'listener'):
        listener = download.listener()
        msgerr = None
        torddl, zuzdl, leechdl, storage = limits
        compress, extract = listener.compress is not None, listener.extract is not None
        arch = any([compress, listener.isLeech, extract])
        if config_dict['PREMIUM_MODE'] and not is_premium_user(listener.user_id):
            torddl = zuzdl = leechdl = config_dict['NONPREMIUM_LIMIT']
        if torddl and not arch and tor.size >= torddl * 1024**3:
            msgerr = f'Torrent/direct limit is {torddl}GB'
        elif zuzdl and any([compress, extract]) and tor.size >= zuzdl * 1024**3:
            msgerr = f'Zip/Unzip limit is {zuzdl}GB'
        elif leechdl and listener.isLeech and tor.size >= leechdl * 1024**3:
            msgerr = f'Leech limit is {leechdl}GB'
        if storage and not await check_storage_threshold(tor.size, arch):
            msgerr = f'You must leave {storage}GB free storage'
        if msgerr:
            LOGGER.info('File/folder size over the limit size!')
            __onDownloadError(f'{msgerr}. File/folder size is {get_readable_file_size(tor.size)}.', tor, None, tor.name)


@new_task
async def __onDownloadComplete(tor):
    ext_hash = tor.hash
    tag = tor.tags
    await sleep(2)
    download = await getDownloadByGid(ext_hash[:12])
    if hasattr(download, 'client'):
        listener = download.listener()
        client = download.client()
        if not listener.seed:
            await sync_to_async(client.torrents_pause, torrent_hashes=ext_hash)
        if listener.select:
            await clean_unwanted(listener.dir)
        await listener.onDownloadComplete()
        client = await sync_to_async(get_client)
        if listener.seed:
            async with download_dict_lock:
                if listener.uid in download_dict:
                    removed = False
                    download_dict[listener.uid] = QbittorrentStatus(listener, True)
                else:
                    removed = True
            if removed:
                await __remove_torrent(client, ext_hash, tag)
                return
            async with qb_listener_lock:
                if tag in QbTorrents:
                    QbTorrents[tag]['seeding'] = True
                else:
                    return
            await update_all_messages()
            LOGGER.info(f'Seeding started: {tor.name} - Hash: {ext_hash}')
            await sync_to_async(client.auth_log_out)
        else:
            await __remove_torrent(client, ext_hash, tag)


async def __qb_listener():
    client = await sync_to_async(get_client)
    while True:
        async with qb_listener_lock:
            try:
                if len(await sync_to_async(client.torrents_info)) == 0:
                    QbInterval.clear()
                    await sync_to_async(client.auth_log_out)
                    return
                for tor_info in await sync_to_async(client.torrents_info):
                    TORRENT_TIMEOUT = config_dict['TORRENT_TIMEOUT']
                    tag = tor_info.tags
                    if tag not in QbTorrents:
                        continue
                    state = tor_info.state
                    if state == 'metaDL':
                        QbTorrents[tag]['stalled_time'] = time()
                        if TORRENT_TIMEOUT and time() - tor_info.added_on >= TORRENT_TIMEOUT:
                            __onDownloadError('Dead torrent!', tor_info, ename=tor_info.name)
                        else:
                            await sync_to_async(client.torrents_reannounce, torrent_hashes=tor_info.hash)
                    elif state == 'downloading':
                        QbTorrents[tag]['stalled_time'] = time()
                        limits = [config_dict['TORRENT_DIRECT_LIMIT'], config_dict['ZIP_UNZIP_LIMIT'], config_dict['LEECH_LIMIT'], config_dict['STORAGE_THRESHOLD']]
                        if any(limits) and tor_info.hash:
                            __download_limits(tor_info, limits)
                        if config_dict['STOP_DUPLICATE'] and not QbTorrents[tag]['stop_dup_check']:
                            QbTorrents[tag]['stop_dup_check'] = True
                            __stop_duplicate(tor_info)
                    elif state == 'stalledDL':
                        if not QbTorrents[tag]['rechecked'] and 0.99989999999999999 < tor_info.progress < 1:
                            msg = f'Force recheck - Name: {tor_info.name} Hash: '
                            msg += f'{tor_info.hash} Downloaded Bytes: {tor_info.downloaded} '
                            msg += f'Size: {tor_info.size} Total Size: {tor_info.total_size}'
                            LOGGER.warning(msg)
                            await sync_to_async(client.torrents_recheck, torrent_hashes=tor_info.hash)
                            QbTorrents[tag]['rechecked'] = True
                        elif TORRENT_TIMEOUT and time() - QbTorrents[tag]['stalled_time'] >= TORRENT_TIMEOUT:
                            __onDownloadError('Dead torrent!', tor_info, ename=tor_info.name)
                        else:
                            await sync_to_async(client.torrents_reannounce, torrent_hashes=tor_info.hash)
                    elif state == 'missingFiles':
                        await sync_to_async(client.torrents_recheck, torrent_hashes=tor_info.hash)
                    elif state == 'error':
                        __onDownloadError('No enough space for this torrent on device', tor_info, ename=tor_info.name)
                    elif tor_info.completion_on != 0 and not QbTorrents[tag]['uploaded'] and state not in ['checkingUP', 'checkingDL', 'checkingResumeData']:
                        QbTorrents[tag]['uploaded'] = True
                        __onDownloadComplete(tor_info)
                    elif state in ['pausedUP', 'pausedDL'] and QbTorrents[tag]['seeding']:
                        QbTorrents[tag]['seeding'] = False
                        __onSeedFinish(tor_info)
            except Exception as e:
                LOGGER.error(e)
                client = await sync_to_async(get_client)
        await sleep(3)


async def onDownloadStart(tag):
    async with qb_listener_lock:
        QbTorrents[tag] = {'stalled_time': time(), 'stop_dup_check': False, 'rechecked': False, 'uploaded': False, 'seeding': False}
        if not QbInterval:
            periodic = bot_loop.create_task(__qb_listener())
            QbInterval.append(periodic)