import os
import sys
import logging
import time
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from telegram.error import TelegramError, NetworkError, TimedOut

# --- Setup logging ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- TOKEN DETECTION SYSTEM (Multi-layered) ---
def get_bot_token():
    """Try multiple methods to find the bot token"""
    
    # Method 1: Check environment variables (Railway uses this)
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if token:
        logger.info("✅ Token found in environment variable TELEGRAM_BOT_TOKEN")
        return token
    
    # Method 2: Try alternative environment variable names
    alt_names = ['BOT_TOKEN', 'TELEGRAM_TOKEN', 'TOKEN']
    for name in alt_names:
        token = os.environ.get(name)
        if token:
            logger.info(f"✅ Token found in environment variable {name}")
            return token
    
    # Method 3: Try to read from .env file (local development)
    try:
        env_file = Path('.env')
        if env_file.exists():
            with open('.env', 'r') as f:
                for line in f:
                    if line.strip() and not line.startswith('#'):
                        if '=' in line:
                            key, value = line.strip().split('=', 1)
                            if key.upper() in ['TELEGRAM_BOT_TOKEN', 'BOT_TOKEN', 'TELEGRAM_TOKEN']:
                                logger.info("✅ Token found in .env file")
                                return value
    except Exception as e:
        logger.debug(f"Error reading .env file: {e}")
    
    # Method 4: Check for token in a token.txt file
    try:
        token_file = Path('token.txt')
        if token_file.exists():
            with open('token.txt', 'r') as f:
                token = f.read().strip()
                if token:
                    logger.info("✅ Token found in token.txt file")
                    return token
    except Exception as e:
        logger.debug(f"Error reading token.txt: {e}")
    
    # Method 5: Hardcoded token (FOR TESTING ONLY - REMOVE IN PRODUCTION)
    # If you want to hardcode your token for testing, uncomment the line below
    # return "YOUR_TEST_TOKEN_HERE"
    
    # If no token found, show helpful error and create a mock token for debugging
    logger.error("=" * 60)
    logger.error("❌ NO BOT TOKEN FOUND!")
    logger.error("=" * 60)
    logger.error("Please set your bot token using ONE of these methods:")
    logger.error("")
    logger.error("1. Environment Variable (Recommended for Railway):")
    logger.error("   In Railway dashboard, add variable:")
    logger.error("   Key: TELEGRAM_BOT_TOKEN")
    logger.error("   Value: YOUR_BOT_TOKEN_FROM_BOTFATHER")
    logger.error("")
    logger.error("2. .env file (Local development):")
    logger.error("   Create a .env file with:")
    logger.error("   TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN_FROM_BOTFATHER")
    logger.error("")
    logger.error("3. token.txt file:")
    logger.error("   Create token.txt with just your token inside")
    logger.error("")
    logger.error("=" * 60)
    logger.error("")
    logger.error("To get a token: Talk to @BotFather on Telegram")
    logger.error("Send /newbot and follow the instructions")
    
    return None

# --- Get the token ---
TOKEN = get_bot_token()

# If no token, create a mock bot for testing (will show as offline)
if not TOKEN:
    logger.error("❌ No token available. Bot will not start.")
    logger.info("💡 Tip: Add TELEGRAM_BOT_TOKEN to your Railway variables!")
    sys.exit(1)

