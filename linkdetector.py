import re
import logging
from aiogram import Dispatcher, Bot
from aiogram.types import Message
from aiogram.filters import BaseFilter

logger = logging.getLogger(__name__)

class LinkDetectorFilter(BaseFilter):
    """Filter to detect links and mentions in messages"""
    
    async def __call__(self, message: Message) -> bool:
        if not message.text or not message.chat:
            return False
            
        # Only work in groups and supergroups
        if message.chat.type not in ['group', 'supergroup']:
            return False
            
        text = message.text
        
        # Check for links (http, https, www, .com, .net, etc)
        link_patterns = [
            r'https?://[^\s]+',
            r'www\.[^\s]+',
            r'\b[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b',
            r't\.me/[^\s]+',
            r'@[a-zA-Z0-9_]+\.[a-zA-Z]{2,}',
        ]
        
        for pattern in link_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
                
        # Check for mentions
        mention_pattern = r'@[a-zA-Z0-9_]+'
        mentions = re.findall(mention_pattern, text)
        
        if mentions:
            return True
            
        return False

async def handle_link_message(message: Message, bot: Bot):
    """Handle messages containing links or mentions"""
    try:
        if not message.text or not message.from_user:
            logger.debug("Message has no text or from_user, skipping")
            return
            
        text = message.text
        user_id = message.from_user.id
        chat_id = message.chat.id
        username = message.from_user.username or message.from_user.full_name
        
        logger.info(f"Processing message from user {user_id} in chat {chat_id}: '{text[:50]}...'")
        
        # Check for direct links first
        link_patterns = [
            r'https?://[^\s]+',
            r'www\.[^\s]+', 
            r'\b[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b',
            r't\.me/[^\s]+',
            r'@[a-zA-Z0-9_]+\.[a-zA-Z]{2,}',
        ]
        
        has_link = False
        for pattern in link_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                has_link = True
                logger.warning(f"Link detected in message: pattern '{pattern}' matched in '{text}'")
                break
        
        if has_link:
            # Delete message and warn
            await message.delete()
            await message.answer(f"@{message.from_user.username}, ❌ Reklama tarqatish taqiqlanadi! Linklar yuborish mumkin emas.",
                                 parse_mode="HTML")
            logger.warning(f"Link message deleted from user {user_id} in chat {chat_id}")
            return
            
        # Check for mentions
        mention_pattern = r'@([a-zA-Z0-9_]+)'
        mentions = re.findall(mention_pattern, text)
        
        if mentions:
            logger.info(f"Found mentions in message: {mentions}")
            
            # Check each mention
            for mention in mentions:
                logger.info(f"Checking mention: @{mention}")
                
                try:
                    # Try to check if user is in the chat
                    is_member = await check_user_in_chat(bot, chat_id, mention)
                    logger.info(f"User @{mention} membership check result: {is_member}")
                    
                    if not is_member:
                        # User not found in group - likely spam
                        await message.delete()
                        warning_msg = await message.answer(
                            f"@{message.from_user.username}, ⚠️ Reklama tarqatish taqiqlanadi! Guruhda yo'q foydalanuvchilarni mention qilish mumkin emas.",
                            parse_mode="HTML"
                        )
                        logger.warning(f"Foreign mention deleted: @{mention} from user {user_id} in chat {chat_id}")
                        
                        # Delete warning message after 5 seconds
                        import asyncio
                        await asyncio.sleep(5)
                        try:
                            await warning_msg.delete()
                        except:
                            pass
                        return
                    else:
                        logger.info(f"Mention @{mention} is valid - user is in group")
                        
                except Exception as e:
                    logger.error(f"Error checking mention @{mention}: {e}")
                    # If we can't verify, assume it's spam for safety
                    await message.delete()
                    await message.answer(f"@{message.from_user.username}, ⚠️ Reklama tarqatish taqiqlanadi!", parse_mode="HTML")
                    logger.warning(f"Mention deleted due to verification error: @{mention}")
                    return
                    
    except Exception as e:
        logger.error(f"Error in handle_link_message: {e}")

async def check_user_in_chat(bot: Bot, chat_id: int, username: str) -> bool:
    """Check if user with given username is in the chat"""
    try:
        logger.debug(f"Checking if @{username} is in chat {chat_id}")
        
        # Method 1: Try to get chat member by username
        try:
            # This works if the user has been active recently or is an admin
            member = await bot.get_chat_member(chat_id, f"@{username}")
            if member.status in ['creator', 'administrator', 'member']:
                logger.info(f"@{username} confirmed as member with status: {member.status}")
                return True
        except Exception as e:
            logger.debug(f"get_chat_member failed for @{username}: {e}")
        
        # Method 2: Check in administrators list
        try:
            admins = await bot.get_chat_administrators(chat_id)
            for admin in admins:
                if admin.user.username and admin.user.username.lower() == username.lower():
                    logger.info(f"@{username} found in administrators")
                    return True
        except Exception as e:
            logger.debug(f"Could not get administrators: {e}")
        
        # Method 3: Maintain a simple cache of recent users (in-memory)
        # This is a fallback method - we'll track users who send messages
        cache_key = f"{chat_id}:{username.lower()}"
        if hasattr(bot, '_user_cache') and cache_key in bot._user_cache:
            logger.info(f"@{username} found in user cache")
            return True
        
        logger.warning(f"@{username} not found in chat {chat_id} - treating as foreign")
        return False
            
    except Exception as e:
        logger.error(f"Error in check_user_in_chat for @{username}: {e}")
        return False

async def cache_user_activity(bot: Bot, message: Message):
    """Cache user activity for mention verification"""
    try:
        if not hasattr(bot, '_user_cache'):
            bot._user_cache = {}
        
        if message.from_user and message.from_user.username:
            cache_key = f"{message.chat.id}:{message.from_user.username.lower()}"
            bot._user_cache[cache_key] = True
            logger.debug(f"Cached user activity: @{message.from_user.username} in chat {message.chat.id}")
            
    except Exception as e:
        logger.error(f"Error caching user activity: {e}")

def setup_link_detector(dp: Dispatcher, bot: Bot):
    """Setup link detector handlers"""
    
    @dp.message(LinkDetectorFilter())
    async def link_detector_handler(message: Message):
        await handle_link_message(message, bot)
    
    # Cache user activity for all group messages
    @dp.message(lambda message: message.chat and message.chat.type in ['group', 'supergroup'])
    async def cache_users_handler(message: Message):
        await cache_user_activity(bot, message)
        
    logger.info("Link detector setup completed")