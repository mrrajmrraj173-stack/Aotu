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

# ================= BUILD VLESS =================

def build_vless(config_data):

    try:

        outbound = config_data["outbounds"][0]

        vnext = outbound["settings"]["vnext"][0]

        user_data = vnext["users"][0]

        stream = outbound["streamSettings"]

        address = vnext["address"]
        port = vnext["port"]

        uuid = user_data["id"]

        security = stream.get("security", "none")

        network = stream.get("network", "ws")

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

        name = "Decrypted"

        link = (
            f"vless://{uuid}@{address}:{port}"
            f"?type={network}"
            f"&security={security}"
            f"&path={path}"
            f"&host={host}"
            f"&sni={sni}"
            f"#{name}"
        )

        return link

    except Exception as e:

        logging.error(f"Build VLESS Error: {e}")

        return None

# ================= BUILD SSH =================

def build_ssh(data):

    try:

        ssh = (
            data["encryptedLockedConfig"]
            ["EncryptedLockedConfig"]
            ["SshConfig"]
        )

        host = ssh.get("EncryptedHost", "")
        port = ssh.get("EncryptedPort", "")
        userx = ssh.get("EncryptedUsername", "")
        password = ssh.get("EncryptedPassword", "")

        if not host:
            return None

        return f"{host}:{port}@{userx}:{password}"

    except Exception as e:

        logging.error(f"SSH Build Error: {e}")

        return None

# ================= EXTRACT =================

def extract_all_configs(data, results):

    try:

        if isinstance(data, dict):

            for k, v in data.items():

                if isinstance(v, str):

                    low = v.lower()

                    if (
                        "vless://" in low
                        or "vmess://" in low
                        or "trojan://" in low
                        or "ss://" in low
                        or "hy2://" in low
                        or "hysteria2://" in low
                    ):

                        results.append(v.strip())

                extract_all_configs(v, results)

            # SSH
            try:

                tunnel_type = (
                    data
                    .get("encryptedLockedConfig", {})
                    .get("LockedAppConfig", {})
                    .get("TunnelType", "")
                )

                if tunnel_type.upper() == "SSH":

                    ssh_link = build_ssh(data)

                    if ssh_link:
                        results.append(ssh_link)

            except:
                pass

            # VLESS
            try:

                enc = (
                    data["encryptedLockedConfig"]
                    ["EncryptedLockedConfig"]
                    ["V2RayConfig"]
                    ["EncryptedConfig"]
                )

                if (
                    isinstance(enc, dict)
                    and "outbounds" in enc
                ):

                    vless = build_vless(enc)

                    if vless:
                        results.append(vless)

            except:
                pass

        elif isinstance(data, list):

            for item in data:

                extract_all_configs(item, results)

    except Exception as e:

        logging.error(f"Extract Error: {e}")

# ================= ADMIN =================

def is_admin(event):

    return event.sender_id == ADMIN_ID

# ================= START =================

@bot.on(events.NewMessage(pattern=r"^/start"))
async def start(event):

    if not is_admin(event):
        return

    await event.reply(
        "🤖 USERBOT MANAGER\n\n"
        "/status\n"
        "/add_channel @channel\n"
        "/remove_channel @channel\n"
        "/show_channels\n\n"
        "/set_decrypt_bot @bot\n"
        "/set_main_channel @channel\n\n"
        "/add_keyword keyword\n"
        "/remove_keyword keyword\n"
        "/show_keywords\n"
        "/show_config"
    )

# ================= STATUS =================

@bot.on(events.NewMessage(pattern=r"^/status"))
async def status(event):

    if not is_admin(event):
        return

    txt = (
        f"🤖 STATUS\n\n"
        f"📡 Channels:\n{config['source_channels']}\n\n"
        f"🔑 Keywords:\n{config['keywords']}\n\n"
        f"📤 Main Channel:\n{config['main_channel']}\n\n"
        f"🤖 Decrypt Bot:\n{config['decrypt_bot']}"
    )

    await event.reply(txt)

# ================= ADD CHANNEL =================

@bot.on(events.NewMessage(pattern=r"^/add_channel"))
async def add_channel(event):

    if not is_admin(event):
        return

    args = event.raw_text.split()[1:]

    if not args:
        return

    for ch in args:

        if ch not in config["source_channels"]:

            config["source_channels"].append(ch)

            try:
                await user(JoinChannelRequest(ch))
            except:
                pass

    save_config()

    await event.reply("✅ Channel added")

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

    txt = "\n".join(config["source_channels"])

    if not txt:
        txt = "No channels"

    await event.reply(txt)

# ================= SET DECRYPT BOT =================

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

# ================= SET MAIN CHANNEL =================

@bot.on(events.NewMessage(pattern=r"^/set_main_channel"))
async def set_main_channel(event):

    if not is_admin(event):
        return

    args = event.raw_text.split()

    if len(args) < 2:
        return

    config["main_channel"] = args[1]

    save_config()

    await event.reply("✅ Saved")

