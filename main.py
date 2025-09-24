import logging
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.storage.memory import MemoryStorage
import os
from dotenv import load_dotenv

from commands import setup_commands
from linkdetector import setup_link_detector
from joinremover import setup_join_remover
from admin import setup_admin
from database import db

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Set debug level for our modules
logging.getLogger('linkdetector').setLevel(logging.DEBUG)
logging.getLogger('commands').setLevel(logging.INFO)
logging.getLogger('joinremover').setLevel(logging.INFO)
logging.getLogger('admin').setLevel(logging.INFO)
logging.getLogger('database').setLevel(logging.INFO)

# Get bot token and super admin ID from environment
BOT_TOKEN = os.getenv('BOT_TOKEN')
SUPER_ADMIN_ID = os.getenv('SUPER_ADMIN_ID')

# Validate environment variables
if not BOT_TOKEN:
    logger.error("BOT_TOKEN environment variable is required!")
    logger.error("Please create a .env file with your bot token:")
    logger.error("BOT_TOKEN=your_bot_token_here")
    raise ValueError("BOT_TOKEN environment variable is required")

if not SUPER_ADMIN_ID:
    logger.warning("SUPER_ADMIN_ID not set - admin features will be disabled")
    logger.warning("To enable admin features, add your user ID to .env file:")
    logger.warning("SUPER_ADMIN_ID=your_user_id_here")
    logger.warning("You can get your user ID from @userinfobot")
else:
    try:
        admin_id = int(SUPER_ADMIN_ID)
        logger.info(f"Admin features enabled for user ID: {admin_id}")
    except ValueError:
        logger.error("SUPER_ADMIN_ID must be a valid integer (user ID)")
        SUPER_ADMIN_ID = None

logger.info(f"Bot configuration:")
logger.info(f"  - BOT_TOKEN: {'✅ Set' if BOT_TOKEN else '❌ Missing'}")
logger.info(f"  - SUPER_ADMIN_ID: {'✅ Set (' + str(SUPER_ADMIN_ID) + ')' if SUPER_ADMIN_ID else '❌ Missing'}")

async def track_user_activity(message: Message):
    """Track user activity in database"""
    try:
        if message.from_user and not message.from_user.is_bot:
            await db.add_user(
                user_id=message.from_user.id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name,
                is_bot=message.from_user.is_bot,
                language_code=message.from_user.language_code,
                is_premium=getattr(message.from_user, 'is_premium', False)
            )
            await db.update_user_activity(message.from_user.id)
        
        if message.chat and message.chat.type in ['group', 'supergroup']:
            await db.add_group(
                chat_id=message.chat.id,
                title=message.chat.title,
                chat_type=message.chat.type,
                username=message.chat.username
            )
            await db.update_group_activity(message.chat.id)
            
    except Exception as e:
        logger.error(f"Error tracking user activity: {e}")

def setup_activity_tracking(dp: Dispatcher):
    """Setup activity tracking for private messages (group messages are handled in linkdetector.py)"""
    
    # This handler only tracks private messages since group messages are handled in linkdetector
    @dp.message(lambda message: message.chat and message.chat.type == 'private')
    async def private_activity_tracker(message: Message):
        await track_user_activity(message)
        logger.debug(f"Private activity tracked for user {message.from_user.id if message.from_user else 'N/A'}")

async def on_startup():
    """Actions to perform on bot startup"""
    logger.info("🚀 Bot is starting up...")
    
    # Initialize database
    try:
        await db.init_db()
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        raise
    
    logger.info("✅ Bot startup completed successfully")

async def on_shutdown():
    """Actions to perform on bot shutdown"""
    logger.info("🔄 Bot is shutting down...")
    logger.info("✅ Bot shutdown completed")

async def main():
    # Perform startup actions
    await on_startup()
    
    # Initialize bot and dispatcher
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Setup handlers in order of priority
    logger.info("🔧 Setting up handlers...")
    
    # 1. Commands (highest priority)
    logger.info("  📋 Setting up commands...")
    setup_commands(dp)
    
    # 2. Admin handlers  
    logger.info("  👤 Setting up admin handlers...")
    setup_admin(dp, bot)
    
    # 3. Content filters (link detector, join remover)
    logger.info("  🔍 Setting up content filters...")
    setup_link_detector(dp, bot)
    setup_join_remover(dp, bot)
    
    # 4. Activity tracking (lowest priority - catches remaining messages)
    logger.info("  📊 Setting up activity tracking...")
    setup_activity_tracking(dp)
    
    logger.info("✅ All handlers setup completed")
    
    try:
        logger.info("🤖 Bot ishga tushmoqda... (Bot is starting...)")
        logger.info("📞 Press Ctrl+C to stop the bot")
        
        # Start polling
        await dp.start_polling(bot, skip_updates=True)
        
    except KeyboardInterrupt:
        logger.info("⏹️ Bot stopped by user (Ctrl+C)")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
    finally:
        # Perform shutdown actions
        await on_shutdown()
        await bot.session.close()
        logger.info("🔚 Bot session closed")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⏹️ Bot to'xtatildi (Bot stopped)")
    except Exception as e:
        logger.error(f"❌ Critical error: {e}")
        raise