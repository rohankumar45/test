from html import escape

from bot import config_dict
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.bot_commands import BotCommands


class UsetString:
        CAP = f'''
<b>CUSTOM CAPTION SETTING</b>\n
Set custom caption with <b>HTML</b> style
Example: <code>{escape("<b>By:</b> <a href='https://t.me/R4ndom_Releases'>Random Releases</a>")}</code>
Result: <b>By:</b> <a href='https://t.me/R4ndom_Releases'>Random Releases</a>\n
<i>*Be careful when you use html tag for caption\n
Timeout: 60s.</i>
'''
        DUMP = '''
<b>DUMPID SETTING</b>\n
Example: <code>-1005670987</code>\n
<i>*ID must be startwith <code>-100xxx</code>\n
Timeout: 60s.</i>
'''
        GDX = '''
<b>CUSTOM GDRIVE SETTING</b>\n
Example: <b>0AHrdo0ZYDJTgUk9PVA</b>\n
<b>Index Link (Optional)</b>
Send index link after GDrive ID separated by space
Example:
<code>0AHrdo0ZYDJTgUk9PVA https://xx.xxxxxx.workers.dev/0:</code>\n
<i>#Add SA-Email to your Drive and give a permission\n
Timeout: 60s.</i>
'''
        PRE = '''
<b>PRENAME SETTING</b>\n
Example: <b>@MyChannel -</b>\n
<b>Org Name:</b>
<code>Batman (2022) [1080p] - H264.mkv</code>
<b>Result:</b>
<code>@MyChannel - Batman (2022) [1080p] - H264.mkv</code>\n
<i>Timeout: 60s.</i>
'''
        SUF = '''
<b>SUFNAME SETTING</b>\n
Example: <b>- @MyChannel</b>\n
<b>Org Name:</b>
<code>Batman (2022) [1080p] - H264.mkv</code>
<b>Result:</b>
<code>Batman (2022) [1080p] - H264 - @MyChannel.mkv</code>\n
<i>Timeout: 60s.</i>
'''
        SES = f'''
<b>SESSION SETTING</b>\n
Send valid session string to download content from restricted Chat/Channel without /{BotCommands.JoinChatCommand}.
<b>Your account must be a member of the channel.</b>\n
<i>Timeout: 60s.</i>
'''
        REM = '''
<b>REMNAME SETTING</b>\n
Example: <code>[</code><b>|</b><code>]</code><b>|</b> <code>-</code>\n
<b>Org Name:</b>
<code>Batman (2022) [1080p] - H264.mkv</code>
<b>Result:</b>
<code>Batman (2022) 1080p H264.mkv</code>\n
<i>*Separated by <b>|</b>
Timeout: 60s.</i>
'''
        YT = f'''
<b>YT-DLP OPTIONS SETTING</b>\n
Examples:
1. <code>{escape('bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[height<=1080]')}</code> this will give 1080p-mp4.
2. <code>{escape('bv*[height<=720][ext=webm]+ba/b[height<=720]')}</code> this will give 720p-webm.
Check all yt-dlp api options from this <a href='https://github.com/yt-dlp/yt-dlp/blob/master/yt_dlp/YoutubeDL.py#L184'>FILE</a> or use this <a href='https://t.me/mltb_official/177'>SCRIPT</a> to convert cli arguments to api options.\n
<i>Timeout: 60s.</i>
'''


