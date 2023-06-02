from aiofiles.os import path as aiopath
from asyncio import gather
from asyncio import sleep
from time import time

from bot import aria2, download_dict_lock, download_dict, config_dict, LOGGER
from bot.helper.ext_utils.bot_utils import getDownloadByGid, get_readable_file_size, bt_selection_buttons, is_premium_user, new_thread, sync_to_async
from bot.helper.ext_utils.fs_utils import check_storage_threshold, clean_unwanted, clean_target
from bot.helper.mirror_utils.status_utils.aria_status import Aria2Status
from bot.helper.telegram_helper.message_utils import sendMessage, deleteMessage, update_all_messages, sendingMessage
from bot.helper.ext_utils.task_manager import stop_duplicate_check


@new_thread
async def __onDownloadStarted(api, gid):
    download = await sync_to_async(api.get_download, gid)
    if download.is_metadata:
        LOGGER.info(f'onDownloadStarted: {gid} METADATA')
        await sleep(1)
        if dl := await getDownloadByGid(gid):
            listener = dl.listener()
            if listener.select:
                metamsg = '<i>Downloading <b>Metadata</b>, please wait...</i>'
                meta = await sendMessage(metamsg, listener.message)
                while True:
                    await sleep(0.5)
                    if download.is_removed or download.followed_by_ids:
                        await deleteMessage(meta)
                        break
                    download = download.live
        return
    else:
        LOGGER.info(f'onDownloadStarted: {download.name} - Gid: {gid}')
    dl = None
    if config_dict['STOP_DUPLICATE']:
        await sleep(1)
        if dl:= await getDownloadByGid(gid):
            listener = dl.listener()
            if not listener.select and not listener.user_dict.get('cus_gdrive') and listener.upPath == 'gd':
                download = await sync_to_async(api.get_download, gid)
                if not download.is_torrent:
                    await sleep(3)
                    download = download.live
                file, sname = await stop_duplicate_check(download.name, listener)
                if file:
                    LOGGER.info('File/folder already in Drive!')
                    await listener.onDownloadError('File/folder already in Drive!', file, sname)
                    await sync_to_async(api.remove, [download], force=True, files=True)
                    return
    torddl, zuzdl, leechdl, storage = config_dict['TORRENT_DIRECT_LIMIT'], config_dict['ZIP_UNZIP_LIMIT'], config_dict['LEECH_LIMIT'], config_dict['STORAGE_THRESHOLD']
    if any([torddl, zuzdl, leechdl, storage]):
        if not dl:
            await sleep(1)
            dl = await getDownloadByGid(gid)
        if dl and hasattr(dl, 'listener'):
            listener = dl.listener()
            download = await sync_to_async(api.get_download, gid)
            size = download.total_length
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
                await listener.onDownloadError(f'{msgerr}. File/folder size is {get_readable_file_size(size)}.', ename=download.name)
                await sync_to_async(api.remove, [download], force=True, files=True)


@new_thread
async def __onDownloadComplete(api, gid):
    try:
        download = await sync_to_async(api.get_download, gid)
    except:
        return
    if download.followed_by_ids:
        new_gid = download.followed_by_ids[0]
        LOGGER.info(f'Gid changed from {gid} to {new_gid}')
        await sleep(1.5)
        if dl:= await getDownloadByGid(new_gid):
            listener = dl.listener()
            if config_dict['BASE_URL'] and listener.select:
                if not dl.queued:
                    await sync_to_async(api.client.force_pause, new_gid)
                SBUTTONS = bt_selection_buttons(new_gid)
                msg = f'<code>{dl.name()}</code>\n\n{listener.tag}, your download paused. Choose files then press <b>Done Selecting</b> button to start downloading.'
                await sendingMessage(msg, listener.message, config_dict['IMAGE_PAUSE'], SBUTTONS)
    elif download.is_torrent:
        if dl := await getDownloadByGid(gid):
            if hasattr(dl, 'listener') and dl.seeding:
                LOGGER.info(f'Cancelling Seed: {download.name} onDownloadComplete')
                listener = dl.listener()
                await listener.onUploadError(f'Seeding stopped with Ratio {dl.ratio()} ({dl.seeding_time()})', download.name)
                await sync_to_async(api.remove, [download], force=True, files=True)
    else:
        LOGGER.info(f'onDownloadComplete: {download.name} - Gid: {gid}')
        if dl := await getDownloadByGid(gid):
            listener = dl.listener()
            await listener.onDownloadComplete()
            await sync_to_async(api.remove, [download], force=True, files=True)


@new_thread
async def __onBtDownloadComplete(api, gid):
    seed_start_time = time()
    await sleep(1)
    download = await sync_to_async(api.get_download, gid)
    LOGGER.info(f'onBtDownloadComplete: {download.name} - Gid: {gid}')
    if dl := await getDownloadByGid(gid):
        listener = dl.listener()
        if listener.select:
            res = download.files
            await gather(*[clean_target(file_o.path) for file_o in res if not file_o.selected])
            await clean_unwanted(download.dir)
        if listener.seed:
            try:
                await sync_to_async(api.set_options, {'max-upload-limit': '0'}, [download])
            except Exception as e:
                LOGGER.error(f'{e} You are not able to seed because you added global option seed-time=0 without adding specific seed_time for this torrent GID: {gid}')
        else:
            try:
                await sync_to_async(api.client.force_pause, gid)
            except Exception as e:
                LOGGER.error(f'{e} GID: {gid}')
        await listener.onDownloadComplete()
        download = download.live
        if listener.seed:
            if download.is_complete:
                if dl := await getDownloadByGid(gid):
                    LOGGER.info(f'Cancelling Seed: {download.name}')
                    await listener.onUploadError(f'Seeding stopped with Ratio {dl.ratio()} ({dl.seeding_time()})', download.name)
                    await sync_to_async(api.remove, [download], force=True, files=True)
            else:
                async with download_dict_lock:
                    if listener.uid not in download_dict:
                        await sync_to_async(api.remove, [download], force=True, files=True)
                        return
                    download_dict[listener.uid] = Aria2Status(gid, listener, True)
                    download_dict[listener.uid].start_time = seed_start_time
                LOGGER.info(f'Seeding started: {download.name} - Gid: {gid}')
                await update_all_messages()
        else:
            await sync_to_async(api.remove, [download], force=True, files=True)


@new_thread
async def __onDownloadStopped(api, gid):
    await sleep(6)
    if dl := await getDownloadByGid(gid):
        download = await sync_to_async(api.get_download, gid)
        ername = download.name.replace('[METADATA]', '')
        listener = dl.listener()
        await listener.onDownloadError('Dead torrent!', ename=ername)


@new_thread
async def __onDownloadError(api, gid):
    LOGGER.info(f'onDownloadError: {gid}')
    error = 'None'
    try:
        download = await sync_to_async(api.get_download, gid)
        error = download.error_message
        LOGGER.info(f'Download Error: {error}')
    except:
        pass
    if dl:= await getDownloadByGid(gid):
        listener = dl.listener()
        await listener.onDownloadError(error, ename=dl.name().replace('[METADATA]', ''))


def start_aria2_listener():
    aria2.listen_to_notifications(threaded=False,
                                  on_download_start=__onDownloadStarted,
                                  on_download_error=__onDownloadError,
                                  on_download_stop=__onDownloadStopped,
                                  on_download_complete=__onDownloadComplete,
                                  on_bt_download_complete=__onBtDownloadComplete,
                                  timeout=60)