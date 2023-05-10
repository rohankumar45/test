from pyrogram.errors import UserAlreadyParticipant, InviteHashExpired
from pyrogram.filters import command
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message

from bot import bot, bot_dict, config_dict, LOGGER
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage, auto_delete_message


async def join_chat(_, message: Message):
    reply = message.reply_to_message
    if savebot:= bot_dict['SAVEBOT']:
        args = message.text.split()
        if not reply and len(args) == 1:
            msg = await sendMessage('Please provided a chat join link!', message)
        else:
            link = reply.text.strip() if reply else args[1].strip()
            try:
                await savebot.join_chat(link)
                text = 'Suscessfully joined to chat.'
            except UserAlreadyParticipant:
                text = 'Already joined to chat.'
            except InviteHashExpired:
                text = 'Invite link expired!'
            except Exception as e:
                LOGGER.error(e)
                text = 'Invalid link!'
            msg = await sendMessage(text, message)
    else:
        msg = await sendMessage('Save content mode is disabled!', message)
    await auto_delete_message(message, msg, reply)


bot.add_handler(MessageHandler(join_chat, filters=command(BotCommands.JoinChatCommand) & CustomFilters.authorized))