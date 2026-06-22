import os
import logging
import threading
import subprocess
import re
import sys
import asyncio
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# --- Flask Web Server ---
app = Flask(__name__)

# Render apna port khud deta hai, warna 5000 use hoga
PORT = int(os.environ.get('PORT', 5000))

@app.route('/')
def home():
    return "Bot is running 24/7 on Render!"

# Ye route Telegram ka webhook hit karega
@app.route('/webhook', methods=['POST'])
def webhook():
    if request.method == 'POST':
        update = Update.de_json(request.get_json(force=True), bot_app.bot)
        asyncio.run(bot_app.process_update(update))
        return 'OK', 200

# --- Bot Logic ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- YAHAN APNA TOKEN AUR ID DALO ---
TOKEN = "8901541112:AAERoiZbxU3kwNtnwR_wcRxXDfhEJYwQs-4" 
OWNER_ID = 754309254 # Apni chat id yahan number me dalo
PASSWORD = "dk1724890"

running_scripts = {}
approved_users = {}

def scan_python_dependencies(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        imports = re.findall(r'^(?:from|import)\s+([a-zA-Z0-9_]+)', content, re.MULTILINE)
        return list(set(imports))
    except Exception as e:
        return []

def scan_js_dependencies(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        requires = re.findall(r'require\([\'"](.+?)[\'"]\)', content)
        imports = re.findall(r'from\s+[\'"](.+?)[\'"]', content)
        return list(set(requires + imports))
    except Exception as e:
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
        f"🔰 Your Status: 🆓 Free User\n\n"
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
        await update.message.reply_text("🔐 Access Restricted.")
        return

    scripts = running_scripts.get(user_id, [])
    if not scripts:
        await update.message.reply_text("❌ You have no scripts running.")
        return
    
    if context.args:
        script_to_stop = context.args[0]
        for s in scripts:
            if s["name"] == script_to_stop and s["proc"].poll() is None:
                s["proc"].terminate()
                s["log"].close()
                await update.message.reply_text(f"✅ Stopped `{script_to_stop}`.")
                return
        await update.message.reply_text(f"❌ Script not found or already stopped.")
    else:
        keyboard = []
        for i, s in enumerate(scripts):
            if s["proc"].poll() is None:
                keyboard.append([InlineKeyboardButton(f"🛑 Stop {s['name']}", callback_data=f"stop_{i}")])
        if keyboard:
            await update.message.reply_text("Select a script to stop:", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.message.reply_text("ℹ️ No active scripts running.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    if user_id not in approved_users and user_id != OWNER_ID:
        await query.edit_message_text(text="🔐 Access Restricted.")
        return

    if query.data.startswith('stop_'):
        index = int(query.data.split('_')[1])
        scripts = running_scripts.get(user_id, [])
        if 0 <= index < len(scripts):
            script = scripts[index]
            if script["proc"].poll() is None:
                script["proc"].terminate()
                script["log"].close()
                await query.edit_message_text(text=f"✅ Stopped `{script['name']}`.")

async def install_module(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != OWNER_ID and user_id not in approved_users: return

    if not context.args:
        await update.message.reply_text("Usage: /install <package_name>")
        return
    package = context.args[0]
    if package.lower() == "telegram": package = "python-telegram-bot"
        
    await update.message.reply_text(f"⏳ Installing `{package}`...")
    process = subprocess.run([sys.executable, "-m", "pip", "install", package, "--no-cache-dir"], capture_output=True, text=True)
    if process.returncode == 0:
        await update.message.reply_text(f"✅ Successfully installed `{package}`!")
    else:
        await update.message.reply_text(f"❌ Failed:\n`{process.stderr[:500]}`")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    
    if user_id != OWNER_ID and user_id not in approved_users:
        if text == PASSWORD:
            approved_users[user_id] = True
            await update.message.reply_text("✅ Password correct! Send /start to begin.")
        else:
            await update.message.reply_text("🔐 Wrong password.")
        return

    if text == "𝐔𝐏𝐋𝐎𝐀𝐃 𝐅𝐈𝐋𝐄𝐒 👾":
        await update.message.reply_text("📤 Send your Python (`.py`) or JS (`.js`) file.")
    elif text == "📂 𝐂𝐇𝐄𝐀𝐊 𝐅𝐈𝐋𝐄𝐒":
        scripts = running_scripts.get(user_id, [])
        if not scripts:
            await update.message.reply_text("📂 No scripts running.")
        else:
            status_msg = "📂 Running scripts:\n"
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
        
        msg = await update.message.reply_text(f"⏳ Processing `{file_name}`...")
        
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
            else:
                await msg.edit_text("❌ Unsupported file type.")
                return

            if deps and pkg_mgr == "pip":
                await msg.edit_text(f"📦 Installing {len(deps)} dependencies...")
                for dep in deps:
                    if dep == "telegram": dep = "python-telegram-bot"
                    subprocess.run([sys.executable, "-m", "pip", "install", dep, "--no-cache-dir"], capture_output=True, timeout=60)
            
            await msg.edit_text(f"🚀 Launching `{file_name}`...")
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            log_file = open(f"{file_path}.log", "w", encoding="utf-8", errors="ignore")
            
            proc = subprocess.Popen(cmd, stdout=log_file, stderr=log_file, text=True, start_new_session=True, env=env, encoding='utf-8', errors='replace')
            
            if user_id not in running_scripts:
                running_scripts[user_id] = []
            running_scripts[user_id].append({"name": file_name, "proc": proc, "log": log_file})
            
            await asyncio.sleep(4)
            if proc.poll() is not None:
                log_file.close()
                with open(f"{file_path}.log", "r", encoding="utf-8", errors="ignore") as f:
                    error_log = f.read()[-500:]
                await msg.edit_text(f"❌ `{file_name}` failed. Error:\n`{error_log}`")
            else:
                await msg.edit_text(f"✅ `{file_name}` is now hosted and running 24/7.")
        except Exception as e:
            await msg.edit_text(f"❌ Error: {str(e)}")

# --- Main Execution ---
if __name__ == '__main__':
    if not TOKEN or TOKEN == "BOT_TOKEN_ADD_KARO":
        print("Error: TOKEN not set!")
    else:
        # Pehle Bot application banao
        bot_app = ApplicationBuilder().token(TOKEN).connect_timeout(60).read_timeout(60).write_timeout(60).build()
        
        # Handlers add karo
        bot_app.add_handler(CommandHandler('start', start))
        bot_app.add_handler(CommandHandler('install', install_module))
        bot_app.add_handler(CommandHandler('stop', stop_script))
        bot_app.add_handler(CallbackQueryHandler(button_handler))
        bot_app.add_handler(MessageHandler(filters.Document.ALL | filters.TEXT & (~filters.COMMAND), handle_message))

        # Webhook set karne ka function
        async def setup_webhook():
            # RENDER ME JO URL BANEGA WO YAHAN AAYEGA (https://xyz.onrender.com)
            render_url = os.environ.get('RENDER_EXTERNAL_URL')
            if render_url:
                webhook_url = f"{render_url}/webhook"
                await bot_app.bot.set_webhook(webhook_url)
                print(f"Webhook set to: {webhook_url}")
            else:
                print("Running locally, skipping webhook.")

        # Webhook setup run karo
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(setup_webhook())
        
        # Ab Flask server chalao
        print("Flex-Devloper KA BOT START HO GEYA HE AB USE KARO 🤭")
        app.run(host='0.0.0.0', port=PORT)
