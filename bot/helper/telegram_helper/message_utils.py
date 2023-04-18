from aiofiles import open as aiopen
from aiofiles.os import path as aiopath
from aiohttp import ClientSession
from asyncio import sleep, gather
from datetime import datetime, timedelta
from pyrogram.errors import FloodWait
from pyrogram.types import Message, InlineKeyboardMarkup, InputMediaPhoto, ChatPermissions
from time import time

from bot import bot, bot_loop, Interval, status_reply_dict, status_reply_dict_lock, config_dict, download_dict_lock, LOGGER
from bot.helper.ext_utils.bot_utils import get_readable_message, setInterval, sync_to_async
from bot.helper.ext_utils.fs_utils import clean_target


async def sendingMessage(text: str, message: Message, photo, reply_markup: InlineKeyboardMarkup=None):
    if config_dict['ENABLE_IMAGE_MODE']:
        return await sendPhoto(text, message, photo, reply_markup)
    else:
        return await sendMessage(text, message, reply_markup)


async def sendMessage(text: str, message: Message, reply_markup: InlineKeyboardMarkup = None):
    try:
        return await message.reply_text(text=text, reply_markup=reply_markup, disable_notification=True,
                                        disable_web_page_preview=True, quote=True)
    except FloodWait as f:
        LOGGER.warning(f)
        await sleep(f.value * 1.2)
        return await sendMessage(text, message, reply_markup)
    except Exception as e:
        LOGGER.error(e)


async def sendMedia(caption: str, chat_id: int, reply_to: Message, reply_markup: InlineKeyboardMarkup=None):
    try:
        return await reply_to.copy(chat_id, caption, reply_markup=reply_markup, disable_notification=True)
    except FloodWait as f:
        LOGGER.warning(f)
        await sleep(f.value * 1.2)
        return await sendMedia(caption, bot, chat_id, reply_to, reply_markup)
    except Exception as e:
        LOGGER.error(e)


async def sendSticker(fileid: str, message: Message, is_misc=False):
    try:
        msgsticker = await message.reply_sticker(fileid, quote=True, disable_notification=True)
        if not is_misc:
            if DLS:= config_dict['STICKER_DELETE_DURATION']:
                bot_loop.create_task(auto_delete_message(msgsticker, stime=DLS))
    except FloodWait as f:
        LOGGER.warning(f)
        await sleep(f.value * 1.2)
        return await sendSticker(fileid, message, is_misc)
    except Exception as e:
        LOGGER.error(e)


async def sendCustom(text: str, chat_id: int, reply_markup: InlineKeyboardMarkup = None):
    try:
        return await bot.send_message(chat_id, text, reply_markup=reply_markup, disable_notification=True)
    except FloodWait as f:
        LOGGER.warning(f)
        await sleep(f.value * 1.2)
        return await sendCustom(text, chat_id, reply_markup)
    except Exception as e:
        LOGGER.error(e)


async def editCustom(text: str, chat_id: int, message_id: int, reply_markup=None):
    try:
        return await bot.edit_message_text(chat_id, message_id, text, reply_markup=reply_markup, disable_web_page_preview=True)
    except FloodWait as f:
        LOGGER.warning(f)
        await sleep(f.value * 1.2)
        return await editCustom(text, chat_id, message_id, reply_markup)
    except Exception as e:
        LOGGER.error(e)


async def editMessage(text: str, message: Message, reply_markup=None):
    try:
        return await message.edit_text(text, reply_markup=reply_markup, disable_web_page_preview=True)
    except FloodWait as f:
        LOGGER.warning(f)
        await sleep(f.value * 1.2)
        return await editMessage(text, message, reply_markup)
    except Exception as e:
        LOGGER.error(e)
        return str(e)


async def copyMessage(chat_id: int, message: Message, reply_markup: InlineKeyboardMarkup=None):
    try:
        return await message.copy(chat_id, disable_notification=True,
                                  reply_markup=reply_markup or message.reply_markup)
    except FloodWait as f:
        LOGGER.warning(f)
        await sleep(f.value * 1.2)
        return await copyMessage(chat_id, message, reply_markup)
    except Exception as e:
        LOGGER.error(e)


async def sendRss(text: str):
    return await sendCustom(text, config_dict['RSS_CHAT_ID'])


