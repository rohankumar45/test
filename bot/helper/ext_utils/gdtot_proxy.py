from aiohttp import ClientSession
from bs4 import BeautifulSoup
from re import compile as re_compile
from urllib.parse import urlparse, quote_plus


async def search_gdtot(query):
    async with ClientSession() as session:
        async with session.get(f'https://gdbot.xyz/search?q={quote_plus(query)}') as r:
            soup = BeautifulSoup(await r.read(), 'html.parser')
            links = soup.select("a[href*='https://gdbot.xyz/file']")
            info = [x.string for x in soup.find_all('span', string=re_compile(r'Size*'))]
            titles = [x.string for x in soup.find_all('a')[5:]]
            text, result = '', []
            for i, (title, inf, link) in enumerate(zip(titles, info, links), start=1):
                async with session.get(link['href']) as r:
                    soup = BeautifulSoup(await r.read(), 'html.parser')
                    text += f"{str(i).zfill(3)}. <a href='{link['href']}'>{str(title).strip()}</a>\n{inf}\n"
                    for x in soup.select('a'):
                        link = x['href']
                        if 'gdbot.xyz' not in link:
                            text += f"<a href='{link}'><b>{str(urlparse(link).hostname).upper()}</b></a> "
                    text += '\n\n'
                result.append(text)
                text = ''
        return result