from bot.helper.ext_utils.bot_utils import MirrorStatus, get_readable_file_size, get_readable_time, EngineStatus, presuf_remname_name


class TelegramStatus:
    def __init__(self, obj, listener, size, gid, status):
        self.__obj = obj
        self.__listener = listener
        self.__size = size
        self.__gid = gid
        self.__status = status
        self.message = listener.message

    def processed_bytes(self):
        return get_readable_file_size(self.__obj.processed_bytes)

    def size(self):
        return get_readable_file_size(self.__size)

    def status(self):
        if self.__status == 'dl':
            return MirrorStatus.STATUS_DOWNLOADING
        return MirrorStatus.STATUS_UPLOADING

    def name(self):
        return self.__obj.name

    def progress(self):
        try:
            progress_raw = self.__obj.processed_bytes / self.__size * 100
        except:
            progress_raw = 0
        return f'{round(progress_raw, 2)}%'

    def speed(self):
        return f'{get_readable_file_size(self.__obj.speed)}/s'

    def eta(self):
        try:
            return f'{get_readable_time((self.__size - self.__obj.processed_bytes) / self.__obj.speed)}'
        except:
            return '~'

    def gid(self) -> str:
        return self.__gid

    def download(self):
        return self.__obj

    def eng(self):
        return EngineStatus.STATUS_TG

    @property
    def sname(self):
        name = self.name()
        if self.__status == 'dl' and not self.__listener.newname:
            name = presuf_remname_name(self.__listener.user_dict, name)
        return name



