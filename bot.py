#!/usr/bin/env python3
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
import sys

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

# Get token from environment variable
BOT_TOKEN = os.getenv('TELEGRAM_TOKEN')

if not BOT_TOKEN:
    print("❌ No bot token found! Set TELEGRAM_TOKEN in Render environment.")
    sys.exit(1)

print(f"✅ Token found: {BOT_TOKEN[:10]}...")

# --- BOT FUNCTIONS ---

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

async def handle_images(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming images"""
    try:
        if not update.message.photo and not update.message.document:
            await update.message.reply_text("⚠️ Please send an image file (JPG, PNG, JPEG)")
            return

        processing_msg = await update.message.reply_text("🔄 Converting your image(s) to PDF...")
        
        images = []
        
        if update.message.photo:
            photo = update.message.photo[-1]
            file = await context.bot.get_file(photo.file_id)
            image_bytes = await file.download_as_bytearray()
            img = Image.open(io.BytesIO(image_bytes))
            images.append(img)
            logger.info(f"Loaded photo: {img.size}")
        
        elif update.message.document:
            doc = update.message.document
            if doc.mime_type and doc.mime_type.startswith('image/'):
                file = await context.bot.get_file(doc.file_id)
                image_bytes = await file.download_as_bytearray()
                img = Image.open(io.BytesIO(image_bytes))
                images.append(img)
                logger.info(f"Loaded document: {img.size}")
            else:
                await processing_msg.edit_text("⚠️ Please send a valid image file")
                return
        
        if not images:
            await processing_msg.edit_text("❌ No valid images found.")
            return
        
        pdf_bytes = await convert_images_to_pdf(images)
        
        await processing_msg.edit_text("✅ Converting complete! Sending your PDF...")
        
        await update.message.reply_document(
            document=pdf_bytes,
            filename=f"converted_{len(images)}_image(s).pdf",
            caption=f"📄 Here's your PDF with {len(images)} image(s)!"
        )
        
        await processing_msg.delete()
        
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text(f"❌ Sorry, an error occurred: {str(e)}")

async def convert_images_to_pdf(images):
    """Convert a list of PIL Images to PDF bytes"""
    pdf_buffer = io.BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=A4)
    
    for img in images:
        if img.mode in ('RGBA', 'LA', 'P'):
            img = img.convert('RGB')
        
        temp_img = io.BytesIO()
        img.save(temp_img, format='JPEG', quality=95)
        temp_img.seek(0)
        
        img_reader = ImageReader(temp_img)
        img_width, img_height = img.size
        a4_width, a4_height = A4
        
        scale_x = a4_width / img_width
        scale_y = a4_height / img_height
        scale = min(scale_x, scale_y) * 0.9
        
        new_width = img_width * scale
        new_height = img_height * scale
        
        x = (a4_width - new_width) / 2
        y = (a4_height - new_height) / 2
        
        c.drawImage(img_reader, x, y, width=new_width, height=new_height)
        c.showPage()
    
    c.save()
    pdf_bytes = pdf_buffer.getvalue()
    pdf_buffer.close()
    return io.BytesIO(pdf_bytes)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")
    if update and update.message:
        await update.message.reply_text("❌ Something went wrong. Please try again.")

# Function to run the bot in a separate thread
def run_bot():
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
        print("✅ Bot is running!")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        print(f"❌ Bot error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    # Start the bot in a background thread
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    # Run Flask to keep Render happy
    port = int(os.environ.get('PORT', 5000))
    print(f"🌐 Starting web server on port {port}...")
    app.run(host='0.0.0.0', port=port)
