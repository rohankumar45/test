from os import path as ospath

from bot import config_dict
from bot.helper.ext_utils.bot_utils import get_readable_file_size, sync_to_async, cmd_exec
from bot.helper.ext_utils.fs_utils import get_path_size
from bot.helper.ext_utils.telegraph_helper import TelePost


async def mediainfo(path: str, size: int) -> str:
    name = ospath.basename(path)
    file_size = get_readable_file_size(await get_path_size(path))
    total_size = get_readable_file_size(size)
    metadata = (await cmd_exec(['mediainfo', path]))[0].replace(path, name)
    metadata = f"<img src='{config_dict['IMAGE_MEDINFO']}' /><b>{name}<br>Size: {file_size}/{total_size}</b><br><pre>{metadata}</pre>"
    telepost = TelePost('Media Info')
    return await sync_to_async(telepost.create_post, metadata)