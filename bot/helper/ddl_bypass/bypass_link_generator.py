from base64 import b64decode
from bs4 import BeautifulSoup
from cloudscraper import create_scraper
from re import sub as re_sub, findall as re_findall, search as re_search, compile as re_compile
from time import time, sleep
from urllib.parse import urlparse, unquote

from bot import LOGGER
from bot.helper.ddl_bypass.addon import SiteList, RecaptchaV3, getlinks, decrypt_url
from bot.helper.ddl_bypass.direct_link_generator import direct_link_generator, get_fembed_links
from bot.helper.ext_utils.exceptions import DirectDownloadLinkException


def bypass_link(link: str) -> str:
    site = SiteList()
    if 'adf.ly' in link:
        return adfly(link)
    elif 'bluemediafile.site' in link:
        return bluemediafile(link)
    elif any(x in link for x in ['bit.ly', 'tinyurl.com']):
        return bit_tiny(link)
    elif 'droplink.co' in link:
        return droplink(link)
    elif 'earn.moneykamalo.com' in link:
        return moneykamalo(link)
    elif 'earnl.xyz' in link:
        return earnl(link)
    elif any(x in link for x in site.fembed_list):
        return fembed_bypass(link)
    elif 'filecrypt.co' in link:
        return filecrypt(link)
    elif 'flashlink.in' in link:
        return flashlink(link)
    elif 'gplinks.co' in link:
        return gplinks(link)
    elif any(x in link for x in ['gtlinks.me', 'theforyou.in', 'kinemaster.cc']):
        return gtlinks(link)
    elif 'hypershort.com' in link:
        return hypershort(link)
    elif 'indiurl.in' in link:
        return indiurl(link)
    elif 'linkbnao.co' in link:
        return linkbnao(link)
    elif 'linkvertise.com' in link:
        return linkvertise(link)
    elif 'mdiskshortners.in' in link:
        return mdiskshortners(link)
    elif 'mdisk.pro' in link:
        return mdiskpro(link)
    elif any(x in link for x in ['ouo.io', 'ouo.press']):
        return ouo(link)
    elif 'pkin.me' in link:
        return pkin(link)
    elif 'psa.pm' in link:
        return psa(link)
    elif 'rocklinks.net' in link:
        return rocklinks(link)
    elif 'rslinks.net' in link:
        return rslinks(link)
    elif 'shareus.in' in link:
        return shareus(link)
    elif any(x in link for x in site.shortest_list):
        return shortest(link)
    elif 'short2url.in' in link:
        return short2url(link)
    elif 'shortly.xyz' in link:
        return shortly(link)
    elif any(x in link for x in tuple(site.aio_bypass_dict()[0].keys())):
        return aio_one(link)
    elif any(x in link for x in tuple(site.aio_bypass_dict()[1].keys())):
        return aio_two(link)
    elif 'shortingly.me' in link:
        return shortingly(link)
    elif 'sirigan.my.id' in link :
        return sirigan(link)
    elif 'thinfi.com' in link:
        return thinfi(link)
    elif 'tinyfy.in' in link:
        return tinyfy(link)
    elif 'tnlink.in' in link:
        return tnlink(link)
    elif 'try2link.com' in link:
        return try2link(link)
    elif 'urlsopen.com' in link:
        return urlsopen(link)
    elif any(x in link for x in site.passvip_list):
        return vip_bypass(link)
    else:
        return direct_link_generator(link)


def adfly(url:str) -> str:
    cget = create_scraper().request
    try:
        res = cget('get', url).text
        out = {'error': False, 'src_url': url}
        try:
            ysmm = re_findall("ysmm\s+=\s+['|\'](.*?)['|\']", res)[0]
        except:
            out['error'] = True
            return out
        url = decrypt_url(ysmm)
        if re_search(r'go\.php\?u\=', url):
            url = b64decode(re_sub(r'(.*?)u=', '', url)).decode()
        elif '&dest=' in url:
            url = unquote(re_sub(r'(.*?)dest=', '', url))
        out['bypassed_url'] = url
        return out['bypassed_url']
    except Exception as e:
        LOGGER.error(e)
        raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}')