async def sendPhoto(caption: str, message: Message, photo, reply_markup: InlineKeyboardMarkup = None):
    try:
        return await message.reply_photo(photo, True, caption, reply_markup=reply_markup, disable_notification=True)
    except FloodWait as f:
        LOGGER.warning(f)
        await sleep(f.value * 1.2)
        return await sendPhoto(caption, message, photo, reply_markup)
    except Exception as e:
        LOGGER.error(e)


async def editPhoto(caption: str, message: Message, photo, reply_markup: InlineKeyboardMarkup = None):
    try:
        return await message.edit_media(InputMediaPhoto(photo, caption), reply_markup)
    except FloodWait as f:
        LOGGER.warning(f)
        await sleep(f.value * 1.2)
        return await editPhoto(caption, message, photo, reply_markup)
    except Exception as err:
        LOGGER.error(err)


async def deleteMessage(*args: Message):
    msgs = [msg.delete() for msg in args if msg]
    await gather(*msgs, return_exceptions=True)


async def sendFile(message: Message, doc: str, caption: str ='', thumb=None):
    try:
        thumbnail = None
        if thumb:
            async with ClientSession() as session:
                async with session.get(thumb) as r:
                    if r.status == 200:
                        async for data in r.content.iter_chunked(1024):
                            async with aiopen('thumb.png', 'ba') as f:
                                await f.write(data)
            if await aiopath.exists('thumb.png'):
                thumbnail = 'thumb.png'
        await message.reply_document(doc, caption=caption, quote=True, thumb=thumbnail)
        for file in [doc, 'thumb.png']:
            if file != 'log.txt':
                await clean_target(file)
    except FloodWait as f:
        LOGGER.warning(f)
        await sleep(f.value * 1.2)
        return await sendFile(message, doc, caption, thumb)
    except Exception as e:
        LOGGER.error(e)


async def auto_delete_message(*args, stime=config_dict['AUTO_DELETE_MESSAGE_DURATION']):
    if stime:
        await sleep(stime)
        await deleteMessage(*args)


async def delete_all_messages():
    async with status_reply_dict_lock:
        for key, data in list(status_reply_dict.items()):
            try:
                del status_reply_dict[key]
                await deleteMessage(data[0])
            except Exception as e:
                LOGGER.error(e)


async def update_all_messages(force=False):
    async with status_reply_dict_lock:
        if not status_reply_dict or not Interval or (not force and time() - list(status_reply_dict.values())[0][1] < 3):
            return
        for chat_id in list(status_reply_dict.keys()):
            status_reply_dict[chat_id][1] = time()
    async with download_dict_lock:
        msg, buttons = await sync_to_async(get_readable_message)
    if msg:
        async with status_reply_dict_lock:
            for chat_id in list(status_reply_dict.keys()):
                if status_reply_dict[chat_id] and msg != status_reply_dict[chat_id][0].text:
                    rmsg = await editMessage(msg, status_reply_dict[chat_id][0], buttons)
                    if isinstance(rmsg, str) and rmsg.startswith('Telegram says: [400'):
                        del status_reply_dict[chat_id]
                        continue
                    status_reply_dict[chat_id][0].text = msg
                    status_reply_dict[chat_id][1] = time()


async def sendStatusMessage(msg):
    async with download_dict_lock:
        progress, buttons = await sync_to_async(get_readable_message)
    if progress:
        async with status_reply_dict_lock:
            chat_id = msg.chat.id
            if chat_id in list(status_reply_dict.keys()):
                message = status_reply_dict[chat_id][0]
                await deleteMessage(message)
                del status_reply_dict[chat_id]
            message = await sendMessage(progress, msg, buttons)
            message.text = progress
            status_reply_dict[chat_id] = [message, time()]
            if not Interval:
                Interval.append(setInterval(config_dict['STATUS_UPDATE_INTERVAL'], update_all_messages))


async def startRestrict(message: Message):
    try:
        await bot.restrict_chat_member(message.chat.id,
                                       message.from_user.id,
                                       ChatPermissions(can_send_messages=False),
                                       datetime.now() + timedelta(seconds=config_dict['AUTO_MUTE_DURATION']))
    except Exception as err:
        LOGGER.error(f'[MuteUser] Error: {err}')