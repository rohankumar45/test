from aiofiles import open as aiopen
from aiofiles.os import rename, path as aiopath
from asyncio import create_subprocess_exec, create_subprocess_shell, sleep, gather
from dotenv import load_dotenv
from functools import partial
from os import getcwd, environ
from pyrogram import Client
from pyrogram.filters import command, regex, create
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.types import Message, CallbackQuery
from time import time


from bot import bot, bot_loop, bot_dict, aria2, config_dict, drive_dict, status_reply_dict_lock, Interval, aria2_options, aria2c_global, download_dict, qbit_options, get_client, \
                LOGGER, DATABASE_URL, DRIVES_IDS, DRIVES_NAMES, INDEX_URLS, GLOBAL_EXTENSION_FILTER, SHORTENERES, SHORTENER_APIS
from bot.helper.ext_utils.bot_utils import setInterval, sync_to_async, new_thread
from bot.helper.ext_utils.conf_loads import default_values, load_config, megarest_client, intialize_userbot, intialize_savebot
from bot.helper.ext_utils.db_handler import DbManger
from bot.helper.ext_utils.fs_utils import clean_target, download_gclone
from bot.helper.ext_utils.task_manager import start_from_queued
from bot.helper.mirror_utils.rclone_utils.serve import rclone_serve_booter
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendFile, sendMessage, sendingMessage, editMessage, update_all_messages, editPhoto, deleteMessage
from bot.modules.rss import addJob
from bot.modules.torrent_search import initiate_search_tools

START = 0
STATE = 'view'
handler_dict = {}