def bluemediafile(url, torrent=True):
    def decodeKey(encoded):
        key = ''
        i = len(encoded) // 2 - 5
        while i >= 0:
            key += encoded[i]
            i = i - 2
        i = len(encoded) // 2 + 4
        while i < len(encoded):
            key += encoded[i]
            i = i + 2
        return key
    headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:103.0) Gecko/20100101 Firefox/103.0',
               'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
               'Accept-Language': 'en-US,en;q=0.5',
               'Alt-Used': 'bluemediafiles.com',
               'Connection': 'keep-alive',
               'Upgrade-Insecure-Requests': '1',
               'Sec-Fetch-Dest': 'document',
               'Sec-Fetch-Mode': 'navigate',
               'Sec-Fetch-Site': 'none',
               'Sec-Fetch-User': '?1'}
    cget = create_scraper().request
    res = cget('get', url, headers=headers)
    soup = BeautifulSoup(res.text, 'html.parser')
    script = str(soup.findAll('script')[3])
    encodedKey = script.split('Create_Button("')[1].split('");')[0]
    headers.update({'Referer': url, 'Sec-Fetch-Site': 'same-origin'})
    params = {'url': decodeKey(encodedKey)}
    if torrent:
        res = cget('get', 'https://dl.pcgamestorrents.org/get-url.php', params=params, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        furl = soup.find('a', class_='button').get('href')
    else:
        res = cget('get', 'https://bluemediafiles.com/get-url.php', params=params, headers=headers)
        furl = res.url
        if 'mega.nz' in furl:
            furl = furl.replace('mega.nz/%23!', 'mega.nz/file/').replace('!', '#')
    try:
        return furl
    except Exception as e:
        LOGGER.error(e)
        raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}')


def bit_tiny(url: str) -> str:
    response = create_scraper().request('get', url).url
    if 'http' in response:
        return response
    else:
        raise DirectDownloadLinkException('ERROR: Error trying to bypass.')


def droplink(url: str) -> str:
    cget = create_scraper(allow_brotli=False).request
    res = cget('get', url, timeout=5)
    try:
        ref = re_findall("action[ ]{0,}=[ ]{0,}['|\"](.*?)['|\"]", res.text)[0]
        h = {'referer': ref}
        res = cget('get', url, headers=h)
        bs4 = BeautifulSoup(res.content, 'html.parser')
        inputs = bs4.find_all('input')
        data = {input.get('name'): input.get('value') for input in inputs}
        h = {'content-type': 'application/x-www-form-urlencoded', 'x-requested-with': 'XMLHttpRequest'}
        p = urlparse(url)
        final_url = f'{p.scheme}://{p.netloc}/links/go'
        sleep(3.1)
        res = cget('post', final_url, data=data, headers=h).json()
        if stats:= res['status'] == 'success':
            return res['url']
        else:
            raise DirectDownloadLinkException(f'ERROR: status {stats}.')
    except Exception as e:
        LOGGER.error(e)
        raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}')


def moneykamalo(url):
    cget = create_scraper().request
    DOMAIN = 'https://go.moneykamalo.com'
    url = url[:-1] if url[-1] == '/' else url
    code = url.split('/')[-1]
    final_url = f'{DOMAIN}/{code}'
    ref = 'https://techkeshri.com/'
    h = {'referer': ref}
    resp = cget('get', final_url, headers=h)
    soup = BeautifulSoup(resp.content, 'html.parser')
    try:
        inputs = soup.find_all('input')
        data = { input.get('name'): input.get('value') for input in inputs }
        h = {'x-requested-with': 'XMLHttpRequest'}
        sleep(5)
        r = cget('post', f'{DOMAIN}/links/go', data=data, headers=h)
        return r.json()['url']
    except Exception as e:
        LOGGER.error(e)
        raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}')


