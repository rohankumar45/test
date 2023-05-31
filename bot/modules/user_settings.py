from aiofiles.os import path as aiopath, mkdir
from asyncio import sleep
from functools import partial
from html import escape
from os import path as ospath, getcwd
from PIL import Image
from pyrogram import Client
from pyrogram.filters import command, regex, create
from pyrogram.handlers import CallbackQueryHandler, MessageHandler
from pyrogram.types import CallbackQuery, Message
from time import time

from bot import bot, bot_loop, user_data, config_dict, DATABASE_URL
from bot.helper.ext_utils.bot_utils import update_user_ldata, get_readable_time, is_premium_user, get_readable_file_size, UserDaily, sync_to_async, new_thread, new_task
from bot.helper.ext_utils.conf_loads import intialize_savebot
from bot.helper.ext_utils.db_handler import DbManger
from bot.helper.ext_utils.force_mode import ForceMode
from bot.helper.ext_utils.fs_utils import clean_target
from bot.helper.ext_utils.help_messages import UsetString
from bot.helper.ext_utils.telegram_helper import content_dict, TeleContent
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage, copyMessage, auto_delete_message, sendPhoto, editPhoto, deleteMessage, editMessage, sendCustom


handler_dict = {}


async def get_user_settings(from_user, data: str, uset_data: str):
    buttons = ButtonMaker()
    user_id = from_user.id
    thumbpath = ospath.join('thumbnails', f'{user_id}.jpg')
    rclone_path = ospath.join('rclone', f'{user_id}.conf')
    user_dict = user_data.get(user_id, {})
    premium_left = status_user = daily_limit = ''
    image = None

    if not data:
        mergevid, buttonkey, buttondata = ('ENABLE ✅', '✅ Merge Videos', 'mergevid') if user_dict.get('merge_vid') else ('DISABLE', 'Merge Videos', 'mergevid')
        buttons.button_data(buttonkey, f'userset {user_id} {buttondata}', 'header')

        sendpm, buttonkey, buttondata = ('ENABLE ✅', '✅ Send PM', 'sendpm') if user_dict.get('enable_pm') else ('DISABLE', 'Send PM', 'sendpm')
        buttons.button_data(buttonkey, f'userset {user_id} {buttondata}')

        sendss, buttonkey, buttondata = ('ENABLE ✅', '✅ Screenshot', 'imgss') if user_dict.get('enable_ss') else ('DISABLE', 'Screenshot', 'imgss')
        buttons.button_data(buttonkey, f'userset {user_id} {buttondata}')

        AD = config_dict['AS_DOCUMENT']
        ltype, buttonkey, buttondata = ('DOCUMENT', '✅ As Document', 'doc') if not user_dict and AD or user_dict.get('as_doc') else ('MEDIA', 'As Document', 'doc')
        buttons.button_data(buttonkey, f'userset {user_id} {buttondata}')

        MG = config_dict['MEDIA_GROUP']
        mediagroup, buttonkey, buttondata = ('ENABLE ✅', '✅ As Group', 'mgroup') if user_dict.get('media_group') or 'media_group' not in user_dict and MG else ('DISABLE', 'As Group', 'mgroup')
        buttons.button_data(buttonkey, f'userset {user_id} {buttondata}')

        prename = user_dict.get('user_prename', 'NOT SET')
        buttons.button_data('✅ Prename' if user_dict.get('user_prename') else 'Prename', f'userset {user_id} setdata prename')

        sufname = user_dict.get('user_sufname', 'NOT SET')
        buttons.button_data('✅ Sufname' if user_dict.get('user_sufname') else 'Sufname', f'userset {user_id} setdata sufname')

        remname = user_dict.get('user_remname', '')
        buttons.button_data('✅ Remname' if remname else 'Remname', f'userset {user_id} setdata remname')

        thumbmsg, buttonkey = ('EXISTS ✅', '✅ Thumbnail') if await aiopath.exists(thumbpath) else ('NOT SET', 'Thumbnail')
        buttons.button_data(buttonkey, f'userset {user_id} setdata sthumb')

        dumpid, buttonkey = (f"<code>{user_dict.get('dump_id')}</code>", '✅ Dump ID') if user_dict.get('dump_id') else ('<b>NOT SET</b>', 'Dump ID')
        buttons.button_data(buttonkey, f'userset {user_id} setdata dumpid')

        gdxmsg, buttonkey = ('CUSTOM ✅', '✅ Custom GDX') if user_dict.get('cus_gdrive') else ('GLOBAL', 'Custom GDX')
        buttons.button_data(buttonkey, f'userset {user_id} setdata gdx')

        rccmsg, buttonkey = ('EXISTS ✅', '✅ RClone') if await aiopath.exists(rclone_path) else ('NOT SET', 'RClone')
        buttons.button_data(buttonkey, f'userset {user_id} setdata rcc')

        YOPT = config_dict['YT_DLP_OPTIONS']
        buttonkey = '✅ YT-DLP'
        if user_dict.get('yt_opt'):
            yto = f"\n<b><code>{escape(user_dict['yt_opt'])}</code></b>"
        elif 'yt_opt' not in user_dict and YOPT:
            yto = f"\n<b><code>{escape(YOPT)}</code></b>"
        else:
            buttonkey = 'YT-DLP'
            yto = '<b>NONE</b>'
        buttons.button_data(buttonkey, f'userset {user_id} setdata yto')

        buttons.button_data('Caption', f'userset {user_id} capmode')
        buttons.button_data('Zip Mode', f'userset {user_id} zipmode')
        sesmsg, buttonkey = ('ENABLE ✅', '✅ Session String') if user_dict.get('user_string') else ('DISABLE', 'Session String')
        buttons.button_data(buttonkey, f'userset {user_id} setdata session')

        capmode = user_dict.get('user_cap', 'mono')
        custom_cap = 'ENABLE ✅' if user_dict.get('user_caption') else 'NOT SET'
        if config_dict['PREMIUM_MODE']:
            user_premi = user_dict.get('is_premium')
            if (time_data := user_dict.get('premium_left')) and user_premi and user_id != config_dict['OWNER_ID']:
                if time_data  - time() <= 0:
                    await update_user_ldata(user_id, 'premium_left', -1)
                    await update_user_ldata(user_id, 'is_premium', False)
                else:
                    premium_left = f'<b>├ </b>Premium Left: <b>{get_readable_time(time_data - time())}</b>\n'
            if user_id != config_dict['OWNER_ID']:
                status_user = '<b>├ </b>Status: <b>PREMIUM</b>\n' if user_premi else '<b>├ </b>Status: <b>NORMAL</b>\n'
        if config_dict['DAILY_MODE']:
            if not is_premium_user(user_id):
                await UserDaily(user_id).get_daily_limit()
                daily_limit = f"<b>├ </b>Daily Limit: <b>{get_readable_file_size(user_data[user_id]['daily_limit'])}/{config_dict['DAILY_LIMIT_SIZE']}GB</b>\n"
                daily_limit += f"<b>├ </b>Reset Time: <b>{get_readable_time(user_data[user_id]['reset_limit'] - time())}</b>\n"
        text = "<b>USER SETTINGS</b>\n"\
            f"<b>┌ </b>Settings For: <b>{from_user.mention}</b>\n"\
            f"{status_user}"\
            f"{premium_left}"\
            f"{daily_limit}"\
            f"<b>├ </b>Leech Type: <b>{ltype}</b>\n"\
            f"<b>├ </b>As Group: <b>{mediagroup}</b>\n"\
            f"<b>├ </b>Thumbnail: <b>{thumbmsg}</b>\n"\
            f"<b>├ </b>PM Mode: <b>{sendpm}</b>\n"\
            f"<b>├ </b>SS Mode: <b>{sendss}</b>\n"\
            f"<b>├ </b>GDX Mode: <b>{gdxmsg}</b>\n"\
            f"<b>├ </b>RClone: <b>{rccmsg}</b>\n"\
            f"<b>├ </b>Dump ID: {dumpid}\n"\
            f"<b>├ </b>Caption: <b>{capmode.upper()}</b>\n"\
            f"<b>├ </b>Prename: <b>{prename}</b>\n"\
            f"<b>├ </b>Sufname: <b>{sufname}</b>\n"\
            f"<b>├ </b>Merge Videos: <b>{mergevid}</b>\n"\
            f"<b>├ </b>Custom Caption: <b>{custom_cap}</b>\n"\
            f"<b>├ </b>Session String: <b>{sesmsg}</b>\n"\
            f"<b>└ </b>YT-DLP Options: {yto}\n\n"
        if remname:
            text += f"<b>Remname:</b> <code>{remname[0:450]}</code>\n\n"
        text += f"<i>Leech Split Size ~ {get_readable_file_size(config_dict['LEECH_SPLIT_SIZE'])}</i>"

    elif data == 'capmode':
        ex_cap = 'Thor: Love and Thunder (2022) 1080p.mkv'
        if user_dict.get('user_prename'):
            ex_cap = f"{user_dict.get('user_prename')} {ex_cap}"
        if user_dict.get('user_sufname'):
            fname, ext = ex_cap.rsplit('.', maxsplit=1)
            ex_cap = f"{fname} {user_dict.get('user_sufname')}.{ext}"
        if user_dict.get('user_cap') == 'italic':
            user_capmode, image, ex_cap = ('ITALIC', config_dict['IMAGE_ITALIC'], f"<i>{ex_cap}</i>")
            buttons  = cap_buttons(buttons, user_id, user_dict, "normal", "mono", "bold")
        elif user_dict.get('user_cap') == 'bold':
            user_capmode, image, ex_cap = ('BOLD', config_dict['IMAGE_BOLD'], f"<b>{ex_cap}</b>")
            buttons  = cap_buttons(buttons, user_id, user_dict, "normal", "mono", "italic")
        elif user_dict.get('user_cap') == 'normal':
            user_capmode, image = ('NORMAL', config_dict['IMAGE_NORMAL'])
            buttons  = cap_buttons(buttons, user_id, user_dict, "mono", "italic", "bold")
        else:
            user_capmode, image, ex_cap = ('MONO', config_dict['IMAGE_MONO'], f"<code>{ex_cap}</code>")
            buttons  = cap_buttons(buttons, user_id, user_dict, "normal", "bold", "italic")

        if user_dict.get('user_caption'):
            custom_cap = f"\n<code>{escape(user_dict.get('user_caption'))}</code>"
            if user_dict.get('user_fnamecap'):
                fname_cup = '<b>├ </b>FName Caption: <b>ENABLE</b>\n'
            else:
                fname_cup = '<b>├ </b>FName Caption: <b>DISABLE</b>\n'
                user_capmode, image, ex_cap = ('DISABLE', config_dict['IMAGE_CAPTION'], '<b>DISABLE</b>')
        else:
            custom_cap, fname_cup= '<b>DISABLE</b>', ''
        text = "<b>CAPTION SETTINGS</b>\n" \
            f"<b>┌ </b>Caption Settings: <b>{from_user.mention}</b>\n" \
            f"<b>├ </b>Caption Mode: <b>{user_capmode}</b>\n" \
            f"{fname_cup}" \
            f"<b>└ </b>Custom Caption: {custom_cap}\n\n" \
            f"<b>Example:</b> {ex_cap}"

    elif data == 'zipmode':
        but_dict = {'zfolder': ['Folders', f'userset {user_id} zipmode zfolder'],
                    'zfpart': ['Cloud Part', f'userset {user_id} zipmode zfpart'],
                    'zeach': ['Each Files', f'userset {user_id} zipmode zeach'],
                    'zpart': ['Part Mode', f'userset {user_id} zipmode zpart'],
                    'auto': ['Auto Mode', f'userset {user_id} zipmode auto']}
        def_data = but_dict[uset_data][0]
        but_dict[uset_data][0] = f'✅ {def_data}'
        for btn in but_dict.values():
            buttons.button_data(btn[0], btn[1])
        buttons.button_data('<<', f'userset {user_id} back')
        part_size = get_readable_file_size(config_dict['LEECH_SPLIT_SIZE'])
        image = config_dict['IMAGE_ZIP']
        text = '<b>ZIP MODE SETTINGS</b>\n' \
               '⁍ <b>Folders/Default:</b> Zip file/folder\n' \
              f'⁍ <b>Cloud Part:</b> Zip file/folder as part {part_size} (Mirror Cmds)\n' \
               '⁍ <b>Each Files:</b> Zip each file in folder/subfolder\n' \
              f'⁍ <b>Part Mode:</b> Zip each file in folder/subfolder as part if size more than {part_size} (Mirror Cmds)\n' \
              f'⁍ <b>Auto Mode:</b> Zip only file in folder/subfolder if size more than {part_size}\n\n' \
              f'<b>Current Mode:</b> {def_data}\n\n' \
               '<i>*Seed torrent only working in <b>Deafult Mode</b></i>'

    elif data == 'setdata':
        if uset_data == 'sthumb':
            if await aiopath.exists(thumbpath):
                text = 'This is your current thumbnail.'
                buttons.button_data('Change Thumbnail', f'userset {user_id} prepare sthumb')
                buttons.button_data('Delete Thumbnail', f'userset {user_id} rthumb')
            else:
                text = 'Send a photo to save it as custom thumbnail.'
                buttons.button_data('Set Thumbnail', f'userset {user_id} prepare sthumb')
        if uset_data == 'rcc':
            text, image = 'Send a valid file for <b>config.conf</b>.', config_dict['IMAGE_RCLONE']
            if await aiopath.exists(rclone_path):
                buttons.button_data('Change RClone', f'userset {user_id} prepare rcc')
                buttons.button_data('Delete RClone', f'userset {user_id} rmrcc')
            else:
                buttons.button_data('Set RClone', f'userset {user_id} prepare rcc')
        elif uset_data == 'setcap':
            text, image = UsetString.CAP.replace('Timeout: 60s.', ''), config_dict['IMAGE_CAPTION']
            if user_dict.get('user_caption'):
                buttons.button_data('Change Caption', f'userset {user_id} prepare setcap')
                buttons.button_data('Remove Caption', f'userset {user_id} rsetcap')
            else:
                buttons.button_data('Set Caption', f'userset {user_id} prepare setcap')
            buttons.button_data('<<', f'userset {user_id} capmode')
        elif uset_data == 'dumpid':
            text, image = UsetString.DUMP.replace('Timeout: 60s.', ''), config_dict['IMAGE_DUMID']
            if user_dict.get('dump_id'):
                buttons.button_data('Change Dump', f'userset {user_id} prepare dumpid')
                buttons.button_data('Remove ID', f'userset {user_id} rdumpid')
                log_title = user_dict.get('log_title')
                buttons.button_data('✅ Log Title' if log_title else 'Log Title', f'userset {user_id} setdata dumpid {not log_title}')
            else:
                buttons.button_data('Set Dump', f'userset {user_id} prepare dumpid')
        elif uset_data == 'gdx':
            text, image = UsetString.GDX.replace('Timeout: 60s.', ''), config_dict['IMAGE_GD']
            if user_dict.get('cus_gdrive'):
                buttons.button_data('Change GDX', f'userset {user_id} prepare gdx')
                buttons.button_data('Remove GDX', f'userset {user_id} rgdx')
            else:
                buttons.button_data("Set GDX", f"userset {user_id} prepare gdx")
        elif uset_data == 'prename':
            text, image = UsetString.PRE.replace('Timeout: 60s.', ''), config_dict['IMAGE_PRENAME']
            if user_dict.get('user_prename'):
                buttons.button_data('Change Prename', f'userset {user_id} prepare prename')
                buttons.button_data('Remove Prename', f'userset {user_id} rprename')
            else:
                buttons.button_data('Set Prename', f'userset {user_id} prepare prename')
        elif uset_data == 'sufname':
            text, image = UsetString.SUF.replace('Timeout: 60s.', ''), config_dict['IMAGE_SUFNAME']
            if user_dict.get('user_sufname'):
                buttons.button_data('Change Sufname', f'userset {user_id} prepare sufname')
                buttons.button_data('Remove Sufname', f'userset {user_id} rsufname')
            else:
                buttons.button_data('Set Sufname', f'userset {user_id} prepare sufname')
        elif uset_data == 'remname':
            text, image = UsetString.REM.replace('Timeout: 60s.', ''), config_dict['IMAGE_REMNAME']
            if user_dict.get('user_remname'):
                buttons.button_data('Change Remname', f'userset {user_id} prepare remname')
                buttons.button_data('Remove Remname', f'userset {user_id} rremname')
            else:
                buttons.button_data('Set Remname', f'userset {user_id} prepare remname')
        elif uset_data == 'session':
            text, image = UsetString.SES.replace('Timeout: 60s.', ''), config_dict['IMAGE_USER']
            if user_dict.get('user_string'):
                buttons.button_data('Change Session', f'userset {user_id} prepare session')
                buttons.button_data('Remove Session', f'userset {user_id} rsession')
            else:
                buttons.button_data('Set Session', f'userset {user_id} prepare session')
        elif uset_data == 'yto':
            text, image = UsetString.YT.replace('Timeout: 60s.', ''), config_dict['IMAGE_YT']
            if user_dict.get('yt_opt') or config_dict['YT_DLP_OPTIONS']:
                buttons.button_data('Change YT-DLP', f'userset {user_id} prepare yto')
                buttons.button_data('Remove YT-DLP', f'userset {user_id} ryto')
            else:
                buttons.button_data('Set YT-DLP', f'userset {user_id} prepare yto')
        if uset_data != 'setcap':
            buttons.button_data('<<', f'userset {user_id} back')

    elif data == 'prepare':
        msg_thumb = 'Send a photo to to change current thumbnail.\n\n<i>Timeout: 60s.</i>' if await aiopath.exists(thumbpath) else \
                    'Send a photo to save it as custom thumbnail.\n\n<i>Timeout: 60s.</i>'
        msg_rclone = 'Send new valid file to change current <b>config.conf</b>.\n\n<i>Timeout: 60s.</i>' if await aiopath.exists(rclone_path) else \
                    'Send a valid file for <b>config.conf</b>.\n\n<i>Timeout: 60s.</i>'
        prepare_dict = {'sthumb': (msg_thumb, image),
                        'rcc': (msg_rclone, config_dict['IMAGE_RCLONE']),
                        'dumpid': (UsetString.DUMP, config_dict['IMAGE_DUMID']),
                        'gdx': (UsetString.GDX, config_dict['IMAGE_GD']),
                        'setcap': (UsetString.CAP, config_dict['IMAGE_CAPTION']),
                        'prename': (UsetString.PRE, config_dict['IMAGE_PRENAME']),
                        'sufname': (UsetString.SUF, config_dict['IMAGE_SUFNAME']),
                        'remname': (UsetString.REM, config_dict['IMAGE_REMNAME']),
                        'session': (UsetString.SES, config_dict['IMAGE_USER']),
                        'yto': (UsetString.YT, config_dict['IMAGE_YT'])}
        text, image = prepare_dict[uset_data]
        buttons.button_data('<<', f'userset {user_id} setdata {uset_data}')

    buttons.button_data('Close', f'userset {user_id} close')
    return text, image, buttons.build_menu(2)


