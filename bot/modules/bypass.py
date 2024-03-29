from argparse import ArgumentParser
from pyrogram import Client
from pyrogram.filters import command
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message
from random import choice
from time import time
from urllib.parse import urlparse

from bot import bot, config_dict, user_data, LOGGER
from bot.helper.ddl_bypass.addon import SiteList
from bot.helper.ddl_bypass.bypass_link_generator import bypass_link
from bot.helper.ext_utils.bot_utils import get_readable_time, is_url, is_premium_user, get_link, action, get_date_time, sync_to_async, new_task, is_media
from bot.helper.ext_utils.exceptions import DirectDownloadLinkException
from bot.helper.ext_utils.force_mode import ForceMode
from bot.helper.ext_utils.multi import run_multi
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import auto_delete_message, sendMessage, editMessage, copyMessage, deleteMessage, sendPhoto


@new_task
async def bypass(client: Client, message: Message):
    input_list = message.text.split()
    try:
        args = parser.parse_args(input_list[1:])
    except:
        await sendMessage('Send link along with command or reply to link', message)
        return

    reply_to = message.reply_to_message
    user_id = message.from_user.id
    isSuperGroup = message.chat.type.name in ['SUPERGROUP', 'CHANNEL']

    if config_dict['PREMIUM_MODE']:
        if not is_premium_user(user_id):
            await sendMessage('This feature only for <b>Premium User</b>!', message)
            return

    if fmsg:= await ForceMode(message).run_force('fsub', 'funame', pm_mode='bypass_pm_message'):
        await auto_delete_message(message, fmsg, reply_to)
        return

    multi = args.multi
    if isinstance(multi, list):
        multi = multi[0]

    run_multi(bypass, client, message, multi, input_list, '')

    sites = SiteList()
    if not (url:= get_link(message)) and not is_url(url) or is_media(reply_to):
        text = '<b>Send link along with command or by replying to the link by command\n'
        text += f"GDSharer List:</b>\n{' ~ '.join(sites.gd_sharer)}\n\n"
        text += f"<b>DDL List:</b>\n{' ~ '.join(sites.ddl_list)}\n\n"
        text += f"<b>Bypass List:</b>\n{' ~ '.join(sites.bypass_list)}"
        msg = await sendMessage(text, message)
        await auto_delete_message(message, msg)
        return

    buttons = ButtonMaker()
    buttons.button_link('Source Link', url)
    host = urlparse(url).netloc
    bpmsg = await sendMessage(f'<i>Bypassing {host} link, please wait...</i>', message)
    LOGGER.info(f'Bypassing: {url}')
    result, start_time = '', time()

    try:
        if 'gofile.io' in host:
            result, _ = await sync_to_async(bypass_link, url)
        else:
            result = await sync_to_async(bypass_link, url)
    except DirectDownloadLinkException as err:
        LOGGER.info(f'Failed to bypass: {url}')
        if str(err).startswith('ERROR:'):
            err = str(err).replace('trying to generate direct', 'when trying bypass')
        elif 'No direct link function' in str(err):
            err = str(err).replace('No direct link function found for', 'Unsupport site for')
        await editMessage(f'{message.from_user.mention}, {err}', bpmsg)
        return

    if 'filecrypt.co' in url or 'psa.' in url or any(x in url for x in sites.fembed_list):
        result = result
    else:
        result = f'<code>{result}</code>'
    bmsg = '<b>BYPASS RESULT</b>\n'
    bmsg += f'<b>┌ Cc: </b>{message.from_user.mention}\n'
    bmsg += f'<b>├ ID: </b><code>{user_id}</code>\n'
    bmsg += f'<b>├ Action: </b>{action(message)}\n'
    bmsg += f'<b>├ Add: </b>{get_date_time(message)[0]}\n'
    bmsg += f"<b>├ At: </b>{get_date_time(message)[1]} ({config_dict['TIME_ZONE_TITLE']})\n"
    bmsg += f'<b>├ Elapsed: </b>{get_readable_time(time() - start_time) or "1s"}\n'
    bmsg += f'<b>└ Bypass Result:</b>\n{result}'

    if config_dict['ENABLE_IMAGE_MODE']:
        pmsg = await sendPhoto(bmsg, message, choice(config_dict['IMAGE_COMPLETE'].split()), buttons.build_menu(1))
        if pmsg:
            await deleteMessage(bpmsg)
            bpmsg = pmsg
        else:
            await editMessage(bmsg, bpmsg, buttons.build_menu(1))
    else:
        await editMessage(bmsg, bpmsg, buttons.build_menu(1))

    if chat_id:= config_dict['OTHER_LOG']:
        await copyMessage(chat_id, bpmsg, buttons.build_menu(1))

    if user_data.get(user_id, {}).get('enable_pm') and isSuperGroup:
        await copyMessage(user_id, bpmsg, buttons.build_menu(1))

    if isSuperGroup and (stime:= config_dict['AUTO_DELETE_UPLOAD_MESSAGE_DURATION']):
        await auto_delete_message(message, reply_to, stime=stime)


parser = ArgumentParser(description='Bypass args usage:', argument_default='')

parser.add_argument('link', nargs='*')
parser.add_argument('-i', nargs='+', default=0, dest='multi', type=int)

bot.add_handler(MessageHandler(bypass, filters=command(BotCommands.BypassCommand) & CustomFilters.authorized))