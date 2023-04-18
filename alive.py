from logging import error as logerror, info as loginfo
from os import environ
from requests import get as rget
from time import sleep


BASE_URL = environ.get('BASE_URL', '') or environ.get('RCLONE_SERVE_URL', '')
BASE_URL = BASE_URL.rstrip('/') if BASE_URL else ''
if BASE_URL:
    while True:
        loginfo('Alive.py has been started...')
        try:
            rget(BASE_URL).status_code
            sleep(600)
        except Exception as e:
            logerror(f'alive.py: {e}')
            sleep(2)
            continue