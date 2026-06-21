import os
import logging
import threading
import subprocess
import re
import sys
import asyncio
import signal
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# --- Keep Alive Logic ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running 24/7!"

def run_flask():
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)

def keep_alive():
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()

# --- Bot Logic ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = "BOT_TOKE  ADD KARO"
OWNER_ID = APNA CHAT ID DO
PASSWORD = "Flex-Devloper TUMHARE PAPA HE"

# Store running processes: {user_id: [process_info, ...]}
running_scripts = {}
# Store approved users: {user_id: True}
approved_users = {}

def scan_python_dependencies(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        imports = re.findall(r'^(?:from|import)\s+([a-zA-Z0-9_]+)', content, re.MULTILINE)
        return list(set(imports))
    except Exception as e:
        logger.error(f"Error scanning python deps: {e}")
        return []

def scan_js_dependencies(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        requires = re.findall(r'require\([\'"](.+?)[\'"]\)', content)
        imports = re.findall(r'from\s+[\'"](.+?)[\'"]', content)
        return list(set(requires + imports))
    except Exception as e:
        logger.error(f"Error scanning js deps: {e}")
        return []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != OWNER_ID and user_id not in approved_users:
        await update.message.reply_text("🔐 Access Restricted. Please enter the password to use this bot.")
        return

    user = update.effective_user
    welcome_text = (
        f"〽️ Welcome, {user.first_name}...💞!\n\n"
        f"🆔 Your User ID: {user.id}\n"
        f"✳️ Username: @{user.username if user.username else 'Not set'}\n"
        f"🔰 Your Status: 🆓 Free User\n"
        f"📁 Files Uploaded: 0 / 10\n\n"
        f"🤖 Host & run Python (.py) or JS (.js) scripts.\n"
        f"Upload single scripts or .zip archives.\n\n"
        f"👇 Use buttons or type commands."
    )
    
    inline_keyboard = [[InlineKeyboardButton("📢 Updates Channel", url="https://t.me/Aiflex_Devloper")]]
    inline_markup = InlineKeyboardMarkup(inline_keyboard)
    
    reply_keyboard = [
        [KeyboardButton("𝐔𝐏𝐋𝐎𝐀𝐃 𝐅𝐈𝐋𝐄𝐒 👾"), KeyboardButton("📂 𝐂𝐇𝐄𝐀𝐊 𝐅𝐈𝐋𝐄𝐒")],
        [KeyboardButton("⚡ 𝐁𝐎𝐓 𝐒𝐏𝐄𝐄𝐃"), KeyboardButton("📊 Statistics")],
        [KeyboardButton("📩 Send Command"), KeyboardButton("📞 Contact Owner")],
        [KeyboardButton("🛑 𝐒𝐓𝐎𝐏 𝐒𝐂𝐑𝐈𝐏𝐓")]
    ]
    reply_markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    await update.message.reply_text("Options menu activated!", reply_markup=inline_markup)

async def stop_script(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != OWNER_ID and user_id not in approved_users:
        await update.message.reply_text("🔐 Access Restricted. Please enter the password first.")
        return

    scripts = running_scripts.get(user_id, [])
    
    if not scripts:
        await update.message.reply_text("❌ You have no scripts running.")
        return
    
    script_to_stop = None
    if context.args:
        script_to_stop = context.args[0]
    
    if not script_to_stop:
        keyboard = []
        for i, s in enumerate(scripts):
            if s["proc"].poll() is None:
                keyboard.append([InlineKeyboardButton(f"🛑 Stop {s['name']}", callback_data=f"stop_{i}")])
        
        if not keyboard:
            await update.message.reply_text("❌ All your scripts are already stopped.")
            return
            
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Select a script to stop:", reply_markup=reply_markup)
    else:
        found = False
        for i, s in enumerate(scripts):
            if s["name"] == script_to_stop:
                found = True
                if s["proc"].poll() is None:
                    try:
                        # Windows friendly stop command
                        s["proc"].terminate()
                        s["log"].close()
                        await update.message.reply_text(f"✅ Stopped `{script_to_stop}`.")
                    except Exception as e:
                        await update.message.reply_text(f"❌ Error stopping `{script_to_stop}`: {str(e)}")
                else:
                    await update.message.reply_text(f"ℹ️ `{script_to_stop}` is already stopped.")
                break
        if not found:
            await update.message.reply_text(f"❌ Script `{script_to_stop}` not found.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    
    if user_id != OWNER_ID and user_id not in approved_users:
        await query.edit_message_text(text="🔐 Access Restricted. Please enter the password first.")
        return

    if query.data.startswith('stop_'):
        index = int(query.data.split('_')[1])
        scripts = running_scripts.get(user_id, [])
        if 0 <= index < len(scripts):
            script = scripts[index]
            if script["proc"].poll() is None:
                try:
                    # Windows friendly stop command
                    script["proc"].terminate()
                    script["log"].close()
                    await query.edit_message_text(text=f"✅ Stopped `{script['name']}`.")
                except Exception as e:
                    await query.edit_message_text(text=f"❌ Error stopping `{script['name']}`: {str(e)}")
            else:
                await query.edit_message_text(text=f"ℹ️ `{script['name']}` is already stopped.")
        else:
            await query.edit_message_text(text="❌ Script index not found.")

async def install_module(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != OWNER_ID and user_id not in approved_users:
        await update.message.reply_text("🔐 Access Restricted. Please enter the password first.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /install <package_name>")
        return
    package = context.args[0]
    if package.lower() == "telegram":
        package = "python-telegram-bot"
        
    await update.message.reply_text(f"⏳ Installing `{package}`...")
    try:
        process = subprocess.run([sys.executable, "-m", "pip", "install", package, "--no-cache-dir"], capture_output=True, text=True)
        if process.returncode == 0:
            await update.message.reply_text(f"✅ Successfully installed `{package}`!")
        else:
            await update.message.reply_text(f"❌ Failed to install `{package}`:\n`{process.stderr[:500]}`")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    
    if user_id != OWNER_ID and user_id not in approved_users:
        if text == PASSWORD:
            approved_users[user_id] = True
            await update.message.reply_text("✅ Password correct! You are now approved to use the bot. Send /start to begin.")
        else:
            await update.message.reply_text("🔐 Access Restricted. Please enter the correct password.")
        return

    if text == "𝐔𝐏𝐋𝐎𝐀𝐃 𝐅𝐈𝐋𝐄𝐒 👾":
        await update.message.reply_text("📤 Send your Python (`.py`), JS (`.js`), or ZIP (`.zip`) file.")
    elif text == "📂 𝐂𝐇𝐄𝐂𝐊 𝐅𝐈𝐋𝐄𝐒":
        scripts = running_scripts.get(user_id, [])
        if not scripts:
            await update.message.reply_text("📂 You have no scripts running.")
        else:
            status_msg = "📂 Your running scripts:\n"
            for s in scripts:
                status = "Running" if s["proc"].poll() is None else "Stopped"
                status_msg += f"- {s['name']}: {status}\n"
            await update.message.reply_text(status_msg)
    elif text == "⚡ 𝐁𝐎𝐓 𝐒𝐏𝐄𝐄𝐃":
        await update.message.reply_text("⚡ Bot latency: 0.1s")
    elif text == "📊 Statistics":
        total = sum(len(v) for v in running_scripts.values())
        await update.message.reply_text(f"📊 Total active scripts: {total}")
    elif text == "📩 Send Command":
        await update.message.reply_text("📩 Feature coming soon.")
    elif text == "📞 Contact Owner":
        await update.message.reply_text("📞 Contact: @icookclans")
    elif text == "🛑 𝐒𝐓𝐎𝐏 𝐒𝐂𝐑𝐈𝐏𝐓":
        await stop_script(update, context)
    elif update.message.document:
        doc = update.message.document
        file_name = doc.file_name
        os.makedirs("downloads", exist_ok=True)
        file_path = os.path.join("downloads", file_name)
        
        msg = await update.message.reply_text(f"⏳ Processing `{file_name}`... (Heavy file support active)")
        
        try:
            new_file = await context.bot.get_file(doc.file_id)
            await new_file.download_to_drive(file_path)
            
            await msg.edit_text(f"🔍 Scanning `{file_name}` for dependencies...")
            deps = []
            if file_name.endswith('.py'):
                deps = scan_python_dependencies(file_path)
                cmd = [sys.executable, file_path]
                pkg_mgr = "pip"
            elif file_name.endswith('.js'):
                deps = scan_js_dependencies(file_path)
                cmd = ["node", "--max-old-space-size=512", file_path]
                pkg_mgr = "npm"
            elif file_name.endswith('.zip'):
                await msg.edit_text("📦 ZIP detected. Extraction logic coming soon.")
                return
            else:
                await msg.edit_text("❌ Unsupported file type. Please send .py or .js.")
                return

            if deps:
                await msg.edit_text(f"📦 Installing {len(deps)} dependencies...")
                for dep in deps:
                    if dep == "telegram" and pkg_mgr == "pip":
                        dep = "python-telegram-bot"
                    try:
                        subprocess.run([sys.executable, "-m", "pip", "install", dep, "--no-cache-dir"], capture_output=True, timeout=60)
                    except Exception as e:
                        logger.error(f"Failed to install {dep}: {e}")
            
                        await msg.edit_text(f"🚀 Launching `{file_name}`...")
            
            # 1. Force UTF-8 Environment create karein
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            env["PYTHONLEGACYWINDOWSSTDIO"] = "utf-8"

            # 2. Log file ko UTF-8 me open karein (Ye zaroori hai Emojis ke liye)
            log_file = open(f"{file_path}.log", "w", encoding="utf-8", errors="ignore")
            
            # 3. Process start karte waqt 'env' aur 'encoding' pass karein
            proc = subprocess.Popen(
                cmd, 
                stdout=log_file, 
                stderr=log_file, 
                text=True, 
                start_new_session=True,
                env=env,              # Environment fix
                encoding='utf-8',     # Process encoding fix
                errors='replace'      # Agar koi corrupt character ho to crash na ho
            )
            
            if user_id not in running_scripts:

                running_scripts[user_id] = []
            running_scripts[user_id].append({"name": file_name, "proc": proc, "log": log_file})
            
            await asyncio.sleep(4)
            if proc.poll() is not None:
                log_file.close()
                # Encoding fix yahan bhi zaroori hai
                with open(f"{file_path}.log", "r", encoding="utf-8", errors="ignore") as f:

                    error_log = f.read()[-500:]
                await msg.edit_text(f"❌ `{file_name}` failed. Error:\n`{error_log}`")
            else:
                await msg.edit_text(f"✅ `{file_name}` is now hosted and running 24/7.")
                
        except Exception as e:
            await msg.edit_text(f"❌ Error handling file: {str(e)}")
    else:
        await update.message.reply_text("Please use the menu buttons or send a file to host.")

if __name__ == '__main__':
    if not TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not found. Please set the TELEGRAM_BOT_TOKEN secret.")
        keep_alive()
        import time
        while True:
            time.sleep(60)
    else:
        keep_alive()
        application = ApplicationBuilder().token(TOKEN).connect_timeout(60).read_timeout(60).write_timeout(60).build()
        application.add_handler(CommandHandler('start', start))
        application.add_handler(CommandHandler('install', install_module))
        application.add_handler(CommandHandler('stop', stop_script))
        application.add_handler(CallbackQueryHandler(button_handler))
        application.add_handler(MessageHandler(filters.Document.ALL | filters.TEXT & (~filters.COMMAND), handle_message))
        print("Flex-Devloper KA BOT START HO GEYA HE AB USE KARO 🤭")
        application.run_polling()
