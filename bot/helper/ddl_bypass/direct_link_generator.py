from base64 import b64decode
from bs4 import BeautifulSoup
from cloudscraper import create_scraper
from hashlib import sha256
from http.cookiejar import MozillaCookieJar
from json import loads as jsonloads, dumps as jsondumps
from lxml import etree
from os import path
from re import findall as re_findall, match as re_match, search as re_search, compile as re_compile, sub, DOTALL
from requests import Session
from time import sleep
from urllib.parse import parse_qs, quote, unquote, urlparse
from uuid import uuid4

from bot import config_dict, LOGGER
from bot.helper.ext_utils.bot_utils import is_sharar, get_readable_time, is_gdrive_link
from bot.helper.ddl_bypass.addon import SiteList
from bot.helper.ext_utils.exceptions import DirectDownloadLinkException


def direct_link_generator(link: str):
    domain = urlparse(link).hostname
    if not domain:
        raise DirectDownloadLinkException("ERROR: Invalid URL")
    site = SiteList()
    if 'youtube.com' in domain or 'youtu.be' in domain:
        raise DirectDownloadLinkException("ERROR: Use ytdl cmds for YouTube links!")
    # File Hoster
    elif '1fichier.com' in domain:
        return fichier(link)
    elif 'akmfiles' in domain:
        return akmfiles(link)
    elif any(x in domain for x in site.anon_site):
        return anonbase(link)
    elif 'antfiles.com' in domain:
        return antfiles(link)
    elif 'github.com' in domain:
        return github(link)
    elif 'gofile.io' in domain:
        return gofile(link)
    elif 'hxfile.co' in domain:
        return hxfile(link)
    elif 'krakenfiles.com' in domain:
        return krakenfiles(link)
    elif 'letsupload.io' in domain:
        return letsupload(link)
    elif 'linkbox' in domain:
        return linkbox(link)
    elif "mdisk.me" in domain:
        return mdisk(link)
    elif 'mediafire.com' in domain:
        return mediafire(link)
    elif '1drv.ms' in domain:
        return onedrive(link)
    elif 'osdn.net' in domain:
        return osdn(link)
    elif 'pixeldrain.com' in domain:
        return pixeldrain(link)
    elif 'racaty' in domain:
        return racaty(link)
    elif 'romsget.io' in domain:
        return link if domain == 'static.romsget.io' else romsget(link)
    elif 'send.cm' in domain:
        return sendcm(link)
    elif 'sfile.mobi' in domain:
        return sfile(link)
    elif 'shrdsk' in domain:
        return shrdsk(link)
    elif 'solidfiles.com' in domain:
        return solidfiles(link)
    elif 'sourceforge.net' in domain:
        return sourceforge(link)
    elif any(x in domain for x in ['terabox', 'nephobox', '4funbox', 'mirrobox', 'momerybox', '1024tera']):
        return terabox(link)
    elif 'uploadbaz.me' in domain:
        return uploadbaz(link)
    elif 'upload.ee' in domain:
        return uploadee(link)
    elif 'uppit.com' in domain:
        return uppit(link)
    elif 'uptobox.com' in domain:
        return uptobox(link)
    elif 'userscloud.com' in domain:
        return userscloud(link)
    elif any(x in domain for x in ['wetransfer.com', 'we.tl']):
        return wetransfer(link)
    elif 'yadi.sk' in domain or 'disk.yandex.com' in domain:
        return yandex_disk(link)
    # Video Hoster
    elif any(x in domain for x in site.fembed_list):
        return fembed(link)
    elif 'mp4upload.com' in domain:
        return mp4upload(link)
    elif any(x in domain for x in ['slmaxed.com', 'sltube.org']):
        return streamlare(link)
    elif any(x in domain for x in site.sbembed_list):
        return streamsb(link)
    elif 'streamtape.com' in domain:
        return streamtape(link)
    # GDrive Sharer
    elif is_sharar(link):
        if is_gdrive_link(link):
            return link
        elif 'gdtot' in domain:
            return gdtot(link)
        elif 'filepress' in domain:
            return filepress(link)
        elif 'sharer.pw' in domain:
            return sharerpw(link)
        else:
            return sharer_scraper(link)
    else:
        raise DirectDownloadLinkException(f'No direct link function found for {link}')