async def update_user_settings(query: CallbackQuery, data: str=None, uset_data: str=None):
    text, image, button = await get_user_settings(query.from_user, data, uset_data)
    if not image:
        if await aiopath.exists(thumb:= ospath.join('thumbnails', f'{query.from_user.id}.jpg')):
            image = thumb
        else:
            image = config_dict['IMAGE_USETIINGS']
    await editPhoto(text, query.message, image, button)


async def set_user_settings(_, message: Message, query: CallbackQuery, key: str):
    user_id = message.from_user.id
    handler_dict[user_id] = False
    value = message.text
    is_passed = True
    if 'cus_gdrive' in key:
        value = value.split()
        await update_user_ldata(user_id, key[0], value[0])
        if len(value) == 2:
            await update_user_ldata(user_id, key[1], value[1].rstrip('/'))
        await deleteMessage(message)
        await update_user_settings(query)
        return
    if key == 'dump_id':
        if value.startswith('-100') and len(value) == 14:
            try:
                value = int(value)
            except:
                is_passed = False
        else:
            is_passed = False
    if is_passed:
        await update_user_ldata(user_id, key, value)
        await deleteMessage(message)
        if key == 'dump_id':
            await update_user_settings(query, 'setdata', 'dumpid')
        else:
            data = 'capmode' if key == 'user_caption' else None
            await update_user_settings(query, data)
        if key == 'user_string':
            bot_loop.create_task(intialize_savebot(value, True, user_id))
    else:
        await update_user_settings(query, 'setdata', 'dumpid')
        msg = await sendMessage('Invalid ID!', message)
        await auto_delete_message(message, msg, stime=5)


