from aiofiles import open as aiopen
from aiohttp import ClientSession
from html import escape
from pyrogram.filters import command, regex
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.types import Message, CallbackQuery
from time import time
from urllib.parse import quote

from bot import bot, config_dict, get_client, LOGGER
from bot.helper.ext_utils.bot_utils import get_readable_file_size, get_readable_time, get_date_time, action, sync_to_async, new_task
from bot.helper.ext_utils.force_mode import ForceMode
from bot.helper.ext_utils.html_helper import html_template
from bot.helper.ext_utils.telegram_helper import content_dict, TeleContent
from bot.helper.ext_utils.telegraph_helper import telegraph
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import editMessage, sendMessage, deleteMessage, sendFile, auto_delete_message, sendingMessage


TELEGRAPH_LIMIT = 300
PLUGINS = []
SITES = None


async def initiate_search_tools():
    qbclient = await sync_to_async(get_client)
    qb_plugins = await sync_to_async(qbclient.search_plugins)
    if SEARCH_PLUGINS := config_dict['SEARCH_PLUGINS']:
        globals()['PLUGINS'] = []
        src_plugins = eval(SEARCH_PLUGINS)
        if qb_plugins:
            names = [plugin['name'] for plugin in qb_plugins]
            await sync_to_async(qbclient.search_uninstall_plugin, names=names)
        await sync_to_async(qbclient.search_install_plugin, src_plugins)
    elif qb_plugins:
        for plugin in qb_plugins:
            await sync_to_async(qbclient.search_uninstall_plugin, names=plugin['name'])
        globals()['PLUGINS'] = []
    await sync_to_async(qbclient.auth_log_out)
    if SEARCH_API_LINK := config_dict['SEARCH_API_LINK']:
        global SITES
        try:
            async with ClientSession(trust_env=True) as c:
                async with c.get(f'{SEARCH_API_LINK}/api/v1/sites') as res:
                    data = await res.json()
            SITES = {str(site): str(site).capitalize() for site in data['supported_sites']}
            SITES['all'] = 'All'
        except Exception as e:
            LOGGER.error(f'{e} Can\'t fetching sites from SEARCH_API_LINK make sure use latest version of API')
            SITES = None


@new_task
async def torrentSearch(_, message: Message):
    user_id = message.from_user.id
    reply_to = message.reply_to_message
    tag = message.from_user.mention
    key = None

    if fmsg:= await ForceMode(message).run_force('fsub', 'funame'):
        await auto_delete_message(message, fmsg, reply_to)
        return

    if reply_to and reply_to.text:
        key = reply_to.text.strip()
    elif not reply_to and len(args:= message.text.split(maxsplit=1)) != 1:
        key = args[1]

    tele = TeleContent(message, key)
    content_dict[message.id] = tele

    SEARCH_PLUGINS = config_dict['SEARCH_PLUGINS']
    if not SITES and not SEARCH_PLUGINS:
        smsg = await sendMessage('No API link or search PLUGINS added for this function!', message)
        await auto_delete_message(message, smsg)
    elif not key and not SITES:
        smsg = await sendMessage(f'{tag}, send a search key along with command', message)
        await auto_delete_message(message, smsg)
    elif not key:
        buttons = await get_buttons(user_id, 'noargs')
        await sendMessage(f'{tag}, Send a search key along with command or by reply with command!', message, buttons)
    elif SITES and SEARCH_PLUGINS:
        buttons = await get_buttons(user_id, 'dualmode')
        await sendMessage(f'{tag}, Choose Tool to Search <b>{key.title()}</b>.', message, buttons)
    elif SITES:
        buttons = await get_buttons(user_id, 'apisearch', key=key)
        await sendMessage(f'{tag}, Choose Site to Search <b>{key.title()}</b>.', message, buttons)
    else:
        buttons = await get_buttons(user_id)
        await sendMessage(f'{tag}, Choose Site to Search <b>{key.title()}</b>.', message, buttons)