async def get_buttons(key=None, edit_type=None):
    buttons = ButtonMaker()
    if key is None:
        buttons.button_data('Bot Variables', 'botset var')
        buttons.button_data('Private Files', 'botset private')
        buttons.button_data('Qbit Settings', 'botset qbit')
        buttons.button_data('Aria2c Settings', 'botset aria')
        buttons.button_data('Close', 'botset close')
        msg = '<b>BOT SETTINGS</b>'
        image = config_dict['IMAGE_CONSET']
    elif key == 'var':
        for k in list(config_dict.keys())[START:20 + START]:
            buttons.button_data(k, f'botset editvar {k}')
        if STATE == 'view':
            buttons.button_data('Edit', 'botset edit var')
            image = config_dict['IMAGE_CONVIEW']
        else:
            buttons.button_data('View', 'botset view var')
            image = config_dict['IMAGE_CONEDIT']
        if config_dict['ENABLE_MEGAREST'] and config_dict['MEGA_KEY']:
            buttons.button_data('Reload Mega', 'botset reloadmega', 'header')
        if config_dict['USER_SESSION_STRING']:
            buttons.button_data('Restart Userbot', 'botset restartubot', 'header')
        if config_dict['SAVE_SESSION_STRING']:
            buttons.button_data('Restart Savebot', 'botset restartsbot', 'header')
        buttons.button_data('<<', 'botset back')
        buttons.button_data('Close', 'botset close')
        for x in range(0, len(config_dict)-1, 20):
            buttons.button_data(int(x/20) + 1, f'botset start var {x}', position='footer')
        msg = f'<b>BOT VARIABLES ~ {int(START/20) + 1}\nState:</b> {STATE.title()}'
    elif key == 'private':
        buttons.button_data('<<', 'botset back')
        buttons.button_data('Close', 'botset close')
        msg = '<b>PRIVATE FILES</b>\n' \
              '<b>┌</b> <code>config.env</code>\n' \
              '<b>├</b> <code>credentials.json</code>\n' \
              '<b>├</b> <code>token.pickle</code>\n' \
              '<b>├</b> <code>accounts.zip</code>\n' \
              '<b>├</b> <code>list_drives.txt</code>\n' \
              '<b>├</b> <code>multi_id.txt</code>\n' \
              '<b>├</b> <code>cookies.txt</code>\n' \
              '<b>├</b> <code>terabox.txt</code>\n' \
              '<b>├</b> <code>shorteners.txt</code>\n' \
              '<b>├</b> <code>rclone.conf</code>\n' \
              '<b>└</b> <code>.netrc</code>\n\n' \
              '<i>To delete private file send the name of the file only as text message.\nTimeout: 60s.</i>'
        image = config_dict['IMAGE_CONPRIVATE']
    elif key == 'aria':
        for k in list(aria2_options.keys())[START:20 + START]:
            buttons.button_data(k, f'botset editaria {k}')
        if STATE == 'view':
            buttons.button_data('Edit', 'botset edit aria')
            image = config_dict['IMAGE_CONVIEW']
        else:
            buttons.button_data('View', 'botset view aria')
            image = config_dict['IMAGE_CONEDIT']
        buttons.button_data('Add new key', 'botset editaria newkey')
        buttons.button_data('<<', 'botset back')
        buttons.button_data('Close', 'botset close')
        for x in range(0, len(aria2_options)-1, 20):
            buttons.button_data(int(x/20) + 1, f'botset start aria {x}', position='footer')
        msg = f'<b>ARIA OPTION ~ {int(START/20) + 1}\nState:</b> {STATE.title()}'
    elif key == 'qbit':
        for k in list(qbit_options.keys())[START:20 + START]:
            buttons.button_data(k, f'botset editqbit {k}')
        if STATE == 'view':
            buttons.button_data('Edit', 'botset edit qbit')
            image = config_dict['IMAGE_CONVIEW']
        else:
            buttons.button_data('View', 'botset view qbit')
            image = config_dict['IMAGE_CONEDIT']
        buttons.button_data('<<', 'botset back')
        buttons.button_data('Close', 'botset close')
        for x in range(0, len(qbit_options)-1, 20):
            buttons.button_data(int(x/20) + 1, f'botset start qbit {x}', position='footer')
        msg = f'<b>QBITTORRENT OPTIONS ~ {int(START/20) + 1}\nState:</b> {STATE.title()}'
    elif edit_type == 'editvar':
        msg = ''
        buttons.button_data('<<', 'botset back var')
        if key not in ['TELEGRAM_HASH', 'TELEGRAM_API', 'OWNER_ID', 'BOT_TOKEN']:
            buttons.button_data('Default', f'botset resetvar {key}')
        buttons.button_data('Close', 'botset close')
        if key in ['SUDO_USERS', 'CMD_SUFFIX', 'OWNER_ID', 'TELEGRAM_HASH', 'TELEGRAM_API',
                   'AUTHORIZED_CHATS', 'DATABASE_URL', 'BOT_TOKEN', 'DOWNLOAD_DIR']:
            msg += 'Restart required for this edit to take effect!\n\n'
        msg += f'Send a valid value for <b>{key}</b>.\n\n<i>Timeout: 60s.</i>'
        image = config_dict['IMAGE_CONEDIT']
    elif edit_type == 'editaria':
        buttons.button_data('<<', 'botset back aria')
        if key != 'newkey':
            buttons.button_data('Default', f'botset resetaria {key}')
            buttons.button_data('Empty String', f'botset emptyaria {key}')
        buttons.button_data('Close', 'botset close')
        image = config_dict['IMAGE_CONEDIT']
        if key == 'newkey':
            msg = f'Send a key with value. <b>Example:</b> https-proxy-user:value\n\n<i>Timeout: 60s.</i>'
        else:
            msg = f'Send a valid value for <b>{key}</b>.\n\n<i>Timeout: 60s.</i>'
    elif edit_type == 'editqbit':
        buttons.button_data('Empty String', f'botset emptyqbit {key}')
        buttons.button_data('<<', 'botset back qbit')
        buttons.button_data('Close', 'botset close')
        msg = f'Send a valid value for <b>{key}</b>.\n\n<i>Timeout: 60s.</i>'
        image = config_dict['IMAGE_CONEDIT']
    image = image if image else None
    return msg, image, buttons.build_menu(2)