async def set_thumb(_, message: Message, query: CallbackQuery):
    user_id = query.from_user.id
    handler_dict[user_id] = False
    path = 'thumbnails'
    msg = await sendMessage('<i>Processing, please wait...</i>', message)
    if not await aiopath.isdir(path):
        await mkdir(path)
    photo_dir = await message.download()
    des_dir = ospath.join(path, f'{user_id}.jpg')
    await sync_to_async(Image.open(photo_dir).convert('RGB').save, des_dir, 'JPEG')
    await clean_target(photo_dir)
    await update_user_ldata(user_id, 'thumb', des_dir)
    await deleteMessage(message, msg)
    await update_user_settings(query)
    if DATABASE_URL:
        await DbManger().update_user_doc(user_id, 'thumb', des_dir)


async def add_rclone(_, message: Message, query: CallbackQuery):
    user_id = message.from_user.id
    handler_dict[user_id] = False
    path = ospath.join(getcwd(), 'rclone')
    if not await aiopath.isdir(path):
        await mkdir(path)
    if message.document.file_name.endswith('.conf'):
        des_dir = ospath.join(path, f'{user_id}.conf')
        msg = await sendMessage('<i>Processing, please wait...</i>', message)
        await message.download(file_name=des_dir)
        await update_user_ldata(user_id, 'rclone', ospath.join('rclone', f'{user_id}.conf'))
        await deleteMessage(message, msg)
        await update_user_settings(query)
        if DATABASE_URL:
            await DbManger().update_user_doc(user_id, 'rclone', des_dir)
    else:
        await update_user_settings(query, 'setdata', 'rcc')
        msg = await sendMessage('Invalid RClone file!', message)
        await auto_delete_message(message, msg, stime=5)


