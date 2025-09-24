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

# Get bot token from environment
BOT_TOKEN = os.getenv('BOT_TOKEN')

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required")

async def main():
    # Initialize bot and dispatcher
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Setup handlers
    setup_commands(dp)
    setup_link_detector(dp, bot)
    setup_join_remover(dp, bot)
    
    try:
        logger.info("Bot ishga tushmoqda...")
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot to'xtatildi")
    except Exception as e:
        logger.error(f"Xatolik: {e}")