from pyrogram.filters import command, regex
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.types import Message, CallbackQuery
from time import time

from bot import bot, config_dict
from bot.helper.ext_utils.bot_utils import is_media, get_readable_time, get_date_time, action, new_task
from bot.helper.ext_utils.force_mode import ForceMode
from bot.helper.ext_utils.gdtot_proxy import search_gdtot
from bot.helper.ext_utils.telegram_helper import content_dict, TeleContent
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage, deleteMessage, editMessage, auto_delete_message


@new_task
async def _gdtot(_, message: Message):
    reply_to = message.reply_to_message
    mid = message.id
    args = message.text.split(maxsplit=1)

    if fmsg:= await ForceMode(message).run_force('fsub', 'funame'):
        await auto_delete_message(message, fmsg, reply_to)
        return

    if reply_to and is_media(reply_to) or not reply_to and len(args) == 1:
        msg = await sendMessage(f'{message.from_user.mention}, send query along with command or by reply with command.', message)
        await auto_delete_message(message, msg, reply_to)
        return

    key = reply_to.text.strip() if reply_to else args[1]
    msg = await sendMessage(f'<i>Searching for <b>{key.title()}</b>, please wait...</i>', message)
    tele = TeleContent(message, key, 5)
    content_dict[mid] = tele
    result = await search_gdtot(key)
    if result:
        cap = f"<b>GDTot Search Result:</b>\n"
        cap += f"<b>┌ Found: </b>{len(result)}\n"
        cap += f"<b>├ Cc: </b>{message.from_user.mention}\n"
        cap += f"<b>├ Action: </b>{action(message)}\n"
        cap += f"<b>├ Elapsed: </b>{get_readable_time(time() - message.date.timestamp())}\n"
        cap += f"<b>├ Add: </b>{get_date_time(message)[0]}\n"
        cap += f"<b>├ At: </b>{get_date_time(message)[1]} ({config_dict['TIME_ZONE_TITLE']})\n"
        cap += f"<b>└ Key Input: </b><code>{key.title()}</code>"
        await tele.set_data(result, cap)
        text, buttons = await tele.get_content('gdtot')
        await editMessage(text, msg, buttons)
        if len(result) < 5:
            tele.cancel()
            del content_dict[mid]
    else:
        await editMessage(f'Not found search for <b>{key.title()}</b>!', msg)


@new_task
async def gdtot_callbak(_, query: CallbackQuery):
    message = query.message
    data = query.data.split()
    print(data)
    tele: TeleContent = content_dict.get(int(data[3]))
    if not tele and data[2] != 'close':
        await query.answer('Old Task!', show_alert=True)
    elif data[2] == 'close':
        if tele:
            tele.cancel()
            del content_dict[int(data[3])]
        await deleteMessage(message, message.reply_to_message, tele.reply if tele else None)
    else:
        tdata = int(data[4]) if data[2] == 'foot' else int(data[3])
        text, buttons = await tele.get_content('gdtot', data[2], tdata)
        if not buttons:
            await query.answer(text, show_alert=True)
            return
        await query.answer()
        await editMessage(text, message, buttons)


bot.add_handler(MessageHandler(_gdtot, filters=command(BotCommands.GdtotCommand) & CustomFilters.authorized))
bot.add_handler(CallbackQueryHandler(gdtot_callbak, filters=regex('^gdtot')))