async def update_buttons(message: Message, key: str=None, edit_type: str=None):
    msg, image, buttons = await get_buttons(key, edit_type)
    if config_dict['ENABLE_IMAGE_MODE']:
        await editPhoto(msg, message, image, buttons)
    else:
        await editMessage(msg, message, buttons)


async def edit_variable(_, message: Message, omsg: Message, key: str):
    handler_dict[message.chat.id] = False
    value = message.text
    if key == 'ENABLE_MEGAREST':
        if value.lower() == 'true':
            megarest_client()
        else:
            await (await create_subprocess_exec('pkill', '-9', '-f', 'megasdkrest')).wait()
            LOGGER.info('Megarest stopped! Switch to Megasdk client.')
    if value.lower() == 'true':
        value = True
    elif value.lower() == 'false':
        value = False
        if key == 'INCOMPLETE_TASK_NOTIFIER' and DATABASE_URL:
            await DbManger().trunc_table('tasks')
    elif key == 'RSS_DELAY':
        value = int(value)
        addJob(value)
    elif key == 'DOWNLOAD_DIR':
        if not value.endswith('/'):
            value += '/'
    elif key == 'STATUS_UPDATE_INTERVAL':
        value = int(value)
        if len(download_dict) != 0:
            async with status_reply_dict_lock:
                if Interval:
                    Interval[0].cancel()
                    Interval.clear()
                    Interval.append(setInterval(value, update_all_messages))
    elif key == 'TORRENT_TIMEOUT':
        value = int(value)
        downloads = await sync_to_async(aria2.get_downloads)
        for download in downloads:
            if not download.is_complete:
                try:
                    await sync_to_async(aria2.client.change_option, download.gid, {'bt-stop-timeout': f'{value}'})
                except Exception as e:
                    LOGGER.error(e)
        aria2_options['bt-stop-timeout'] = f'{value}'
    elif key == 'LEECH_SPLIT_SIZE':
        value = min(int(value), bot_dict['MAX_SPLIT_SIZE'])
    elif key == 'BASE_URL':
        await (await create_subprocess_exec('pkill', '-9', '-f', 'gunicorn')).wait()
        await create_subprocess_shell(f'gunicorn web.wserver:app --bind 0.0.0.0:{environ.get("PORT")} --worker-class gevent')
    elif key == 'PORT':
        value = int(value)
        if config_dict['BASE_URL']:
            await (await create_subprocess_exec('pkill', '-9', '-f', 'gunicorn')).wait()
            await create_subprocess_shell(f'gunicorn web.wserver:app --bind 0.0.0.0:{value} --worker-class gevent')
    elif key == 'EXTENSION_FILTER':
        fx = value.split()
        GLOBAL_EXTENSION_FILTER.clear()
        GLOBAL_EXTENSION_FILTER.append('aria2')
        for x in fx:
            GLOBAL_EXTENSION_FILTER.append(x.strip().lower())
    elif key == 'GDRIVE_ID':
        if DRIVES_NAMES and DRIVES_NAMES[0] == 'Main':
            DRIVES_IDS[0] = value
        else:
            DRIVES_IDS.insert(0, value)
    elif key == 'INDEX_URL':
        value = value.rstrip('/')
        if DRIVES_NAMES and DRIVES_NAMES[0] == 'Main':
            INDEX_URLS[0] = value
        else:
            INDEX_URLS.insert(0, value)
    elif key == 'GCLONE_URL':
        bot_loop.create_task(download_gclone())
    elif value.isdigit() or value.startswith('-1'):
        value = int(value)
    config_dict[key] = value
    if key == 'USER_SESSION_STRING':
        await intialize_userbot()
    elif key == 'SAVE_SESSION_STRING':
        await intialize_savebot()
    await update_buttons(omsg, 'var')
    LOGGER.info(f'Change var {key} = {value.__class__.__name__.upper()}: {value}')
    await deleteMessage(message)
    if DATABASE_URL:
        await DbManger().update_config({key: value})
    if key in ['SEARCH_PLUGINS', 'SEARCH_API_LINK']:
        await initiate_search_tools()
    elif key in ['QUEUE_ALL', 'QUEUE_DOWNLOAD', 'QUEUE_UPLOAD']:
        await start_from_queued()
    elif key in ['RCLONE_SERVE_URL', 'RCLONE_SERVE_PORT', 'RCLONE_SERVE_USER', 'RCLONE_SERVE_PASS']:
        await rclone_serve_booter()


