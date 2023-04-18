from asyncio import sleep
from pyrogram import Client
from pyrogram.filters import command, regex
from pyrogram.handlers import CallbackQueryHandler, MessageHandler
from pyrogram.types import CallbackQuery, Message

from bot import bot, bot_loop, download_dict, download_dict_lock, user_data, config_dict, OWNER_ID
from bot.helper.ext_utils.bot_utils import getDownloadByGid, getAllDownload, MirrorStatus, new_task
from bot.helper.ext_utils.force_mode import ForceMode
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage, sendingMessage, auto_delete_message, deleteMessage, editPhoto, editMessage


@new_task
async def cancel_mirror(client: Client, message: Message):
    user_id = message.from_user.id
    reply_to = message.reply_to_message
    msg = message.text.split()
    if len(msg) > 1:
        gid = msg[1]
        dl = await getDownloadByGid(gid)
        if not dl:
            cancelmsg = await sendMessage(f'{message.from_user.mention}, GID: <code>{gid}</code> not found.', message)
            await auto_delete_message(message, cancelmsg)
            return
    elif reply_to:
        async with download_dict_lock:
            dl = download_dict.get(reply_to.id)
        if not dl:
            cancelmsg = await sendMessage(f'{message.from_user.mention}, this is not an active task!', message)
            await auto_delete_message(message, cancelmsg)
            return
    elif len(msg) == 1:
        cancelmsg = f'Reply to an active <code>/{BotCommands.MirrorCommand}</code> message which was used to start the download or send <code>/{BotCommands.CancelMirror} GID</code> to cancel it!'
        if config_dict['AUTO_MUTE'] and message.chat.type.name in ['SUPERGROUP', 'CHANNEL']:
            fmode = ForceMode(message)
            if fmsg:= await fmode.auto_muted(cancelmsg):
                await auto_delete_message(message, fmsg, reply_to)
                return
        else:
            cancelmsg = await sendMessage(cancelmsg, message)
            await auto_delete_message(message, cancelmsg)
            return

    if OWNER_ID != user_id and dl.message.from_user.id != user_id and (user_id not in user_data or not user_data[user_id].get('is_sudo')):
        cancelmsg = await sendMessage(f'{message.from_user.mention}, this task is not for you!', message)
        await auto_delete_message(message, cancelmsg)
        return

    obj = dl.download()
    await obj.cancel_download()
    await auto_delete_message(message)


async def cancel_all(message: Message, status: str):
    matches = await getAllDownload(status)
    if matches:
        for dl in matches:
            obj = dl.download()
            await obj.cancel_download()
            await sleep(1)
        text = f'Successfully cancelled {len(matches)} task for <b>{status}</b>.'
    else:
        text = f'Not a task for <b>{status}</b>.'
    await sendMessage(text, message.reply_to_message)
    await deleteMessage(message)


@new_task
async def cancell_all_buttons(client: Client, message: Message):
    async with download_dict_lock:
        count = len(download_dict)
    if count == 0:
        await sendMessage('No active tasks!', message)
        return
    buttons = ButtonMaker()
    buttons.button_data('Downloading', f'canall {MirrorStatus.STATUS_DOWNLOADING}')
    buttons.button_data('Uploading', f'canall {MirrorStatus.STATUS_UPLOADING}')
    buttons.button_data('GoFile', f'canall {MirrorStatus.STATUS_UPLOADINGTOGO}')
    buttons.button_data('Seeding', f'canall {MirrorStatus.STATUS_SEEDING}')
    buttons.button_data('Cloning', f'canall {MirrorStatus.STATUS_CLONING}')
    buttons.button_data('Extracting', f'canall {MirrorStatus.STATUS_EXTRACTING}')
    buttons.button_data('Archiving', f'canall {MirrorStatus.STATUS_ARCHIVING}')
    buttons.button_data('DL Queued', f'canall {MirrorStatus.STATUS_QUEUEDL}')
    buttons.button_data('UL Queued', f'canall {MirrorStatus.STATUS_QUEUEUP}')
    buttons.button_data('Paused', f'canall {MirrorStatus.STATUS_PAUSED}')
    buttons.button_data('All', 'canall all')
    buttons.button_data('Close', 'canall close', 'footer')
    await sendingMessage('Choose tasks to cancel.', message, config_dict['IMAGE_CANCEL'], buttons.build_menu(2))


@new_task
async def cancel_all_update(client: Client, query: CallbackQuery):
    message = query.message
    data = query.data.split()
    await query.answer()
    if data[1] == 'close':
        await deleteMessage(message, message.reply_to_message)
    else:
        if config_dict['ENABLE_IMAGE_MODE']:
            await editPhoto(f"<i>Canceling {data[1].replace('...', '')} task(s), please wait...</i>", message, config_dict['IMAGE_CANCEL'])
        else:
            await editMessage(f"<i>Canceling {data[1].replace('...', '')} task(s), please wait...</i>", message)
        await cancel_all(message, data[1])


bot.add_handler(MessageHandler(cancel_mirror, filters=command(BotCommands.CancelMirror) & CustomFilters.authorized))
bot.add_handler(MessageHandler(cancell_all_buttons, filters=command(BotCommands.CancelAllCommand) & CustomFilters.sudo))
bot.add_handler(CallbackQueryHandler(cancel_all_update, filters=regex('^canall') & CustomFilters.sudo))
