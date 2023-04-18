from pyrogram import Client
from pyrogram.filters import command, regex
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.types import Message, CallbackQuery
from time import time

from bot import bot, config_dict, LOGGER, OWNER_ID
from bot.helper.ext_utils.bot_utils import is_media, sync_to_async, new_task, get_date_time, action, get_readable_time
from bot.helper.ext_utils.force_mode import ForceMode
from bot.helper.ext_utils.telegram_helper import TeleContent
from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage, sendMessage, auto_delete_message, sendFile, deleteMessage, sendPhoto


list_dict = {}


async def get_button(from_user, mid, data=None, isRecursive=False):
    buttons = ButtonMaker()
    if not data:
        buttons.button_data('Folders', f'ldrive {from_user.id} style folders')
        buttons.button_data('Files', f'ldrive {from_user.id} style files')
        buttons.button_data('Both', f'ldrive {from_user.id} style both')
        buttons.button_data(f"{'✅ ' if isRecursive else ''}Recursive", f'ldrive {from_user.id} rec {isRecursive}')
        text = f"{from_user.mention}, Choose Option to Search <b>{list_dict[mid]['content'].key.title()}</b>."
    else:
        buttons.button_data('HTML', f'ldrive {from_user.id} html {data}')
        buttons.button_data('Telegraph', f'ldrive {from_user.id} graph {data}')
        buttons.button_data('Telegram', f'ldrive {from_user.id} tele {data}')
        buttons.button_data('<<', f'ldrive {from_user.id} back')
        text = f'{from_user.mention}, Choose Style for the Result of Seach Drive.'
    buttons.button_data('Cancel', f'ldrive {from_user.id} cancel')
    return text, buttons.build_menu(2) if not data else buttons.build_menu(3)


@new_task
async def list_buttons(client: Client, message: Message):
    reply_to = message.reply_to_message
    mid = message.id
    args = message.text.split(maxsplit=1)
    fmode = ForceMode(message)
    if config_dict['FSUB'] and (fmsg:= await fmode.force_sub):
        await auto_delete_message(message, fmsg, reply_to)
        return
    if config_dict['FUSERNAME'] and (fmsg:= await fmode.force_username):
        await auto_delete_message(message, fmsg, reply_to)
        return
    if reply_to and is_media(reply_to) or not reply_to and len(args) == 1:
        msg = await sendMessage(f'{message.from_user.mention}, send a search key along with command or by reply with command.', message)
        await auto_delete_message(message, msg, reply_to)
        return
    key = reply_to.text.strip() if reply_to else args[1]
    tele = TeleContent(message, key)
    list_dict.update({mid: {'content': tele, 'recursive': False}})
    text, buttons = await get_button(message.from_user, mid)
    await sendMessage(text, message, buttons)


