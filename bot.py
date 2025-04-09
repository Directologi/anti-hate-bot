import logging
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
from apscheduler.schedulers.background import BackgroundScheduler
import requests
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt

# === НАСТРОЙКИ ===
BOT_TOKEN = "ВСТАВЬ_СЮДА_СВОЙ_ТОКЕН"  # 👈 ВСТАВЬ сюда свой токен Telegram бота

# === ЛОГИ ===
logging.basicConfig(level=logging.INFO)

# === БАЗА ДАННЫХ ===
conn = sqlite3.connect("antihatebot.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS brands (id INTEGER PRIMARY KEY, name TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS reviews (id INTEGER PRIMARY KEY AUTOINCREMENT, brand TEXT, source TEXT, text TEXT, tone TEXT, link TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)")
conn.commit()

# === АНАЛИЗ ТОНАЛЬНОСТИ (простая эвристика) ===
def detect_tone(text: str) -> str:
    negative_words = ["ужас", "плохо", "отвратительно", "некомпетентно", "негатив", "кошмар", "хамство"]
    text_lower = text.lower()
    if any(word in text_lower for word in negative_words):
        return "негатив"
    return "нейтрал"

# === ПАРСЕР (пример на Отзовик) ===
def parse_otzovik(brand):
    url = f"https://otzovik.com/reviews/{brand.replace(' ', '_')}/"
    headers = {"User-Agent": "Mozilla/5.0"}
    reviews = []

    try:
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        items = soup.find_all("div", class_="review-body")

        for item in items[:5]:
            text = item.get_text(strip=True)
            tone = detect_tone(text)
            reviews.append((brand, "otzovik", text, tone, url))

    except Exception as e:
        logging.error(f"Ошибка при парсинге Otzovik: {e}")

    return reviews

# === КОМАНДЫ БОТА ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Привет! Я AntiHateBot. Введите /add <бренд> для добавления бренда к мониторингу.")

async def add_brand(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) == 0:
        await update.message.reply_text("Введите название бренда: /add MyBrand")
        return

    brand = " ".join(context.args)
    cursor.execute("INSERT INTO brands (name) VALUES (?)", (brand,))
    conn.commit()
    await update.message.reply_text(f"✅ Бренд '{brand}' добавлен!")

async def list_brands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cursor.execute("SELECT name FROM brands")
    rows = cursor.fetchall()
    if not rows:
        await update.message.reply_text("Список брендов пуст.")
        return
    text = "\n".join(f"- {row[0]}" for row in rows)
    await update.message.reply_text("📋 Мониторинг брендов:\n" + text)

async def manual_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cursor.execute("SELECT name FROM brands")
    brands = [row[0] for row in cursor.fetchall()]
    all_reviews = []

    for brand in brands:
        reviews = parse_otzovik(brand)
        for r in reviews:
            cursor.execute("INSERT INTO reviews (brand, source, text, tone, link) VALUES (?, ?, ?, ?, ?)", r)
        all_reviews.extend(reviews)

    conn.commit()

    if all_reviews:
        for r in all_reviews:
            await update.message.reply_text(f"⚠️ [{r[0]} - {r[1]}] {r[3].upper()}\n{r[2][:300]}...\n🔗 {r[4]}")
    else:
        await update.message.reply_text("Новых негативных отзывов не найдено.")

async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cursor.execute("SELECT tone, COUNT(*) FROM reviews GROUP BY tone")
    data = cursor.fetchall()

    if not data:
        await update.message.reply_text("Отзывов пока нет.")
        return

    labels = [d[0] for d in data]
    values = [d[1] for d in data]

    plt.figure(figsize=(5, 3))
    plt.bar(labels, values, color=["orange", "red"])
    plt.title("Общая тональность отзывов")
    plt.tight_layout()
    plt.savefig("report.png")
    plt.close()

    with open("report.png", "rb") as photo:
        await update.message.reply_photo(photo)

# === ПЛАНОВЫЙ АНАЛИЗ ===
def scheduled_job():
    cursor.execute("SELECT name FROM brands")
    brands = [row[0] for row in cursor.fetchall()]

    for brand in brands:
        reviews = parse_otzovik(brand)
        for r in reviews:
            cursor.execute("INSERT INTO reviews (brand, source, text, tone, link) VALUES (?, ?, ?, ?, ?)", r)
    conn.commit()

# === ГЛАВНАЯ ФУНКЦИЯ ===
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_brand))
    app.add_handler(CommandHandler("brands", list_brands))
    app.add_handler(CommandHandler("check", manual_check))
    app.add_handler(CommandHandler("report", report))

    # Планировщик
    scheduler = BackgroundScheduler()
    scheduler.add_job(scheduled_job, "interval", hours=24)
    scheduler.start()

    app.run_polling()

if __name__ == "__main__":
    main()
