from speedtest import Speedtest
from pyrogram.filters import command
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message

from bot import bot, LOGGER
from bot.helper.ext_utils.bot_utils import get_readable_file_size, sync_to_async, new_task
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import auto_delete_message, sendMessage, deleteMessage, sendPhoto, editMessage


@new_task
async def speedtest(_, message: Message):
    msg = await sendMessage('<i>Running speed test...</i>', message)
    try:
        test = Speedtest()
        await sync_to_async(test.get_best_server)
        await sync_to_async(test.download)
        await sync_to_async(test.upload)
        await sync_to_async(test.results.share)
        result = await sync_to_async(test.results.dict)
        caption = f'''
<b>SPEEDTEST RESULT</b>
<b>┌ IP: </b>{result['client']['ip']}
<b>├ ISP: </b>{result['client']['isp']}
<b>├ Ping: </b>{int(result['ping'])} ms
<b>├ ISP Rating: </b>{result['client']['isprating']}
<b>├ ISP Rating: </b>{result['client']['isprating']}
<b>├ Sponsor: </b>{result['server']['sponsor']}
<b>├ Upload: </b>{get_readable_file_size(result['upload'] / 8)}
<b>├ Download: </b>{get_readable_file_size(result['download'] / 8)}
<b>├ Server Name: </b>{result['server']['name']}
<b>├ Country: </b>{result['server']['country']}, {result['server']['cc']}
<b>└ LAT/LON </b>{result['client']['lat']}/{result['client']['lon']}
'''
        await deleteMessage(msg)
        await sendPhoto(caption, message, result['share'])
    except Exception as err:
        LOGGER.error(str(err))
        await editMessage(f'Failed running speedtest {err}', msg)
        await auto_delete_message(message, msg)


bot.add_handler(MessageHandler(speedtest, filters=command(BotCommands.SpeedCommand) & CustomFilters.sudo))