#================================================== FILE HOSTER ===============================================
def fichier(link: str) -> str:
    regex = r"^([http:\/\/|https:\/\/]+)?.*1fichier\.com\/\?.+"
    gan = re_match(regex, link)
    if not gan:
        raise DirectDownloadLinkException("ERROR: The link you entered is wrong!")
    if "::" in link:
        pswd = link.split("::")[-1]
        url = link.split("::")[-2]
    else:
        pswd = None
        url = link
    cget = create_scraper().request
    try:
        if pswd is None:
            req = cget('post', url)
        else:
            pw = {"pass": pswd}
            req = cget('post', url, data=pw)
    except Exception as e:
        raise DirectDownloadLinkException(f"ERROR: {e}")
    if req.status_code == 404:
        raise DirectDownloadLinkException("ERROR: File not found/The link you entered is wrong!")
    soup = BeautifulSoup(req.content, 'lxml')
    if soup.find("a", {"class": "ok btn-general btn-orange"}):
        if dl_url := soup.find("a", {"class": "ok btn-general btn-orange"})["href"]:
            return dl_url
        raise DirectDownloadLinkException("ERROR: Unable to generate Direct Link 1fichier!")
    elif len(soup.find_all("div", {"class": "ct_warn"})) == 3:
        str_2 = soup.find_all("div", {"class": "ct_warn"})[-1]
        if "you must wait" in str(str_2).lower():
            if numbers := [int(word) for word in str(str_2).split() if word.isdigit()]:
                raise DirectDownloadLinkException(f"ERROR: 1fichier is on a limit. Please wait {numbers[0]} minute.")
            else:
                raise DirectDownloadLinkException("ERROR: 1fichier is on a limit. Please wait a few minutes/hour.")
        elif "protect access" in str(str_2).lower():
            raise DirectDownloadLinkException("ERROR: This link requires a password!\n\n<b>This link requires a password!</b>\n- Insert sign <b>::</b> after the link and write the password after the sign.\n\n<b>Example:</b> https://1fichier.com/?smmtd8twfpm66awbqz04::love you\n\n* No spaces between the signs <b>::</b>\n* For the password, you can use a space!")
        else:
            raise DirectDownloadLinkException("ERROR: Failed to generate Direct Link from 1fichier!")
    elif len(soup.find_all("div", {"class": "ct_warn"})) == 4:
        str_1 = soup.find_all("div", {"class": "ct_warn"})[-2]
        str_3 = soup.find_all("div", {"class": "ct_warn"})[-1]
        if "you must wait" in str(str_1).lower():
            if numbers := [int(word) for word in str(str_1).split() if word.isdigit()]:
                raise DirectDownloadLinkException(f"ERROR: 1fichier is on a limit. Please wait {numbers[0]} minute.")
            else:
                raise DirectDownloadLinkException("ERROR: 1fichier is on a limit. Please wait a few minutes/hour.")
        elif "bad password" in str(str_3).lower():
            raise DirectDownloadLinkException("ERROR: The password you entered is wrong!")
        else:
            raise DirectDownloadLinkException("ERROR: Error trying to generate Direct Link from 1fichier!")
    else:
        raise DirectDownloadLinkException("ERROR: Error trying to generate Direct Link from 1fichier!")


def akmfiles(url):
    cget = create_scraper().request
    try:
        url = cget('GET', url).url
        json_data = {
            'op': 'download2',
            'id': url.split('/')[-1]
            }
        res = cget('POST', url, data=json_data)
    except Exception as e:
        raise DirectDownloadLinkException(f'ERROR: {e}')
    if (direct_link := etree.HTML(res.content).xpath("//a[contains(@class,'btn btn-dow')]/@href")):
        return direct_link[0]
    else:
        raise DirectDownloadLinkException('ERROR: Error trying to generate direct link from Akmfiles.')


def anonbase(url: str) -> str:
    cget = create_scraper().request
    try:
        soup = BeautifulSoup(cget('get', url).content, 'lxml')
    except Exception as e:
        raise DirectDownloadLinkException(f"ERROR: {e}")
    if sa := soup.find(id="download-url"):
        return sa['href']
    raise DirectDownloadLinkException("ERROR: Error trying to generate direct link.")


def antfiles(url: str) -> str:
    cget = create_scraper().request
    raw = cget('get', url)
    text = raw.text if hasattr(raw, "text") else raw
    try:
        soup = BeautifulSoup(text, "html.parser")
        if (a := soup.find(class_="main-btn", href=True)):
            return "{0.scheme}://{0.netloc}/{1}".format(urlparse(url), a["href"])
    except Exception as e:
        raise DirectDownloadLinkException(f"ERROR: {e}")


def github(url: str) -> str:
    try:
        re_findall(r'\bhttps?://.*github\.com.*releases\S+', url)[0]
    except IndexError:
        raise DirectDownloadLinkException("No GitHub Releases links found")
    cget = create_scraper().request
    download = cget('get', url, stream=True, allow_redirects=False)
    try:
        return download.headers["location"]
    except KeyError:
        raise DirectDownloadLinkException("ERROR: Can't extract the Github link.")


def gofile(url: str) -> str:
    api_uri = 'https://api.gofile.io'
    session = Session()
    args = {'fileNum':0, 'password':''}
    try:
        if '--' in url:
            _link = url.split('--')
            url = _link[0]
            for l in _link[1:]:
                if 'pw:' in l:
                    args['password'] = l.strip('pw:')
                if 'fn:' in l:
                    args['fileNum'] = int(l.strip('fn:'))
        crtAcc = session.get(api_uri+'/createAccount').json()
        data = {'contentId': url.split('/')[-1],
                'token': crtAcc['data']['token'],
                'websiteToken': '12345',
                'cache': 'true',
                'password': sha256(args['password'].encode('utf-8')).hexdigest()}
        getCon = session.get(api_uri+'/getContent', params=data).json()
    except Exception as e:
        raise DirectDownloadLinkException(f"ERROR: {e}")
    fileNum = args.get('fileNum')
    if getCon['status'] == 'ok':
        rstr = jsondumps(getCon)
        link = re_findall(r'"link": "(.*?)"', rstr)
        if fileNum > len(link):
            fileNum = 0 #Force to first link
    elif getCon['status'] == 'error-passwordWrong':
        raise DirectDownloadLinkException(f"ERROR: Password required!\n\n- Use <b>--pw:</b> arg after the link.\n<b>Example:</b> <code>/cmd https://gofile.io/d/xyz--pw:love you</code>")
    else:
        raise DirectDownloadLinkException("ERROR: Error trying to generate direct link from Gofile.")
    dl_url = link[fileNum] if fileNum == 0 else link[fileNum-1]
    headers=f"""Host: {urlparse(dl_url).netloc}
                Cookie: accountToken={data['token']}
            """
    return dl_url, headers


