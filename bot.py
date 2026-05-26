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

ADMIN_IDS = [
    6167414734,
    6167414734
]

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

    return str(text).replace("\r", "\n")

def unique_list(items):

    seen = set()
    result = []

    for item in items:

        item = str(item).strip()

        if not item:
            continue

        if item in seen:
            continue

        seen.add(item)

        result.append(item)

    return result

# =========================================================
# ADMIN CHECK
# =========================================================

def is_admin(event):

    return event.sender_id in ADMIN_IDS

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
# DIRECT CONFIG EXTRACTOR
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

        for item in found:

            item = item.strip()
            item = item.replace("\\/", "/")

            results.append(item)

    return unique_list(results)

# =========================================================
# SSH EXTRACTOR
# =========================================================

def extract_ssh_accounts(text):

    text = normalize_text(text)

    results = []

    direct_pattern = r'([a-zA-Z0-9._-]+\.[a-zA-Z0-9._-]+:\d+@[^\s:@]+:[^\s]+)'

    direct_found = re.findall(
        direct_pattern,
        text,
        re.IGNORECASE
    )

    results.extend(direct_found)

    domain_patterns = [

        r'Dominio\s*:\s*([^\s]+).*?User\s*:\s*([^\s]+).*?Pass\s*:\s*([^\s]+)',

        r'Domain\s*:\s*([^\s]+).*?User\s*:\s*([^\s]+).*?Pass\s*:\s*([^\s]+)',
    ]

    for pattern in domain_patterns:

        found = re.findall(
            pattern,
            text,
            re.IGNORECASE | re.DOTALL
        )

        for domain, username, password in found:

            line = f"{domain}:80@{username}:{password}"

            results.append(line)

    return unique_list(results)

# =========================================================
# BUILD VLESS
# =========================================================

