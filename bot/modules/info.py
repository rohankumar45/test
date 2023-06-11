from aiofiles.os import path as aiopath
from aiohttp import ClientSession, request as aiorequests
from asyncio import sleep
from bs4 import BeautifulSoup
from json import loads as jsonloads
from pyrogram import enums
from pyrogram.errors import FloodWait
from pyrogram.filters import command, regex
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.types import Message, CallbackQuery, InputMediaPhoto
from random import choice
from re import findall as re_findall
from urllib.parse import quote_plus

from bot import bot, config_dict, LOGGER
from bot.helper.ext_utils.bot_utils import is_media, new_task
from bot.helper.ext_utils.force_mode import ForceMode
from bot.helper.ext_utils.fs_utils import clean_target
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import editPhoto, sendPhoto, deleteMessage, auto_delete_message


info_dict = {}


anime_query = '''
    query ($id: Int,$search: String) {
        Media (id: $id, type: ANIME,search: $search) {
            id
            title {
            romaji
            english
            native
        }
        description (asHtml: false)
        startDate{
            year
        }
        episodes
        season
        type
        format
        status
        duration
        siteUrl
        studios{
            nodes{
                name
            }
        }
        trailer{
            id
            site
            thumbnail
        }
        averageScore
        genres
        bannerImage
    }
}
'''
character_query = '''
    query ($query: String) {
        Character (search: $query) {
            id
            name {
                first
                last
                full
            }
            siteUrl
            image {
                large
            }
            description
    }
}
'''

manga_query = '''
query ($id: Int,$search: String) {
    Media (id: $id, type: MANGA,search: $search) {
        id
        title {
            romaji
            english
            native
        }
        description (asHtml: false)
        startDate{
            year
        }
        type
        format
        status
        siteUrl
        averageScore
        genres
        bannerImage
    }
}
'''

GENRES_EMOJI = {'Action': '👊',
                'Adventure': choice(['🪂', '🧗‍♀', '🌋']),
                'Family': '👨‍',
                'Musical': '🎸',
                'Comedy': '🤣',
                'Drama': ' 🎭',
                'Ecchi': choice(['💋', '🥵']),
                'Fantasy': choice(['🧞', '🧞‍♂', '🧞‍♀', '🌗']),
                'Hentai': '🔞',
                'History': '📜',
                'Horror': '☠',
                'Mahou Shoujo': '☯',
                'Mecha': '🤖',
                'Music': '🎸',
                'Mystery': '🔮',
                'Psychological': '♟',
                'Romance': '💞',
                'Sci-Fi': '🛸',
                'Slice of Life': choice(['☘', '🍁']),
                'Sports': '⚽️',
                'Supernatural': '🫧',
                'Thriller': choice(['🥶', '🔪', '🤯'])}


async def anim_content(template, variables):
    async with ClientSession() as session:
        async with session.post('https://graphql.anilist.co', json={'query': template, 'variables': variables}) as r:
            return (await r.json())['data']


async def get_content(url, is_json=True):
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_5) AppleWebKit/600.1.17 (KHTML, like Gecko) Version/7.1 Safari/537.85.10"}
    async with aiorequests('GET', url, headers=headers) as res:
        return await res.json() if is_json else await res.text()


def list_to_str(data, limit=None):
    if len(data) == 0:
        return 'N/A'
    elif len(data) == 1:
        return data[0]
    elif limit:
        return ', '.join(x for x in data[:limit])
    else:
        return ', '.join(x for x in data)


def shorten(description, info = 'anilist.co'):
    msg = ""
    if len(description) > 700:
        description = description[0:500] + '...'
        msg += f"**Description**: __{description}__[Read More]({info})"
    else:
        msg += f"\n**Description**: __{description}__"
    return msg


async def editAnime(caption: str, message: Message, photo: str, reply_markup=None):
    try:
        return await bot.edit_message_media(message.chat.id, message.id,
                                            media=InputMediaPhoto(photo,caption, parse_mode=enums.ParseMode.MARKDOWN),
                                            reply_markup=reply_markup)
    except FloodWait as f:
        LOGGER.warning(str(f))
        await sleep(f.value ** 1.5)
        return await editAnime(caption, message, photo, reply_markup)
    except Exception as err:
        LOGGER.error(err)
        return str(err)