def hxfile(url: str) -> str:
    cget = create_scraper().request
    headers = {'content-type': 'application/x-www-form-urlencoded',
               'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.152 Safari/537.36'}
    data = {'op': 'download2',
            'id': urlparse(url).path.strip("/"),
            'rand': '',
            'referer': '',
            'method_free': '',
            'method_premium': ''}
    response = cget('post', url, headers=headers, data=data)
    text = response.text if hasattr(response, "text") else response
    link = None
    soup = BeautifulSoup(text, "html.parser")
    if (btn := soup.find(class_="btn btn-dow")):
        link = btn["href"]
    if (unique := soup.find(id="uniqueExpirylink")):
        link = unique["href"]
    if link:
        return link
    else:
        raise DirectDownloadLinkException("ERROR: Error trying to generate direct link from HxFile.")


def krakenfiles(page_link: str) -> str:
    cget = create_scraper().request
    try:
        page_resp = cget('get', page_link)
    except Exception as e:
        raise DirectDownloadLinkException(f"ERROR: {e}")
    soup = BeautifulSoup(page_resp.text, "lxml")
    try:
        token = soup.find("input", id="dl-token")["value"]
    except:
        raise DirectDownloadLinkException(f"ERROR: Page link is wrong: {page_link}")
    hashes = [item["data-file-hash"] for item in soup.find_all("div", attrs={"data-file-hash": True})]
    if not hashes:
        raise DirectDownloadLinkException(f"ERROR: Hash not found for : {page_link}")
    dl_hash = hashes[0]
    payload = f'------WebKitFormBoundary7MA4YWxkTrZu0gW\r\nContent-Disposition: form-data; name="token"\r\n\r\n{token}\r\n------WebKitFormBoundary7MA4YWxkTrZu0gW--'
    headers = {"content-type": "multipart/form-data; boundary=----WebKitFormBoundary7MA4YWxkTrZu0gW",
               "cache-control": "no-cache",
               "hash": dl_hash}
    dl_link_resp = cget('post', f"https://krakenfiles.com/download/{hash}", data=payload, headers=headers)
    dl_link_json = dl_link_resp.json()
    if "url" in dl_link_json:
        return dl_link_json["url"]
    else:
        raise DirectDownloadLinkException(f"ERROR: Failed to acquire download URL from kraken for: {page_link}")


def letsupload(url: str) -> str:
    cget = create_scraper().request
    try:
        res = cget("POST", url)
    except Exception as e:
        raise DirectDownloadLinkException(f'ERROR: {e}')
    if direct_link := re_findall(r"(https?://letsupload\.io\/.+?)\'", res.text):
        return direct_link[0]
    else:
        raise DirectDownloadLinkException('ERROR: Direct Link not found')


def linkbox(url):
    cget = create_scraper().request
    try:
        url = cget('GET', url).url
        res = cget('GET', f'https://www.linkbox.to/api/file/detail?itemId={url.split("/")[-1]}').json()
    except Exception as e:
        raise DirectDownloadLinkException(f'ERROR: {e}')
    if 'data' not in res:
        raise DirectDownloadLinkException('ERROR: Data not found!!')
    data = res['data']
    if not data:
        raise DirectDownloadLinkException('ERROR: Data is None!!')
    if 'itemInfo' not in data:
        raise DirectDownloadLinkException('ERROR: itemInfo not found!!')
    itemInfo = data['itemInfo']
    if 'url' not in itemInfo:
        raise DirectDownloadLinkException('ERROR: url not found in itemInfo!!')
    if "name" not in itemInfo:
        raise DirectDownloadLinkException('ERROR: Name not found in itemInfo!!')
    name = quote(itemInfo["name"])
    raw = itemInfo['url'].split("/", 3)[-1]
    return f'https://wdl.nuplink.net/{raw}&filename={name}'


def mdisk(url: str) -> str:
    cget = create_scraper().request
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36"}
        link = url[:-1] if url[-1] == '/' else url
        token = link.split("/")[-1]
        api = f"https://diskuploader.entertainvideo.com/v1/file/cdnurl?param={token}"
        response = cget('get', api, headers=headers).json()
        download_url = response["download"]
        return download_url.replace(" ", "%20")
    except Exception as e:
        LOGGER.error(e)
        raise DirectDownloadLinkException(f"ERROR: {e}")


