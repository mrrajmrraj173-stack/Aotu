import asyncio
import json
import logging
import os
import re
from collections import deque

from telethon import TelegramClient, events
from telethon.tl.functions.channels import JoinChannelRequest

# ================= CONFIG =================

API_ID = 31053465
API_HASH = "557478eb1546473d5d4da5a15990b379"

BOT_TOKEN = "8285296504:AAHW15d5UcTTYrxR1uAdevw8VNDLLQ9y7l0"

ADMIN_ID = 6167414734

USER_SESSION = "userbot"

CONFIG_FILE = "config.json"
PROCESSED_FILE = "processed.txt"

# ================= LOGGING =================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# ================= CLIENTS =================

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

# ================= CONFIG =================

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

# ================= GLOBAL =================

queue = deque()

processing = False

allowed_extensions = [
    ".hc",
    ".ehi",
    ".npvt",
    ".dark",
    ".ssh"
]

# ================= EXTRACT CONFIGS =================

def extract_configs(text):

    configs = []

    patterns = [
        r'vless://[^\s]+',
        r'vmess://[^\s]+',
        r'trojan://[^\s]+',
        r'ss://[^\s]+',
        r'hy2://[^\s]+',
        r'hysteria2://[^\s]+',
        r'[a-zA-Z0-9._-]+:\d+@[^\s:]+:[^\s]+'
    ]

    for p in patterns:

        found = re.findall(
            p,
            text,
            re.IGNORECASE
        )

        configs.extend(found)

    return list(
        set(
            [
                x.strip()
                for x in configs
                if x.strip()
            ]
        )
    )

# ================= BUILD VLESS =================

def build_vless(outbound):

    try:

        vnext = outbound["settings"]["vnext"][0]

        user_data = vnext["users"][0]

        stream = outbound.get(
            "streamSettings",
            {}
        )

        address = vnext.get("address", "")
        port = vnext.get("port", 443)

        uuid = user_data.get("id", "")

        security = stream.get(
            "security",
            "none"
        )

        network = stream.get(
            "network",
            "ws"
        )

        host = (
            stream
            .get("wsSettings", {})
            .get("headers", {})
            .get("Host", "")
        )

        path = (
            stream
            .get("wsSettings", {})
            .get("path", "/")
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
            f"#Decrypted"
        )

    except Exception as e:

        logging.error(e)

        return None

# ================= JSON EXTRACT =================

def extract_json_configs(data, results):

    try:

        if isinstance(data, dict):

            # DIRECT
            for k, v in data.items():

                if isinstance(v, str):

                    results.extend(
                        extract_configs(v)
                    )

                extract_json_configs(
                    v,
                    results
                )

            # V2RAY CONFIG
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

                except:
                    pass

        elif isinstance(data, list):

            for item in data:

                extract_json_configs(
                    item,
                    results
                )

    except Exception as e:

        logging.error(e)

# ================= ADMIN CHECK =================

def is_admin(event):

    return event.sender_id == ADMIN_ID

# ================= COMMANDS =================

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

# ================= ADD CHANNEL =================

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

# ================= REMOVE CHANNEL =================

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

# ================= SHOW CHANNELS =================

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

# ================= SET MAIN =================

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

# ================= SET DECRYPT BOT =================

@bot.on(events.NewMessage(pattern=r"^/set_decrypt_bot"))
async def set_bot(event):

    if not is_admin(event):
        return

    args = event.raw_text.split()

    if len(args) < 2:
        return

    config["decrypt_bot"] = args[1]

    save_config()

    await event.reply("✅ Saved")

# ================= KEYWORDS =================

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

# ================= REMOVE KEYWORD =================

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

# ================= SHOW KEYWORDS =================

@bot.on(events.NewMessage(pattern=r"^/show_keywords"))
async def show_keywords(event):

    if not is_admin(event):
        return

    txt = "\n".join(config["keywords"])

    if not txt:
        txt = "No keywords"

    await event.reply(txt)

