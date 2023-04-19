from bot.helper.ext_utils.bot_utils import MirrorStatus, get_readable_file_size, get_readable_time, EngineStatus


class GofileUploadStatus:
    def __init__(self, obj, size, gid, message):
        self.__obj = obj
        self.__size = size
        self.__gid = gid
        self.message = message

    def processed_bytes(self):
        return get_readable_file_size(self.__obj.uploaded_bytes)

    def size(self):
        return get_readable_file_size(self.__size)

    def status(self):
        return MirrorStatus.STATUS_UPLOADINGTOGO

    def name(self):
        return self.__obj.name

    def progress_raw(self):
        try:
            return self.__obj.uploaded_bytes / self.__size * 100
        except ZeroDivisionError:
            return 0

    def progress(self):
        return f'{round(self.progress_raw(), 2)}%'

    def speed(self):
        return f'{get_readable_file_size(self.__obj.speed)}/s'

    def eta(self):
        try:
            return f'{get_readable_time((self.__size - self.__obj.uploaded_bytes) / self.__obj.speed)}'
        except ZeroDivisionError:
            return '~'

    def gid(self) -> str:
        return self.__gid

    def download(self):
        return self.__obj

    def eng(self):
        return EngineStatus.STATUS_GFILE

    @property
    def sname(self):
        return self.name()


