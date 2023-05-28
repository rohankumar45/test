from aiofiles import open as aiopen
from aiohttp import ClientSession
from apscheduler.triggers.interval import IntervalTrigger
from asyncio import Lock, sleep
from datetime import datetime, timedelta
from feedparser import parse as feedparse
from functools import partial
from pyrogram import Client
from pyrogram.filters import command, regex, create
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.types import Message, CallbackQuery
from re import split as re_split
from time import time

from bot import bot, scheduler, rss_dict, config_dict, LOGGER, DATABASE_URL
from bot.helper.ext_utils.bot_utils import new_thread, new_task
from bot.helper.ext_utils.help_messages import HelpString
from bot.helper.ext_utils.db_handler import DbManger
from bot.helper.ext_utils.exceptions import RssShutdownException
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import deleteMessage, editMessage, sendMessage, sendRss, auto_delete_message, sendFile


rss_dict_lock = Lock()
handler_dict = {}


@new_task
async def _auto_delete(*args, stime: int=6):
    await auto_delete_message(*args, stime=stime)


async def rssMenu(event):
    user_id = event.from_user.id
    buttons = ButtonMaker()
    buttons.button_data('Subscribe', f'rss sub {user_id}')
    buttons.button_data('Subscriptions', f'rss list {user_id} 0')
    buttons.button_data('Get Items', f'rss get {user_id}')
    buttons.button_data('Edit', f'rss edit {user_id}')
    buttons.button_data('Pause', f'rss pause {user_id}')
    buttons.button_data('Resume', f'rss resume {user_id}')
    buttons.button_data('Unsubscribe', f'rss unsubscribe {user_id}')
    if await CustomFilters.sudo('', event):
        buttons.button_data('All Subscriptions', f'rss listall {user_id} 0')
        buttons.button_data('Pause All', f'rss allpause {user_id}')
        buttons.button_data('Resume All', f'rss allresume {user_id}')
        buttons.button_data('Unsubscribe All', f'rss allunsub {user_id}')
        buttons.button_data('Delete User', f'rss deluser {user_id}')
        if scheduler.running:
            buttons.button_data('Shutdown Rss', f'rss shutdown {user_id}')
        else:
            buttons.button_data('Start Rss', f'rss start {user_id}')
    buttons.button_data('Close', f'rss close {user_id}')
    msg = f'<b>RSS MENU</b>\n<b>Users</b>: {len(rss_dict)}\n<b>Running:</b> {scheduler.running}'
    return msg, buttons.build_menu(2)


async def updateRssMenu(query: CallbackQuery):
    msg, buttons = await rssMenu(query)
    await editMessage(msg, query.message, buttons)


@new_thread
async def getRssMenu(_, message: Message):
    msg, buttons = await rssMenu(message)
    await sendMessage(msg, message, buttons)


