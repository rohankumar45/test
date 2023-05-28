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
            f'/{BotCommands.ZipMirrorCommand[0]} or /{BotCommands.ZipMirrorCommand[1]}: Start mirroring and upload the file/folder compressed with zip extension.',
            f'/{BotCommands.UnzipMirrorCommand[0]} or /{BotCommands.UnzipMirrorCommand[1]}: Start mirroring and upload the file/folder extracted from any archive extension.',
            f'/{BotCommands.LeechCommand[0]} or /{BotCommands.LeechCommand[1]}: Start leeching to Telegram.',
            f'/{BotCommands.ZipLeechCommand[0]} or /{BotCommands.ZipLeechCommand[1]}: Start leeching and upload the file/folder compressed with zip extension.',
            f'/{BotCommands.UnzipLeechCommand[0]} or /{BotCommands.UnzipLeechCommand[1]}: Start leeching and upload the file/folder extracted from any archive extension.']

    QBIT = [f'/{BotCommands.QbMirrorCommand[0]} or /{BotCommands.QbMirrorCommand[1]}: Start Mirroring to Google Drive using qBittorrent.',
            f'/{BotCommands.QbZipMirrorCommand[0]} or /{BotCommands.QbZipMirrorCommand[1]}: Start mirroring using qBittorrent and upload the file/folder compressed with zip extension.',
            f'/{BotCommands.QbUnzipMirrorCommand[0]} or /{BotCommands.QbUnzipMirrorCommand[1]}: Start mirroring using qBittorrent and upload the file/folder extracted from any archive extension.',
            f'/{BotCommands.QbLeechCommand[0]} or /{BotCommands.QbLeechCommand[1]}: Start leeching using qBittorrent.',
            f'/{BotCommands.QbZipLeechCommand[0]} or /{BotCommands.QbZipLeechCommand[1]}: Start leeching using qBittorrent and upload the file/folder compressed with zip extension.',
            f'/{BotCommands.QbUnzipLeechCommand[0]} or /{BotCommands.QbUnzipLeechCommand[1]}: Start leeching using qBittorrent and upload the file/folder extracted from any archive extension.']

    EXTRAML = [f'/{BotCommands.BtSelectCommand}: Select files from torrents by gid or reply.',
               f'/{BotCommands.CancelMirror}: Cancel task by gid or reply.']

    YTDL = [f'/{BotCommands.YtdlCommand[0]} or /{BotCommands.YtdlCommand[1]}: Mirror yt-dlp supported link.',
            f'/{BotCommands.YtdlZipCommand[0]} or /{BotCommands.YtdlZipCommand[1]}: Mirror yt-dlp supported link as zip.',
            f'/{BotCommands.YtdlLeechCommand[0]} or /{BotCommands.YtdlLeechCommand[1]}: Leech yt-dlp supported link.',
            f'/{BotCommands.YtdlZipLeechCommand[0]} or /{BotCommands.YtdlZipLeechCommand[1]}: Leech yt-dlp supported link as zip.']

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
<b>NOTES:</b>
1. When use cmd by reply don't add any option in link msg! Always add them after cmd msg!
2. Options (<b>n: and pswd:</b>) should be added randomly after the link if link along with the cmd and after any other option
3. Options (<b>d, s, m:, b and multi</b>) should be added randomly before the link and before any other option.
4. Commands that start with <b>qb</b> are <b>ONLY</b> for torrents.
5. (n:) option doesn't work with torrents.
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
<b>Send link along with command line:</b>
<code>/cmd</code> link n: newname pswd: xx(zip/unzip)

<b>By replying to link/file:</b>
<code>/cmd</code> n: newname pswd: xx(zip/unzip)

<b>Direct link authorization:</b>
<code>/cmd</code> link n: newname pswd: xx(zip/unzip)
<b>username</b>
<b>password</b>
'''

    MLBULK = '''