async def get_buttons(user_id: int, method=None, site=None, key=None):
    buttons = ButtonMaker()
    SEARCH_PLUGINS = config_dict['SEARCH_PLUGINS']
    if not method:
        if not PLUGINS:
            qbclient = await sync_to_async(get_client)
            pl = await sync_to_async(qbclient.search_plugins)
            for name in pl:
                PLUGINS.append(name['name'])
            await sync_to_async(qbclient.auth_log_out)
        for siteName in PLUGINS:
            buttons.button_data(siteName.title(), f'torser {user_id} {siteName} plugin')
        buttons.button_data('All', f'torser {user_id} all plugin')
        if SITES and SEARCH_PLUGINS:
            buttons.button_data('<<', f'torser {user_id} dualmode')
    elif method and site:
        buttons.button_data('HTML', f'torser {user_id} html {site} {method}')
        buttons.button_data('Telegraph', f'torser {user_id} graph {site} {method}')
        buttons.button_data('Telegram', f'torser {user_id} tele {site} {method}')
        buttons.button_data('<<', f'torser {user_id} {method}')
    elif method == 'noargs':
        buttons.button_data('Trending', f'torser {user_id} apitrend')
        buttons.button_data('Recent', f'torser {user_id} apirecent')
    elif method == 'dualmode':
        buttons.button_data('Api', f'torser {user_id} apisearch')
        buttons.button_data('Plugins', f'torser {user_id} plugin')
    elif method.startswith('api'):
        for data, name in SITES.items():
            buttons.button_data(name, f'torser {user_id} {data} {method}')
        if SITES and SEARCH_PLUGINS:
            buttons.button_data('<<', f"torser {user_id} {'dualmode' if key else 'noargs'}")
    buttons.button_data('Cancel', f'torser {user_id} cancel')
    return buttons.build_menu(3) if site else buttons.build_menu(2)


@new_task
async def torrentSearchUpdate(_, query: CallbackQuery):
    user_id = query.from_user.id
    message = query.message
    data = query.data.split()
    tag = query.from_user.mention
    tele_data = ['pre', 'nex', 'foot', 'close', 'page']
    try:
        mid = message.reply_to_message.id
    except:
        try:
            mid = int(data[3])
        except:
            pass
    tele: TeleContent = content_dict.get(mid)
    if user_id != int(data[1]):
        await  query.answer('Not Yours!', show_alert=True)
    elif not tele and data[2] != 'close':
        await query.answer('Old Task!', show_alert=True)
    elif data[2].startswith('api'):
        await query.answer()
        buttons = await get_buttons(user_id, data[2], key=tele.key)
        await editMessage(f'{tag}, Choose Site to Search (API Mode).', message, buttons)
    elif data[2] == 'plugin':
        await query.answer()
        buttons = await get_buttons(user_id)
        await editMessage(f'{tag}, Choose Site to Search (Plugin Mode).', message, buttons)
    elif data[2] == 'dualmode':
        await query.answer()
        buttons = await get_buttons(user_id, data[2])
        await editMessage(f'{tag}, Choose Tool to Search.', message, buttons)
    elif data[2] == 'noargs':
        await query.answer()
        buttons = await get_buttons(user_id, data[2])
        await editMessage(f'{tag}, Send a search key along with command or by reply with command!', message, buttons)
    elif len(data) == 4 and data[2] not in tele_data:
        await query.answer()
        buttons = await get_buttons(user_id, data[3], data[2])
        await editMessage(f'{tag}, Choose Style for the Result of Torrent Seach.', message, buttons)
    elif data[2] == 'page':
        await query.answer(f'Total Page ~ {tele.pages}', show_alert=True)
    elif data[2] in ['pre', 'nex', 'foot']:
        tdata = int(data[4]) if data[2] == 'foot' else int(data[3])
        text, buttons = await tele.get_content('torser', data[2], tdata)
        if not buttons:
            await query.answer(text, show_alert=True)
            return
        await query.answer()
        await editMessage(text, message, buttons)
    elif data[2] in ['tele', 'graph', 'html']:
        await query.answer()
        site, method = data[3], data[4]
        sdict = {'html': 'html style', 'graph': 'telegraph style', 'tele': 'telegram style', 'key': tele.key.title if tele.key else ''}
        if method.startswith('api'):
            if not tele.key:
                if method == 'apirecent':
                    tele.key = endpoint = 'recent'
                elif method == 'apitrend':
                    tele.key = endpoint = 'trending'
                await editMessage(f"<i>Searching <b>{endpoint}</b> items in {SITES.get(site).title()} with {sdict[data[2]]}...</i>", message)
            else:
                await editMessage(f"<i>Searching for <b>{tele.key.title()}</b> in {SITES.get(site).title()} with {sdict[data[2]]}...</i>", message)
        else:
            await editMessage(f"<i>Searching for <b>{tele.key.title()}</b> in {site.title()} with {sdict[data[2]]}...</i>", message)
        await __search(tele.key, site, message, method, data[2])
    elif data[2] == 'close':
        await query.answer('Closing torrent search...')
        if tele:
            tele.cancel()
            del content_dict[mid]
        await deleteMessage(message, message.reply_to_message, tele.reply if tele else None)
    else:
        await query.answer()
        await editMessage(f'{tag}, Torrent search has been canceled!', message)