def mediafire(url: str) -> str:
    if final_link := re_findall(r'https?:\/\/download\d+\.mediafire\.com\/\S+\/\S+\/\S+', url):
        return final_link[0]
    cget = create_scraper().request
    try:
        url = cget('get', url).url
        page = cget('get', url).text
    except Exception as e:
        raise DirectDownloadLinkException(f"ERROR: {e}")
    if not (final_link := re_findall(r"\'(https?:\/\/download\d+\.mediafire\.com\/\S+\/\S+\/\S+)\'", page)):
        raise DirectDownloadLinkException("ERROR: No links found in this page.")
    return final_link[0]


def onedrive(link: str) -> str:
    cget = create_scraper().request
    try:
        link = cget('get', link).url
        parsed_link = urlparse(link)
        link_data = parse_qs(parsed_link.query)
    except Exception as e:
        raise DirectDownloadLinkException(f"ERROR: {e}")
    if not link_data:
        raise DirectDownloadLinkException("ERROR: Unable to find link_data")
    folder_id = link_data.get('resid')
    if not folder_id:
        raise DirectDownloadLinkException('ERROR: folder id not found')
    folder_id = folder_id[0]
    authkey = link_data.get('authkey')
    if not authkey:
        raise DirectDownloadLinkException('ERROR: authkey not found')
    authkey = authkey[0]
    boundary = uuid4()
    headers = {'content-type': f'multipart/form-data;boundary={boundary}'}
    data = f'--{boundary}\r\nContent-Disposition: form-data;name=data\r\nPrefer: Migration=EnableRedirect;FailOnMigratedFiles\r\nX-HTTP-Method-Override: GET\r\nContent-Type: application/json\r\n\r\n--{boundary}--'
    try:
        resp = cget(
            'get', f'https://api.onedrive.com/v1.0/drives/{folder_id.split("!", 1)[0]}/items/{folder_id}?$select=id,@content.downloadUrl&ump=1&authKey={authkey}', headers=headers, data=data).json()
    except Exception as e:
        raise DirectDownloadLinkException(f'ERROR: {e}')
    if "@content.downloadUrl" not in resp:
        raise DirectDownloadLinkException('ERROR: Direct link not found')
    return resp['@content.downloadUrl']


def osdn(url: str) -> str:
    osdn_link = 'https://osdn.net'
    try:
        link = re_findall(r'\bhttps?://.*osdn\.net\S+', url)[0]
    except IndexError:
        raise DirectDownloadLinkException("No OSDN links found.")
    cget = create_scraper().request
    try:
        page = BeautifulSoup(cget('get', link, allow_redirects=True).content, 'lxml')
    except Exception as e:
        raise DirectDownloadLinkException(f"ERROR: {e}")
    info = page.find('a', {'class': 'mirror_link'})
    link = unquote(osdn_link + info['href'])
    mirrors = page.find('form', {'id': 'mirror-select-form'}).findAll('tr')
    urls = []
    for data in mirrors[1:]:
        mirror = data.find('input')['value']
        urls.append(sub(r'm=(.*)&f', f'm={mirror}&f', link))
    return urls[0]


def pixeldrain(url: str) -> str:
    url = url.strip("/ ")
    file_id = url.split("/")[-1]
    if url.split("/")[-2] == "l":
        info_link = f"https://pixeldrain.com/api/list/{file_id}"
        dl_link = f"https://pixeldrain.com/api/list/{file_id}/zip"
    else:
        info_link = f"https://pixeldrain.com/api/file/{file_id}/info"
        dl_link = f"https://pixeldrain.com/api/file/{file_id}"
    cget = create_scraper().request
    try:
        resp = cget('get', info_link).json()
    except Exception as e:
        raise DirectDownloadLinkException(f"ERROR: {e}")
    if resp["success"]:
        return dl_link
    else:
        raise DirectDownloadLinkException(f"ERROR: Cant't download due {resp['message']}.")


def racaty(url: str) -> str:
    cget = create_scraper().request
    try:
        url = cget('GET', url).url
        json_data = {'op': 'download2', 'id': url.split('/')[-1]}
        res = cget('POST', url, data=json_data)
    except Exception as e:
        raise DirectDownloadLinkException(f'ERROR: {e}')
    if (direct_link := etree.HTML(res.text).xpath("//a[contains(@id,'uniqueExpirylink')]/@href")):
        return direct_link[0]
    else:
        raise DirectDownloadLinkException("ERROR: Error trying to generate direct link from Racaty.")


def romsget(url: str) -> str:
    cget = create_scraper().request
    try:
        bs1 = BeautifulSoup(cget('GET', url).text, 'html.parser')
        upos = bs1.find('form', {'id':'download-form'}).get('action')
        meid = bs1.find('input', {'id':'mediaId'}).get('name')
        try:
            dlid = bs1.find('button', {'data-callback':'onDLSubmit'}).get('dlid')
        except:
            dlid = bs1.find('div', {'data-callback':'onDLSubmit'}).get('dlid')
        pos = cget("post", "https://www.romsget.io"+upos, data={meid:dlid})
        bs2 = BeautifulSoup(pos.text, 'html.parser')
        udl = bs2.find('form', {'name':'redirected'}).get('action')
        prm = bs2.find('input', {'name':'attach'}).get('value')
        return f"{udl}?attach={prm}"
    except Exception as e:
        LOGGER.error(e)
        raise DirectDownloadLinkException(f"ERROR: {e}")


