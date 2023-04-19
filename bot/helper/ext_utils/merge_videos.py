from aiofiles import open as aiopen
from asyncio import create_subprocess_exec, sleep, gather
from asyncio.subprocess import PIPE
from math import floor
from natsort import natsorted
from os import path as ospath, walk
from re import findall as re_findall

from bot import download_dict, download_dict_lock, LOGGER
from bot.helper.ext_utils.fs_utils import get_path_size, clean_target
from bot.helper.ext_utils.leech_utils import get_media_info, get_document_type
from bot.helper.ext_utils.bot_utils import sync_to_async
from bot.helper.mirror_utils.status_utils.ffmpeg_status import FFMpegStatus
from bot.helper.telegram_helper.message_utils import update_all_messages


class Merge:
    def __init__(self, listener):
        self.__listener = listener
        self.__processed_bytes = 0
        self.__percent = 0
        self.__eta = 0
        self.__duration = 0

    @property
    def processed_bytes(self):
        return self.__processed_bytes

    @property
    def percent(self):
        return self.__percent

    @property
    def eta(self):
        return self.__eta

    async def __progress(self, progress):
        while self.__listener.suproc != 0:
            await sleep(1)
            async with aiopen(progress, 'r+') as f:
                text = await f.read()
                await f.truncate(0)
            time_used = re_findall('out_time_ms=(\d+)', text)
            prog = re_findall('progress=(\w+)', text)
            speed = re_findall('speed=(\d+\.?\d*)', text)
            total_size = re_findall('total_size=(\d+)', text)
            if len(prog) and prog[-1] == 'end':
                break
            time_used = time_used[-1] if len(time_used) else 1
            speed = speed[-1] if len(speed) else 1
            elapsed_time = int(time_used) / 1000000

            self.__processed_bytes = int(total_size[-1]) if len(total_size) else 1
            self.__eta = floor((self.__duration - elapsed_time) / float(speed))
            self.__percent = floor(elapsed_time * 100 / self.__duration)

    async def merge_vids(self, path, gid):
        list_files, remove_files = [], []
        for dirpath, _, files in await sync_to_async(walk, path):
            for file in natsorted(files):
                video_file = ospath.join(dirpath, file)
                if (await get_document_type(video_file))[0]:
                    self.__duration += (await get_media_info(video_file))[0]
                    list_files.append(f"file '{video_file}'")
                    remove_files.append(video_file)
        if len(list_files) > 1:
            name = ospath.basename(path)
            size = await get_path_size(path)
            async with download_dict_lock:
                download_dict[self.__listener.uid] = FFMpegStatus(name, size, gid, self, self.__listener)
            await update_all_messages()
            input_file, progress = ospath.join(path, 'input.txt'), ospath.join(path, 'progress.txt')
            async with aiopen(input_file, 'w') as f:
                await f.write('\n'.join(list_files))
            LOGGER.info(f'Merging: {name}')
            cmd = ['ffmpeg', '-ignore_unknown', '-loglevel', 'error', '-progress', progress, '-f', 'concat',
                   '-safe', '0', '-i', input_file, '-map', '0', '-c', 'copy', f'{ospath.join(path, name)}.mkv']
            self.__listener.suproc = await create_subprocess_exec(*cmd)
            _, code = await gather(self.__progress(progress), self.__listener.suproc.wait())
            if self.__listener.suproc == 'cancelled' or code == -9:
                return
            elif code == 0:
                await gather(clean_target(input_file), clean_target(progress))
                if not self.__listener.seed:
                    await gather(*[clean_target(file) for file in remove_files])
                LOGGER.info(f'Merge successfully with name: {name}.mkv')
            else:
                LOGGER.error(f'Failed to merge: {name}.mkv')
        return True