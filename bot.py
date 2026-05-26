#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ADVANCED TELEGRAM VPN CONFIG COLLECTOR
-------------------------------------

FEATURES
========
✅ Monitor multiple channels
✅ Keyword based filtering
✅ Ignore photos/videos/media
✅ Queue system
✅ Send ONLY 1 file to decrypt bot
✅ Wait 20 sec before next file
✅ Duplicate remover
✅ Auto extract:
    - VLESS
    - VMESS
    - TROJAN
    - SS
    - HY2
    - SSH
✅ Extract from:
    - .hc
    - .dark
    - .npvt
    - .ssh
    - txt/json
✅ Extract from direct messages too
✅ Upload clean configs to main channel
✅ JSON recursive parser
✅ Stable + async safe
"""

import asyncio
import hashlib
import json
import logging
import os
import re
from collections import deque

from telethon import TelegramClient, events
from telethon.tl.functions.channels import JoinChannelRequest

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
    API_HASH
)

bot = TelegramClient(
    "controlbot",
    API_ID,
    API_HASH
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

        processed = set(
            x.strip()
            for x in f.readlines()
            if x.strip()
        )

def save_processed(x):

    with open(PROCESSED_FILE, "a", encoding="utf-8") as f:
        f.write(x + "\n")

# =========================================================
# GLOBALS
# =========================================================

queue = deque()

sent_hashes = set()

processing = False

ALLOWED_EXTENSIONS = [
    ".hc",
    ".ehi",
    ".npvt",
    ".dark",
    ".ssh",
    ".txt"
]

MEDIA_EXTENSIONS = [
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".mp4",
    ".mkv",
    ".mov",
    ".webp",
    ".avi"
]

# =========================================================
# HELPERS
# =========================================================

def normalize_text(text):

    return text.replace("\r", "\n")

def unique_list(items):

    seen = set()

    result = []

    for item in items:

        item = item.strip()

        if not item:
            continue

        h = hashlib.md5(
            item.encode()
        ).hexdigest()

        if h in seen:
            continue

        seen.add(h)

        result.append(item)

    return result

# =========================================================
# DUPLICATE FILTER
# =========================================================

def is_duplicate(text):

    h = hashlib.md5(
        text.strip().encode()
    ).hexdigest()

    if h in sent_hashes:
        return True

    sent_hashes.add(h)

    return False

# =========================================================
# EXTRACT DIRECT CONFIGS
# =========================================================

def extract_direct_configs(text):

    text = normalize_text(text)

    results = []

    patterns = [

        r'vless://[^\s"\']+',

        r'vmess://[^\s"\']+',

        r'trojan://[^\s"\']+',

        r'ss://[^\s"\']+',

        r'hy2://[^\s"\']+',

        r'hysteria2://[^\s"\']+'
    ]

    for pattern in patterns:

        found = re.findall(
            pattern,
            text,
            re.IGNORECASE
        )

        results.extend(found)

    return unique_list(results)

# =========================================================
# EXTRACT SSH
# =========================================================

def extract_ssh_accounts(text):

    text = normalize_text(text)

    results = []

    # FORMAT:
    # host:port@user:pass

    patterns = [

        r'([a-zA-Z0-9._-]+\.[a-zA-Z0-9._-]+:\d+@[^\s:@]+:[^\s]+)',

        r'Dominio\s*:\s*([^\s]+).*?User\s*:\s*([^\s]+).*?Pass\s*:\s*([^\s]+)',
    ]

    # DIRECT
    found = re.findall(
        patterns[0],
        text,
        re.IGNORECASE
    )

    results.extend(found)

    # DOMAIN USER PASS FORMAT
    found2 = re.findall(
        patterns[1],
        text,
        re.IGNORECASE | re.DOTALL
    )

    for domain, userx, password in found2:

        line = f"{domain}:80@{userx}:{password}"

        results.append(line)

    return unique_list(results)

# =========================================================
# BUILD VLESS
# =========================================================

def build_vless(outbound):

    try:

        vnext = outbound["settings"]["vnext"][0]

        user_data = vnext["users"][0]

        stream = outbound.get(
            "streamSettings",
            {}
        )

        address = vnext.get(
            "address",
            ""
        )

        port = vnext.get(
            "port",
            443
        )

        uuid = user_data.get(
            "id",
            ""
        )

        network = stream.get(
            "network",
            "ws"
        )

        security = stream.get(
            "security",
            "none"
        )

        path = (
            stream
            .get("wsSettings", {})
            .get("path", "/")
        )

        host = (
            stream
            .get("wsSettings", {})
            .get("headers", {})
            .get("Host", "")
        )

        sni = (
            stream
            .get("tlsSettings", {})
            .get("serverName", "")
        )

        return (
            f"vless://{uuid}@{address}:{port}"
            f"?type={network}"
            f"&security={security}"
            f"&path={path}"
            f"&host={host}"
            f"&sni={sni}"
            f"#DecryptedAuto"
        )

    except Exception as e:

        logging.error(f"VLESS BUILD ERROR: {e}")

        return None

# =========================================================
# BUILD VMESS
# =========================================================

def build_vmess(outbound):

    try:

        vnext = outbound["settings"]["vnext"][0]

        user_data = vnext["users"][0]

        stream = outbound.get(
            "streamSettings",
            {}
        )

        data = {

            "v": "2",

            "ps": "DecryptedAuto",

            "add": vnext.get("address", ""),

            "port": str(vnext.get("port", 443)),

            "id": user_data.get("id", ""),

            "aid": "0",

            "net": stream.get("network", "ws"),

            "type": "none",

            "host": (
                stream
                .get("wsSettings", {})
                .get("headers", {})
                .get("Host", "")
            ),

            "path": (
                stream
                .get("wsSettings", {})
                .get("path", "/")
            ),

            "tls": (
                "tls"
                if stream.get("security") == "tls"
                else ""
            ),

            "sni": (
                stream
                .get("tlsSettings", {})
                .get("serverName", "")
            )
        }

        import base64

        encoded = base64.b64encode(
            json.dumps(data).encode()
        ).decode()

        return f"vmess://{encoded}"

    except Exception as e:

        logging.error(f"VMESS BUILD ERROR: {e}")

        return None

# =========================================================
# JSON PARSER
# =========================================================

def parse_json(data, results):

    try:

        if isinstance(data, dict):

            # DIRECT CONFIGS
            for k, v in data.items():

                if isinstance(v, str):

                    results.extend(
                        extract_direct_configs(v)
                    )

                    results.extend(
                        extract_ssh_accounts(v)
                    )

                parse_json(v, results)

            # HC SSH FIELD
            if "sshField" in data:

                ssh = str(data["sshField"]).strip()

                if ssh:

                    results.append(ssh)

            # OUTBOUNDS
            if "outbounds" in data:

                try:

                    for outbound in data["outbounds"]:

                        protocol = outbound.get(
                            "protocol",
                            ""
                        ).lower()

                        if protocol == "vless":

                            link = build_vless(
                                outbound
                            )

                            if link:
                                results.append(link)

                        elif protocol == "vmess":

                            link = build_vmess(
                                outbound
                            )

                            if link:
                                results.append(link)

                except Exception as e:
                    logging.error(e)

        elif isinstance(data, list):

            for item in data:

                parse_json(item, results)

    except Exception as e:

        logging.error(f"JSON PARSER ERROR: {e}")

# =========================================================
# EXTRACT EVERYTHING
# =========================================================

def extract_all(text):

    text = normalize_text(text)

    results = []

    # DIRECT CONFIGS
    results.extend(
        extract_direct_configs(text)
    )

    # SSH
    results.extend(
        extract_ssh_accounts(text)
    )

    # TRY JSON
    try:

        start = text.find("{")

        end = text.rfind("}") + 1

        if start != -1 and end != -1:

            raw = text[start:end]

            data = json.loads(raw)

            parse_json(data, results)

    except Exception as e:

        logging.error(f"JSON LOAD ERROR: {e}")

    return unique_list(results)

# =========================================================
# ADMIN CHECK
# =========================================================

def is_admin(event):

    return event.sender_id == ADMIN_ID

# =========================================================
# START
# =========================================================

@bot.on(events.NewMessage(pattern=r"^/start"))
async def start(event):

    if not is_admin(event):
        return

    await event.reply(
        "/add_channel @channel\n"
        "/remove_channel @channel\n"
        "/show_channels\n\n"
        "/set_main_channel @channel\n"
        "/set_decrypt_bot @bot\n\n"
        "/add_keyword keyword\n"
        "/remove_keyword keyword\n"
        "/show_keywords"
    )

# =========================================================
# ADD CHANNEL
# =========================================================

@bot.on(events.NewMessage(pattern=r"^/add_channel"))
async def add_channel(event):

    if not is_admin(event):
        return

    args = event.raw_text.split()[1:]

    for ch in args:

        if ch not in config["source_channels"]:

            config["source_channels"].append(ch)

            try:

                await user(
                    JoinChannelRequest(ch)
                )

            except:
                pass

    save_config()

    await event.reply("✅ Added")

# =========================================================
# REMOVE CHANNEL
# =========================================================

@bot.on(events.NewMessage(pattern=r"^/remove_channel"))
async def remove_channel(event):

    if not is_admin(event):
        return

    args = event.raw_text.split()[1:]

    for ch in args:

        if ch in config["source_channels"]:

            config["source_channels"].remove(ch)

    save_config()

    await event.reply("✅ Removed")

# =========================================================
# SHOW CHANNELS
# =========================================================

@bot.on(events.NewMessage(pattern=r"^/show_channels"))
async def show_channels(event):

    if not is_admin(event):
        return

    txt = "\n".join(
        config["source_channels"]
    )

    if not txt:
        txt = "No channels"

    await event.reply(txt)

# =========================================================
# MAIN CHANNEL
# =========================================================

@bot.on(events.NewMessage(pattern=r"^/set_main_channel"))
async def set_main(event):

    if not is_admin(event):
        return

    args = event.raw_text.split()

    if len(args) < 2:
        return

    config["main_channel"] = args[1]

    save_config()

    await event.reply("✅ Saved")

# =========================================================
# DECRYPT BOT
# =========================================================

@bot.on(events.NewMessage(pattern=r"^/set_decrypt_bot"))
async def set_decrypt_bot(event):

    if not is_admin(event):
        return

    args = event.raw_text.split()

    if len(args) < 2:
        return

    config["decrypt_bot"] = args[1]

    save_config()

    await event.reply("✅ Saved")

# =========================================================
# ADD KEYWORD
# =========================================================

@bot.on(events.NewMessage(pattern=r"^/add_keyword"))
async def add_keyword(event):

    if not is_admin(event):
        return

    args = event.raw_text.split()[1:]

    for kw in args:

        kw = kw.lower()

        if kw not in config["keywords"]:

            config["keywords"].append(kw)

    save_config()

    await event.reply("✅ Added")

# =========================================================
# REMOVE KEYWORD
# =========================================================

@bot.on(events.NewMessage(pattern=r"^/remove_keyword"))
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

# =========================================================
# SHOW KEYWORDS
# =========================================================

@bot.on(events.NewMessage(pattern=r"^/show_keywords"))
async def show_keywords(event):

    if not is_admin(event):
        return

    txt = "\n".join(config["keywords"])

    if not txt:
        txt = "No keywords"

    await event.reply(txt)

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

            await user.send_file(
                config["decrypt_bot"],
                path,
                caption="decrypt"
            )

            logging.info(
                f"SENT TO DECRYPT: {path}"
            )

            # IMPORTANT
            # NEXT FILE AFTER 20 SEC
            await asyncio.sleep(20)

        except Exception as e:

            logging.error(e)

            await asyncio.sleep(5)

# =========================================================
# KEYWORD CHECK
# =========================================================

def keyword_match(text):

    if not config["keywords"]:
        return True

    text = text.lower()

    for kw in config["keywords"]:

        if kw.lower() in text:
            return True

    return False

# =========================================================
# MONITOR CHANNELS
# =========================================================

@user.on(events.NewMessage)
async def monitor(event):

    try:

        if not config["main_channel"]:
            return

        chat = await event.get_chat()

        username = getattr(
            chat,
            "username",
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

        text = msg.raw_text or ""

        filename = ""

        if msg.file:
            filename = (
                msg.file.name or ""
            ).lower()

        # KEYWORD FILTER
        if not keyword_match(
            text + " " + filename
        ):
            return

        # =================================================
        # DIRECT EXTRACTION
        # =================================================

        extracted = extract_all(text)

        clean = []

        for x in extracted:

            if not is_duplicate(x):
                clean.append(x)

        if clean:

            await user.send_message(
                config["main_channel"],
                "\n\n".join(clean)
            )

            logging.info(
                f"DIRECT EXTRACT: {len(clean)}"
            )

        # =================================================
        # FILE CHECK
        # =================================================

        if not msg.file:

            processed.add(unique_id)

            save_processed(unique_id)

            return

        # IGNORE MEDIA
        for ext in MEDIA_EXTENSIONS:

            if filename.endswith(ext):
                return

        valid = False

        for ext in ALLOWED_EXTENSIONS:

            if filename.endswith(ext):

                valid = True
                break

        if not valid:
            return

        path = await msg.download_media()

        queue.append({
            "path": path
        })

        logging.info(
            f"QUEUED FILE: {filename}"
        )

        processed.add(unique_id)

        save_processed(unique_id)

    except Exception as e:

        logging.error(e)

# =========================================================
# DECRYPT BOT RESPONSE
# =========================================================

@user.on(events.NewMessage)
async def decrypt_response(event):

    try:

        if not config["decrypt_bot"]:
            return

        sender = await event.get_sender()

        sender_username = (
            getattr(sender, "username", "")
            or ""
        ).lower()

        decrypt_bot = (
            config["decrypt_bot"]
            .replace("@", "")
            .lower()
        )

        if sender_username != decrypt_bot:
            return

        text = ""

        # TXT FILE
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

        extracted = extract_all(text)

        clean = []

        for x in extracted:

            if not is_duplicate(x):
                clean.append(x)

        if not clean:

            logging.warning(
                "NO CONFIG FOUND"
            )

            return

        await user.send_message(
            config["main_channel"],
            "\n\n".join(clean)
        )

        logging.info(
            f"UPLOADED: {len(clean)} CONFIGS"
        )

    except Exception as e:

        logging.error(e)

# =========================================================
# MAIN
# =========================================================

async def main():

    print("STARTING USERBOT")

    await user.start()

    print("STARTING CONTROL BOT")

    await bot.start(
        bot_token=BOT_TOKEN
    )

    me = await user.get_me()

    print(f"LOGGED IN: {me.first_name}")

    asyncio.create_task(
        process_queue()
    )

    print("SYSTEM RUNNING")

    await asyncio.gather(
        user.run_until_disconnected(),
        bot.run_until_disconnected()
    )

# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    asyncio.run(main())