def earnl(url):
    cget = create_scraper().request
    DOMAIN = 'https://v.earnl.xyz'
    url = url[:-1] if url[-1] == '/' else url
    code = url.split('/')[-1]
    final_url = f'{DOMAIN}/{code}'
    ref = 'https://link.modmakers.xyz/'
    h = {'referer': ref}
    resp = cget('get', final_url, headers=h)
    soup = BeautifulSoup(resp.content, 'html.parser')
    try:
        inputs = soup.find_all('input')
        data = { input.get('name'): input.get('value') for input in inputs }
        h = { 'x-requested-with': 'XMLHttpRequest' }
        sleep(5)
        r = cget('post', f'{DOMAIN}/links/go', data=data, headers=h)
        return r.json()['url']
    except Exception as e:
        LOGGER.error(e)
        raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}')


def fembed_bypass(url: str) -> str:
    try:
        dl_url = get_fembed_links(url)
        res = ''
        for index, (qual, links) in enumerate(dl_url.items(), start=1):
            res += f"{index}. <b>{qual.replace('/mp4', '')}</b>:\n<code>{links}</code>\n"
        return res
    except Exception as e:
        LOGGER.error(e)
        raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}')


def filecrypt(url: str) -> str:
    client = create_scraper(allow_brotli=False)
    headers = {'authority': 'filecrypt.co',
               'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
               'accept-language': 'en-US,en;q=0.9',
               'cache-control': 'max-age=0',
               'content-type': 'application/x-www-form-urlencoded',
               'dnt': '1',
               'origin': 'https://filecrypt.co',
               'referer': url,
               'sec-ch-ua': "'Google Chrome';v='105', 'Not)A;Brand';v='8', 'Chromium';v='105'",
               'sec-ch-ua-mobile': '?0',
               'sec-ch-ua-platform': 'Windows',
               'sec-fetch-dest': 'document',
               'sec-fetch-mode': 'navigate',
               'sec-fetch-site': 'same-origin',
               'sec-fetch-user': '?1',
               'upgrade-insecure-requests': '1',
               'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36'}
    resp = client.get(url, headers=headers)
    soup = BeautifulSoup(resp.content, 'html.parser')
    buttons = soup.find_all('button')
    try:
        for ele in buttons:
            line = ele.get('onclick')
            if line and 'DownloadDLC' in line:
                dlclink = 'https://filecrypt.co/DLC/' + line.split('DownloadDLC('')[1].split(''')[0] + '.html'
                break
        resp = client.get(dlclink, headers=headers)
        result = getlinks(resp.text)
        links = ''
        for index, link in enumerate(result, start=1):
            links += f'{index}. <code>{link}</code>\n'
        return links
    except Exception as e:
        LOGGER.error(e)
        raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}')


def flashlink(url):
    DOMAIN = 'https://files.cordtpoint.co.in'
    url = url[:-1] if url[-1] == '/' else url
    code = url.split('/')[-1]
    final_url = f'{DOMAIN}/{code}'
    client = create_scraper(allow_brotli=False)
    resp = client.get(final_url)
    soup = BeautifulSoup(resp.content, 'html.parser')
    try:
        inputs = soup.find(id='go-link').find_all(name='input')
        data = { input.get('name'): input.get('value') for input in inputs }
        h = {'x-requested-with': 'XMLHttpRequest'}
        sleep(15)
        r = client.post(f'{DOMAIN}/links/go', data=data, headers=h)
        return r.json()['url']
    except Exception as e:
        LOGGER.error(e)
        raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}')


def gplinks(url: str) -> str:
    cget = create_scraper().request
    try:
        url = url[:-1] if url[-1] == '/' else url
        domain ='https://gplinks.co/'
        vid = cget('get', url, allow_redirects= False).headers['Location'].split('=')[-1]
        url = f'{url}/?{vid}'
        response = cget('get', url, allow_redirects=False)
        soup = BeautifulSoup(response.content, 'html.parser')
        inputs = soup.find(id='go-link').find_all(name='input')
        data = { input.get('name'): input.get('value') for input in inputs }
        sleep(5)
        headers={'x-requested-with': 'XMLHttpRequest'}
        return cget('post', domain+'links/go', data=data, headers=headers).json()['url']
    except Exception as e:
        LOGGER.error(e)
        raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}')