def sendcm(url: str) -> str:
    base_url = "https://send.cm/"
    client = create_scraper(allow_brotli=False)
    hs = {"Content-Type": "application/x-www-form-urlencoded",
          "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36"}
    resp = client.get(url)
    scrape = BeautifulSoup(resp.text, "html.parser")
    inputs = scrape.find_all("input")
    file_id = inputs[1]["value"]
    parse = {"op":"download2", "id": file_id, "referer": url}
    resp2 = client.post(base_url, data=parse, headers=hs, allow_redirects=False)
    dl_url = resp2.headers["Location"]
    dl_url = dl_url.replace(" ", "%20")
    if "http" in dl_url:
        return dl_url
    else:
        raise DirectDownloadLinkException("ERROR: Error trying to generate direct link from Sendcm.")


def sfile(url:str) -> str:
    cget = create_scraper().request
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Linux; Android 8.0.1; SM-G532G Build/MMB29T) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3239.83 Mobile Safari/537.36"}
        url = url[:-1] if url[-1] == '/' else url
        token = url.split("/")[-1]
        soup = BeautifulSoup(cget("get", "https://sfile.mobi/download/" + token, headers=headers).content, "html.parser")
        return soup.find("p").a.get("href")
    except Exception as e:
        LOGGER.error(e)
        raise DirectDownloadLinkException(f"ERROR: {e}")


def shrdsk(url):
    cget = create_scraper().request
    try:
        url = cget('GET', url).url
        res = cget('GET', f'https://us-central1-affiliate2apk.cloudfunctions.net/get_data?shortid={url.split("/")[-1]}')
    except Exception as e:
        raise DirectDownloadLinkException(f'ERROR: {e}')
    if res.status_code != 200:
        raise DirectDownloadLinkException(f'ERROR: Status Code {res.status_code}')
    res = res.json()
    if ("type" in res and res["type"].lower() == "upload" and "video_url" in res):
        return res["video_url"]
    raise DirectDownloadLinkException("ERROR: cannot find direct link.")


def solidfiles(url: str) -> str:
    cget = create_scraper().request
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/36.0.1985.125 Safari/537.36'}
        pageSource = cget('get', url, headers=headers).text
        mainOptions = str(re_search(r'viewerOptions\'\,\ (.*?)\)\;', pageSource).group(1))
        return jsonloads(mainOptions)["downloadUrl"]
    except Exception as e:
        raise DirectDownloadLinkException(f"ERROR: {e}")


def sourceforge(url: str) -> str:
    cget = create_scraper().request
    try:
        link = re_findall(r"\bhttps?://sourceforge\.net\S+", url)[0]
        file_path = re_findall(r"files(.*)/download", link)[0]
        project = re_findall(r"projects?/(.*?)/files", link)[0]
        mirrors = (
            f"https://sourceforge.net/settings/mirror_choices?"
            f"projectname={project}&filename={file_path}"
        )
        page = BeautifulSoup(cget('get', mirrors).content, "html.parser")
        info = page.find("ul", {"id": "mirrorList"}).findAll("li")
        for mirror in info[1:]:
            return f'https://{mirror["id"]}.dl.sourceforge.net/project/{project}/{file_path}?viasf=1'
    except Exception as e:
        LOGGER.error(e)
        raise DirectDownloadLinkException(f"ERROR: {e}")


def terabox(url) -> str:
    if not path.isfile('terabox.txt'):
        raise DirectDownloadLinkException("ERROR: terabox.txt not found.")
    session = create_scraper()
    try:
        res = session.request('GET', url)
        key = res.url.split('?surl=')[-1]
        jar = MozillaCookieJar('terabox.txt')
        jar.load()
        session.cookies.update(jar)
        res = session.request('GET', f'https://www.terabox.com/share/list?app_id=250528&shorturl={key}&root=1')
        result = res.json()['list']
    except Exception as e:
        raise DirectDownloadLinkException(f"ERROR: {e}")
    if len(result) > 1:
        raise DirectDownloadLinkException("ERROR: Can't download mutiple files!")
    result = result[0]
    if result['isdir'] != '0':
        raise DirectDownloadLinkException("ERROR: Can't download folder!")
    return result['dlink']


def uploadbaz(url: str)-> str:
    try:
        url = url[:-1] if url[-1] == '/' else url
        token = url.split("/")[-1]
        cget = create_scraper().request
        headers = {'content-type': 'application/x-www-form-urlencoded',
                'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36'}
        data = {'op': 'download2',
                'id': token,
                'rand': '',
                'referer': '',
                'method_free': '',
                'method_premium': ''}
        response = cget('post', url, headers=headers, data=data, allow_redirects=False)
        return response.headers["Location"]
    except Exception as e:
        LOGGER.error(e)
        raise DirectDownloadLinkException(f"ERROR: {e}")


def uploadee(url: str) -> str:
    cget = create_scraper().request
    try:
        soup = BeautifulSoup(cget('get', url).content, 'lxml')
        sa = soup.find('a', attrs={'id': 'd_l'})
        return sa['href']
    except:
        raise DirectDownloadLinkException(f"ERROR: Failed to acquire download URL from upload.ee for : {url}")