Bulk can be used by text message and by replying to text file contains links seperated by new line.
You can use it only by reply to message(text/file). Options that came after link should be added along with and after link and not with cmd.
Example:
link n: newname up: remote1:path1
link pswd: pass(zip/unzip) \\nusername\\npassword(authentication) up: remote2:path2
link pswd: pass(zip/unzip) up: remote2:path2 \\n{username}\\n{password}(authentication)(last option)
You can set start and end of the links from the bulk with b:start:end or only end by b::end or only start by b:start. The default start is from zero(first link) to inf.
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

<b>Multi links only by replying to first gdlink or rclone_path:</b>
<code>/cmd</code> 10 (number of links/pathies)

<b>Gdrive:</b>
<code>/cmd</code> gdrivelink

<b>RClone:</b>
<code>/cmd</code> rcl or rclone_path up: rcl or rclone_path rcf: flagkey:flagvalue|flagkey|flagkey:flagvalue

<b>Notes:</b>
if up: not specified then rclone destination will be the RCLONE_PATH from config.env
'''

    RCLONE = '''
<b>Rclone Download</b>:
Treat rclone paths exactly like links
<code>/cmd</code> main:dump/ubuntu.iso or <code>rcl</code> (To select config, remote and path)
Users can add their own rclone from user settings
If you want to add path manually from your config add <code>mrcc:</code> before the path without space
<code>/cmd</code> <code>mrcc:</code>main:/dump/ubuntu.iso

<b>Upload</b>:
<code>/cmd</code> link up: <code>rcl</code> (To select rclone config, remote and path)
You can directly add the upload path. up: remote:dir/subdir
If DEFAULT_UPLOAD is `rc` then you can pass up: `gd` to upload using gdrive tools to GDRIVE_ID.
If DEFAULT_UPLOAD is `gd` then you can pass up: `rc` to upload to RCLONE_PATH.
If you want to add path manually from your config (uploaded from usetting) add <code>mrcc:</code> before the path without space
<code>/cmd</code> link up: <code>mrcc:</code>main:dump

<b>Rclone Flags</b>:
<code>/cmd</code> link|path|rcl up: path|rcl rcf: --buffer-size:8M|--drive-starred-only|key|key:value
This will override all other flags except --exclude
Check here all <a href='https://rclone.org/flags/'>RcloneFlags</a>.
'''

    BTSEL = '''
<code>/cmd</code> <b>s</b> link or by replying to file/link
This option should be always before n: or pswd:
'''

    BTSEED = '''
<code>/cmd</code> <b>d</b> link or by replying to file/link
To specify ratio and seed time add d:ratio:time. Ex: d:0.7:10 (ratio and time) or d:0.7 (only ratio) or d::10 (only time) where time in minutes.
Those options should be always before n: or pswd:
'''

    GOFILE = '''
<code>/cmd go</code> link or reply to a message
<i>*GoFile upload only for cmd mirror not leech</i>
'''

    MLMULTI = '''
<b>Multi links only by replying to first link/file:</b>
<code>/cmd</code> 10 (number of links/files)
Number should be always before n: or pswd:

<b>Multi links within same upload directory only by replying to first link/file:</b>
<code>/cmd</code> 10 (number of links/files) m:folder_name
Number and m:folder_name (folder_name without space) should be always before n: or pswd:
'''

    YLNOTE = '''
1. When use cmd by reply don't add any option in link msg! Always add them after cmd msg!
2. Options (<b>b, s, m: and multi</b>) should be added randomly before link and before any other option.
3. Options (<b>n:, pswd: and opt:</b>) should be added randomly after the link if link along with the cmd or after cmd if by reply.
4. You can always add video quality from yt-dlp api options.
5. Don't add file extension while rename using `n:`

<b>Options Note:</b> Add `^` before integer or float, some values must be numeric and some string.
Like playlist_items:10 works with string, so no need to add `^` before the number but playlistend works only with integer so you must add `^` before the number like example above.
You can add tuple and dict also. Use double quotes inside dict.

Check all yt-dlp api options from this <a href='https://github.com/yt-dlp/yt-dlp/blob/master/yt_dlp/YoutubeDL.py#L184'>FILE</a> or use this <a href='https://t.me/mltb_official_channel/177'>script</a> to convert cli arguments to api options.
'''

    YLDL = '''