def gtlinks(url: str) -> str:
    client = create_scraper(allow_brotli=False)
    token = url.split('/')[-1]
    domain ='https://gplinks.co/'
    referer = 'https://mynewsmedia.co/'
    try:
        vid = client.get(url, allow_redirects= False).headers['Location'].split('=')[-1]
        url = f'{url}/?{vid}'
        response = client.get(url, allow_redirects=False)
        soup = BeautifulSoup(response.content, 'html.parser')
        inputs = soup.find(id='go-link').find_all(name='input')
        data = {input.get('name'): input.get('value') for input in inputs}
        sleep(10)
        headers={'x-requested-with': 'XMLHttpRequest'}
        return client.post(domain+'links/go', data=data, headers=headers).json()['url']
    except Exception as e:
        LOGGER.error(e)
        raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}')


def hypershort(url: str) -> str:
    cget = create_scraper().request
    response= cget('get', url)
    soup = BeautifulSoup(response.content, 'html.parser')
    dom = 'https://blog.miuiflash.com'
    token_response = cget('get', f'{dom}/links/createToken.js').text
    token_regex = re_search('itsToken\.value = \S+', token_response)
    token = token_regex[0].split("=")[1].removesuffix('"').removeprefix(' "')
    inputs = soup.find(id='re-form').find_all(name='input')
    data = { input.get('name'): input.get('value') for input in inputs }['getData']
    next_page_link = soup.find('form').get('action')
    resp = cget('post', next_page_link, data={'itsToken':token, 'get2Data':data},
    headers = {'referer':next_page_link})
    soup = BeautifulSoup(resp.content, 'html.parser')
    data = { input.get('name'): input.get('value') for input in inputs }
    sleep(4)
    tokenize_url = soup.find(name='iframe', id='anonIt').get('src')
    tokenize_url_resp = cget('get', tokenize_url)
    soup = BeautifulSoup(tokenize_url_resp.content, 'html.parser')
    sleep(3)
    try:
        inputs = soup.find(id='go-link').find_all(name='input')
        data = { input.get('name'): input.get('value') for input in inputs }
        return cget('post', f'{dom}/blog/links/go', data=data, cookies=tokenize_url_resp.cookies,
                    headers={'x-requested-with': 'XMLHttpRequest', 'referer':tokenize_url}).json()['url']
    except Exception as e:
        LOGGER.error(e)
        raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}')


def indiurl(url):
    cget = create_scraper().request
    DOMAIN = 'https://file.earnash.com/'
    url = url[:-1] if url[-1] == '/' else url
    code = url.split('/')[-1]
    final_url = f'{DOMAIN}/{code}'
    ref = 'https://indiurl.cordtpoint.co.in/'
    h = {'referer': ref}
    resp = cget('get', final_url, headers=h)
    soup = BeautifulSoup(resp.content, 'html.parser')
    try:
        inputs = soup.find_all('input')
        data = { input.get('name'): input.get('value') for input in inputs }
        h = {'x-requested-with': 'XMLHttpRequest'}
        sleep(10)
        r = cget('post', f'{DOMAIN}/links/go', data=data, headers=h)
        return r.json()['url']
    except Exception as e:
        LOGGER.error(e)
        raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}')


def linkbnao(url):
    client = create_scraper(allow_brotli=False)
    DOMAIN = 'https://vip.linkbnao.com'
    url = url[:-1] if url[-1] == '/' else url
    code = url.split('/')[-1]
    final_url = f'{DOMAIN}/{code}'
    ref = 'https://ffworld.xyz/'
    h = {'referer': ref}
    resp = client.get(final_url, headers=h)
    soup = BeautifulSoup(resp.content, 'html.parser')
    try:
        inputs = soup.find_all('input')
        data = { input.get('name'): input.get('value') for input in inputs }
        h = {'x-requested-with': 'XMLHttpRequest'}
        sleep(2)
        r = client.post(f'{DOMAIN}/links/go', data=data, headers=h)
        return r.json()['url']
    except Exception as e:
        LOGGER.error(e)
        raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}')


