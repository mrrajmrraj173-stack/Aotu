#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import base64
import hashlib
import json
import logging
import os
import re
from collections import deque

from telethon import TelegramClient, events
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest

# =========================================================
# CONFIG
# =========================================================

API_ID = 31053465
API_HASH = "557478eb1546473d5d4da5a15990b379"

BOT_TOKEN = "8285296504:AAHW15d5UcTTYrxR1uAdevw8VNDLLQ9y7l0"

ADMIN_ID = 6167414734

USER_SESSION = "userbot"

CONFIG_FILE = "config.json"
PROCESSED_FILE = "processed.txt"

# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# =========================================================
# CLIENTS
# =========================================================

user = TelegramClient(
    USER_SESSION,
    API_ID,
    API_HASH,
    sequential_updates=True  # Important for multiple channels
)

bot = TelegramClient(
    "controlbot",
    API_ID,
    API_HASH,
    sequential_updates=True
)

# =========================================================
# DEFAULT CONFIG
# =========================================================

config = {
    "source_channels": [],
    "keywords": [],
    "main_channel": "",
    "decrypt_bot": ""
}

# =========================================================
# LOAD CONFIG
# =========================================================

if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config.update(json.load(f))

# =========================================================
# SAVE CONFIG
# =========================================================

def save_config():
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)

# =========================================================
# PROCESSED
# =========================================================

processed = set()
if os.path.exists(PROCESSED_FILE):
    with open(PROCESSED_FILE, "r", encoding="utf-8") as f:
        processed = set(x.strip() for x in f.readlines() if x.strip())

def save_processed(x):
    with open(PROCESSED_FILE, "a", encoding="utf-8") as f:
        f.write(x + "\n")

# =========================================================
# GLOBALS
# =========================================================

queue = deque()
sent_hashes = set()

ALLOWED_EXTENSIONS = [
    ".hc", ".ehi", ".npvt", ".dark", ".ssh", ".txt"
]

MEDIA_EXTENSIONS = [
    ".jpg", ".jpeg", ".png", ".gif", ".mp4", ".mkv", ".mov", ".webp", ".avi"
]

# =========================================================
# HELPERS
# =========================================================

def normalize_text(text):
    return str(text).replace("\r", "\n")

def unique_list(items):
    seen = set()
    result = []
    for item in items:
        item = str(item).strip()
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result

def is_admin(event):
    return event.sender_id in ADMIN_IDS

def is_duplicate(text):
    h = hashlib.md5(text.strip().encode()).hexdigest()
    if h in sent_hashes:
        return True
    sent_hashes.add(h)
    return False

def keyword_match(text):
    if not config["keywords"]:
        return True
    text = text.lower()
    for kw in config["keywords"]:
        if kw.lower() in text:
            return True
    return False

# =========================================================
# MONITORING MULTIPLE CHANNELS
# =========================================================

@user.on(events.NewMessage(incoming=True))
async def monitor(event):
    try:
        if not config["main_channel"]:
            return

        chat = await event.get_chat()
        chat_id = str(event.chat_id)
        chat_username = getattr(chat, "username", None)

        # Check if this chat is in source_channels (by username or ID)
        matched = False
        for source in config["source_channels"]:
            source = str(source).strip()
            if chat_username and source.lower() == f"@{chat_username}".lower():
                matched = True
                break
            if source == chat_id:
                matched = True
                break
        if not matched:
            return

        msg = event.message
        unique_id = f"{chat_id}_{msg.id}"
        if unique_id in processed:
            return

        text = msg.raw_text or ""
        filename = (msg.file.name or "").lower() if msg.file else ""

        if not keyword_match(text + " " + filename):
            return

        # Extract configs
        from functools import partial
        from copy import deepcopy
        extracted = extract_all(text)
        clean = [x for x in extracted if not is_duplicate(x)]

        if clean:
            await user.send_message(config["main_channel"], "\n\n".join(clean))

        if not msg.file:
            processed.add(unique_id)
            save_processed(unique_id)
            return

        # Only queue allowed files
        if any(filename.endswith(ext) for ext in MEDIA_EXTENSIONS):
            return
        if not any(filename.endswith(ext) for ext in ALLOWED_EXTENSIONS):
            return

        path = await msg.download_media()
        queue.append({"path": path})
        logging.info(f"QUEUED: {filename}")

        processed.add(unique_id)
        save_processed(unique_id)

    except Exception as e:
        logging.error(e)

# =========================================================
# PROCESS QUEUE
# =========================================================

async def process_queue():
    while True:
        try:
            if not queue:
                await asyncio.sleep(2)
                continue
            item = queue.popleft()
            path = item["path"]
            await user.send_file(config["decrypt_bot"], path, caption="decrypt")
            logging.info(f"SENT TO DECRYPT: {path}")
            try:
                os.remove(path)
            except:
                pass
            await asyncio.sleep(5)  # reduced from 20 for faster processing
        except Exception as e:
            logging.error(e)
            await asyncio.sleep(5)

# =========================================================
# MAIN
# =========================================================

async def main():
    print("STARTING USERBOT")
    await user.start()
    print("STARTING CONTROL BOT")
    await bot.start(bot_token=BOT_TOKEN)
    me = await user.get_me()
    print(f"LOGGED IN AS: {me.first_name}")
    asyncio.create_task(process_queue())
    print("SYSTEM RUNNING")
    await asyncio.gather(
        user.run_until_disconnected(),
        bot.run_until_disconnected()
    )

if __name__ == "__main__":
    asyncio.run(main())