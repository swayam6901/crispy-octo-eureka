import os
import random
import json
import threading
import time
from pyrogram import Client, filters
from flask import Flask

# ----------------- 1. KEEP-ALIVE SERVER -----------------
app = Flask(__name__)

@app.route('/')
def home():
    return "🔥 RoastHimBot is alive and roasting!"

def run_server():
    app.run(host="0.0.0.0", port=3000)

threading.Thread(target=run_server).start()

# ----------------- 2. TELEGRAM BOT SETUP -----------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")

bot = Client(
    "roasthimbot",
    bot_token=BOT_TOKEN,
    api_id=API_ID,
    api_hash=API_HASH
)

# ----------------- 3. ROAST LINES -----------------
ROAST_FILE = "roasts.txt"
ROASTS = []

def load_roasts():
    global ROASTS
    try:
        with open(ROAST_FILE, "r", encoding="utf-8") as f:
            ROASTS = [line.strip() for line in f if line.strip()]
        print(f"✅ Loaded {len(ROASTS)} roasts")
    except FileNotFoundError:
        ROASTS = ["has an IQ so low, even a potato looks like a genius."]
        print("⚠️ roasts.txt not found, using default roast.")

# initial load
load_roasts()

# reload roasts every hour
def auto_reload_roasts():
    while True:
        time.sleep(3600)
        load_roasts()

threading.Thread(target=auto_reload_roasts, daemon=True).start()

# ----------------- 4. STATS -----------------
STATS_FILE = "stats.json"
try:
    with open(STATS_FILE, "r") as f:
        STATS = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    STATS = {}  # {group_id: {total: int, users: {user_id: count}}}

def save_stats():
    with open(STATS_FILE, "w") as f:
        json.dump(STATS, f)

# ----------------- 5. COOLDOWN -----------------
COOLDOWN = 5  # seconds
last_roast = {}  # {user_id: timestamp}

def check_cooldown(user_id):
    now = time.time()
    if user_id in last_roast and now - last_roast[user_id] < COOLDOWN:
        return False
    last_roast[user_id] = now
    return True

# ----------------- 6. COMMANDS -----------------

@bot.on_message(filters.command("start") & filters.private)
async def start_private(client, message):
    await message.reply_text(
        "🔥 **RoastHimBot** is online!\n\n"
        "👉 Add me to a **group** and use `/roast @username` to roast someone brutally 😈\n\n"
        "👨‍💻 Creator: [@regnis](https://t.me/regnis)",
        disable_web_page_preview=True
    )

@bot.on_message(filters.command("help") & filters.private)
async def help_private(client, message):
    await message.reply_text(
        "**📜 RoastHimBot Commands:**\n\n"
        "🔥 `/roast @username` - Roast the mentioned user brutally.\n"
        "📊 `/stats` - Show roast stats for the group.\n"
        "📩 `/help` - Show this help message.\n\n"
        "⚠️ Works only in **groups**.\n\n"
        "👨‍💻 Credits: [@regnis](https://t.me/regnis)",
        disable_web_page_preview=True
    )

# ----------------- 7. ROAST COMMAND -----------------

@bot.on_message(filters.command("roast") & filters.group)
async def roast_user(client, message):
    if not message.entities or len(message.entities) < 2:
        await message.reply_text("⚠️ Tag someone to roast! Usage: `/roast @username`")
        return

    # check cooldown
    user_id = message.from_user.id
    if not check_cooldown(user_id):
        await message.reply_text(f"⏱️ Wait {COOLDOWN}s before roasting again!")
        return

    # get tagged user
    tagged_user = None
    entity = message.entities[1]
    if entity.type == "mention":
        tagged_user = message.text.split()[1]
    elif entity.type == "text_mention":
        tagged_user = f"@{entity.user.username}" if entity.user.username else entity.user.first_name

    if not tagged_user:
        await message.reply_text("⚠️ Couldn't find a valid username to roast!")
        return

    roast_line = random.choice(ROASTS)
    await message.reply_text(f"{tagged_user} 's {roast_line}")

    # update stats
    chat_id = str(message.chat.id)
    if chat_id not in STATS:
        STATS[chat_id] = {"total": 0, "users": {}}
    STATS[chat_id]["total"] += 1
    STATS[chat_id]["users"][str(user_id)] = STATS[chat_id]["users"].get(str(user_id), 0) + 1
    save_stats()

# ----------------- 8. STATS COMMAND -----------------

@bot.on_message(filters.command("stats") & filters.group)
async def stats_group(client, message):
    chat_id = str(message.chat.id)
    if chat_id not in STATS:
        await message.reply_text("📊 No roasts have been done in this group yet!")
        return

    group_stats = STATS[chat_id]
    text = f"📊 **Roast Stats:**\n\nTotal Roasts: {group_stats['total']}\n\n"
    text += "**Top Roasters:**\n"
    sorted_users = sorted(group_stats["users"].items(), key=lambda x: x[1], reverse=True)
    for uid, count in sorted_users[:10]:
        text += f"- [{uid}](tg://user?id={uid}): {count}\n"

    await message.reply_text(text, disable_web_page_preview=True)

# ----------------- 9. BLOCK PRIVATE ROAST -----------------
@bot.on_message(filters.command("roast") & filters.private)
async def block_private(client, message):
    await message.reply_text("❌ This command only works inside groups.")

# ----------------- 10. START BOT -----------------
print("🚀 RoastHimBot is running...")
bot.run()
