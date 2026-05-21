# telegram_auto_bot.py

import asyncio
import json
import logging
from telethon import TelegramClient, events
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.errors import FloodWaitError

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# ============= CONFIGURATION =============
API_ID = 31053465
API_HASH = '557478eb1546473d5d4da5a15990b379'
BOT_TOKEN = '8285296504:AAEn4SjqhAa-oEgW8KrXNJ0QuPyyhol9UTU'

ADMIN_ID = 6167414734

source_channels = []
decrypt_bot_username = None
main_channel_id = None
keywords = []

DATA_FILE = 'bot_data.json'

# ============= DATA SAVE/LOAD =============
def save_data():
    with open(DATA_FILE, 'w') as f:
        json.dump({
            'source_channels': source_channels,
            'decrypt_bot_username': decrypt_bot_username,
            'main_channel_id': main_channel_id,
            'keywords': keywords
        }, f)


def load_data():
    global source_channels, decrypt_bot_username
    global main_channel_id, keywords

    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)

            source_channels = data.get('source_channels', [])
            decrypt_bot_username = data.get('decrypt_bot_username')
            main_channel_id = data.get('main_channel_id')
            keywords = data.get('keywords', [])

    except FileNotFoundError:
        pass


load_data()

# ============= TELEGRAM CLIENT =============
bot = TelegramClient(
    'auto_bot',
    API_ID,
    API_HASH,
    auto_reconnect=True,
    retry_delay=5,
    connection_retries=999999
)

# ============= COMMANDS =============
@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    if event.sender_id != ADMIN_ID:
        return

    await event.reply(
        "🤖 Bot Active!\n\n"
        "Commands:\n"
        "/add_channels @channel\n"
        "/remove_channels @channel\n"
        "/show_channels\n\n"
        "/add_keyword keyword\n"
        "/remove_keyword keyword\n"
        "/show_keywords\n\n"
        "/set_decrypt_bot @bot\n"
        "/set_main_channel @channel\n"
        "/show_config\n\n"
        "/scan_now\n"
        "/start_auto\n"
        "/stop_auto"
    )


@bot.on(events.NewMessage(pattern='/add_channels'))
async def add_channels(event):
    if event.sender_id != ADMIN_ID:
        return

    global source_channels

    args = event.raw_text.split()[1:]

    for ch in args:
        ch = ch.strip()

        if ch not in source_channels:
            source_channels.append(ch)

            try:
                await bot(JoinChannelRequest(ch))
                logging.info(f"Joined {ch}")

            except Exception as e:
                logging.error(f"Join failed {ch}: {e}")

    save_data()

    await event.reply(f"✅ Added:\n{source_channels}")


@bot.on(events.NewMessage(pattern='/remove_channels'))
async def remove_channels(event):
    if event.sender_id != ADMIN_ID:
        return

    global source_channels

    args = event.raw_text.split()[1:]

    for ch in args:
        if ch in source_channels:
            source_channels.remove(ch)

    save_data()

    await event.reply(f"✅ Remaining:\n{source_channels}")


@bot.on(events.NewMessage(pattern='/show_channels'))
async def show_channels(event):
    if event.sender_id != ADMIN_ID:
        return

    text = '\n'.join(source_channels) if source_channels else 'None'

    await event.reply(f"📡 Channels:\n{text}")


@bot.on(events.NewMessage(pattern='/add_keyword'))
async def add_keyword(event):
    if event.sender_id != ADMIN_ID:
        return

    global keywords

    args = event.raw_text.split()[1:]

    for kw in args:
        kw = kw.lower()

        if kw not in keywords:
            keywords.append(kw)

    save_data()

    await event.reply(f"✅ Keywords:\n{keywords}")


@bot.on(events.NewMessage(pattern='/remove_keyword'))
async def remove_keyword(event):
    if event.sender_id != ADMIN_ID:
        return

    global keywords

    args = event.raw_text.split()[1:]

    for kw in args:
        kw = kw.lower()

        if kw in keywords:
            keywords.remove(kw)

    save_data()

    await event.reply(f"✅ Remaining:\n{keywords}")


@bot.on(events.NewMessage(pattern='/show_keywords'))
async def show_keywords(event):
    if event.sender_id != ADMIN_ID:
        return

    text = ', '.join(keywords) if keywords else 'All Files'

    await event.reply(f"🔑 Keywords:\n{text}")


@bot.on(events.NewMessage(pattern='/set_decrypt_bot'))
async def set_decrypt_bot(event):
    if event.sender_id != ADMIN_ID:
        return

    global decrypt_bot_username

    args = event.raw_text.split()

    if len(args) < 2:
        await event.reply("Usage:\n/set_decrypt_bot @username")
        return

    decrypt_bot_username = args[1]

    save_data()

    await event.reply(f"✅ Decrypt Bot:\n{decrypt_bot_username}")


@bot.on(events.NewMessage(pattern='/set_main_channel'))
async def set_main_channel(event):
    if event.sender_id != ADMIN_ID:
        return

    global main_channel_id

    args = event.raw_text.split()

    if len(args) < 2:
        await event.reply("Usage:\n/set_main_channel @channel")
        return

    try:
        entity = await bot.get_entity(args[1])

        main_channel_id = entity.id

        save_data()

        await event.reply("✅ Main channel saved")

    except Exception as e:
        await event.reply(f"❌ Error:\n{e}")