async def rssSub(_, message: Message, query: CallbackQuery):
    user_id = message.from_user.id
    handler_dict[user_id] = False
    tag = message.from_user.mention
    msg = ''
    smsg = None
    items = message.text.split('\n')
    for index, item in enumerate(items, start=1):
        args = item.split()
        if len(args) < 2:
            errmsg = await sendMessage(f'{item}. Wrong Input format. Read help message before adding new subcription!', message)
            _auto_delete(message, errmsg)
            continue
        title = args[0].strip()
        if (user_feeds := rss_dict.get(user_id, False)) and title in user_feeds:
            errmsg = await sendMessage(f'This title {title} already subscribed! Choose another title!', message)
            _auto_delete(message, errmsg)
            continue
        feed_link = args[1].strip()
        if feed_link.startswith(('inf:', 'exf:', 'opt:', 'c:')):
            errmsg = await sendMessage(f'Wrong input in line {index}! Re-add only the mentioned line correctly! Read the example!', message)
            _auto_delete(message, errmsg)
            continue
        inf_lists, exf_lists = [], []
        if len(args) > 2:
            arg = item.split(' c: ', 1)
            cmd = re_split(' inf: | exf: | opt: ', arg[1])[0].strip() if len(arg) > 1 else None
            arg = item.split(' inf: ', 1)
            inf = re_split(' c: | exf: | opt: ', arg[1])[0].strip() if len(arg) > 1 else None
            arg = item.split(' exf: ', 1)
            exf = re_split(' c: | inf: | opt: ', arg[1])[0].strip() if len(arg) > 1 else None
            arg = item.split(' opt: ', 1)
            opt = re_split(' c: | inf: | exf: ', arg[1])[0].strip() if len(arg) > 1 else None
            if inf is not None:
                filters_list = inf.split('|')
                for x in filters_list:
                    y = x.split(' or ')
                    inf_lists.append(y)
            if exf is not None:
                filters_list = exf.split('|')
                for x in filters_list:
                    y = x.split(' or ')
                    exf_lists.append(y)
        else:
            inf = exf = cmd = opt = None
        try:
            async with ClientSession(trust_env=True) as session:
                async with session.get(feed_link) as res:
                    html = await res.text()
            rss_d = feedparse(html)
            last_title = rss_d.entries[0]['title']
            msg += "<b>Subscribed!</b>"
            msg += f"\n<b>Title: </b><code>{title}</code>\n<b>Feed Url: </b>{feed_link}"
            msg += f"\n<b>latest record for </b>{rss_d.feed.title}:"
            msg += f"\nName: <code>{last_title.replace('>', '').replace('<', '')}</code>"
            try:
                last_link = rss_d.entries[0]['links'][1]['href']
            except IndexError:
                last_link = rss_d.entries[0]['link']
            msg += f"\nLink: <code>{last_link}</code>"
            msg += f"\n<b>Command: </b><code>{cmd}</code>"
            msg += f"\n<b>Filters:-</b>\ninf: <code>{inf}</code>\nexf: <code>{exf}<code/>"
            msg += f"\nOptions: {opt}\n\n"
            async with rss_dict_lock:
                if rss_dict.get(user_id, False):
                    rss_dict[user_id][title] = {'link': feed_link, 'last_feed': last_link, 'last_title': last_title,
                                                'inf': inf_lists, 'exf': exf_lists, 'paused': False, 'command': cmd, 'options': opt, 'tag': tag}
                else:
                    rss_dict[user_id] = {title: {'link': feed_link, 'last_feed': last_link, 'last_title': last_title,
                                                 'inf': inf_lists, 'exf': exf_lists, 'paused': False, 'command': cmd, 'options': opt, 'tag': tag}}
            LOGGER.info(f'Rss Feed Added: id: {user_id} - title: {title} - link: {feed_link} - c: {cmd} - inf: {inf} - exf: {exf} - opt: {opt}')
        except (IndexError, AttributeError) as e:
            emsg = f"The link: {feed_link} doesn't seem to be a RSS feed or it's region-blocked!"
            smsg = await sendMessage(f'{emsg}\n<b>Error:</b>{e}', message)
        except Exception as e:
            smsg = await sendMessage(f'<b>ERROR:</b> {e}', message)
    async with rss_dict_lock:
        if rss_dict.get(user_id) and DATABASE_URL:
            await DbManger().rss_update(user_id)
    if not smsg and msg:
        smsg = await sendMessage(msg, message)
    await updateRssMenu(query)
    _auto_delete(message, smsg, stime=20)


async def getUserId(title):
    async with rss_dict_lock:
        return next(((True, user_id) for user_id, feed in list(rss_dict.items()) if feed['title'] == title), (False, False))


