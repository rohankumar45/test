from aiohttp import ClientSession
from base64 import b64decode, b64encode
from json import loads as jsonloads
from urllib.parse import quote

from bot import LOGGER


next_page = False
next_page_token = ''


async def func(payload_input, url, username, password):
    global next_page, next_page_token
    url = url + '/' if  url[-1] != '/' else url
    try:
        user_pass = f'{username}:{password}'
        headers = {'authorization': 'Basic '+ b64encode(user_pass.encode()).decode()}
    except:
        return 'Username/password combination is wrong or invalid link!'
    try:
        async with ClientSession() as session:
            async with session.post(url, data=payload_input, headers=headers) as r:
                if r.status == 401:
                    return 'Username/password combination is wrong or invalid link!'
                try:
                    json_data = b64decode((await r.read())[::-1][24:-20]).decode('utf-8')
                    decrypted_response = jsonloads(json_data)
                except:
                    return 'Something went wrong or invalid link! Check index link/username/password and try again.'
    except:
        return 'Something wrong or invalid link!'
    page_token = decrypted_response.get('nextPageToken')
    if page_token == None:
        next_page = False
    else:
        next_page = True
        next_page_token = page_token
    result = []
    try:
        if list(decrypted_response.get('data').keys())[0] == 'error':
            raise Exception
        file_length = len(decrypted_response['data']['files'])
        for i, _ in enumerate(range(file_length)):
            files_type = decrypted_response['data']['files'][i]['mimeType']
            files_name = decrypted_response['data']['files'][i]['name']
            if files_type != 'application/vnd.google-apps.folder':
                direct_download_link = url + quote(files_name)
                result.append(direct_download_link)
    except Exception as e:
        LOGGER.error(e.__class__.__name__)
    return result


async def index_scrap(url, username='none', password='none'):
    x = 0
    payload = {'page_token':next_page_token, 'page_index': x}
    res = await func(payload, url, username, password)
    results = []
    if 'wrong' not in res:
        results.extend(res)
    while next_page == True:
        payload = {'page_token':next_page_token, 'page_index': x}
        res = await func(payload, url, username, password)
        if 'wrong' not in res:
            results.extend(res)
        x += 1
    return res if 'wrong' in res else results


async def index_scrapper(listener):
    msg = listener.message.text
    reply_to = listener.reply_to
    url = listener.link
    mesg = msg.split('\n')
    message_args = mesg[0].split(maxsplit=1)
    pswd = usr = ''
    pswd_arg = mesg[0].split(' pswd: ')
    if reply_to:
        url = reply_to.text
        if len(pswd_arg) > 1:
            pswd = pswd_arg[1]
        if len(mesg) > 2:
            msg = msg.split()
            usr = msg[1]
            pswd = msg[2]
    if not reply_to and len(pswd_arg) > 1:
        pswd = pswd_arg[1]
    if not reply_to and len(mesg) > 2:
        try:
            msg = msg.split()
            url = msg[1]
            usr = msg[2]
            pswd = msg[3]
        except:
            await listener.OnScrapError()
            return
    if reply_to:
        if len(message_args) and len(msg) == 1:
            usr = None
            pswd = None
    return await index_scrap(url, usr, pswd)