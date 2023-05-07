from time import time
from os import path as ospath

from bot import LOGGER
from bot.helper.ext_utils.bot_utils import get_readable_file_size, MirrorStatus, get_readable_time, EngineStatus, presuf_remname_name, async_to_sync
from bot.helper.ext_utils.fs_utils import get_path_size


class ZipStatus:
    def __init__(self, name, size, gid, listener, zpath=''):
        self.__name = name
        self.__zpath = zpath
        self.__size = size
        self.__gid = gid
        self.__start_time = time()
        self.__iszpath = False
        self.__listener = listener
        self.message = listener.message

    def gid(self):
        return self.__gid

    def speed_raw(self):
        return self.processed_raw() / (time() - self.__start_time)

    def progress_raw(self):
        try:
            return self.processed_raw() / self.__size * 100
        except:
            return 0

    def progress(self):
        return f'{round(self.progress_raw(), 2)}%'

    def speed(self):
        return f'{get_readable_file_size(self.speed_raw())}/s'

    def name(self):
        if self.__zpath and (zname := ospath.basename(self.__zpath)) != self.__name:
            self.__iszpath = True
            zname = presuf_remname_name(self.__listener.user_dict, zname)
            zsize = get_readable_file_size(async_to_sync(get_path_size, self.__listener.dir))
            return f'{self.__name} ({zsize}) ~ {zname}.zip'
        return self.__name

    def size(self):
        return get_readable_file_size(self.__size)

    def eta(self):
        try:
            return get_readable_time((self.__size - self.processed_raw()) / self.speed_raw())
        except:
            return '~'

    def status(self):
        return MirrorStatus.STATUS_ARCHIVING

    def processed_raw(self):
        if self.__listener.newDir or self.__zpath:
            return async_to_sync(get_path_size, self.__listener.newDir)
        else:
            return async_to_sync(get_path_size, self.__listener.dir) - self.__size

    def processed_bytes(self):
            return get_readable_file_size(self.processed_raw())

    def download(self):
        return self

    async def cancel_download(self):
        LOGGER.info(f'Cancelling Archive: {self.__name}')
        if self.__listener.suproc:
            try: self.__listener.suproc.kill()
            except: pass
        else:
            self.__listener.suproc = 'cancelled'
        await self.__listener.onUploadError('Archiving stopped by user!', self.__name)

    def eng(self):
        return EngineStatus.STATUS_ZIP

    @property
    def sname(self):
        name = self.name()
        if not self.__iszpath and not self.__listener.newname:
            name = presuf_remname_name(self.__listener.user_dict, name)
        return name