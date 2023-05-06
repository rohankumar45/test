import hashlib

from aiofiles.os import path as aiopath, makedirs
from os import path as ospath
from pyrogram.filters import command
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message
from time import time

from bot import bot, config_dict, user_data, LOGGER
from bot.helper.ext_utils.bot_utils import get_readable_time, get_readable_file_size, is_media, action, get_date_time, new_task
from bot.helper.ext_utils.force_mode import ForceMode
from bot.helper.ext_utils.fs_utils import clean_target
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import editMessage, sendMessage, sendMedia, auto_delete_message, copyMessage, deleteMessage


@new_task
async def hasher(_, message: Message):
    user_id = message.from_user.id
    reply_to = message.reply_to_message
    tag = message.from_user.mention
    media = None
    isSuperGroup = message.chat.type.name in ['SUPERGROUP', 'CHANNEL']

    fmode = ForceMode(message)
    if config_dict['FSUB'] and (fmsg:= await fmode.force_sub):
        await auto_delete_message(message, fmsg, reply_to)
        return
    if config_dict['FUSERNAME'] and (fmsg:= await fmode.force_username):
        await auto_delete_message(message, fmsg, reply_to)
        return
    if user_data.get(user_id, {}).get('enable_pm') and isSuperGroup and not await fmode.hash_pm_message:
        return

    if not reply_to or reply_to and not (media := is_media(reply_to)):
        msg = await sendMessage(f'{tag}, replying to media or file!', message)
        await auto_delete_message(message, msg)
        return

    VtPath = ospath.join('hash', str(message.from_user.id))
    if not await aiopath.exists(VtPath):
        await makedirs(VtPath)
    hmsg = await sendMessage('<i>Processing media/file...</i>', message)
    try:
        fname, fsize = media.file_name, media.file_size
        outpath = await bot.download_media(message=media, file_name=ospath.join(VtPath, media.file_name))
    except Exception as e:
        LOGGER.error(e)
        await clean_target('hash')
        await editMessage('Error when downloading. Try again later.', hmsg)
        return
    try:
        with open(outpath, 'rb') as f:
            md5 = hashlib.md5()
            sha1 = hashlib.sha1()
            sha224 = hashlib.sha224()
            sha256 = hashlib.sha256()
            sha512 = hashlib.sha512()
            sha384 = hashlib.sha384()
            while chunk := f.read(8192):
                md5.update(chunk)
                sha1.update(chunk)
                sha224.update(chunk)
                sha256.update(chunk)
                sha512.update(chunk)
                sha384.update(chunk)
    except Exception as a:
        LOGGER.info(str(a))
        await clean_target('hash')
        await editMessage('Hashing error. Check Logs.', hmsg)
        return
    msg = '<b>HASH INFO</b>\n'
    msg += f'<code>{fname}</code>\n'
    msg += f'<b>┌ Cc: </b>{tag}\n'
    msg += f'<b>├ ID: </b><code>{message.from_user.id}</code>\n'
    msg += f'<b>├ Size: </b>{get_readable_file_size(fsize)}\n'
    msg += f'<b>├ Elapsed: </b>{get_readable_time(time() - message.date.timestamp())}\n'
    msg += f'<b>├ Action: </b>{action(message)}\n'
    msg += f'<b>├ Add: </b>{get_date_time(message)[0]}\n'
    msg += f'<b>└ At: </b>{get_date_time(message)[1]} ({config_dict["TIME_ZONE_TITLE"]})\n\n'
    msg += f'<b>MD5: </b>\n<code>{md5.hexdigest()}</code>\n'
    msg += f'<b>SHA1: </b>\n<code>{sha1.hexdigest()}</code>\n'
    msg += f'<b>SHA224: </b>\n<code>{sha224.hexdigest()}</code>\n'
    msg += f'<b>SHA256: </b>\n<code>{sha256.hexdigest()}</code>\n'
    msg += f'<b>SHA512: </b>\n<code>{sha512.hexdigest()}</code>\n'
    msg += f'<b>SHA384: </b>\n<code>{sha384.hexdigest()}</code>'
    await deleteMessage(hmsg)
    hash_msg = await sendMedia(msg, message.chat.id, reply_to)
    await clean_target('hash')

    if chat_id := config_dict['OTHER_LOG']:
        await copyMessage(chat_id, hash_msg)

    if user_data.get(user_id, {}).get('enable_pm') and isSuperGroup:
        await copyMessage(user_id, hash_msg)

    if isSuperGroup and (stime:= config_dict['AUTO_DELETE_UPLOAD_MESSAGE_DURATION']):
        await auto_delete_message(message, reply_to, stime=stime)


bot.add_handler(MessageHandler(hasher, filters=command(BotCommands.HashCommand) & CustomFilters.authorized))