def uppit(url: str)-> str:
    try:
        url = url[:-1] if url[-1] == '/' else url
        token = url.split("/")[-1]
        cget = create_scraper().request
        headers = {'content-type': 'application/x-www-form-urlencoded',
                'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36'}
        data = {'op': 'download2',
                'id': token,
                'rand': '',
                'referer': '',
                'method_free': '',
                'method_premium': ''}
        response = cget('post', url, headers=headers, data=data)
        soup = BeautifulSoup(response.text, "html.parser")
        return soup.find("span", {'style':'background:#f9f9f9;border:1px dotted #bbb;padding:7px;'}).a.get("href")
    except Exception as e:
        LOGGER.error(e)
        raise DirectDownloadLinkException(f"ERROR: {e}")


def userscloud(url: str)-> str:
    try:
        url = url[:-1] if url[-1] == '/' else url
        token = url.split("/")[-1]
        cget = create_scraper().request
        headers = {'content-type': 'application/x-www-form-urlencoded',
                'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36'}
        data = {'op': 'download2',
                'id': token,
                'rand': '',
                'referer': '',
                'method_free': '',
                'method_premium': ''}
        response = cget('post', url, headers=headers, data=data, allow_redirects=False)
        return response.headers['Location']
    except Exception as e:
        LOGGER.error(e)
        raise DirectDownloadLinkException(f"ERROR: {e}")


def uptobox(url: str) -> str:
    """ Uptobox direct link generator
    based on https://github.com/jovanzers/WinTenCermin and https://github.com/sinoobie/noobie-mirror """
    try:
        link = re_findall(r'\bhttps?://.*uptobox\.com\S+', url)[0]
    except IndexError:
        raise DirectDownloadLinkException("No Uptobox links found")
    if link := re_findall(r'\bhttps?://.*\.uptobox\.com/dl\S+', url):
        return link[0]
    cget = create_scraper().request
    try:
        file_id = re_findall(r'\bhttps?://.*uptobox\.com/(\w+)', url)[0]
        if UPTOBOX_TOKEN := config_dict['UPTOBOX_TOKEN']:
            file_link = f'https://uptobox.com/api/link?token={UPTOBOX_TOKEN}&file_code={file_id}'
        else:
            file_link = f'https://uptobox.com/api/link?file_code={file_id}'
        res = cget('get', file_link).json()
    except Exception as e:
        raise DirectDownloadLinkException(f"ERROR: {e}")
    if res['statusCode'] == 0:
        return res['data']['dlLink']
    elif res['statusCode'] == 16:
        sleep(1)
        waiting_token = res["data"]["waitingToken"]
        sleep(res["data"]["waiting"])
    elif res['statusCode'] == 39:
        raise DirectDownloadLinkException(f"ERROR: Uptobox is being limited please wait {get_readable_time(res['data']['waiting'])}")
    else:
        raise DirectDownloadLinkException(f"ERROR: {res['message']}")
    try:
        res = cget('get', f"{file_link}&waitingToken={waiting_token}").json()
        return res['data']['dlLink']
    except Exception as e:
        raise DirectDownloadLinkException(f"ERROR: {e}")


def wetransfer(url):
    cget = create_scraper().request
    try:
        url = cget('GET', url).url
        json_data = {
            'security_hash': url.split('/')[-1],
            'intent': 'entire_transfer'
            }
        res = cget('POST', f'https://wetransfer.com/api/v4/transfers/{url.split("/")[-2]}/download', json=json_data).json()
    except Exception as e:
        raise DirectDownloadLinkException(f'ERROR: {e}')
    if "direct_link" in res:
        return res["direct_link"]
    elif "message" in res:
        raise DirectDownloadLinkException(f"ERROR: {res['message']}")
    elif "error" in res:
        raise DirectDownloadLinkException(f"ERROR: {res['error']}")
    else:
        raise DirectDownloadLinkException("ERROR: Error trying to generate direct link from Wetransfer.")


def yandex_disk(url: str) -> str:
    try:
        link = re_findall(r'\b(https?://(yadi.sk|disk.yandex.com)\S+)', url)[0][0]
    except IndexError:
        return "No Yandex.Disk links found\n"
    api = 'https://cloud-api.yandex.net/v1/disk/public/resources/download?public_key={}'
    cget = create_scraper().request
    try:
        return cget('get', api.format(link)).json()['href']
    except KeyError:
        raise DirectDownloadLinkException("ERROR: File not found/Download limit reached!")
#==============================================================================================================


#================================================= VIDEO HOSTER ===============================================
def get_fembed_links(url):
    cget = create_scraper().request
    url = url.replace("/v/", "/f/")
    raw = cget('get', url)
    api = re_search(r"(/api/source/[^\"']+)", raw.text)
    if api:
        result = {}
        raw = cget('post', "https://layarkacaxxi.icu" + api.group(1)).json()
        for d in raw["data"]:
            f = d["file"]
            head = cget('head', f)
            direct = head.headers.get("Location", f)
            result[f"{d['label']}/{d['type']}"] = direct
        return result


