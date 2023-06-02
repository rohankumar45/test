import heroku3

from aiofiles import open as aiopen
from aiofiles.os import path as aiopath
from asyncio import gather
from os import execl as osexecl
from platform import system, architecture, release
from psutil import disk_usage, cpu_percent, swap_memory, cpu_count, virtual_memory, net_io_counters, boot_time
from signal import signal, SIGINT

from asyncio import create_subprocess_exec
from pyrogram import Client
from pyrogram.filters import command, regex, new_chat_members, left_chat_member
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.types import Message, CallbackQuery, BotCommand
from sys import executable
from time import time

from bot import bot, bot_dict, bot_name, alive, botStartTime, Interval, QbInterval, user_data, config_dict, scheduler, LOGGER, DATABASE_URL, INCOMPLETE_TASK_NOTIFIER, OWNER_ID
from bot.helper import save_message
from bot.helper.ext_utils.bot_utils import get_readable_file_size, get_readable_time, cmd_exec, sync_to_async, new_task, get_progress_bar_string
from bot.helper.ext_utils.conf_loads import intialize_userbot, intialize_savebot
from bot.helper.ext_utils.db_handler import DbManger
from bot.helper.ext_utils.fs_utils import start_cleanup, clean_all, exit_clean_up, clean_target
from bot.helper.ext_utils.help_messages import HelpString, get_help_button
from bot.helper.ext_utils.heroku_status import getHerokuDetails
from bot.helper.listeners.aria2_listener import start_aria2_listener
from bot.helper.resume_task import set_incomplte_task
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage, editMessage, sendFile, auto_delete_message, sendingMessage, deleteMessage, editPhoto, sendCustom, editCustom
from bot.modules import authorize, bot_settings, clone, gd_count, gd_delete, gd_list, cancel_mirror, gdtot_serach, heroku_sleep, mirror_leech, status, torrent_search, torrent_select, user_settings, ytdlp, shell, eval, rss, speedtest, wayback, hash, bypass, scrapper, purge, broadcase, info, misc_tools, backup, join_chat


@new_task
async def stats(_, message: Message):
    if await aiopath.exists('.git'):
        last_commit = await cmd_exec("git log -1 --date=short --pretty=format:'%cd \n<b>├ From</b> %cr'", True)
        last_commit = last_commit[0]
    else:
        last_commit = 'No UPSTREAM_REPO'
    cpu, mem, disk, swap = f'{cpu_percent(interval=1)}%', f'{virtual_memory().percent}%', f'{disk_usage("/")[3]}%', f'{swap_memory().percent}%'
    stats = f'''
<b>UPSTREAM AND BOT STATUS</b>
<b>┌ Commit Date:</b> {last_commit}
<b>├ Bot Uptime:</b> {get_readable_time(time() - botStartTime)}
<b>└ OS Uptime:</b> {get_readable_time(time() - boot_time())}\n
<b>SYSTEM STATUS</b>
<b>┌ SWAP:</b> {get_readable_file_size(swap_memory().total)}
<b>├ Total Cores:</b> {cpu_count(logical=True)}
<b>├ Physical Cores:</b> {cpu_count(logical=False)}
<b>├ Upload:</b> {get_readable_file_size(net_io_counters().bytes_sent)}
<b>├ Download:</b> {get_readable_file_size(net_io_counters().bytes_recv)}
<b>├ Disk Free:</b> {get_readable_file_size(disk_usage('/')[2])}
<b>├ Disk Used:</b> {get_readable_file_size(disk_usage('/')[1])}
<b>├ Disk Space:</b> {get_readable_file_size(disk_usage('/')[0])}
<b>├ Memory Free:</b> {get_readable_file_size(virtual_memory().available)}
<b>├ Memory Used:</b> {get_readable_file_size(virtual_memory().used)}
<b>├ Memory Total:</b> {get_readable_file_size(virtual_memory().total)}
<b>├ CPU:</b> {get_progress_bar_string(cpu)} {cpu}
<b>├ RAM:</b> {get_progress_bar_string(mem)} {mem}
<b>├ DISK:</b> {get_progress_bar_string(disk)} {disk}
<b>├ SWAP:</b> {get_progress_bar_string(swap)} {swap}
<b>└ OS:</b> {system()}, {architecture()[0]}, {release()}\n
'''
    if heroku:= await getHerokuDetails():
        stats += heroku
    statsmsg = await sendingMessage(stats, message, config_dict['IMAGE_STATS'])
    await auto_delete_message(message, statsmsg)


