import google.generativeai as genai  # ✅ Импорт библиотеки
from aiogram import Bot, Dispatcher
from config import TELEGRAM_BOT_TOKEN, GOOGLE_API_KEY
from database import init_db
from handlers import router

# ✅ Настройка Gemini
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel("gemini-pro")

# ✅ Бот
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
dp.include_router(router)

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())