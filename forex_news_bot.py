import requests
from bs4 import BeautifulSoup
from telegram import Bot
from datetime import datetime, timedelta
import pytz
import schedule
import time

# === Налаштування ===
TOKEN = 'тут_твій_токен'
CHAT_ID = 'тут_твій_чат_id'
bot = Bot(token=TOKEN)

# Часовий пояс Києва
kyiv_tz = pytz.timezone("Europe/Kyiv")

# Для запобігання повторним повідомленням
sent_reminders = set()

# Отримати список важливих червоних новин
def fetch_important_news():
    url = 'https://www.forexfactory.com/calendar'
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')

    today = datetime.now(kyiv_tz).date()
    events = []

    for row in soup.select('tr.calendar__row'):
        try:
            time_cell = row.select_one('.calendar__time')
            currency = row.select_one('.calendar__currency')
            impact = row.select_one('.impact--high')
            title = row.select_one('.calendar__event-title')

            if not (time_cell and currency and impact and title):
                continue

            curr = currency.text.strip()
            if curr not in ['USD', 'EUR', 'GBP']:
                continue

            raw_time = time_cell.text.strip()
            if raw_time in ['All Day', 'Tentative', '']:
                continue

            now = datetime.now(kyiv_tz)
            news_time = datetime.strptime(raw_time, "%I:%M%p")
            news_time = kyiv_tz.localize(datetime.combine(now.date(), news_time.time()))

            if news_time.date() != today:
                continue

            events.append({
                'time': news_time,
                'currency': curr,
                'title': title.text.strip()
            })

        except Exception:
            continue

    return events

# Надсилання ранкового звіту
def morning_report():
    events = fetch_important_news()
    if not events:
        bot.send_message(chat_id=CHAT_ID, text="Сьогодні немає важливих новин по EUR, USD, GBP.")
        return

    text = "Сьогоднішні важливі новини:

"
    for ev in events:
        time_str = ev['time'].strftime('%H:%M')
        text += f"{time_str} — {ev['currency']} — {ev['title']}
"

    bot.send_message(chat_id=CHAT_ID, text=text)

# Перевірка на нагадування перед новинами
def reminder_check():
    events = fetch_important_news()
    now = datetime.now(kyiv_tz)

    for ev in events:
        remind_time = ev['time'] - timedelta(minutes=15)
        key = f"{ev['time'].isoformat()}_{ev['currency']}_{ev['title']}"

        if key not in sent_reminders and now >= remind_time and now < ev['time']:
            text = f"Нагадування!
Через 15 хвилин — важлива новина:

{ev['currency']} — {ev['title']}
Час: {ev['time'].strftime('%H:%M')}"
            bot.send_message(chat_id=CHAT_ID, text=text)
            sent_reminders.add(key)

# Розклад
schedule.every().day.at("07:00").do(morning_report)

# Цикл
while True:
    schedule.run_pending()
    reminder_check()
    time.sleep(60)
