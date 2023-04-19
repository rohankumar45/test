from os import path as ospath
from time import time

from bot import LOGGER
from bot.helper.ext_utils.bot_utils import get_readable_file_size, MirrorStatus, get_readable_time, EngineStatus, presuf_remname_name, async_to_sync
from bot.helper.ext_utils.fs_utils import get_path_size


class SplitStatus:
    def __init__(self, name, size, gid, listener):
        self.__name = name
        self.__size = size
        self.__gid = gid
        self.__listener = listener
        self.__start_time = time()
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
        return self.__name

    def size(self):
        return get_readable_file_size(self.__size)

    def eta(self):
        try:
            return f'{get_readable_time((self.__size - self.processed_raw()) / self.speed_raw())}'
        except:
            return '~'

    def status(self):
        return MirrorStatus.STATUS_SPLITTING

    def processed_bytes(self):
        return get_readable_file_size(self.processed_raw())

    def processed_raw(self):
        return self.__listener.total_size + (async_to_sync(get_path_size, self.__listener.dir) - self.__size)

    def download(self):
        return self

    def listener(self):
        return self.__listener

    async def cancel_download(self):
        LOGGER.info(f'Cancelling Split: {self.name()}')
        if self.__listener.suproc is not None:
            self.__listener.suproc.kill()
        else:
            self.__listener.suproc = 'cancelled'
        await self.__listener.onUploadError('Splitting stopped by user!', self.name())

    def eng(self):
        return EngineStatus.STATUS_SPLIT

    @property
    def sname(self):
        name = self.name()
        if not self.__listener.newname and ospath.isfile(ospath.join(self.__listener.dir, name)):
            name = presuf_remname_name(self.__listener.user_dict, name)
        return name