def linkvertise(url):
    params = {'url': url,}
    response = create_scraper().get('https://bypass.pm/bypass2', params=params).json()
    if response['success']:
        return response['destination']
    else:
        raise DirectDownloadLinkException(f'ERROR: {response["msg"]}')


def mdiskshortners(url):
    client = create_scraper(allow_brotli=False)
    DOMAIN = 'https://mdiskshortners.in/'
    url = url[:-1] if url[-1] == '/' else url
    code = url.split('/')[-1]
    final_url = f'{DOMAIN}/{code}'
    ref = 'https://www.adzz.in/'
    h = {'referer': ref}
    resp = client.get(final_url, headers=h)
    soup = BeautifulSoup(resp.content, 'html.parser')
    try:
        inputs = soup.find_all('input')
        data = { input.get('name'): input.get('value') for input in inputs }
        h = {'x-requested-with': 'XMLHttpRequest'}
        sleep(2)
        r = client.post(f'{DOMAIN}/links/go', data=data, headers=h)
        return r.json()['url']
    except Exception as e:
        LOGGER.error(e)
        raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}')


def mdiskpro(url):
    client = create_scraper(allow_brotli=False)
    DOMAIN = 'https://mdisk.pro'
    ref = 'https://m.meclipstudy.in/'
    h = {'referer': ref}
    resp = client.get(url, headers=h)
    soup = BeautifulSoup(resp.content, 'html.parser')
    try:
        inputs = soup.find_all('input')
        data = { input.get('name'): input.get('value') for input in inputs }
        h = {'x-requested-with': 'XMLHttpRequest'}
        sleep(8)
        r = client.post(f'{DOMAIN}/links/go', data=data, headers=h)
        return r.json()['url']
    except Exception as e:
        LOGGER.error(e)
        raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}')


def ouo(url: str) -> str:
    cget = create_scraper().request
    try:
        tempurl = url.replace('ouo.press', 'ouo.io')
        p = urlparse(tempurl)
        id = tempurl.split('/')[-1]
        res = cget('get', tempurl)
        next_url = f'{p.scheme}://{p.hostname}/go/{id}'
        anchor_url = 'https://www.google.com/recaptcha/api2/anchor?ar=1&k=6Lcr1ncUAAAAAH3cghg6cOTPGARa8adOf-y9zv2x&co=aHR0cHM6Ly9vdW8uaW86NDQz&hl=en&v=1B_yv3CBEV10KtI2HJ6eEXhJ&size=invisible&cb=4xnsug1vufyr'
        for _ in range(2):
            if res.headers.get('Location'):
                break
            bs4 = BeautifulSoup(res.content, 'lxml')
            inputs = bs4.form.findAll('input', {'name': re_compile(r'token$')})
            data = { input.get('name'): input.get('value') for input in inputs }
            ans = RecaptchaV3(anchor_url)
            data['x-token'] = ans
            h = {'content-type': 'application/x-www-form-urlencoded'}
            res = cget('post', next_url, data=data, headers=h, allow_redirects=False)
            next_url = f'{p.scheme}://{p.hostname}/xreallcygo/{id}'
        result = res.headers.get('Location')
        if any(x in result for x in ['ouo.io', 'ouo.press']):
            return ouo(result)
        return result
    except Exception as e:
        LOGGER.error(e)
        raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}')


