from bot.helper.ext_utils.bot_utils import MirrorStatus, get_readable_file_size, get_readable_time, EngineStatus, presuf_remname_name


class MegaDownloadStatus:
    def __init__(self, name, size, gid, obj, listener):
        self.__obj = obj
        self.__name = name
        self.__size = size
        self.__gid = gid
        self.__listener = listener
        self.message = listener.message

    def name(self):
        return self.__name

    def progress_raw(self):
        try:
            return round(self.__obj.downloaded_bytes / self.__size * 100,2)
        except:
            return 0.0

    def progress(self):
        return f'{self.progress_raw()}%'

    def status(self):
        return MirrorStatus.STATUS_DOWNLOADING

    def processed_bytes(self):
        return get_readable_file_size(self.__obj.downloaded_bytes)

    def eta(self):
        try:
            return get_readable_time((self.__size - self.__obj.downloaded_bytes) / self.__obj.speed)
        except:
            return '~'

    def size(self):
        return get_readable_file_size(self.__size)

    def speed(self):
        return f'{get_readable_file_size(self.__obj.speed)}/s'

    def gid(self):
        return self.__gid

    def download(self):
        return self.__obj

    def eng(self):
        return EngineStatus.STATUS_MEGA

    @property
    def sname(self):
        name = self.name()
        if not self.__listener.newname and self.__obj.type == 'file':
            name = presuf_remname_name(self.__listener.user_dict, name)
        return name