async def rssUpdate(client: Client, message: Message, query: CallbackQuery, state: str):
    user_id = message.from_user.id
    handler_dict[user_id] = False
    titles = message.text.split()
    is_sudo = await CustomFilters.sudo(client, message)
    updated = []
    for title in titles:
        title = title.strip()
        if not (res := rss_dict[user_id].get(title, False)):
            if is_sudo:
                res, user_id = await getUserId(title)
            if not res:
                user_id = message.from_user.id
                errmsg = await sendMessage(f'{title} not found!', message)
                _auto_delete(message, errmsg)
                continue
        istate = rss_dict[user_id][title].get('paused', False)
        if istate and state == 'pause' or not istate and state == 'resume':
            errmsg = await sendMessage(f'{title} already {state}d!', message)
            _auto_delete(message, errmsg)
            continue
        async with rss_dict_lock:
            updated.append(title)
            if state == 'unsubscribe':
                del rss_dict[user_id][title]
            elif state == 'pause':
                rss_dict[user_id][title]['paused'] = True
            elif state == 'resume':
                rss_dict[user_id][title]['paused'] = False
        if state == 'resume':
            if scheduler.state == 2:
                scheduler.resume()
            elif is_sudo and not scheduler.running:
                addJob(config_dict['RSS_DELAY'])
                scheduler.start()
        if is_sudo and DATABASE_URL and user_id != message.from_user.id:
            await DbManger().rss_update(user_id)
        if not rss_dict[user_id]:
            async with rss_dict_lock:
                del rss_dict[user_id]
            if DATABASE_URL:
                await DbManger().rss_delete(user_id)
                if not rss_dict:
                    await DbManger().trunc_table('rss')
    LOGGER.info(f'Rss link with Title(s): {updated} has been {state}d!')
    msg = await sendMessage(f'Rss links with Title(s): <code>{updated}</code> has been {state}d!', message)
    if DATABASE_URL and rss_dict.get(user_id):
        await DbManger().rss_update(user_id)
    await updateRssMenu(query)
    _auto_delete(message, msg, stime=10)


async def rssList(query: CallbackQuery, start: int, all_users: bool=False):
    user_id = query.from_user.id
    buttons = ButtonMaker()
    if all_users:
        list_feed = f'<b>All RSS Subscriptions\n<b>Page:</b> {int(start/5)+1} </b>'
        async with rss_dict_lock:
            keysCount = sum(len(v.keys()) for v in list(rss_dict.values()))
            index = 0
            for titles in list(rss_dict.values()):
                for index, (title, data) in enumerate(list(titles.items())[start:5+start]):
                    list_feed += f"\n\n<b>Title:</b> <code>{title}</code>\n"
                    list_feed += f"<b>Feed Url:</b> <code>{data['link']}</code>\n"
                    list_feed += f"<b>Command:</b> <code>{data['command']}</code>\n"
                    list_feed += f"<b>Inf:</b> <code>{data['inf']}</code>\n"
                    list_feed += f"<b>Exf:</b> <code>{data['exf']}</code>\n"
                    list_feed += f"<b>Paused:</b> <code>{data['paused']}</code>\n"
                    list_feed += f"<b>Options:</b> <code>{data['options']}</code>\n"
                    list_feed += f"<b>User:</b> {data['tag'].lstrip('@')}"
                    index += 1
                    if index == 5:
                        break
    else:
        list_feed = f'<b>Your RSS Subscriptions\n<b>Page:</b> {int(start/5)+1} </b>'
        async with rss_dict_lock:
            keysCount = len(rss_dict.get(user_id, {}).keys())
            for title, data in list(rss_dict[user_id].items())[start:5+start]:
                list_feed += f"\n\n<b>Title:</b> <code>{title}</code>\n<b>Feed Url: </b><code>{data['link']}</code>\n"
                list_feed += f"<b>Command:</b> <code>{data['command']}</code>\n"
                list_feed += f"<b>Inf:</b> <code>{data['inf']}</code>\n"
                list_feed += f"<b>Exf:</b> <code>{data['exf']}</code>\n"
                list_feed += f"<b>Paused:</b> <code>{data['paused']}</code>\n"
                list_feed += f"<b>Options:</b> <code>{data['options']}</code>"
    buttons.button_data('<<', f'rss back {user_id}')
    buttons.button_data('Close', f'rss close {user_id}')
    if keysCount > 5:
        for x in range(0, keysCount, 5):
            buttons.button_data(f'{int(x/5)+1}', f'rss list {user_id} {x}', 'footer')
    if query.message.text.html == list_feed:
        return
    await editMessage(list_feed, query.message, buttons.build_menu(2))