def pkin(url: str) -> str:
    url = url[:-1] if url[-1] == '/' else url
    token = url.split('/')[-1]
    domain = 'https://go.paisakamalo.in/'
    referer = 'https://techkeshri.com/'
    token = url.split('/')[-1]
    cget = create_scraper().request
    user_agent= 'Mozilla/5.0 (Linux; Android 11; 2201116PI) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Mobile Safari/537.36'
    response = cget('get', domain+token, headers={'referer': referer, 'user-agent': user_agent})
    soup = BeautifulSoup(response.content, 'html.parser')
    try:
        inputs = soup.find(id='go-link').find_all(name='input')
        data = { input.get('name'): input.get('value') for input in inputs }
        time.sleep(3)
        headers = {'x-requested-with': 'XMLHttpRequest', 'user-agent': user_agent}
        return cget('post', domain+'links/go', data=data, headers=headers).json()['url']
    except Exception as e:
        LOGGER.error(e)
        raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}')


def psa(url: str) -> str:
    client = create_scraper(allow_brotli=False)
    r = client.get(url)
    soup = BeautifulSoup(r.text, 'html.parser').find_all(class_='dropshadowboxes-drop-shadow dropshadowboxes-rounded-corners dropshadowboxes-inside-and-outside-shadow dropshadowboxes-lifted-both dropshadowboxes-effect-default')
    links = []
    for link in soup:
        try:
            exit_gate = link.a.get('href')
            links.append(try2link(exit_gate))
        except:
            pass
    if links:
        result = ''
        for index, res in enumerate(links, start=1):
            result += f'{index}. <code>{res}</code>\n'
        return result
    else:
        raise DirectDownloadLinkException('ERROR: Error trying bypass from PSA.')


def rocklinks(url: str) -> str:
    client = create_scraper(allow_brotli=False)
    DOMAIN = 'https://rl.techysuccess.com'
    url = url[:-1] if url[-1] == '/' else url
    code = url.split('/')[-1]
    final_url = f'{DOMAIN}/{code}'
    ref = 'https://disheye.com/'
    h = {'referer': ref}
    resp = client.get(final_url, headers=h)
    soup = BeautifulSoup(resp.content, 'html.parser')
    try: inputs = soup.find(id='go-link').find_all(name='input')
    except: return 'Incorrect Link'
    data = { input.get('name'): input.get('value') for input in inputs }
    h = { 'x-requested-with': 'XMLHttpRequest' }
    sleep(10)
    r = client.post(f'{DOMAIN}/links/go', data=data, headers=h)
    try:
        return r.json()['url']
    except Exception as e:
        LOGGER.error(e)
        raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}')


def rslinks(url):
    download = create_scraper().request('get', url, stream=True, allow_redirects=False)
    try:
        res = download.headers['location']
        code = res.split('ms9')[-1]
        final = f'http://techyproio.blogspot.com/p/short.html?{code}=='
        return final
    except Exception as e:
        LOGGER.error(e)
        raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}')

def shareus(url: str) -> str:
    token = url.split('=')[-1]
    bypassed_url = 'https://us-central1-my-apps-server.cloudfunctions.net/r?shortid='+ token
    cget = create_scraper().request
    response = cget('get', bypassed_url).text
    if not 'Error' in response:
        return response
    else:
        raise DirectDownloadLinkException('ERROR: Error trying bypass from Shareus.')


def shortest(url: str) -> str:
    cget = create_scraper().request
    try:
        parsed_url = urlparse(url)
        resp = cget('get', url, headers={'referer': url})
        session_id = re_findall('''sessionId(?:\s+)?:(?:\s+)?['|'](.*?)['|']''', resp.text)[0]
        final_url = f'{parsed_url.scheme}://{parsed_url.netloc}/shortest-url/end-adsession'
        params = {'adSessionId': session_id, 'callback': '_'}
        sleep(5)
        response = cget('get', final_url, params=params, headers={'referer': url})
        return re_findall('"(.*?)"', response.text)[1].replace('\/','/')
    except Exception as e:
        LOGGER.error(e)
        raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}')