async def edit_aria(_, message: Message, omsg: Message, key: str):
    handler_dict[message.chat.id] = False
    value = message.text
    if key == 'newkey':
        key, value = [x.strip() for x in value.split(':', 1)]
    elif value.lower() == 'true':
        value = 'true'
    elif value.lower() == 'false':
        value = 'false'
    if key in aria2c_global:
        await sync_to_async(aria2.set_global_options, {key: value})
    else:
        downloads = await sync_to_async(aria2.get_downloads)
        for download in downloads:
            if not download.is_complete:
                try:
                    await sync_to_async(aria2.client.change_option, download.gid, {key: value})
                except Exception as e:
                    LOGGER.error(e)
    aria2_options[key] = value
    await update_buttons(omsg, 'aria')
    await deleteMessage(message)
    if DATABASE_URL:
        await DbManger().update_aria2(key, value)


async def edit_qbit(_, message: Message, omsg: Message, key: str):
    handler_dict[message.chat.id] = False
    value = message.text
    if value.lower() == 'true':
        value = True
    elif value.lower() == 'false':
        value = False
    elif key == 'max_ratio':
        value = float(value)
    elif value.isdigit() or value.startswith('-'):
        value = int(value)
    await sync_to_async(get_client().app_set_preferences, {key: value})
    qbit_options[key] = value
    await update_buttons(omsg, 'qbit')
    await deleteMessage(message)
    if DATABASE_URL:
        await DbManger().update_qbittorrent(key, value)