async def rssGet(_, message: Message, query: CallbackQuery):
    user_id = message.from_user.id
    handler_dict[user_id] = False
    args = message.text.split()
    if len(args) < 2:
        msg = await sendMessage(f'{args}. Wrong Input format. You should add number of the items you want to get. Read help message before adding new subcription!', message)
        await updateRssMenu(query)
        _auto_delete(message, msg)
        return
    try:
        title = args[0]
        count = int(args[1])
        data = rss_dict[user_id].get(title, False)
        if data and count > 0:
            msg = await sendMessage(f'Getting the last <b>{count}</b> item(s) from {title}', message)
            try:
                async with ClientSession(trust_env=True) as session:
                    async with session.get(data['link']) as res:
                        html = await res.text()
                rss_d = feedparse(html)
                item_info = ""
                for item_num in range(count):
                    try:
                        link = rss_d.entries[item_num]['links'][1]['href']
                    except IndexError:
                        link = rss_d.entries[item_num]['link']
                    item_info += f"<b>Name: </b><code>{rss_d.entries[item_num]['title'].replace('>', '').replace('<', '')}</code>\n"
                    item_info += f"<b>Link: </b><code>{link}</code>\n\n"
                item_info_ecd = item_info.encode()
                if len(item_info_ecd) > 4000:
                    filename = f'RSSGet {title} items_no. {count}.txt'
                    async with aiopen(filename, 'w', encoding='utf-8') as f:
                        await f.write(f'{item_info_ecd}')
                    await sendFile(message, filename, f'RSSGet {title} items_no. {count}')
                    await deleteMessage(msg)
                else:
                    await editMessage(item_info, msg)
            except IndexError as e:
                LOGGER.error(str(e))
                await editMessage('Parse depth exceeded. Try again with a lower value.', msg)
            except Exception as e:
                LOGGER.error(str(e))
                await editMessage(str(e), msg)
    except Exception as e:
        LOGGER.error(str(e))
        msg = await sendMessage(f'Enter a valid value!. {e}', message)
    await updateRssMenu(query)
    _auto_delete(message, msg, stime=10)


async def rssEdit(_, message: Message, query: CallbackQuery):
    user_id = message.from_user.id
    handler_dict[user_id] = False
    items = message.text.split('\n')
    for item in items:
        args = item.split()
        title = args[0].strip()
        if len(args) < 2:
            msg = await sendMessage(f'{item}. Wrong Input format. Read help message before editing!', message)
            _auto_delete(message, msg)
            continue
        elif not rss_dict[user_id].get(title, False):
            msg = await sendMessage('Enter a valid title. Title not found!', message)
            _auto_delete(message, msg)
            continue
        inf_lists, exf_lists = [], []
        arg = item.split(' c: ', 1)
        cmd = re_split(' inf: | exf: | opt: ', arg[1])[0].strip() if len(arg) > 1 else None
        arg = item.split(' inf: ', 1)
        inf = re_split(' c: | exf: | opt: ', arg[1])[0].strip() if len(arg) > 1 else None
        arg = item.split(' exf: ', 1)
        exf = re_split(' c: | inf: | opt: ', arg[1])[0].strip() if len(arg) > 1 else None
        arg = item.split(' opt: ', 1)
        opt = re_split(' c: | inf: | exf: ', arg[1])[0].strip() if len(arg) > 1 else None
        async with rss_dict_lock:
            if opt is not None:
                if opt.lower() == 'none':
                    opt = None
                rss_dict[user_id][title]['options'] = opt
            if cmd is not None:
                if cmd.lower() == 'none':
                    cmd = None
                rss_dict[user_id][title]['command'] = cmd
            if inf is not None:
                if inf.lower() != 'none':
                    filters_list = inf.split('|')
                    for x in filters_list:
                        y = x.split(' or ')
                        inf_lists.append(y)
                rss_dict[user_id][title]['inf'] = inf_lists
            if exf is not None:
                if exf.lower() != 'none':
                    filters_list = exf.split('|')
                    for x in filters_list:
                        y = x.split(' or ')
                        exf_lists.append(y)
                rss_dict[user_id][title]['exf'] = exf_lists
    if DATABASE_URL:
        await DbManger().rss_update(user_id)
    await deleteMessage(message)
    await updateRssMenu(query)


