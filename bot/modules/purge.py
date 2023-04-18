from pyrogram import Client
from pyrogram.filters import command
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message
from time import time

from bot import bot, LOGGER
from bot.helper.ext_utils.bot_utils import get_readable_time, new_task
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage, deleteMessage


@new_task
async def purge_message(client: Client, message: Message):
    reply_to = message.reply_to_message
    msg = await sendMessage('<i>Deleting message, please wait..</i>', message)
    if not reply_to:
        await editMessage('Reply to a message to purge from.', msg)
        return
    del_msg = 0
    for mid in range(reply_to.id, message.id):
        try:
            await bot.delete_messages(message.chat.id, mid)
            del_msg += 1
        except:
            pass
    text = f'Successfully deleted {del_msg} message in {get_readable_time(time() - message.date.timestamp())}.' if del_msg != 0 else 'No message deleted.'
    await deleteMessage(message)
    LOGGER.info(f'Purge {del_msg} message.')
    await editMessage(text, msg)


bot.add_handler(MessageHandler(purge_message, filters=command(BotCommands.PurgeCommand) & CustomFilters.owner))