def cap_buttons(buttons: ButtonMaker, user_id: int, user_dict: dict, *args):
    caption, fnamecap = user_dict.get('user_caption'), user_dict.get('user_fnamecap', True)
    if not user_dict or fnamecap:
        for mode in args:
            buttons.button_data(mode.title(), f"userset {user_id} cap{mode}")
    buttons.button_data('<<', f'userset {user_id} back')
    buttons.button_data('✅ Custom Caption' if caption else 'Custom Caption', f'userset {user_id} setdata setcap')
    if caption:
        buttons.button_data('✅ FCaption' if fnamecap else 'FCaption', f'userset {user_id} fcapname')
    return buttons


@new_thread
async def edit_user_settings(client: Client, query: CallbackQuery):
    message = query.message
    user_id = query.from_user.id
    data = query.data.split()
    user_dict = user_data.get(user_id, {})
    premi_features = {'capmode': 'user_caption',
                      'dumpid': 'dump_id',
                      'gdx': 'cus_gdrive',
                      'mgroup': 'media_group',
                      'prename': 'user_prename',
                      'sufname': 'user_sufname',
                      'remname': 'user_remname',
                      'session': 'user_string',
                      'sendpm': 'enable_pm',
                      'mergevid': 'merge_vid',
                      'imgss': 'enable_ss'}
    pre_data = data[3] if data[2] == 'setdata' else data[2]
    if config_dict['PREMIUM_MODE'] and not is_premium_user(user_id) and pre_data in premi_features:
        await query.answer('Upss, Premium User Required!', show_alert=True)
        is_modified = False
        for key in list(premi_features.values()):
            if user_dict.get(key):
                is_modified = True
                await update_user_ldata(user_id, key, False)
        if is_modified:
            await update_user_settings(query)
        return
    if user_id != int(data[1]):
        await query.answer('Not Yours!', show_alert=True)
    elif data[2] == 'setdata':
        handler_dict[user_id] = False
        await query.answer()
        if data[3] == 'dumpid' and len(data) == 5:
            await update_user_ldata(user_id, 'log_title', eval(data[4]))
        await update_user_settings(query, data[2], data[3])
    elif data[2] == 'doc':
        await update_user_ldata(user_id, 'as_doc', not user_dict.get('as_doc', False))
        await query.answer(f"Your File Will Deliver As {'Document' if user_dict.get('as_doc') else 'Media'}!", show_alert=True)
        await update_user_settings(query)
    elif data[2] == 'mgroup':
        await update_user_ldata(user_id, 'media_group', not user_dict.get('media_group', False))
        await query.answer("Leech File(s) Will Send As Media Group!", show_alert=True) if user_dict.get('media_group') else await query.answer()
        await update_user_settings(query)
    elif data[2] == 'ryto':
        await query.answer("YT-DLP Quality Removed!", show_alert=True)
        await update_user_ldata(user_id, 'yt_opt', '')
        await update_user_settings(query)
    elif data[2] == 'back':
        handler_dict[user_id] = False
        await query.answer()
        await update_user_settings(query)
    elif data[2] == 'fcapname':
        await update_user_ldata(user_id, 'user_fnamecap', not user_dict.get('user_fnamecap', False))
        await query.answer(f"File Name Caption Has Been {'Enabled' if user_dict.get('user_fnamecap') else 'Disable'}!", show_alert=True)
        await update_user_settings(query, 'capmode')
    elif data[2] == 'rsetcap':
        await update_user_ldata(user_id, 'user_caption', False)
        await update_user_ldata(user_id, 'user_fnamecap', True)
        await query.answer("Your Custom Caption Has Been Deleted!", show_alert=True)
        await update_user_settings(query, 'capmode')
    elif data[2] == 'rdumpid':
        await update_user_ldata(user_id, 'dump_id', False)
        await update_user_ldata(user_id, 'log_title', False)
        await query.answer("Your Dump ID Has Been Deleted!", show_alert=True)
        await update_user_settings(query)
    elif data[2] == 'rgdx':
        await update_user_ldata(user_id, 'cus_gdrive', False)
        await update_user_ldata(user_id, 'cus_index', False)
        await query.answer("Custom GD Has Been Disable!", show_alert=True)
        await update_user_settings(query)
    elif data[2] == 'rprename':
        await update_user_ldata(user_id, 'user_prename', False)
        await query.answer("Your Prename Has Been Deleted!", show_alert=True)
        await update_user_settings(query)
    elif data[2] == 'rsufname':
        await update_user_ldata(user_id, 'user_sufname', False)
        await query.answer("Your Sufix Name Has Been Deleted!", show_alert=True)
        await update_user_settings(query)
    elif data[2] == 'rremname':
        await update_user_ldata(user_id, 'user_remname', False)
        await query.answer("Your Prefix Name Has Been Deleted!", show_alert=True)
        await update_user_settings(query)
    elif data[2] == 'rsession':
        await update_user_ldata(user_id, 'user_string', '')
        await query.answer("Your Session String Has Been Deleted!", show_alert=True)
        await intialize_savebot(user_id=user_id)
        await update_user_settings(query)
    elif data[2] == 'sendpm':
        await update_user_ldata(user_id, 'enable_pm', not user_dict.get('enable_pm', False))
        await query.answer(f"PM Mode Has Been {'Enable' if user_dict.get('enable_pm') else 'Disable'}!", show_alert=True)
        await update_user_settings(query)
    elif data[2] == 'mergevid':
        await update_user_ldata(user_id, 'merge_vid', not user_dict.get('merge_vid', False))
        await query.answer(f"Merge Videos Has Been {'Enable' if user_dict.get('merge_vid') else 'Disable'}!", show_alert=True)
        await update_user_settings(query)
    elif data[2] == 'imgss':
        await update_user_ldata(user_id, 'enable_ss', not user_dict.get('enable_ss', False))
        await query.answer(f"SS Mode Has Been {'Enable' if user_dict.get('enable_ss') else 'Disable'}!", show_alert=True)
        await update_user_settings(query)
    elif data[2] == 'capmode':
        await query.answer()
        await update_user_settings(query, data[2])
    elif data[2] == 'zipmode':
        try:
            zmode = data[3]
        except:
            zmode = user_dict.get('zipmode', 'zfolder')
        if zmode == user_dict.get('zipmode', '') and len(data) == 4:
            await query.answer('Already Selected!', show_alert=True)
            return
        await query.answer()
        await update_user_ldata(user_id, 'zipmode', zmode)
        await update_user_settings(query, data[2], zmode)
    elif data[2] == 'capmono':
        await update_user_ldata(user_id, 'user_cap', 'mono')
        await query.answer("Caption Change to Mono!", show_alert=True)
        await update_user_settings(query, 'capmode')
    elif data[2] == 'capitalic':
        await update_user_ldata(user_id, 'user_cap', 'italic')
        await query.answer("Caption Change to Italic!", show_alert=True)
        await update_user_settings(query, 'capmode')
    elif data[2] == 'capbold':
        await update_user_ldata(user_id, 'user_cap', 'bold')
        await query.answer("Caption Change to Bold!", show_alert=True)
        await update_user_settings(query, 'capmode')
    elif data[2] == 'capnormal':
        await update_user_ldata(user_id, 'user_cap', 'normal')
        await query.answer("Caption Change to Normal!", show_alert=True)
        await update_user_settings(query, 'capmode')
    elif data[2] == 'close':
        handler_dict[user_id] = False
        await query.answer()
        await deleteMessage(message, message.reply_to_message)
    elif data[2] == 'rthumb':
        if await aiopath.exists(thumb:= ospath.join('thumbnails', f'{user_id}.jpg')):
            await query.answer("Thumbnail Removed!", show_alert=True)
            await clean_target(thumb)
            await update_user_ldata(user_id, 'thumb', False)
            await update_user_settings(query)
            if DATABASE_URL:
                await DbManger().update_user_doc(user_id, 'thumb')
        else:
            await query.answer("Old Settings", show_alert=True)
            await update_user_settings(query)
    elif data[2] == 'rmrcc':
        if await aiopath.exists(rcpath:= ospath.join('rclone', f'{user_id}.conf')):
            await query.answer()
            await clean_target(rcpath)
            await update_user_ldata(user_id, 'rclone', '')
            await update_user_settings(query)
            if DATABASE_URL:
                await DbManger().update_user_doc(user_id, 'rclone')
        else:
            await query.answer("Old Settings", show_alert=True)
            await update_user_settings(query)
    elif data[2] == 'prepare':
        if data[3] == 'sthumb':
            photo, document = True, False
            pfunc = partial(set_thumb, query=query)
        elif data[3] == 'rcc':
            await query.answer()
            photo, document = False, True
            pfunc = partial(add_rclone, query=query)
        else:
            handler_dict[user_id] = True
            prepare_dict = {'dumpid': 'dump_id',
                            'gdx': ('cus_gdrive', 'cus_index'),
                            'setcap': 'user_caption',
                            'prename': 'user_prename',
                            'sufname': 'user_sufname',
                            'remname': 'user_remname',
                            'session': 'user_string',
                            'yto': 'yt_opt'}
            key = prepare_dict[data[3]]
            if key == 'dump_id':
                await query.answer('Don\'t forget add me to your chat!', show_alert=True)
            else:
                await query.answer()
            photo = document = False
            pfunc = partial(set_user_settings, query=query, key=key)
        await update_user_settings(query, data[2], data[3])
        await event_handler(client, query, pfunc, photo, document)

