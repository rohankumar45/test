from aiofiles.os import path as aiopath
from asyncio import gather
from pyrogram import Client
from pyrogram.filters import command, regex
from pyrogram.handlers import CallbackQueryHandler, MessageHandler
from pyrogram.types import CallbackQuery, Message

from bot import aria2, bot, config_dict, download_dict, download_dict_lock, user_data, LOGGER, OWNER_ID
from bot.helper.ext_utils.bot_utils import MirrorStatus, bt_selection_buttons, getDownloadByGid, sync_to_async, new_task
from bot.helper.ext_utils.fs_utils import clean_target
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import auto_delete_message, deleteMessage, sendingMessage, sendMessage, sendStatusMessage


@new_task
async def select(client: Client, message: Message):
    user_id = message.from_user.id
    tag = message.from_user.mention
    msg = message.text.split()
    if len(msg) > 1:
        gid = msg[1]
        dl = await getDownloadByGid(gid)
        if not dl:
            qbselmsg = await sendMessage(f'{tag}, GID: <code>{gid}</code> not found!', message)
            await auto_delete_message(message, qbselmsg)
            return
    elif reply_to:= message.reply_to_message:
        async with download_dict_lock:
            dl = download_dict.get(reply_to.id)
        if not dl:
            qbselmsg = await sendMessage(f'{tag}, this is not an active task!', message)
            await auto_delete_message(message, qbselmsg)
            return
    elif len(msg) == 1:
        msg = 'Reply to an active /cmd which was used to start the qb-download or add gid along with cmd\n\n' \
            'This command mainly for selection incase you decided to select files from already added torrent. '\
            'But you can always use /cmd with arg `s` to select files before download start.'
        qbselmsg = await sendMessage(msg, message)
        await auto_delete_message(message, qbselmsg)
        return
    if OWNER_ID != user_id and dl.message.from_user.id != user_id and \
        (user_id not in user_data or not user_data[user_id].get('is_sudo')):
        qbselmsg = await sendMessage(f'{tag}, this task is not for you!', message)
        await auto_delete_message(message, qbselmsg)
        return
    if dl.status() not in [MirrorStatus.STATUS_DOWNLOADING, MirrorStatus.STATUS_PAUSED, MirrorStatus.STATUS_QUEUEDL]:
        qbselmsg = await sendMessage(f'{tag}, task should be in download or pause (incase message deleted by wrong) or queued (status incase you used torrent file)!', message)
        await auto_delete_message(message, qbselmsg)
        return
    if dl.name().startswith('[METADATA]'):
        qbselmsg = await sendMessage(f'{tag}, try after downloading metadata finished!', message)
        await auto_delete_message(message, qbselmsg)
        return

    try:
        listener = dl.listener()
        if listener.isQbit:
            id_ = dl.hash()
            client = dl.client()
            if not dl.queued:
                await sync_to_async(client.torrents_pause, torrent_hashes=id_)
        else:
            id_ = dl.gid()
            if not dl.queued:
                try:
                    await sync_to_async(aria2.client.force_pause, id_)
                except Exception as e:
                    LOGGER.error(f"{e} Error in pause, this mostly happens after abuse aria2")
        listener.select = True
    except:
        qbselmsg = await sendMessage('This is not a bittorrent task!', message)
        await auto_delete_message(message, qbselmsg)
        return

    SBUTTONS = bt_selection_buttons(id_)
    msg = f'<code>{dl.name()}</code>\n\n{tag}, download paused. Choose files then press <b>Done Selecting</b> button to resume downloading.'
    await sendingMessage(msg, message, config_dict['IMAGE_PAUSE'], SBUTTONS)


async def get_confirm(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    message = query.message
    data = query.data.split()
    dl = await getDownloadByGid(data[2])
    if not dl:
        await query.answer('This task has been cancelled!', show_alert=True)
        await deleteMessage(message)
        return
    if hasattr(dl, 'listener'):
        listener = dl.listener()
    else:
        await query.answer('Not in download state anymore! Keep this message to resume the seed if seed enabled!', show_alert=True)
        return
    if user_id != listener.message.from_user.id:
        await query.answer('Not Yours!', show_alert=True)
    elif data[1] == 'canc':
        await query.answer('Canceling...')
        obj = dl.download()
        await obj.cancel_download()
        await deleteMessage(message)
    elif data[1] == 'pin':
        await query.answer(data[3], show_alert=True)
    elif data[1] == 'done':
        await query.answer()
        id_ = data[3]
        if len(id_) > 20:
            client = dl.client()
            tor_info = (await sync_to_async(client.torrents_info, torrent_hash=id_))[0]
            path = tor_info.content_path.rsplit('/', 1)[0]
            res = await sync_to_async(client.torrents_files, torrent_hash=id_)
            for f in res:
                if f.priority == 0:
                    await gather(*[clean_target(f_path) for f_path in [f'{path}/{f.name}', f'{path}/{f.name}.!qB']])
            if not dl.queued:
                await sync_to_async(client.torrents_resume, torrent_hashes=id_)
        else:
            res = await sync_to_async(aria2.client.get_files, id_)
            for f in res:
                if f['selected'] == 'false':
                    await clean_target(f['path'])
            if not dl.queued:
                try:
                    await sync_to_async(aria2.client.unpause, id_)
                except Exception as e:
                    LOGGER.error(f"{e} Error in resume, this mostly happens after abuse aria2. Try to use select cmd again!")
        await sendStatusMessage(listener.message)
        await deleteMessage(message)
        if BotCommands.BtSelectCommand in message.reply_to_message.text:
            await deleteMessage(message.reply_to_message)


bot.add_handler(MessageHandler(select, filters=command(BotCommands.BtSelectCommand) & CustomFilters.authorized))
bot.add_handler(CallbackQueryHandler(get_confirm, filters=regex('^btsel')))