# --- Bot Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_message = (
        "👋 *Welcome to Word Counter Bot!*\n\n"
        "I can help you analyze any text you send me.\n\n"
        "📊 *What I can do:*\n"
        "• Count words\n"
        "• Count characters (with/without spaces)\n"
        "• Count sentences\n"
        "• Count paragraphs\n"
        "• Find most common word\n\n"
        "📝 *Just send me any text and I'll analyze it!*"
    )
    
    keyboard = [
        [InlineKeyboardButton("📊 Try Me!", callback_data='example')],
        [InlineKeyboardButton("ℹ️ About", callback_data='about')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_message, 
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "📖 *How to use this bot:*\n\n"
        "1️⃣ Send me any text message\n"
        "2️⃣ I'll automatically count everything!\n\n"
        "📌 *Commands:*\n"
        "/start - Start the bot\n"
        "/stats - Detailed stats of last text\n"
        "/help - Show this help"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

def count_text_statistics(text):
    """Analyze text and return all statistics."""
    if not text or not text.strip():
        return None
    
    text = text.strip()
    words = text.split()
    word_count = len(words)
    
    char_with_spaces = len(text)
    char_without_spaces = len(text.replace(' ', ''))
    
    # Count sentences
    sentence_count = sum(1 for char in text if char in '.!?')
    if sentence_count == 0 and len(text.strip()) > 0:
        sentence_count = 1
    
    # Count paragraphs
    paragraphs = [p for p in text.split('\n') if p.strip()]
    paragraph_count = len(paragraphs)
    
    # Unique words
    unique_words = len(set(word.lower() for word in words))
    
    # Average word length
    avg_word_length = round(sum(len(word) for word in words) / word_count, 2) if word_count > 0 else 0
    
    # Most common word
    from collections import Counter
    word_freq = Counter(word.lower() for word in words)
    most_common = word_freq.most_common(1)
    most_common_word = most_common[0][0] if most_common else "N/A"
    most_common_count = most_common[0][1] if most_common else 0
    
    return {
        'word_count': word_count,
        'char_with_spaces': char_with_spaces,
        'char_without_spaces': char_without_spaces,
        'sentence_count': sentence_count,
        'paragraph_count': paragraph_count,
        'unique_words': unique_words,
        'avg_word_length': avg_word_length,
        'most_common_word': most_common_word,
        'most_common_count': most_common_count,
        'text_preview': text[:100] + ('...' if len(text) > 100 else '')
    }

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        text = update.message.text
        context.user_data['last_text'] = text
        
        stats = count_text_statistics(text)
        
        if not stats:
            await update.message.reply_text("❌ Please send some valid text.")
            return
        
        response = (
            f"📊 *Text Analysis*\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📝 *Words:* `{stats['word_count']}`\n"
            f"🔤 *Characters (with spaces):* `{stats['char_with_spaces']}`\n"
            f"🔡 *Characters (no spaces):* `{stats['char_without_spaces']}`\n"
            f"📚 *Sentences:* `{stats['sentence_count']}`\n"
            f"📄 *Paragraphs:* `{stats['paragraph_count']}`\n"
            f"🔄 *Unique words:* `{stats['unique_words']}`\n"
            f"⭐ *Most common:* `{stats['most_common_word']}` ({stats['most_common_count']}x)\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📎 _{stats['text_preview']}_"
        )
        
        keyboard = [[InlineKeyboardButton("📈 More Stats", callback_data='more_stats')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            response, 
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Error in handle_text: {e}")
        await update.message.reply_text("❌ Something went wrong. Please try again.")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        last_text = context.user_data.get('last_text')
        
        if not last_text:
            await update.message.reply_text(
                "❌ I don't have any text to analyze yet.\n"
                "Send me some text first!"
            )
            return
        
        stats = count_text_statistics(last_text)
        
        if not stats:
            await update.message.reply_text("❌ Error analyzing the text.")
            return
        
        detailed_response = (
            f"📈 *Detailed Statistics*\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📝 *Total words:* {stats['word_count']}\n"
            f"🔤 *Characters (with spaces):* {stats['char_with_spaces']}\n"
            f"🔡 *Characters (without spaces):* {stats['char_without_spaces']}\n"
            f"📚 *Total sentences:* {stats['sentence_count']}\n"
            f"📄 *Total paragraphs:* {stats['paragraph_count']}\n"
            f"🔄 *Unique words:* {stats['unique_words']}\n"
            f"📏 *Avg word length:* {stats['avg_word_length']}\n"
            f"⭐ *Most common word:* {stats['most_common_word']} ({stats['most_common_count']} times)\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📎 _{stats['text_preview']}_"
        )
        
        await update.message.reply_text(detailed_response, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error in stats_command: {e}")
        await update.message.reply_text("❌ Error fetching statistics.")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        
        if query.data == 'example':
            await query.edit_message_text(
                "📝 *Try it now!*\n\n"
                "Just send me any text message and I'll analyze it instantly.\n\n"
                "For example: send a paragraph, a tweet, or an entire essay!",
                parse_mode='Markdown'
            )
        elif query.data == 'about':
            await query.edit_message_text(
                "ℹ️ *About this bot*\n\n"
                "A powerful word counter bot built with Python and the Telegram Bot API.\n\n"
                "✨ *Features:*\n"
                "• Word count\n"
                "• Character count\n"
                "• Sentence & paragraph count\n"
                "• Unique words analysis\n"
                "• Most common word\n\n"
                "🔒 *Privacy:* Your text is processed temporarily and not stored.",
                parse_mode='Markdown'
            )
        elif query.data == 'more_stats':
            await query.edit_message_text(
                "📈 *For more detailed statistics, use:*\n"
                "`/stats`\n\n"
                "This shows additional info about the last text you sent.",
                parse_mode='Markdown'
            )
    except Exception as e:
        logger.error(f"Error in button_callback: {e}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")
    
    if isinstance(context.error, (NetworkError, TimedOut)):
        logger.warning("Network error - will retry automatically")
        return
    
    if isinstance(context.error, TelegramError):
        logger.error(f"Telegram API error: {context.error}")
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ Telegram API error. Please try again later."
            )
        return
    
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ An unexpected error occurred. Please try again."
        )

# --- Main Function with Auto-Retry ---
def main():
    logger.info("=" * 60)
    logger.info("🤖 Word Counter Bot Starting...")
    logger.info("=" * 60)
    
    # Show token info (hide most of it for security)
    token_preview = TOKEN[:15] + "..." if len(TOKEN) > 15 else TOKEN
    logger.info(f"🔑 Using token: {token_preview}")
    logger.info("📡 Connecting to Telegram...")
    
    # Retry logic for connection issues
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            # Build the application with timeout settings
            app = ApplicationBuilder() \
                .token(TOKEN) \
                .connect_timeout(30.0) \
                .read_timeout(30.0) \
                .build()
            
            # Add handlers
            app.add_handler(CommandHandler("start", start))
            app.add_handler(CommandHandler("help", help_command))
            app.add_handler(CommandHandler("stats", stats_command))
            app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
            app.add_handler(CallbackQueryHandler(button_callback))
            app.add_error_handler(error_handler)
            
            # Start the bot
            logger.info("✅ Bot is running and waiting for messages...")
            logger.info("=" * 60)
            
            app.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True,
                timeout=60
            )
            
            # If we get here, bot stopped normally
            break
            
        except (NetworkError, TimedOut) as e:
            retry_count += 1
            logger.warning(f"⚠️ Connection error (attempt {retry_count}/{max_retries}): {e}")
            if retry_count < max_retries:
                wait_time = retry_count * 5
                logger.info(f"⏳ Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                logger.error("❌ Max retries reached. Exiting.")
                sys.exit(1)
                
        except Exception as e:
            logger.error(f"❌ Fatal error: {e}")
            logger.error("Bot will restart automatically (Railway auto-restart)")
            sys.exit(1)

if __name__ == "__main__":
    main()
