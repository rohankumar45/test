import heroku3

from aiohttp import ClientSession
from random import choice

from bot import config_dict, LOGGER
from bot.helper.ext_utils.bot_utils import get_readable_time


async def getHerokuDetails():
    HAPI, HNAME = config_dict['HEROKU_API_KEY'], config_dict['HEROKU_APP_NAME']
    if HAPI and HNAME:
        try:
            heroku_api = 'https://api.heroku.com'
            Heroku = heroku3.from_key(HAPI)
            app = Heroku.app(HNAME)
            useragent = ('Mozilla/5.0 (Linux; Android 10; SM-G975F) ', 'AppleWebKit/537.36 (KHTML, like Gecko) ', 'Chrome/81.0.4044.117 Mobile Safari/537.36')
            user_id = Heroku.account().id
            headers = {'User-Agent': choice(useragent),
                    'Authorization': f'Bearer {HAPI}',
                    'Accept': 'application/vnd.heroku+json; version=3.account-quotas'}
            path = f'/accounts/{user_id}/actions/get-quota'
            async with ClientSession() as session:
                async with session.get(heroku_api + path, headers=headers) as resp:
                    result = await resp.json()
            account_quota = result['account_quota']
            quota_used = result['quota_used']
            quota_remain = account_quota - quota_used
            other_app_usage = 0
            stats = '<b>HEROKU STATUS</b>\n'
            stats += f'<b>┌ Full: </b>{get_readable_time(account_quota) or "~"}\n'
            stats += f'<b>├ Used: </b>{get_readable_time(quota_used) or "~"}\n'
            stats += f'<b>├ Free: </b>{get_readable_time(quota_remain) or "~"}\n'
            for apps in result['apps']:
                other_app_usage += int(apps.get('quota_used', 0))
            stats += f'<b>├ This App: </b>{str(app.name)}'
            stats += f'\n<b>└ Other Usage: </b>{get_readable_time(other_app_usage) or "~"}'
            return stats
        except Exception as e:
            LOGGER.error(e)
