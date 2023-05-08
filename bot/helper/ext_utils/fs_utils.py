from aiofiles import open as aiopen
from aiofiles.os import remove as aioremove, path as aiopath, listdir, makedirs, rename as aiorename
from aiohttp import ClientSession
from aioshutil import rmtree as aiormtree, disk_usage
from asyncio import create_subprocess_exec
from magic import Magic
from os import walk, path as ospath
from re import split as re_split, search as re_search, sub as resub, I
from shutil import rmtree
from subprocess import run as srun
from sys import exit as sexit

from bot import aria2, config_dict, get_client, DOWNLOAD_DIR, LOGGER, GLOBAL_EXTENSION_FILTER
from bot.helper.ext_utils.bot_utils import sync_to_async
from bot.helper.ext_utils.exceptions import NotSupportedExtractionArchive


ARCH_EXT = ['.tar.bz2', '.tar.gz', '.bz2', '.gz', '.tar.xz', '.tar', '.tbz2', '.tgz', '.lzma2',
            '.zip', '.7z', '.z', '.rar', '.iso', '.wim', '.cab', '.apm', '.arj', '.chm',
            '.cpio', '.cramfs', '.deb', '.dmg', '.fat', '.hfs', '.lzh', '.lzma', '.mbr',
            '.msi', '.mslz', '.nsis', '.ntfs', '.rpm', '.squashfs', '.udf', '.vhd', '.xar']

FIRST_SPLIT_REGEX = r'(\.|_)part0*1\.rar$|(\.|_)7z\.0*1$|(\.|_)zip\.0*1$|^(?!.*(\.|_)part\d+\.rar$).*\.rar$'

SPLIT_REGEX = r'\.r\d+$|\.7z\.\d+$|\.z\d+$|\.zip\.\d+$'


def is_first_archive_split(file):
    return bool(re_search(FIRST_SPLIT_REGEX, file))


def is_archive(file):
    return file.endswith(tuple(ARCH_EXT))


def is_archive_split(file):
    return bool(re_search(SPLIT_REGEX, file))


async def download_gclone():
    LOGGER.info('Downloading GClone...')
    await clean_target('gclone')
    if GCLONE_URL:= config_dict['GCLONE_URL']:
        try:
            async with ClientSession() as session:
                async with session.get(GCLONE_URL) as r:
                    if r.status == 200:
                        async for data in r.content.iter_chunked(1024):
                            async with aiopen('gclone', 'ba') as f:
                                await f.write(data)
        except Exception as e:
            LOGGER.error(e)
        if await aiopath.exists('gclone'):
            await (await create_subprocess_exec('chmod', '-R', '777', 'gclone')).wait()
            LOGGER.info('GClone sucessfully downloaded!')


async def clean_target(path: str):
    if await aiopath.exists(path):
        LOGGER.info(f'Cleaning Target: {path}')
        cleaned = False
        if await aiopath.isdir(path):
            try:
                await rmtree(path)
                cleaned = True
            except:
                pass
        elif await aiopath.isfile(path):
            try:
                await aioremove(path)
                cleaned = True
            except:
                pass
        return cleaned


async def clean_download(path):
    if await aiopath.exists(path):
        LOGGER.info(f'Cleaning Download: {path}')
        try:
            await aiormtree(path)
        except:
            pass


async def start_cleanup():
    get_client().torrents_delete(torrent_hashes='all')
    try:
        await aiormtree(DOWNLOAD_DIR)
    except:
        pass
    await makedirs(DOWNLOAD_DIR)


def clean_all():
    aria2.remove_all(True)
    qb = get_client()
    qb.torrents_delete(torrent_hashes='all')
    qb.auth_log_out()
    try:
        rmtree(DOWNLOAD_DIR)
    except:
        pass


