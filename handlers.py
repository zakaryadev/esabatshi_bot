# handlers.py
import sqlite3
from aiogram import Router, F
from aiogram.types import FSInputFile, Message
from aiogram.filters import Command
from database import (
    add_transaction,
    add_user,
    calculate_balance,
    calculate_balance_by_category,
    get_user_language,
    set_user_language,
    get_transaction_history,
    export_to_excel,
)
from analyze_text_with_gemini import analyze_text_with_gemini, parse_gemini_result
from voice_to_text import voice_to_text

router = Router()

@router.message(Command("start"))
async def start(message: Message):
    user_id = message.from_user.id
    name = message.from_user.full_name
    add_user(user_id, name)
    await message.answer(
        "Привет! Я ваш финансовый помощник.\n"
        "Вы можете отправлять мне текстовые или голосовые сообщения,\n"
        "например: 'Потратил 300 сумов на кофе'"
    )

@router.message(Command("history"))
async def show_history(message: Message):
    user_id = message.from_user.id
    args = message.text.split()[1:]  # Получаем аргументы после /history

    if args and args[0].lower() == "week":
        period = "week"
    elif args and args[0].lower() == "month":
        period = "month"
    else:
        period = None

    if period == "week":
        query = """
            SELECT type, amount, category, date 
            FROM transactions 
            WHERE user_id = ? AND date >= date('now', '-7 days')
            ORDER BY date DESC
        """
    elif period == "month":
        query = """
            SELECT type, amount, category, date 
            FROM transactions 
            WHERE user_id = ? AND strftime('%Y-%m', date) = strftime('%Y-%m', 'now')
            ORDER BY date DESC
        """
    else:
        query = """
            SELECT type, amount, category, date 
            FROM transactions 
            WHERE user_id = ? 
            ORDER BY date DESC 
            LIMIT 10
        """

    conn = sqlite3.connect("budget.db")
    cursor = conn.cursor()
    cursor.execute(query, (user_id,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await message.answer("⚠️ У вас пока нет записей.")
        return

    # Формируем текст истории
    history_text = "📋 История транзакций:\n\n"
    for i, (trans_type, amount, category, date) in enumerate(rows, start=1):
        sign = "+" if trans_type == "доход" else "-"
        history_text += f"{i}. [{date}] {trans_type.capitalize()}: {sign}{abs(amount):,.0f} сум ({category})\n"

    await message.answer(history_text)

@router.message(F.voice)
async def handle_voice(message: Message, bot):
    user_id = message.from_user.id
    user_language = get_user_language(user_id) or "ru-RU"  # По умолчанию русский

    file_id = message.voice.file_id
    file = await bot.get_file(file_id)
    file_path = file.file_path
    await bot.download_file(file_path, "voice.ogg")

    text = voice_to_text("voice.ogg", language=user_language)
    result = analyze_text_with_gemini(text)
    await message.reply(result)

    parsed = parse_gemini_result(result)

    if parsed.get("тип") and parsed.get("сумма"):
        try:
            amount = float(parsed["сумма"])
            add_transaction(message.from_user.id, parsed)
            await message.answer(f"✅ {parsed['тип'].capitalize()}: {amount:,.0f} сум")
        except ValueError:
            await message.answer("❌ Не удалось распознать сумму.")
    else:
        await message.answer("⚠️ Не хватает данных для записи. Укажите тип (доход/расход) и сумму.")
    
@router.message(Command("export"))
async def export_data(message: Message):
    user_id = message.from_user.id
    file_path = export_to_excel(user_id)

    # Отправляем файл пользователю
    document = FSInputFile(file_path)
    await message.answer_document(document=document, caption="📊 Ваш отчёт в формате Excel")

    # Удаляем временный файл после отправки
    import os
    os.remove(file_path)

@router.message(Command("language"))
async def set_language(message: Message):
    user_id = message.from_user.id
    args = message.text.split()[1:]

    if not args:
        await message.answer("Выберите язык: /language kazakh, /language uzbek, /language karakalpak")
        return

    language = args[0].lower()
    if language in ["kazakh", "kk"]:
        set_user_language(user_id, "kk-KZ")
        await message.answer("✅ Язык установлен: казахский")
    elif language in ["uzbek", "uz"]:
        set_user_language(user_id, "uz-UZ")
        await message.answer("✅ Язык установлен: узбекский")
    elif language in ["karakalpak", "kaa"]:
        set_user_language(user_id, "uz-UZ")  # Используем узбекский как аналог
        await message.answer("✅ Язык установлен: каракалпакский (используется узбекский)")
    else:
        await message.answer("❌ Неизвестный язык. Выберите: /language kazakh, /language uzbek, /language karakalpak")

@router.message(F.text)
async def handle_text(message: Message):
    text = message.text.strip().lower()

    # Проверка на запрос баланса
    balance_keywords = ["баланс", "сколько денег", "сколько у меня", "сколько есть"]
    if any(keyword in text for keyword in balance_keywords):
        balance = calculate_balance(message.from_user.id)
        categories = calculate_balance_by_category(message.from_user.id)

        report_text = f"🧮 Общий баланс: {balance:,.0f} сум\n\n"
        report_text += "📊 Баланс по категориям:\n"

        if not categories:
            report_text += "- Нет данных по категориям."
        else:
            for category, amount in categories.items():
                sign = "+" if amount >= 0 else "-"
                report_text += f"- {category}: {sign}{abs(amount):,.0f} сум\n"

        await message.answer(report_text)
        return

    result = analyze_text_with_gemini(text)

    # Если Gemini вернул BALANCE_REQUEST
    if "BALANCE_REQUEST" in result:
        balance = calculate_balance(message.from_user.id)
        categories = calculate_balance_by_category(message.from_user.id)

        report_text = f"🧮 Общий баланс: {balance:,.0f} сум\n\n"
        report_text += "📊 Баланс по категориям:\n"

        if not categories:
            report_text += "- Нет данных по категориям."
        else:
            for category, amount in categories.items():
                sign = "+" if amount >= 0 else "-"
                report_text += f"- {category}: {sign}{abs(amount):,.0f} сум\n"

        await message.answer(report_text)
        return

    parsed = parse_gemini_result(result)
    if parsed:
        try:
            amount = float(parsed["сумма"])
            add_transaction(message.from_user.id, parsed)
            await message.answer(f"✅ {parsed['тип'].capitalize()}: {amount:,.0f} сум")
        except ValueError:
            await message.answer("❌ Не удалось распознать сумму.")