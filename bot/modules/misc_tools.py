from aiofiles import open as aiopen
from aiofiles.os import path as aiopath, makedirs
from aiohttp import ClientSession
from asyncio import sleep
from gtts import gTTS
from os import path as ospath
from PIL import Image
from pyrogram.filters import command, regex
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.types import Message, CallbackQuery
from telegraph import upload_file
from urllib.parse import quote_plus

from bot import bot, config_dict, LOGGER
from bot.helper.ext_utils.bot_utils import ButtonMaker, is_premium_user, is_url, sync_to_async, new_task
from bot.helper.ext_utils.fs_utils import clean_target
from bot.helper.ext_utils.genss import GenSS
from bot.helper.ext_utils.help_messages import HelpString
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage, sendMessage, editMessage, deleteMessage, sendPhoto, sendSticker

message_dict = {}

class miscTool:
    def __init__(self, message: Message):
        self.__message = message
        self.__reply_to = message.reply_to_message
        self.__doc = None
        self.__file = ''
        self.__error = ''
        self.lang = 'en'

    async def __get_content(self, url, webss=False):
        self.__error = ''
        async with ClientSession() as session:
            async with session.get(url) as r:
                if r.status == 200:
                    return await r.json()
                else:
                    self.__error = f'Got respons {r.status}'

    async def translator(self, text):
        url = f'https://script.google.com/macros/s/AKfycbyhNk6uVgrtJLEFRUT6y5B2pxETQugCZ9pKvu01-bE1gKkDRsw/exec?q={text}&target={self.lang}'
        return (await self.__get_content(url))['text'].strip()

    async def webss(self, url, mode='webss'):
        if mode == 'webss':
            LOGGER.info(f'Generated Screemshot: {url}')
            url = f'https://webss.yasirapi.eu.org/api?url={url}&width=1080&height=720'
            self.__file = f'Webss_{self.__message.id}.png'
        async with ClientSession() as session:
            async with session.get(url) as r:
                if r.status == 200:
                    async for data in r.content.iter_chunked(1024):
                        async with aiopen(self.__file, 'ba') as f:
                            await f.write(data)
                else:
                    self.__error = f'Got respons {r.status}'
                    return
        return self.__file

    async def vidss(self, url):
        vidss = GenSS(self.__message, url)
        await vidss.ddl_ss()
        if vidss.error:
            self.__error = vidss.error
            return
        self.__file = vidss.rimage
        return vidss

    async def thumb(self, title):
        url = f'https://yasirapi.eu.org/justwatch?q={quote_plus(title)}&locale={self.lang}'
        json_data = await self.__get_content(url)
        if not json_data:
            return
        files, base_dir = [], ospath.join(config_dict['DOWNLOAD_DIR'], f'{self.__message.id}')
        await makedirs(base_dir, exist_ok=True)
        for item in json_data['results']['items']:
            base_name = item['full_path'].rsplit('/', 1)[-1]
            url = f"https://images.justwatch.com/{item['poster'].rsplit('/', 1)[0]}/s592/{base_name}.webp"
            self.__file = ospath.join(base_dir, f'{base_name.title()}.webp')
            await self.webss(url, 'thumb')
            if await aiopath.exists(self.__file):
                img = Image.open(self.__file).convert('RGB')
                png_image = ospath.join(base_dir, f'{base_name.title()}.png')
                img.save(png_image, 'png')
                await clean_target(self.__file)
                files.append(png_image)
        return files, base_dir

    async def pahe_search(self, title):
        url = f'https://yasirapi.eu.org/pahe?q={title}'
        result = (await self.__get_content(url))['result']
        if self.__error:
            return
        return result

    async def image_ocr(self):
        self.__is_image()
        if self.__error:
            return
        self.__file = f'{self.__message.id}.jpg'
        await self.__download_image()
        result = await self.__process_image()
        await self.cleanup()
        return result

    async def image_sticker(self):
        self.__is_image()
        is_image = True
        if self.__error:
            is_image = False
            self.__is_animated()
        if self.__error:
            return
        ext = '.webp' if is_image else '.jpg'
        self.__file = str(self.__message.id) + ext
        await self.__download_image()
        return self.__file

    async def tts(self, text):
        self.__file = f'tts_{self.__message.id}.aac'
        try:
            tts = gTTS(text, lang=self.lang)
            await sync_to_async(tts.save, self.__file)
            return self.__file
        except Exception as err:
            await self.cleanup()
            self.__error =  f'ERROR: <code>{err}</code>'

    async def __process_image(self):
        res = await sync_to_async(upload_file, self.__file)
        self.__url = f'https://telegra.ph{res[0]}'
        url = f'https://script.google.com/macros/s/AKfycbwURISN0wjazeJTMHTPAtxkrZTWTpsWIef5kxqVGoXqnrzdLdIQIfLO7jsR5OQ5GO16/exec?url={self.__url}'
        return (await self.__get_content(url))['text'].strip()

    def __is_animated(self):
        self.__error = ''
        if self.__reply_to.sticker and not self.__reply_to.sticker.is_animated:
            self.__doc = self.__reply_to
        else:
            self.__error = 'ERROR: Invalid reply!'

    def __is_image(self):
        if self.__reply_to.photo:
            self.__doc = self.__reply_to
        elif self.__reply_to.document and 'image' in self.__reply_to.document.mime_type:
            self.__doc = self.__reply_to
        if not self.__doc or self.__reply_to.video:
            self.__error = 'ERROR: Invalid reply!'

    async def cleanup(self, delete=False):
        await clean_target(self.__file)
        if delete:
            del message_dict[self.__message.id]

    async def __download_image(self):
        await self.__doc.download(file_name=f'./{self.__file}')

    @property
    def error(self):
        return self.__error

    @property
    def languages(self):
        return ('af', 'am', 'ar', 'az', 'be', 'bg', 'bn', 'bs', 'ca', 'ceb', 'co', 'cs', 'cy', 'da', 'de', 'el', 'en', 'eo', 'es', 'et', 'eu', 'fa', 'fi', 'fr', \
                'fy', 'ga', 'gd', 'gl', 'gu', 'ha', 'haw', 'hi', 'hmn', 'hr', 'ht', 'hu', 'hy', 'id', 'ig', 'is', 'it', 'iw', 'ja', 'jw', 'ka', 'kk', 'km', 'kn', \
                'ko', 'ku', 'ky', 'la', 'lb', 'lo', 'lt', 'lv', 'mg', 'mi', 'mk', 'ml', 'mn', 'mr', 'ms', 'mt', 'my', 'ne', 'nl', 'no', 'ny', 'pa', 'pl', 'ps', \
                'pt', 'ro', 'ru', 'sd', 'si', 'sk', 'sl', 'sm', 'sn', 'so', 'sq', 'sr', 'st', 'su', 'sv', 'sw', 'ta', 'te', 'tg', 'th', 'tl', 'tr', 'uk', 'ur', 'uz', \
                'vi', 'xh', 'yi', 'yo', 'zh', 'zh_CN', 'zh_TW', 'zu')


