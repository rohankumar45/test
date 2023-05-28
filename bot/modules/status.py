from asyncio import sleep
from psutil import cpu_percent, virtual_memory, disk_usage, net_io_counters
from pyrogram.filters import command, regex
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.types import Message, CallbackQuery
from time import time

from bot import bot, status_reply_dict_lock, download_dict, download_dict_lock, botStartTime, Interval, config_dict, user_data, DOWNLOAD_DIR, LOGGER, OWNER_ID
from bot.helper.ext_utils.bot_utils import get_readable_file_size, get_readable_time, turn_page, setInterval, MirrorStatus, new_task
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import deleteMessage, auto_delete_message, sendStatusMessage, update_all_messages, delete_all_messages, sendMessage, editMessage, sendingMessage


@new_task
async def mirror_status(_, message: Message):
    async with download_dict_lock:
        count = len(download_dict)
    if count:
        await sendStatusMessage(message)
        await deleteMessage(message)
        async with status_reply_dict_lock:
            if Interval:
                Interval[0].cancel()
                Interval.clear()
                Interval.append(setInterval(config_dict['STATUS_UPDATE_INTERVAL'], update_all_messages))
    else:
        msg = 'No Active Downloads!\n▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n'
        msg += f'<b>CPU:</b> {cpu_percent()}% | <b>RAM:</b> {virtual_memory().percent}% | <b>FREE:</b> {get_readable_file_size(disk_usage(DOWNLOAD_DIR).free)}\n'
        msg += f'<b>IN:</b> {get_readable_file_size(net_io_counters().bytes_recv)}<b> | OUT:</b> {get_readable_file_size(net_io_counters().bytes_sent)} | {get_readable_time(time() - botStartTime)}'
        statusmsg = await sendingMessage(msg, message, config_dict['IMAGE_STATUS'])
        await auto_delete_message(message, statusmsg)


async def bot_statistics():
    async with download_dict_lock:
        tasks = len(download_dict)
        if tasks == 0:
            return
        upload = download = clone = queuedl = queueul = pause = archive = extract = split = seed = 0
        for stats in list(download_dict.values()):
            if stats.status() == MirrorStatus.STATUS_UPLOADING:
                upload += 1
            elif stats.status() == MirrorStatus.STATUS_DOWNLOADING:
                download += 1
            elif stats.status() == MirrorStatus.STATUS_CLONING:
                clone += 1
            elif stats.status() == MirrorStatus.STATUS_QUEUEDL:
                queuedl += 1
            elif stats.status() == MirrorStatus.STATUS_QUEUEUP:
                queueul += 1
            elif stats.status() == MirrorStatus.STATUS_PAUSED:
                pause += 1
            elif stats.status() == MirrorStatus.STATUS_ARCHIVING:
                archive += 1
            elif stats.status() == MirrorStatus.STATUS_EXTRACTING:
                extract += 1
            elif stats.status() == MirrorStatus.STATUS_SPLITTING:
                split += 1
            elif stats.status() == MirrorStatus.STATUS_SEEDING:
                seed += 1
    return f'''
Tasks ({tasks})
ZIP: {archive} | UZIP: {extract} | SPL: {split} | DL: {download} | UL {upload} | QDL: {queuedl} | QUL: {queueul} | PS: {pause} | SD: {seed} | CL: {clone}

Limits
UTB: {config_dict['UPTOBOX_STATUS']} | MG: {config_dict['MEGA_STATUS']}
DL: {config_dict.get('TORRENT_DIRECT_LIMIT', '~ ')}GB | Z/U: {config_dict.get('ZIP_UNZIP_LIMIT', '~ ')}GB | MG: {config_dict.get('MEGA_LIMIT', '~ ')}GB
'''


@new_task
async def status_pages(_, query: CallbackQuery):
    user_id = query.from_user.id
    data = query.data.split()
    message = query.message
    admins = user_data.get(user_id, {}).get('is_sudo') or user_id == OWNER_ID
    async with download_dict_lock:
        uid = [dl.message.from_user.id for dl in list(download_dict.values())]
    try:
        if data[1] == 'statistic':
            stats = await bot_statistics()
            if stats:
                await query.answer(stats, show_alert=True)
            else:
                await query.answer('Old status! Closing in 2s...')
                await auto_delete_message(message, stime=2)
        elif data[1] == 'close':
            if admins:
                await query.answer()
                if message.chat.type.name in ['SUPERGROUP', 'CHANNEL']:
                    await sendMessage(f'Status closed by {query.from_user.mention}. Type /{BotCommands.StatusCommand} to get new status.', message)
                await delete_all_messages()
            else:
                await query.answer('Upss, sudo only!', show_alert=True)
        if not admins and user_id not in uid:
            await query.answer('Upss, you doesn\'t have an active task!', show_alert=True)
        else:
            await query.answer()
            if data[1] == 'refresh':
                await editMessage(f'<i>{query.from_user.mention} refreshing status...</i>', message)
                await sleep(1.5)
            else:
                await turn_page(data)
            await update_all_messages(True)
    except Exception as e:
        LOGGER.error(e)


bot.add_handler(MessageHandler(mirror_status, filters=command(BotCommands.StatusCommand) & CustomFilters.authorized))
bot.add_handler(CallbackQueryHandler(status_pages, filters=regex('^status')))