async def event_handler(client: Client, query: CallbackQuery, pfunc: partial, photo: bool=False, document: bool=False):
    user_id = query.from_user.id
    handler_dict[user_id] = True
    start_time = time()
    async def event_filter(_, __, event):
        if photo:
            mtype = event.photo
        elif document:
            mtype = event.document
        else:
            mtype = event.text
        user = event.from_user or event.sender_chat
        return bool(user.id == user_id and event.chat.id == query.message.chat.id and mtype)
    handler = client.add_handler(MessageHandler(pfunc, filters=create(event_filter)), group=-1)
    while handler_dict[user_id]:
        await sleep(0.5)
        if time() - start_time > 60:
            handler_dict[user_id] = False
            await update_user_settings(query)
    client.remove_handler(*handler)


@new_task
async def user_settings(_, message: Message):
    if config_dict['FUSERNAME'] and (fmsg:= await ForceMode(message).force_username):
        await auto_delete_message(message, fmsg)
        return
    msg, image, buttons = await get_user_settings(message.from_user, None, None)
    if await aiopath.exists(thumb:= ospath.join('thumbnails', f'{message.from_user.id}.jpg')):
        image = thumb
    await sendPhoto(msg, message, image or config_dict['IMAGE_USETIINGS'], buttons)


@new_task
async def set_premium_users(_, message: Message):
    if not config_dict['PREMIUM_MODE']:
        await sendMessage('<b>Premium Mode</b> is disable!', message)
        return
    reply_to = message.reply_to_message
    args = message.text.split()
    text = 'Reply to a user or send user ID with options (add/del) and duration time in day(s)'
    if not reply_to and len(args) == 1:
        await sendMessage(text, message)
        return
    if reply_to and len(args) > 1:
        premi_id = reply_to.from_user.id
        if args[1] == 'add':
            day = int(args[2])
    elif len(args) > 2:
        premi_id = int(args[2])
        if args[1] == 'add':
            day = int(args[3])
    else:
        await sendMessage(text, message)
        return
    user_text = ''
    if args[1] == 'add':
        duartion = int(time() + (86400 * day))
        text = f'😘 Yeay, <b>{premi_id}</b> has been added as <b>Premium User</b> for {day} day(s).'
        user_text = f'Yeay 😘, you have been added as <b>Premium User</b> for {day}(s).'
        await update_user_ldata(premi_id, 'premium_left', duartion)
        await update_user_ldata(premi_id, 'is_premium', True)
    elif args[1] == 'del':
        text = f'😑 Hmm, <b>{premi_id}</b> has been remove as <b>Premium User</b>!'
        user_text = f'Huhu 😑, you have been leased as <b>Premium User</b>!'
        await update_user_ldata(premi_id, 'premium_left', -1)
        await update_user_ldata(premi_id, 'is_premium', False)
    msg = await sendMessage(text, message)
    if user_text:
        await sendCustom(user_text, premi_id)
    await auto_delete_message(message, msg)


