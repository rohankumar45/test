from aiofiles import open as aiopen
from aiohttp import ClientSession
from argparse import ArgumentParser
from asyncio import sleep
from bs4 import BeautifulSoup
from functools import partial
from pyrogram.filters import command, regex, user
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.types import Message, CallbackQuery
from random import choice
from re import sub as resub
from time import time

from bot import bot, config_dict, user_data
from bot.helper.ext_utils.bot_utils import get_readable_time, is_premium_user, get_link, is_media, action, get_date_time, new_task, new_thread, is_url, is_magnet
from bot.helper.ext_utils.force_mode import ForceMode
from bot.helper.ext_utils.index_scrape import index_scrapper
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import auto_delete_message, sendMedia, sendMessage, copyMessage, deleteMessage, editMessage, sendingMessage


class ScrapeHelper():
    def __init__(self, message: Message, editabale: Message, link: str, scrapfile=False):
        self.message = message
        self.__editabale = editabale
        self.__scrapfile = scrapfile
        self.__user_id = message.from_user.id
        self.__isSuperGroup = message.chat.type.name in ['SUPERGROUP', 'CHANNEL']
        self.__pm = user_data.get(self.__user_id, {}).get('enable_pm')
        self.__buttons = None
        self.__done = False
        self.reply_to = message.reply_to_message
        self.link = link
        self.is_cancelled = False

    @new_thread
    async def __event_handler(self):
        pfunc = partial(stop_scrapper, obj=self)
        handler = bot.add_handler(CallbackQueryHandler(pfunc, filters=regex('^scrap') & user(self.__user_id)), group=-1)
        while not self.is_cancelled or not self.__done:
            await sleep(0.5)
        bot.remove_handler(*handler)

    async def __OnScrapSuccess(self, totals: int, mode: str):
        self.__done = True
        log_msg = '<b>SCRAPPER LOGS</b>\n'
        log_msg += f'<b>┌ Cc: </b>{self.message.from_user.mention}\n'
        log_msg += f'<b>├ ID: </b><code>{self.__user_id}</code>\n'
        log_msg += f'<b>├ Action: </b>{action(self.message)}\n'
        log_msg += f"<b>├ Status: </b>#{'cancelled' if self.is_cancelled else 'done'}\n"
        log_msg += mode
        log_msg += f'<b>├ Add: </b>{get_date_time(self.message)[0]}\n'
        log_msg += f'<b>├ At: </b>{get_date_time(self.message)[1]} ({config_dict["TIME_ZONE_TITLE"]})\n'
        log_msg += f'<b>├ Elapsed: </b>{get_readable_time(time() - self.message.date.timestamp())}\n'
        log_msg += f'<b>└ Total Link: </b>{totals} Link'
        await deleteMessage(self.__editabale)
        buttons = ButtonMaker()
        buttons.button_link('Source Link', self.link)
        if self.__scrapfile:
            msg_scrap = await sendMedia(log_msg, self.message.chat.id, self.reply_to)
        else:
            msg_scrap = await sendingMessage(log_msg, self.message, choice(config_dict['IMAGE_COMPLETE'].split()), buttons.build_menu(1))
        if self.__pm and self.__isSuperGroup:
            await copyMessage(self.__user_id, msg_scrap)
        if chat_id := config_dict['OTHER_LOG']:
            await copyMessage(chat_id, msg_scrap)
        if self.__isSuperGroup and (stime:= config_dict['AUTO_DELETE_UPLOAD_MESSAGE_DURATION']):
            await auto_delete_message(self.message, self.reply_to, stime=stime)

    async def OnScrapError(self, error=None):
        self.__done = True
        if not error:
            error = f'''
<b>Send link along with command line:</b>
<code>/{BotCommands.ScrapperCommand}</code> (Link) -au username -ap password\n
<b>By replying to link/txt file:</b>
<code>/{BotCommands.ScrapperCommand}</code> -au username -ap password\n

<b>Current Support:
┌ Index link
├ TXT file (.txt)
├ Torrent Site
├ <a href='https://www.animeremux.xyz/'>Animeremux</a>
├ <a href='https://atishmkv.bond/'>Atishmkv</a>
└ <a href='https://cinevood.bio/'>Cinevood</a>

None: Auth and pass ONLY for index link
'''
        await editMessage(error, self.__editabale)
        await auto_delete_message(self.message, self.__editabale, self.reply_to)

    async def __resp(self, url):
        async with ClientSession() as session:
            async with session.get(url) as r:
                return await r.read()

    async def __tasks_buttons(self, index, links):
        if not self.__buttons:
            buttons = ButtonMaker()
            buttons.button_data('Stop', 'scrap stop')
            self.__buttons = buttons.build_menu(1)
        await editMessage(f'Executing {index}/{len(links)} result(s)...\nClick stop button to cancel send scrapping result(s).', self.__editabale, self.__buttons)

    async def anime_remux(self):
        self.__event_handler()
        links = BeautifulSoup(await self.__resp(self.link), 'html.parser').select("a[href*='urlshortx.com']")
        if links:
            index = 1
            mode = '<b>├ Mode: </b>Animeremux\n'
            for x in links:
                lnk = x['href'].split('url=')[-1]
                if lnk:
                    title = BeautifulSoup(await self.__resp(lnk), 'html.parser').title
                    isize = x.text.index('[')
                    await self.__tasks_buttons(index, links)
                    msg = await sendMessage(f'{index}. <b>{title.text} ~ {x.text[isize:]}</b>\n<code>{lnk}</code>', self.message)
                    if self.__pm and self.__isSuperGroup:
                        await copyMessage(self.__user_id , msg)
                    if self.is_cancelled:
                        mode += f'<b>├ Executed: </b>{index} Link\n'
                        break
                    index += 1
                    await sleep(5)
            await self.__OnScrapSuccess(len(links), mode)
        else:
            await self.OnScrapError('ERROR: Can\'t find any link!')

    async def atishmkv(self):
        self.__event_handler()
        soup = BeautifulSoup(await self.__resp(self.link), 'html.parser').select("a[href^='https://gdflix.lol/file']")
        links = [a['href'] for a in soup]
        if links:
            mode = '<b>├ Mode: </b>Atishmkv\n'
            for index, link in enumerate(links, 1):
                await self.__tasks_buttons(index, links)
                title = BeautifulSoup(await self.__resp(link), 'html.parser').title.string
                title = resub(r'GDFlix \| ', '', title)
                msg = await sendMessage(f'{index}. <b>{title}</b>\n<code>{link}</code>', self.message)
                if self.__pm and self.__isSuperGroup:
                    await copyMessage(self.__user_id , msg)
                if self.is_cancelled:
                    mode += f'<b>├ Executed: </b>{index} Link\n'
                    break
                await sleep(5)
            await self.__OnScrapSuccess(len(links), mode)
        else:
            await self.OnScrapError('ERROR: Can\'t find any link!')

    async def cinevood(self):
        self.__event_handler()
        soup = BeautifulSoup(await self.__resp(self.link), 'html.parser')
        gdflixs = [a['href'] for a in soup.select("a[href^='https://gdflix.lol/file']")]
        filepress = [x['href'] for x in soup.select("a[href^='https://filepress.click/file']")]
        links = list(zip(gdflixs, filepress))
        if links:
            mode = '<b>├ Mode: </b>Cinevood\n'
            for index, (gdflix, fpress) in enumerate(links, 1):
                await self.__tasks_buttons(index, links)
                title = BeautifulSoup(await self.__resp(gdflix), 'html.parser').title.string
                title = resub(r'GDFlix \| ', '', title)
                msg = await sendMessage(f'{index}. <b>{title}</b>\n<code>{gdflix}\n{fpress}</code>', self.message)
                if self.__pm and self.__isSuperGroup:
                    await copyMessage(self.__user_id , msg)
                if self.is_cancelled:
                    mode += f'<b>├ Executed: </b>{index} Link\n'
                    break
                await sleep(5)
            await self.__OnScrapSuccess(len(links), mode)
        else:
            await self.OnScrapError('ERROR: Can\'t find any link!')

    async def manget(self, args: ArgumentParser):
        self.__event_handler()
        soup = BeautifulSoup(await self.__resp(self.link), 'html.parser').select("a[href^='magnet:?xt=urn:btih:']")
        links = [link['href'] for link in soup]
        if links:
            mode = '<b>├ Mode: </b>Magnet\n'
            for index, link in enumerate(links, 1):
                await self.__tasks_buttons(index, links)
                msg = await sendMessage(f'<code>{link}</code>', self.message)
                if self.__pm and self.__isSuperGroup:
                    await copyMessage(self.__user_id , msg)
                if self.is_cancelled:
                    mode += f'<b>├ Executed: </b>{index} Link\n'
                    break
                await sleep(5)
            await self.__OnScrapSuccess(len(links), mode)
        else:
            ussr, pssw = ' '.join(args.auth_user).strip(), ' '.join(args.auth_pswd).strip()
            links = await index_scrapper(self.link, ussr, pssw)
            if 'wrong' in links:
                await self.OnScrapError(links)
                return
            if links:
                mode = '<b>├ Mode: </b>Index\n'
                for index, link in enumerate(links, 1):
                    await self.__tasks_buttons(index, links)
                    msg = await sendMessage(f'<code>{link}</code>', self.message)
                    if self.__pm and self.__isSuperGroup:
                        await copyMessage(self.__user_id , msg)
                    if self.is_cancelled:
                        mode += f'<b>├ Executed: </b>{index} Link\n'
                        break
                    await sleep(5)
                await self.__OnScrapSuccess(len(links), mode)
            else:
                await self.OnScrapError('ERROR: Can\'t find any link!')

    async def txt_file(self):
        self.__event_handler()
        start, end = 0, 1000
        file = self.reply_to.document
        is_text = file.file_name
        if not is_text.endswith('.txt'):
            await self.OnScrapError('Only for document/file (.txt).')
            return
        await self.reply_to.download(file_name='./links.txt')
        async with aiopen('links.txt', 'r+') as f:
            lines = await f.readlines()
        links = [x.strip() for x in lines[start:end] if is_url(x.strip()) or is_magnet(x.strip())]
        if links:
            mode = '<b>├ Mode: </b>TXT File\n'
            for index, link in enumerate(links, 1):
                await self.__tasks_buttons(index, links)
                msg = await sendMessage(f'<code>{link}</code>', self.message)
                if self.__pm and self.__isSuperGroup:
                    await copyMessage(self.__user_id , msg)
                if self.is_cancelled:
                    mode += f'<b>├ Executed: </b>{index} Link\n'
                    break
                await sleep(5)
            await self.__OnScrapSuccess(len(links), mode)
        else:
            await self.OnScrapError('ERROR: Can\'t find any link!')


