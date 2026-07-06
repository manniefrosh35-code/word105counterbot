import os
import sys
import logging
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from telegram.error import TelegramError, NetworkError, TimedOut

# --- Setup logging with more details ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Get the bot token with multiple fallbacks ---
TOKEN = None

# Try to get token from environment variable
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')

# If not found, try alternative environment variable names
if not TOKEN:
    TOKEN = os.environ.get('BOT_TOKEN')
    
if not TOKEN:
    TOKEN = os.environ.get('TELEGRAM_TOKEN')

# If still not found, try reading from .env file (for local development)
if not TOKEN:
    try:
        with open('.env', 'r') as f:
            for line in f:
                if line.startswith('TELEGRAM_BOT_TOKEN='):
                    TOKEN = line.strip().split('=')[1].strip('"\'')
                    break
    except FileNotFoundError:
        pass

# Final check - if no token, show helpful error and exit
if not TOKEN:
    logger.error("❌ No bot token found!")
    logger.error("Please set TELEGRAM_BOT_TOKEN environment variable")
    logger.error("Example: TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIJklmnopQRstUVWXyz")
    sys.exit(1)

logger.info("✅ Bot token found successfully!")

# --- Command: /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_message = (
        "👋 *Welcome to Word Counter Bot!*\n\n"
        "I can help you analyze any text you send me.\n\n"
        "📊 *What I can do:*\n"
        "• Count words\n"
        "• Count characters (with/without spaces)\n"
        "• Count sentences\n"
        "• Count paragraphs\n\n"
        "📝 *Just send me any text and I'll analyze it!*\n\n"
        "You can also use these commands:\n"
        "/stats - Get detailed statistics\n"
        "/help - Show this message again"
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

# --- Command: /help ---
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "📖 *How to use this bot:*\n\n"
        "1️⃣ Send me any text message\n"
        "2️⃣ I'll automatically count:\n"
        "   • Words\n"
        "   • Characters (with spaces)\n"
        "   • Characters (without spaces)\n"
        "   • Sentences\n"
        "   • Paragraphs\n\n"
        "📌 *Commands:*\n"
        "/start - Start the bot\n"
        "/stats - Get detailed stats of last text\n"
        "/help - Show this help message"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

# --- Core function: Count everything ---
def count_text_statistics(text):
    """Analyze text and return all statistics."""
    if not text or not text.strip():
        return None
    
    # Clean the text
    text = text.strip()
    
    # Count words
    words = text.split()
    word_count = len(words)
    
    # Count characters
    char_count_with_spaces = len(text)
    char_count_without_spaces = len(text.replace(' ', ''))
    
    # Count sentences (split by ., !, ?)
    sentence_delimiters = ['.', '!', '?']
    sentence_count = sum(1 for char in text if char in sentence_delimiters)
    
    # If no sentence delimiter found but text has content, count as 1 sentence
    if sentence_count == 0 and len(text.strip()) > 0:
        sentence_count = 1
    
    # Count paragraphs (split by newline)
    paragraphs = [p for p in text.split('\n') if p.strip()]
    paragraph_count = len(paragraphs)
    
    # Count unique words
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
        'char_with_spaces': char_count_with_spaces,
        'char_without_spaces': char_count_without_spaces,
        'sentence_count': sentence_count,
        'paragraph_count': paragraph_count,
        'unique_words': unique_words,
        'avg_word_length': avg_word_length,
        'most_common_word': most_common_word,
        'most_common_count': most_common_count,
        'text_preview': text[:100] + ('...' if len(text) > 100 else '')
    }

