from pyrogram import Client
from pyrogram.filters import command
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message
from random import choice
from time import time
from waybackpy import Url as wayurl

from bot import bot, config_dict, user_data, LOGGER
from bot.helper.ext_utils.bot_utils import get_readable_time, is_url, action, get_date_time, sync_to_async, get_link, new_task
from bot.helper.ext_utils.force_mode import ForceMode
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import editMessage, sendMessage, auto_delete_message, copyMessage, sendingMessage, deleteMessage


@new_task
async def wayback(_, message: Message):
    user_id = message.from_user.id
    reply_to = message.reply_to_message
    tag = message.from_user.mention
    isSuperGroup = message.chat.type.name in ['SUPERGROUP', 'CHANNEL']
    link = ''
    fmode = ForceMode(message)
    if config_dict['FSUB'] and (fmsg:= await fmode.force_sub):
        await auto_delete_message(message, fmsg, reply_to)
        return
    if config_dict['FUSERNAME'] and (fmsg:= await fmode.force_username):
        await auto_delete_message(message, fmsg, reply_to)
        return
    if user_data.get(user_id, {}).get('enable_pm') and isSuperGroup and not await fmode.wayback_pm_message:
        return
    link = await get_link(message)
    if not is_url(link):
        msg = await sendMessage(f'{tag}, send link along with command or by replying to the link by command', message)
        await auto_delete_message(message, msg)
        return
    mesg = await sendMessage('<i>Processing link...</i>', message)
    wayback_link = await sync_to_async(saveWebPage, link)
    if not wayback_link:
        await editMessage('Cannot archieved. Try again later.', msg)
        return
    msg = 'WAYBACK SAVE\n'
    msg += f'<b>┌ Cc: </b>{tag}\n'
    msg += f'<b>├ ID: </b><code>{user_id}</code>\n'
    msg += f'<b>├ Elapsed: </b>{get_readable_time(time() - message.date.timestamp())}\n'
    msg += f'<b>├ Action: </b>{action(message)}\n'
    msg += f'<b>├ Add: </b>{get_date_time(message)[0]}\n'
    msg += f'<b>├ At: </b>{get_date_time(message)[1]} ({config_dict["TIME_ZONE_TITLE"]})\n'
    msg += f'<b>└ Source Link:</b>\n<code>{link}</code>'
    buttons = ButtonMaker()
    buttons.button_link('Wayback Result', wayback_link)
    await deleteMessage(mesg)
    way_msg = await sendingMessage(msg, message, choice(config_dict['IMAGE_COMPLETE'].split()), buttons.build_menu(1))
    if chat_id := config_dict['OTHER_LOG']:
        await copyMessage(chat_id, way_msg)

    if user_data.get(user_id, {}).get('enable_pm') and isSuperGroup:
        await copyMessage(user_id, way_msg)

    if isSuperGroup and (stime:= config_dict['AUTO_DELETE_UPLOAD_MESSAGE_DURATION']):
        await auto_delete_message(message, reply_to, stime=stime)


def saveWebPage(pageurl: str):
    LOGGER.info(f'Wayback running for: {pageurl}')
    try:
        useragent = ('Mozilla/5.0 (Linux; Android 10; SM-G975F) ', 'AppleWebKit/537.36 (KHTML, like Gecko) ', 'Chrome/81.0.4044.117 Mobile Safari/537.36')
        wayback = wayurl(pageurl, choice(useragent))
        archive = wayback.save()
        LOGGER.info(f'Wayback success for: {pageurl}')
        return archive.archive_url
    except Exception as e:
        LOGGER.error(f'Wayback unsuccess for: {pageurl} ~ {e}')
        return None


bot.add_handler(MessageHandler(wayback, filters=command(BotCommands.WayBackCommand) & CustomFilters.authorized))