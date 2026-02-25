import asyncio
import logging

from aiogram import F
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

import gspread
from oauth2client.service_account import ServiceAccountCredentials


import os
import json

TOKEN = os.environ["BOT_TOKEN"]
if not TOKEN:
    raise ValueError("BOT_TOKEN не задан")

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds_dict = json.loads(os.environ["GOOGLE_CREDENTIALS"])

creds = ServiceAccountCredentials.from_json_keyfile_dict(
    creds_dict,
    scope
)

client = gspread.authorize(creds)
SHEET_URL = "https://docs.google.com/spreadsheets/d/17_xS6lVQn1G3M8AwU04Oa4PIgY6BlgB0T8mDlsysXuo/edit?gid=0#gid=0"
sheet = client.open_by_url(os.environ["SHEET_URL"]).sheet1


# --- FSM ---
class Form(StatesGroup):
    waiting_for_fio = State()


bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Проверить долг")]
    ],
    resize_keyboard=True
)


@dp.message(CommandStart())
async def start_handler(message: Message, state: FSMContext):
    await message.answer(
        "Нажмите кнопку ниже для проверки задолженности.",
        reply_markup=keyboard
    )

@dp.message(F.text == "Проверить долг")
async def request_fio(message: Message, state: FSMContext):
    await state.set_state(Form.waiting_for_fio)
    await message.answer("Введите ваше ФИО (маленькими буквами):")

@dp.message(Form.waiting_for_fio)
async def check_debt(message: Message, state: FSMContext):
    fio_input = message.text.strip().lower()
    username = message.from_user.username

    if not username:
        await message.answer("У вас не установлен username в Telegram.")
        await state.clear()
        return

    username = "@" + username.lower()

    records = sheet.get_all_records()
    user_rows = []

    for row in records:
        table_fio = str(row.get("ФИО", "")).strip().lower()
        table_tg = str(row.get("ТГ", "")).strip().lower()

        if table_fio == fio_input and table_tg == username:
            user_rows.append(row)

    if not user_rows:
        await message.answer("Данные не найдены, попробуйте снова.\n\nВведите ФИО:")
        return

    response = "Ваши данные:\n\n"

    for row in user_rows:
        project = row.get("Проект", "")
        amount = row.get("Сумма", "")
        form_link = str(row.get("Ссылка на форму", "")).strip()

        response += f"Проект: {project} — {amount}\n"

        if form_link:
            response += f"Ссылка на форму: {form_link}\n"

        response += "\n"

    await message.answer(response)
    await state.clear()


async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)


if __name__ == "__main__":

    asyncio.run(main())

