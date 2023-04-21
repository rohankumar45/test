from asyncio import sleep
from pyrogram import Client
from pyrogram.filters import regex
from pyrogram.handlers import CallbackQueryHandler
from pyrogram.types import CallbackQuery, Message

from bot import bot, config_dict, LOGGER
from bot.helper.ext_utils.bot_utils import action
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.message_utils import sendMessage
from bot.modules.mirror_leech import _mirror_leech
from bot.modules.ytdlp import _ytdl


incompte_dict = {}


async def set_incomplte_task(cid, link):
    message: Message = await bot.get_messages(cid, int(link.split('/')[-1]))
    if not message.empty:
        try:
            mesg = message.text.split('\n')
            if len(mesg) > 1 and mesg[1].startswith('Tag: '):
                try:
                    id_ = int(mesg[1].split()[-1])
                    message.from_user = await bot.get_users(id_)
                except Exception as e:
                    LOGGER.error(e)
            elif message.from_user.is_bot and (reply:= message.reply_to_message):
                message.from_user = reply.from_user
            uid = message.from_user.id
            incompte_dict.setdefault(uid, {'msgs': []})
            incompte_dict[uid]['msgs'].append(message)
        except Exception as e:
            LOGGER.error(e)


async def start_resume_task(client: Client, tasks: list):
    for msg in tasks:
        cmd = action(msg)[1:] + str(config_dict['CMD_SUFFIX'])
        isZip = extract = isQbit = isLeech = isYt = False
        def _check_cmd(cmds):
            if any(x == cmd for x in cmds):
                return True
        if _check_cmd(BotCommands.UnzipMirrorCommand):
            extract = True
        elif _check_cmd(BotCommands.ZipMirrorCommand):
            isZip = True
        elif _check_cmd(BotCommands.QbMirrorCommand):
            isQbit = True
        elif _check_cmd(BotCommands.QbUnzipMirrorCommand):
            extract = isQbit = True
        elif _check_cmd(BotCommands.QbZipMirrorCommand):
            isZip = isQbit = True
        elif _check_cmd(BotCommands.LeechCommand):
            isLeech = True
        elif _check_cmd(BotCommands.UnzipLeechCommand):
            extract = isLeech = True
        elif _check_cmd(BotCommands.ZipLeechCommand):
            isZip = isLeech = True
        elif _check_cmd(BotCommands.QbLeechCommand):
            isQbit = isLeech = True
        elif _check_cmd(BotCommands.QbUnzipLeechCommand):
            extract = isQbit = isLeech = True
        elif _check_cmd(BotCommands.QbZipLeechCommand):
            isZip = isQbit = isLeech = True
        elif _check_cmd(BotCommands.YtdlCommand):
            isYt = True
        elif _check_cmd(BotCommands.YtdlZipCommand):
            isZip = isYt = True
        elif _check_cmd(BotCommands.YtdlLeechCommand):
            isLeech = isYt = True
        elif _check_cmd(BotCommands.YtdlZipLeechCommand):
            isLeech = isZip = isYt = True

        message = await sendMessage(msg.text, msg.reply_to_message or msg)
        message.from_user = msg.from_user
        if isYt:
            _ytdl(client, message, isZip, isLeech)
        else:
            _mirror_leech(client, message, isZip, extract, isQbit, isLeech)
        await sleep(6)
    del incompte_dict[msg.from_user.id]

async def resume_task(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    if tasks:= incompte_dict.get(user_id):
        await query.answer()
        await start_resume_task(client, tasks['msgs'])
    else:
        await query.answer('You didn\'t have incomplete task(s) to resume!', show_alert=True)


bot.add_handler(CallbackQueryHandler(resume_task, filters=regex('^resume')))