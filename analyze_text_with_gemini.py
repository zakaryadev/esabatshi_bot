import google.generativeai as genai
from config import GOOGLE_API_KEY

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

def analyze_text_with_gemini(text):
    prompt = f"""
        Ты — финансовый помощник. Проанализируй следующий текст на любом из языков (казахский, узбекский, русский) и определи:
        - Это доход или расход?
        - Какая сумма? (в узбекских сумах)
        - Категория (питание, транспорт, зарплата и т.п.)
        - Дата (если указана)

        Если это запрос информации о балансе (например, 'Сколько денег?', 'Покажи баланс'), верни только: BALANCE_REQUEST

        ВАЖНО: Отвечай ТОЛЬКО в этом формате:
        Тип: [доход/расход]
        Сумма: [только число без пробелов]
        Категория: [еда, зарплата, такси и т.п.]
        Дата: [YYYY-MM-DD] (или сегодняшняя дата, если не указана)

        ТЕКСТ: "{text}"
        """

    response = model.generate_content(prompt)
    return response.text.strip()

def parse_gemini_result(text):
    lines = text.split("\n")
    data = {}

    for line in lines:
        if ": " in line:
            key, value = line.split(": ", 1)
            data[key.lower()] = value.strip()

    # Чистим сумму
    if "сумма" in data:
        cleaned_amount = ''.join(filter(str.isdigit, data["сумма"]))
        data["сумма"] = cleaned_amount if cleaned_amount else "0"
    
    # Нормализуем тип операции
    if "тип" in data:
        operation_type = data["тип"].lower().strip()
        if "доход" in operation_type:
            data["тип"] = "доход"
        elif "расход" in operation_type:
            data["тип"] = "расход"
        else:
            data["тип"] = "неизвестно"
    else:
        data["тип"] = "неизвестно"

    # Устанавливаем дату по умолчанию
    from datetime import datetime
    if "дата" not in data or not data["дата"]:
        data["дата"] = datetime.now().strftime("%Y-%m-%d")

    return data