@new_task
async def start(client: Client, message: Message):
    buttons = ButtonMaker()
    buttons.button_link('Owner', f'{config_dict["AUTHOR_URL"]}')
    buttons.button_link('Channel', f'https://t.me/{config_dict["CHANNEL_USERNAME"]}')
    if await CustomFilters.authorized(client, message):
        starmsg = await sendingMessage(f'Bot ready to use, type /{BotCommands.HelpCommand} to get a list of available commands',
                                       message, config_dict['IMAGE_AUTH'], buttons.build_menu(2))
    else:
        if user_data.get(message.from_user.id, {}).get('enable_pm'):
            text = f'''
<b>Bot ready to use...</b>
Back to the group and happy mirroring...
All mirror and leech file(s) will send here and log channel

Join @{config_dict['CHANNEL_USERNAME']} for more info...
'''
            starmsg = await sendingMessage(text, message, config_dict['IMAGE_AUTH'], buttons.build_menu(2))
        else:
            starmsg = await sendingMessage('<b>Upss...</b>\nNot authorized user!', message, config_dict['IMAGE_UNAUTH'], buttons.build_menu(2))
    await auto_delete_message(message, starmsg)


async def restart(_, message: Message):
    cmd = message.text.split(maxsplit=1)
    hrestart = hkill = False
    HAPI, HNAME = config_dict['HEROKU_API_KEY'], config_dict['HEROKU_APP_NAME']
    if len(cmd) == 2:
        hrestart = cmd[1].lower().startswith('dyno')
        hkill = cmd[1].lower().startswith('kill')
    if hrestart or hkill:
        if not HAPI or not HNAME:
            LOGGER.info('Heroku details is missing!')
            await sendMessage('<b>HEROKU_APP_NAME</b> or <b>HEROKU_API_KEY</b> not set!', message)
            return
    if hrestart:
        msg = await sendMessage('<i>Restarting with dyno mode...</i>', message)
        async with aiopen('.restartmsg', 'w') as f:
            await f.truncate(0)
            await f.write(f'{msg.chat.id}\n{msg.id}\n')
        try:
            heroku3.from_key(HAPI).app(HNAME).restart()
        except Exception as e:
            await editMessage(f'ERROR: {e}', msg)
    elif hkill:
        msg = await sendMessage('Killed Dyno.', message)
        try:
            heroku_conn = heroku3.from_key(HAPI)
            app = heroku_conn.app(HNAME)
            for po in (proclist := app.process_formation()):
                proclist[po.type].scale(0)
        except Exception as e:
            await editMessage(f'ERROR: {e}', msg)
    else:
        msg = await sendMessage('<i>Restarting with normal mode...</i>', message)
        if scheduler.running:
            scheduler.shutdown(wait=False)
        for interval in [QbInterval, Interval]:
            if interval:
                interval[0].cancel()
        alive.kill()
        await sync_to_async(clean_all)
        proc1 = await create_subprocess_exec('pkill', '-9', '-f', 'gunicorn|aria2c|qbittorrent-nox|megasdkrest|ffmpeg|rclone')
        proc2 = await create_subprocess_exec('python3', 'update.py')
        await gather(proc1.wait(), proc2.wait())
        async with aiopen('.restartmsg', 'w') as f:
            await f.write(f'{msg.chat.id}\n{msg.id}\n')
        osexecl(executable, executable, '-m', 'bot')


@new_task
async def ping(_, message: Message):
    start_time = int(round(time() * 1000))
    reply = await sendMessage('Starting Ping', message)
    end_time = int(round(time() * 1000))
    await editMessage(f'{end_time - start_time} ms', reply)
    await auto_delete_message(message, reply)


@new_task
async def log(_, message: Message):
    await sendFile(message, 'log.txt', thumb=config_dict['IMAGE_LOGS'])
    await auto_delete_message(message)


async def help_query(_, query: CallbackQuery):
    data = query.data.split(maxsplit=2)
    message = query.message
    if int(data[1]) != query.from_user.id:
        await query.answer('Not Yours!', show_alert=True)
    elif data[2] == 'close':
        await query.answer()
        await deleteMessage(message, message.reply_to_message)
    else:
        await query.answer()
        text, image, buttons = get_help_button(query.from_user, data[2])
        if config_dict['ENABLE_IMAGE_MODE']:
            await editPhoto(text, message, image, buttons)
        else:
            await editMessage(text, message, buttons)


async def bot_help(_, message: Message):
    text, image, buttons = get_help_button(message.from_user)
    await sendingMessage(text, message, image, buttons)