async def get_data(from_user, mid: int, data=None, movid=None):
    image = config_dict['IMAGE_INFO']
    buttons = ButtonMaker()
    title = info_dict[mid]['title']
    animention = f'[{from_user.first_name}](tg://user?id={from_user.id})'
    if not data or data == 'back':
        buttons.button_data('Anime', f'info|{from_user.id}|anime|{mid}')
        buttons.button_data('Manga', f'info|{from_user.id}|manga|{mid}')
        buttons.button_data('Character', f'info|{from_user.id}|char|{mid}')
        buttons.button_data('IMDb', f'info|{from_user.id}|imdb|{mid}')
        buttons.button_data('MyDrama', f'info|{from_user.id}|mdl|{mid}')
        buttons.button_data('User Info', f'info|{from_user.id}|user|{mid}')
        text = f'{from_user.mention}, Choose Available Options Below!'
        if title:
            text += f'<b>Query:</b> {title.title()}'

    elif data == 'anime':
        json = (await anim_content(anime_query, {'search' : title})).get('Media')
        text = f'Not found Anime for **{title.title()}**.'
        if json:
            text = f'**ANIME RESULT** ~ {animention}\n\n'
            text += f"**{json['title']['romaji']}** "
            if native := json.get('title', {}).get('native'):
                text += f'(`{native}`)\n'
            else:
                text += '\n'
            text += f"**Type:**  `{json['format']}`\n"
            text += f"**Status:** `{json['status']}`\n"
            text += f"**Episodes:** `{json.get('episodes', 'N/A')}`\n"
            text += f"**Duration:** `{json.get('duration', 'N/A')}`\n"
            text += f"**Score:** `{json['averageScore']}`\n"
            text += "**Genres:** " + ', '.join(f'`{x}`' for x in json['genres']) + '\n'
            text += "**Studios:** " + ", ".join(f"`{x['name']}`" for x in json['studios']['nodes']) + '\n'
            trailer = json.get('trailer')
            if trailer and trailer.get('site') == "youtube":
                trailer = f"https://youtu.be/{trailer.get('id')}"
            description = json.get('description', 'N/A').replace('<i>', '').replace('</i>', '').replace('<br>', '')
            text += shorten(description, json.get('siteUrl'))
            if trailer:
                buttons.button_link("Trailer", trailer)
            buttons.button_link("More Info", json.get('siteUrl'))
            if json.get('bannerImage'):
                image = json['bannerImage']

    elif data == 'manga':
        text = f'Not found Manga for **{title.title()}**.'
        json = (await anim_content(manga_query, {'search': title})).get('Media')
        if json:
            text = f'**MANGA RESULT** ~ {animention}\n\n'
            if name := json.get('title', {}).get('romaji'):
                text += f"**{name}** "
            if native := json.get('title', {}).get('native'):
                text += f"(`{native}`)"
            if start_date := json.get('startDate', {}).get('year'):
                text += f"\n**Start Date**: `{start_date}`"
            if status:= json.get('status'):
                text += f"\n**Status**: `{status}`"
            if score:= json.get('averageScore'):
                text += f"\n**Score**: `{score}`"
            text += '\n**Genres**: ' + ', '.join(f'`{x}`' for x in json.get('genres', [])) + '\n'
            text += f"__{json.get('description').replace('<br><br>', '')}__"
            image = json["bannerImage"] if json.get("bannerImage") else config_dict['IMAGE_UNKNOW']

    elif data == 'char':
        json = (await anim_content(character_query, {'query': title})).get('Character')
        text = f'Not found Character for **{title.title()}**.'
        if json:
            text = f'**CHARACTER RESULT** ~ {animention}\n\n'
            text += f"**{json.get('name').get('full')}**"
            if native := json.get('name').get('native'):
                text += f'(`{native})`\n'
            else :
                text += '\n'
            description = f"{json['description']}"
            text += shorten(description, json.get('siteUrl'))
            buttons.button_link("More info", json.get('siteUrl'))
            image = json['image']['large'] if json.get('image', {}).get('large') else config_dict['IMAGE_UNKNOW']

    elif data == 'imdb':
        image = config_dict['IMAGE_IMDB']
        try:
            result = (await get_content(f'https://v3.sg.media-imdb.com/suggestion/titles/x/{quote_plus(title)}.json')).get('d')
            if not result:
                text = f'Not Found Result(s) For <b>{title.upper()}</b>'
            else:
                text = ''
                for count, movie in enumerate(result, start=1):
                    mname = movie.get("l")
                    year = f"({movie['y']})" if movie.get('y') else 'N/A'
                    typee = movie.get('q', 'N/A').replace('feature', 'movie').capitalize()
                    movieid = re_findall(r'tt(\d+)', movie.get('id'))[0]
                    text += f'{count}. <b>{mname} {year} ~ {typee}</b>\n'
                    buttons.button_data(count, f'info|{from_user.id}|imdbdata|{movieid}|{mid}')
                text = f'Found {len(result)} Result(s) For <b>{title.upper()} ~ {from_user.mention}\n\n{text}</b>'
        except Exception as err:
            LOGGER.error(err)
            text = f'{from_user.mention}, ERROR: {err}'

    elif data == 'imdbdata':
        try:
            url = f'https://www.imdb.com/title/tt{movid}/'
            res = await get_content(url, False)
            sop = BeautifulSoup(res, 'lxml')
            imdata = jsonloads(sop.find('script', attrs={'type': 'application/ld+json'}).contents[0])
            text = f'<b>IMDb RESULT</b> ~ {from_user.mention}\n\n'
            typee = f"~ {imdata['@type']}" if imdata.get('@type') else ''
            class_ = 'ipc-metadata-list-item__list-content-item ipc-metadata-list-item__list-content-item--link'
            tahun = re_findall('\d{4}', sop.title.text)[0] if re_findall('\d{4}', sop.title.text) else 'N/A'
            text += f"<a href='{url}'><b>{imdata['name']} ({tahun})</b></a> <b>{typee}</b>\n"
            text += f"<b>AKA:</b> <code>{imdata.get('alternateName')}</code>\n\n" if imdata.get('alternateName') else '\n'
            if duration := sop.select('li[data-testid="title-techspec_runtime"]'):
                text += f"<b>Duration:</b> <code>{duration[0].find(class_='ipc-metadata-list-item__content-container').text}</code>\n"
            if contenrating := imdata.get('contentRating'):
                text += f'<b>Catrgory:</b> <code>{contenrating}</code>\n'
            if agreerating := imdata.get('aggregateRating'):
                text += f"<b>Rating:</b> ⭐️ <code>{agreerating['ratingValue']}</code> ~ <code>{agreerating['ratingCount']}</code> Vote\n"
            if releases := sop.select('li[data-testid="title-details-releasedate"]'):
                text += f"<b>Release:</b> <a href='https://www.imdb.com{releases[0].find(class_=class_)['href']}'>{releases[0].find(class_=class_).text}</a>\n"
            if genre := imdata.get('genre'):
                text += '<b>Genre:</b> ' + ', '.join(f"{GENRES_EMOJI[i]} #{i.replace('-', '_').replace(' ', '_')}" if i in GENRES_EMOJI else f"#{i.replace('-', '_').replace(' ', '_')}" for i in genre) + '\n'
            if scount := sop.select('li[data-testid="title-details-origin"]'):
                text += f'<b>Country:</b> ' +  ', '.join(f'#{x.text}'.replace(' ', '').replace('-', '') for x in scount[0].findAll(class_=class_)) + '\n'
            if languages := sop.select('li[data-testid="title-details-languages"]'):
                text += f'<b>Language:</b> ' + ', '.join(f'#{lang.text}'.replace(' ', '_').replace('-', '_') for lang in languages[0].findAll(class_=class_)) + '\n'
            if directors := imdata.get('director'):
                text += f"\n<b>Cast Info</b>\n"
                text += '<b>Director:</b> ' + ', '.join(f"<a href='https://www.imdb.com{x['url']}'>{x['name']}</a>" for x in directors) + '\n'
            if creators := imdata.get('creator'):
                text += '<b>Writter:</b> ' + ', '.join(f"<a href='https://www.imdb.com{x['url']}'>{x['name']}</a>" for x in creators if x['@type'] == 'Person') + '\n'
            if actors := imdata.get('actor'):
                text += '<b>Starts:</b> ' + ', '.join(f"<a href='https://www.imdb.com{x['url']}'>{x['name']}</a>" for x in actors) + '\n'
            if awards := sop.select('li[data-testid="award_information"]'):
                text += f"<b>Awards:</b> <code>{awards[0].find(class_='ipc-metadata-list-item__list-content-item').text.title()}</code>\n\n"
            else:
                text += '\n'
            if keywords := imdata.get('keywords'):
                text += '<b>Keywords</b>\n' + ', '.join(f'#{x}'.replace(' ', '_').replace('-', '_') for x in keywords.split(',')) + '\n\n'
            if descriptions := imdata.get('description'):
                text += f'<b>SUMMARY</b>\n{descriptions}\n\n'
            if trailer := imdata.get('trailer'):
                buttons.button_link('Open IMDb', f"https://www.imdb.com{imdata['url']}")
                buttons.button_link('Trailer', trailer['url'])
            else:
                buttons.button_link('Open IMDb', f"https://www.imdb.com{imdata['url']}")
            text = text.replace('&apos;', '\'')
            image = imdata['image'] if imdata.get('image') else config_dict['IMAGE_UNKNOW']
        except Exception as err:
            LOGGER.error(err)
            text = f'ERROR: {err}'
        buttons.button_data('<<', f'info|{from_user.id}|imdb|{mid}')

    elif data == 'mdl':
        url = f'https://kuryana.vercel.app/search/q/{title}'
        json = (await get_content(url))['results']['dramas']
        text = f'Not found result for <b>{title.title()}</b> in MyDramalist database.'
        if json:
            text = f'<b>MYDRAMALIST RESULT</b> ~ {from_user.mention}\n\n'
            for index, movie in enumerate(json, start=1):
                slugid, slugtitle = movie['slug'].split('-', maxsplit=1)
                info_dict[mid][slugid] = slugtitle
                text += f"{index}. <b>{movie.get('title')} ~ ({movie.get('year')})</b>\n"
                buttons.button_data(index, f"info|{from_user.id}|mdldata|{slugid}|{mid}")

    elif data == 'mdldata':
        try:
            text = f'<b>MYDRAMALIST RESULT</b> ~ {from_user.mention}\n\n'
            res = await get_content(f"https://kuryana.vercel.app/id/{movid}-{info_dict[mid][movid]}")
            text += f"<b>{res['data']['title'].title()}</b>\n"
            text += f"<b>AKA:</b> <code>{list_to_str(res['data']['others']['also_known_as'])}</code>\n\n"
            text += f"<b>Rating:</b> <code>{res['data']['details']['score']}</code>\n"
            text += f"<b>Content:</b> <code>{res['data']['details']['content_rating']}</code>\n"
            text += f"<b>Type:</b> <code>{res['data']['details']['type']}</code>\n"
            text += f"<b>Country:</b> <code>{res['data']['details']['country']}</code>\n"
            if res["data"]["details"]["type"] == "Movie":
                text += f"<b>Release Date:</b> <code>{res['data']['details']['release_date']}</code>\n"
            elif res["data"]["details"]["type"] == "Drama":
                text += f"<b>Episode:</b> <code>{res['data']['details']['episodes']}</code>\n"
                text += f"<b>Aired:</b> <code>{res['data']['details']['aired']}</code>\n"
                try: text += f"<b>Aired on:</b> <code>{res['data']['details']['aired_on']}</code>\n"
                except: pass
                try: text += f"<b>Original Network:</b> <code>{res['data']['details']['original_network']}</code>\n"
                except: pass
            if duration := res.get('data', {}).get('details', {}).get('duration'):
                text += f"<b>Duration:</b> <code>{duration}</code>\n"
            text += f"<b>Genre:</b> <code>{list_to_str(res['data']['others']['genres'])}</code>\n"
            text += f"<b>Tags:</b> {list_to_str(res['data']['others']['tags'], 10)}\n\n"
            synopsis = f"{res['data']['synopsis'][:700]}..." if len(res['data']['synopsis']) > 700 else res['data']['synopsis']
            text += f"<b>SYNOPSIS</b>\n{synopsis}"
            text = f'{text[:1200]}...' if len(text) > 1200 else text
            if img := res.get('data', {}).get('poster'):
                index = img.index('https')
                image = img[index:]
            else:
                image = config_dict['IMAGE_UNKNOW']
            buttons.button_link('Open MyDramaList', res["data"]["link"])
        except Exception as err:
            LOGGER.error(err)
            text = str(err)
        buttons.button_data('<<', f"info|{from_user.id}|mdl|{mid}")

    elif data == 'user':
        user = await bot.get_users(movid)
        try:
            image = await bot.download_media(user.photo.big_file_id, file_name=f'./{user.id}.png')
        except:
            image = config_dict['IMAGE_UNKNOW']
        try:
            user_member = await bot.get_chat_member(info_dict[mid]['chatid'], movid)
            user_member = f'<b>├ Status:</b> {user_member.status.name.title()}\n'
            user_member += f'<b>├ Joined:</b> {user_member.joined_date or "~"}\n'
        except:
            user_member = ''
        text = '<b>USER INFO</b>\n'
        text += f'<b>┌ ID:</b> <code>{user.id}</code>\n'
        text += f'<b>├ First Name:</b> {user.first_name}\n'
        text += f'<b>├ Last Name:</b> {user.last_name or "~"}\n'
        text += f'<b>├ Username:</b> {"@" + user.username or "~"}\n'
        text += f'<b>├ Language:</b> {user.language_code.upper() if user.language_code else "~"}\n'
        text += user_member
        text += f'<b>├ Premium User:</b> {"Yes" if user.is_premium else "No"}\n'
        text += f'<b>└ DC ID:</b> {user.dc_id or "~"}'
        if user.username:
            buttons.button_link('Details', f'https://t.me/{user.username}')

    position = 'footer' if data in ['imdb', 'mdl'] else None
    if data and data not in ['back', 'mdldata', 'imdbdata']:
        buttons.button_data("<<", f'info|{from_user.id}|back|{mid}', position)
    buttons.button_data("Close", f'info|{from_user.id}|close|{mid}', position)
    return text, image, buttons.build_menu(4) if data in ['imdb', 'mdl'] else buttons.build_menu(2)