<b>Send link along with command line:</b>
<code>/cmd</code> s link n: newname pswd: xx(zip) opt: x:y|x1:y1

<b>By replying to link:</b>
<code>/cmd</code> n: newname pswd: xx(zip) opt: x:y|x1:y1
'''

    YLBULK = '''
Bulk can be used by text message and by replying to text file contains links seperated by new line.
You can use it only by reply to message(text/file). Options that came after link should be added along with and after link and not with cmd.
Example:
link n: newname up: remote1:path1
link pswd: pass(zip/unzip) opt: ytdlpoptions up: remote2:path2
Reply to this example by this cmd for example <code>/cmd</code> b(bulk) m:folder_name(same dir)
You can set start and end of the links from the bulk with b:start:end or only end by b::end or only start by b:start. The default start is from zero(first link) to inf.
'''

    YLQUAL = '''
Incase default quality added from yt-dlp options using format option and you need to select quality for specific link or links with multi links feature.
<code>/cmd</code> s link
This option should be always before n:, pswd: and opt:

<b>Options Example:</b> opt: playliststart:^10|matchtitle:S13|writesubtitles:true|live_from_start:true|postprocessor_args:{'ffmpeg': ['-threads', '4']}|wait_for_video:(5, 100)
'''

    YLMULTI = '''
<b>Multi links only by replying to first link:</b>
<code>/cmd</code> 10 (number of links)
Number should be always before n:, pswd: and opt:

<b>Multi links within same upload directory only by replying to first link:</b>
<code>/cmd</code> 10 (number of links) m:folder_name
Number and m:folder_name should be always before n:, pswd: and opt:
'''

    RSSHELP = '''
