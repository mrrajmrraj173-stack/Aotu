import asyncio
import hashlib
import json
import logging
import os
import re
from collections import deque

from telethon import TelegramClient, events

# ================= CONFIG =================

API_ID = 31053465
API_HASH = "557478eb1546473d5d4da5a15990b379"

BOT_TOKEN = "8285296504:AAHW15d5UcTTYrxR1uAdevw8VNDLLQ9y7l0"

ADMIN_ID = 6167414734

USER_SESSION = "userbot"

CONFIG_FILE = "config.json"

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
    "main_channel": None
}

if os.path.exists(CONFIG_FILE):

    with open(CONFIG_FILE, "r") as f:
        config.update(json.load(f))


def save_config():

    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)


# ================= GLOBAL =================

queue = deque()

processed_messages = set()

processed_content = set()

ALLOWED_EXTENSIONS = [
    ".txt",
    ".json"
]

# ================= HELPERS =================

def is_admin(event):

    return event.sender_id == ADMIN_ID


def normalize_text(text):

    return (
        text.strip()
        .replace(" ", "")
        .replace("\n", "")
        .lower()
    )


def content_hash(text):

    return hashlib.md5(
        normalize_text(text).encode()
    ).hexdigest()


# ================= EXTRACTORS =================

def extract_links(text):

    results = []

    patterns = [
        r'https?://[^\s]+',
    ]

    for pattern in patterns:

        found = re.findall(
            pattern,
            text,
            re.IGNORECASE
        )

        results.extend(found)

    return list(set(results))


def extract_json_values(data, results):

    try:

        if isinstance(data, dict):

            for k, v in data.items():

                if isinstance(v, str):

                    results.extend(
                        extract_links(v)
                    )

                extract_json_values(v, results)

        elif isinstance(data, list):

            for item in data:

                extract_json_values(item, results)

    except Exception as e:

        logging.error(e)


# ================= QUEUE =================

async def process_queue():

    while True:

        try:

            if not queue:

                await asyncio.sleep(2)
                continue

            item = queue.popleft()

            text = item["text"]

            if not text:
                continue

            h = content_hash(text)

            if h in processed_content:
                continue

            processed_content.add(h)

            if config["main_channel"]:

                await user.send_message(
                    config["main_channel"],
                    text
                )

                logging.info("Forwarded result")

            await asyncio.sleep(5)

        except Exception as e:

            logging.error(e)
            await asyncio.sleep(5)


# ================= COMMANDS =================

@bot.on(events.NewMessage(pattern=r"^/start"))
async def start(event):

    if not is_admin(event):
        return

    await event.reply(
        "/add_channel @channel\n"
        "/remove_channel @channel\n"
        "/show_channels\n"
        "/add_keyword keyword\n"
        "/remove_keyword keyword\n"
        "/show_keywords\n"
        "/set_main_channel @channel"
    )


@bot.on(events.NewMessage(pattern=r"^/add_channel"))
async def add_channel(event):

    if not is_admin(event):
        return

    args = event.raw_text.split()[1:]

    for ch in args:

        if ch not in config["source_channels"]:

            config["source_channels"].append(ch)

    save_config()

    await event.reply("Added")


@bot.on(events.NewMessage(pattern=r"^/remove_channel"))
async def remove_channel(event):

    if not is_admin(event):
        return

    args = event.raw_text.split()[1:]

    for ch in args:

        if ch in config["source_channels"]:

            config["source_channels"].remove(ch)

    save_config()

    await event.reply("Removed")


@bot.on(events.NewMessage(pattern=r"^/show_channels"))
async def show_channels(event):

    if not is_admin(event):
        return

    txt = "\n".join(
        config["source_channels"]
    )

    await event.reply(txt or "No channels")


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

    await event.reply("Added")


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

    await event.reply("Removed")


@bot.on(events.NewMessage(pattern=r"^/show_keywords"))
async def show_keywords(event):

    if not is_admin(event):
        return

    txt = "\n".join(config["keywords"])

    await event.reply(txt or "No keywords")


@bot.on(events.NewMessage(pattern=r"^/set_main_channel"))
async def set_main(event):

    if not is_admin(event):
        return

    args = event.raw_text.split()

    if len(args) < 2:
        return

    config["main_channel"] = args[1]

    save_config()

    await event.reply("Saved")


# ================= MONITOR =================

@user.on(events.NewMessage)
async def monitor(event):

    try:

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

        if unique_id in processed_messages:
            return

        processed_messages.add(unique_id)

        text = msg.raw_text or ""

        # keyword filter

        if config["keywords"]:

            matched = False

            low = text.lower()

            for kw in config["keywords"]:

                if kw in low:
                    matched = True
                    break

            if not matched:
                return

        results = []

        # direct text extraction

        results.extend(
            extract_links(text)
        )

        # json extraction

        try:

            start = text.find("{")
            end = text.rfind("}") + 1

            if start != -1 and end != -1:

                data = json.loads(
                    text[start:end]
                )

                extract_json_values(
                    data,
                    results
                )

        except:
            pass

        # file extraction

        if msg.file:

            filename = (
                msg.file.name or ""
            ).lower()

            valid = False

            for ext in ALLOWED_EXTENSIONS:

                if filename.endswith(ext):
                    valid = True
                    break

            if valid:

                path = await msg.download_media()

                try:

                    with open(
                        path,
                        "r",
                        encoding="utf-8",
                        errors="ignore"
                    ) as f:

                        content = f.read()

                    results.extend(
                        extract_links(content)
                    )

                except Exception as e:

                    logging.error(e)

                finally:

                    try:
                        os.remove(path)
                    except:
                        pass

        results = list(set(results))

        if not results:
            return

        final_text = "\n\n".join(results)

        queue.append({
            "text": final_text
        })

        logging.info(
            f"Queued results from {username}"
        )

    except Exception as e:

        logging.error(e)


# ================= MAIN =================

async def main():

    logging.info("Starting user")

    await user.start()

    logging.info("Starting bot")

    await bot.start(
        bot_token=BOT_TOKEN
    )

    asyncio.create_task(
        process_queue()
    )

    logging.info("Running")

    await asyncio.gather(
        user.run_until_disconnected(),
        bot.run_until_disconnected()
    )


# ================= RUN =================

if __name__ == "__main__":

    asyncio.run(main())