# ================= ADD KEYWORD =================

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

    await event.reply("✅ Keyword added")

# ================= SHOW CONFIG =================

@bot.on(events.NewMessage(pattern=r"^/show_config"))
async def show_config(event):

    if not is_admin(event):
        return

    txt = (
        f"📡 Channels:\n{config['source_channels']}\n\n"
        f"🤖 Decrypt Bot:\n{config['decrypt_bot']}\n\n"
        f"📤 Main Channel:\n{config['main_channel']}\n\n"
        f"🔑 Keywords:\n{config['keywords']}"
    )

    await event.reply(txt)

# ================= MONITOR =================

@user.on(events.NewMessage)
async def monitor(event):

    try:

        if not config["decrypt_bot"]:
            return

        if not config["main_channel"]:
            return

        chat = await event.get_chat()

        username = getattr(chat, "username", None)

        if not username:
            return

        username = f"@{username}"

        if username not in config["source_channels"]:
            return

        msg = event.message

        unique_id = f"{username}_{msg.id}"

        if unique_id in processed:
            return

        if not msg.media:
            return

        matched = True

        if config["keywords"]:

            matched = False

            text = (
                msg.raw_text or ""
            ).lower()

            for kw in config["keywords"]:

                if kw in text:
                    matched = True

            if msg.file:

                name = (
                    msg.file.name or ""
                ).lower()

                for kw in config["keywords"]:

                    if kw in name:
                        matched = True

        if not matched:
            return

        logging.info(
            f"Downloading from {username}"
        )

        path = await msg.download_media()

        if not path:
            return

        logging.info(
            "Sending to decrypt bot"
        )

        await user.send_file(
            config["decrypt_bot"],
            path,
            caption="decrypt"
        )

        processed.add(unique_id)

        save_processed(unique_id)

    except Exception as e:

        logging.error(
            f"Monitor Error: {e}"
        )

# ================= DECRYPT RESPONSE =================

@user.on(events.NewMessage)
async def decrypt_response(event):

    try:

        if not config["decrypt_bot"]:
            return

        sender = await event.get_sender()

        sender_username = (
            getattr(sender, "username", "") or ""
        ).lower()

        decrypt_name = (
            config["decrypt_bot"]
            .replace("@", "")
            .lower()
        )

        if sender_username != decrypt_name:
            return

        text = ""

        # ===== FILE =====

        if event.file:

            path = await event.download_media()

            try:

                with open(
                    path,
                    "r",
                    encoding="utf-8",
                    errors="ignore"
                ) as f:

                    text = f.read()

            except Exception as e:

                logging.error(e)

            finally:

                try:
                    os.remove(path)
                except:
                    pass

        elif event.raw_text:

            text = event.raw_text

        if not text:
            return

        configs = []

        # ===== JSON =====

        try:

            start = text.find("{")
            end = text.rfind("}") + 1

            if start != -1 and end != -1:

                json_text = text[start:end]

                data = json.loads(json_text)

                extract_all_configs(
                    data,
                    configs
                )

        except Exception as e:

            logging.error(
                f"JSON Error: {e}"
            )

        # ===== REGEX =====

        patterns = [

            r'vless://[^\s]+',
            r'vmess://[^\s]+',
            r'trojan://[^\s]+',
            r'ss://[^\s]+',
            r'hy2://[^\s]+',
            r'hysteria2://[^\s]+',

            r'[^\s:@]+:[0-9]+@[^\s:@]+:[^\s]+'
        ]

        for p in patterns:

            found = re.findall(
                p,
                text,
                re.IGNORECASE
            )

            configs.extend(found)

        # ===== CLEAN =====

        clean = []

        for x in configs:

            x = x.strip()

            if x and x not in clean:
                clean.append(x)

        configs = clean

        if not configs:

            logging.warning(
                "No configs found"
            )

            return

        output = "\n\n".join(configs)

        # ===== DIRECT SEND =====

        if len(output) < 4000:

            await user.send_message(
                config["main_channel"],
                output
            )

        else:

            parts = []

            while len(output) > 3500:

                cut = output.rfind(
                    "\n\n",
                    0,
                    3500
                )

                if cut == -1:
                    cut = 3500

                parts.append(
                    output[:cut]
                )

                output = output[cut:]

            parts.append(output)

            for p in parts:

                await user.send_message(
                    config["main_channel"],
                    p
                )

        logging.info(
            f"Sent {len(configs)} configs"
        )

    except Exception as e:

        logging.error(
            f"Decrypt Error: {e}"
        )

# ================= MAIN =================

async def main():

    print("Starting USERBOT...")

    await user.start()

    print("Starting CONTROL BOT...")

    await bot.start(
        bot_token=BOT_TOKEN
    )

    me = await user.get_me()

    print(
        f"Logged in as {me.first_name}"
    )

    print("BOT RUNNING...")

    await asyncio.gather(
        user.run_until_disconnected(),
        bot.run_until_disconnected()
    )

# ================= RUN =================

if __name__ == "__main__":

    asyncio.run(main())