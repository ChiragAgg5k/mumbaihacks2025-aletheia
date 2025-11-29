import os
import asyncio
import logging
import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Backend API URL
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    welcome_message = """👋 Welcome to Aletheia - Your Fake News Detection Bot!

I analyze messages to help you identify potential misinformation.

**How I work:**
1. Send me any message or forward news content
2. I'll first check if it's news-related
3. If it is news, I'll analyze it for potential misinformation

**Commands:**
/start - Show this welcome message
/help - Get help on using the bot
/check <text> - Manually check specific text

Stay informed, stay vigilant! 🔍"""
    await update.message.reply_text(welcome_message, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    help_text = """🔍 **Aletheia Bot Help**

**Automatic Detection:**
Simply send or forward any message, and I'll automatically:
- Detect if it's news content
- Analyze it for misinformation if it is

**Manual Check:**
Use `/check <your text>` to force-check any text

**Tips:**
- Forward suspicious WhatsApp/social media messages
- Share news article text for verification
- I work best with complete news content

**Note:** I use AI analysis and may not always be 100% accurate. Always verify important news from multiple credible sources."""
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Force check text provided with /check command."""
    if not context.args:
        await update.message.reply_text("Please provide text to check. Usage: `/check <text>`", parse_mode="Markdown")
        return
    
    text = " ".join(context.args)
    await analyze_message(update, text)


async def call_backend_analyze(text: str) -> dict:
    """Call the backend API to analyze text for misinformation."""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{BACKEND_URL}/analyze/text",
                json={"text": text}
            )
            response.raise_for_status()
            return response.json()
    except httpx.TimeoutException:
        logger.error("Backend request timed out")
        return None
    except Exception as e:
        logger.error(f"Error calling backend: {e}")
        return None


async def analyze_message(update: Update, text: str) -> None:
    """Analyze text using the backend API."""
    # Send typing indicator
    await update.message.chat.send_action("typing")
    
    # Call backend API
    result = await call_backend_analyze(text)
    
    if result is None:
        await update.message.reply_text(
            "❌ **Error**\n\nCould not connect to the analysis backend. Please try again later.",
            parse_mode="Markdown"
        )
        return
    
    is_misinfo = result.get("is_misinformation", False)
    confidence = result.get("confidence", 0)
    
    # Build response
    if is_misinfo:
        emoji = "🚨" if confidence > 0.7 else "⚠️"
        status = "LIKELY MISINFORMATION" if confidence > 0.7 else "POTENTIALLY MISLEADING"
    else:
        emoji = "✅"
        status = "APPEARS CREDIBLE"
    
    confidence_bar = "█" * int(confidence * 10) + "░" * (10 - int(confidence * 10))
    
    response = f"""{emoji} **{status}**

**Confidence:** [{confidence_bar}] {confidence:.0%}
"""
    
    response += "\n_Remember: Always verify important news from multiple credible sources._"
    
    await update.message.reply_text(response, parse_mode="Markdown")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming messages."""
    text = update.message.text
    
    if not text or len(text.strip()) < 10:
        return  # Ignore very short messages
    
    await analyze_message(update, text)


async def main() -> None:
    """Start the bot."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not found in environment variables!")
        return
    
    # Create the Application
    application = Application.builder().token(token).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("check", check_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Initialize and run the bot
    logger.info("Starting Aletheia Telegram Bot...")
    async with application:
        await application.initialize()
        await application.start()
        await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        
        # Keep running until interrupted
        logger.info("Bot is running. Press Ctrl+C to stop.")
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
        finally:
            await application.updater.stop()
            await application.stop()
            await application.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
