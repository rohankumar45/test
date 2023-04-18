from pyrogram import Client
from pyrogram.filters import command
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message

from bot import bot, alive, config_dict
from bot.helper.ext_utils.bot_utils import new_task
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage


@new_task
async def sleep(client: Client, message: Message):
    if not (BASE_URL := config_dict['BASE_URL']):
        await sendMessage('BASE_URL_OF_BOT not provided!', message)
    elif alive.returncode:
        await sendMessage('Ping have been stopped, your bot will sleep in less than 30 min.', message)
    else:
        alive.kill()
        msg = 'Your bot will sleep in 30 minute maximum.\n\n'
        msg += 'In case changed your mind and want to use the bot again before the sleep then restart the bot.\n\n'
        msg += f'Open this link when you want to wake up the bot {BASE_URL}.'
        await sendMessage(msg, message)


bot.add_handler(MessageHandler(sleep, filters=command(BotCommands.SleepCommand) & CustomFilters.owner))