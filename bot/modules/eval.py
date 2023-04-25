from aiofiles import open as aiopen
from contextlib import redirect_stdout
from io import StringIO
from os import path as ospath, getcwd, chdir
from pyrogram import Client
from pyrogram.filters import command
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message
from textwrap import indent
from traceback import format_exc

from bot import bot, config_dict, LOGGER
from bot.helper.ext_utils.bot_utils import sync_to_async, new_task
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage, auto_delete_message, sendFile

namespaces = {}

def namespace_of(message: Message):
    if message.chat.id not in namespaces:
        namespaces[message.chat.id] = {'__builtins__': globals()['__builtins__'],
                                       'bot': bot,
                                       'message': message,
                                       'user': message.from_user or message.sender_chat,
                                       'chat': message.chat}
    return namespaces[message.chat.id]


def log_input(message: Message):
    LOGGER.info(f'IN: {message.text} (user={message.from_user.id}, chat={message.chat.id})')


async def send(msg, message):
    if len(str(msg)) > 2000:
        async with aiopen('output.txt', 'w', encoding='utf-8') as f:
            await f.write(msg)
        await sendFile(message, 'output.txt', 'Eval output', config_dict['IMAGE_TXT'])
    else:
        LOGGER.info(f"OUT: '{msg}'")
        await sendMessage(f'<code>{msg}</code>', message)


@new_task
async def evaluate(client: Client, message: Message):
    if len(message.text.split()) == 1:
        await sendMessage('No command given to execute!', message)
        return
    await send(await sync_to_async(do, eval, message), message)


@new_task
async def execute(client: Client, message: Message):
    if len(message.text.split()) == 1:
        await sendMessage('No command given to execute!', message)
        return
    await send(await sync_to_async(do, exec, message), message)


def cleanup_code(code):
    if code.startswith('```') and code.endswith('```'):
        return '\n'.join(code.split('\n')[1:-1])
    return code.strip('` \n')


def do(func, message: Message):
    log_input(message)
    content = message.text.split(maxsplit=1)[-1]
    body = cleanup_code(content)
    env = namespace_of(message)
    chdir(getcwd())
    with open(ospath.join(getcwd(), 'bot/modules/temp.txt'), 'w') as temp:
        temp.write(body)
    stdout = StringIO()
    to_compile = f"def func():\n{indent(body, '  ')}"
    try:
        exec(to_compile, env)
    except Exception as e:
        return f'{e.__class__.__name__}: {e}'
    func = env['func']
    try:
        with redirect_stdout(stdout):
            func_return = func()
    except Exception as e:
        value = stdout.getvalue()
        return f'{value}{format_exc()}'
    else:
        value = stdout.getvalue()
        result = None
        if func_return is None:
            if value:
                result = f'{value}'
            else:
                try:
                    result = f'{repr(eval(body, env))}'
                except:
                    pass
        else:
            result = f'{value}{func_return}'
        if result:
            return result


async def clear(client: Client, message: Message):
    log_input(message)
    global namespaces
    if message.chat.id in namespaces:
        del namespaces[message.chat.id]
    await send('Locals Cleared.', message)


@new_task
async def exechelp(client: Client, message: Message):
    text = f'''
<b>Executor</b>
<b>┌ </b>{BotCommands.EvalCommand} <i>Run Python Code Line | Lines</i>
<b>├ </b>{BotCommands.ExecCommand} <i>Run Commands In Exec</i>
<b>└ </b>{BotCommands.ClearLocalsCommand} <i>Cleared locals</i>
'''
    msg = await sendMessage(text, message)
    await auto_delete_message(message, msg)


bot.add_handler(MessageHandler(exechelp, filters=command(BotCommands.ExecHelpCommand) & CustomFilters.owner))
bot.add_handler(MessageHandler(evaluate, filters=command(BotCommands.EvalCommand) & CustomFilters.owner))
bot.add_handler(MessageHandler(execute, filters=command(BotCommands.ExecCommand) & CustomFilters.owner))
bot.add_handler(MessageHandler(clear, filters=command(BotCommands.ClearLocalsCommand) & CustomFilters.owner))