@bot.on(events.NewMessage(pattern='/show_config'))
async def show_config(event):
    if event.sender_id != ADMIN_ID:
        return

    await event.reply(
        f"📋 Config\n\n"
        f"Channels: {source_channels}\n"
        f"Keywords: {keywords}\n"
        f"Decrypt Bot: {decrypt_bot_username}\n"
        f"Main Channel: {main_channel_id}"
    )


# ============= SCAN =============
async def scan_and_forward():

    if not source_channels:
        return

    if not decrypt_bot_username:
        return

    processed_file = 'processed_ids.txt'

    try:
        with open(processed_file, 'r') as f:
            processed_ids = set(f.read().splitlines())

    except:
        processed_ids = set()

    for channel in source_channels:

        try:
            entity = await bot.get_entity(channel)

            logging.info(f"Scanning {channel}")

            async for message in bot.iter_messages(entity, limit=100):

                msg_id = f"{channel}_{message.id}"

                if msg_id in processed_ids:
                    continue

                has_file = bool(message.document or message.media)

                matched = True

                if keywords:

                    matched = False

                    text = (
                        (message.text or '') +
                        (message.message or '')
                    ).lower()

                    for kw in keywords:
                        if kw in text:
                            matched = True
                            break

                    if message.document:

                        for attr in message.document.attributes:

                            if hasattr(attr, 'file_name'):

                                filename = attr.file_name.lower()

                                if any(
                                    kw in filename
                                    for kw in keywords
                                ):
                                    matched = True

                if has_file and matched:

                    try:
                        await bot.forward_messages(
                            decrypt_bot_username,
                            message
                        )

                        processed_ids.add(msg_id)

                        with open(processed_file, 'a') as f:
                            f.write(msg_id + '\n')

                        logging.info(
                            f"Forwarded from {channel}"
                        )

                        await asyncio.sleep(3)

                    except FloodWaitError as e:

                        logging.warning(
                            f"FloodWait {e.seconds}s"
                        )

                        await asyncio.sleep(e.seconds)

                    except Exception as e:

                        logging.error(
                            f"Forward failed: {e}"
                        )

        except Exception as e:

            logging.error(
                f"Scan error {channel}: {e}"
            )


# ============= RECEIVE FROM DECRYPT BOT =============
@bot.on(events.NewMessage)
async def decrypt_handler(event):

    if not decrypt_bot_username:
        return

    if not main_channel_id:
        return

    try:
        sender = await event.get_sender()

        sender_username = (
            getattr(sender, 'username', '') or ''
        ).lower()

        decrypt_clean = (
            decrypt_bot_username
            .replace('@', '')
            .lower()
        )

        if sender_username == decrypt_clean:

            try:

                if event.message.media:

                    await bot.forward_messages(
                        main_channel_id,
                        event.message
                    )

                elif event.message.text:

                    await bot.send_message(
                        main_channel_id,
                        event.message.text
                    )

                logging.info(
                    "Sent to main channel"
                )

            except Exception as e:

                logging.error(
                    f"Main channel send error: {e}"
                )

    except Exception as e:

        logging.error(
            f"Decrypt handler error: {e}"
        )


# ============= AUTO SCAN =============
auto_scan_task = None


async def auto_scan_loop():

    while True:

        try:

            logging.info("Auto Scan Running")

            await scan_and_forward()

            await asyncio.sleep(600)

        except asyncio.CancelledError:

            logging.info("Auto Scan Stopped")
            break

        except Exception as e:

            logging.error(
                f"Auto scan error: {e}"
            )

            await asyncio.sleep(10)


@bot.on(events.NewMessage(pattern='/scan_now'))
async def scan_now(event):

    if event.sender_id != ADMIN_ID:
        return

    await event.reply("🔄 Scanning...")

    await scan_and_forward()

    await event.reply("✅ Done")


@bot.on(events.NewMessage(pattern='/start_auto'))
async def start_auto(event):

    if event.sender_id != ADMIN_ID:
        return

    global auto_scan_task

    if auto_scan_task and not auto_scan_task.done():

        await event.reply(
            "⚠️ Already Running"
        )

        return

    auto_scan_task = asyncio.create_task(
        auto_scan_loop()
    )

    await event.reply(
        "✅ Auto Scan Started"
    )


@bot.on(events.NewMessage(pattern='/stop_auto'))
async def stop_auto(event):

    if event.sender_id != ADMIN_ID:
        return

    global auto_scan_task

    if auto_scan_task:

        auto_scan_task.cancel()

        auto_scan_task = None

        await event.reply(
            "✅ Auto Scan Stopped"
        )

    else:

        await event.reply(
            "⚠️ Not Running"
        )


# ============= MAIN =============
async def main():

    try:

        await bot.start(bot_token=BOT_TOKEN)

        logging.info("🤖 Bot Started")

        try:

            await bot.send_message(
                ADMIN_ID,
                "✅ Bot Online"
            )

        except Exception as e:

            logging.error(
                f"Admin msg error: {e}"
            )

        await bot.run_until_disconnected()

    except Exception as e:

        logging.error(
            f"Main error: {e}"
        )

    finally:

        await bot.disconnect()


if __name__ == '__main__':

    asyncio.run(main())