def build_vless(outbound):

    try:

        settings = outbound.get("settings", {})
        vnext = settings.get("vnext", [])[0]
        user_data = vnext.get("users", [])[0]

        stream = outbound.get(
            "streamSettings",
            {}
        )

        address = vnext.get("address", "")
        port = vnext.get("port", 443)

        uuid = user_data.get("id", "")

        network = stream.get(
            "network",
            "ws"
        )

        security = stream.get(
            "security",
            "none"
        )

        ws = stream.get("wsSettings", {})

        path = ws.get("path", "/")

        host = (
            ws.get("headers", {})
            .get("Host", "")
        )

        tls = stream.get(
            "tlsSettings",
            {}
        )

        sni = tls.get(
            "serverName",
            ""
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

        settings = outbound.get("settings", {})
        vnext = settings.get("vnext", [])[0]
        user_data = vnext.get("users", [])[0]

        stream = outbound.get(
            "streamSettings",
            {}
        )

        vmess_json = {

            "v": "2",
            "ps": "DecryptedAuto",
            "add": vnext.get("address", ""),
            "port": str(vnext.get("port", 443)),
            "id": user_data.get("id", ""),
            "aid": "0",

            "net": stream.get(
                "network",
                "ws"
            ),

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

        encoded = base64.b64encode(
            json.dumps(vmess_json).encode()
        ).decode()

        return f"vmess://{encoded}"

    except Exception as e:

        logging.error(f"VMESS BUILD ERROR: {e}")

        return None

# =========================================================
# BUILD TROJAN
# =========================================================

def build_trojan(outbound):

    try:

        settings = outbound.get(
            "settings",
            {}
        )

        server = settings.get(
            "servers",
            []
        )[0]

        stream = outbound.get(
            "streamSettings",
            {}
        )

        address = server.get(
            "address",
            ""
        )

        port = server.get(
            "port",
            443
        )

        password = server.get(
            "password",
            ""
        )

        network = stream.get(
            "network",
            "ws"
        )

        security = stream.get(
            "security",
            "tls"
        )

        ws = stream.get(
            "wsSettings",
            {}
        )

        path = ws.get(
            "path",
            "/"
        )

        host = (
            ws.get("headers", {})
            .get("Host", "")
        )

        tls = stream.get(
            "tlsSettings",
            {}
        )

        sni = tls.get(
            "serverName",
            ""
        )

        return (
            f"trojan://{password}@{address}:{port}"
            f"?type={network}"
            f"&security={security}"
            f"&path={path}"
            f"&host={host}"
            f"&sni={sni}"
            f"#DecryptedAuto"
        )

    except Exception as e:

        logging.error(f"TROJAN BUILD ERROR: {e}")

        return None

# =========================================================
# JSON PARSER
# =========================================================

def parse_json(data, results):

    try:

        if isinstance(data, dict):

            for k, v in data.items():

                if isinstance(v, str):

                    results.extend(
                        extract_direct_configs(v)
                    )

                    results.extend(
                        extract_ssh_accounts(v)
                    )

                parse_json(v, results)

            if "sshField" in data:

                ssh = str(
                    data["sshField"]
                ).strip()

                if ssh:
                    results.append(ssh)

            if "outbounds" in data:

                try:

                    for outbound in data["outbounds"]:

                        protocol = outbound.get(
                            "protocol",
                            ""
                        ).lower()

                        if protocol == "vless":

                            x = build_vless(outbound)

                            if x:
                                results.append(x)

                        elif protocol == "vmess":

                            x = build_vmess(outbound)

                            if x:
                                results.append(x)

                        elif protocol == "trojan":

                            x = build_trojan(outbound)

                            if x:
                                results.append(x)

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

    results.extend(
        extract_direct_configs(text)
    )

    results.extend(
        extract_ssh_accounts(text)
    )

    try:

        fixed = (
            text
            .replace("\\/", "/")
            .replace("\\n", "")
        )

        start = fixed.find("{")
        end = fixed.rfind("}") + 1

        if start != -1 and end != -1:

            raw = fixed[start:end]

            data = json.loads(raw)

            parse_json(data, results)

    except Exception as e:

        logging.error(f"JSON LOAD ERROR: {e}")

    return unique_list(results)

# =========================================================
# COMMANDS
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

    added = []
    failed = []

    for ch in args:

        try:

            if "t.me/+" in ch or "joinchat" in ch:

                invite_hash = (
                    ch.split("/")[-1]
                    .replace("+", "")
                    .strip()
                )

                await user(
                    ImportChatInviteRequest(
                        invite_hash
                    )
                )

            else:

                await user(
                    JoinChannelRequest(ch)
                )

            if ch not in config["source_channels"]:

                config["source_channels"].append(ch)

            added.append(ch)

        except Exception as e:

            logging.error(e)

            failed.append(ch)

    save_config()

    msg = ""

    if added:

        msg += (
            "✅ Added:\n" +
            "\n".join(added)
        )

    if failed:

        msg += (
            "\n\n❌ Failed:\n" +
            "\n".join(failed)
        )

    await event.reply(msg)

# =========================================================
# REMOVE CHANNEL
# =========================================================

@bot.on(events.NewMessage(pattern=r"^/remove_channel"))
async def remove_channel(event):

    if not is_admin(event):
        return

    args = event.raw_text.split()[1:]

    removed = []

    for ch in args:

        if ch in config["source_channels"]:

            config["source_channels"].remove(ch)

            removed.append(ch)

    save_config()

    if removed:

        await event.reply(
            "✅ Removed:\n" +
            "\n".join(removed)
        )

    else:

        await event.reply(
            "❌ Not Found"
        )

# =========================================================
# SHOW CHANNELS
# =========================================================

@bot.on(events.NewMessage(pattern=r"^/show_channels"))
async def show_channels(event):

    if not is_admin(event):
        return

    if not config["source_channels"]:

        await event.reply("No channels")

        return

    await event.reply(
        "\n".join(
            config["source_channels"]
        )
    )

# =========================================================
# SET MAIN CHANNEL
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
# SET DECRYPT BOT
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
# KEYWORD COMMANDS
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

@bot.on(events.NewMessage(pattern=r"^/show_keywords"))
async def show_keywords(event):

    if not is_admin(event):
        return

    txt = "\n".join(config["keywords"])

    await event.reply(
        txt if txt else "No keywords"
    )

# =========================================================
# KEYWORD MATCH
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

            try:
                os.remove(path)
            except:
                pass

            await asyncio.sleep(20)

        except Exception as e:

            logging.error(e)

            await asyncio.sleep(5)

# =========================================================
# MONITOR
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

        if not keyword_match(
            text + " " + filename
        ):
            return

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

        if not msg.file:

            processed.add(unique_id)
            save_processed(unique_id)

            return

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
            f"QUEUED: {filename}"
        )

        processed.add(unique_id)

        save_processed(unique_id)

    except Exception as e:

        logging.error(e)

# =========================================================
# DECRYPT RESPONSE
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

                try:
                    os.remove(path)
                except:
                    pass

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
                "NO CONFIG EXTRACTED"
            )

            return

        await user.send_message(
            config["main_channel"],
            "\n\n".join(clean)
        )

        logging.info(
            f"UPLOADED {len(clean)} CONFIGS"
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

    print(
        f"LOGGED IN AS: {me.first_name}"
    )

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