import os
import logging
import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.WARNING
)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

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
    await analyze_message(update, text, force_check=True)


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


async def call_backend_analyze_image(image_bytes: bytes) -> dict:
    """Call the backend API to analyze image for misinformation."""
    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(
                f"{BACKEND_URL}/analyze/image",
                files={"file": ("image.jpg", image_bytes, "image/jpeg")}
            )
            response.raise_for_status()
            return response.json()
    except httpx.TimeoutException:
        logger.error("Backend image request timed out")
        return None
    except Exception as e:
        logger.error(f"Error calling backend for image: {e}")
        return None


async def analyze_message(update: Update, text: str, force_check: bool = False) -> None:
    """Analyze text using the backend API."""
    # Send typing indicator
    await update.message.chat.send_action("typing")
    
    # Call backend API
    result = await call_backend_analyze(text)
    
    if result is None:
        await update.message.reply_text(
            "❌ **Error**\n\nCould not connect to the analysis backend. Please try again later.",
            parse_mode="Markdown",
            reply_to_message_id=update.message.message_id
        )
        return
    
    # If not news and not a forced check, silently ignore
    is_news = result.get("is_news", True)
    if not is_news and not force_check:
        # Don't respond to non-news messages
        return
    
    is_misinfo = result.get("is_misinformation", False)
    confidence = result.get("confidence", 0)
    summary = result.get("summary", "")
    evidence = result.get("evidence", [])
    sources = result.get("sources_checked", [])
    recommendation = result.get("recommendation", "")
    
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
    
    if summary:
        response += f"\n**Summary:**\n{summary}\n"
    
    if evidence and len(evidence) > 0:
        response += "\n**Evidence:**\n"
        for e in evidence[:3]:  # Limit to 3 items
            response += f"• {e}\n"
    
    if sources and len(sources) > 0:
        response += "\n**Sources:**\n"
        for s in sources[:3]:  # Limit to 3 items
            # If it's a URL, make it clickable
            if s.startswith("http"):
                response += f"• {s}\n"
            else:
                response += f"• {s}\n"
    
    if recommendation:
        response += f"\n**Recommendation:**\n{recommendation}\n"
    
    response += "\n_Always verify important news from multiple credible sources._"
    
    await update.message.reply_text(
        response,
        parse_mode="Markdown",
        reply_to_message_id=update.message.message_id
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming text messages."""
    text = update.message.text
    
    if not text or len(text.strip()) < 10:
        return  # Ignore very short messages
    
    await analyze_message(update, text)


async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming images."""
    # Send typing indicator
    await update.message.chat.send_action("typing")
    
    try:
        # Get the largest photo size
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        image_bytes = await file.download_as_bytearray()
        
        # Call backend
        result = await call_backend_analyze_image(bytes(image_bytes))
        
        if result is None:
            await update.message.reply_text(
                "❌ **Error**\n\nCould not analyze the image. Please try again later.",
                parse_mode="Markdown",
                reply_to_message_id=update.message.message_id
            )
            return
        
        # Format response
        is_misinfo = result.get("is_misinformation", False)
        confidence = result.get("confidence", 0)
        summary = result.get("summary", "")
        extracted_text = result.get("extracted_text", "")
        image_desc = result.get("image_description", "")
        recommendation = result.get("recommendation", "")
        
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
        
        if summary:
            response += f"\n**Summary:**\n{summary}\n"
        
        if extracted_text and extracted_text != "No text found":
            text_preview = extracted_text[:200] + "..." if len(extracted_text) > 200 else extracted_text
            response += f"\n**Text in Image:**\n_{text_preview}_\n"
        
        if image_desc:
            response += f"\n**Image Description:**\n{image_desc}\n"
        
        if recommendation:
            response += f"\n**Recommendation:**\n{recommendation}\n"
        
        response += "\n_Always verify important news from multiple credible sources._"
        
        await update.message.reply_text(
            response,
            parse_mode="Markdown",
            reply_to_message_id=update.message.message_id
        )
        
    except Exception as e:
        logger.error(f"Error handling image: {e}")
        await update.message.reply_text(
            "❌ **Error**\n\nFailed to process the image. Please try again.",
            parse_mode="Markdown"
        )


def main() -> None:
    """Start the bot."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN not found in environment variables!")
        return
    
    print(f"🤖 Starting Aletheia Telegram Bot...")
    print(f"📡 Backend URL: {BACKEND_URL}")
    
    # Create the Application
    application = Application.builder().token(token).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("check", check_command))
    application.add_handler(MessageHandler(filters.PHOTO, handle_image))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Run the bot
    print("✅ Bot is running! Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