async def update_private_file(_, message: Message, omsg: Message):
    handler_dict[message.chat.id] = False
    if not message.media and (file_name := message.text):
        fn = file_name.rsplit('.zip', 1)[0]
        if file_name != 'config.env':
            await clean_target(fn)
        if fn == 'accounts':
            await gather(clean_target('accounts'), clean_target('rclone_sa'))
            config_dict['USE_SERVICE_ACCOUNTS'] = False
            if DATABASE_URL:
                await DbManger().update_config({'USE_SERVICE_ACCOUNTS': False})
        elif file_name in ['.netrc', 'netrc']:
            await (await create_subprocess_exec('touch', '.netrc')).wait()
            await (await create_subprocess_exec('chmod', '600', '.netrc')).wait()
            await (await create_subprocess_exec('cp', '.netrc', '/root/.netrc')).wait()
        elif file_name == 'shorteners.txt':
            SHORTENERES.clear()
            SHORTENER_APIS.clear()
        elif file_name == 'multi_id.txt':
            config_dict['MULTI_GDID'] = False
            if DATABASE_URL:
                await DbManger().update_config({'MULTI_GDID': False})
        LOGGER.info(f'Removed private file: {fn}')
        await deleteMessage(message)
    elif doc:= message.document:
        tmsg = await sendMessage('<i>Processing, please wait...</i>', message)
        file_name = doc.file_name
        await message.download(file_name=f'{getcwd()}/{file_name}')
        if file_name == 'accounts.zip':
            await gather(clean_target('accounts'), clean_target('rclone_sa'))
            await (await create_subprocess_exec('7z', 'x', '-o.', '-aoa', 'accounts.zip', 'accounts/*.json')).wait()
            await (await create_subprocess_exec('chmod', '-R', '777', 'accounts')).wait()
            config_dict['USE_SERVICE_ACCOUNTS'] = True
            if DATABASE_URL:
                await DbManger().update_config({'USE_SERVICE_ACCOUNTS': True})
        elif file_name == 'config.env':
            load_dotenv('config.env', override=True)
            await load_config()
        elif file_name in ['.netrc', 'netrc']:
            if file_name == 'netrc':
                await rename('netrc', '.netrc')
                file_name = '.netrc'
            await (await create_subprocess_exec('chmod', '600', '.netrc')).wait()
            await (await create_subprocess_exec('cp', '.netrc', '/root/.netrc')).wait()
        elif file_name == 'list_drives.txt':
            DRIVES_IDS.clear()
            DRIVES_NAMES.clear()
            INDEX_URLS.clear()
            if GDRIVE_ID := config_dict['GDRIVE_ID']:
                DRIVES_NAMES.append('Main')
                DRIVES_IDS.append(GDRIVE_ID)
                INDEX_URLS.append(config_dict['INDEX_URL'])
            async with aiopen('list_drives.txt', 'r+') as f:
                for line in await f.readlines():
                    temp = line.strip().split()
                    DRIVES_IDS.append(temp[1])
                    DRIVES_NAMES.append(temp[0].replace('_', ' '))
                    if len(temp) > 2:
                        INDEX_URLS.append(temp[2])
                    else:
                        INDEX_URLS.append('')
        elif file_name == 'shorteners.txt':
            SHORTENERES.clear()
            SHORTENER_APIS.clear()
            with open('shorteners.txt', 'r+') as f:
                lines = f.readlines()
                for line in lines:
                    temp = line.strip().split()
                    if len(temp) == 2:
                        SHORTENERES.append(temp[0])
                        SHORTENER_APIS.append(temp[1])
        elif file_name == 'multi_id.txt':
            drive_dict.clear()
            if GDRIVE_ID := config_dict['GDRIVE_ID']:
                drive_dict['Default'] = ['Default', GDRIVE_ID, config_dict['INDEX_URL']]
            async with aiopen('multi_id.txt', 'r') as f:
                for x in await f.readlines():
                    x = x.strip().split()
                    index = x[2].rstrip('/') if len(x) > 2 else ''
                    drive_dict[x[0]] = [x[0], x[1], index]
                    if x[1] not in DRIVES_IDS:
                        DRIVES_IDS.append(x[1])
                        DRIVES_NAMES.append(x[0])
                        INDEX_URLS.append(index)
        if '@github.com' in config_dict['UPSTREAM_REPO']:
            buttons = ButtonMaker()
            msg = 'Push to <b>UPSTREAM_REPO</b>?'
            buttons.button_data('Yes', f'botset push {file_name}')
            buttons.button_data('No', 'botset close')
            await editMessage(msg, tmsg, buttons.build_menu(2))
        else:
            await deleteMessage(message, tmsg)
        LOGGER.info(f'Added private file: {file_name}')
    if file_name == 'rclone.conf':
        await rclone_serve_booter()
    await update_buttons(omsg)
    if DATABASE_URL:
        await DbManger().update_private_file(file_name)
    await clean_target('accounts.zip')


async def event_handler(client: Client, query: CallbackQuery, pfunc: partial, rfunc: partial, document=False):
    chat_id = query.message.chat.id
    handler_dict[chat_id] = True
    start_time = time()
    async def event_filter(_, __, event):
        user = event.from_user or event.sender_chat
        return bool(user.id == query.from_user.id and event.chat.id == chat_id and (event.text or event.document and document))
    handler = client.add_handler(MessageHandler(pfunc, filters=create(event_filter)), group=-1)
    while handler_dict[chat_id]:
        await sleep(0.5)
        if time() - start_time > 60:
            handler_dict[chat_id] = False
            await rfunc()
    client.remove_handler(*handler)


