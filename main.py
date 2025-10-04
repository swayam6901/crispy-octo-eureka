import os
import random
import json
import threading
import time
import traceback
from dotenv import load_dotenv
from flask import Flask
from pyrogram import Client, filters
from pyrogram.errors import RPCError
from pyrogram.enums import ParseMode  # ✅ Proper import for parse mode

# Load env
load_dotenv()

# Flask app to keep alive
app = Flask(__name__)
@app.route("/")
def alive():
    return "🔥 RoastHimBot is alive and roasting!"

threading.Thread(target=lambda: app.run(host="0.0.0.0", port=3000), daemon=True).start()

# Bot credentials
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

if not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN missing in environment")
if not API_ID or not API_HASH:
    raise RuntimeError("❌ API_ID or API_HASH missing in environment")

API_ID = int(API_ID)

bot = Client(
    "roasthimbot",
    bot_token=BOT_TOKEN,
    api_id=API_ID,
    api_hash=API_HASH
)

# ---------- Roast list ----------
ROAST_FILE = "roasts.txt"
ROASTS = []

def load_roasts():
    global ROASTS
    try:
        with open(ROAST_FILE, "r", encoding="utf-8") as f:
            ROASTS = [l.strip() for l in f if l.strip()]
    except FileNotFoundError:
        ROASTS = ["has an IQ so low, even a potato looks like a genius."]

load_roasts()

def auto_reload_roasts():
    while True:
        time.sleep(3600)
        try:
            load_roasts()
        except:
            pass

threading.Thread(target=auto_reload_roasts, daemon=True).start()

# ---------- Stats ----------
STATS_FILE = "stats.json"
try:
    with open(STATS_FILE, "r", encoding="utf-8") as f:
        STATS = json.load(f)
except:
    STATS = {}

def save_stats():
    try:
        with open(STATS_FILE, "w", encoding="utf-8") as f:
            json.dump(STATS, f)
    except:
        pass

# ---------- Cooldown ----------
COOLDOWN = 5
_last_roast = {}

def check_cooldown(uid):
    uid = str(uid)
    now = time.time()
    last = _last_roast.get(uid, 0)
    if now - last < COOLDOWN:
        return False, int(COOLDOWN - (now - last))
    _last_roast[uid] = now
    return True, 0

# ---------- Helpers ----------
async def resolve_username_to_user(client, username):
    if not username:
        return None
    username = username.lstrip("@")
    try:
        return await client.get_users(username)
    except:
        return None

async def get_target(client, message):
    target_user = None
    target_display = None

    if message.entities:
        for ent in message.entities:
            if ent.type == "text_mention" and ent.user:
                target_user = ent.user
                break
            if ent.type == "mention":
                off = ent.offset
                ln = ent.length
                uname = message.text[off: off + ln]
                found = await resolve_username_to_user(client, uname)
                if found:
                    target_user = found
                else:
                    target_display = uname
                break

    if not target_user and not target_display and message.reply_to_message:
        ru = message.reply_to_message.from_user
        if ru:
            target_user = ru

    if not target_user and not target_display:
        parts = message.text.split()
        if len(parts) >= 2 and parts[1].startswith("@"):
            uname = parts[1]
            found = await resolve_username_to_user(client, uname)
            if found:
                target_user = found
            else:
                target_display = uname

    if target_user:
        target_display = f"@{target_user.username}" if target_user.username else (target_user.first_name or "User")
    return target_display

# ---------- Commands ----------

@bot.on_message(filters.command("start") & filters.private)
async def cmd_start(client, message):
    text = (
        "🔥 <b>RoastHimBot</b> is online!\n\n"
        "👉 Add me to a <b>group</b> and use <code>/roast @username</code> or reply with <code>/roast</code> to roast someone 😈\n\n"
        "💻 Creator: <a href='https://t.me/regnis'>@regnis</a>\n\n"
        "ℹ️ Use <code>/help</code> for commands."
    )
    await message.reply_text(text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)

@bot.on_message(filters.command("help") & filters.private)
async def cmd_help(client, message):
    text = (
        "📜 <b>RoastHimBot - Help</b>\n\n"
        "🔥 <code>/roast @username</code> - Roast the mentioned user\n"
        "🔥 Reply to a user's message with <code>/roast</code> - Roast that user\n"
        "📊 <code>/stats</code> - Show roast stats for the group\n\n"
        "⚠️ Bot works only in <b>groups</b>\n"
        "💻 Credits: <a href='https://t.me/regnis'>@regnis</a>"
    )
    await message.reply_text(text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)

@bot.on_message(filters.command("roast") & filters.group)
async def cmd_roast(client, message):
    try:
        ok, wait = check_cooldown(message.from_user.id)
        if not ok:
            await message.reply_text(f"⏱️ <b>Wait {wait}s</b> before roasting again!", parse_mode=ParseMode.HTML)
            return

        target_display = await get_target(client, message)
        if not target_display:
            await message.reply_text("⚠️ Can't find a valid user to roast! Tag, mention or reply to someone.", parse_mode=ParseMode.HTML)
            return

        if not ROASTS:
            await message.reply_text("❌ Roast list is empty. Add lines to roasts.txt", parse_mode=ParseMode.HTML)
            return

        roast_line = random.choice(ROASTS)
        text = f"🔥 <b>{target_display}</b> {roast_line} 😎"
        await message.reply_text(text, parse_mode=ParseMode.HTML)

        cid = str(message.chat.id)
        if cid not in STATS:
            STATS[cid] = {"total": 0, "users": {}}
        STATS[cid]["total"] += 1
        uid = str(message.from_user.id)
        STATS[cid]["users"][uid] = STATS[cid]["users"].get(uid, 0) + 1
        save_stats()
    except Exception:
        tb = traceback.format_exc()
        print("Roast error:", tb)
        try:
            await message.reply_text("❌ An internal error occurred while roasting. Check logs.", parse_mode=ParseMode.HTML)
        except:
            pass

@bot.on_message(filters.command("stats") & filters.group)
async def cmd_stats(client, message):
    try:
        cid = str(message.chat.id)
        if cid not in STATS or STATS[cid].get("total", 0) == 0:
            await message.reply_text("📊 No roasts have been done in this group yet.", parse_mode=ParseMode.HTML)
            return

        gs = STATS[cid]
        sorted_users = sorted(gs["users"].items(), key=lambda x: x[1], reverse=True)
        lines = [f"📊 <b>Roast Stats</b>\n\nTotal Roasts: <b>{gs['total']}</b>\n\n🏆 <b>Top Roasters:</b>"]
        for uid, cnt in sorted_users[:10]:
            lines.append(f"- <a href='tg://user?id={uid}'>User</a>: {cnt} 🔥")
        text = "\n".join(lines)
        await message.reply_text(text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    except Exception:
        tb = traceback.format_exc()
        print("Stats error:", tb)
        await message.reply_text("❌ Could not fetch stats due to an internal error.", parse_mode=ParseMode.HTML)

@bot.on_message(filters.command("roast") & filters.private)
async def block_private(client, message):
    await message.reply_text("❌ This command only works inside groups.", parse_mode=ParseMode.HTML)

print("🚀 RoastHimBot starting...")
bot.run()
