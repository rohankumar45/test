from pyrogram.types import Message

from bot import bot, bot_loop, bot_name, download_dict, download_dict_lock, config_dict, user_data
from bot.helper.ext_utils.bot_utils import get_user_task, is_premium_user, is_media, update_user_ldata
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.message_utils import auto_delete_message, sendMessage, sendingMessage, sendCustom, startRestrict


class ForceMode:
    def __init__(self, message: Message):
        self.__message = message
        self.__reply_to = message.reply_to_message
        self.__uid = message.from_user.id
        self.__tag = message.from_user.mention
        self.__user_dict = user_data.get(self.__uid, {})

    async def run_force(self, *args, pm_mode='None'):
        isSuperGroup = self.__message.chat.type.name in ['SUPERGROUP', 'CHANNEL']
        msg = None

        if 'fsub' in args:
            msg = await self.__force_sub()
        if not msg and 'funame' in args:
            msg = await self.__force_username()
        if not msg and 'limit' in args:
            msg = await self.__task_limiter()
        if not msg and self.__user_dict.get('enable_pm') and isSuperGroup and (mode:= getattr(self, pm_mode, None)):
            msg = await self.__chec_pm()
        if not msg and 'mute' in args and isSuperGroup:
            msg = await self.auto_muted()

        return msg

    async def __chec_pm(self):
        try:
            await bot.get_chat(self.__uid)
        except:
            buttons = ButtonMaker()
            buttons.button_link('Click Here', f'http://t.me/{bot_name}')
            warn_msg = 'Message will send in pm'
            return await sendingMessage(f'{self.__tag}...\n{warn_msg}', self.__message, config_dict['IMAGE_PM'], buttons.build_menu(1))


    async def bypass_pm_message(self):
        msg_nolink = 'No <b>link</b> given to bypass 😑'
        msg_media = f'<code>/{BotCommands.BypassCommand}</code> not for file/media! Link only 😑'
        msg_link = 'Your <b>link</b> on progress to bypass, will send once done 😊'
        warn_msg = 'All <b>Bypass</b> result will send in bot PM and log channel\n<b>Start me first in PM</b>'
        return await self.__send_pm_message(msg_nolink, msg_media, msg_link, warn_msg)

    async def clone_pm_message(self):
        msg_nolink = 'No <b>GDrive or Sharer</b> link given 😑'
        msg_media = f'<code>/{BotCommands.CloneCommand}</code> not for file/media! <b>GDrive or Sharer</b> link only 😑'
        msg_link = 'Your <b>GDrive or Sharer</b> link has been added, will send once done 😊'
        warn_msg = 'All <b>Clone</b> result will send in bot PM and log channel\n<b>Start me first in PM</b>'
        return await self.__send_pm_message(msg_nolink, msg_media, msg_link, warn_msg)

    async def count_pm_message(self):
        msg_nolink = 'No <b>GDrive</b> link given to count 😑'
        msg_media = f'<code>/{BotCommands.CountCommand}</code> not for file/media! <b>GDrive</b> link only 😑'
        msg_link = 'Your <b>GDrive</b> link on counting, will send once done 😊'
        warn_msg = 'All <b>Count</b> result will send in bot PM and log channel\n<b>Start me first in PM</b>'
        return await self.__send_pm_message(msg_nolink, msg_media, msg_link, warn_msg)

    async def hash_pm_message(self):
        msg_no_media ='No <b>file/media</b> given 😑'
        msg_link = f'<code>/{BotCommands.HashCommand}</code> not for link! <b>media/file</b> only 😑'
        msg_media = 'Your <b>media/file</b> has been executed, will send once done 😊'
        warn_msg = 'nAll <b>Hash</b> result will send in bot PM and log channel\n<b>Start me first in PM</b>'
        return await self.__send_pm_message(msg_no_media, msg_media, msg_link, warn_msg)

    async def mirror_leech_pm_message(self):
        msg_nolink = 'No <b>link</b> given 😑'
        msg_media = 'Your requested for <b>file/media</b> has been added, will send once done 😊'
        msg_link = f'Your requested has been added, will send once done 😊'
        warn_msg = 'All mirror and leech file(s) will send in bot PM and log channel\n<b>Start me first in PM</b>'
        return await self.__send_pm_message(msg_nolink, msg_media, msg_link, warn_msg)

    async def scrapper_pm_message(self):
        msg_nolink = 'No <b>link</b> or <b>.txt</b> file given to scrapper 😑'
        msg_media = f'<code>/{BotCommands.ScrapperCommand}</code> only for link and txt file'
        msg_txt = 'Your <b>.txt</b> file on progress to scrapper, will send one by one once done 😊'
        msg_link = 'Your <b>link</b> on progress to scrapper, will send one by one once done 😊'
        warn_msg = 'All <b>Scrapper</b> result will send in bot PM and log channel\n<b>Start me first in PM</b>'
        return await self.__send_pm_message(msg_nolink, msg_media, msg_link, warn_msg, msg_txt)

    async def wayback_pm_message(self):
        msg_nolink = 'No <b>link</b> given to save 😑'
        msg_media = f'<code>/{BotCommands.WayBackCommand}</code> not for file/media! Link only 😑'
        msg_link = 'Your <b>link</b> on progress to save, will send once done 😊'
        warn_msg = 'All <b>Bypass</b> result will send in bot PM and log channel\n<b>Start me first in PM</b>'
        return await self.__send_pm_message(msg_nolink, msg_media, msg_link, warn_msg)

    async def ytdlp_pm_message(self):
        msg_nolink = 'No <b>YT-DLP</b> link given 😑'
        msg_media = '<code>/watchcmds</code> not for file/media! <b>YT-DLP</b> link only 😑'
        msg_link = f'Your <b>YT-DLP</b> link has been added, will send once done 😊'
        warn_msg = 'All <b>YT-DLP</b> mirror and leech file(s) will send in bot PM and log channel\n<b>Start me first in PM</b>'
        return await self.__send_pm_message(msg_nolink, msg_media, msg_link, warn_msg)

    async def __force_username(self):
        if config_dict['FUSERNAME']:
            uname = self.__message.from_user.username
            if not uname:
                return await sendMessage('Upss... Set username first! 😑\nGo to Settings -> Edit Profile -> Username', self.__message)
            if not (duname:= self.__user_dict.get('user_name', '')) and duname != uname:
                await update_user_ldata(self.__uid, 'user_name', self.__message.from_user.username)

    async def __force_sub(self):
        if config_dict['FSUB']:
            try:
                await bot.get_chat_member(config_dict['FSUB_CHANNEL_ID'], self.__uid)
            except:
                CHANNEL_USERNAME = config_dict['CHANNEL_USERNAME']
                buttons = ButtonMaker()
                buttons.button_link(f"{config_dict['FSUB_BUTTON_NAME']}", f'https://t.me/{CHANNEL_USERNAME}')
                fsub_msg = f"<b>Upss...</b>\n{self.__tag}, you should join <a href='https://t.me/{CHANNEL_USERNAME}'>{CHANNEL_USERNAME}</a> to use this bot."
                return await sendingMessage(fsub_msg, self.__message, config_dict['IMAGE_FSUB'], buttons.build_menu(1))

    async def __task_limiter(self):
        if not is_premium_user(self.__uid):
            if USER_TASKS_LIMIT := config_dict['USER_TASKS_LIMIT']:
                if await get_user_task(self.__uid) >= USER_TASKS_LIMIT:
                    return await sendingMessage(f'Upss, {self.__tag} you can only add {USER_TASKS_LIMIT} task! Wait until another task done and try again.', self.__message, config_dict['IMAGE_LIMIT'])
            if TOTAL_TASKS_LIMIT := config_dict['TOTAL_TASKS_LIMIT']:
                async with download_dict_lock:
                    total_tasks = len(download_dict)
                if total_tasks >= TOTAL_TASKS_LIMIT:
                    return await sendingMessage(f'Upss, {self.__tag} task limit is {TOTAL_TASKS_LIMIT}, wait until some task done and try again!', self.__message, config_dict['IMAGE_LIMIT'])

    async def auto_muted(self, help_msg=''):
        if config_dict['AUTO_MUTE']:
            authuser = (await bot.get_chat_member(config_dict['MUTE_CHAT_ID'], self.__uid)).status.name in ['OWNER', 'ADMINISTRATOR']
            if help_msg:
                if authuser:
                    return await sendMessage(f'Hmm...\n{self.__tag}, you are a <b>Admin</b>, please take your time to read! /{BotCommands.HelpCommand}\n\n{help_msg}', self.__message)
                else:
                    mute_msg = f"<b>Upss...</b>\n{self.__tag}, you are <b>MUTED</b> ({config_dict['AUTO_MUTE_DURATION']}s)\nLearn before use or watch others and read /{BotCommands.HelpCommand}\n\n{help_msg}"
                    await startRestrict(self.__message)
                    return await sendMessage(mute_msg, self.__message)
            else:
                if not authuser:
                    await startRestrict(self.__message)

    async def __send_pm_message(self, msg_nolink, msg_media, msg_link, warn_msg, msg_txt=''):
        pmmsg = None
        if not self.__reply_to and len(self.__message.text.split()) == 1:
            pmmsg = await sendCustom(msg_nolink, self.__uid)
        elif self.__reply_to and (media := is_media(self.__reply_to)):
            if msg_txt:
                msg = msg_txt if media.file_name.endswith('.txt') else msg_media
                pmmsg = await sendCustom(msg, self.__uid)
            else:
                pmmsg = await sendCustom(msg_media, self.__uid)
        else:
            pmmsg = await sendCustom(msg_link, self.__uid)

        if pmmsg:
            bot_loop.create_task(auto_delete_message(pmmsg, stime=5))
            return True
        else:
            buttons = ButtonMaker()
            buttons.button_link('Click Here', f'http://t.me/{bot_name}')
            botpmmsg = await sendingMessage(f'{self.__tag}...\n{warn_msg}', self.__message, config_dict['IMAGE_PM'], buttons.build_menu(1))
            await auto_delete_message(self.__message, botpmmsg, self.__reply_to)