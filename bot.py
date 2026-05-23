# =========================================
# TELEGRAM AUTO CONFIG COLLECTOR
# USERBOT + CONTROL BOT
# =========================================

import asyncio
import json
import logging
import os
import re

from telethon import TelegramClient, events

# =========================================
# API CONFIG
# =========================================

API_ID = 31053465
API_HASH = "557478eb1546473d5d4da5a15990b379"

# CONTROL BOT TOKEN
BOT_TOKEN = "8285296504:AAEW7lyDUdAgwXv0rZx1WQEFYeONUaDXplk"

# YOUR TELEGRAM USER ID
ADMIN_ID = 6167414734

# DECRYPT BOT
DECRYPT_BOT = "@ScriptoolzDecrypt_bot"

# =========================================
# FILES
# =========================================

CONFIG_FILE = "config.json"
PROCESSED_FILE = "processed.txt"

# =========================================
# LOGGING
# =========================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# =========================================
# DEFAULT CONFIG
# =========================================

default_config = {
    "source_channels": [],
    "keywords": [],
    "main_channel": None
}

# =========================================
# LOAD CONFIG
# =========================================

if not os.path.exists(CONFIG_FILE):

    with open(CONFIG_FILE, "w") as f:
        json.dump(default_config, f, indent=4)

with open(CONFIG_FILE, "r") as f:
    config = json.load(f)

# =========================================
# SAVE CONFIG
# =========================================

def save_config():

    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

# =========================================
# LOAD PROCESSED
# =========================================

processed = set()

if os.path.exists(PROCESSED_FILE):

    with open(PROCESSED_FILE, "r") as f:
        processed = set(f.read().splitlines())

def save_processed(x):

    with open(PROCESSED_FILE, "a") as f:
        f.write(x + "\n")

# =========================================
# REGEX
# =========================================

PATTERNS = [
    r'vless://[^\s]+',
    r'vmess://[^\s]+',
    r'trojan://[^\s]+',
    r'hysteria2://[^\s]+',
    r'hy2://[^\s]+'
]

# =========================================
# CLIENTS
# =========================================

# USERBOT
user = TelegramClient(
    "userbot",
    API_ID,
    API_HASH
)

# CONTROL BOT
bot = TelegramClient(
    "controlbot",
    API_ID,
    API_HASH
)

# =========================================
# ADMIN CHECK
# =========================================

def is_admin(event):

    return event.sender_id == ADMIN_ID

# =========================================
# START COMMAND
# =========================================

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):

    if not is_admin(event):
        return

    await event.reply(
        "🤖 USERBOT MANAGER\n\n"

        "/status\n\n"

        "/add_channel @channel\n"
        "/remove_channel @channel\n"
        "/show_channels\n\n"

        "/set_main_channel @channel\n\n"

        "/add_keyword keyword\n"
        "/remove_keyword keyword\n"
        "/show_keywords"
    )

# =========================================
# STATUS
# =========================================

@bot.on(events.NewMessage(pattern='/status'))
async def status(event):

    if not is_admin(event):
        return

    text = (
        f"🤖 STATUS\n\n"

        f"📡 Channels:\n"
        f"{config['source_channels']}\n\n"

        f"🔑 Keywords:\n"
        f"{config['keywords']}\n\n"

        f"📤 Main Channel:\n"
        f"{config['main_channel']}"
    )

    await event.reply(text)

# =========================================
# ADD CHANNEL
# =========================================

@bot.on(events.NewMessage(pattern='/add_channel'))
async def add_channel(event):

    if not is_admin(event):
        return

    args = event.raw_text.split()[1:]

    for ch in args:

        if ch not in config["source_channels"]:

            config["source_channels"].append(ch)

    save_config()

    await event.reply(
        f"✅ Added\n\n"
        f"{config['source_channels']}"
    )

# =========================================
# REMOVE CHANNEL
# =========================================

@bot.on(events.NewMessage(pattern='/remove_channel'))
async def remove_channel(event):

    if not is_admin(event):
        return

    args = event.raw_text.split()[1:]

    for ch in args:

        if ch in config["source_channels"]:

            config["source_channels"].remove(ch)

    save_config()

    await event.reply("✅ Removed")

# =========================================
# SHOW CHANNELS
# =========================================

@bot.on(events.NewMessage(pattern='/show_channels'))
async def show_channels(event):

    if not is_admin(event):
        return

    text = "\n".join(
        config["source_channels"]
    )

    if not text:
        text = "No Channels"

    await event.reply(text)

# =========================================
# ADD KEYWORD
# =========================================

@bot.on(events.NewMessage(pattern='/add_keyword'))
async def add_keyword(event):

    if not is_admin(event):
        return

    args = event.raw_text.split()[1:]

    for kw in args:

        kw = kw.lower()

        if kw not in config["keywords"]:

            config["keywords"].append(kw)

    save_config()

    await event.reply(
        f"✅ Keywords\n\n"
        f"{config['keywords']}"
    )

