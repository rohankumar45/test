from aiofiles import open as aiopen
from aiofiles.os import path as aiopath
from asyncio import wait_for, Event, wrap_future
from configparser import ConfigParser
from functools import partial
from json import loads
from pyrogram import Client
from pyrogram.filters import regex, user
from pyrogram.handlers import CallbackQueryHandler
from pyrogram.types import Message, CallbackQuery
from time import time

from bot import LOGGER
from bot.helper.ext_utils.bot_utils import get_readable_time, cmd_exec, new_thread, get_readable_file_size, new_task
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.message_utils import editMessage, sendMessage, deleteMessage

LIST_LIMIT = 6


class RcloneList:
    def __init__(self, client: Client, message: Message, user_id: int):
        self.__client = client
        self.__message = message
        self.__user_id = user_id
        self.__rc_user = False
        self.__rc_owner = False
        self.__sections = []
        self.__time = time()
        self.__timeout = 240
        self.__reply_to = None
        self.remote = ''
        self.is_cancelled = False
        self.query_proc = False
        self.item_type = '--dirs-only'
        self.event = Event()
        self.user_rcc_path = f'rclone/{self.__user_id}.conf'
        self.config_path = ''
        self.path = ''
        self.list_status = ''
        self.path_list = []
        self.iter_start = 0
        self.page_step = 1

    @new_thread
    async def __event_handler(self):
        pfunc = partial(path_updates, obj=self)
        handler = self.__client.add_handler(CallbackQueryHandler(pfunc, filters=regex('^rcq') & user(self.__user_id)), group=-1)
        try:
            await wait_for(self.event.wait(), timeout=self.__timeout)
        except:
            self.path = ''
            self.remote = 'Timed Out. Task has been cancelled!'
            self.is_cancelled = True
            self.event.set()
        finally:
            self.__client.remove_handler(*handler)

    async def __send_list_message(self, msg, buttons):
        if not self.is_cancelled:
            if not self.__reply_to:
                # await editMessage('<i>Waiting for rclone select...</i>', self.__message)
                # self.__reply_to = await sendMessage(msg, self.__message, buttons)
                self.__reply_to = await self.__client.get_messages(self.__message.chat.id, self.__message.id)
            # else:
            await editMessage(msg, self.__reply_to, buttons)

    async def get_path_buttons(self):
        items_no = len(self.path_list)
        pages = (items_no + LIST_LIMIT - 1) // LIST_LIMIT
        if items_no <= self.iter_start:
            self.iter_start = 0
        elif self.iter_start < 0 or self.iter_start > items_no:
            self.iter_start = LIST_LIMIT * (pages - 1)
        page = (self.iter_start/LIST_LIMIT) + 1 if self.iter_start != 0 else 1
        buttons = ButtonMaker()
        for index, idict in enumerate(self.path_list[self.iter_start:LIST_LIMIT+self.iter_start]):
            orig_index = index + self.iter_start
            if idict['IsDir']:
                ptype = 'fo'
                name = idict['Path']
            else:
                ptype = 'fi'
                name = f"[{get_readable_file_size(idict['Size'])}] {idict['Path']}"
            buttons.button_data(name, f'rcq pa {ptype} {orig_index}')
        if items_no > LIST_LIMIT:
            for i in [1, 2, 4, 6, 10, 30, 50, 100]:
                buttons.button_data(i, f'rcq ps {i}', 'header')
            buttons.button_data('Prev', 'rcq pre', 'footer')
            buttons.button_data('Next', 'rcq nex', 'footer')
        if self.list_status == 'rcd':
            if self.item_type == '--dirs-only':
                buttons.button_data('Files', 'rcq itype --files-only', 'footer')
            else:
                buttons.button_data('Folders', 'rcq itype --dirs-only', 'footer')
        if self.list_status == 'rcu' or len(self.path_list) > 0:
            buttons.button_data('This Path', 'rcq cur', 'footer')
        if self.path or len(self.__sections) > 1 or self.__rc_user and self.__rc_owner:
            buttons.button_data('<<', 'rcq back pa', 'footer')
        if self.path:
            buttons.button_data('Root', 'rcq root', 'footer')
        buttons.button_data('Cancel', 'rcq cancel', 'footer')
        msg = f'<b>Choose Path:</b>\n'
        if items_no > LIST_LIMIT:
            msg += f'Page: <b>{int(page)}/{pages}</b> | Steps: <b>{self.page_step}</b>\n\n'
        msg += f'Items: <b>{items_no}</b>\n'
        msg += f'Item Type: <b>{self.item_type}</b>\n'
        msg += f"Transfer Type: <b>{'Download' if self.list_status == 'rcd' else 'Upload' }</b>\n"
        msg += f'Config Path: <b>{self.config_path}</b>\n'
        msg += f'Current Path: <code>{self.remote}{self.path}</code>\n\n'
        msg += f'<i>Timeout: {get_readable_time(self.__timeout-(time()-self.__time))}</i>'
        await self.__send_list_message(msg, buttons.build_menu(f_cols=2))

    async def get_path(self, itype=''):
        if self.__reply_to:
            await editMessage(f'<i>Listing file(s), please wait...</i>', self.__reply_to)
        if itype:
            self.item_type == itype
        elif self.list_status == 'rcu':
            self.item_type == '--dirs-only'
        cmd = ['./gclone', 'lsjson', self.item_type, '--fast-list', '--no-mimetype', '--no-modtime', '--config', self.config_path, f'{self.remote}{self.path}']
        if self.is_cancelled:
            return
        res, err, code = await cmd_exec(cmd)
        if code not in [0, -9]:
            LOGGER.error(f'While rclone listing. Path: {self.remote}{self.path}. Stderr: {err}')
            self.remote = err
            self.path = ''
            self.event.set()
            return
        result = loads(res)
        if len(result) == 0 and itype != self.item_type and self.list_status == 'rcd':
            itype = '--dirs-only' if self.item_type == '--files-only' else '--files-only'
            self.item_type = itype
            return await self.get_path(itype)
        self.path_list = sorted(result, key=lambda x: x["Path"])
        self.iter_start = 0
        await self.get_path_buttons()

    async def list_remotes(self):
        config = ConfigParser()
        async with aiopen(self.config_path, 'r') as f:
            contents = await f.read()
            config.read_string(contents)
        if config.has_section('combine'):
            config.remove_section('combine')
        self.__sections = config.sections()
        if len(self.__sections) == 1:
            self.remote = f'{self.__sections[0]}:'
            await self.get_path()
        else:
            msg = 'Choose Rclone remote:\n' + f"Transfer Type: <b>{'Download' if self.list_status == 'rcd' else 'Upload'}</b>\n"
            msg += f'Config Path: <b>{self.config_path}</b>\n\n'
            msg += f'<i>Timeout: {get_readable_time(self.__timeout-(time()-self.__time))}.</i>'
            buttons = ButtonMaker()
            for remote in self.__sections:
                buttons.button_data(remote, f'rcq re {remote}:')
            if self.__rc_user and self.__rc_owner:
                buttons.button_data('<<', 'rcq back re', 'footer')
            buttons.button_data('Cancel', 'rcq cancel', 'footer')
            await self.__send_list_message(msg, buttons.build_menu(2))

    async def list_config(self):
        if self.__rc_user and self.__rc_owner:
            msg = 'Choose Rclone remote:\n' + f"Transfer Type: <b>{'Download' if self.list_status == 'rcd' else 'Upload'}</b>\n\n"
            msg += f'<i>Timeout: {get_readable_time(self.__timeout-(time()-self.__time))}.</i>'
            buttons = ButtonMaker()
            buttons.button_data('Owner Config', 'rcq owner')
            buttons.button_data('My Config', 'rcq user')
            buttons.button_data('Cancel', 'rcq cancel')
            await self.__send_list_message(msg, buttons.build_menu(2))
        else:
            self.config_path = 'rclone.conf' if self.__rc_owner else self.user_rcc_path
            await self.list_remotes()

    async def back_from_path(self):
        if self.path:
            path = self.path.rsplit('/', 1)
            self.path = path[0] if len(path) > 1 else ''
            await self.get_path()
        elif len(self.__sections) > 1:
            await self.list_remotes()
        else:
            await self.list_config()

    async def get_rclone_path(self, status, config_path=None):
        self.list_status = status
        future = self.__event_handler()
        if config_path:
            self.config_path = config_path
            await self.list_remotes()
        else:
            self.__rc_user = await aiopath.exists(self.user_rcc_path)
            self.__rc_owner = await aiopath.exists('rclone.conf')
            if not self.__rc_owner and not self.__rc_user:
                self.event.set()
                return 'Rclone Config not Exists!'
            await self.list_config()
        await wrap_future(future)
        # await deleteMessage(self.__reply_to)
        if self.config_path != 'rclone.conf' and not self.is_cancelled:
            return f'mrcc:{self.remote}{self.path}'
        return f'{self.remote}{self.path}'