# --- Message handler: Analyze any text ---
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        text = update.message.text
        
        # Store the last analyzed text in context for /stats command
        context.user_data['last_text'] = text
        
        # Get statistics
        stats = count_text_statistics(text)
        
        if not stats:
            await update.message.reply_text("❌ Please send some valid text to analyze.")
            return
        
        # Create a beautiful response
        response = (
            f"📊 *Text Analysis Report*\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📝 *Words:* `{stats['word_count']}`\n"
            f"🔤 *Characters (with spaces):* `{stats['char_with_spaces']}`\n"
            f"🔡 *Characters (no spaces):* `{stats['char_without_spaces']}`\n"
            f"📚 *Sentences:* `{stats['sentence_count']}`\n"
            f"📄 *Paragraphs:* `{stats['paragraph_count']}`\n"
            f"🔄 *Unique words:* `{stats['unique_words']}`\n"
            f"📏 *Avg word length:* `{stats['avg_word_length']}` chars\n"
            f"⭐ *Most common word:* `{stats['most_common_word']}` ({stats['most_common_count']} times)\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📎 *Preview:* _{stats['text_preview']}_"
        )
        
        # Send response with an inline button to get even more stats
        keyboard = [[InlineKeyboardButton("📈 More Stats", callback_data='more_stats')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            response, 
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Error in handle_text: {e}")
        await update.message.reply_text("❌ Sorry, something went wrong. Please try again.")

# --- Command: /stats - Show detailed stats of last text ---
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
            f"📏 *Average word length:* {stats['avg_word_length']}\n"
            f"⭐ *Most common word:* {stats['most_common_word']} ({stats['most_common_count']} times)\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📎 *Preview:*\n"
            f"_{stats['text_preview']}_"
        )
        
        await update.message.reply_text(detailed_response, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error in stats_command: {e}")
        await update.message.reply_text("❌ Error fetching statistics. Please try again.")

# --- Callback handler for inline buttons ---
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        
        if query.data == 'example':
            await query.edit_message_text(
                "📝 *Try it now!*\n\n"
                "Just send me any text message and I'll analyze it instantly.\n\n"
                "For example, send me a paragraph, a tweet, or even a whole essay!",
                parse_mode='Markdown'
            )
        
        elif query.data == 'about':
            await query.edit_message_text(
                "ℹ️ *About this bot*\n\n"
                "This is a powerful word counter bot built with Python and the Telegram Bot API.\n\n"
                "✨ *Features:*\n"
                "• Word count\n"
                "• Character count (with/without spaces)\n"
                "• Sentence count\n"
                "• Paragraph count\n"
                "• Unique words analysis\n"
                "• Average word length\n"
                "• Most common word\n\n"
                "🔒 *Privacy:* Your text is only processed temporarily and not stored permanently.",
                parse_mode='Markdown'
            )
        
        elif query.data == 'more_stats':
            await query.edit_message_text(
                "📈 *For more detailed statistics, use the command:*\n"
                "`/stats`\n\n"
                "This will show you additional information about the last text you sent.",
                parse_mode='Markdown'
            )
    except Exception as e:
        logger.error(f"Error in button_callback: {e}")
        await update.effective_message.reply_text("❌ Something went wrong. Please try again.")

# --- Error handler with retry logic ---
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")
    
    # Handle specific errors gracefully
    if isinstance(context.error, (NetworkError, TimedOut)):
        logger.warning("Network error - will retry")
        # Don't send message for network errors, they will retry automatically
        return
    
    if isinstance(context.error, TelegramError):
        logger.error(f"Telegram API error: {context.error}")
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ Sorry, something went wrong with the Telegram API. Please try again later."
            )
        return
    
    # Generic error
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ An unexpected error occurred. Please try again later."
        )

# --- Health check endpoint (optional) ---
async def health_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot is running and healthy!")

# --- Main function with retry logic ---
def main():
    logger.info("🤖 Starting Word Counter Bot...")
    logger.info(f"📊 Bot Token: {TOKEN[:10]}... (hidden for security)")
    
    # Retry logic for connection
    max_retries = 5
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            # Create the application with connection pool settings
            app = ApplicationBuilder() \
                .token(TOKEN) \
                .connect_timeout(30.0) \
                .read_timeout(30.0) \
                .build()
            
            # Add command handlers
            app.add_handler(CommandHandler("start", start))
            app.add_handler(CommandHandler("help", help_command))
            app.add_handler(CommandHandler("stats", stats_command))
            app.add_handler(CommandHandler("health", health_check))
            
            # Add message handler for text messages
            app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
            
            # Add callback handler for inline buttons
            app.add_handler(CallbackQueryHandler(button_callback))
            
            # Add error handler
            app.add_error_handler(error_handler)
            
            # Start the bot using long polling with error handling
            logger.info("✅ Bot is running and waiting for messages...")
            app.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True,
                timeout=60
            )
            
            # If we get here, the bot stopped normally
            break
            
        except (NetworkError, TimedOut) as e:
            retry_count += 1
            logger.warning(f"Connection error (attempt {retry_count}/{max_retries}): {e}")
            if retry_count < max_retries:
                logger.info(f"Retrying in {retry_count * 5} seconds...")
                time.sleep(retry_count * 5)
            else:
                logger.error("Max retries reached. Exiting.")
                sys.exit(1)
                
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            sys.exit(1)

if __name__ == "__main__":
    main()
