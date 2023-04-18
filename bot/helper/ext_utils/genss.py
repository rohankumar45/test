from aiofiles.os import path as aiopath, makedirs
from os import path as ospath
from PIL import Image
from re import search as re_search

from bot import LOGGER
from bot.helper.ext_utils.bot_utils import cmd_exec
from bot.helper.ext_utils.fs_utils import clean_target
from bot.helper.ext_utils.leech_utils import get_media_info


class GenSS:
    def __init__(self, message, path):
        self.__message = message
        self.__path = path
        self.__images = f'genss_{self.__message.id}.jpg'
        self.__ss_path = ospath.join('genss', str(self.__message.id))
        self.__name = ''
        self.__error = False

    async def __combine_image(self):
        await cmd_exec(['ffmpeg', '-hide_banner', '-loglevel', 'quiet', '-i', str(ospath.join(self.__ss_path,'%1d.jpg')),
                        '-filter_complex', 'scale=1920:-1,tile=3x3', self.__images, '-y'])
        if not await aiopath.exists(self.__images):
            self.__images = ''

    async def __run_genss(self, duration, index):
        if not await aiopath.exists(self.__ss_path):
            await makedirs(self.__ss_path)
        des_dir = ospath.join(self.__ss_path, f'{index}.jpg')
        cmds = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-start_at_zero", "-copyts", "-ss", str(duration), "-i", self.__path, "-vf",
                "drawtext=fontfile=font.ttf:fontsize=70:fontcolor=white:box=1:boxcolor=black@0.7:x=(W-tw)/1.05:y=h-(2*lh):text='%{pts\:gmtime\:0\:%H\\\\\:%M\\\\\:%S}'",
                "-vframes", "1", des_dir, "-y"]
        proc = await cmd_exec(cmds)
        if not await aiopath.exists(des_dir):
            LOGGER.error(proc[1])
            return
        with Image.open(des_dir) as img:
            img.convert('RGB').save(des_dir, 'JPEG')
        return des_dir

    async def file_ss(self):
        LOGGER.info(f'Generating Screenshot: {ospath.basename(self.__path)}')
        image = []
        min_dur, max_photo = 5, 10
        duration = (await get_media_info(self.__path))[0]
        if duration > min_dur:
            cur_step = duration // max_photo
            current = cur_step
            for x in range(max_photo):
                img = await self.__run_genss(current, str(x))
                image.append(img)
                current += cur_step
            if any(image):
                await self.__combine_image()
        if not await aiopath.exists(self.__images):
            self.__error = 'Failed generated screenshot, something wrong with url or not video in url!'
            LOGGER.info(f'Failed Generating Screenshot: {ospath.basename(self.__path)}')
        else:
            LOGGER.info(f'Successfully Generating Screenshot: {ospath.basename(self.__path)}')
        await clean_target(self.__ss_path)

    async def ddl_ss(self):
        self.__name = re_search('.+/(.+)', self.__path).group(1)
        await self.file_ss()

    @property
    def error(self):
        return self.__error

    @property
    def name(self):
        return self.__name

    @property
    def rimage(self):
        return self.__images