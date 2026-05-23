import asyncio
import json
import logging
import os
import re

from telethon import TelegramClient, events
from telethon.tl.functions.channels import JoinChannelRequest

# ================= CONFIG =================

API_ID = 31053465
API_HASH = "557478eb1546473d5d4da5a15990b379"
BOT_TOKEN = "8285296504:AAELcUuzAmjX1gynoiBGtuvf7DnQLCkbZGo"
ADMIN_ID = 61674147

USER_SESSION = "userbot"

CONFIG_FILE = "config.json"
PROCESSED_FILE = "processed.txt"

# ================= LOGGING =================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# ================= CLIENTS =================

user = TelegramClient(USER_SESSION, API_ID, API_HASH)
bot = TelegramClient("control", API_ID, API_HASH)

# ================= CONFIG DATA =================

config = {
    "source_channels": [],
    "keywords": [],
    "main_channel": None,
    "decrypt_bot": None
}

if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "r") as f:
        config.update(json.load(f))

def save_config():
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

# ================= PROCESSED =================

processed = set()

if os.path.exists(PROCESSED_FILE):
    with open(PROCESSED_FILE, "r") as f:
        processed = set(f.read().splitlines())

def save_processed(x):
    with open(PROCESSED_FILE, "a") as f:
        f.write(x + "\n")

# ================= UNIVERSAL EXTRACTOR =================

def extract_all_configs(data, results):

    if isinstance(data, dict):

        for k, v in data.items():

            if isinstance(v, str):

                v_low = v.lower()

                # VLESS / VMESS / TROJAN
                if "vless://" in v_low or "vmess://" in v_low or "trojan://" in v_low:
                    results.append(v.strip())

                # SSH FORMAT user@host:port:pass style
                if re.match(r".+:.+@.+:.+", v.strip()):
                    results.append(v.strip())

            extract_all_configs(v, results)

    elif isinstance(data, list):

        for i in data:
            extract_all_configs(i, results)

# ================= CONTROL BOT COMMANDS =================

@bot.on(events.NewMessage(pattern="/start"))
async def start(event):

    if event.sender_id != ADMIN_ID:
        return

    await event.reply(
        "🤖 BOT READY\n\n"
        "/add_channel @name\n"
        "/remove_channel @name\n"
        "/show_channels\n"
        "/set_decrypt_bot @bot\n"
        "/set_main_channel @channel\n"
        "/add_keyword word\n"
        "/show_config"
    )

# ================= ADD CHANNEL =================

@bot.on(events.NewMessage(pattern="/add_channel"))
async def add_channel(event):

    if event.sender_id != ADMIN_ID:
        return

    args = event.raw_text.split()[1:]

    for ch in args:

        if ch not in config["source_channels"]:

            config["source_channels"].append(ch)

            try:
                await user(JoinChannelRequest(ch))
            except:
                pass

    save_config()
    await event.reply("✅ Channel added")

# ================= MONITOR CHANNELS =================

@user.on(events.NewMessage)
async def monitor(event):

    try:

        chat = await event.get_chat()
        username = getattr(chat, "username", None)

        if username:
            username = f"@{username}"

        if config["source_channels"] and username not in config["source_channels"]:
            return

        msg = event.message

        if not msg.media:
            return

        # keyword filter
        if config["keywords"]:
            text = (msg.raw_text or "").lower()

            if not any(k.lower() in text for k in config["keywords"]):
                return

        path = await msg.download_media()

        await user.send_file(
            config["decrypt_bot"],
            path,
            caption="decrypt"
        )

        logging.info(f"Sent to decrypt bot from {username}")

        processed.add(f"{username}_{msg.id}")
        save_processed(f"{username}_{msg.id}")

    except Exception as e:
        logging.error(e)

# ================= DECRYPT RESPONSE =================

@user.on(events.NewMessage)
async def decrypt_response(event):

    try:

        if not config["decrypt_bot"]:
            return

        sender = await event.get_sender()

        if not sender.username:
            return

        if sender.username.lower() != config["decrypt_bot"].replace("@", "").lower():
            return

        text = ""

        # read file or text
        if event.file:

            path = await event.download_media()

            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()

            os.remove(path)

        else:
            text = event.raw_text or ""

        text = text.strip()

        configs = []

        # JSON parse first
        try:
            data = json.loads(text)
            extract_all_configs(data, configs)

        except:

            # fallback regex
            configs = re.findall(
                r'(vless://[^\s]+|vmess://[^\s]+|trojan://[^\s]+|[^\s]+@[^\s]+:[^\s]+)',
                text
            )

        configs = list(set([c.strip() for c in configs if c]))

        if not configs:
            logging.warning("No configs found")
            return

        out_file = "configs.txt"

        with open(out_file, "w", encoding="utf-8") as f:
            f.write("\n".join(configs))

        await user.send_file(
            config["main_channel"],
            out_file,
            caption=f"✅ Configs: {len(configs)}"
        )

        logging.info("Uploaded to main channel")

    except Exception as e:
        logging.error(e)

# ================= MAIN =================

async def main():

    print("Starting USERBOT...")
    await user.start()

    print("Starting CONTROL BOT...")
    await bot.start(bot_token=BOT_TOKEN)

    print("BOT RUNNING...")

    await asyncio.gather(
        user.run_until_disconnected(),
        bot.run_until_disconnected()
    )

if __name__ == "__main__":
    asyncio.run(main())