@new_task
async def path_updates(_, query: CallbackQuery, obj: RcloneList):
    await query.answer()
    data = query.data.split()
    if data[1] == 'cancel':
        obj.remote = 'Task has been cancelled!'
        obj.path = ''
        obj.is_cancelled = True
        obj.event.set()
        return
    if obj.query_proc:
        return
    obj.query_proc = True
    if data[1] == 'pre':
        obj.iter_start -= LIST_LIMIT * obj.page_step
        await obj.get_path_buttons()
    elif data[1] == 'nex':
        obj.iter_start += LIST_LIMIT * obj.page_step
        await obj.get_path_buttons()
    elif data[1] == 'back':
        if data[2] == 're':
            await obj.list_config()
        else:
            await obj.back_from_path()
    elif data[1] == 're':
        # Some remotes has space
        data = query.data.split(maxsplit=2)
        obj.remote = data[2]
        await obj.get_path()
    elif data[1] == 'pa':
        index = int(data[3])
        obj.path += f"/{obj.path_list[index]['Path']}" if obj.path else obj.path_list[index]['Path']
        if data[2] == 'fo':
            await obj.get_path()
        else:
            obj.event.set()
    elif data[1] == 'ps':
        if obj.page_step == int(data[2]):
            return
        obj.page_step = int(data[2])
        await obj.get_path_buttons()
    elif data[1] == 'root':
        obj.path = ''
        await obj.get_path()
    elif data[1] == 'itype':
        obj.item_type = data[2]
        await obj.get_path()
    elif data[1] == 'cur':
        obj.event.set()
    elif data[1] == 'owner':
        obj.config_path = 'rclone.conf'
        obj.path = ''
        obj.remote = ''
        await obj.list_remotes()
    elif data[1] == 'user':
        obj.config_path = obj.user_rcc_path
        obj.path = ''
        obj.remote = ''
        await obj.list_remotes()
    obj.query_proc = False