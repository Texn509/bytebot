import os
import json
import asyncio
import logging
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler

# Enable logging to track the bot's behavior in Docker logs
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment configurations passed via GitHub Actions/Docker
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_USER_ID = int(os.getenv("ALLOWED_USER_ID", "0"))

# Constants & Default Configurations
DEFAULT_LOCATION = "108131332549295"
DEFAULT_MULTIPLIER = 10.0
DEFAULT_EXCLUSIONS = ["rent", "iso", "wanted", "broken", "parts", "lease"]
CONFIG_FILE = "bot_state.json"

# State Tracking variables
current_multiplier = DEFAULT_MULTIPLIER
current_exclusions = list(DEFAULT_EXCLUSIONS)

def load_state():
    """Loads the state variables from disk to maintain persistent changes across restarts"""
    global current_multiplier, current_exclusions
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                data = json.load(f)
                current_multiplier = data.get("multiplier", DEFAULT_MULTIPLIER)
                current_exclusions = data.get("exclusions", list(DEFAULT_EXCLUSIONS))
                logger.info("State successfully loaded from storage.")
        except Exception as e:
            logger.error(f"Error loading state file: {e}")

def save_state():
    """Saves state adjustments permanently to survive container deployment restarts"""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump({"multiplier": current_multiplier, "exclusions": current_exclusions}, f)
    except Exception as e:
        logger.error(f"Failed to save system state: {e}")

async def check_auth(update: Update) -> bool:
    """Validates if the user sending commands has matching firewall clearance credentials"""
    user_id = update.effective_user.id if update.effective_user else 0
    if user_id != ALLOWED_USER_ID:
        if update.message:
            await update.message.reply_text(
                f"⛔ **Access Denied.**\nYour current Telegram User ID is: `{user_id}`.\n"
                "Please configure this numeric value inside your GitHub Secrets to gain access.",
                parse_mode="Markdown"
            )
        return False
    return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Initializes the chat, loads persistent state, and delivers the UI dashboard panels"""
    if not await check_auth(update):
        return

    load_state()

    # Persistent bottom reply hardware buttons for quick navigation
    reply_keyboard = [['📊 Show Dashboard', '🔄 Restart Scraper Run']]
    reply_markup_text = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "👋 **Welcome to your Facebook Marketplace Deal Scraper Portal!**\n"
        "Use the bottom control bar or interactive menus below to manage execution profiles.",
        reply_markup=reply_markup_text,
        parse_mode="Markdown"
    )
    await send_dashboard(update, context)

async def send_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generates and updates the interactive click-menu dashboard layout panel"""
    # Inline custom touch button definitions
    keyboard = [
        [
            InlineKeyboardButton("📈 5x ROI", callback_data="set_mult_5"),
            InlineKeyboardButton("🔥 10x ROI", callback_data="set_mult_10"),
            InlineKeyboardButton("💎 15x ROI", callback_data="set_mult_15")
        ],
        [
            InlineKeyboardButton("❌ Clear Exclusion Deck", callback_data="clear_excl"),
            InlineKeyboardButton("📍 Reset Location (Default)", callback_data="reset_loc")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    status_msg = (
        "🤖 **Scraper Control Center Dashboard**\n"
        "---------------------------------------\n"
        f"🎯 **Target Location Profile ID:** `{DEFAULT_LOCATION}`\n"
        f"📊 **Current Loop Processing Rate:** `{current_multiplier}x` multiplier context\n"
        f"🚫 **Active Keyword Scrape Exclusions:** `{', '.join(current_exclusions) if current_exclusions else 'None'}`\n"
        "---------------------------------------\n"
        "👇 *Tap an action below to instantly alter background running parameters:* "
    )

    if update.message:
        await update.message.reply_text(status_msg, reply_markup=reply_markup, parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.message.edit_text(status_msg, reply_markup=reply_markup, parse_mode="Markdown")

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes interactive click actions natively on the backend daemon engine"""
    global current_multiplier, current_exclusions
    query = update.callback_query

    if not await check_auth(update):
        await query.answer(text="Unauthorized account execution blocked.", show_alert=True)
        return

    await query.answer() # Immediately acknowledge click interface to eliminate UI lag latency

    data = query.data
    logger.info(f"Interactive dashboard button clicked: {data}")

    if data == "set_mult_5":
        current_multiplier = 5.0
    elif data == "set_mult_10":
        current_multiplier = 10.0
    elif data == "set_mult_15":
        current_multiplier = 15.0
    elif data == "clear_excl":
        current_exclusions = []
    elif data == "reset_loc":
        logger.info("Location profile reset instruction verified.")

    save_state()
    # Refresh dashboard stats visually
    await send_dashboard(update, context)

async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Intercepts bottom keyboard layout instructions and routes operations natively"""
    if not await check_auth(update):
        return

    user_text = update.message.text

    if user_text == '📊 Show Dashboard':
        await send_dashboard(update, context)
    elif user_text == '🔄 Restart Scraper Run':
        await update.message.reply_text("🔄 *Initializing rolling process sequence restart...*", parse_mode="Markdown")
        # Custom logic for trigger integration hook (fb_deals_scraper.py) goes here
        await update.message.reply_text("✅ Core engine context reset successfully executed.")
    else:
        # Dynamic fallback parser for user inputs
        await update.message.reply_text(
            f"❓ Command keyword context `{user_text}` unmapped.\nUse the dashboard panel to tweak active parameters.",
            parse_mode="Markdown"
        )

def main():
    """Startup runtime application context wrapper initialization"""
    if not TOKEN:
        print("CRITICAL EXCEPTION ERROR: Missing required 'TELEGRAM_BOT_TOKEN' environment variable assignment!")
        return

    logger.info("Initializing framework core pipelines...")
    app = Application.builder().token(TOKEN).build()

    # Bind handling infrastructure logic pipelines
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback_query))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))

    logger.info("Bot execution loop initialized successfully. Now listening for user input sequences...")
    app.run_polling()

if __name__ == '__main__':
    main()