async def rssDelete(_, message: Message, query: CallbackQuery):
    handler_dict[message.from_user.id] = False
    users = message.text.split()
    for user in users:
        user = int(user)
        async with rss_dict_lock:
            del rss_dict[user]
        if DATABASE_URL:
            await DbManger().rss_delete(user)
    await updateRssMenu(query)


async def event_handler(client: Client, query: CallbackQuery, pfunc: partial):
    user_id = query.from_user.id
    handler_dict[user_id] = True
    start_time = time()
    async def event_filter(_, __, event):
        user = event.from_user or event.sender_chat
        return bool(user.id == user_id and event.chat.id == query.message.chat.id and event.text)
    handler = client.add_handler(MessageHandler(pfunc, create(event_filter)), group=-1)
    while handler_dict[user_id]:
        await sleep(0.5)
        if time() - start_time > 60:
            handler_dict[user_id] = False
            await updateRssMenu(query)
    client.remove_handler(*handler)


@new_thread
async def rssListener(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    message = query.message
    data = query.data.split()
    if int(data[2]) != user_id and not await CustomFilters.sudo(client, query):
        await query.answer("You don't have permission to use these buttons!", show_alert=True)
    elif data[1] == 'close':
        await query.answer()
        handler_dict[user_id] = False
        await deleteMessage(message, message.reply_to_message)
    elif data[1] == 'back':
        await query.answer()
        handler_dict[user_id] = False
        await updateRssMenu(query)
    elif data[1] == 'sub':
        await query.answer()
        handler_dict[user_id] = False
        buttons = ButtonMaker()
        buttons.button_data('<<', f'rss back {user_id}')
        buttons.button_data('Close', f'rss close {user_id}')
        await editMessage(HelpString.RSSHELP, message, buttons.build_menu(2))
        pfunc = partial(rssSub, query=query)
        await event_handler(client, query, pfunc)
    elif data[1] == 'list':
        handler_dict[user_id] = False
        if len(rss_dict.get(int(data[2]), {})) == 0:
            await query.answer('No subscriptions!', show_alert=True)
        else:
            await query.answer()
            start = int(data[3])
            await rssList(query, start)
    elif data[1] == 'get':
        handler_dict[user_id] = False
        if len(rss_dict.get(int(data[2]), {})) == 0:
            await query.answer('No subscriptions!', show_alert=True)
        else:
            await query.answer()
            buttons = ButtonMaker()
            buttons.button_data('<<', f'rss back {user_id}')
            buttons.button_data('Close', f'rss close {user_id}')
            await editMessage('Send one title with vlaue separated by space get last X items.\nTitle Value\n\n<i>Timeout: 60s.</i>', message, buttons.build_menu(2))
            pfunc = partial(rssGet, query=query)
            await event_handler(client, query, pfunc)
    elif data[1] in ['unsubscribe', 'pause', 'resume']:
        handler_dict[user_id] = False
        if len(rss_dict.get(int(data[2]), {})) == 0:
            await query.answer('No subscriptions!', show_alert=True)
        else:
            await query.answer()
            buttons = ButtonMaker()
            buttons.button_data('<<', f'rss back {user_id}')
            if data[1] == 'pause':
                buttons.button_data('Pause AllMyFeeds', f'rss uallpause {user_id}')
            elif data[1] == 'resume':
                buttons.button_data('Resume AllMyFeeds', f'rss uallresume {user_id}')
            elif data[1] == 'unsubscribe':
                buttons.button_data('Unsub AllMyFeeds', f'rss uallunsub {user_id}')
            buttons.button_data('Close', f'rss close {user_id}')
            await editMessage( f'Send one or more rss titles separated by space to {data[1]}.\n\n<i>Timeout: 60s.</i>', message, buttons.build_menu(2))
            pfunc = partial(rssUpdate, query=query, state=data[1])
            await event_handler(client, query, pfunc)
    elif data[1] == 'edit':
        handler_dict[user_id] = False
        if len(rss_dict.get(int(data[2]), {})) == 0:
            await query.answer('No subscriptions!', show_alert=True)
        else:
            await query.answer()
            buttons = ButtonMaker()
            buttons.button_data('<<', f'rss back {user_id}')
            buttons.button_data('Close', f'rss close {user_id}')
            msg = '''Send one or more rss titles with new filters or command separated by new line.
Examples:
Title1 c: mirror exf: none inf: 1080 or 720 opt: up: remote:path/subdir
Title2 c: none inf: none opt: none
Note: Only what you provide will be edited, the rest will be the same like example 2: exf will stay same as it is.

<i>Timeout: 60s.</i>
            '''
            await editMessage(msg, message, buttons.build_menu(2))
            pfunc = partial(rssEdit, query=query)
            await event_handler(client, query, pfunc)
    elif data[1].startswith('uall'):
        handler_dict[user_id] = False
        if len(rss_dict.get(int(data[2]), {})) == 0:
            await query.answer('No subscriptions!', show_alert=True)
            return
        await query.answer()
        if data[1].endswith('unsub'):
            async with rss_dict_lock:
                del rss_dict[int(data[2])]
            if DATABASE_URL:
                await DbManger().rss_delete(int(data[2]))
            await updateRssMenu(query)
        elif data[1].endswith('pause'):
            async with rss_dict_lock:
                for title in list(rss_dict[int(data[2])].keys()):
                    rss_dict[int(data[2])][title]['paused'] = True
            if DATABASE_URL:
                await DbManger().rss_update(int(data[2]))
        elif data[1].endswith('resume'):
            async with rss_dict_lock:
                for title in list(rss_dict[int(data[2])].keys()):
                    rss_dict[int(data[2])][title]['paused'] = False
            if scheduler.state == 2:
                scheduler.resume()
            if DATABASE_URL:
                await DbManger().rss_update(int(data[2]))
        await updateRssMenu(query)
    elif data[1].startswith('all'):
        if len(rss_dict) == 0:
            await query.answer('No subscriptions!', show_alert=True)
            return
        await query.answer()
        if data[1].endswith('unsub'):
            async with rss_dict_lock:
                rss_dict.clear()
            if DATABASE_URL:
                await DbManger().trunc_table('rss')
            await updateRssMenu(query)
        elif data[1].endswith('pause'):
            async with rss_dict_lock:
                for user in list(rss_dict.keys()):
                    for title in list(rss_dict[user].keys()):
                        rss_dict[int(data[2])][title]['paused'] = True
            if scheduler.running:
                scheduler.pause()
            if DATABASE_URL:
                await DbManger().rss_update_all()
        elif data[1].endswith('resume'):
            async with rss_dict_lock:
                for user in list(rss_dict.keys()):
                    for title in list(rss_dict[user].keys()):
                        rss_dict[int(data[2])][title]['paused'] = False
            if scheduler.state == 2:
                scheduler.resume()
            elif not scheduler.running:
                addJob(config_dict['RSS_DELAY'])
                scheduler.start()
            if DATABASE_URL:
                await DbManger().rss_update_all()
    elif data[1] == 'deluser':
        if len(rss_dict) == 0:
            await query.answer('No subscriptions!', show_alert=True)
        else:
            await query.answer()
            buttons = ButtonMaker()
            buttons.button_data('<<', f'rss back {user_id}')
            buttons.button_data('Close', f'rss close {user_id}')
            msg = 'Send one or more user_id separated by space to delete their resources.\n\n<i>Timeout: 60s.</i>'
            await editMessage(msg, message, buttons.build_menu(2))
            pfunc = partial(rssDelete, query=query)
            await event_handler(client, query, pfunc)
    elif data[1] == 'listall':
        if not rss_dict:
            await query.answer('No subscriptions!', show_alert=True)
        else:
            await query.answer()
            start = int(data[3])
            await rssList(query, start, all_users=True)
    elif data[1] == 'shutdown':
        if scheduler.running:
            await query.answer()
            scheduler.shutdown(wait=False)
            await sleep(0.5)
            await updateRssMenu(query)
        else:
            await query.answer('Already Stopped!', show_alert=True)
    elif data[1] == 'start':
        if not scheduler.running:
            await query.answer()
            addJob(config_dict['RSS_DELAY'])
            scheduler.start()
            await updateRssMenu(query)
        else:
            await query.answer('Already Running!', show_alert=True)


async def rssMonitor():
    if not config_dict['RSS_CHAT_ID']:
        LOGGER.warning('RSS_CHAT_ID not added! Shutting down rss scheduler...')
        scheduler.shutdown(wait=False)
        return
    if len(rss_dict) == 0:
        scheduler.pause()
        return
    all_paused = True
    for user, items in list(rss_dict.items()):
        for title, data in list(items.items()):
            await sleep(0)
            try:
                if data['paused']:
                    continue
                async with ClientSession(trust_env=True) as session:
                    async with session.get(data['link']) as res:
                        html = await res.text()
                rss_d = feedparse(html)
                try:
                    last_link = rss_d.entries[0]['links'][1]['href']
                except IndexError:
                    last_link = rss_d.entries[0]['link']
                last_title = rss_d.entries[0]['title']
                if data['last_feed'] == last_link or data['last_title'] == last_title:
                    all_paused = False
                    continue
                all_paused = False
                feed_count = 0
                while True:
                    try:
                        await sleep(10)
                    except:
                        raise RssShutdownException('Rss Monitor Stopped!')
                    try:
                        item_title = rss_d.entries[feed_count]['title']
                        try:
                            url = rss_d.entries[feed_count]['links'][1]['href']
                        except IndexError:
                            url = rss_d.entries[feed_count]['link']
                        if data['last_feed'] == url or data['last_title'] == item_title:
                            break
                    except IndexError:
                        LOGGER.warning(f'Reached Max index no. {feed_count} for this feed: {title}. Maybe you need to use less RSS_DELAY to not miss some torrents')
                        break
                    parse = True
                    for flist in data['inf']:
                        if all(x not in item_title.lower() for x in flist):
                            parse = False
                            feed_count += 1
                            break
                    for flist in data['exf']:
                        if any(x in item_title.lower() for x in flist):
                            parse = False
                            feed_count += 1
                            break
                    if not parse:
                        continue
                    if command := data['command']:
                        options = opt if (opt := data['options']) else ''
                        feed_msg = f"/{command.replace('/', '')} {url} {options}"
                    else:
                        feed_msg = f"<b>Name: </b><code>{item_title.replace('>', '').replace('<', '')}</code>\n\n"
                        feed_msg += f"<b>Link: </b><code>{url}</code>"
                    feed_msg += f"\n<b>Tag: </b><code>{data['tag']}</code> <code>{user}</code>"
                    await sendRss(feed_msg)
                    feed_count += 1
                async with rss_dict_lock:
                    if user not in rss_dict or not rss_dict[user].get(title, False):
                        continue
                    rss_dict[user][title].update({'last_feed': last_link, 'last_title': last_title})
                await DbManger().rss_update(user)
                LOGGER.info(f'Feed Name: {title}')
                LOGGER.info(f'Last item: {last_link}')
            except RssShutdownException as ex:
                LOGGER.info(ex)
                break
            except Exception as e:
                LOGGER.error(f"{e} Feed Name: {title} - Feed Link: {data['link']}")
                continue
    if all_paused:
        scheduler.pause()


def addJob(delay):
    scheduler.add_job(rssMonitor, trigger=IntervalTrigger(seconds=delay), id='0', name='RSS', misfire_grace_time=15,
                      max_instances=1, next_run_time=datetime.now()+timedelta(seconds=20), replace_existing=True)


addJob(config_dict['RSS_DELAY'])
scheduler.start()
bot.add_handler(MessageHandler(getRssMenu, filters=command(BotCommands.RssCommand) & CustomFilters.authorized))
bot.add_handler(CallbackQueryHandler(rssListener, filters=regex('^rss')))