# =========================================
# REMOVE KEYWORD
# =========================================

@bot.on(events.NewMessage(pattern='/remove_keyword'))
async def remove_keyword(event):

    if not is_admin(event):
        return

    args = event.raw_text.split()[1:]

    for kw in args:

        kw = kw.lower()

        if kw in config["keywords"]:

            config["keywords"].remove(kw)

    save_config()

    await event.reply("✅ Removed")

# =========================================
# SHOW KEYWORDS
# =========================================

@bot.on(events.NewMessage(pattern='/show_keywords'))
async def show_keywords(event):

    if not is_admin(event):
        return

    text = "\n".join(
        config["keywords"]
    )

    if not text:
        text = "All Files"

    await event.reply(text)

# =========================================
# SET MAIN CHANNEL
# =========================================

@bot.on(events.NewMessage(pattern='/set_main_channel'))
async def set_main_channel(event):

    if not is_admin(event):
        return

    args = event.raw_text.split()

    if len(args) < 2:

        return await event.reply(
            "Usage:\n"
            "/set_main_channel @channel"
        )

    config["main_channel"] = args[1]

    save_config()

    await event.reply(
        "✅ Main Channel Saved"
    )

# =========================================
# MONITOR CHANNELS
# =========================================

@user.on(events.NewMessage)
async def monitor(event):

    try:

        if not config["main_channel"]:
            return

        chat = await event.get_chat()

        username = getattr(
            chat,
            'username',
            None
        )

        if not username:
            return

        username = f"@{username}"

        if username not in config["source_channels"]:
            return

        msg = event.message

        unique_id = f"{username}_{msg.id}"

        if unique_id in processed:
            return

        text = (
            (msg.raw_text or "") +
            " " +
            (
                msg.file.name.lower()
                if msg.file else ""
            )
        ).lower()

        matched = False

        if not config["keywords"]:

            matched = True

        else:

            for kw in config["keywords"]:

                if kw.lower() in text:

                    matched = True
                    break

        if not matched:
            return

        if not msg.media:
            return

        logging.info(
            f"Matched from {username}"
        )

        # =====================================
        # DOWNLOAD FILE
        # =====================================

        path = await msg.download_media()

        if not path:
            return

        # =====================================
        # SEND TO DECRYPT BOT
        # =====================================

        logging.info(
            "Sending to decrypt bot..."
        )

        await user.send_file(
            DECRYPT_BOT,
            path,
            caption="decrypt"
        )

        processed.add(unique_id)

        save_processed(unique_id)

        os.remove(path)

        await asyncio.sleep(5)

    except Exception as e:

        logging.error(
            f"Monitor Error: {e}"
        )

# =========================================
# DECRYPT BOT RESPONSE
# =========================================

@user.on(events.NewMessage(from_users=DECRYPT_BOT))
async def decrypt_response(event):

    try:

        text = ""

        # =====================================
        # TXT FILE
        # =====================================

        if event.file:

            filename = (
                event.file.name or ""
            ).lower()

            if filename.endswith(".txt"):

                path = await event.download_media()

                with open(
                    path,
                    "r",
                    encoding="utf-8",
                    errors="ignore"
                ) as f:

                    text = f.read()

                os.remove(path)

        elif event.raw_text:

            text = event.raw_text

        if not text:
            return

        # =====================================
        # EXTRACT CONFIGS
        # =====================================

        configs = []

        for pattern in PATTERNS:

            found = re.findall(
                pattern,
                text,
                re.IGNORECASE
            )

            configs.extend(found)

        configs = list(set(configs))

        if not configs:
            return

        logging.info(
            f"Configs Found: {len(configs)}"
        )

        # =====================================
        # SAVE CONFIGS
        # =====================================

        with open(
            "configs.txt",
            "w",
            encoding="utf-8"
        ) as f:

            f.write(
                "\n\n".join(configs)
            )

        # =====================================
        # SEND TO MAIN CHANNEL
        # =====================================

        await user.send_file(
            config["main_channel"],
            "configs.txt",
            caption=(
                f"✅ Fresh Configs\n\n"
                f"🔥 Total Configs: "
                f"{len(configs)}"
            )
        )

        os.remove("configs.txt")

    except Exception as e:

        logging.error(
            f"Decrypt Error: {e}"
        )

# =========================================
# MAIN
# =========================================

async def main():

    print("Starting USERBOT...")

    await user.start()

    print("Starting CONTROL BOT...")

    await bot.start(
        bot_token=BOT_TOKEN
    )

    me = await user.get_me()

    print(
        f"Logged in as "
        f"{me.first_name}"
    )

    print("BOT RUNNING...")

    await asyncio.gather(
        user.run_until_disconnected(),
        bot.run_until_disconnected()
    )

# =========================================
# RUN
# =========================================

asyncio.run(main())