Use this format to add feed url:
Title1 link (required)
Title2 link c: cmd inf: xx exf: xx opt: options like(up, rcf, pswd) (optional)
Title3 link c: cmd d:ratio:time opt: up: gd
c: command + any mirror option before link like seed option.
opt: any option after link like up, rcf and pswd(zip).
inf: For included words filter.
exf: For excluded words filter.
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
    image = config_dict['IMAGE_HELP']
    def _build_button(*args, back=True):
        for x in args:
            buttons.button_data(x.split()[0], f'help {from_user.id} {x.lower()}')
        if back:
            buttons.button_data('<<', f'help {from_user.id} back', 'footer')
    if not data or data == 'back':
        text = f'{from_user.mention}, Choose Options Below.'
        _build_button('Aria', 'qBit', 'Ytdl', 'Drive', 'User', 'Owner', 'Mirror/Leech', 'YouTube/Leech', back=False)
    elif data == 'aria':
        image = config_dict['IMAGE_ARIA']
        ariahelp ='\n'.join(x for x in HelpString.ARIA + HelpString.EXTRAML)
        text = f'<b>ARIA COMMANDS</b>\n\n{ariahelp}'
        _build_button('qBit', 'Ytdl', 'Drive', 'User', 'Owner')
    elif data == 'qbit':
        image = config_dict['IMAGE_QBIT']
        text = '<b>QBITTORRENT COMMANDS</b>\n\n'
        text += '\n'.join(x for x in HelpString.QBIT + HelpString.EXTRAML)
        _build_button('Aria', 'Ytdl', 'Drive', 'User', 'Owner')
    elif data == 'ytdl':
        image = config_dict['IMAGE_YT']
        text = '<b>YTDL COMMANDS</b>\n\n'
        text += '\n'.join(x for x in HelpString.YTDL)
        _build_button('Aria', 'qBit', 'Drive', 'User', 'Owner')
    elif data == 'drive':
        image = config_dict['IMAGE_GD']
        text = '<b>GDRIVE COMMANDS</b>\n\n'
        text += '\n'.join(x for x in HelpString.DRIVE)
        _build_button('Aria', 'qBit', 'Ytdl', 'User', 'Owner')
    elif data == 'user':
        image = config_dict['IMAGE_USER']
        text = '<b>USER COMMANDS</b>\n\n'
        text += '\n'.join(x for x in HelpString.USER)
        _build_button('Aria', 'qBit', 'Ytdl', 'Drive', 'Owner')
    elif data == 'owner':
        image = config_dict['IMAGE_OWNER']
        text = '<b>OWNER COMMANDS</b>\n\n'
        text += '\n'.join(x for x in HelpString.OWNER)
        _build_button('Aria', 'qBit', 'Ytdl', 'Drive', 'User')
    elif data.startswith('mirror'):
        text = f'<b>MIRROR/LEECH NOTES</b>\n{HelpString.MLNOTE}'
        _build_button('Basic ML', 'Selection', 'Seed', 'RClone', 'GoFile ML', 'Multi ML', 'TG Link', 'Bulk ML')
    elif data == 'basic ml':
        text = f'<b>BASIC COMMAND</b>\n{HelpString.MLDL}'
        _build_button('Selection', 'Seed', 'RClone', 'GoFile ML', 'Multi ML', 'TG Link', 'Bulk ML')
    elif data == 'bulk ml':
        text = f'<b>BULK DOWNLOAD</b>\n{HelpString.MLBULK}'
        _build_button('Selection', 'Seed', 'RClone', 'GoFile ML', 'Multi ML', 'TG Link')
    elif data == 'selection':
        text = f'<b>TORRENT SELECTION</b>\n{HelpString.BTSEL}'
        _build_button('Basic ML', 'Seed', 'RClone', 'GoFile ML', 'Multi ML', 'TG Link', 'Bulk ML')
    elif data == 'seed':
        text = f'<b>TORRENT SEED</b>\n{HelpString.BTSEED}'
        _build_button('Basic ML', 'Selection', 'RClone', 'GoFile ML', 'Multi ML', 'TG Link', 'Bulk ML')
    elif data == 'rclone':
        text = f'<b>RCLONE DOWNLOAD</b>\n{HelpString.RCLONE}'
        _build_button('Basic ML', 'Selection', 'GoFile ML', 'Multi ML', 'TG Link', 'Bulk ML')
    elif data == 'tg link':
        text = f'<b>TG LINK DOWNLOAD</b>\n{HelpString.MTG}'
        _build_button('Basic ML', 'Selection', 'Seed', 'RClone', 'Multi ML', 'Bulk ML')
    elif data == 'gofile ml':
        text = f'<b>GOFILE UPLOAD</b>\n{HelpString.GOFILE}'
        _build_button('Basic ML', 'Selection', 'Seed', 'RClone', 'Multi ML', 'TG Link', 'Bulk ML')
    elif data == 'multi ml':
        text = f'<b>MULTI LINK</b>\n{HelpString.MLMULTI}'
        _build_button('Basic ML', 'Selection', 'Seed', 'RClone', 'GoFile ML', 'TG Link', 'Bulk ML')
    elif data.startswith('youtube'):
        text = f'<b>YOUTUBE/LEECH NOTES</b>\n{HelpString.YLNOTE}'
        _build_button('Basic YL', 'Quality', 'GoFile YL', 'Multi YL', 'Bulk YL')
    elif data == 'basic yl':
        text = f'<b>BASIC COMMAND</b>\n{HelpString.YLDL}'
        _build_button('Quality', 'GoFile YL', 'Multi YL', 'Bulk YL')
    elif data == 'bulk yl':
        text = f'<b>BULK DOWNLOAD</b>\n{HelpString.YLBULK}'
        _build_button('Quality', 'GoFile YL', 'Multi YL')
    elif data == 'quality':
        text = f'<b>YOUTUBE QUALITY</b>\n{HelpString.YLQUAL}'
        _build_button('Basic YL', 'GoFile YL', 'Multi YL', 'Bulk YL')
    elif data == 'gofile yl':
        text = f'<b>GOFILE UPLOAD</b>\n{HelpString.GOFILE}'
        _build_button('Basic YL', 'Quality', 'Multi YL', 'Bulk YL')
    elif data == 'multi yl':
        text = f'<b>MULTI LINK</b>\n{HelpString.YLMULTI}'
        _build_button('Basic YL', 'Quality', 'GoFile YL', 'Bulk YL')
    buttons.button_data('Close', f'help {from_user.id} close', 'footer')
    return text, image, buttons.build_menu(3)