async def __search(key: str, site: str, message: Message, method: str, style: str):
    omsg = message.reply_to_message
    dt_date, dt_time = get_date_time(omsg)
    TIME_ZONE_TITLE = config_dict['TIME_ZONE_TITLE']
    if method.startswith('api'):
        SEARCH_API_LINK = config_dict['SEARCH_API_LINK']
        SEARCH_LIMIT = config_dict['SEARCH_LIMIT']
        if method == 'apisearch':
            LOGGER.info(f"API Searching: {key} from {site}")
            if site == 'all':
                api = f"{SEARCH_API_LINK}/api/v1/all/search?query={key}&limit={SEARCH_LIMIT}"
            else:
                api = f"{SEARCH_API_LINK}/api/v1/search?site={site}&query={key}&limit={SEARCH_LIMIT}"
        elif method == 'apitrend':
            LOGGER.info(f"API Trending from {site}")
            if site == 'all':
                api = f"{SEARCH_API_LINK}/api/v1/all/trending?limit={SEARCH_LIMIT}"
            else:
                api = f"{SEARCH_API_LINK}/api/v1/trending?site={site}&limit={SEARCH_LIMIT}"
        elif method == 'apirecent':
            LOGGER.info(f"API Recent from {site}")
            if site == 'all':
                api = f"{SEARCH_API_LINK}/api/v1/all/recent?limit={SEARCH_LIMIT}"
            else:
                api = f"{SEARCH_API_LINK}/api/v1/recent?site={site}&limit={SEARCH_LIMIT}"
        try:
            async with ClientSession(trust_env=True) as c:
                async with c.get(api) as res:
                    search_results = await res.json()
            if 'error' in search_results or search_results['total'] == 0:
                await editMessage(f"Search not found for <i>{key}</i> in <i>{SITES.get(site).title()}</i>", message)
                return
            cap = f"<b>Torrent Search Result:</b>\n"
            cap += f"<b>┌ Found: </b>{search_results['total']}\n"
            cap += f"<b>├ Elapsed: </b>{get_readable_time(time() - omsg.date.timestamp())}\n"
            cap += f"<b>├ Cc: </b>{omsg.from_user.mention}\n"
            cap += f"<b>├ Action: </b>{action(omsg)}\n"
            cap += f"<b>├ Add: </b>{dt_date}\n"
            cap += f"<b>├ At: </b>{dt_time} ({TIME_ZONE_TITLE})\n"
            cap += "<b>├ Mode: </b>API\n"
            if method == 'apitrend':
                cap += "<b>├ Category: </b>Trending\n"
                cap += f"<b>└ Torrent Site: </b><i>{SITES.get(site).title()}</i>"
            elif method == 'apirecent':
                cap += "<b>├ Category: </b>Recent\n"
                cap += f"<b>└ Torrent Site: </b><i>{SITES.get(site).title()}</i>"
            else:
                cap += f"<b>├ Torrent Site: </b><i>{SITES.get(site).title()}</i>\n"
                cap += f"<b>└ Input Key: </b><code>{key.title()}</code>"
            search_results = search_results['data']
        except Exception as e:
            await editMessage(str(e), message)
            await auto_delete_message(message)
    else:
        LOGGER.info(f"PLUGINS Searching: {key} from {site}")
        client = await sync_to_async(get_client)
        search = await sync_to_async(client.search_start, pattern=key, plugins=site, category='all')
        search_id = search.id
        while True:
            result_status = await sync_to_async(client.search_status, search_id=search_id)
            status = result_status[0].status
            if status != 'Running':
                break
        dict_search_results = await sync_to_async(client.search_results, search_id=search_id, limit=TELEGRAPH_LIMIT)
        search_results = dict_search_results.results
        total_results = dict_search_results.total
        if total_results == 0:
            await editMessage(f"Search not found for <i>{key}</i> in <i>{site.title()}</i>", message)
            return
        cap = "<b>Torrent Search Result:</b>\n"
        cap += f"<b>┌ Found: </b>{total_results}\n"
        cap += f"<b>├ Elapsed: </b>{get_readable_time(time() - omsg.date.timestamp())}\n"
        cap += f"<b>├ Cc: </b>{omsg.from_user.mention}\n"
        cap += f"<b>├ Action: </b>{action(omsg)}\n"
        cap += f"<b>├ Add: </b>{dt_date}\n"
        cap += f"<b>├ At: </b>{dt_time} ({TIME_ZONE_TITLE})\n"
        cap += "<b>├ Mode: </b>Plugin\n"
        cap += f"<b>├ Torrent Site: </b><i>{site.title()}</i>\n"
        cap += f"<b>└ Input Key: </b><code>{key.title()}</code>"
        await sync_to_async(client.search_delete, search_id=search_id)
        await sync_to_async(client.auth_log_out)
    hmsg = await __getResult(search_results, key, message, method, style)
    if style == 'tele':
        tele: TeleContent = content_dict[omsg.id]
        await tele.set_data(hmsg, cap)
        text, buttons = await tele.get_content('torser')
        await editMessage(text, message, buttons)
        if len(hmsg) < 8:
            tele.cancel()
            del content_dict[omsg.id]
    elif style == 'graph':
        buttons = ButtonMaker()
        buttons.button_link("View", hmsg)
        await sendingMessage(cap,omsg, config_dict['IMAGE_SEARCH'], buttons.build_menu(1))
        await deleteMessage(message)
    else:
        name = f"{method.title()}_{str(key).title()}_{site.upper()}_{time()}.html"
        async with aiopen(name, "w", encoding='utf-8') as f:
            await f.write(html_template.replace('{msg}', hmsg).replace('{title}', f'{method}_{key}_{site}'))
        await sendFile(omsg, name, cap, config_dict['IMAGE_HTML'])
        await deleteMessage(message)
    if style != 'tele':
        del content_dict[omsg.id]
    del hmsg
    if message.chat.type.name in ['SUPERGROUP', 'CHANNEL'] and (stime:= config_dict['AUTO_DELETE_UPLOAD_MESSAGE_DURATION']):
        await auto_delete_message(omsg, stime=stime)


