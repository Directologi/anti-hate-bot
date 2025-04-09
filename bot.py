import logging
import sqlite3
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler
import requests
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt

BOT_TOKEN = "ВСТАВЬ_СЮДА_СВОЙ_ТОКЕН"

logging.basicConfig(level=logging.INFO)

conn = sqlite3.connect("antihatebot.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users (chat_id INTEGER PRIMARY KEY)")
cursor.execute("CREATE TABLE IF NOT EXISTS brands (id INTEGER PRIMARY KEY, chat_id INTEGER, name TEXT)")
cursor.execute("""CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER,
    brand TEXT,
    source TEXT,
    text TEXT,
    tone TEXT,
    link TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)""")
conn.commit()

def detect_tone(text: str) -> str:
    negative_words = ["ужас", "плохо", "отвратительно", "некомпетентно", "негатив", "кошмар", "хамство"]
    text_lower = text.lower()
    if any(word in text_lower for word in negative_words):
        return "негатив"
    return "нейтрал"

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
            reviews.append(("otzovik", text, tone, url))
    except Exception as e:
        logging.error(f"Ошибка Otzovik: {e}")
    return reviews

def parse_flamp(brand):
    return []  # Заглушка, можно добавить реальный парсинг

def parse_zoon(brand):
    return []  # Заглушка

def parse_2gis(brand):
    return []  # Заглушка

def parse_vk(brand):
    return []  # Заглушка

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    cursor.execute("INSERT OR IGNORE INTO users (chat_id) VALUES (?)", (chat_id,))
    conn.commit()
    await update.message.reply_text("👋 Привет! Введи /add <бренд> для начала мониторинга.")

async def add_brand(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not context.args:
        await update.message.reply_text("❗ Укажи название бренда: /add MyBrand")
        return
    brand = " ".join(context.args)
    cursor.execute("INSERT INTO brands (chat_id, name) VALUES (?, ?)", (chat_id, brand))
    conn.commit()
    await update.message.reply_text(f"✅ Бренд '{brand}' добавлен.")

async def list_brands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    cursor.execute("SELECT name FROM brands WHERE chat_id = ?", (chat_id,))
    rows = cursor.fetchall()
    if not rows:
        await update.message.reply_text("📭 У тебя пока нет брендов.")
        return
    text = "\n".join(f"— {row[0]}" for row in rows)
    await update.message.reply_text("📋 Твои бренды:
" + text)

async def manual_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    cursor.execute("SELECT name FROM brands WHERE chat_id = ?", (chat_id,))
    brands = [row[0] for row in cursor.fetchall()]
    all_reviews = []

    for brand in brands:
        for parser in [parse_otzovik, parse_flamp, parse_zoon, parse_2gis, parse_vk]:
            reviews = parser(brand)
            for source, text, tone, link in reviews:
                cursor.execute("INSERT INTO reviews (chat_id, brand, source, text, tone, link) VALUES (?, ?, ?, ?, ?, ?)",
                               (chat_id, brand, source, text, tone, link))
                all_reviews.append((brand, source, text, tone, link))

    conn.commit()

    if all_reviews:
        for r in all_reviews:
            await update.message.reply_text(f"⚠️ [{r[0]} - {r[1]}] {r[3].upper()}
{r[2][:300]}...
🔗 {r[4]}")
    else:
        await update.message.reply_text("🎉 Новых негативных отзывов не найдено.")

async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    cursor.execute("SELECT tone, COUNT(*) FROM reviews WHERE chat_id = ? GROUP BY tone", (chat_id,))
    data = cursor.fetchall()
    if not data:
        await update.message.reply_text("📉 Пока нет отзывов для анализа.")
        return
    labels = [d[0] for d in data]
    values = [d[1] for d in data]
    plt.figure(figsize=(5, 3))
    plt.bar(labels, values, color=["orange", "red"])
    plt.title("Тональность отзывов")
    plt.tight_layout()
    plt.savefig("report.png")
    plt.close()
    with open("report.png", "rb") as photo:
        await update.message.reply_photo(photo)

async def sources(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    cursor.execute("SELECT source, COUNT(*) FROM reviews WHERE chat_id = ? GROUP BY source", (chat_id,))
    data = cursor.fetchall()
    if not data:
        await update.message.reply_text("🔍 Пока нет данных по источникам.")
        return
    text = "\n".join(f"✅ {row[0]} — {row[1]}" for row in data)
    await update.message.reply_text(f"📡 Источники отзывов:
{text}")

def scheduled_job():
    cursor.execute("SELECT DISTINCT chat_id FROM brands")
    for row in cursor.fetchall():
        chat_id = row[0]
        cursor.execute("SELECT name FROM brands WHERE chat_id = ?", (chat_id,))
        brands = [r[0] for r in cursor.fetchall()]
        for brand in brands:
            for parser in [parse_otzovik, parse_flamp, parse_zoon, parse_2gis, parse_vk]:
                reviews = parser(brand)
                for source, text, tone, link in reviews:
                    cursor.execute("INSERT INTO reviews (chat_id, brand, source, text, tone, link) VALUES (?, ?, ?, ?, ?, ?)",
                                   (chat_id, brand, source, text, tone, link))
    conn.commit()

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_brand))
    app.add_handler(CommandHandler("brands", list_brands))
    app.add_handler(CommandHandler("check", manual_check))
    app.add_handler(CommandHandler("report", report))
    app.add_handler(CommandHandler("sources", sources))
    scheduler = BackgroundScheduler()
    scheduler.add_job(scheduled_job, "interval", hours=24)
    scheduler.start()
    app.run_polling()

if __name__ == "__main__":
    main()