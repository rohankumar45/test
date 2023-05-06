from math import ceil
from asyncio import Lock

from bot.helper.telegram_helper.button_build import ButtonMaker


content_dict = {}


class TeleContent:
    def __init__(self, message, key=None, max=8):
        self.key = key
        self.__message = message
        self.__max = max
        self.__start = 0
        self.__lock = Lock()

    @property
    def reply(self):
        return self.__message.reply_to_message

    @property
    def pages(self):
        return self.__pages

    async def set_data(self, content, cap):
        if len(content) < 100:
            content = [x[1:] for x in content]
        self.__content = content
        self.__cap = cap
        self.__count = 0
        self.__page_no = 1
        self.__pages = ceil(len(self.__content) / self.__max)

    async def __prepare_data(self, data, fdata):
        if data == 'nex':
            if self.__page_no == self.__pages:
                self.__count = 0
                self.__page_no = 1
            else:
                self.__count += self.__max
                self.__page_no += 1
        elif data == 'pre':
            if self.__page_no == 1:
                self.__count = self.__max * (self.__pages - 1)
                self.__page_no = self.__pages
            else:
                self.__count -= self.__max
                self.__page_no -= 1
        elif data == 'foot':
            if fdata == self.__start or fdata == self.__count:
                return f'Already in page {self.__page_no}!'
            self.__start = fdata
            self.__count = self.__start
            if  self.__start / self.__max == 0:
                self.__page_no = 1
            else:
                self.__page_no = int(self.__start / self.__max) + 1

        if self.__page_no > self.__pages and self.__pages != 0:
            self.__count -= self.__max
            self.__page_no -= 1

    async def get_content(self, pattern, data=None, fdata=None):
        if pre := await self.__prepare_data(data, fdata):
            return pre, None
        buttons = ButtonMaker()
        async with self.__lock:
            text, mid, user_id = '', self.__message.id, self.__message.from_user.id
            task = len(self.__content)
            for index, r_data in enumerate(self.__content[self.__count:], start=1):
                text += r_data
                if index == self.__max:
                    break
            if task > self.__max:
                buttons.button_data('<<', f'{pattern} {user_id} pre {mid}')
                buttons.button_data(f'{self.__page_no}/{self.__pages}', f'{pattern} {user_id} page {mid}')
                buttons.button_data('>>', f'{pattern} {user_id} nex {mid}')
            buttons.button_data('Close', f'{pattern} {user_id} close {mid}')
            if self.__pages >= 5:
                for x in range(0, task, self.__max):
                    buttons.button_data(int(x/self.__max) + 1, f'{pattern} {user_id} foot {mid} {x}', position='footer')
            text += f'▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n{self.__cap}'
            return text, buttons.build_menu(3)