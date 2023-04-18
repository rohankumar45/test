import mimetypes

from aiofiles.os import path as aiopath, listdir
from aiohttp import ClientSession
from os import path as ospath
from requests import post as rpost, put as rput
from requests_toolbelt import MultipartEncoder
from requests_toolbelt.multipart.encoder import MultipartEncoderMonitor
from threading import RLock
from time import time

from bot import config_dict, LOGGER
from bot.helper.ext_utils.bot_utils import sync_to_async


class GoFileUploader:
    def __init__(self, name=None, listener=None, createdfolderid=None):
        self.__listener = listener
        self.uploaded_bytes = 0
        self.__start_time = time()
        self.__is_cancelled = False
        self.createdfolderid = createdfolderid
        self.name = name
        self.folderpathd = []
        self.__resource_lock = RLock()
        self.__server = 2

    async def __get_server(self):
        async with ClientSession() as session:
            async with session.get('https://api.gofile.io/getServer') as r:
                server = (await r.json())['data']['server']
                server = int(server.split('e', maxsplit=1)[1])
                if server != 5:
                    self.__server = server
        LOGGER.info(f'GoFile running in server {self.__server}')

    def callback(self, monitor, chunk=(1024 * 1024 * 30), bytesread=0, bytestemp=0):
        bytesread += monitor.bytes_read
        bytestemp += monitor.bytes_read
        if bytestemp > chunk:
            self.uploaded_bytes = bytesread
            bytestemp = 0

    async def uploadThis(self):
        await self.__get_server()
        file_path = ospath.join(self.__listener.dir, self.name)
        if await aiopath.isfile(file_path):
            await sync_to_async(self.gofileupload_, filepath=(file_path), parentfolderid=self.createdfolderid)
        else:
            await self.uploadNow(file_path, self.createdfolderid)
        self.folderpathd = []

    async def uploadNow(self, path, createdfolderid):
        self.folderpathd.append(createdfolderid)
        for f in await listdir(path):
            file_path = ospath.join(path, f)
            if await aiopath.isfile(file_path):
                await sync_to_async(self.gofileupload_, filepath=file_path, parentfolderid=self.folderpathd[-1])
            elif await aiopath.isdir(file_path):
                subfolder = await sync_to_async(self.gofoldercreate_, foldername=f, parentfolderid=self.folderpathd[-1])
                y = subfolder['id']
                await self.uploadNow(file_path, y)
        del self.folderpathd[-1]

    def gofileupload_(self, filepath, parentfolderid):
        filename = ospath.basename(filepath)
        mimetype = mimetypes.guess_type(filename)
        m = MultipartEncoder(fields={'file': (filename, open(filepath, 'rb'), mimetype), 'token': config_dict['GOFILETOKEN'], 'folderId': parentfolderid})
        monitor = MultipartEncoderMonitor(m, self.callback)
        headers = {'Content-Type': monitor.content_type}
        rpost(f'https://store{self.__server}.gofile.io/uploadFile', data=monitor, headers=headers)

    def gofoldercreate_(self, foldername, parentfolderid):
        m = {'folderName': foldername, 'token': config_dict['GOFILETOKEN'], 'parentFolderId': parentfolderid}
        x = rput('https://api.gofile.io/createFolder', data=m).json()['data']
        LOGGER.info(f'Created Folder {foldername}')
        return x

    @property
    def speed(self):
        with self.__resource_lock:
            try:
                return self.uploaded_bytes / (time() - self.__start_time)
            except ZeroDivisionError:
                return 0

    @property
    def cancelled(self):
        return self.__is_cancelled

    async def cancel_download(self):
        self.__is_cancelled = True
        LOGGER.info(f'Cancelling Upload: {self.name}')
        await self.__listener.onUploadError('Your upload has been stopped!', self.name)