def fembed(url: str) -> str:
    dl_url = get_fembed_links(url)
    try:
        count = len(dl_url)
        lst_link = [dl_url[i] for i in dl_url]
        return lst_link[count-1]
    except Exception as e:
        LOGGER.error(e)
        raise DirectDownloadLinkException(f"ERROR: {e}")


def mp4upload(url: str) -> str:
    cget = create_scraper().request
    try:
        url = url[:-1] if url[-1] == '/' else url
        headers = {'referer':'https://mp4upload.com'}
        token = url.split("/")[-1]
        data = {'op': 'download2','id': token,
				'rand': '','referer': 'https://www.mp4upload.com/',
				'method_free': '','method_premium':''}
        response = cget('post', url, headers=headers, data=data, allow_redirects=False)
        bypassed_json = {}
        bypassed_json["bypassed_url"] = response.headers["Location"]
        bypassed_json["headers "] = headers
        return bypassed_json["bypassed_url"]
    except Exception as e:
        LOGGER.error(e)
        raise DirectDownloadLinkException(f"ERROR: {e}")


def streamlare(url: str)-> str:
    try:
        CONTENT_ID = re_compile(r"/[ve]/([^?#&/]+)")
        API_LINK = "https://sltube.org/api/video/download/get"
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4136.7 Safari/537.36"
        session = create_scraper()
        content_id = CONTENT_ID.search(url).group(1)
        r = session.request('get', url).text
        soup = BeautifulSoup(r, "html.parser")
        csrf_token = soup.find("meta", {"name":"csrf-token"}).get("content")
        xsrf_token =  session.cookies.get_dict()["XSRF-TOKEN"]
        headers={"x-requested-with": "XMLHttpRequest", "x-csrf-token": csrf_token, "x-xsrf-token":xsrf_token, 'referer': url, "user-agent":user_agent}
        payload = {"id": content_id}
        result = session.request('post', API_LINK, headers=headers, data=payload).json()["result"]
        result["headers"] = {"user-agent": user_agent}
        return result["Original"]["url"]
    except Exception as e:
        LOGGER.error(e)
        raise DirectDownloadLinkException(f"ERROR: {e}")


def streamsb(url: str) -> str:
    cget = create_scraper().request
    raw = cget('get', url)
    text = raw.text if hasattr(raw, "text") else raw
    soup = BeautifulSoup(text, "html.parser")
    dl_url = {}
    for a in soup.findAll("a", onclick=re_compile(r"^download_video[^>]+")):
        print(a)
        data = dict(zip(["id", "mode", "hash"], re_findall(r"[\"']([^\"']+)[\"']", a["onclick"])))
        data["op"] = "download_orig"
        raw = cget('get', "https://sbembed.com/dl", params=data)
        text = raw.text if hasattr(raw, "text") else raw
        soup = BeautifulSoup(text, "html.parser")
        if (direct := soup.find("a", text=re_compile("(?i)^direct"))):
            dl_url[a.text] = direct["href"]
    count = len(dl_url)
    lst_link = [dl_url[i] for i in dl_url]
    try:
        return lst_link[count-1]
    except Exception as e:
        raise DirectDownloadLinkException(f"ERROR: {e}")


def streamtape(url):
    cget = create_scraper().request
    raw = cget('get', url)
    if (videolink := re_findall(r"document.*((?=id\=)[^\"']+)", raw.text)):
        nexturl = "https://streamtape.com/get_video?" + videolink[-1]
        head = cget('head', nexturl)
        return head.headers.get("Location", nexturl)
    else:
        raise DirectDownloadLinkException("ERROR: Error trying to generate direct link from Streamtape.")
#==============================================================================================================


#================================================= GDRIVE SHARER ==============================================
def sharerpw(url: str, forced_login=False) -> str:
    SHARERPW_XSRF_TOKEN = config_dict['SHARERPW_XSRF_TOKEN']
    SHARERPW_LARAVEL_SESSION = config_dict['SHARERPW_LARAVEL_SESSION']
    if not SHARERPW_XSRF_TOKEN or not SHARERPW_LARAVEL_SESSION:
        raise DirectDownloadLinkException("ERROR: Sharer Token/Session not provided!")
    try:
        client = create_scraper(allow_brotli=False)
        client.cookies.update({"XSRF-TOKEN": SHARERPW_XSRF_TOKEN, "laravel_session": SHARERPW_LARAVEL_SESSION})
        res = client.get(url)
        token = re_findall("_token\s=\s'(.*?)'", res.text, DOTALL)[0]
        ddl_btn = etree.HTML(res.content).xpath("//button[@id='btndirect']")
        headers = {'content-type': 'application/x-www-form-urlencoded; charset=UTF-8', 'x-requested-with': 'XMLHttpRequest'}
        data = {'_token': token}
        if not forced_login:
            data['nl'] = 1
        try:
            res = client.post(url+'/dl', headers=headers, data=data).json()
            return res['url']
        except:
            if len(ddl_btn) and not forced_login:
                return sharerpw(url, forced_login=True)
            else:
                raise Exception
    except Exception as e:
        raise DirectDownloadLinkException(f"ERROR: {e}")