async def verify_message(message: Message):
    misc = miscTool(message)
    reply_to = message.reply_to_message
    text = ''
    if reply_to and not reply_to.text:
        await misc.image_ocr()
        if merr:= misc.error:
            return merr, ''
    if len(lang := message.text.split()) != 1:
        if lang[1] in misc.languages:
            misc.lang = lang[1]
    if not text:
        try:
            if reply_to:
                text = reply_to.text.strip()
            elif misc.lang == 'en':
                text = message.text.split(maxsplit=1)[-1]
            else:
                text = message.text.split(maxsplit=2)[-1]
        except:
            return 'Something went wrong', ''
    return text, misc


async def get_button(from_user, mid: int):
    button = ButtonMaker()
    dat_ = f'fun {from_user.id}'
    but_dict = {'OCR': f'{dat_} ocr {mid}',
                'TTS': f'{dat_} tts {mid}',
                'Webss': f'{dat_} wss {mid}',
                'Vidss': f'{dat_} vss {mid}',
                'Pahe': f'{dat_} pahe {mid}',
                'Translate': f'{dat_} tr {mid}',
                'Convert': f'{dat_} conv {mid}',
                'Thumb': f'{dat_} thumb {mid}',
                'Close': f'{dat_} close {mid}'}
    head = f"Task For ~ <b><a href='tg://user?id={from_user.id}'>{from_user.first_name}</a></b>"
    for key, value in but_dict.items():
        button.button_data(key, value)
    return head + HelpString.MISC, button.build_menu(2)


async def misc_tools(_, message: Message):
    if config_dict['PREMIUM_MODE']:
        if not is_premium_user(message.from_user.id):
            await sendMessage('This feature only for <b>Premium User</b>!', message)
            return
    if not message.reply_to_message and len(message.text.split()) == 1:
        await sendMessage('Send command with a message or reply to a message.\n' + HelpString.MISC, message)
        return
    message_dict[message.id] = message
    text, buttons = await get_button(message.from_user, message.id)
    await sendMessage(text, message, buttons)


