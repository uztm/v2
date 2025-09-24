import logging
from aiogram import Dispatcher, Bot
from aiogram.types import Message
from aiogram.enums import ContentType

logger = logging.getLogger(__name__)

async def handle_new_members(message: Message, bot: Bot):
    """Handle new member join messages"""
    try:
        # Delete the "user joined" message
        await message.delete()
        logger.info(f"Deleted join message in chat {message.chat.id}")
        
    except Exception as e:
        logger.error(f"Error deleting join message: {e}")

async def handle_left_members(message: Message, bot: Bot):
    """Handle member left messages"""
    try:
        # Delete the "user left" message
        await message.delete()
        logger.info(f"Deleted leave message in chat {message.chat.id}")
        
    except Exception as e:
        logger.error(f"Error deleting leave message: {e}")

def setup_join_remover(dp: Dispatcher, bot: Bot):
    """Setup join/leave message remover"""
    
    @dp.message(lambda message: message.content_type == ContentType.NEW_CHAT_MEMBERS)
    async def new_member_handler(message: Message):
        await handle_new_members(message, bot)
    
    @dp.message(lambda message: message.content_type == ContentType.LEFT_CHAT_MEMBER)
    async def left_member_handler(message: Message):
        await handle_left_members(message, bot)
        
    logger.info("Join remover setup completed")