def short2url(url):
    client = create_scraper(allow_brotli=False)
    DOMAIN = 'https://techyuth.xyz/blog'
    url = url[:-1] if url[-1] == '/' else url
    code = url.split('/')[-1]
    final_url = f'{DOMAIN}/{code}'
    ref = 'https://blog.coin2pay.xyz/'
    h = {'referer': ref}
    resp = client.get(final_url, headers=h)
    soup = BeautifulSoup(resp.content, 'html.parser')
    try:
        inputs = soup.find_all('input')
        data = { input.get('name'): input.get('value') for input in inputs }
        h = { 'x-requested-with': 'XMLHttpRequest' }
        sleep(10)
        r = client.post(f'{DOMAIN}/links/go', data=data, headers=h)
        return r.json()['url']
    except Exception as e:
        LOGGER.error(e)
        raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}')


def shortly(url: str) -> str:
    cget = create_scraper().request
    try:
        shortly_url = url[:-1] if url[-1] == '/' else url
        token = shortly_url.split('/')[-1]
        shortly_bypass_api = 'https://www.shortly.xyz/getlink.php/'
        return cget('post', shortly_bypass_api, data={'id':token}, headers={'referer':'https://www.shortly.xyz/link'}).text
    except Exception as e:
        LOGGER.error(e)
        raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}')


def aio_one(url: str)-> str:
    shortner_dict = SiteList().aio_bypass_dict()[0]
    domain, sleep_time = [shortner_dict[x] for x in tuple(shortner_dict.keys()) if x in url][0]
    shortner_url = url[:-1] if url[-1] == '/' else url
    token = shortner_url.split('/')[-1]
    cget = create_scraper().request
    response = cget('get', domain + token, headers={'referer': domain + token})
    soup = BeautifulSoup(response.content, 'html.parser')
    try:
        inputs = soup.find(id='go-link').find_all(name='input')
        data = { input.get('name'): input.get('value') for input in inputs }
        sleep(sleep_time)
        headers = {'x-requested-with': 'XMLHttpRequest'}
        return cget('post', domain + 'links/go', data=data, headers=headers).json()['url']
    except Exception as e:
        LOGGER.error(e)
        raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}')


def aio_two(url: str) -> str:
    shortner_dict = SiteList().aio_bypass_dict()[1]
    domain, referer, sleep_time = [shortner_dict[x] for x in tuple(shortner_dict.keys()) if x in url][0]
    shortner_url = url[:-1] if url[-1] == '/' else url
    token = shortner_url.split('/')[-1]
    cget = create_scraper().request
    response = cget('get', domain+token, headers={'referer': referer})
    soup = BeautifulSoup(response.content, 'html.parser')
    try:
        inputs = soup.find(id='go-link').find_all(name='input')
        data = { input.get('name'): input.get('value') for input in inputs }
        sleep(sleep_time)
        headers={'x-requested-with': 'XMLHttpRequest'}
        return cget('post', domain+'links/go', data=data, headers=headers).json()['url']
    except Exception as e:
        LOGGER.error(e)
        raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}')


def shortingly(url: str) -> str:
    client = create_scraper(allow_brotli=False)
    DOMAIN = 'https://go.techyjeeshan.xyz'
    url = url[:-1] if url[-1] == '/' else url
    code = url.split('/')[-1]
    final_url = f'{DOMAIN}/{code}'
    resp = client.get(final_url)
    soup = BeautifulSoup(resp.content, 'html.parser')
    try:
        inputs = soup.find(id='go-link').find_all(name='input')
    except:
        raise DirectDownloadLinkException('ERROR: Incorrect link!')
    data = { input.get('name'): input.get('value') for input in inputs }
    h = { 'x-requested-with': 'XMLHttpRequest' }
    sleep(5)
    r = client.post(f'{DOMAIN}/links/go', data=data, headers=h)
    try:
        return r.json()['url']
    except Exception as e:
        raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}')


def sirigan(url: str) -> str:
    res = create_scraper().request('get', url)
    try:
        url = res.url.split('=', maxsplit=1)[-1]
        while True:
            try: url = b64decode(url).decode('utf-8')
            except: break
        return url.split('url=')[-1]
    except Exception as e:
        LOGGER.error(e)
        raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}')


