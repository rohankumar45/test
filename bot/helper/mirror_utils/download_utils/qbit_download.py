from aiofiles.os import path as aiopath
from time import time


from bot import download_dict, download_dict_lock, config_dict, non_queued_dl, queue_dict_lock, get_client, LOGGER
from bot.helper.ext_utils.bot_utils import bt_selection_buttons, sync_to_async
from bot.helper.ext_utils.fs_utils import clean_target
from bot.helper.ext_utils.task_manager import is_queued
from bot.helper.listeners.qbit_listener import onDownloadStart
from bot.helper.mirror_utils.status_utils.qbit_status import QbittorrentStatus
from bot.helper.telegram_helper.message_utils import sendMessage, deleteMessage, sendStatusMessage, sendingMessage


async def add_qb_torrent(link, path, listener, ratio, seed_time):
    client = await sync_to_async(get_client)
    ADD_TIME = time()
    try:
        url = link
        tpath = None
        if await aiopath.exists(link):
            url = None
            tpath = link
        added_to_queue, event = await is_queued(listener.uid)
        op = await sync_to_async(client.torrents_add, url, tpath, path, is_paused=added_to_queue, tags=f'{listener.uid}',
                                 ratio_limit=ratio, seeding_time_limit=seed_time, headers={'user-agent': 'Wget/1.12'})
        if op.lower() == 'ok.':
            tor_info = await sync_to_async(client.torrents_info, tag=f'{listener.uid}')
            if len(tor_info) == 0:
                while True:
                    tor_info = await sync_to_async(client.torrents_info, tag=f'{listener.uid}')
                    if len(tor_info) > 0:
                        break
                    elif time() - ADD_TIME >= 120:
                        msg = 'Not added! Check if the link is valid or not. If it\'s torrent file then report, this happens if torrent file size above 10mb.'
                        await sendMessage(msg, listener.message)
                        return
            tor_info = tor_info[0]
            ext_hash = tor_info.hash
        else:
            await sendMessage('This Torrent already added or unsupported/invalid link/file.', listener.message)
            return
        async with download_dict_lock:
            download_dict[listener.uid] = QbittorrentStatus(listener, queued=added_to_queue)
        await onDownloadStart(f'{listener.uid}')
        if added_to_queue:
            LOGGER.info(f'Added to Queue/Download: {tor_info.name} - Hash: {ext_hash}')
        else:
            async with queue_dict_lock:
                non_queued_dl.add(listener.uid)
            LOGGER.info(f'QbitDownload started: {tor_info.name} - Hash: {ext_hash}')
        await listener.onDownloadStart()
        LOGGER.info(f'QbitDownload started: {tor_info.name} - Hash: {ext_hash}')
        if config_dict['BASE_URL'] and listener.select:
            if link.startswith('magnet:'):
                metamsg = '<i>Downloading <b>Metadata</b>, please wait...</i>'
                meta = await sendMessage(metamsg, listener.message)
                while True:
                    tor_info = await sync_to_async(client.torrents_info, tag=f'{listener.uid}')
                    if len(tor_info) == 0:
                        await deleteMessage(meta)
                        return
                    try:
                        tor_info = tor_info[0]
                        if tor_info.state not in ['metaDL', 'checkingResumeData', 'pausedDL']:
                            await deleteMessage(meta)
                            break
                    except:
                        await deleteMessage(meta)
                        return
            ext_hash = tor_info.hash
            if not added_to_queue:
                await sync_to_async(client.torrents_pause, torrent_hashes=ext_hash)
            SBUTTONS = bt_selection_buttons(ext_hash)
            msg = f'<code>{tor_info.name}</code>\n\n{listener.tag}, your download paused. Choose files then press <b>Done Selecting</b> button to start downloading.'
            await sendingMessage(msg, listener.message, config_dict['IMAGE_PAUSE'], SBUTTONS)
        else:
            await sendStatusMessage(listener.message)
        if added_to_queue:
            await event.wait()
            async with download_dict_lock:
                if listener.uid not in download_dict:
                    return
                download_dict[listener.uid].queued = False
            await sync_to_async(client.torrents_resume, torrent_hashes=ext_hash)
            LOGGER.info(f'Start Queued Download from Qbittorrent: {tor_info.name} - Hash: {ext_hash}')
            async with queue_dict_lock:
                non_queued_dl.add(listener.uid)
    except Exception as e:
        await sendMessage(str(e), listener.message)
    finally:
        await clean_target(link)