# ================= KEEP ALIVE =================

async def keep_alive():

    while True:

        try:

            if config["decrypt_bot"]:

                await user.send_message(
                    config["decrypt_bot"],
                    "alive"
                )

        except Exception as e:

            logging.error(e)

        await asyncio.sleep(30)

# ================= PROCESS QUEUE =================

async def process_queue():

    global processing

    while True:

        if processing:

            await asyncio.sleep(2)
            continue

        if not queue:

            await asyncio.sleep(2)
            continue

        processing = True

        item = queue.popleft()

        try:

            path = item["path"]

            await user.send_file(
                config["decrypt_bot"],
                path,
                caption="decrypt"
            )

            logging.info(
                "Sent to decrypt bot"
            )

            await asyncio.sleep(40)

        except Exception as e:

            logging.error(e)

        processing = False

# ================= MONITOR =================

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

        # ================= KEYWORD CHECK =================

        matched = True

        if config["keywords"]:

            matched = False

            low = text.lower()

            for kw in config["keywords"]:

                if kw in low:
                    matched = True
                    break

            if msg.file:

                name = (
                    msg.file.name or ""
                ).lower()

                for kw in config["keywords"]:

                    if kw in name:
                        matched = True
                        break

        if not matched:
            return

        # ================= DIRECT CONFIG =================

        direct_configs = extract_configs(text)

        if direct_configs:

            await user.send_message(
                config["main_channel"],
                "\n\n".join(direct_configs)
            )

            processed.add(unique_id)

            save_processed(unique_id)

            return

        # ================= FILE ONLY =================

        if not msg.file:
            return

        filename = (
            msg.file.name or ""
        ).lower()

        # ignore media
        if (
            filename.endswith(".jpg")
            or filename.endswith(".png")
            or filename.endswith(".mp4")
            or filename.endswith(".jpeg")
            or filename.endswith(".webp")
        ):
            return

        valid = False

        for ext in allowed_extensions:

            if filename.endswith(ext):

                valid = True
                break

        if not valid:
            return

        path = await msg.download_media()

        queue.append({
            "path": path
        })

        processed.add(unique_id)

        save_processed(unique_id)

        logging.info(
            f"Queued: {filename}"
        )

    except Exception as e:

        logging.error(e)

# ================= DECRYPT RESPONSE =================

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

        decrypt_name = (
            config["decrypt_bot"]
            .replace("@", "")
            .lower()
        )

        if sender_username != decrypt_name:
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

                os.remove(path)

        elif event.raw_text:

            text = event.raw_text

        if not text:
            return

        configs = []

        # DIRECT
        configs.extend(
            extract_configs(text)
        )

        # JSON
        try:

            start = text.find("{")
            end = text.rfind("}") + 1

            if start != -1 and end != -1:

                data = json.loads(
                    text[start:end]
                )

                extract_json_configs(
                    data,
                    configs
                )

        except Exception as e:

            logging.error(e)

        configs = list(
            set(
                [
                    x.strip()
                    for x in configs
                    if x.strip()
                ]
            )
        )

        if not configs:

            logging.warning(
                "No configs extracted"
            )

            return

        final_text = "\n\n".join(configs)

        await user.send_message(
            config["main_channel"],
            final_text
        )

        logging.info(
            f"Uploaded {len(configs)} configs"
        )

    except Exception as e:

        logging.error(e)

# ================= MAIN =================

async def main():

    print("Starting USERBOT")

    await user.start()

    print("Starting BOT")

    await bot.start(
        bot_token=BOT_TOKEN
    )

    me = await user.get_me()

    print(
        f"Logged in as {me.first_name}"
    )

    asyncio.create_task(
        keep_alive()
    )

    asyncio.create_task(
        process_queue()
    )

    print("RUNNING")

    await asyncio.gather(
        user.run_until_disconnected(),
        bot.run_until_disconnected()
    )

# ================= RUN =================

if __name__ == "__main__":

    asyncio.run(main())