async def __getResult(search_results: list, key: str, message: Message, method: str, style: str):
    TSEARCH_TITLE = config_dict['TSEARCH_TITLE']
    if style in ['tele', 'graph']:
        contents = []
        if method == 'apirecent':
            msg = "<h4>API Recent Results</h4>"
        elif method == 'apisearch':
            msg = f"<h4>API Search Result(s) For {key}</h4>"
        elif method == 'apitrend':
            msg = "<h4>API Trending Results</h4>"
        else:
            msg = f"<h4>PLUGINS Search Result(s) For {key}</h4>"
        if style == 'tele':
            msg = ''
        for index, result in enumerate(search_results, start=1):
            if method.startswith('api'):
                try:
                    if 'name' in result.keys():
                        if style == 'tele':
                            msg += f"<a href='{result['url']}'>{escape(result['name'])}</a><br>"
                        else:
                            msg += f"<code><a href='{result['url']}'>{escape(result['name'])}</a></code><br>"
                    if 'torrents' in result.keys():
                        for subres in result['torrents']:
                            msg += f"<b>Quality: </b>{subres['quality']} | <b>Type: </b>{subres['type']} | "
                            msg += f"<b>Size: </b>{subres['size']}<br>"
                            if 'torrent' in subres.keys():
                                msg += f"<a href='{subres['torrent']}'>Direct Link</a><br>"
                            elif 'magnet' in subres.keys():
                                msg += "<b>Share Magnet to</b> "
                                msg += f"<a href='http://t.me/share/url?url={subres['magnet']}'>Telegram</a><br>"
                        msg += '<br>'
                    else:
                        msg += f"<b>Size: </b>{result['size']}<br>"
                        try:
                            msg += f"<b>Seeders: </b>{result['seeders']} | <b>Leechers: </b>{result['leechers']}<br>"
                        except:
                            pass
                        if 'torrent' in result.keys():
                            msg += f"<a href='{result['torrent']}'>Direct Link</a><br><br>"
                        elif 'magnet' in result.keys():
                            msg += "<b>Share Magnet to</b> "
                            msg += f"<a href='http://t.me/share/url?url={quote(result['magnet'])}'>Telegram</a><br><br>"
                        else:
                            msg += '<br>'
                except:
                    continue
            else:
                msg += f"<a href='{result.descrLink}'>{escape(result.fileName)}</a><br>"
                msg += f"<b>Size: </b>{get_readable_file_size(result.fileSize)}<br>"
                msg += f"<b>Seeders: </b>{result.nbSeeders} | <b>Leechers: </b>{result.nbLeechers}<br>"
                link = result.fileUrl
                if link.startswith('magnet:'):
                    msg += f"<b>Share Magnet to</b> <a href='http://t.me/share/url?url={quote(link)}'>Telegram</a><br><br>"
                else:
                    msg += f"<a href='{link}'>Direct Link</a><br><br>"

            if style == 'tele':
                contents.append(str(index).zfill(3) + '. ' + msg.replace('<br>', '\n'))
                msg = ""
            elif len(msg.encode('utf-8')) > 39000:
                contents.append(msg)
                msg = ""

            if index == TELEGRAPH_LIMIT:
                break

        if style == 'tele':
            return contents

        if msg != "":
            contents.append(msg)

        await editMessage(f"<i>Creating {len(contents)} telegraph pages...</i>", message)
        path = [(await telegraph.create_page(TSEARCH_TITLE, content))["path"] for content in contents]
        if len(path) > 1:
            await editMessage(f"<i>Editing {len(contents)} telegraph pages...</i>", message)
            await telegraph.edit_telegraph(path, contents)
        return f"https://telegra.ph/{path[0]}"
    else:
        if method == 'apirecent':
            msg = f'<span class="container center rfontsize"><h1>{TSEARCH_TITLE}</h1><h4>Recent Results</h4></span>'
        elif method == 'apisearch':
            msg = f'<span class="container center rfontsize"><h1>{TSEARCH_TITLE}</h1><h4>Search Results For {key}</h4></span>'
        elif method == 'apitrend':
            msg = f'<span class="container center rfontsize"><h1>{TSEARCH_TITLE}</h1><h4>Trending Results</h4></span>'
        else:
            msg = f'<span class="container center rfontsize"><h1>{TSEARCH_TITLE}</h1><h4>Search Results For {key}</h4></span>'
        for result in search_results:
            msg += '<span class="container start rfontsize">'
            if method.startswith('api'):
                try:
                    if 'name' in result.keys():
                        msg += f"<div> <a class='withhover' href='{result['url']}'>{escape(result['name'])}</a></div>"
                    if 'torrents' in result.keys():
                        for subres in result['torrents']:
                            msg += f"<span class='topmarginsm'><b>Quality: </b>{subres['quality']} | "
                            msg += f"<b>Type: </b>{subres['type']} | <b>Size: </b>{subres['size']}</span>"
                            if 'torrent' in subres.keys():
                                msg += "<span class='topmarginxl'><a class='withhover' "
                                msg += f"href='{subres['torrent']}'>Direct Link</a></span>"
                            elif 'magnet' in subres.keys():
                                msg += "<span><b>Share Magnet to</b> <a class='withhover' "
                                msg += f"href='http://t.me/share/url?url={subres['magnet']}'>Telegram</a></span>"
                        msg += '<br>'
                    else:
                        msg += f"<span class='topmarginsm'><b>Size: </b>{result['size']}</span>"
                        try:
                            msg += f"<span class='topmarginsm'><b>Seeders: </b>{result['seeders']} | "
                            msg += f"<b>Leechers: </b>{result['leechers']}</span>"
                        except:
                            pass
                        if 'torrent' in result.keys():
                            msg += "<span class='topmarginxl'><a class='withhover' "
                            msg += f"href='{result['torrent']}'>Direct Link</a></span>"
                        elif 'magnet' in result.keys():
                            msg += "<span class='topmarginxl'><b>Share Magnet to</b> <a class='withhover' "
                            msg += f"href='http://t.me/share/url?url={quote(result['magnet'])}'>Telegram</a></span>"
                except:
                    continue
            else:
                msg += f"<div> <a class='withhover' href='{result.descrLink}'>{escape(result.fileName)}</a></div>"
                msg += f"<span class='topmarginsm'><b>Size: </b>{get_readable_file_size(result.fileSize)}</span>"
                msg += f"<span class='topmarginsm'><b>Seeders: </b>{result.nbSeeders} | "
                msg += f"<b>Leechers: </b>{result.nbLeechers}</span>"
                link = result.fileUrl
                if link.startswith('magnet:'):
                    msg += "<span class='topmarginxl'><b>Share Magnet to</b> <a class='withhover' "
                    msg += f"href='http://t.me/share/url?url={quote(link)}'>Telegram</a></span>"
                else:
                    msg += f"<span class='topmarginxl'><a class='withhover' href='{link}'>Direct Link</a></span>"
            msg += '</span>'
        return msg


bot.add_handler(MessageHandler(torrentSearch, filters=command(BotCommands.SearchCommand) & CustomFilters.authorized))
bot.add_handler(CallbackQueryHandler(torrentSearchUpdate, filters=regex("^torser")))