@new_task
async def misc_callback(_, query: CallbackQuery):
    buttons = ButtonMaker()
    user_id = query.from_user.id
    message = query.message
    data = query.data.split()
    try:
        mid = message.reply_to_message.id
    except:
        try:
            mid = int(data[-1])
        except:
            pass
    omsg = message_dict.get(mid)
    buttons.button_data('<<', f'fun {user_id} back')
    buttons.button_data('Close', f'fun {user_id} close')
    if int(data[1]) != user_id:
        await query.answer('Not Yours!', show_alert=True)
    elif not omsg and data[2] != 'close':
        await query.answer('Old Task!', show_alert=True)
    elif data[2] =='back':
        text, buttons = await get_button(query.from_user, mid)
        await editMessage(text, message, buttons)
    elif data[2] in ['tr', 'tts']:
        await query.answer()
        text = '<i>Translating, please wait...</i>' if data[2] == 'tr' else '<i>Converting, please wait...</i>'
        await editMessage(text, message)
        text, misc = await verify_message(omsg)
        if not misc:
            await editMessage(text, message, buttons.build_menu(2))
            return
        result = await misc.translator(text) if data[2] == 'tr' else await misc.tts(misc.translator(text))
        if data[2] == 'tr':
            await editMessage(f'Translte to -> {misc.lang.upper()}\n\n{result}', message, buttons.build_menu(2))
        else:
            res = await misc.tts(await misc.translator(text))
            if misc.error:
                await editMessage(misc.error, message, buttons.build_menu(2))
            else:
                await deleteMessage(message)
                await message.reply_audio(res, quote=True, reply_to_message_id=omsg.id,
                                          caption=f'Text to Speech -> {misc.lang.upper()}\n\n<b>Original Text:</b>\n<code>{text}</code>')
            await misc.cleanup(True)
    elif data[2] == 'thumb':
        await query.answer()
        await editMessage('<i>Getting thumbnail(s), please wait...</i>', message)
        text, misc = await verify_message(omsg)
        if not misc:
            await editMessage(text, message, buttons.build_menu(2))
            return
        pngs, dirpath = await misc.thumb(text)
        if not pngs:
            await editMessage(f'Failed getting thumbnail for <b>{text.title()}</b>!', message, buttons.build_menu(2))
            return
        await editMessage(f'Sucsesfully generating {len(pngs)} thumbnail poster for {text.title()}. Sending the files...', message)
        for png in pngs:
            await sendPhoto(f'<code>{ospath.basename(png)}</code>', omsg, png)
            if len(pngs) > 1:
                await sleep(5)
        await editMessage(f'Sucsesfully generating {len(pngs)} thumbnail poster for {text.title()}.', message, buttons.build_menu(2))
        await clean_target(dirpath)
    elif data[2] == 'pahe':
        await query.answer()
        await editMessage('<i>Processing pahe search...</i>', message)
        text, misc = await verify_message(omsg)
        if not misc or is_url(text):
            await editMessage('Send valid title!', message, buttons.build_menu(2))
            return
        await editMessage(f'<i>Searching <b>{text.title()}</b>, please wait...</i>', message)
        result = await misc.pahe_search(text)
        head = ''
        if len(result) == 0:
            result =f'Not found Pahe search for <b>{text.title()}</b>'
        elif not misc.error:
            head = f'<b>Search Pahe For {text.upper()}</b>\n\n'
            result = ''.join(f"{count}. <a href=\'{x['link']}\'>{x['judul']}</a>\n" for count, x in enumerate(result, start=1))
        await editMessage(head + result, message, buttons.build_menu(2))
    elif data[2] in ['wss', 'vss']:
        text, misc = await verify_message(omsg)
        if not misc or not text.startswith('http') or not is_url(text):
            await query.answer('SS utils only for url/link!', show_alert=True)
            return
        await query.answer()
        await editMessage('<i>Generated screenshot, please wait...</i>', message)
        ssbuttons = ButtonMaker()
        ssbuttons.button_link('Source', text)
        if data[2] == 'wss':
            photo = await misc.webss(text)
            caption = 'Web Screenshot Generated.'
        else:
            vssres = await misc.vidss(text)
            if vssres:
                photo = vssres.rimage
                caption = f'Video Screenshot Generated:\n<code>{vssres.name}</code>'
        if misc.error:
            await editMessage(misc.error, message, buttons.build_menu(2))
            return
        await sendPhoto(caption, omsg, photo, ssbuttons.build_menu(1))
        await deleteMessage(message)
        await misc.cleanup(True)
    elif data[2] == 'ocr':
        if not (reply:= omsg.reply_to_message) or reply.text or reply.video:
            await query.answer('Upss, reply to a photo!', show_alert=True)
            return
        await query.answer()
        await editMessage('<i>Generate text, please wait...</i>', message)
        misc = miscTool(omsg)
        result = await misc.image_ocr()
        await editMessage(misc.error or f'OCR Result:\n\n{result}', message, buttons.build_menu(2))
    elif data[2] == 'conv':
        if not (reply:= omsg.reply_to_message) or reply.text or reply.video:
            await query.answer('Upss, reply to a photo or static sticker!', show_alert=True)
            return
        await query.answer()
        misc = miscTool(omsg)
        res = await misc.image_sticker()
        if misc.error:
            await editMessage(misc.error, message, buttons.build_menu(2))
        else:
            await deleteMessage(message)
            if res.endswith('.jpg'):
                await sendPhoto('', omsg, res)
            else:
                await sendSticker(res, omsg, True)
            await misc.cleanup(True)
    else:
        if omsg:
            del message_dict[omsg.id]
        await deleteMessage(message, message.reply_to_message, omsg.reply_to_message if omsg else None)


bot.add_handler(MessageHandler(misc_tools, filters=command(BotCommands.MiscCommand) & CustomFilters.authorized))
bot.add_handler(CallbackQueryHandler(misc_callback, filters=regex('^fun')))