class HelpString:
    ARIA = [f'/{BotCommands.MirrorCommand[0]} or /{BotCommands.MirrorCommand[1]}: Start mirroring to Google Drive.',
            f'/{BotCommands.LeechCommand[0]} or /{BotCommands.LeechCommand[1]}: Start leeching to Telegram.']

    QBIT = [f'/{BotCommands.QbMirrorCommand[0]} or /{BotCommands.QbMirrorCommand[1]}: Start Mirroring to Google Drive using qBittorrent.',
            f'/{BotCommands.QbLeechCommand[0]} or /{BotCommands.QbLeechCommand[1]}: Start leeching using qBittorrent.']

    EXTRAML = [f'/{BotCommands.BtSelectCommand}: Select files from torrents by gid or reply.',
               f'/{BotCommands.CancelMirror}: Cancel task by gid or reply.']

    YTDL = [f'/{BotCommands.YtdlCommand[0]} or /{BotCommands.YtdlCommand[1]}: Mirror yt-dlp supported link.',
            f'/{BotCommands.YtdlLeechCommand[0]} or /{BotCommands.YtdlLeechCommand[1]}: Leech yt-dlp supported link.']

    DRIVE = [f'/{BotCommands.CloneCommand} [drive_url]: Copy file/folder to Google Drive.',
             f'/{BotCommands.CountCommand} [drive_url]: Count file/folder of Google Drive.',
             f'/{BotCommands.ListCommand} [query]: Search in Google Drive(s).',
             f'/{BotCommands.DeleteCommand} [drive_url]: Delete file/folder from Google Drive (Only Owner & Sudo).']

    USER = [f'/{BotCommands.RssCommand}: RSS Menu (list, sub, unsub, etc).',
            f'/{BotCommands.HelpCommand}: Get help (this message).',
            f'/{BotCommands.UserSetCommand} [query]: Users settings.',
            f'/{BotCommands.StatsCommand}: Show stats of the machine where the bot is hosted in.',
            f'/{BotCommands.StatusCommand}: Shows a status of all the downloads.',
            f'/{BotCommands.SearchCommand} [query]: Search for torrents with API.',
            f'/{BotCommands.GdtotCommand} [query]: Search movie from gdtot.xyz.',
            f'/{BotCommands.PingCommand}: Check how long it takes to Ping the Bot (Only Owner & Sudo).',
            f'/{BotCommands.MiscCommand}: Misc tools (OCR, Translate, TTS, etc).',
            f'/{BotCommands.BypassCommand}: Bypass some support website.',
            f'/{BotCommands.ScrapperCommand}: Scrapper index link.',
            f'/{BotCommands.JoinChatCommand}: Joined to chat for download restrict content.',
            f'/{BotCommands.InfoCommand}: Get info about anime, movie, and user.',
            f'/{BotCommands.HashCommand}: Get hash help file/media.',
            f'/{BotCommands.BackupCommand}: Backup message from any chat to another chat.',
            f'/{BotCommands.WayBackCommand}: Archive a webpage with wayback machine.']

    OWNER = [f'/{BotCommands.SpeedCommand}: Check internet speed of the host.',
             f'/{BotCommands.CancelAllCommand} [query]: Cancel all [status] tasks.',
             f'/{BotCommands.AuthorizeCommand}: Authorize a chat or a user to use the bot (Only Owner & Sudo).',
             f'/{BotCommands.UnAuthorizeCommand}: Unauthorize a chat or a user to use the bot (Only Owner & Sudo).',
             f'/{BotCommands.UsersCommand}: show users settings (Only Owner & Sudo).',
             f'/{BotCommands.AddSudoCommand}: Add sudo user (Only Owner).',
             f'/{BotCommands.RmSudoCommand}: Remove sudo users (Only Owner).',
             f'/{BotCommands.RestartCommand}: Restart and update the bot (Only Owner & Sudo).',
             f'/{BotCommands.LogCommand}: Get a log file of the bot. Handy for getting crash reports (Only Owner & Sudo).',
             f'/{BotCommands.ShellCommand}: Run shell commands (Only Owner).',
             f'/{BotCommands.EvalCommand}: Run Python Code Line | Lines (Only Owner).',
             f'/{BotCommands.ExecCommand}: Run Commands In Exec (Only Owner).',
             f'/{BotCommands.SleepCommand}: Sleep the bot (Only Owner).',
             f'/{BotCommands.PurgeCommand}: Purge the message (Only Owner).',
             f'/{BotCommands.BroadcaseCommand}: Send broadcase message (Only Owner).',
             f'/{BotCommands.BotSetCommand}: Bot settings (Only Owner).',
             f'/{BotCommands.ClearLocalsCommand}: Clear {BotCommands.EvalCommand} or {BotCommands.ExecCommand} locals (Only Owner).']

    MLNOTE = '''
Available Arguments:
<code>-n</code>: New Name
<code>-z</code>: Zip to Archive
<code>-e</code>: Extract Archive
<code>-i</code>: Multi Link
<code>-s</code>: Select (Torrent)
<code>-d</code>: Seed (Torrent)
<code>-m</code>: Same Directory
<code>-b</code>: Bulk Download
<code>-j</code>: Join
<code>-gf</code>: GoFile Upload
<code>-up</code>: Upload (RClone or GD)
<code>-rcf</code>: RClone Flags
<code>-au</code>: Auth Username
<code>-ap</code>: Auth Password

Note: <i><b>QB</b> commands ONLY for torrents!</i>
'''

    MTG = '''
Treat links like any direct link
Some links need user access so sure you must add USER_SESSION_STRING for it.
Three types of links:
Public: <code>https://t.me/channel_name/message_id</code>
Private: <code>tg://openmessage?user_id=xxxxxx&message_id=xxxxx</code>
Super: <code>https://t.me/c/channel_id/message_id</code>
'''

    MLDL = '''
<code>/cmd</code> link -n new name

<b>By replying to link/file</b>:
<code>/cmd</code> -n new name -z -e -up upload destination

<b>Direct link authorization</b>: -au -ap
<code>/cmd</code> link -au username -ap password
'''

    MLZUZ = '''
<code>/cmd</code> link -e password (extract password protected)
<code>/cmd</code> link -z password (zip password protected)
<code>/cmd</code> link -z password -e (extract and zip password protected)
<code>/cmd</code> link -e password -z password (extract password protected and zip password protected)
Note: When both extract and zip added with cmd it will extract first and then zip, so always extract first
'''

    MLJOIN = '''
This option will only work before extract and zip, so mostly it will be used with -m argument (samedir)
By Reply:
<code>/cmd</code> -i 3 -j -m folder name
<code>/cmd</code> -b -j -m folder name
if u have link have splitted files:
<code>/cmd</code> link -j
'''

    MLBULK = '''
Bulk can be used by text message and by replying to text file contains links seperated by new line.
You can use it only by reply to message(text/file).
All options should be along with link!
Example:
link1 -n new name -up remote1:path1 -rcf |key:value|key:value
link2 -z -n new name -up remote2:path2
link3 -e -n new name -up remote2:path2
Note: You can't add -m arg for some links only, do it for all links or use multi without bulk!
Reply to this example by this cmd for example <code>/cmd</code> -b(bulk)
You can set start and end of the links from the bulk like seed, with -b start:end or only end by -b :end or only start by -b start. The default start is from zero(first link) to inf.
'''

    MISC = f'''
1. OCR: Generate text from image.
2. TTS: Text to speech, generate sound from text or image.
4. Webss: Generate screenshot from url.
5. Vidss: Generate screenshot from ddl.
6. Translate: Translate from text or image.
7. Pahe: Find movie by title from Pahe website.
8. Convert: Convert non animation sticker from image or from sticker to image.
9. Thumbnail: Genearte some thumbnail poster.\n
<b>Note</b>\nAvailable code for TTS and Translate <b><a href='https://graph.org/Support-Site-12-07-2'>Here</a></b>.
<b>Example:</b> <code>/{BotCommands.MiscCommand} id</code>, result will in id (Indonesia) language.
<i>*Some laguage may not work for TTS.</i>
'''

    CLONE = '''
<b>Support Site:
┌ GDToT
├ GDrive
├ Sharer
├ AppDrive
├ Gdflix
├ FileBee
└ Filepress</b>

Send support sites or rclone path along with command or by replying to the link/rc_path by command

<b>Multi links only by replying to first link or rclone_path:</b>
<code>/cmd</code> -i 10(number of links/pathies)

<b>Gdrive:</b>
<code>/cmd</code> gdrivelink

<b>RClone:</b>
<code>/cmd</code> (rcl or rclone_path) -up (rcl or rclone_path) -rcf |flagkey:flagvalue|flagkey|flagkey:flagvalue

Notes:
1. If -up not specified then rclone destination will be the RCLONE_PATH from config.env
2. When use -rcf start it with `|` to avoid reading it as bot argument.
'''

    RCLONE = '''
<b>Rclone Download</b>:
Treat rclone paths exactly like links
<code>/cmd</code> main:dump/ubuntu.iso or <code>rcl</code> (To select config, remote and path)
Users can add their own rclone from user settings
If you want to add path manually from your config add <code>mrcc:</code> before the path without space
<code>/cmd</code> <code>mrcc:</code>main:/dump/ubuntu.iso

<b>Upload</b>: -up
<code>/cmd</code> link -up <code>rcl</code> (To select rclone config, remote and path)
You can directly add the upload path: -up remote:dir/subdir
If DEFAULT_UPLOAD is `rc` then you can pass up: `gd` to upload using gdrive tools to GDRIVE_ID.
If DEFAULT_UPLOAD is `gd` then you can pass up: `rc` to upload to RCLONE_PATH.
If you want to add path manually from your config (uploaded from usetting) add <code>mrcc:</code> before the path without space
<code>/cmd</code> link -up <code>mrcc:</code>main:dump

<b>Rclone Flags</b>: -rcf
<code>/cmd</code> link -up path|rcl -rcf |--buffer-size:8M|--drive-starred-only|key|key:value
This will override all other flags except --exclude
Note: When use -rcf start it with `|` to avoid reading it as bot argument.
Check here all <a href='https://rclone.org/flags/'>RcloneFlags</a>.
'''

    BTSEL = '''
<code>/cmd</code> link -s or by replying to file/link
'''

    BTSEED = '''
<code>/cmd</code> link -d ratio:seed_time or by replying to file/link
To specify ratio and seed time add -d ratio:time. Ex: -d 0.7:10 (ratio and time) or -d 0.7 (only ratio) or -d :10 (only time) where time in minutes.
'''

    GOFILE = '''
<code>/cmd</code> link or reply to a message
<i>*GoFile upload only for cmd mirror not leech</i>
'''

    MLMULTI = '''
<b>Multi links only by replying to first link/file</b>:
<code>/cmd</code> -i 10(number of links/files)

<b>Multi links within same upload directory only by replying to first link/file</b>: -m
<code>/cmd</code> -i 10(number of links/files) -m folder name (multi message)
<code>/cmd</code> -b -m folder name (bulk-message/file)
'''

    YLNOTE = '''
Available Arguments:
<code>-n</code>: New Name
<code>-z</code>: Zip to Archive
<code>-i</code>: Multi Link
<code>-s</code>: Quality Select
<code>-m</code>: Same Directory
<code>-b</code>: Bulk Download
<code>-o</code>: BYTDL Options
<code>-gf</code>: GoFile Upload
<code>-up</code>: Upload (RClone or GD)
<code>-rcf</code>: RClone Flags
'''

    YLDL = '''
<b>Send link along with command line</b>:
<code>/cmd</code> link -s -n new name -opt x:y|x1:y1

<b>By replying to link</b>:
<code>/cmd</code> -n  new name -z password -opt x:y|x1:y1

<b>New Name</b>: -n
<code>/cmd</code> link -n new name
Note: Don't add file extension

<b>Zip</b>: -z password
<code>/cmd</code> link -z (zip)
<code>/cmd</code> link -z password (zip password protected)
'''

    YLBULK = '''
Bulk can be used by text message and by replying to text file contains links seperated by new line.
You can use it only by reply to message(text/file).
All options should be along with link!
Example:
link1 -n new name -up remote1:path1 -rcf |key:value|key:value
link2 -z -n new name -up remote2:path2
link3 -e -n new name -opt ytdlpoptions

Note: You can't add -m arg for some links only, do it for all links or use multi without bulk!
link pswd: pass(zip/unzip) opt: ytdlpoptions up: remote2:path2
Reply to this example by this cmd for example <code>/cmd</code> b(bulk) m:folder_name(same dir)
You can set start and end of the links from the bulk with b:start:end or only end by b::end or only start by b:start. The default start is from zero(first link) to inf.
'''

    YTOPT = '''
Incase default quality added from yt-dlp options using format option and you need to select quality for specific link or links with multi links feature.
<code>/cmd</code> link -s

<code>/cmd</code> link -opt playliststart:^10|fragment_retries:^inf|matchtitle:S13|writesubtitles:true|live_from_start:true|postprocessor_args:{"ffmpeg": ["-threads", "4"]}|wait_for_video:(5, 100)
Note: Add `^` before integer or float, some values must be numeric and some string.
Like playlist_items:10 works with string, so no need to add `^` before the number but playlistend works only with integer so you must add `^` before the number like example above.
You can add tuple and dict also. Use double quotes inside dict.

Check all yt-dlp api options from this <a href='https://github.com/yt-dlp/yt-dlp/blob/master/yt_dlp/YoutubeDL.py#L184'>FILE</a> or use this <a href='https://t.me/mltb_official_channel/177'>script</a> to convert cli arguments to api options.
'''

    YLMULTI = '''
<b>Multi links only by replying to first link</b>:
<code>/cmd</code> -i 10(number of links)

<b>Multi links within same upload directory only by replying to first link</b>: -m
<code>/cmd</code> -i 10(number of links) -m folder name
'''

    RSSHELP = '''
Use this format to add feed url:
Title1 link (required)
Title2 link -c cmd -inf xx -exf xx
Title3 link -c cmd -d ratio:time -z password

-c command + any arg
-inf For included words filter.
-exf For excluded words filter.

Example: Title https://www.rss-url.com inf: 1080 or 720 or 144p|mkv or mp4|hevc exf: flv or web|xxx opt: up: mrcc:remote:path/subdir rcf: --buffer-size:8M|key|key:value
This filter will parse links that it's titles contains `(1080 or 720 or 144p) and (mkv or mp4) and hevc` and doesn't conyain (flv or web) and xxx` words. You can add whatever you want.

Another example: inf:  1080  or 720p|.web. or .webrip.|hvec or x264. This will parse titles that contains ( 1080  or 720p) and (.web. or .webrip.) and (hvec or x264). I have added space before and after 1080 to avoid wrong matching. If this `10805695` number in title it will match 1080 if added 1080 without spaces after it.

Filter Notes:
1. | means and.
2. Add `or` between similar keys, you can add it between qualities or between extensions, so don't add filter like this f: 1080|mp4 or 720|web because this will parse 1080 and (mp4 or 720) and web ... not (1080 and mp4) or (720 and web)."
3. You can add `or` and `|` as much as you want."
4. Take look on title if it has static special character after or before the qualities or extensions or whatever and use them in filter to avoid wrong match.

<i>Timeout: 60s.</i>
        '''

    @property
    def all_commands(self):
        return self.ARIA + self.QBIT + self.EXTRAML + self.YTDL + self.DRIVE + self.USER + self.OWNER


