from aiofiles.os import path as aiopath
from asyncio import Event

from bot import config_dict, queued_dl, queued_up, non_queued_up, non_queued_dl, queue_dict_lock, LOGGER
from bot.helper.ext_utils.bot_utils import sync_to_async, presuf_remname_name
from bot.helper.ext_utils.fs_utils import get_base_name
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper


def start_dl_from_queued(uid):
    queued_dl[uid].set()
    del queued_dl[uid]


def start_up_from_queued(uid):
    queued_up[uid].set()
    del queued_up[uid]


async def stop_duplicate_check(name: str, listener, mega_type='folder'):
    if config_dict['STOP_DUPLICATE'] and not listener.isLeech and not listener.user_dict.get('cus_gdrive') and listener.upPath == 'gd':
        LOGGER.info(f'Checking File/Folder if already in Drive: {name}')
        if listener.isZip:
            name = f'{name}.zip'
        elif listener.extract:
            try:
                name = get_base_name(name)
            except:
                name = None
        if name:
            LOGGER.info(mega_type)
            LOGGER.info(bool(listener.newname))
            if not listener.newname and (await aiopath.isfile(f'{listener.dir}/{name}' or mega_type == 'file')):
                LOGGER.info('================================================')
                name = presuf_remname_name(listener.user_dict, name)
            count, file = await sync_to_async(GoogleDriveHelper().drive_list, name, stopDup=True)
            if count:
                return file, name
        LOGGER.info('Checking duplicate is passed...')
    return None, ''


async def is_queued(uid: int):
    all_limit, dl_limit = config_dict['QUEUE_ALL'], config_dict['QUEUE_DOWNLOAD']
    added_to_queue, event = False, None
    if all_limit or dl_limit:
        async with queue_dict_lock:
            dl = len(non_queued_dl)
            up = len(non_queued_up)
            if (all_limit and dl + up >= all_limit and (not dl_limit or dl >= dl_limit)) or (dl_limit and dl >= dl_limit):
                added_to_queue = True
                event = Event()
                queued_dl[uid] = event
    return added_to_queue, event


async def start_from_queued():
    if all_limit := config_dict['QUEUE_ALL']:
        dl_limit, up_limit = config_dict['QUEUE_DOWNLOAD'], config_dict['QUEUE_UPLOAD']
        async with queue_dict_lock:
            dl = len(non_queued_dl)
            up = len(non_queued_up)
            all_ = dl + up
            if all_ < all_limit:
                f_tasks = all_limit - all_
                if queued_up and (not up_limit or up < up_limit):
                    for index, uid in enumerate(list(queued_up.keys()), start=1):
                        f_tasks = all_limit - all_
                        start_up_from_queued(uid)
                        f_tasks -= 1
                        if f_tasks == 0 or (up_limit and index >= up_limit - up):
                            break
                if queued_dl and (not dl_limit or dl < dl_limit) and f_tasks != 0:
                    for index, uid in enumerate(list(queued_dl.keys()), start=1):
                        start_dl_from_queued(uid)
                        if (dl_limit and index >= dl_limit - dl) or index == f_tasks:
                            break
        return

    if up_limit := config_dict['QUEUE_UPLOAD']:
        async with queue_dict_lock:
            up = len(non_queued_up)
            if queued_up and up < up_limit:
                f_tasks = up_limit - up
                for index, uid in enumerate(list(queued_up.keys()), start=1):
                    start_up_from_queued(uid)
                    if index == f_tasks:
                        break
    else:
        async with queue_dict_lock:
            if queued_up:
                for uid in list(queued_up.keys()):
                    start_up_from_queued(uid)

    if dl_limit := config_dict['QUEUE_DOWNLOAD']:
        async with queue_dict_lock:
            dl = len(non_queued_dl)
            if queued_dl and dl < dl_limit:
                f_tasks = dl_limit - dl
                for index, uid in enumerate(list(queued_dl.keys()), start=1):
                    start_dl_from_queued(uid)
                    if index == f_tasks:
                        break
    else:
        async with queue_dict_lock:
            if queued_dl:
                for uid in list(queued_dl.keys()):
                    start_dl_from_queued(uid)