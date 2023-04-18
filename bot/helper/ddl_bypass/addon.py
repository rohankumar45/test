from base64 import b64decode
from cloudscraper import create_scraper
from re import findall as re_findall

class SiteList():
    def __init__(self):
        self.__load_site_list()

    @property
    def fembed_list(self):
        return self.__fmed_list

    @property
    def sbembed_list(self):
        return self.__sbem_list

    @property
    def shortest_list(self):
        return self.__shortest_list

    @property
    def gd_sharer(self):
        return self.__gd_sharer

    @property
    def passvip_list(self):
        return self.__passvip_list

    @property
    def anon_site(self):
        return self.__anon_site

    @property
    def ddl_list(self):
        return tuple(sorted(self.__anon_site + self.__files_hoster + self.__videos_hoster + self.__fmed_list + self.__sbem_list + self.__gd_sharer))

    @property
    def bypass_list(self):
        return tuple(sorted(self.__bypass_sites + self.__passvip_list + self.__shortest_list + self.aio_bypass_list))

    @property
    def aio_bypass_list(self):
        aio_one, aio_two = self.aio_bypass_dict()
        return tuple(aio_one.keys()) + tuple(aio_two.keys())

    def __load_site_list(self):
        self.__anon_site = ('anonfiles.com', 'hotfile.io', 'bayfiles.com', 'megaupload.nz', 'letsupload.cc', 'filechan.org',
                            'myfile.is', 'vshare.is', 'rapidshare.nu', 'lolabits.se', 'openload.cc', 'share-online.is', 'upvid.cc')
        self.__files_hoster = ('1fichier.com', 'antfiles.com', 'github.com', 'gofile.io', 'hxfile.co', 'krakenfiles.com', 'letsupload.io', 'mdisk.me',
                               'mediafire.com', 'onedrive.com','osdn.net', 'pixeldrain.com', 'racaty.net', 'romsget.io', 'send.cm', 'sfile.mobi',
                               'solidfiles.com', 'sourceforge.net', 'uploadbaz.me', 'upload.ee', 'uploadhaven.com','uppit.com', 'uptobox.com',
                               'userscloud.com', 'wetransfer.com', 'yandex.com', 'zippyshare.com', 'racaty.io')
        self.__videos_hoster = ('mp4upload.com', 'streamlare.com', 'streamtape.com')
        self.__gd_sharer = ('appdrive', 'gdtot', 'gdflix', 'sharer')
        self.__fmed_list = ('fembed.net', 'fembed.com', 'femax20.com', 'fcdn.stream', 'feurl.com', 'layarkacaxxi.icu', 'naniplay.nanime.in', 'naniplay.nanime.biz',
                            'naniplay.com', 'mm9842.com', 'javcl.me', 'asianclub.tv', 'javhdfree.icu', 'sexhd.co', 'vanfem.com')
        self.__sbem_list = ('sbembed.com', 'sbembed1.com', 'sbplay.org', 'sbvideo.net', 'streamsb.net', 'sbplay.one', 'cloudemb.com', 'playersb.com', 'tubesb.com',
                            'sbplay1.com', 'embedsb.com', 'watchsb.com', 'sbplay2.com', 'japopav.tv', 'viewsb.com', 'sbplay2.xyz', 'sbfast.com', 'sbfull.com',
                            'javplaya.com', 'sbanh.com')
        self.__bypass_sites = ('adf.ly', 'droplink.co', 'filecrypt.co', 'gplinks.co', 'gtlinks.me', 'theforyou.in', 'kinemaster.cc', 'hypershort.com', 'ouo.io',
                               'rocklinks.net', 'shortly.xyz', 'sirigan.my.id', 'thinfi.com', 'tinyurl.com', 'try2link.com','shortingly.me', 'psa.pm', 'pkin.me',
                               'flashlink.in', 'bluemediafile.site', 'tnlink.in', 'urlsopen.com', 'short2url.in', 'linkvertise.com', 'mdiskshortners.in', 'tinyfy.in',
                               'earnl.xyz', 'earn.moneykamalo.com', 'indiurl.in', 'linkbnao.co', 'mdisk.pro', 'rslinks.net', 'bit.ly')
        self.__passvip_list = ('boost.ink', 'exe.io', 'exey.io', 'goo.gl', 'mboost.me', 'ph.apps2app.com', 'rekonise.com', 'shrto.ml',
                               'shortconnect.com', 'social-unlock.com', 'sub2unlock.com', 'sub2unlock.net', 'sub4unlock.com', 't.co', 'ytsubme.com')
        self.__shortest_list = ('shorte.st', 'festyy.com', 'cllkme.com', 'estyy.com', 'gestyy.com', 'corneey.com', 'destyy.com', 'ceesty.com')

    @staticmethod
    def aio_bypass_dict():
        shortner_dict_one = {'tekcrypt.in': ['https://tekcrypt.in/tek/', 20],
                             'go.rocklinks.net': ['https://dwnld.povathemes.com/', 10],
                             'rocklinks.net': ['https://dwnld.povathemes.com/', 10],
                             'm.easysky.in': ['https://techy.veganab.co/', 5],
                             'indianshortner.in': ['https://indianshortner.com/', 5],
                             'open.crazyblog.in': ['https://hr.vikashmewada.com/', 7],
                             'link.tnvalue.in': ['https://internet.webhostingtips.club/', 5],
                             'shortingly.me': ['https://go.techyjeeshan.xyz/', 5],
                             'dulink.in': ['https://tekcrypt.in/tek/', 20],
                             'bindaaslinks.com': ['https://www.techishant.in/blog/', 5],
                             'pdiskshortener.com': ['https://pdiskshortener.com/', 10],
                             'mdiskshortner.link': ['https://mdiskshortner.link/', 15],
                             'g.rewayatcafe.com': ['https://course.rewayatcafe.com/', 7],
                             'ser2.crazyblog.in': ['https://ser3.crazyblog.in/', 12],
                             'za.uy' : ['https://za.uy/', 5],
                             'bitshorten.com': ['https://bitshorten.com/', 21],
                             'rocklink.in': ['https://rocklink.in/', 6]}
        shortner_dict_two =  {'ez4short.com':['https://ez4short.com/', 'https://techmody.io/', 5],
                              'xpshort.com': ['https://push.bdnewsx.com/', 'https://veganho.co/', 10],
                              'vearnl.in': ['https://go.urlearn.xyz/', 'https://v.modmakers.xyz/', 5],
                              'adrinolinks.in': ['https://adrinolinks.in/', 'https://wikitraveltips.com/', 5],
                              'techymozo.com': ['https://push.bdnewsx.com/', 'https://veganho.co/', 8],
                              'linksxyz.in': ['https://blogshangrila.com/insurance/', 'https://cypherroot.com/', 13],
                              'short-jambo.com' :['https://short-jambo.com/', 'https://aghtas.com/how-to-create-a-forex-trading-plan/', 10],
                              'linkpays.in': ['https://m.techpoints.xyz//', 'https://www.filmypoints.in/', 10],
                              'pi-l.ink' : ['https://go.pilinks.net/', 'https://poketoonworld.com/', 5],
                              'arn4link.in': ['https://m.open2get.in/','https://ezeviral.com/2022/03/01/why-is-cloud-hosting-the-ideal-solution/', 3],
                              'open2get.in': ['https://m.open2get.in/', 'https://ezeviral.com/2022/03/01/why-is-cloud-hosting-the-ideal-solution/', 3]}
        return shortner_dict_one, shortner_dict_two


