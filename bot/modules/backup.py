from asyncio import sleep
from pyrogram import Client
from pyrogram.filters import command, regex
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.types import Message, CallbackQuery
from time import time

from bot import bot
from bot.helper.ext_utils.bot_utils import get_readable_time, new_task
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage, copyMessage, deleteMessage

hanlder_dict = {}


@new_task
async def backup_message(client: Client, message: Message):
    try:
        _, start, end, source_id, des_id = message.text.split()
    except:
        await sendMessage('Send valid format: start, end, source id, destination id!', message)
        return
    try:
        stitle = (await client.get_chat(int(source_id))).title
    except:
        await sendMessage('U must add me to source chat!', message)
        return
    try:
        dtitle = (await client.get_chat(int(des_id))).title
    except:
        await sendMessage('U must add me to destination chat!', message)
        return
    buttons = ButtonMaker()
    buttons.button_data('Stop', f'backup stop {message.from_user.id} {message.id}')
    hanlder_dict[message.id] = False
    cmsg = await sendMessage('Starting copy message(s)...', message, buttons.build_menu(1))
    await sleep(2)
    succ = fail = empy = 0
    status, first_id = 'Done', None
    same_id = source_id == des_id
    for x in range(int(start), int(end)):
        if hanlder_dict[message.id]:
            status = f'Cancelled ({x})'
            break
        msg = await client.get_messages(int(source_id), x)
        if not msg.empty:
            text = f'Copying message <b>{x}/{end}</b>.\n' \
                    f'<b>{stitle} >> {dtitle}</b>\n\n' \
                    f'<i>Elapsed {get_readable_time(time() - message.date.timestamp())}</i>'
            await editMessage(text, cmsg, buttons.build_menu(1))
            if same_id and msg.id == first_id:
                break
            if copyed:= await copyMessage(int(des_id), msg):
                succ += 1
                if same_id and not first_id:
                    first_id = copyed.id
            else:
                fail += 1
            if same_id:
                await deleteMessage(msg)
            await sleep(10)
        else:
            empy += 1

    text = f'Backup Message {status}!\n' \
        f'<b>Time Taken:</b> {get_readable_time(time() - message.date.timestamp())}\n' \
        f'<b>Total:</b> {end}\n' \
        f'<b>Success:</b> {succ}\n' \
        f'<b>Empty:</b> {empy}\n' \
        f'<b>Failed:</b> {fail}\n' \
        f'<b>From Chat:</b> {stitle}\n' \
        f'<b>To Chat:</b> {dtitle}'
    await editMessage(text, cmsg)


async def backup_message_hanlder(client: Client, query: CallbackQuery):
    data = query.data.split()
    if int(data[2]) != query.from_user.id:
        await query.answer('Not yours!', show_alert=True)
    else:
        hanlder_dict[int(data[3])] = True
        await query.answer('Cancelling backup mmessage(s)...')


bot.add_handler(MessageHandler(backup_message, filters=command(BotCommands.BackupCommand) & CustomFilters.authorized))
bot.add_handler(CallbackQueryHandler(backup_message_hanlder, filters=regex('^backup')))