async def update_data(query: CallbackQuery, mid: int, data=None, movid=None):
    text, image, buttons = await get_data(query.from_user, mid, data, movid)
    editData = editAnime if data in ['anime', 'manga', 'char'] else editPhoto
    await editData(text, query.message, image, buttons)
    if await aiopath.isfile(image):
        await clean_target(image)


@new_task
async def search_info(_, message: Message):
    reply_to = message.reply_to_message
    args = message.text.split(maxsplit=1)

    if fmsg:= await ForceMode(message).run_force('fsub', 'funame'):
        await auto_delete_message(message, fmsg, reply_to)
        return

    if reply_to and is_media(reply_to) or not reply_to and len(args) == 1:
        query = ''
    elif reply_to :
        query = reply_to.text.strip()
    else:
        query = args[1].strip()
    info_dict[message.id] = {'title': query,
                             'chatid': message.chat.id,
                             'repuid': reply_to.from_user.id if reply_to else None,
                             'repmsg': reply_to}
    text, image, buttons = await get_data(message.from_user, message.id)
    await sendPhoto(text, message, image, buttons)


@new_task
async def query_info(_, query: CallbackQuery):
    message = query.message
    user_id = query.from_user.id
    data = query.data.split('|')
    generate_data = ['anime', 'manga', 'char', 'imdb', 'mdl']
    omsg = message.reply_to_message
    try:
        mid = omsg.message_id
    except:
        try:
            mid = int(data[-1])
        except:
            pass
    info = info_dict.get(mid)
    if not info and data[2] != 'close':
        await query.answer('Old task!', show_alert=True)
        return
    if int(data[1]) != user_id:
        await query.answer('Not Yours!', show_alert=True)
    elif data[2] in generate_data:
        if info['title'] == '':
            await query.answer('Upss, give a query to continue!', show_alert=True)
            return
        await query.answer()
        await editPhoto('<i>Generating data, please wait...</i>', message, config_dict['IMAGE_INFO'])
        await update_data(query, mid, data[2])
    elif data[2] == 'back':
        await query.answer()
        await update_data(query, mid, data[2])
    elif data[2] =='user':
        await query.answer()
        await editPhoto('<i>Getting data, please wait...</i>', message, config_dict['IMAGE_INFO'])
        uid = info_dict[mid]['repuid'] if info_dict[mid]['repuid'] else user_id
        await update_data(query, mid, data[2], uid)
    elif data[2] in ['mdldata', 'imdbdata']:
        await query.answer()
        site = 'MyDramalist' if data[2] == 'mdldata' else 'IMDb'
        await editPhoto(f'<i>Generating data from <b>{site}</b>, please wait...</i>', message, config_dict['IMAGE_INFO'])
        await update_data(query, mid, data[2], data[3])
    else:
        await query.answer()
        repmsg = None
        if info:
            repmsg = info.get('repmsg')
            del info_dict[mid]
        await deleteMessage(message, omsg, repmsg)


bot.add_handler(MessageHandler(search_info, filters=command(BotCommands.InfoCommand) & CustomFilters.authorized))
bot.add_handler(CallbackQueryHandler(query_info, filters=regex('^info')))