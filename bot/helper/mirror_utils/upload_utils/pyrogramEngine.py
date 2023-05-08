from aiofiles.os import path as aiopath, rename as aiorename, makedirs
from aioshutil import copy
from asyncio import sleep
from logging import getLogger, ERROR
from natsort import natsorted
from os import path as ospath, walk
from PIL import Image
from pyrogram import Client
from pyrogram.errors import FloodWait, RPCError
from pyrogram.types import InputMediaVideo, InputMediaDocument, Message
from re import match as re_match
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type, RetryError
from time import time

from bot import bot, bot_dict, user_data, config_dict, GLOBAL_EXTENSION_FILTER, DEFAULT_SPLIT_SIZE
from bot.helper.ext_utils.bot_utils import sync_to_async, default_button
from bot.helper.ext_utils.fs_utils import clean_unwanted, clean_target, get_path_size, is_archive, get_base_name
from bot.helper.ext_utils.leech_utils import take_ss, get_document_type, get_media_info
from bot.helper.ext_utils.genss import GenSS
from bot.helper.ext_utils.mediainfo import mediainfo
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.message_utils import deleteMessage


LOGGER = getLogger(__name__)
getLogger('pyrogram').setLevel(ERROR)


class TgUploader:
    def __init__(self, name=None, path=None, size=0, listener=None):
        self.name = name
        self.__last_uploaded = 0
        self.__processed_bytes = 0
        self.__listener = listener
        self.__path = path
        self.__start_time = time()
        self.__is_cancelled = False
        self.__user_id = listener.message.from_user.id
        self.__thumb = f'thumbnails/{self.__user_id}.jpg'
        self.__msgs_dict = {}
        self.__is_corrupted = False
        self.__size = size
        self.__media_dict = {'videos': {}, 'documents': {}}
        self.__last_msg_in_group = False
        self.__client = None
        self.__up_path = ''

    async def __upload_progress(self, current, total):
        if self.__is_cancelled:
            self.__client.stop_transmission()
        chunk_size = current - self.__last_uploaded
        self.__last_uploaded = current
        self.__processed_bytes += chunk_size

    async def upload(self, o_files, m_size):
        await self.__user_settings()
        await self.__msg_to_reply()
        corrupted_files = total_files = 0
        for dirpath, _, files in sorted(await sync_to_async(walk, self.__path)):
            if dirpath.endswith('/yt-dlp-thumb'):
                continue
            for file_ in natsorted(files):
                self.__up_path = ospath.join(dirpath, file_)
                if file_.lower().endswith(tuple(GLOBAL_EXTENSION_FILTER)) or file_.startswith('Thumb'):
                    if not file_.startswith('Thumb'):
                        await clean_target(self.__up_path)
                    continue
                try:
                    f_size = await get_path_size(self.__up_path)
                    if self.__listener.seed and file_ in o_files and f_size in m_size:
                        continue
                    if f_size == 0:
                        corrupted_files += 1
                        LOGGER.error(f'{self.__up_path} size is zero, telegram don\'t upload zero size files')
                        continue
                    if self.__is_cancelled:
                        return
                    caption = await self.__prepare_file(file_, dirpath)
                    if self.__last_msg_in_group:
                        group_lists = [x for v in self.__media_dict.values() for x in v.keys()]
                        if (match := re_match(r'.+(?=\.0*\d+$)|.+(?=\.part\d+\..+)', self.__up_path)) and match.group(0) not in group_lists:
                            for key, value in list(self.__media_dict.items()):
                                for subkey, msgs in list(value.items()):
                                    if len(msgs) > 1:
                                        await self.__send_media_group(msgs, subkey, key)
                    self.__last_msg_in_group = False
                    self.__last_uploaded = 0
                    await self.__upload_file(caption, file_)
                    total_files += 1
                    if self.__is_cancelled:
                        return
                    if not self.__is_corrupted and (self.__listener.isSuperGroup or self.__leech_log):
                        self.__msgs_dict[self.__send_msg.link] = file_
                    await sleep(3)
                except Exception as err:
                    if isinstance(err, RetryError):
                        LOGGER.info(f'Total Attempts: {err.last_attempt.attempt_number}')
                        corrupted_files += 1
                        self.__is_corrupted = True
                    else:
                        LOGGER.error(f'{err}. Path: {self.__up_path}')
                    if self.__is_cancelled:
                        return
                    continue
                finally:
                    if not self.__is_cancelled and await aiopath.exists(self.__up_path) and (not self.__listener.seed or self.__listener.newDir or
                        dirpath.endswith('/splited_files_mltb') or '/copied_mltb/' in self.__up_path):
                        await clean_target(self.__up_path)

        for key, value in list(self.__media_dict.items()):
            for subkey, msgs in list(value.items()):
                if len(msgs) > 1:
                    await self.__send_media_group(msgs, subkey, key)
        if self.__is_cancelled:
            return
        if self.__listener.seed and not self.__listener.newDir:
            await clean_unwanted(self.__path)
        if total_files == 0:
            await self.__listener.onUploadError(f"No files to upload or in blocked list ({config_dict['EXTENSION_FILTER'].replace(' ', ', ')})!", self.name)
            return
        if total_files <= corrupted_files:
            await self.__listener.onUploadError('Files Corrupted or unable to upload. Check logs!', self.name)
            return
        LOGGER.info(f'Leech Completed: {self.name}')
        await self.__listener.onUploadComplete(None, self.__size, self.__msgs_dict, total_files, corrupted_files, self.name)

    @retry(wait=wait_exponential(multiplier=2, min=4, max=8), stop=stop_after_attempt(8), retry=retry_if_exception_type(Exception))
    async def __upload_file(self, caption, file, force_document=False):
        if self.__thumb and not await aiopath.exists(self.__thumb):
            self.__thumb = None
        thumb = self.__thumb
        if self.__is_cancelled:
            return
        try:
            self.__client = bot_dict['USERBOT'] if bot_dict['IS_PREMIUM'] and await get_path_size(self.__up_path) > DEFAULT_SPLIT_SIZE else bot
            is_video, is_audio, is_image = await get_document_type(self.__up_path)
            if not is_image and thumb is None:
                file_name = ospath.splitext(file)[0]
                thumb_path = f'{self.__path}/yt-dlp-thumb/{file_name}.jpg'
                if await aiopath.isfile(thumb_path):
                    thumb = thumb_path
            ss_image = None
            if is_video:
                duration = (await get_media_info(self.__up_path))[0]
                ss_image = await self.__gen_ss(self.__up_path)
                if not thumb:
                    thumb = await take_ss(self.__up_path, duration)

            buttons = await self.__get_button(True if is_video or is_audio else False)
            if self.__as_doc or force_document or (not is_video and not is_audio and not is_image):
                key = 'documents'
                if self.__is_cancelled:
                    return
                self.__send_msg = await self.__client.send_document(chat_id=self.__send_msg.chat.id,
                                                                    document=self.__up_path,
                                                                    thumb=thumb,
                                                                    caption=caption,
                                                                    disable_notification=True,
                                                                    progress=self.__upload_progress,
                                                                    reply_to_message_id=self.__send_msg.id,
                                                                    reply_markup=buttons)
                await self.__premium_check(key, buttons)
            elif is_video:
                key = 'videos'
                if thumb:
                    with Image.open(thumb) as img:
                        width, height = img.size
                else:
                    width, height = 480, 320
                if not self.__up_path.upper().endswith(('MKV', 'MP4')):
                    dirpath, file_ = self.__up_path.rsplit('/', 1)
                    if self.__listener.seed and not self.__listener.newDir and not dirpath.endswith('/splited_files_mltb'):
                        dirpath = ospath.join(dirpath, 'copied_mltb')
                        await makedirs(dirpath, exist_ok=True)
                        new_path = ospath.join(dirpath, f'{ospath.splitext(file_)[0]}.mp4')
                        self.__up_path = await copy(self.__up_path, new_path)
                    else:
                        new_path = f'{ospath.splitext(self.__up_path)[0]}.mp4'
                        await aiorename(self.__up_path, new_path)
                        self.__up_path = new_path
                if self.__is_cancelled:
                    return
                self.__send_msg = await self.__client.send_video(chat_id=self.__send_msg.chat.id,
                                                                 video=self.__up_path,
                                                                 caption=caption,
                                                                 duration=duration,
                                                                 width=width,
                                                                 height=height,
                                                                 thumb=thumb,
                                                                 supports_streaming=True,
                                                                 disable_notification=True,
                                                                 progress=self.__upload_progress,
                                                                 reply_to_message_id=self.__send_msg.id,
                                                                 reply_markup=buttons)
                await self.__premium_check(key, buttons)
            elif is_audio:
                key = 'audios'
                duration, artist, title = await get_media_info(self.__up_path)
                if self.__is_cancelled:
                    return
                self.__send_msg = await self.__client.send_audio(chat_id=self.__send_msg.chat.id,
                                                                 audio=self.__up_path,
                                                                 caption=caption,
                                                                 duration=duration,
                                                                 performer=artist,
                                                                 title=title,
                                                                 thumb=thumb,
                                                                 disable_notification=True,
                                                                 progress=self.__upload_progress,
                                                                 reply_to_message_id=self.__send_msg.id,
                                                                 reply_markup=buttons)
                await self.__premium_check(key, buttons)
            else:
                key = 'photos'
                if self.__is_cancelled:
                    return
                self.__send_msg = await bot.send_photo(chat_id=self.__send_msg.chat.id,
                                                       photo=self.__up_path,
                                                       caption=caption,
                                                       disable_notification=True,
                                                       progress=self.__upload_progress,
                                                       reply_to_message_id=self.__send_msg.id,
                                                       reply_markup=buttons)

            if self.__listener.isSuperGroup and self.__leech_log and self.__enable_pm or self.__listener.isSuperGroup and self.__enable_pm:
                await self.__copy_Leech(key, self.__user_id, self.__send_msg)
            if self.__user_dump:
                await self.__copy_Leech(key, self.__user_dump, self.__send_msg)
            if ss_image:
                await self.__send_ss(ss_image, buttons)
                await clean_target(ss_image)

            if not self.__is_cancelled and self.__media_group and (self.__send_msg.video or self.__send_msg.document):
                if match := re_match(r'.+(?=\.0*\d+$)|.+(?=\.part\d+\..+)', self.__up_path):
                    subkey = match.group(0)
                    if subkey in self.__media_dict[key].keys():
                        self.__media_dict[key][subkey].append(self.__send_msg)
                    else:
                        self.__media_dict[key][subkey] = [self.__send_msg]
                    msgs = self.__media_dict[key][subkey]
                    if len(msgs) == 10:
                        await self.__send_media_group(msgs, subkey, key)
                    else:
                        self.__last_msg_in_group = True

            if not self.__thumb and thumb and await aiopath.exists(thumb):
                await clean_target(thumb)
        except FloodWait as f:
            LOGGER.warning(str(f))
            await sleep(f.value)
        except Exception as err:
            if not self.__thumb and thumb and await aiopath.exists(thumb):
                await clean_target(thumb)
            err_type = 'RPCError: ' if isinstance(err, RPCError) else ''
            LOGGER.error(f'{err_type}{err}. Path: {self.__up_path}')
            if 'Telegram says: [400' in str(err) and key != 'documents':
                LOGGER.error(f'Retrying As Document. Path: {self.__up_path}')
                return await self.__upload_file(caption, file, True)
            raise err

    async def __user_settings(self):
        user_dict = user_data.get(self.__user_id, {})
        self.__as_doc = user_dict.get('as_doc', False) or ('as_doc' not in user_dict and config_dict['AS_DOCUMENT']) or self.__listener.isZip
        self.__media_group = user_dict.get('media_group', False) or ('media_group' not in user_dict and config_dict['MEDIA_GROUP'])
        self.__cap_mode = user_dict.get('user_cap', 'mono')
        self.__enable_pm = user_dict.get('enable_pm', False)
        self.__enable_ss = user_dict.get('enable_ss', False)
        self.__user_caption = user_dict.get('user_caption', False)
        self.__user_dump = user_dict.get('dump_id', False)
        self.__user_fnamecap = user_dict.get('user_fnamecap', True)
        if config_dict['AUTO_THUMBNAIL']:
            for dirpath, _, files in await sync_to_async(walk, self.__path):
                for file in files:
                    filepath = ospath.join(dirpath, file)
                    if file.startswith('Thumb') and (await get_document_type(filepath))[-1]:
                        self.__thumb = filepath

    @property
    def speed(self):
        try:
            return self.__processed_bytes / (time() - self.__start_time)
        except:
            return 0

    @property
    def processed_bytes(self):
        return self.__processed_bytes

    async def cancel_download(self):
        self.__is_cancelled = True
        LOGGER.info(f'Cancelling Upload: {self.name}')
        await self.__listener.onUploadError('Upload stopped by user!', self.name)

    #================================================== UTILS ==================================================
    async def __prepare_file(self, file_, dirpath):
        caption = self.__caption_mode(file_)
        if len(file_) > 60:
            if is_archive(file_):
                name = get_base_name(file_)
                ext = file_.split(name, 1)[1]
            elif match := re_match(r'.+(?=\..+\.0*\d+$)|.+(?=\.part\d+\..+)', file_):
                name = match.group(0)
                ext = file_.split(name, 1)[1]
            elif len(fsplit := ospath.splitext(file_)) > 1:
                name, ext = fsplit[0], fsplit[1]
            else:
                name, ext = file_, ''
            extn = len(ext)
            remain = 60 - extn
            name = name[:remain]
            if self.__listener.seed and not self.__listener.newDir and not dirpath.endswith('/splited_files_mltb'):
                dirpath = ospath.join(dirpath, 'copied_mltb')
                await makedirs(dirpath, exist_ok=True)
                new_path = ospath.join(dirpath, f'{name}{ext}')
                self.__up_path = await copy(self.__up_path, new_path)
            else:
                new_path = ospath.join(dirpath, f'{name}{ext}')
                await aiorename(self.__up_path, new_path)
                self.__up_path = new_path
        return caption

    def __caption_mode(self, file):
        if self.__cap_mode == 'italic':
            caption = f'<i>{file}</i>'
        elif self.__cap_mode == 'bold':
            caption = f'<b>{file}</b>'
        elif self.__cap_mode == 'normal':
            caption = file
        else:
            caption = f'<code>{file}</code>'
        if self.__user_caption:
            caption = f'''{caption}\n\n{self.__user_caption}''' if self.__user_fnamecap else self.__user_caption
        return caption

    async def __gen_ss(self, vid_path):
        if not self.__enable_ss or self.__is_cancelled:
            return
        ss = GenSS(self.__listener.message, vid_path)
        await ss.file_ss()
        if ss.error:
            return
        return ss.rimage
    #===========================================================================================================

    #================================================= MESSAGE =================================================
    async def __msg_to_reply(self):
        self.__leech_log = config_dict['LEECH_LOG']
        try:
            if self.__leech_log:
                caption = f'<b>▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n{self.name}\n▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬</b>'
                if self.__thumb and await aiopath.exists(self.__thumb):
                    self.__send_msg = await bot.send_photo(self.__leech_log, photo=self.__thumb, caption=caption)
                else:
                    self.__send_msg = await bot.send_message(self.__leech_log, caption, disable_web_page_preview=True)
            else:
                self.__send_msg = await bot.get_messages(self.__listener.message.chat.id, self.__listener.uid)
            if user_data.get(self.__user_id, {}).get('log_title') and self.__user_dump:
                await self.__copy_Leech('Log title', self.__user_dump, self.__send_msg)
        except FloodWait as f:
            LOGGER.warning(f)
            await sleep(f.value * 1.2)
            await self.__msg_to_reply()

    async def __premium_check(self, text: str, buttons):
        LOGGER.info(f'Using premium client! Edit markup {text}: ' + self.__send_msg.caption.split('\n')[0])
        if cmsg:= await (await bot.get_messages(self.__send_msg.chat.id, self.__send_msg.id)).edit_reply_markup(buttons):
            self.__send_msg = cmsg

    async def __send_media_group(self, msgs, subkey, key):
        try:
            msgs_list = await bot.send_media_group(chat_id=self.__send_msg.chat.id,
                                                   media=self.__get_input_media(subkey, key),
                                                   disable_notification=True,
                                                   reply_to_message_id=msgs[0].reply_to_message.id)
        except FloodWait as f:
            LOGGER.warning(f)
            await sleep(f.value * 1.2)
            await self.__send_media_group(msgs, subkey, key)
        if self.__enable_pm:
            await self.__copy_media_group(self.__user_id, msgs_list)
        if self.__user_dump:
            await self.__copy_media_group(self.__user_dump, msgs_list)
        for msg in msgs:
            if msg.link in self.__msgs_dict:
                del self.__msgs_dict[msg.link]
            await deleteMessage(msg)
        del self.__media_dict[key][subkey]
        if self.__listener.isSuperGroup or self.__leech_log:
            for m in msgs_list:
                self.__msgs_dict[m.link] = m.caption.split('\n')[0] + ' ~ (Grouped)'
        self.__send_msg = msgs_list[-1]

    async def __copy_media_group(self, chat_id, msgs):
        try:
            captions = [self.__caption_mode(msg.caption.split('\n')[0]) for msg in msgs]
            await bot.copy_media_group(chat_id=chat_id, from_chat_id=msgs[0].chat.id, message_id=msgs[0].id, captions=captions)
        except FloodWait as f:
            LOGGER.warning(f)
            await sleep(f.value * 1.2)
            await self.__copy_media_group(chat_id, msgs)
        except Exception as e:
            LOGGER.error(e)

    async def __send_ss(self, ss_image, button):
        try:
            ssmsg = await bot.send_photo(chat_id=self.__send_msg.chat.id,
                                         photo=ss_image,
                                         caption=f'<b>Screenshot Generated:\n</b><code>{ospath.basename(self.__up_path)}</code>',
                                         disable_notification=True,
                                         reply_to_message_id=self.__send_msg.id,
                                         reply_markup=button)
            if self.__enable_pm and self.__listener.isSuperGroup or self.__enable_pm and self.__leech_log:
                await self.__copy_Leech('SS', self.__user_id, ssmsg)
            if self.__user_dump:
                await self.__copy_Leech('SS', self.__user_dump, ssmsg)
        except FloodWait as f:
            LOGGER.warning(f)
            await sleep(f.value * 1.2)
            await self.__send_ss(ss_image, button)
        except Exception as e:
            LOGGER.error(e)

    async def __copy_Leech(self, text: str, chat_id: int, message: Message, buttons=None):
        try:
            if buttons:
                reply_markup = buttons
            elif config_dict['SAVE_MESSAGE'] and self.__listener.isSuperGroup:
                reply_markup = default_button(message)
            else:
                reply_markup = message.reply_markup
            return await message.copy()
            return await bot.copy_message(chat_id=chat_id,
                                          message_id=message.id,
                                          from_chat_id=message.chat.id,
                                          reply_to_message_id=message.reply_to_message.id if chat_id == message.chat.id else None,
                                          reply_markup=reply_markup)
        except FloodWait as f:
            LOGGER.warning(f)
            await sleep(f.value * 1.2)
            await self.__copy_Leech(text, chat_id, message, buttons)
        except Exception as e:
            LOGGER.error(f'Failed copy {text} to {chat_id}: {e}')

    def __get_input_media(self, subkey, key):
        rlist = []
        for msg in self.__media_dict[key][subkey]:
            caption = self.__caption_mode(msg.caption.split('\n')[0])
            if key == 'videos':
                input_media = InputMediaVideo(media=msg.video.file_id, caption=caption)
            else:
                input_media = InputMediaDocument(media=msg.document.file_id, caption=caption)
            rlist.append(input_media)
        return rlist

    async def __get_button(self, media_info=False):
        buttons = ButtonMaker()
        media_result = await mediainfo(self.__up_path, self.__size) if media_info else None
        if media_result:
            buttons.button_link('Media Info', media_result)
        if config_dict['SAVE_MESSAGE'] and self.__listener.isSuperGroup:
            buttons.button_data('Save Message', 'save', 'footer')
        return buttons.build_menu(1)
    #===========================================================================================================