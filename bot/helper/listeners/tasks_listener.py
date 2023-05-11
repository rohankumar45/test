from aiofiles.os import listdir, path as aiopath, makedirs
from aioshutil import move
from asyncio import create_subprocess_exec, sleep, Event
from glob import glob
from html import escape
from natsort import natsorted
from os import walk, path as ospath
from pyrogram.types import Message
from random import choice
from requests import utils as rutils, put
from time import time


from bot import bot_loop, bot_dict, bot_name, download_dict, download_dict_lock, Interval, aria2, user_data, config_dict, status_reply_dict_lock, non_queued_up, non_queued_dl, queued_up, queued_dl, queue_dict_lock, \
                DOWNLOAD_DIR, LOGGER, DATABASE_URL, DEFAULT_SPLIT_SIZE
from bot.helper.ext_utils.bot_utils import get_readable_time, is_magnet, is_url, presuf_remname_name, is_premium_user, action, get_link, is_media, get_date_time, UserDaily, default_button, sync_to_async, get_readable_file_size
from bot.helper.ext_utils.db_handler import DbManger
from bot.helper.ext_utils.exceptions import NotSupportedExtractionArchive
from bot.helper.ext_utils.fs_utils import get_base_name, get_path_size, clean_download, clean_target, presuf_remname_file, is_first_archive_split, is_archive, is_archive_split
from bot.helper.ext_utils.leech_utils import split_file
from bot.helper.ext_utils.shortenurl import short_url
from bot.helper.ext_utils.task_manager import start_from_queued
from bot.helper.ext_utils.telegraph_helper import TelePost
from bot.helper.ext_utils.merge_videos import Merge
from bot.helper.mirror_utils.rclone_utils.transfer import RcloneTransferHelper
from bot.helper.mirror_utils.status_utils.extract_status import ExtractStatus
from bot.helper.mirror_utils.status_utils.gdrive_status import GdriveStatus
from bot.helper.mirror_utils.status_utils.gofile_upload_status import GofileUploadStatus
from bot.helper.mirror_utils.status_utils.queue_status import QueueStatus
from bot.helper.mirror_utils.status_utils.rclone_status import RcloneStatus
from bot.helper.mirror_utils.status_utils.split_status import SplitStatus
from bot.helper.mirror_utils.status_utils.telegram_status import TelegramStatus
from bot.helper.mirror_utils.status_utils.zip_status import ZipStatus
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.mirror_utils.upload_utils.gofileuploadTools import GoFileUploader
from bot.helper.mirror_utils.upload_utils.pyrogramEngine import TgUploader
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.message_utils import sendCustom, sendMedia, sendMessage, auto_delete_message, delete_all_messages, sendSticker, update_all_messages, sendFile, copyMessage, sendingMessage