def gdtot(url: str) -> str:
    CRYPT_GDTOT = config_dict['CRYPT_GDTOT']
    if not CRYPT_GDTOT:
        LOGGER.info("ERROR: CRYPT_GDTOT cookie not provided")
        return gdtot_plus(url)
    match = re_findall(r'https?://(.+)\.gdtot\.(.+)\/\S+\/\S+', url)[0]
    session = create_scraper()
    session.cookies.update({'crypt': CRYPT_GDTOT})
    session.request('get', url)
    res = session.request("get", f"https://{match[0]}.gdtot.{match[1]}/dld?id={url.split('/')[-1]}")
    matches = re_findall('gd=(.*?)&', res.text)
    try:
        decoded_id = b64decode(str(matches[0])).decode('utf-8')
        return f'https://drive.google.com/open?id={decoded_id}'
    except:
        return gdtot_plus(url)


def filepress(url):
    cget = create_scraper().request
    try:
        url = cget('GET', url).url
        raw = urlparse(url)
        json_data = {'id': raw.path.split('/')[-1],
                     'method': 'publicDownlaod'}
        api = f'{raw.scheme}://{raw.hostname}/api/file/downlaod/'
        res = cget('POST', api, headers={'Referer': f'{raw.scheme}://{raw.hostname}'}, json=json_data).json()
    except Exception as e:
        raise DirectDownloadLinkException(f'ERROR: {e}')
    if 'data' not in res:
        raise DirectDownloadLinkException(f'ERROR: {res["statusText"]}')
    return f'https://drive.google.com/uc?id={res["data"]}&export=download'


def gdtot_plus(url):
    cget = create_scraper().request
    try:
        res = cget('GET', f'https://gdtot.pro/file/{url.split("/")[-1]}')
    except Exception as e:
        raise DirectDownloadLinkException(f'ERROR: {e}')
    token_url = etree.HTML(res.content).xpath("//a[contains(@class,'inline-flex items-center justify-center')]/@href")
    if not token_url:
        try:
            url = cget('GET', url).url
            p_url = urlparse(url)
            res = cget("GET",f"{p_url.scheme}://{p_url.hostname}/ddl/{url.split('/')[-1]}")
        except Exception as e:
            raise DirectDownloadLinkException(f'ERROR: {e}')
        if (drive_link := re_findall(r"myDl\('(.*?)'\)", res.text)) and "drive.google.com" in drive_link[0]:
            return drive_link[0]
        else:
            raise DirectDownloadLinkException('ERROR: Drive Link not found, Try in your broswer!')
    token_url = token_url[0]
    try:
        token_page = cget('GET', token_url)
    except Exception as e:
        raise DirectDownloadLinkException(f'ERROR: {e} with {token_url}')
    path = re_findall('\("(.*?)"\)', token_page.text)
    if not path:
        raise DirectDownloadLinkException('ERROR: Cannot bypass this link!')
    path = path[0]
    raw = urlparse(token_url)
    final_url = f'{raw.scheme}://{raw.hostname}{path}'
    return sharer_scraper(final_url)


def sharer_scraper(url):
    cget = create_scraper().request
    try:
        url = cget('GET', url).url
        raw = urlparse(url)
        header = {"useragent": "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US) AppleWebKit/534.10 (KHTML, like Gecko) Chrome/7.0.548.0 Safari/534.10"}
        res = cget('GET', url, headers=header)
    except Exception as e:
        raise DirectDownloadLinkException(f'ERROR: {e}')
    key = re_findall('"key",\s+"(.*?)"', res.text)
    if not key:
        raise DirectDownloadLinkException("ERROR: Key not found!")
    key = key[0]
    if not etree.HTML(res.content).xpath("//button[@id='drc']"):
        raise DirectDownloadLinkException("ERROR: This link don't have direct download button.")
    boundary = uuid4()
    headers = {'Content-Type': f'multipart/form-data; boundary=----WebKitFormBoundary{boundary}',
               'x-token': raw.hostname,
               'useragent': 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US) AppleWebKit/534.10 (KHTML, like Gecko) Chrome/7.0.548.0 Safari/534.10'}
    data = f'------WebKitFormBoundary{boundary}\r\nContent-Disposition: form-data; name="action"\r\n\r\ndirect\r\n' \
        f'------WebKitFormBoundary{boundary}\r\nContent-Disposition: form-data; name="key"\r\n\r\n{key}\r\n' \
        f'------WebKitFormBoundary{boundary}\r\nContent-Disposition: form-data; name="action_token"\r\n\r\n\r\n' \
        f'------WebKitFormBoundary{boundary}--\r\n'
    try:
        res = cget("POST", url, cookies=res.cookies, headers=headers, data=data).json()
    except Exception as e:
        raise DirectDownloadLinkException(f'ERROR: {e}')
    if "url" not in res:
        raise DirectDownloadLinkException('ERROR: Drive Link not found, Try in your broswer!')
    if "drive.google.com" in res["url"]:
        return res["url"]
    try:
        res = cget('GET', res["url"])
    except Exception as e:
        raise DirectDownloadLinkException(f'ERROR: {e}')
    if (drive_link := etree.HTML(res.content).xpath("//a[contains(@class,'btn')]/@href")) and "drive.google.com" in drive_link[0]:
        return drive_link[0]
    else:
        raise DirectDownloadLinkException('ERROR: Drive Link not found, Try in your broswer!')
#==============================================================================================================