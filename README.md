# AntiHateBot 🤖

Бот для мониторинга негативных отзывов о брендах на Flamp, Zoon, 2ГИС, Отзовик и в соцсетях. Уведомляет менеджеров в Telegram.

## 📦 Запуск локально

1. Склонируй проект:
```bash
git clone https://github.com/yourname/antihatebot.git
cd antihatebot
```

2. Установи зависимости:
```bash
pip install -r requirements.txt
```

3. В `bot.py` вставь токен Telegram-бота:
```python
BOT_TOKEN = "ВСТАВЬ_СЮДА_СВОЙ_ТОКЕН"
```

4. Запусти бота:
```bash
python bot.py
```

---

## 🚀 Деплой на Render

1. Зарегистрируйся на [https://render.com](https://render.com)
2. Подключи GitHub
3. Создай новый **Web Service**
4. Выбери:
   - **Repo**: этот проект
   - **Environment**: Docker
   - **Branch**: main
   - **Start command**: не нужен (используется `CMD` в Dockerfile)

Render автоматически соберёт контейнер и запустит бота.

---

## ✅ Команды в Telegram

- `/start` — онбординг
- `/brands` — список брендов
- `/check` — ручной запуск анализа
- `/report` — график негатива
- `/help` — справка

---

## 🔒 Не забудь

- Никогда не публикуй токен бота на GitHub!
- Используй `.env` или переменные окружения при деплое, если хочешь больше безопасности.