@new_task
async def new_member(_, message: Message):
    buttons = ButtonMaker()
    buttons.button_link('Owner', f"{config_dict['AUTHOR_URL']}")
    buttons.button_link('Channel', f"https://t.me/{config_dict['CHANNEL_USERNAME']}")
    for user in message.new_chat_members:
        try:
            image = await bot.download_media(user.photo.big_file_id, file_name=f'./{user.id}.png')
        except:
            image = config_dict['IMAGE_WEL']
        text = f'''
Hello there <b>{user.mention}</b>, welcome to <b>{(await bot.get_chat(message.chat.id)).title}</b> Group. Enjoy in mirror/leech party 😘
<b>┌ ID:</b> <code>{user.id}</code>
<b>├ First Name:</b> {user.first_name}
<b>├ Last Name:</b> {user.last_name or '~'}
<b>├ Username:</b> {'@' + user.username if user.username else '~'}
<b>├ Language:</b> {user.language_code.upper() if user.language_code else '~'}
<b>├ DC ID:</b> {user.dc_id or '~'}
<b>└ Premium User:</b> {'Yes' if user.is_premium else 'No'}'''
        newmsg = await sendingMessage(text, message, image, buttons.build_menu(2))
        if await aiopath.exists(image):
            await clean_target(image)
    await auto_delete_message(message, newmsg)


@new_task
async def leave_member(_, message: Message):
    user = message.left_chat_member
    leavemsg = await sendingMessage(f'Yeah... <b>{user.mention}</b>, don\'t come back here! 😕😕', message, config_dict['IMAGE_BYE'])
    await sendCustom('Yeah u are leaved!', user.id)
    await auto_delete_message(message, leavemsg)


async def set_command():
    commands = [BotCommand(x[1:x.index(' ')].replace(':', '').strip(), x[x.index(' '):].strip()) for x in HelpString().all_commands]
    await bot.set_bot_commands(commands)


async def restart_notification():
    if await aiopath.isfile('.restartmsg'):
        with open('.restartmsg') as f:
            chat_id, msg_id = map(int, f)
    else:
        chat_id, msg_id = 0, 0

    async def send_incompelete_task_message(cid, msg, reply_markup):
        if msg.startswith('Restarted Successfully!'):
            await editCustom(msg, chat_id, msg_id, reply_markup)
            await clean_target('.restartmsg')
        else:
            await sendCustom(msg, cid, reply_markup)

    notifier_dict = False
    premium_message = '\nPremium leech enable 😘!' if bot_dict['IS_PREMIUM'] else ''
    if INCOMPLETE_TASK_NOTIFIER and DATABASE_URL:
        if notifier_dict := await DbManger().get_incomplete_tasks():
            buttons = ButtonMaker()
            buttons.button_data('Resume', 'resume')
            for cid, data in notifier_dict.items():
                msg = 'Restarted Successfully!' if cid == chat_id else 'Bot Restarted!'
                msg += premium_message
                for tag, links in data.items():
                    msg += f'\n\n{tag}: '
                    for index, link in enumerate(links, start=1):
                        await set_incomplte_task(cid, link)
                        msg += f" <a href='{link}'>{index}</a> |"
                        if len(msg.encode()) > 4000:
                            if 'Restarted Successfully!' in msg and cid == chat_id:
                                await send_incompelete_task_message(cid, msg, buttons.build_menu(1))
                            msg = ''
                if msg:
                    await send_incompelete_task_message(cid, msg, buttons.build_menu(1))

    if await aiopath.isfile('.restartmsg'):
        with open('.restartmsg') as f:
            chat_id, msg_id = map(int, f)
        msg = f'Restarted Successfully!{premium_message}'
        await editCustom(msg, chat_id, msg_id)
        await clean_target('.restartmsg')
    elif not notifier_dict and user_data:
        for id_ in user_data:
            if user_data[id_].get('is_auth') or user_data[id_].get('is_sudo') or id_ == OWNER_ID:
                await sendCustom(f'Bot Restarted!{premium_message}', id_)


async def main():
    await sync_to_async(start_aria2_listener, wait=False)
    bot.add_handler(MessageHandler(start, filters=command(BotCommands.StartCommand)))
    bot.add_handler(MessageHandler(log, filters=command(BotCommands.LogCommand) & CustomFilters.owner))
    bot.add_handler(MessageHandler(restart, filters=command(BotCommands.RestartCommand) & CustomFilters.sudo))
    bot.add_handler(MessageHandler(ping, filters=command(BotCommands.PingCommand) & CustomFilters.authorized))
    bot.add_handler(MessageHandler(bot_help, filters=command(BotCommands.HelpCommand) & CustomFilters.authorized))
    bot.add_handler(MessageHandler(stats, filters=command(BotCommands.StatsCommand) & CustomFilters.authorized))
    bot.add_handler(CallbackQueryHandler(help_query, filters=regex('help')))
    bot.add_handler(MessageHandler(new_member, filters=new_chat_members))
    bot.add_handler(MessageHandler(leave_member, filters=left_chat_member))
    await gather(intialize_userbot(False), set_command(), start_cleanup(), torrent_search.initiate_search_tools(), return_exceptions=True)
    await gather(intialize_savebot(config_dict['SAVE_SESSION_STRING'], False), restart_notification(), return_exceptions=True)
    LOGGER.info(f'Bot @{bot_name} Started!')
    signal(SIGINT, exit_clean_up)


bot.loop.run_until_complete(main())
bot.loop.run_forever()
