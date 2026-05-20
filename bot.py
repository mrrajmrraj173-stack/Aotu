# telegram_auto_bot.py
import asyncio
import json
import logging
from telethon import TelegramClient, events
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.errors import FloodWaitError

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ============= CONFIGURATION =============
API_ID = 31053465        # Apna API ID daalo
API_HASH = '557478eb1546473d5d4da5a15990b379'
BOT_TOKEN = '8285296504:AAEn4SjqhAa-oEgW8KrXNJ0QuPyyhol9UTU'

ADMIN_ID = 6167414734   # Apna Telegram user ID

# Yeh admin commands se set honge
source_channels = []      # Jahan se file uthani hai
decrypt_bot_username = None  # Decrypt bot ka username (e.g., @DecryptBot)
main_channel_id = None    # Jahan final config upload karna hai
keywords = []             # Keywords filter

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
    global source_channels, decrypt_bot_username, main_channel_id, keywords
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
bot = TelegramClient('auto_bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# ============= COMMANDS =============
@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    if event.sender_id != ADMIN_ID:
        await event.reply("❌ Aap admin nahi ho!")
        return
    await event.reply("""
🤖 **Bot Active!**

📌 **Commands:**

/add_channels @channel1 @channel2
/remove_channels @channel1
/show_channels

/add_keyword keyword1 keyword2
/remove_keyword keyword1
/show_keywords

/set_decrypt_bot @username
/set_main_channel @channelusername
/show_config

/scan_now
/start_auto (har 10 min me scan)
/stop_auto

✅ Bot file uthayega → decrypt bot ko forward karega → decrypt bot se jo config aayegi → main channel pe upload karega
    """)

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
                logging.error(f"Failed to join {ch}: {e}")
    save_data()
    await event.reply(f"✅ Source Channels: {source_channels}")

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
    await event.reply(f"✅ Remaining channels: {source_channels}")

@bot.on(events.NewMessage(pattern='/show_channels'))
async def show_channels(event):
    if event.sender_id != ADMIN_ID:
        return
    await event.reply(f"📡 Source Channels: {', '.join(source_channels) if source_channels else 'None'}")

@bot.on(events.NewMessage(pattern='/add_keyword'))
async def add_keyword(event):
    if event.sender_id != ADMIN_ID:
        return
    global keywords
    args = event.raw_text.split()[1:]
    for kw in args:
        kw_lower = kw.lower()
        if kw_lower not in keywords:
            keywords.append(kw_lower)
    save_data()
    await event.reply(f"✅ Keywords: {keywords}")

@bot.on(events.NewMessage(pattern='/remove_keyword'))
async def remove_keyword(event):
    if event.sender_id != ADMIN_ID:
        return
    global keywords
    args = event.raw_text.split()[1:]
    for kw in args:
        kw_lower = kw.lower()
        if kw_lower in keywords:
            keywords.remove(kw_lower)
    save_data()
    await event.reply(f"✅ Remaining keywords: {keywords}")

@bot.on(events.NewMessage(pattern='/show_keywords'))
async def show_keywords(event):
    if event.sender_id != ADMIN_ID:
        return
    await event.reply(f"🔑 Keywords: {', '.join(keywords) if keywords else 'None (all files)'}")

@bot.on(events.NewMessage(pattern='/set_decrypt_bot'))
async def set_decrypt_bot(event):
    if event.sender_id != ADMIN_ID:
        return
    global decrypt_bot_username
    args = event.raw_text.split()
    if len(args) < 2:
        await event.reply("Usage: /set_decrypt_bot @username")
        return
    decrypt_bot_username = args[1]
    save_data()
    await event.reply(f"✅ Decrypt bot set to: {decrypt_bot_username}")

@bot.on(events.NewMessage(pattern='/set_main_channel'))
async def set_main_channel(event):
    if event.sender_id != ADMIN_ID:
        return
    global main_channel_id
    args = event.raw_text.split()
    if len(args) < 2:
        await event.reply("Usage: /set_main_channel @channel")
        return
    channel = args[1]
    try:
        entity = await bot.get_entity(channel)
        main_channel_id = entity.id
        save_data()
        await event.reply(f"✅ Main channel set to: {channel}")
    except Exception as e:
        await event.reply(f"❌ Error: {e}")

@bot.on(events.NewMessage(pattern='/show_config'))
async def show_config(event):
    if event.sender_id != ADMIN_ID:
        return
    await event.reply(f"""
📋 **Current Config:**
🔹 Source Channels: {', '.join(source_channels) if source_channels else '❌ Not set'}
🔹 Keywords: {', '.join(keywords) if keywords else 'All files'}
🔹 Decrypt Bot: {decrypt_bot_username or '❌ Not set'}
🔹 Main Channel: {main_channel_id or '❌ Not set'}
    """)

@bot.on(events.NewMessage(pattern='/scan_now'))
async def scan_now(event):
    if event.sender_id != ADMIN_ID:
        return
    await event.reply("🔄 Scanning and forwarding started...")
    await scan_and_forward()
    await event.reply("✅ Scan completed!")

# ============= MAIN LOGIC =============
async def scan_and_forward():
    """Source channels se files uthao aur decrypt bot ko forward karo"""
    if not source_channels:
        logging.warning("No source channels configured")
        return
    
    if not decrypt_bot_username:
        logging.warning("Decrypt bot not configured")
        return
    
    processed_ids_file = 'processed_ids.txt'
    
    # Load already processed file IDs
    try:
        with open(processed_ids_file, 'r') as f:
            processed_ids = set(f.read().splitlines())
    except:
        processed_ids = set()
    
    for channel in source_channels:
        try:
            entity = await bot.get_entity(channel)
            logging.info(f"Scanning {channel}...")
            
            async for message in bot.iter_messages(entity, limit=100):
                msg_id = str(message.id)
                
                # Skip if already processed
                if msg_id in processed_ids:
                    continue
                
                # Check if message has file/document
                has_file = message.document or message.media
                
                # Check keywords (if any)
                matched = True
                if keywords:
                    msg_text = (message.text or message.caption or "").lower()
                    matched = any(kw.lower() in msg_text for kw in keywords)
                    # Also check filename
                    if message.document and message.document.attributes:
                        for attr in message.document.attributes:
                            if hasattr(attr, 'file_name'):
                                if any(kw.lower() in attr.file_name.lower() for kw in keywords):
                                    matched = True
                
                if has_file and matched:
                    # Forward to decrypt bot
                    try:
                        await bot.forward_messages(decrypt_bot_username, message)
                        processed_ids.add(msg_id)
                        logging.info(f"✅ Forwarded file from {channel} to {decrypt_bot_username}")
                        
                        # Save processed ID
                        with open(processed_ids_file, 'a') as f:
                            f.write(f"{msg_id}\n")
                        
                        await asyncio.sleep(2)  # Rate limit
                        
                    except FloodWaitError as e:
                        logging.warning(f"Flood wait {e.seconds}s")
                        await asyncio.sleep(e.seconds)
                    except Exception as e:
                        logging.error(f"Forward failed: {e}")
                        
        except Exception as e:
            logging.error(f"Error scanning {channel}: {e}")

# ============= RECEIVE FROM DECRYPT BOT =============
@bot.on(events.NewMessage)
async def handle_from_decrypt_bot(event):
    """Decrypt bot se jo bhi message aayega, usse main channel pe forward karo"""
    global decrypt_bot_username, main_channel_id
    
    # Agar main channel set nahi hai to ignore
    if not main_channel_id:
        return
    
    # Check if message is FROM decrypt bot
    sender = await event.get_sender()
    sender_username = getattr(sender, 'username', '')
    
    if decrypt_bot_username and sender_username:
        # Remove @ and compare
        decrypt_bot_clean = decrypt_bot_username.replace('@', '').lower()
        sender_clean = sender_username.lower()
        
        if decrypt_bot_clean == sender_clean:
            # Message decrypt bot se aayi hai → forward to main channel
            try:
                # Agar text message hai to copy karo
                if event.message.text:
                    await bot.send_message(main_channel_id, event.message.text, 
                                          parse_mode='markdown' if '```' in event.message.text else None)
                    logging.info(f"📤 Forwarded text from decrypt bot to main channel")
                
                # Agar file hai to forward karo
                elif event.message.document or event.message.media:
                    await bot.forward_messages(main_channel_id, event.message)
                    logging.info(f"📤 Forwarded file from decrypt bot to main channel")
                
                # Delete original message from bot (optional)
                # await event.delete()
                
            except Exception as e:
                logging.error(f"Failed to send to main channel: {e}")

# ============= AUTO SCAN LOOP =============
auto_scan_task = None

async def auto_scan_loop():
    """Har 10 minutes me scan karega"""
    while True:
        await asyncio.sleep(600)  # 10 minutes
        logging.info("Auto scan triggered...")
        await scan_and_forward()

@bot.on(events.NewMessage(pattern='/start_auto'))
async def start_auto(event):
    if event.sender_id != ADMIN_ID:
        return
    global auto_scan_task
    if auto_scan_task and not auto_scan_task.done():
        await event.reply("⚠️ Auto scan already running!")
        return
    auto_scan_task = asyncio.create_task(auto_scan_loop())
    await event.reply("✅ Auto scan started! Scanning every 10 minutes.")

@bot.on(events.NewMessage(pattern='/stop_auto'))
async def stop_auto(event):
    if event.sender_id != ADMIN_ID:
        return
    global auto_scan_task
    if auto_scan_task:
        auto_scan_task.cancel()
        auto_scan_task = None
        await event.reply("✅ Auto scan stopped!")
    else:
        await event.reply("⚠️ Auto scan not running!")

# ============= MAIN =============
async def main():
    await bot.start()
    logging.info("🤖 Bot Started!")
    
    # Send ready message to admin
    try:
        await bot.send_message(ADMIN_ID, "✅ Bot is online! Use /start for commands.")
    except:
        pass
    
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())