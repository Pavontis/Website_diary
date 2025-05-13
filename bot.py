import os
import sqlite3
import datetime
import time
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")
BOT_TOKEN = "7641892413:AAFQAoyor9EY7_WUC_rTN6l68FCaKsMpn_c"
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
GET_UPDATES_URL = f"{BASE_URL}/getUpdates"
SEND_MESSAGE_URL = f"{BASE_URL}/sendMessage"
POLL_TIMEOUT = 1
POLL_INTERVAL = 0.2
REMINDER_PERIOD = 60


def send_message(chat_id: int, text: str, parse_mode: str = None):
    data = {"chat_id": chat_id, "text": text}
    if parse_mode:
        data["parse_mode"] = parse_mode
    try:
        resp = requests.post(SEND_MESSAGE_URL, data=data)
        if resp.status_code != 200:
            print(f"❌ Ошибка отправки {chat_id}: {resp.text}")
    except Exception as e:
        print(f"⚠️ Ошибка при отправке сообщения: {e}")


def handle_start(chat_id: int, text: str):
    send_message(chat_id, "Привет! Я Telegram-бот для напоминаний о задачах.")
    send_message(
        chat_id,
        f"Ваш Chat ID:\n`{chat_id}`\nСкопируй его и вставь в форму привязки на сайте.",
        parse_mode="Markdown",
    )
    print(f"[DEBUG] Отправлен Chat ID {chat_id}")


def send_hour_reminders():
    now = datetime.datetime.now()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users WHERE chat_id IS NOT NULL")
    count_users = c.fetchone()[0]

    c.execute(
        """
        SELECT t.id, t.title, t.due_date, u.chat_id
          FROM tasks t
          JOIN users u ON t.user_id = u.id
         WHERE t.is_done = 0
           AND t.due_date IS NOT NULL
           AND t.reminded_hour = 0
           AND u.chat_id IS NOT NULL
    """
    )
    rows = c.fetchall()

    for task_id, title, due_str, chat_id in rows:
        try:
            due = datetime.datetime.fromisoformat(due_str.replace("T", " "))
        except ValueError:
            continue
        delta = (due - now).total_seconds()
        if 0 < delta <= 3600:
            send_message(
                chat_id,
                f"Напоминание: задача «{title}» закончится через 1 час "
                f"({due.strftime('%H:%M %d.%m.%Y')})",
            )
            c.execute("UPDATE tasks SET reminded_hour = 1 WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()


def send_day_reminders():
    now = datetime.datetime.now()

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users WHERE chat_id IS NOT NULL")
    count_users = c.fetchone()[0]

    c.execute(
        """
        SELECT t.id, t.title, t.due_date, u.chat_id
          FROM tasks t
          JOIN users u ON t.user_id = u.id
         WHERE t.is_done = 0
           AND t.due_date IS NOT NULL
           AND t.reminded_day = 0
           AND u.chat_id IS NOT NULL
    """
    )
    rows = c.fetchall()

    for task_id, title, due_str, chat_id in rows:
        try:
            due = datetime.datetime.fromisoformat(due_str.replace("T", " "))
        except ValueError:
            continue
        delta = (due - now).total_seconds()
        if 0 < delta <= 86400:
            send_message(
                chat_id,
                f"Напоминание: задача «{title}» закончится через сутки "
                f"({due.strftime('%H:%M %d.%m.%Y')})",
            )
            c.execute("UPDATE tasks SET reminded_day = 1 WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()


def main_loop():
    offset = None
    last_reminder = time.time() - REMINDER_PERIOD
    while True:
        try:
            resp = requests.get(
                GET_UPDATES_URL, params={"offset": offset, "timeout": POLL_TIMEOUT}
            )
            data = resp.json()
            for upd in data.get("result", []):
                offset = upd["update_id"] + 1
                msg = upd.get("message", {})
                chat = msg.get("chat", {})
                chat_id = chat.get("id")
                text = msg.get("text", "")
                if text.startswith("/start") and chat_id:
                    handle_start(chat_id, text)
            now_ts = time.time()
            if now_ts - last_reminder >= REMINDER_PERIOD:
                send_hour_reminders()
                send_day_reminders()
                last_reminder = now_ts
            time.sleep(POLL_INTERVAL)
        except Exception as e:
            print(f"⚠️ Ошибка в основном цикле: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main_loop()
