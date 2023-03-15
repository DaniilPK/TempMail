import asyncio
import logging
import sqlite3
from os import getenv

from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp.web import run_app
from aiohttp.web_app import Application

from tempmail import TempMail

logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = getenv("TOKEN")
APP_BASE_URL = getenv("APP_BASE_URL")

storage = MemoryStorage()
bot = Bot(token=TELEGRAM_TOKEN, parse_mode="HTML")
dp = Dispatcher(storage=storage)


async def on_startup(bot: Bot, base_url: str):
    await bot.set_webhook(f"{base_url}/webhook")


router = Router()

conn = sqlite3.connect('emails.db')
c = conn.cursor()

c.execute('''
    CREATE TABLE IF NOT EXISTS TempEmail (
    user INTEGER PRIMARY KEY,
    email TEXT,
    email_id TEXT,
    token TEXT
);
''')
conn.commit()


def keyboard():
    kb = [
        [types.KeyboardButton(text="➕ New email address"),
         types.KeyboardButton(text="🔄 Refresh")],
    ]
    return types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


@router.message(Command(commands=['start']), F.chat.type == 'private')
@router.message(F.text == "➕ New email address", F.chat.type == 'private')
async def start_cmd_handler(message: types.Message, bot: Bot):
    await bot.send_chat_action(message.chat.id, 'typing')
    tm = TempMail()
    email, id, token = tm._output()

    c.execute('SELECT * FROM TempEmail WHERE user=?', (message.from_user.id,))
    if c.fetchone() is None:
        c.execute('INSERT INTO TempEmail (user,email, email_id, token) VALUES (?, ?, ?, ?)',
                  (message.from_user.id, email, id, token,))
        conn.commit()
    else:
        c.execute('UPDATE TempEmail SET email=?, email_id=?, token=? WHERE user=?',
                  (email, id, token, message.from_user.id,))
        conn.commit()

    await message.answer(f"<b>Your temporary email address:</b>\n\n <code><b>{email}</b></code>",
                         reply_markup=keyboard())


@router.message(F.text == "🔄 Refresh", F.chat.type == 'private')
async def emails_cmd_handler(message: types.Message, bot: Bot):
    await bot.send_chat_action(message.chat.id, 'typing')
    tm = TempMail()

    c.execute('SELECT email,email_id,token FROM TempEmail WHERE user=?', (message.from_user.id,))
    email, id, token = c.fetchone()
    tm._set(email, id, token)

    all_mails = tm.get_mails()
    if len(all_mails) == 0:
        await message.answer(f'Current email address: <code>{tm.email}</code>\n\n<b>Your inbox is empty</b>')
    else:
        await message.answer(f'<b>Current email address:</b> <code>{tm.email}</code>')
        printed_mails = []
        for mail in all_mails:
            if mail.id not in printed_mails:
                printed_mails.append(mail.id)

                text = f"<b>From:</b> {mail.from_name} - {mail.from_addr}\n"
                text += f"<b>Subject:</b> {mail.subject}\n"
                text += f"<b>Body:</b> {mail.text}\n"

                await message.answer(text, parse_mode=ParseMode.HTML)
                await asyncio.sleep(3)

        del printed_mails


def main():
    logger.info("Starting bot")

    dp["base_url"] = APP_BASE_URL
    dp.startup.register(on_startup)

    dp.include_router(router)

    app = Application()

    SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    ).register(app, path="/webhook")
    setup_application(app, dp, bot=bot)

    run_app(app, host="127.0.0.1", port=5000)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format=u'%(filename)s:%(lineno)d #%(levelname)-8s [%(asctime)s] - %(name)s - %(message)s',
    )
    main()