def decrypt_url(code) -> str:
    '''Bitly Decrypter Function'''
    a, b = '', ''
    for i in range(0, len(code)):
        if i % 2 == 0: a += code[i]
        else: b = code[i] + b
    key = list(a + b)
    i = 0
    while i < len(key):
        if key[i].isdigit():
            for j in range(i+1,len(key)):
                if key[j].isdigit():
                    u = int(key[i]) ^ int(key[j])
                    if u < 10: key[i] = str(u)
                    i = j
                    break
        i += 1
    key = ''.join(key)
    return b64decode(key)[16:-16].decode('utf-8')


def RecaptchaV3(anchor_url: str):
    url_base = 'https://www.google.com/recaptcha/'
    post_data = "v={}&reason=q&c={}&k={}&co={}"
    client = create_scraper()
    client.headers.update({'content-type': 'application/x-www-form-urlencoded'})
    matches = re_findall('([api2|enterprise]+)\/anchor\?(.*)', anchor_url)[0]
    url_base += matches[0] + '/'
    params = matches[1]
    res = client.get(url_base + 'anchor', params=params)
    token = re_findall(r'"recaptcha-token" value="(.*?)"', res.text)[0]
    params = dict(pair.split('=') for pair in params.split('&'))
    post_data = post_data.format(params["v"], token, params["k"], params["co"])
    res = client.post(url_base+'reload', params=f'k={params["k"]}', data=post_data)
    return re_findall(r'"rresp","(.*?)"', res.text)[0]


def getlinks(dlc):
    '''Filecrypt Decrypter Function'''
    client = create_scraper(allow_brotli=False)
    headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:103.0) Gecko/20100101 Firefox/103.0',
               'Accept': 'application/json, text/javascript, */*',
               'Accept-Language': 'en-US,en;q=0.5',
               'X-Requested-With': 'XMLHttpRequest',
               'Origin': 'http://dcrypt.it',
               'Connection': 'keep-alive',
               'Referer': 'http://dcrypt.it/'}
    data = {'content': dlc}
    return client.post('http://dcrypt.it/decrypt/paste', headers=headers, data=data).json()['success']['links']