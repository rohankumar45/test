from pyrogram import Client
from pyrogram.filters import command
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message
from random import choice
from time import time

from bot import bot, config_dict, user_data
from bot.helper.ext_utils.bot_utils import get_readable_time, is_gdrive_link, is_media, get_date_time, action, get_link, sync_to_async, new_task, get_readable_file_size
from bot.helper.ext_utils.force_mode import ForceMode
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import deleteMessage, sendMessage, sendingMessage, sendSticker, auto_delete_message, copyMessage


@new_task
async def countNode(client: Client, message: Message):
    buttons = ButtonMaker()
    user_id = message.from_user.id
    reply_to = message.reply_to_message
    tag = message.from_user.mention
    args = message.text.split()
    isSuperGoup = message.chat.title in ['SUPERGROUP', 'CHANNEL']
    link = ''
    fmode = ForceMode(message)
    if config_dict['FSUB'] and (fmsg:= await fmode.force_sub):
        await auto_delete_message(message, fmsg, reply_to)
        return
    if config_dict['FUSERNAME'] and (fmsg:= await fmode.force_username):
        await auto_delete_message(message, fmsg, reply_to)
        return
    if user_data.get(user_id, {}).get('enable_pm') and isSuperGoup and not await fmode.clone_pm_message:
        return
    if len(args) > 1:
        link = args[1]
    if reply_to:
        if not reply_to.from_user.is_bot:
            tag = reply_to.from_user.mention
        if not is_media(reply_to) and len(link) == 0:
            link = reply_to.text.split(maxsplit=1)[0].strip()

    if is_gdrive_link(link):
        TIME_ZONE_TITLE = config_dict['TIME_ZONE_TITLE']
        dt_date, dt_time = get_date_time(message)
        msg = await sendMessage(f'<i>Counting:</i> <code>{link}</code>', message)
        name, mime_type, size, files, folders = await sync_to_async(GoogleDriveHelper().count, link)
        await deleteMessage(msg)
        if 'not found' in name or not mime_type:
            text = f'<b>{name}</b>\n'
            text += f'<b>┌ Elapsed: </b>{get_readable_time(time() - message.date.timestamp())}\n'
        else:
            text = f'<code>{name}</code>\n'
            text += f'<b>┌ Size: </b>{get_readable_file_size(size)}\n'
            text += f'<b>├ Type: </b>{mime_type}\n'
            if mime_type == 'Folder':
                text += f'<b>├ SubFolders: </b>{folders}\n'
                text += f'<b>├ Files: </b>{files}\n'
            text += f'<b>├ Elapsed: </b>{get_readable_time(time() - message.date.timestamp())}\n'
        text += f'<b>├ Action: </b>{action(message)}\n'
        text += f'<b>├ Cc: </b>{tag}\n'
        text += f'<b>├ Add: </b>{dt_date}\n'
        text += f'<b>└ At: </b>{dt_time} ({TIME_ZONE_TITLE})'
        scr_link = await get_link(message)
        if config_dict['SOURCE_LINK']:
            buttons.button_link('Source', scr_link)
        msg = await sendingMessage(text, message, choice(config_dict['IMAGE_COMPLETE'].split()), buttons.build_menu(2))
        if STICKERID_COUNT:= config_dict['STICKERID_COUNT']:
            await sendSticker(STICKERID_COUNT, message)
        if user_data.get(user_id, {}).get('enable_pm') and isSuperGoup:
            await copyMessage(user_id, msg)
    else:
        countmsg = 'Send <b>GDrive</b> link along with command or by replying to the link by command'
        if config_dict['AUTO_MUTE'] and isSuperGoup:
            if fmsg:= await fmode.auto_muted(countmsg):
                await auto_delete_message(message, fmsg, reply_to)
                return
        else:
            msg = await sendMessage(countmsg, message)
    if reply_to and isSuperGoup and (stime:= config_dict['AUTO_DELETE_UPLOAD_MESSAGE_DURATION']):
        await auto_delete_message(message, msg, reply_to, stime=stime)


bot.add_handler(MessageHandler(countNode, filters=command(BotCommands.CountCommand) & CustomFilters.authorized))