def get_help_button(from_user: int, data: str=None):
    buttons = ButtonMaker()
    image, menu = config_dict['IMAGE_HELP'], 'ml'
    def _build_button(*args, back=True):
        for x in args:
            buttons.button_data(x.split()[0], f'help {from_user.id} {x.lower()}', 'header' if x.lower().startswith(('mirror', 'youtube')) else None)
        if back:
            buttons.button_data('<<', f'help {from_user.id} back', 'footer')
    home_menu = ['Aria', 'qBit', 'YTdl', 'Drive', 'User', 'Owner', 'Mirror/Leech', 'YouTube/Leech']
    ml_menu = ['Basic ML', 'Zip/Unzip', 'Join', 'Selection', 'Seed', 'RClone', 'GoFile ML', 'Multi ML', 'TG Link', 'Bulk ML']
    ytdl_menu = ['Basic YL', 'Options', 'GoFile YL', 'Multi YL', 'Bulk YL']
    if not data or data == 'back':
        text, menu = f'{from_user.mention}, Choose Options Below.', None
        _build_button(*home_menu, back=False)
    elif data == 'aria':
        image, menu = config_dict['IMAGE_ARIA'], 'home'
        ariahelp ='\n'.join(x for x in HelpString.ARIA + HelpString.EXTRAML)
        text = f'<b>ARIA COMMANDS</b>\n{ariahelp}'
        del home_menu[0]
    elif data == 'qbit':
        image, menu = config_dict['IMAGE_QBIT'], 'home'
        text = '<b>QBITTORRENT COMMANDS</b>\n'
        text += '\n'.join(x for x in HelpString.QBIT + HelpString.EXTRAML)
        del home_menu[1]
    elif data == 'ytdl':
        image, menu = config_dict['IMAGE_YT'], 'home'
        text = '<b>YTDL COMMANDS</b>\n'
        text += '\n'.join(x for x in HelpString.YTDL)
        del home_menu[2]
    elif data == 'drive':
        image, menu = config_dict['IMAGE_GD'], 'home'
        text = '<b>GDRIVE COMMANDS</b>\n'
        text += '\n'.join(x for x in HelpString.DRIVE)
        del home_menu[3]
    elif data == 'user':
        image, menu = config_dict['IMAGE_USER'], 'home'
        text = '<b>USER COMMANDS</b>\n'
        text += '\n'.join(x for x in HelpString.USER)
        del home_menu[4]
    elif data == 'owner':
        image, menu = config_dict['IMAGE_OWNER'], 'home'
        text = '<b>OWNER COMMANDS</b>\n'
        text += '\n'.join(x for x in HelpString.OWNER)
        del home_menu[5]
    elif data.startswith('mirror'):
        text = f'<b>MIRROR/LEECH</b>{HelpString.MLNOTE}'
    elif data == 'basic ml':
        text = f'<b>BASIC COMMAND</b>{HelpString.MLDL}'
        del ml_menu[0]
    elif data.startswith('zip'):
        text = f'<b>ZIP/UNZIP (-z -e)</b>{HelpString.BTSEED}'
        del ml_menu[1]
    elif data == 'join':
        text = f'<b>ZIP/UNZIP (-z -e)</b>{HelpString.BTSEED}'
        del ml_menu[2]
    elif data == 'selection':
        text = f'<b>TORRENT SELECTION (-s)</b>{HelpString.BTSEL}'
        del ml_menu[3]
    elif data == 'seed':
        text = f'<b>TORRENT SEED (-d)</b>{HelpString.BTSEED}'
        del ml_menu[4]
    elif data == 'rclone':
        text = f'<b>RCLONE DOWNLOAD</b>{HelpString.RCLONE}'
        del ml_menu[5]
    elif data == 'gofile ml':
        text = f'<b>GOFILE UPLOAD (-gf)</b>{HelpString.GOFILE}'
        del ml_menu[6]
    elif data == 'multi ml':
        text = f'<b>MULTI LINK (-i)</b>{HelpString.MLMULTI}'
        del ml_menu[7]
    elif data == 'tg link':
        text = f'<b>TG LINK DOWNLOAD</b>{HelpString.MTG}'
        del ml_menu[8]
    elif data == 'bulk ml':
        text = f'<b>BULK DOWNLOAD (-b)</b>{HelpString.MLBULK}'
        del ml_menu[9]
    elif data.startswith('youtube'):
        text, menu = f'<b>YOUTUBE/YLEECH</b>{HelpString.YLNOTE}', 'ytdl'
    elif data == 'basic yl':
        text, menu = f'<b>BASIC COMMAND</b>{HelpString.YLDL}', 'ytdl'
        del ytdl_menu[0]
    elif data == 'options':
        text, menu = f'<b>YOUTUBE OPSTIONS (-opt)</b>{HelpString.YTOPT}', 'ytdl'
        del ytdl_menu[1]
    elif data == 'gofile yl':
        text, menu = f'<b>GOFILE UPLOAD (-gf)</b>{HelpString.GOFILE}', 'ytdl'
        del ytdl_menu[2]
    elif data == 'multi yl':
        text, menu = f'<b>MULTI LINK (-i)</b>{HelpString.YLMULTI}', 'ytdl'
        del ytdl_menu[3]
    elif data == 'bulk yl':
        text, menu = f'<b>BULK DOWNLOAD (-b)</b>{HelpString.YLBULK}', 'ytdl'
        del ytdl_menu[4]

    if menu == 'home':
        _build_button(*home_menu)
    elif menu == 'ml':
        _build_button(*ml_menu)
    elif menu == 'ytdl':
        _build_button(*ytdl_menu)

    buttons.button_data('Close', f'help {from_user.id} close', 'footer')
    return text, image, buttons.build_menu(3)