@new_task
async def scrapper(_, message: Message):
    try:
        args = parser.parse_args(message.text.split('\n')[0].split()[1:])
    except:
        await sendMessage('Invalid argument, reply to link or .txt file.', message)
        return

    user_id = message.from_user.id
    user_dict = user_data.get(user_id, {})
    if config_dict['PREMIUM_MODE']:
        if not is_premium_user(message.from_user.id):
            await sendMessage(f'{message.from_user.mention}, This feature only for <b>Premium User</b>!', message)
            return

    isFile = False
    reply_to = message.reply_to_message

    fmode = ForceMode(message)
    if config_dict['FSUB'] and (fmsg:= await fmode.force_sub):
        await auto_delete_message(message, fmsg, reply_to)
        return
    if config_dict['FUSERNAME'] and (fmsg:= await fmode.force_username):
        await auto_delete_message(message, fmsg, reply_to)
        return
    if user_dict.get('enable_pm') and message.chat.type.name in ['SUPERGROUP', 'CHANNEL'] and not await fmode.scrapper_pm_message:
        return
    if reply_to and is_media(reply_to):
        isFile = True
    else:
        link = await get_link(message)
    editabale = await sendMessage(f"<i>Scrapping {'file' if isFile else 'link'}, please wait...</i>", message)
    scrape = ScrapeHelper(message, editabale, link, isFile)
    if isFile:
        await scrape.txt_file()
    elif is_url(link):
        if 'animeremux' in link:
            await scrape.anime_remux()
        elif 'atishmkv' in link:
            await scrape.atishmkv()
        elif 'cinevood' in link:
            await scrape.cinevood()
        else:
            await scrape.manget(args)
    else:
        await scrape.OnScrapError()


async def stop_scrapper(_, query: CallbackQuery, obj: ScrapeHelper):
    await query.answer('Trying to stop...')
    obj.is_cancelled = True


parser = ArgumentParser(description='Scrape args usage:', argument_default='')

parser.add_argument('link', nargs='*')
parser.add_argument('-au', nargs='+', dest='auth_user')
parser.add_argument('-ap', nargs='+', dest='auth_pswd')


bot.add_handler(MessageHandler(scrapper, filters=command(BotCommands.ScrapperCommand) & CustomFilters.authorized))