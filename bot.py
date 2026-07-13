import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from PIL import Image
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from flask import Flask
import threading

# Create Flask app for Render health checks
app = Flask(__name__)

@app.route('/')
@app.route('/health')
def health_check():
    return "Bot is running!", 200

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get token from environment variable (Render will set this)
BOT_TOKEN = os.getenv('TELEGRAM_TOKEN') or os.getenv('BOT_TOKEN')

if not BOT_TOKEN:
    raise ValueError("❌ No bot token found! Set TELEGRAM_TOKEN in Render environment.")

# --- Your bot functions go here ---
# (Copy all your existing bot functions: start, help_command, 
# handle_images, convert_images_to_pdf, error_handler)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_message = """
    👋 Hello! I'm an Image to PDF Converter Bot!
    
    📸 Send me an image (JPG, PNG, JPEG) and I'll convert it to PDF.
    
    📌 You can also send multiple images together and I'll combine them.
    """
    await update.message.reply_text(welcome_message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
    🤖 How to use this bot:
    
    1. Send me one or more images
    2. I'll convert them to PDF
    3. I'll send the PDF back to you
    
    Supported formats: JPG, JPEG, PNG
    """
    await update.message.reply_text(help_text)

# ... (copy your handle_images and convert_images_to_pdf functions here) ...

# Function to run the bot in a separate thread
def run_bot():
    """Start the Telegram bot"""
    try:
        application = Application.builder().token(BOT_TOKEN).build()
        
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(MessageHandler(
            filters.PHOTO | filters.Document.IMAGE, 
            handle_images
        ))
        application.add_error_handler(error_handler)
        
        print("🤖 Bot is starting...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        print(f"❌ Bot error: {e}")

if __name__ == '__main__':
    # Start the bot in a background thread
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    # Run Flask to keep Render happy
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)