class MirrorLeechListener:
    def __init__(self, message: Message, isZip=False, extract=False, isQbit=False, isLeech=False, isGofile=False, pswd=None, tag=None, select=False, seed=False, newname='', multiId=None, sameDir=None, rcFlags=None, upPath=None):
        if sameDir is None:
            sameDir = {}
        self.message = message
        self.uid = message.id
        self.extract = extract
        self.isZip = isZip
        self.isQbit = isQbit
        self.isLeech = isLeech
        self.pswd = pswd
        self.tag = tag
        self.seed = seed
        self.newname = newname
        self.newDir = ''
        self.dir = f'{DOWNLOAD_DIR}{self.uid}'
        self.select = select
        self.isGofile = isGofile
        self.isSuperGroup = message.chat.type.name in ['SUPERGROUP', 'CHANNEL']
        self.suproc = None
        self.user_id = message.from_user.id
        self.sameDir = sameDir
        self.user_dict = user_data.get(self.user_id, {})
        self.rcFlags = rcFlags
        self.upPath = upPath
        self.multiId = multiId or ['', '', '']
        self.__link_go = ''

    async def clean(self):
        try:
            async with status_reply_dict_lock:
                Interval[0].cancel()
                Interval.clear()
            await sync_to_async(aria2.purge)
            await delete_all_messages()
        except:
            pass

    async def __rename(self, path):
        if not self.newname:
            prename, sufname, remname = self.user_dict.get('user_prename'), self.user_dict.get('user_sufname'), self.user_dict.get('user_remname')
            path = await presuf_remname_file(path, prename, sufname, remname)
        return path

    async def __archive(self, m_path, path, size, mpart=False):
        LEECH_SPLIT_SIZE = config_dict['LEECH_SPLIT_SIZE']
        cmd = ["7z", f"-v{LEECH_SPLIT_SIZE}b", "a", "-mx=0", f"-p{self.pswd}", path, m_path]
        if self.isLeech and int(size) > LEECH_SPLIT_SIZE or mpart and int(size) > LEECH_SPLIT_SIZE:
            if self.pswd is None:
                del cmd[4]
            LOGGER.info(f'Zip: orig_path: {m_path}, zip_path: {path}.0*')
        else:
            del cmd[1]
            if self.pswd is None:
                del cmd[3]
            LOGGER.info(f'Zip: orig_path: {m_path}, zip_path: {path}')
        if self.suproc == 'cancelled':
            return
        self.suproc = await create_subprocess_exec(*cmd)
        code = await self.suproc.wait()
        if code == -9:
            return
        elif not self.seed:
            await clean_target(m_path)
        return True

    async def onDownloadStart(self):
        if self.isSuperGroup and config_dict['INCOMPLETE_TASK_NOTIFIER'] and DATABASE_URL:
            await DbManger().add_incomplete_task(self.message.chat.id, self.message.link, self.tag)

    async def onDownloadComplete(self):
        if len(self.sameDir) > 0:
            await sleep(8)
        multi_links = False
        async with download_dict_lock:
            if len(self.sameDir) > 1:
                self.sameDir.remove(self.uid)
                folder_name = (await listdir(self.dir))[-1]
                path = f'{self.dir}/{folder_name}'
                des_path = f'{DOWNLOAD_DIR}{list(self.sameDir)[0]}/{folder_name}'
                await makedirs(des_path, exist_ok=True)
                for item in await listdir(path):
                    if item.endswith(('.aria2', '.!qB')):
                        continue
                    item_path = f"{self.dir}/{folder_name}/{item}"
                    if item in await listdir(des_path):
                        await move(item_path, f'{des_path}/{self.uid}-{item}')
                    else:
                        await move(item_path, f'{des_path}/{item}')
                multi_links = True
            download = download_dict[self.uid]
            name = str(download.name()).replace('/', '')
            gid = download.gid()
        LOGGER.info(f'Download completed: {name}')
        if multi_links:
            await self.onUploadError('Downloaded! Waiting for other tasks.', name)
            return
        if name == 'None' or self.isQbit or not await aiopath.exists(f'{self.dir}/{name}'):
            name = (await listdir(self.dir))[0]
        m_path = f'{self.dir}/{name}'
        if await aiopath.isdir(m_path) or not self.extract and await aiopath.isfile(m_path):
            m_path = await self.__rename(m_path)
        size = await get_path_size(m_path)
        LEECH_SPLIT_SIZE = config_dict['LEECH_SPLIT_SIZE']
        if config_dict['PREMIUM_MODE'] and not is_premium_user(self.user_id):
                LEECH_SPLIT_SIZE = DEFAULT_SPLIT_SIZE
        if not config_dict['QUEUE_COMPLETE']:
            async with queue_dict_lock:
                if self.uid in non_queued_dl:
                    non_queued_dl.remove(self.uid)
        await start_from_queued()
        if self.isZip:
            if self.user_dict.get('merge_vid'):
                if not await Merge(self).merge_vids(m_path, gid):
                    return
            zipmode = self.user_dict.get('zipmode', 'zfolder')
            if zipmode in ['zfolder', 'zfpart']:
                async with download_dict_lock:
                    download_dict[self.uid] = ZipStatus(name, size, gid, self)
                await update_all_messages()
                if self.seed and self.isLeech:
                    self.newDir = f'{self.dir}10000'
                    path = f'{self.newDir}/{name}.zip'
                elif zipmode == 'zfpart':
                    self.newDir = f'{self.dir}10000'
                    path = f'{self.newDir}/{name}/{name}.zip'
                else:
                    path = f'{m_path}.zip'
                mpart = True if zipmode == 'zfpart' else False
                if not await self.__archive(m_path, path, size, mpart):
                    return
                if zipmode == 'zfpart':
                    path = ospath.split(path)[0]
            else:
                self.seed = False
                org_path, archived = m_path, []
                for dirpath, _, files in await sync_to_async(walk, self.dir):
                    for file in natsorted(files):
                        if self.suproc == 'cancelled':
                            return
                        m_path = ospath.join(dirpath, file)
                        size = await get_path_size(m_path)
                        self.newDir = f'{self.dir}10000'
                        path = f'{self.newDir}/{file}.zip'
                        async with download_dict_lock:
                            download_dict[self.uid] = ZipStatus(name, size, gid, self, m_path)
                        await update_all_messages()
                        if zipmode == 'zeach':
                            archived.append(await self.__archive(m_path, path, size))
                        elif zipmode == 'zpart':
                            archived.append(await self.__archive(m_path, path, size, True))
                        elif zipmode == 'auto' and int(size) > LEECH_SPLIT_SIZE:
                            archived.append(await self.__archive(m_path, path, size, True))
                        for zfile in glob(f'{self.newDir}/*'):
                            await move(zfile, dirpath)
                if archived and not all(archived):
                    return
                path = org_path # if await aiopath.isdir(org_path) else f'{org_path}.zip'
        elif self.extract:
            try:
                if await aiopath.isfile(m_path):
                    path = get_base_name(m_path)
                LOGGER.info(f'Extracting: {name}')
                async with download_dict_lock:
                    download_dict[self.uid] = ExtractStatus(name, size, gid, self)
                await update_all_messages()
                if await aiopath.isdir(m_path):
                    if self.seed:
                        self.newDir = f'{self.dir}10000'
                        path = f'{self.newDir}/{name}'
                    else:
                        path = m_path
                    for dirpath, _, files in await sync_to_async(walk, m_path, topdown=False):
                        for file_ in natsorted(files):
                            if is_first_archive_split(file_) or is_archive(file_) and not file_.endswith('.rar'):
                                f_path = ospath.join(dirpath, file_)
                                t_path = dirpath.replace(self.dir, self.newDir) if self.seed else dirpath
                                cmds = ['7z', 'x', f'-p{self.pswd}', f_path, f'-o{t_path}', '-aot', '-xr!@PaxHeader']
                                if not self.pswd:
                                    del cmds[2]
                                if self.suproc == 'cancelled' or self.suproc is not None and self.suproc.returncode == -9:
                                    return
                                self.suproc = await create_subprocess_exec(*cmds)
                                code = await self.suproc.wait()
                                if code == -9:
                                    return
                                elif code != 0:
                                    LOGGER.error('Unable to extract archive splits!')
                        if not self.seed and self.suproc and self.suproc.returncode == 0:
                            for file_ in natsorted(files):
                                if is_archive_split(file_) or is_archive(file_):
                                    del_path = ospath.join(dirpath, file_)
                                    if not await clean_target(del_path):
                                        return
                else:
                    if self.seed and self.isLeech:
                        self.newDir = f'{self.dir}10000'
                        path = path.replace(self.dir, self.newDir)
                    cmd = ['7z', 'x', f'-p{self.pswd}', m_path, f'-o{path}', '-aot', '-xr!@PaxHeader']
                    if not self.pswd:
                        del cmd[2]
                    if self.suproc == 'cancelled':
                        return
                    self.suproc = await create_subprocess_exec(*cmd)
                    code = await self.suproc.wait()
                    if code == -9:
                        return
                    elif code == 0:
                        LOGGER.info(f'Extracted Path: {path}')
                        if not self.seed:
                            if not await clean_target(m_path):
                                return
                    else:
                        LOGGER.error('Unable to extract archive! Uploading anyway')
                        self.newDir = ''
                        path = m_path
                path = await self.__rename(path)
            except NotSupportedExtractionArchive:
                LOGGER.info('Not any valid archive, uploading file as it is.')
                self.newDir = ''
                path = m_path
        else:
            path = m_path
        if not self.isZip and self.user_dict.get('merge_vid'):
            if not await Merge(self).merge_vids(path, gid):
                return
        up_dir, up_name = path.rsplit('/', 1)
        size = await get_path_size(up_dir)
        if self.isLeech:
            o_files, m_size = [], []
            if not self.isZip:
                checked = False
                self.total_size = 0
                for dirpath, _, files in await sync_to_async(walk, up_dir, topdown=False):
                    for file_ in natsorted(files):
                        f_path = ospath.join(dirpath, file_)
                        f_size = await get_path_size(f_path)
                        if f_size > LEECH_SPLIT_SIZE:
                            if not checked:
                                checked = True
                                async with download_dict_lock:
                                    download_dict[self.uid] = SplitStatus(up_name, size, gid, self)
                                await update_all_messages()
                                LOGGER.info(f'Splitting ({LEECH_SPLIT_SIZE}): {up_name}')
                            res = await split_file(f_path, f_size, file_, dirpath, LEECH_SPLIT_SIZE, self)
                            if not res:
                                return
                            if res == 'errored':
                                if f_size <= bot_dict['MAX_SPLIT_SIZE']:
                                    continue
                                if not await clean_target(f_path):
                                    return
                            elif not self.seed or self.newDir:
                                if not await clean_target(f_path):
                                    return
                            else:
                                m_size.append(f_size)
                                o_files.append(file_)

        up_limit, all_limit = config_dict['QUEUE_UPLOAD'], config_dict['QUEUE_ALL']
        added_to_queue = False
        async with queue_dict_lock:
            dl, up = len(non_queued_dl), len(non_queued_up)
            if (all_limit and dl + up >= all_limit and (not up_limit or up >= up_limit)) or (up_limit and up >= up_limit):
                added_to_queue = True
                LOGGER.info(f'Added to Queue/Upload: {name}')
                event = Event()
                queued_up[self.uid] = event
        if added_to_queue:
            async with download_dict_lock:
                download_dict[self.uid] = QueueStatus(name, size, gid, self, 'Up')
            await event.wait()
            async with download_dict_lock:
                if self.uid not in download_dict:
                    return
            LOGGER.info(f'Start from Queued/Upload: {name}')
        async with queue_dict_lock:
            non_queued_up.add(self.uid)
        if self.isLeech:
            size = await get_path_size(up_dir)
            for s in m_size:
                size -= s
            LOGGER.info(f'Leech Name: {up_name}')
            tg = TgUploader(up_name, up_dir, size, self)
            async with download_dict_lock:
                download_dict[self.uid] = TelegramStatus(tg, self, size, gid, 'up')
            await update_all_messages()
            await tg.upload(o_files, m_size)
        elif self.upPath == 'gd':
            size = await get_path_size(path)
            if self.isGofile:
                data = {'folderName': up_name, 'token': config_dict['GOFILETOKEN'], 'parentFolderId': config_dict['GOFILEBASEFOLDER']}
                createdfolder = put('https://api.gofile.io/createFolder', data=data).json()['data']
                gofoldercode, gofolderid = createdfolder['code'], createdfolder['id']
                LOGGER.info(f'GoFile Folder has been created: {up_name} | {gofolderid}')
                go = GoFileUploader(up_name, self, gofolderid)
                async with download_dict_lock:
                    download_dict[self.uid] = GofileUploadStatus(go, size, gid, self.message)
                await update_all_messages()
                await go.uploadThis()
                self.__link_go = (f'https://gofile.io/d/{gofoldercode}')
                if go.cancelled:
                    return
            LOGGER.info(f'Uploading: {up_name}')
            drive = GoogleDriveHelper(up_name, up_dir, self)
            async with download_dict_lock:
                download_dict[self.uid] = GdriveStatus(drive, size, self, gid, 'up')
            await update_all_messages()
            await sync_to_async(drive.upload, up_name, size, self.multiId[1])
        else:
            size = await get_path_size(path)
            LOGGER.info(f'Uploading: {up_name}')
            RCTransfer = RcloneTransferHelper(self, up_name)
            async with download_dict_lock:
                download_dict[self.uid] = RcloneStatus(RCTransfer, self, gid, 'up')
            await update_all_messages()
            await RCTransfer.upload(path, size)

    async def onUploadComplete(self, link, size, files, folders, mime_type, name, rclonePath='', isClone=False):
        LOGGER.info(f'Task Done: {name}')
        dt_date, dt_time = get_date_time(self.message)
        buttons = ButtonMaker()
        buttons_scr = ButtonMaker()
        daily_size = size
        size = get_readable_file_size(size)
        reply_to = self.message.reply_to_message
        images = choice(config_dict['IMAGE_COMPLETE'].split())
        TIME_ZONE_TITLE = config_dict['TIME_ZONE_TITLE']
        drive_mode = None
        if config_dict['MULTI_GDID'] and not self.isLeech and self.upPath == 'gd':
            drive_mode = self.multiId[0]
        if self.isLeech and not self.newname and await aiopath.isfile(f'{self.dir}/{name}'):
            name = presuf_remname_name(self.user_dict, name)
        scr_link = await get_link(self.message)
        if (chat_id:= config_dict['LINK_LOG']) and self.isSuperGroup:
            msg_log = '<b>LINK LOGS</b>\n'
            msg_log += f'<code>{escape(name)}</code>\n'
            msg_log += f'<b>┌ Cc: </b>{self.tag}\n'
            msg_log += f'<b>├ ID: </b><code>{self.user_id}</code>\n'
            msg_log += f'<b>├ Size: </b>{size}\n'
            msg_log += f'<b>├ Elapsed: </b>{get_readable_time(time() - self.message.date.timestamp())}\n'
            msg_log += f'<b>├ Action: </b>{action(self.message)}\n'
            if drive_mode:
                msg_log += f'<b>├ Drive: </b>{drive_mode}\n'
            msg_log += '<b>├ Status: </b>#done\n'
            if self.isLeech:
                msg_log += f'<b>├ Total Files: </b>{folders}\n'
                if mime_type != 0:
                    msg_log += f'<b>├ Corrupted Files: </b>{mime_type}\n'
            else:
                msg_log += f'<b>├ Type: </b>{mime_type}\n'
                if mime_type == 'Folder':
                    if folders:
                        msg_log += f'<b>├ SubFolders: </b>{folders}\n'
                    msg_log += f'<b>├ Files: </b>{files}\n'
            msg_log += f'<b>├ Add: </b>{dt_date}\n'
            msg_log += f'<b>├ At: </b>{dt_time} ({TIME_ZONE_TITLE})\n'
            msg_log += f'<b>└ Source Link:</b>\n<code>{scr_link}</code>'
            if reply_to and is_media(reply_to):
                await sendMedia(msg_log, chat_id, reply_to)
            else:
                await sendCustom(msg_log, chat_id)
        if self.isSuperGroup and config_dict['INCOMPLETE_TASK_NOTIFIER'] and DATABASE_URL:
            await DbManger().rm_complete_task(self.message.link)
        msg = f'<code>{escape(name)}</code>\n'
        msg += f'<b>┌ Size: </b>{size}\n'
        if self.isLeech:
            if config_dict['SOURCE_LINK']:
                if is_magnet(scr_link):
                    tele = TelePost(config_dict['SOURCE_LINK_TITLE'])
                    mag_link = await sync_to_async(tele.create_post, f'<code>{escape(name)}<br>({size})</code><br>{scr_link}')
                    buttons.button_link(f'Source Link', mag_link)
                    buttons_scr.button_link(f'Source Link', mag_link)
                elif is_url(scr_link):
                    buttons.button_link(f'Source Link', scr_link)
                    buttons_scr.button_link(f'Source Link', scr_link)
            if self.user_dict.get('enable_pm') and self.isSuperGroup:
                buttons.button_link('View File(s)', f'http://t.me/{bot_name}')
            msg += f'<b>├ Total Files: </b>{folders}\n'
            if mime_type != 0:
                msg += f'<b>├ Corrupted Files: </b>{mime_type}\n'
            msg += f'<b>├ Elapsed: </b>{get_readable_time(time() - self.message.date.timestamp())}\n'
            msg += f'<b>├ Cc: </b>{self.tag}\n'
            msg += f'<b>├ Action: </b>{action(self.message)}\n'
            msg += f'<b>├ Add: </b>{dt_date}\n'
            msg += f'<b>└ At: </b>{dt_time} ({TIME_ZONE_TITLE})\n\n'
            ONCOMPLETE_LEECH_LOG = config_dict['ONCOMPLETE_LEECH_LOG']
            if not files:
                uploadmsg = await sendingMessage(msg, self.message, images, buttons.build_menu(2))
                if self.user_dict.get('enable_pm') and self.isSuperGroup:
                    if reply_to and is_media(reply_to):
                        await sendMedia(msg, self.user_id, reply_to, buttons_scr.build_menu(2))
                    else:
                        await copyMessage(self.user_id, uploadmsg, buttons_scr.build_menu(2))
                if (chat_id:= config_dict['LEECH_LOG']) and ONCOMPLETE_LEECH_LOG:
                    await copyMessage(chat_id, uploadmsg, buttons_scr.build_menu(2))
            else:
                result_msg = 0
                fmsg = '<b>Leech File(s):</b>\n'
                for index, (link, name) in enumerate(files.items(), start=1):
                    fmsg += f"{index}. <a href='{link}'>{name}</a>\n"
                    if len(fmsg.encode() + msg.encode()) > 4000:
                        uploadmsg = await sendMessage(msg + fmsg, self.message, buttons.build_menu(2))
                        await sleep(1)
                        if self.user_dict.get('enable_pm') and self.isSuperGroup:
                            if reply_to and is_media(reply_to) and result_msg == 0:
                                await sendMedia(msg + fmsg, self.user_id, reply_to, buttons_scr.build_menu(2))
                                result_msg += 1
                            else:
                                await copyMessage(self.user_id, uploadmsg, buttons_scr.build_menu(2))
                        if (chat_id := config_dict['LEECH_LOG']) and ONCOMPLETE_LEECH_LOG:
                            await copyMessage(chat_id, uploadmsg, buttons_scr.build_menu(2))
                        if self.isSuperGroup and (stime:= config_dict['AUTO_DELETE_UPLOAD_MESSAGE_DURATION']):
                            bot_loop.create_task(auto_delete_message(uploadmsg, stime=stime))
                        fmsg = ''
                if fmsg != '':
                    if len(fmsg.encode() + msg.encode()) < 1020:
                        uploadmsg = await sendingMessage(msg + fmsg, self.message, images, buttons.build_menu(2))
                    else:
                        uploadmsg = await sendMessage(msg + fmsg, self.message, buttons.build_menu(2))
                    if self.user_dict.get('enable_pm') and self.isSuperGroup:
                        if reply_to and is_media(reply_to):
                            await sendMedia(msg + fmsg, self.user_id, reply_to, buttons_scr.build_menu(2))
                        else:
                            await copyMessage(self.user_id, uploadmsg, buttons_scr.build_menu(2))
                    if (chat_id := config_dict['LEECH_LOG']) and ONCOMPLETE_LEECH_LOG:
                        await copyMessage(chat_id, uploadmsg, buttons_scr.build_menu(2))
                if STICKERID_LEECH := config_dict['STICKERID_LEECH']:
                    await sendSticker(STICKERID_LEECH, self.message)
            if self.seed:
                if self.newDir:
                    await clean_target(self.newDir)
                async with queue_dict_lock:
                    if self.uid in non_queued_up:
                        non_queued_up.remove(self.uid)
                await start_from_queued()
                return
        else:
            msg += f'<b>├ Type: </b>{mime_type}\n'
            if mime_type == 'Folder':
                if folders:
                    msg += f'<b>├ SubFolders: </b>{folders}\n'
                msg += f'<b>├ Files: </b>{files}\n'
            msg += f'<b>├ Elapsed: </b>{get_readable_time(time() - self.message.date.timestamp())}\n'
            msg += f'<b>├ Cc: </b>{self.tag}\n'
            msg += f'<b>├ Action: </b>{action(self.message)}\n'
            if drive_mode:
                msg += f'<b>├ Drive: </b>{drive_mode}\n'
            msg += f'<b>├ Add: </b>{dt_date}\n'
            msg += f'<b>└ At: </b>{dt_time} ({TIME_ZONE_TITLE})'
            if link or rclonePath:
                if self.isGofile and self.__link_go:
                    golink = await sync_to_async(short_url, self.__link_go)
                    buttons.button_link('GoFile Link', golink)
                if link:
                    link = await sync_to_async(short_url, link)
                    buttons.button_link('Cloud Link', link)
                else:
                    msg += f'\n\n<b>Path:</b> <code>{rclonePath}</code>'
                if rclonePath and (RCLONE_SERVE_URL:= config_dict['RCLONE_SERVE_URL']):
                    remote, path = rclonePath.split(':', 1)
                    url_path = rutils.quote(f'{path}')
                    share_url = f'{RCLONE_SERVE_URL}/{remote}/{url_path}'
                    if mime_type == 'Folder':
                        share_url += '/'
                    buttons.button_link('RClone Link', share_url)
                if not rclonePath:
                    INDEX_URL = self.multiId[2]
                    if INDEX_URL:
                        url_path = rutils.quote(f'{name}')
                        share_url = f'{INDEX_URL}/{url_path}'
                        if mime_type == 'Folder':
                            share_url = await sync_to_async(short_url, f'{share_url}/')
                            buttons.button_link('Index Link', share_url)
                        else:
                            share_url = await sync_to_async(short_url, share_url)
                            buttons.button_link('Index Link', share_url)
                            if config_dict['VIEW_LINK']:
                                share_urls = await sync_to_async(short_url, f'{INDEX_URL}/{url_path}?a=view')
                                buttons.button_link('View Link', share_urls)
            else:
                msg += f'\n\n<b>Path:</b> <code>{rclonePath}</code>'
            if (but_key:= config_dict['BUTTON_FOUR_NAME']) and (but_url:= config_dict['BUTTON_FOUR_URL']):
                buttons.button_link(but_key, but_url)
            if (but_key:= config_dict['BUTTON_FIVE_NAME']) and (but_url:= config_dict['BUTTON_FIVE_URL']):
                buttons.button_link(but_key, but_url)
            if (but_key:= config_dict['BUTTON_SIX_NAME']) and (but_url:= config_dict['BUTTON_SIX_URL']):
                buttons.button_link(but_key, but_url)
            if config_dict['SOURCE_LINK']:
                if is_magnet(scr_link):
                    tele = TelePost(config_dict['SOURCE_LINK_TITLE'])
                    mag_link = await sync_to_async(tele.create_post, f'<code>{escape(name)}<br>({size})</code><br>{scr_link}')
                    buttons.button_link(f'Source Link', mag_link)
                elif is_url(scr_link):
                    buttons.button_link(f'Source Link', scr_link)
            if config_dict['SAVE_MESSAGE'] and self.isSuperGroup:
                buttons.button_data('Save Message', 'save', 'footer')
            uploadmsg = await sendingMessage(msg, self.message, images, buttons.build_menu(2))
            if STICKERID_MIRROR := config_dict['STICKERID_MIRROR']:
                await sendSticker(STICKERID_MIRROR, self.message)
            if chat_id := config_dict['MIRROR_LOG']:
                await copyMessage(chat_id, uploadmsg)
            if self.user_dict.get('enable_pm') and self.isSuperGroup:
                button = default_button(uploadmsg) if config_dict['SAVE_MESSAGE'] else uploadmsg.reply_markup
                if reply_to and is_media(reply_to):
                    await sendMedia(msg, self.user_id, reply_to, button)
                else:
                    await copyMessage(self.user_id, uploadmsg, button)
            if self.seed:
                if self.isZip:
                    await clean_target(f'{self.dir}/{name}')
                elif self.newDir:
                    await clean_target(self.newDir)
                async with queue_dict_lock:
                    if self.uid in non_queued_up:
                        non_queued_up.remove(self.uid)
                await start_from_queued()
                return
        if config_dict['DAILY_MODE'] and not isClone and not is_premium_user(self.user_id):
            await UserDaily(self.user_id).set_daily_limit(daily_size)
        await clean_download(self.dir)
        async with download_dict_lock:
            if self.uid in download_dict.keys():
                del download_dict[self.uid]
            count = len(download_dict)
        if count == 0:
            await self.clean()
        else:
            await update_all_messages()

        async with queue_dict_lock:
            if self.uid in non_queued_dl:
                non_queued_dl.remove(self.uid)
            if self.uid in non_queued_up:
                non_queued_up.remove(self.uid)

        await start_from_queued()

        if self.isSuperGroup and (stime:= config_dict['AUTO_DELETE_UPLOAD_MESSAGE_DURATION']):
            bot_loop.create_task(auto_delete_message(self.message, uploadmsg, reply_to, stime=stime))

    async def onDownloadError(self, error, listfile=None, ename=None, isClone=False):
        reply_to = self.message.reply_to_message
        dt_date, dt_time = get_date_time(self.message)
        TIME_ZONE_TITLE = config_dict['TIME_ZONE_TITLE']
        drive_mode = None
        if config_dict['MULTI_GDID'] and not self.isLeech and self.upPath == 'gd':
            drive_mode = self.multiId[0]
        if (chat_id:= config_dict['LINK_LOG']) and self.isSuperGroup:
            msg_log = '<b>LINK LOGS</b>\n'
            if ename:
                msg_log += f'<code>{ename}</code>\n'
            msg_log += f'<b>┌ Cc: </b>{self.tag}\n'
            msg_log += f'<b>├ ID: </b><code>{self.user_id}</code>\n'
            msg_log += f'<b>├ Elapsed: </b>{get_readable_time(time() - self.message.date.timestamp())}\n'
            msg_log += f'<b>├ Action: </b>{action(self.message)}\n'
            if drive_mode:
                msg_log += f'<b>├ Drive: </b>{drive_mode}\n'
            msg_log += '<b>├ Status: </b>#undone\n'
            msg_log += f"<b>├ On: </b>{'#clone' if isClone else '#download'}\n"
            msg_log += f'<b>├ Add: </b>{dt_date}\n'
            msg_log += f'<b>├ At: </b>{dt_time} ({TIME_ZONE_TITLE})\n'
            msg_log += f'<b>└ Source Link:</b>\n<code>{await get_link(self.message)}</code>'
            if reply_to and is_media(reply_to):
                await sendMedia(msg_log, chat_id, reply_to)
            else:
                await sendCustom(msg_log, chat_id)
        async with download_dict_lock:
            if self.uid in download_dict:
                del download_dict[self.uid]
            count = len(download_dict)
            if self.uid in self.sameDir:
                self.sameDir.remove(self.uid)
        if len(error) > (1000 if config_dict['ENABLE_IMAGE_MODE'] else 3800):
            err_msg = await sync_to_async(TelePost('Download Error').create_post, error.replace('\n', '<br>'))
            err_msg = f'<a href="{err_msg}"><b>Details</b></a>'
        else:
            err_msg = escape(error)
        msg = f"<b>{'Clone' if isClone else 'Download'} Has Been Stopped!</b>\n"
        if ename:
            msg += f'<code>{ename}</code>\n'
        msg += f'<b>┌ Elapsed: </b>{get_readable_time(time() - self.message.date.timestamp())}\n'
        msg += f'<b>├ Cc:</b> {self.tag}\n'
        msg += f'<b>├ Action: </b>{action(self.message)}\n'
        if drive_mode:
            msg += f'<b>├ Drive: </b>{drive_mode}\n'
        msg += f'<b>├ Add: </b>{dt_date}\n'
        msg += f'<b>├ At: </b>{dt_time} ({TIME_ZONE_TITLE})\n'
        msg += f'<b>└ Due to:</b> {err_msg}'
        if listfile:
            await sendFile(self.message, listfile, msg, config_dict['IMAGE_HTML'])
        else:
            await sendingMessage(msg, self.message, choice(config_dict['IMAGE_COMPLETE'].split()))
        if count == 0:
            await self.clean()
        else:
            await update_all_messages()

        if sticker:= config_dict['STICKERID_MIRROR'] if 'already in drive' in error.lower() else config_dict['STICKERID_ERROR']:
            await sendSticker(sticker, self.message)

        if self.isSuperGroup and config_dict['INCOMPLETE_TASK_NOTIFIER'] and DATABASE_URL:
            await DbManger().rm_complete_task(self.message.link)

        async with queue_dict_lock:
            if self.uid in queued_dl:
                queued_dl[self.uid].set()
                del queued_dl[self.uid]
            if self.uid in queued_up:
                queued_up[self.uid].set()
                del queued_up[self.uid]
            if self.uid in non_queued_dl:
                non_queued_dl.remove(self.uid)
            if self.uid in non_queued_up:
                non_queued_up.remove(self.uid)

        await start_from_queued()
        await sleep(3)
        await clean_download(self.dir)
        if self.newDir:
            await clean_download(self.newDir)

        if self.isSuperGroup and (stime:= config_dict['AUTO_DELETE_UPLOAD_MESSAGE_DURATION']):
            bot_loop.create_task(auto_delete_message(self.message, reply_to, stime=stime))

    async def onUploadError(self, error, ename=None, isClone=False):
        buttons = ButtonMaker()
        dt_date, dt_time = get_date_time(self.message)
        reply_to = self.message.reply_to_message
        TIME_ZONE_TITLE = config_dict['TIME_ZONE_TITLE']
        drive_mode = None
        if config_dict['MULTI_GDID'] and not self.isLeech and self.upPath == 'gd':
            drive_mode = self.multiId[0]
        if (chat_id:= config_dict['LINK_LOG']) and self.isSuperGroup:
            msg_log = '<b>LINK LOGS</b>\n'
            if ename:
                msg_log += f'<code>{ename}</code>\n'
            msg_log += f'<b>┌ Cc: </b>{self.tag}\n'
            msg_log += f'<b>├ ID: </b><code>{self.user_id}</code>\n'
            msg_log += f'<b>├ Elapsed: </b>{get_readable_time(time() - self.message.date.timestamp())}\n'
            msg_log += f'<b>├ Action: </b>{action(self.message)}\n'
            if drive_mode:
                msg_log += f'<b>├ Drive: </b>{drive_mode}\n'
            if 'Seeding' in error:
                msg_log += '<b>├ Status: </b>#done\n'
            else:
                msg_log += '<b>├ Status: </b>#undone\n'
            msg_log += f"<b>├ On: </b>{'#clone' if isClone else '#upload'}\n"
            msg_log += f'<b>├ Add: </b>{dt_date}\n'
            msg_log += f'<b>├ At: </b>{dt_time} ({TIME_ZONE_TITLE})\n'
            msg_log += f'<b>└ Source Link:</b>\n<code>{await get_link(self.message)}</code>'
            if reply_to and is_media(reply_to):
                await sendMedia(msg_log, chat_id, reply_to)
            else:
                await sendCustom(msg_log, chat_id)
        async with download_dict_lock:
            if self.uid in download_dict:
                del download_dict[self.uid]
            count = len(download_dict)
            if self.uid in self.sameDir:
                self.sameDir.remove(self.uid)
        if len(error) > (1000 if config_dict['ENABLE_IMAGE_MODE'] else 3800):
            err_msg = await sync_to_async(TelePost('Upload Error').create_post, error.replace('\n', '<br>'))
            err_msg = f'<a href="{err_msg}"><b>Details</b></a>'
        else:
            err_msg = escape(error)
        msg = f"<b>{'Clone' if isClone else 'Upload'} Has Been Stopped!</b>\n"
        if ename:
            msg += f'<code>{ename}</code>\n'
        msg += f'<b>┌ Elapsed: </b>{get_readable_time(time() - self.message.date.timestamp())}\n'
        msg += f'<b>├ Cc:</b> {self.tag}\n'
        msg += f'<b>├ Action: </b>{action(self.message)}\n'
        if drive_mode:
            msg += f'<b>├ Drive: </b>{drive_mode}\n'
        msg += f'<b>├ Add: </b>{dt_date}\n'
        msg += f'<b>├ At: </b>{dt_time} ({TIME_ZONE_TITLE})\n'
        msg += f'<b>└ Due to:</b> {err_msg}'
        if self.isGofile and self.__link_go:
            buttons.button_link('GoFile Link', self.__link_go)
            if config_dict['SAVE_MESSAGE'] and self.isSuperGroup:
                buttons.button_data('Save Message', 'save', 'footer')
        await sendingMessage(msg, self.message, choice(config_dict['IMAGE_COMPLETE'].split()), buttons.build_menu(1))
        if count == 0:
            await self.clean()
        else:
            await update_all_messages()

        if sticker:= config_dict['STICKERID_MIRROR'] if any(x in error for x in ['Seeding', 'Downloaded']) else config_dict['STICKERID_ERROR']:
            await sendSticker(sticker, self.message)

        if self.isSuperGroup and config_dict['INCOMPLETE_TASK_NOTIFIER'] and DATABASE_URL:
            await DbManger().rm_complete_task(self.message.link)

        async with queue_dict_lock:
            if self.uid in queued_dl:
                queued_dl[self.uid].set()
                del queued_dl[self.uid]
            if self.uid in queued_up:
                queued_up[self.uid].set()
                del queued_up[self.uid]
            if self.uid in non_queued_dl:
                non_queued_dl.remove(self.uid)
            if self.uid in non_queued_up:
                non_queued_up.remove(self.uid)

        await start_from_queued()
        await sleep(3)
        await clean_download(self.dir)
        if self.newDir:
            await clean_download(self.newDir)

        if self.isSuperGroup and (stime:= config_dict['AUTO_DELETE_UPLOAD_MESSAGE_DURATION']):
            bot_loop.create_task(auto_delete_message(self.message, reply_to, stime=stime))