@new_thread
async def edit_bot_settings(client: Client, query: CallbackQuery):
    message = query.message
    data = query.data.split()
    if data[1] == 'close':
        handler_dict[message.chat.id] = False
        await query.answer()
        await deleteMessage(message, message.reply_to_message)
    elif data[1] == 'back':
        handler_dict[message.chat.id] = False
        await query.answer()
        key = data[2] if len(data) == 3 else None
        if key is None:
            globals()['START'] = 0
        await update_buttons(message, key)
    elif data[1] == 'reloadmega':
        await query.answer('Relogin Megarest!', show_alert=True)
        await (await create_subprocess_exec('pkill', '-9', '-f', 'megasdkrest')).wait()
        await sleep(1.5)
        megarest_client()
    elif data[1] == 'restartubot':
        await query.answer('Restarting Userbot!', show_alert=True)
        await intialize_userbot()
    elif data[1] == 'restartsbot':
        await query.answer('Restarting Savebot!', show_alert=True)
        await intialize_savebot()
    elif data[1] in ['var', 'aria', 'qbit']:
        await query.answer()
        await update_buttons(message, data[1])
    elif data[1] == 'resetvar':
        if data[2] in ['OWNER_ID', 'DATABASE_URL', 'GCLONE_URL', 'UPSTREAM_REPO', 'UPSTREAM_BRANCH'] and query.from_user.id != config_dict['OWNER_ID']:
            await query.answer('This setting only available for owner!', True)
            return
        handler_dict[message.chat.id] = False
        await query.answer()
        value = ''
        if data[2] in default_values:
            value = default_values[data[2]]
            if data[2] == 'LEECH_SPLIT_SIZE':
                value = bot_dict['MAX_SPLIT_SIZE']
            if data[2] == 'STATUS_UPDATE_INTERVAL' and len(download_dict) != 0:
                async with status_reply_dict_lock:
                    if Interval:
                        Interval[0].cancel()
                        Interval.clear()
                        Interval.append(setInterval(value, update_all_messages))
        elif data[2] == 'EXTENSION_FILTER':
            GLOBAL_EXTENSION_FILTER.clear()
            GLOBAL_EXTENSION_FILTER.append('.aria2')
        elif data[2] == 'TORRENT_TIMEOUT':
            downloads = await sync_to_async(aria2.get_downloads)
            for download in downloads:
                if not download.is_complete:
                    try:
                        await sync_to_async(aria2.client.change_option, download.gid, {'bt-stop-timeout': '0'})
                    except Exception as e:
                        LOGGER.error(e)
            aria2_options['bt-stop-timeout'] = '0'
            if DATABASE_URL:
                await DbManger().update_aria2('bt-stop-timeout', '0')
        elif data[2] == 'BASE_URL':
            await (await create_subprocess_exec('pkill', '-9', '-f', 'gunicorn')).wait()
        elif data[2] == 'PORT':
            value = 80
            if config_dict['BASE_URL']:
                await (await create_subprocess_exec('pkill', '-9', '-f', 'gunicorn')).wait()
                await create_subprocess_shell('gunicorn web.wserver:app --bind 0.0.0.0:80 --worker-class gevent')
        elif data[2] == 'GDRIVE_ID':
            if DRIVES_NAMES and DRIVES_NAMES[0] == 'Main':
                DRIVES_NAMES.pop(0)
                DRIVES_IDS.pop(0)
                INDEX_URLS.pop(0)
        elif data[2] == 'INDEX_URL':
            value = value.rstrip('/')
            if DRIVES_NAMES and DRIVES_NAMES[0] == 'Main':
                INDEX_URLS[0] = ''
        elif data[2] == 'INCOMPLETE_TASK_NOTIFIER' and DATABASE_URL:
            await DbManger().trunc_table('tasks')
        config_dict[data[2]] = value
        LOGGER.info(f'Change var {data[2]} = {value.__class__.__name__.upper()}: {value}')
        if data[2] == 'USER_SESSION_STRING':
            await intialize_userbot()
        elif data[2] == 'SAVE_SESSION_STRING':
            await intialize_savebot()
            config_dict['SAVE_CONTENT'] = False
        await update_buttons(message, 'var')
        if DATABASE_URL:
            await DbManger().update_config({data[2]: value})
        if data[2] in ['SEARCH_PLUGINS', 'SEARCH_API_LINK']:
            await initiate_search_tools()
        elif data[2] in ['QUEUE_ALL', 'QUEUE_DOWNLOAD', 'QUEUE_UPLOAD']:
            await start_from_queued()
        elif data[2] in ['RCLONE_SERVE_URL', 'RCLONE_SERVE_PORT', 'RCLONE_SERVE_USER', 'RCLONE_SERVE_PASS']:
            await rclone_serve_booter()
    elif data[1] == 'resetaria':
        handler_dict[message.chat.id] = False
        aria2_defaults = await sync_to_async(aria2.client.get_global_option)
        if aria2_defaults[data[2]] == aria2_options[data[2]]:
            await query.answer('Value already same as you added in aria.sh!')
            return
        await query.answer()
        value = aria2_defaults[data[2]]
        aria2_options[data[2]] = value
        await update_buttons(message, 'aria')
        downloads = await sync_to_async(aria2.get_downloads)
        for download in downloads:
            if not download.is_complete:
                try:
                    await sync_to_async(aria2.client.change_option, download.gid, {data[2]: value})
                except Exception as e:
                    LOGGER.error(e)
        if DATABASE_URL:
            await DbManger().update_aria2(data[2], value)
    elif data[1] == 'emptyaria':
        handler_dict[message.chat.id] = False
        await query.answer()
        aria2_options[data[2]] = ''
        await update_buttons(message, 'aria')
        downloads = await sync_to_async(aria2.get_downloads)
        for download in downloads:
            if not download.is_complete:
                try:
                    await sync_to_async(aria2.client.change_option, download.gid, {data[2]: ''})
                except Exception as e:
                    LOGGER.error(e)
        if DATABASE_URL:
            await DbManger().update_aria2(data[2], '')
    elif data[1] == 'emptyqbit':
        handler_dict[message.chat.id] = False
        await query.answer()
        await sync_to_async(get_client().app_set_preferences, {data[2]: value})
        qbit_options[data[2]] = ''
        await update_buttons(message, 'qbit')
        if DATABASE_URL:
            await DbManger().update_qbittorrent(data[2], '')
    elif data[1] == 'private':
        handler_dict[message.chat.id] = False
        await query.answer()
        await update_buttons(message, data[1])
        pfunc = partial(update_private_file, omsg=message)
        rfunc = partial(update_buttons, message)
        await event_handler(client, query, pfunc, rfunc, True)
    elif data[1] == 'editvar' and STATE == 'edit':
        if data[2] in ['OWNER_ID', 'DATABASE_URL', 'GCLONE_URL', 'UPSTREAM_REPO', 'UPSTREAM_BRANCH'] and query.from_user.id != config_dict['OWNER_ID']:
            await query.answer('This setting only available for owner!', True)
            return
        handler_dict[message.chat.id] = False
        await query.answer()
        await update_buttons(message, data[2], data[1])
        pfunc = partial(edit_variable, omsg=message, key=data[2])
        rfunc = partial(update_buttons, message, 'var')
        await event_handler(client, query, pfunc, rfunc)
    elif data[1] == 'editvar' and STATE == 'view':
        if data[2] in ['OWNER_ID', 'DATABASE_URL', 'GCLONE_URL', 'UPSTREAM_REPO', 'UPSTREAM_BRANCH'] and query.from_user.id != config_dict['OWNER_ID']:
            await query.answer('This setting only available for owner!', True)
            return
        value = config_dict[data[2]]
        if len(str(value)) > 200:
            await query.answer()
            filename = f'{data[2]}.txt'
            async with aiopen(filename, 'w', encoding='utf-8') as f:
                await f.write(f'{value}')
            await sendFile(message, filename, filename.split('.', maxsplit=1)[0], config_dict['IMAGE_TXT'])
            return
        elif value == '':
            value = None
        await query.answer(f'{value.__class__.__name__.upper()}: {value}', show_alert=True)
    elif data[1] == 'editaria' and (STATE == 'edit' or data[2] == 'newkey'):
        handler_dict[message.chat.id] = False
        await query.answer()
        await update_buttons(message, data[2], data[1])
        pfunc = partial(edit_aria, omsg=message, key=data[2])
        rfunc = partial(update_buttons, message, 'aria')
        await event_handler(client, query, pfunc, rfunc)
    elif data[1] == 'editaria' and STATE == 'view':
        value = aria2_options[data[2]]
        if len(str(value)) > 200:
            await query.answer()
            filename = f'{data[2]}.txt'
            async with aiopen(filename, 'w', encoding='utf-8') as f:
                await f.write(f'{value}')
            await sendFile(message, filename, filename.split('.', maxsplit=1)[0], config_dict['IMAGE_TXT'])
            return
        elif value == '':
            value = None
        await query.answer(f'{value.__class__.__name__.upper()}: {value}', show_alert=True)
    elif data[1] == 'editqbit' and STATE == 'edit':
        handler_dict[message.chat.id] = False
        await query.answer()
        await update_buttons(message, data[2], data[1])
        pfunc = partial(edit_qbit, omsg=message, key=data[2])
        rfunc = partial(update_buttons, message, 'var')
        await event_handler(client, query, pfunc, rfunc)
    elif data[1] == 'editqbit' and STATE == 'view':
        value = qbit_options[data[2]]
        if len(str(value)) > 200:
            await query.answer()
            filename = f'{data[2]}.txt'
            async with aiopen(filename, 'w', encoding='utf-8') as f:
                await f.write(f'{value}')
            await sendFile(message, filename, filename.split('.', maxsplit=1)[0], config_dict['IMAGE_TXT'])
            return
        elif value == '':
            value = None
        await query.answer(f'{value.__class__.__name__.upper()}: {value}', show_alert=True)
    elif data[1] == 'edit':
        await query.answer()
        globals()['STATE'] = 'edit'
        await update_buttons(message, data[2])
    elif data[1] == 'view':
        await query.answer()
        globals()['STATE'] = 'view'
        await update_buttons(message, data[2])
    elif data[1] == 'start':
        await query.answer()
        if START != int(data[3]):
            globals()['START'] = int(data[3])
            await update_buttons(message, data[2])
    elif data[1] == 'push':
        await query.answer()
        filename = data[2].rsplit('.zip', 1)[0]
        if await aiopath.exists(filename):
            await (await create_subprocess_shell(f"git add -f {filename} \
                                                   && git commit -sm botsettings -q \
                                                   && git push origin {config_dict['UPSTREAM_BRANCH']} -qf")).wait()
        else:
            await (await create_subprocess_shell(f"git rm -r --cached {filename} \
                                                   && git commit -sm botsettings -q \
                                                   && git push origin {config_dict['UPSTREAM_BRANCH']} -qf")).wait()
        LOGGER.info('Push update to UPSTREAM_REPO')
        await deleteMessage(message, message.reply_to_message)


@new_thread
async def bot_settings(_, message: Message):
    msg, image, buttons = await get_buttons()
    await sendingMessage(msg, message, image, buttons)


bot.add_handler(MessageHandler(bot_settings, filters=command(BotCommands.BotSetCommand) & CustomFilters.sudo))
bot.add_handler(CallbackQueryHandler(edit_bot_settings, filters=regex('^botset') & CustomFilters.sudo))