def thinfi(thinfi_url: str) -> str :
    response = create_scraper().request('get', thinfi_url)
    try:
        return BeautifulSoup(response.content, 'html.parser').p.a.get('href')
    except Exception as e:
        LOGGER.error(e)
        raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}')


def tinyfy(url):
    cget = create_scraper().request
    DOMAIN = 'https://tinyfy.in'
    url = url[:-1] if url[-1] == '/' else url
    code = url.split('/')[-1]
    final_url = f'{DOMAIN}/{code}'
    ref = 'https://www.yotrickslog.tech/'
    h = {'referer': ref}
    resp = cget('get', final_url, headers=h)
    soup = BeautifulSoup(resp.content, 'html.parser')
    try:
        inputs = soup.find_all('input')
        data = { input.get('name'): input.get('value') for input in inputs }
        h = {'x-requested-with': 'XMLHttpRequest'}
        r = cget('post', f'{DOMAIN}/links/go', data=data, headers=h)
        return r.json()['url']
    except Exception as e:
        LOGGER.error(e)
        raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}')


def tnlink(url):
    client = create_scraper()
    DOMAIN = 'https://internet.usanewstoday.club'
    url = url[:-1] if url[-1] == '/' else url
    code = url.split('/')[-1]
    final_url = f'{DOMAIN}/{code}'
    ref = 'https://usanewstoday.club/'
    h = {'referer': ref}
    while len(client.cookies) == 0:
        resp = client.get(final_url, headers=h)
        sleep(2)
    soup = BeautifulSoup(resp.content, 'html.parser')
    try:
        inputs = soup.find_all('input')
        data = {input.get('name'): input.get('value') for input in inputs}
        h = {'x-requested-with': 'XMLHttpRequest'}
        sleep(8)
        r = client.post(f'{DOMAIN}/links/go', data=data, headers=h)
        return r.json()['url']
    except Exception as e:
        LOGGER.error(e)
        raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}')


def try2link(url):
    cget = create_scraper(allow_brotli=False).request
    url = url[:-1] if url[-1] == '/' else url
    params = (('d', int(time()) + (60 * 4)),)
    r = cget('get', url, params=params, headers= {'Referer': 'https://newforex.online/'})
    soup = BeautifulSoup(r.text, 'html.parser')
    try:
        inputs = soup.find(id='go-link').find_all(name='input')
        data = { input.get('name'): input.get('value') for input in inputs }
        time.sleep(7)
        headers = {'Host': 'try2link.com', 'X-Requested-With': 'XMLHttpRequest', 'Origin': 'https://try2link.com', 'Referer': url}
        bypassed_url = cget('post', 'https://try2link.com/links/go', headers=headers,data=data)
        return bypassed_url.json()['url']
    except Exception as e:
        LOGGER.error(e)
        raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}')


def urlsopen(url):
    client = create_scraper(allow_brotli=False)
    DOMAIN = 'https://blogpost.viewboonposts.com/ssssssagasdgeardggaegaqe'
    url = url[:-1] if url[-1] == '/' else url
    code = url.split('/')[-1]
    final_url = f'{DOMAIN}/{code}'
    ref = 'https://blog.textpage.xyz/'
    h = {'referer': ref}
    resp = client.get(final_url, headers=h)
    soup = BeautifulSoup(resp.content, 'html.parser')
    try:
        inputs = soup.find_all('input')
        data = {input.get('name'): input.get('value') for input in inputs}
        h = {'x-requested-with': 'XMLHttpRequest'}
        sleep(2)
        r = client.post(f'{DOMAIN}/links/go', data=data, headers=h)
        return r.json()['url']
    except Exception as e:
        LOGGER.error(e)
        raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}')


def vip_bypass(url) -> str:
    cget = create_scraper().request
    try:
        data = {'url': url,}
        r = cget('post', 'https://api.bypass.vip/', data=data)
        b = r.json()
        if b['success'] == True:
            return b['destination']
        else:
            raise DirectDownloadLinkException(f'ERROR: Error when trying bypass from {urlparse(url).netloc}.')
    except Exception as e:
        LOGGER.error(e)
        raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}')