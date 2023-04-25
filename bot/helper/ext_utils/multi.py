from asyncio import sleep, Event, wait_for, wrap_future
from functools import partial
from pyrogram import Client
from pyrogram.filters import regex, user
from pyrogram.handlers import CallbackQueryHandler
from pyrogram.types import Message, CallbackQuery

from bot import drive_dict, config_dict
from bot.helper.ext_utils.bot_utils import new_task, new_thread, setInterval
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.message_utils import editMessage, sendMessage


@new_task
async def run_multi(mlist, func, *args):
    client, message, multi, mi, folder_name = mlist
    if multi > 1:
        await sleep(config_dict['MULTI_TIMEGAP'])
        nextmsg = await client.get_messages(message.chat.id, message.reply_to_message.id + 1)
        msg = message.text.split(' ', maxsplit=mi+1)
        if len(msg) == 2 and len(msgauth:= message.text.split('\n')) > 1:
            auth = '\n{}'.format('\n'.join(msgauth[1:]))
        else:
            auth = ''
        msg[mi] = f'{multi - 1}'
        nextmsg = await sendMessage(' '.join(msg) + auth, nextmsg)
        nextmsg = await client.get_messages(message.chat.id, nextmsg.id)
        if folder_name and len(folder_name) > 0:
            args[-1].add(nextmsg.id)
        nextmsg.from_user = message.from_user
        await sleep(4)
        func(client, nextmsg, *args)


class MultiSelect:
    def __init__(self, client: Client, message: Message, from_user, is_gofile: bool=False, enable_go: bool=True):
        self.__client = client
        self.__message = message
        self.__from_user = from_user
        self.__loop = None
        self.__time = 21
        self.__enable_go = enable_go
        self.is_gofile = is_gofile
        self.drive_key = 'Default'
        self.event = Event()

    @new_thread
    async def __event_handler(self):
        pfunc = partial(multi_select_handler, obj=self)
        handler = self.__client.add_handler(CallbackQueryHandler(pfunc, filters=regex('^multi') & user(self.__from_user.id)), group=-1)
        try:
            await wait_for(self.event.wait(), timeout=21)
        except:
            self.path = ''
            self.event.set()
        self.__client.remove_handler(*handler)

    @property
    def text(self):
        msg = f'{self.__from_user.mention}, Choose Category To Upload Your File(s).\n'
        msg += f'Current: <b>{self.drive_key}</b>\n'
        msg += f"GoFile: <b>{'Enable' if self.is_gofile else 'Disable'}</b>\n\n" if config_dict['GOFILE'] and self.__enable_go else '\n'
        msg += f'<i>Timeout: {self.__time}s</i>'
        return msg

    async def __loop_buttons(self):
        self.__time -= 7
        await self.set_buttons()

    async def set_buttons(self):
        buttons = ButtonMaker()
        if config_dict['GOFILE'] and self.__enable_go:
            butkey, butdata = ('✅ GoFile', 'gofile') if self.is_gofile else ('❌ GoFile', 'gofile')
            buttons.button_data(butkey, f'multi {butdata}', 'header')
        data_dict = {x: [x, f'multi {x}'] for x in drive_dict.keys()}
        data_dict[self.drive_key][0] = f'✅ {data_dict[self.drive_key][0]}'
        for btn in data_dict.values():
            buttons.button_data(btn[0], btn[1])
        buttons.button_data('Cancel', f'multi cancel', 'footer')
        buttons.button_data(f'Start ({self.__time}s)', 'multi start', 'footer')
        await editMessage(self.text, self.__message, buttons.build_menu(3))

    async def get_buttons(self):
        future = self.__event_handler()
        await self.set_buttons()
        self.__loop = setInterval(7, self.__loop_buttons)
        await wrap_future(future)
        self.__loop.cancel()
        return drive_dict.get(self.drive_key), self.is_gofile


@new_task
async def multi_select_handler(client: Client, query: CallbackQuery, obj: MultiSelect):
    data = query.data.split()
    print(data)
    if data[1] == 'cancel':
        await query.answer()
        obj.drive_key = ''
        obj.event.set()
    elif data[1] == 'start':
        await query.answer()
        obj.event.set()
    elif data[1] == 'gofile':
        await query.answer()
        obj.is_gofile = not bool(obj.is_gofile)
        await obj.set_buttons()
    else:
        if data[1] == obj.drive_key:
            await query.answer(f'Already selected!', show_alert=True)
        else:
            await query.answer()
            obj.drive_key = data[1]
            await obj.set_buttons()