@new_task
async def reset_daily_limit(_, message: Message):
    reply_to = message.reply_to_message
    args = message.text.split()
    if not reply_to and len(args) == 1:
        await sendMessage('Reply to a user or send user ID to reset daily limit.', message)
        return
    if reply_to:
        user_id = reply_to.from_user.id
    elif len(args) > 1:
        user_id = int(args[1])
    await update_user_ldata(user_id, 'daily_limit', 1)
    await update_user_ldata(user_id, 'reset_limit', time() + 86400)
    msg = await sendMessage('Daily limit has been reset.', message)
    await auto_delete_message(message, msg)


async def send_users_settings(_, message: Message):
    contents = []
    msg = ''
    if len(user_data) == 0:
        await sendMessage('No user data!', message)
        return
    for index, (uid, data) in enumerate(user_data.items(), start=1):
        uname = user_data[uid].get('user_name')
        msg += f"<b><a href='https://t.me/{uname}'>{uname}</a></b>\n" \
                f'⁍ <b>User ID:</b> <code>{uid}</code>\n'
        for key, value in data.items():
            if key == 'reset_limit':
                value -= time()
                value = get_readable_time(0 if value <= 1 else value)
            elif key == 'daily_limit':
                value = f"{get_readable_file_size(value)}/{config_dict['DAILY_LIMIT_SIZE']}GB"
            elif key in ['user_cap', 'zipmode']:
                value = str(value).title()
            elif key in ['thumb', 'rclone']:
                value = 'Exists' if value else 'Not Exists'
            elif str(value).lower() == 'true' or key == 'user_string':
                value = 'Yes'
            elif str(value).lower() == 'false' or key == '':
                value = 'No'
            if key != 'user_name':
                msg += f"⁍ <b>{key.replace('_', ' ').title()}:</b> {escape(str(value))}\n"
        contents.append(str(index).zfill(3) + '. ' + msg + '\n')
        msg = ''
    tele = TeleContent(message)
    content_dict[message.id] = tele
    await tele.set_data(contents, f'<b>FOUND {len(contents)} USERS SETTINGS DATA</b>')
    text, buttons = await tele.get_content('usettings')
    await sendMessage(text, message, buttons)
    if len(contents) < 8:
        tele.cancel()
        del content_dict[message.id]


