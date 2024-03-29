from os import path as ospath

from bot.helper.ext_utils.bot_utils import MirrorStatus, EngineStatus, presuf_remname_name


class RcloneStatus:
    def __init__(self, obj, listener, gid, status):
        self.__obj = obj
        self.__gid = gid
        self.__listener = listener
        self.__status = status
        self.message = listener.message

    def gid(self):
        return self.__gid

    def progress(self):
        return self.__obj.percentage

    def speed(self):
        return self.__obj.speed

    def name(self):
        return self.__obj.name

    def size(self):
        return self.__obj.size

    def eta(self):
        return self.__obj.eta

    def status(self):
        if self.__status == 'dl':
            return MirrorStatus.STATUS_DOWNLOADING
        elif self.__status == 'up':
            return MirrorStatus.STATUS_UPLOADING
        else:
            return MirrorStatus.STATUS_CLONING

    def processed_bytes(self):
        return self.__obj.transferred_size

    def download(self):
        return self.__obj

    def eng(self):
        return EngineStatus.STATUS_RCLONE

    @property
    def sname(self):
        name = self.name()
        if self.__status == 'dl' and not self.__listener.newname and ospath.isfile(ospath.join(self.__listener.dir, name)):
            name = presuf_remname_name(self.__listener.user_dict, name)
        return name