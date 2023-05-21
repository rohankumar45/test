from asyncio import sleep
from html_telegraph_poster import TelegraphPoster, upload_image
from random import SystemRandom
from string import ascii_letters
from telegraph.aio import Telegraph
from telegraph.exceptions import RetryAfterError

from bot import bot_loop, config_dict, LOGGER


class TelegraphHelper:
    def __init__(self, author_name=None, author_url=None):
        self.telegraph = Telegraph(domain='graph.org')
        self.short_name = ''.join(SystemRandom().choices(ascii_letters, k=8))
        self.access_token = None
        self.author_name = author_name
        self.author_url = author_url

    async def create_account(self):
        await self.telegraph.create_account(short_name=self.short_name, author_name=self.author_name, author_url=self.author_url)
        self.access_token = self.telegraph.get_access_token()
        LOGGER.info('Creating Telegraph Account')

    async def create_page(self, title, content):
        try:
            return await self.telegraph.create_page(title=title, author_name=self.author_name, author_url=self.author_url, html_content=content)
        except RetryAfterError as st:
            LOGGER.warning(f'Telegraph Flood control exceeded. I will sleep for {st.retry_after} seconds.')
            await sleep(st.retry_after)
            return await self.create_page(title, content)

    async def edit_page(self, path, title, content):
        try:
            return await self.telegraph.edit_page(path=path, title=title, author_name=self.author_name, author_url=self.author_url, html_content=content)
        except RetryAfterError as st:
            LOGGER.warning(f'Telegraph Flood control exceeded. I will sleep for {st.retry_after} seconds.')
            sleep(st.retry_after)
            return await self.edit_page(path, title, content)

    async def edit_telegraph(self, path, telegraph_content):
        nxt_page = 1
        prev_page = 0
        num_of_path = len(path)
        for content in telegraph_content :
            if nxt_page == 1 :
                content += f'<b><a href="https://telegra.ph/{path[nxt_page]}">Next</a></b>'
                nxt_page += 1
            else :
                if prev_page <= num_of_path:
                    content += f'<b><a href="https://telegra.ph/{path[prev_page]}">Prev</a></b>'
                    prev_page += 1
                if nxt_page < num_of_path:
                    content += f'<b> | <a href="https://telegra.ph/{path[nxt_page]}">Next</a></b>'
                    nxt_page += 1
            await self.edit_page(path = path[prev_page], title=config_dict['TSEARCH_TITLE'], content=content)
        return


class TelePost:
    def __init__(self, title='telegraph'):
        self.__title = title

    def __create_telegraph(self):
        if self.__metadata:
            try:
                telegraph = TelegraphPoster(use_api=True, telegraph_api_url='https://api.graph.org')
                telegraph.create_api_token('Telegraph')
                page = telegraph.post(title=self.__title,
                                    author=config_dict['AUTHOR_NAME'],
                                    author_url=config_dict['AUTHOR_URL'],
                                    text=self.__metadata)
                return page['url']
            except Exception as e:
                LOGGER.error(e)

    def image_post(self, image):
        result = []
        try:
            if isinstance(image, list):
                for img in image:
                    result.append(upload_image(img))
            else:
                result.append(upload_image(image))
            return result
        except: pass

    def create_post(self, metadata):
        self.__metadata = metadata
        return self.__create_telegraph()


telegraph = TelegraphHelper(config_dict['AUTHOR_NAME'], config_dict['AUTHOR_URL'])


bot_loop.create_task(telegraph.create_account())