@new_task
async def select_type(client: Client, query: CallbackQuery):
    message = query.message
    from_user = query.from_user
    data = query.data.split()
    style = False
    try:
        mid = message.reply_to_message.id
    except:
        try:
            mid = int(data[3])
        except:
            pass
    tele: TeleContent = list_dict.get(mid, {}).get('content')
    if not tele and data[2] != 'close':
        await query.answer('Old Task!', show_alert=True)
    elif from_user.id not in [OWNER_ID, int(data[1])]:
        await query.answer('Not Yours!', show_alert=True)
    elif data[2] == 'style':
        await query.answer()
        text, buttons = await get_button(from_user, mid, data[3])
        await editMessage(text, message, buttons)
    elif data[2] == 'rec':
        await query.answer()
        isRecursive = not bool(eval(data[3]))
        list_dict[mid]['recursive'] = isRecursive
        text, buttons = await get_button(from_user, mid, isRecursive=isRecursive)
        await editMessage(text, message, buttons)
    elif data[2] == 'back':
        await query.answer()
        text, buttons = await get_button(from_user, mid)
        await editMessage(text, message, buttons)
    elif data[2] in ['html', 'graph', 'tele']:
        await query.answer()
        style = data[2]
    elif data[2] in ['pre', 'nex', 'foot']:
        tdata = int(data[4]) if data[2] == 'foot' else int(data[3])
        text, buttons = await tele.get_content('ldrive', data[2], tdata)
        if not buttons:
            await query.answer(text, show_alert=True)
            return
        await query.answer()
        await editMessage(text, message, buttons)
    elif data[2] == 'page':
        await query.answer(f'Total Page ~ {tele.pages}', show_alert=True)
    elif data[2] == 'cancel':
        del list_dict[mid]
        await editMessage(f'{query.from_user.mention}, your search list for <b>{tele.key.title()}</b> has ben cancelled!', message)
    else:
        await query.answer('List Closed...')
        if tele and mid in list_dict:
            del list_dict[mid]
        await deleteMessage(message, message.reply_to_message, tele.reply if tele else None)
    if style:
        sdict = {'html': 'html style', 'graph': 'telegraph style', 'tele': 'telegram style'}
        await editMessage(f"<i>Searching for <b>{tele.key.title()}</b> with {sdict[style]} ({data[3].title() if data[3] != 'both' else 'Files & Folders'})...</i>", message)
        await _list_drive(tele.key, message, data[3], style)


async def _list_drive(key: str, message: Message, item_type: str, style: str):
    LOGGER.info(f'Listing: {key}')
    omsg: Message = message.reply_to_message
    gdrive = GoogleDriveHelper()
    recursive = list_dict[omsg.id]['recursive']
    count, data = await sync_to_async(gdrive.drive_list, key, isRecursive=recursive, itemType=item_type, style=style)
    if count:
        dt_date, dt_time = get_date_time(omsg)
        msg = f'<b>Drive Search Result:</b>\n'
        msg += f'<b>┌ Found: </b>{count}\n'
        msg += f'<b>├ Cc: </b>{omsg.from_user.mention}\n'
        msg += f'<b>├ Action: </b>{action(omsg)}\n'
        msg += f'<b>├ Elapsed: </b>{get_readable_time(time() - omsg.date.timestamp())}\n'
        msg += f'<b>├ Add: </b>{dt_date}\n'
        msg += f'<b>├ At: </b>{dt_time} ({config_dict["TIME_ZONE_TITLE"]})\n'
        msg += f"<b>├ Type: </b>{item_type.title() if item_type != 'both' else 'Folders & Files'}\n"
        msg += f"<b>├ Recursive: </b>{'Enable' if recursive else 'Disable'}\n"
        msg += f"<b>└ Key Input: </b><code>{key.title()}</code>"
        if style == 'tele':
            tele: TeleContent = list_dict[omsg.id]['content']
            await tele.set_data(data, msg)
            text, buttons = await tele.get_content('ldrive')
            await editMessage(text, message, buttons)
        elif style == 'graph':
            if config_dict['ENABLE_IMAGE_MODE']:
                await deleteMessage(message)
                await sendPhoto(msg, omsg, config_dict['IMAGE_SEARCH'], data)
            else:
                await editMessage(msg, message, data)
        else:
            await deleteMessage(message)
            await sendFile(omsg, data, msg, config_dict['IMAGE_HTML'])
    else:
        await editMessage(f"{omsg.from_user.mention}, no result found for <i>{key}</i> ({item_type.title() if item_type != 'both' else 'Folders & Files'})", message)
    if style != 'tele' or len(data) < 8:
        del list_dict[omsg.id]
    if style != 'tele' and message.chat.type.name in ['SUPERGROUP', 'CHANNEL'] and (stime:= config_dict['AUTO_DELETE_UPLOAD_MESSAGE_DURATION']):
        await auto_delete_message(omsg, stime=stime)


bot.add_handler(MessageHandler(list_buttons, filters=command(BotCommands.ListCommand) & CustomFilters.authorized))
bot.add_handler(CallbackQueryHandler(select_type, filters=regex("^ldrive")))