def exit_clean_up(signal, frame):
    try:
        LOGGER.info('Please wait, while we clean up and stop the running downloads')
        clean_all()
        srun(['pkill', '-9', '-f', 'gunicorn|aria2c|qbittorrent-nox|ffmpeg'])
        sexit(0)
    except KeyboardInterrupt:
        LOGGER.warning('Force Exiting before the cleanup finishes!')
        sexit(1)


async def clean_unwanted(path):
    LOGGER.info(f'Cleaning unwanted files/folders: {path}')
    for dirpath, _, files in await sync_to_async(walk, path, topdown=False):
        for filee in files:
            if filee.endswith('.!qB') or filee.endswith('.parts') and filee.startswith('.'):
                await clean_target(ospath.join(dirpath, filee))
        if dirpath.endswith(('.unwanted', 'splited_files_mltb', 'copied_mltb')):
            await aiormtree(dirpath)
    for dirpath, _, files in await sync_to_async(walk, path, topdown=False):
        if not await listdir(dirpath):
            await clean_target(dirpath)


async def get_path_size(path):
    if await aiopath.isfile(path):
        return await aiopath.getsize(path)
    total_size = 0
    for root, _, files in await sync_to_async(walk, path):
        for f in files:
            abs_path = ospath.join(root, f)
            total_size += await aiopath.getsize(abs_path)
    return total_size


async def count_files_and_folders(path):
    total_files = total_folders = 0
    for _, dirs, files in await sync_to_async(walk, path):
        total_files += len(files)
        for f in files:
            if f.endswith(tuple(GLOBAL_EXTENSION_FILTER)):
                total_files -= 1
        total_folders += len(dirs)
    return total_folders, total_files


async def presuf_remname_file(path: str, prename: str, sufname: str, remname: str):
    if await aiopath.isfile(path):
        filename = ospath.basename(path)
        filedir = ospath.split(path)[0]
        if prename:
            filename = f'{prename} {filename}'
        if sufname:
            try:
                fname, ext = filename.rsplit('.', maxsplit=1)
                filename = f'{fname} {sufname}.{ext}'
            except: pass
        if remname:
            try: filename = resub(remname.strip('|'), '', str(filename))
            except: pass
        newpath = ospath.join(filedir, filename)
        if any([prename, remname, sufname]):
            await aiorename(path, newpath)
        return str(newpath)
    for root, _, files in await sync_to_async(walk, path):
        for filename in files:
            file = filename
            if prename:
                filename = f'{prename} {filename}'
            if sufname:
                try:
                    fname, ext = filename.rsplit('.', maxsplit=1)
                    filename = f'{fname} {sufname}.{ext}'
                except:
                    pass
            if remname:
                try: filename = resub(remname.strip('|'), '', str(filename))
                except: pass
            if any([prename, remname, sufname]):
                await aiorename(ospath.join(root, file), ospath.join(root, filename))
    return path


async def check_storage_threshold(size: int, arch=False, alloc=False):
    STORAGE_THRESHOLD = config_dict['STORAGE_THRESHOLD']
    if not alloc:
        if not arch:
            if await disk_usage(DOWNLOAD_DIR).free - size < STORAGE_THRESHOLD * 1024**3:
                return False
        elif await disk_usage(DOWNLOAD_DIR).free - (size * 2) < STORAGE_THRESHOLD * 1024**3:
            return False
    elif not arch:
        if await disk_usage(DOWNLOAD_DIR).free < STORAGE_THRESHOLD * 1024**3:
            return False
    elif await disk_usage(DOWNLOAD_DIR).free - size < STORAGE_THRESHOLD * 1024**3:
        return False
    return True


def get_base_name(orig_path):
    extension = next((ext for ext in ARCH_EXT if orig_path.lower().endswith(ext)), '')
    if extension != '':
        return re_split(f'{extension}$', orig_path, maxsplit=1, flags=I)[0]
    else:
        raise NotSupportedExtractionArchive('File format not supported for extraction')


def get_mime_type(file_path):
    mime = Magic(mime=True)
    mime_type = mime.from_file(file_path)
    mime_type = mime_type or 'text/plain'
    return mime_type