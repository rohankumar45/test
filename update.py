from dotenv import load_dotenv, dotenv_values
from logging import FileHandler, StreamHandler, basicConfig, error as log_error, info as log_info, INFO
from os import path as ospath, environ, remove
from pymongo import MongoClient
from subprocess import run as srun

if ospath.exists('log.txt'):
    with open('log.txt', 'r+') as f:
        f.truncate(0)

if ospath.exists('rlog.txt'):
    remove('rlog.txt')

basicConfig(format='%(asctime)s: [%(levelname)s: %(filename)s - %(lineno)d] ~ %(message)s',
            handlers=[FileHandler('log.txt'), StreamHandler()],
            datefmt='%d-%b-%y %I:%M:%S %p',
            level=INFO)

load_dotenv('config.env', override=True)

BOT_TOKEN = environ.get('BOT_TOKEN', '')
if not BOT_TOKEN:
    log_error('BOT_TOKEN variable is missing! Exiting now')
    exit(1)

bot_id = BOT_TOKEN.split(':', 1)[0]

DATABASE_URL = environ.get('DATABASE_URL', '')

if DATABASE_URL:
    conn = MongoClient(DATABASE_URL)
    db = conn.mltb
    old_config = db.settings.deployConfig.find_one({'_id': bot_id})
    config_dict = db.settings.config.find_one({'_id': bot_id})
    if old_config:
        del old_config['_id']
    if (old_config and old_config == dict(dotenv_values('config.env')) or not old_config) and config_dict:
        environ['UPSTREAM_REPO'] = config_dict.get('UPSTREAM_REPO')
        environ['UPSTREAM_BRANCH'] = config_dict.get('UPSTREAM_BRANCH')
        environ['UPDATE_EVERYTHING'] = str(config_dict.get('UPDATE_EVERYTHING'))
    conn.close()

if environ.get('UPDATE_EVERYTHING', 'False').lower() == 'true':
    srun(['pip3', 'install', '-U', '--no-cache-dir', '-r', 'requirements.txt'])

UPSTREAM_REPO = environ.get('UPSTREAM_REPO', '')
UPSTREAM_BRANCH = environ.get('UPSTREAM_BRANCH', '')

if UPSTREAM_REPO:
    if ospath.exists('.git'):
        srun(['rm', '-rf', '.git'])
    update = srun([f'git init -q \
                     && git config --global user.email trollgithub@gmail.com \
                     && git config --global user.name mltb \
                     && git add . \
                     && git commit -sm update -q \
                     && git remote add origin {UPSTREAM_REPO} \
                     && git fetch origin -q \
                     && git reset --hard origin/{UPSTREAM_BRANCH} -q'], shell=True)

    if update.returncode == 0:
        log_info(f'Successfully updated with latest commit from UPSTREAM_REPO ~ {UPSTREAM_BRANCH.upper()} Branch.')
    else:
        log_error('Something went wrong while updating, check UPSTREAM_REPO if valid or not!')