async def users_handler(_, query: CallbackQuery):
    message = query.message
    data = query.data.split()
    tele: TeleContent = content_dict.get(int(data[3]))
    if not tele and data[2] != 'close':
        await query.answer('Old Task!', show_alert=True)
    elif data[2] == 'close':
        if tele:
            tele.cancel()
            del content_dict[int(data[3])]
        await deleteMessage(message, message.reply_to_message)
    else:
        tdata = int(data[4]) if data[2] == 'foot' else int(data[3])
        text, buttons = await tele.get_content('usettings', data[2], tdata)
        if not buttons:
            await query.answer(text, show_alert=True)
            return
        await query.answer()
        await editMessage(text, message, buttons)


bot.add_handler(MessageHandler(set_premium_users, filters=command(BotCommands.UserSetPremiCommand) & CustomFilters.sudo))
bot.add_handler(MessageHandler(send_users_settings, filters=command(BotCommands.UsersCommand) & CustomFilters.sudo))
bot.add_handler(MessageHandler(reset_daily_limit, filters=command(BotCommands.DailyResetCommand) & CustomFilters.sudo))
bot.add_handler(MessageHandler(user_settings, filters=command(BotCommands.UserSetCommand) & CustomFilters.authorized))
bot.add_handler(CallbackQueryHandler(edit_user_settings, filters=regex('^userset')))
bot.add_handler(CallbackQueryHandler(users_handler, filters=regex('^usettings')))