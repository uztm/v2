import logging
from aiogram import Dispatcher
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger(__name__)

async def start_command(message: Message):
    """Handle /start command"""
    try:
        # Create inline keyboard with "Add to Group" button
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="➕ Guruhga admin qilib qo'shish",
                        url=f"https://t.me/{(await message.bot.get_me()).username}?startgroup=true&admin=delete_messages+restrict_members"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="📋 Yordam",
                        callback_data="help"
                    )
                ]
            ]
        )
        
        welcome_text = """
🤖 **Assalomu alaykum! Anti-spam botga xush kelibsiz!**

Men guruhingizni spam xabarlardan himoya qilaman:

✅ **Nima qilaman:**
• Linklar va reklama xabarlarini o'chiraman
• Notanish mention (@username) larni nazorat qilaman  
• Guruhga qo'shilish/chiqish xabarlarini o'chiraman
• Spam va reklama tarqatuvchilarni bloklayaman

🔧 **Qanday ishlatish:**
1. Botni guruhga admin huquqlari bilan qo'shing
2. "Xabarlarni o'chirish" va "Foydalanuvchilarni cheklash" huquqlarini bering
3. Bot avtomatik ishlashni boshlaydi!

⚡ Botni guruhga qo'shish uchun pastdagi tugmani bosing.
        """
        
        await message.answer(welcome_text, reply_markup=keyboard, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await message.answer("Xatolik yuz berdi. Iltimos qayta urinib ko'ring.")

# async def help_command(message: Message):
#     """Handle /help command"""
#     try:
#         help_text = """
# 📖 **Yordam - Bot funksiyalari**

# 🔒 **Anti-spam himoya:**
# • HTTP/HTTPS linklar o'chiriladi
# • Domenlar (.com, .net, .org va boshqalar) o'chiriladi
# • t.me linklari o'chiriladi
# • Notanish @mention lar nazorat qilinadi

# ⚙️ **Avtomatik tozalash:**
# • Guruhga qo'shilish xabarlari o'chiriladi
# • Guruhdan chiqish xabarlari o'chiriladi

# 👮 **Admin huquqlari kerak:**
# • Xabarlarni o'chirish
# • Foydalanuvchilarni cheklash

# ❓ **Savollar bormi?**
# @tmbekzod ga murojaat qiling
#         """
        
#         await message.answer(help_text, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Error in help command: {e}")
        await message.answer("Yordam ma'lumotlarini olishda xatolik yuz berdi.")

def setup_commands(dp: Dispatcher):
    """Setup bot commands"""
    
    @dp.message(Command("start"))
    async def start_handler(message: Message):
        await start_command(message)
    
    @dp.message(Command("help"))
    async def help_handler(message: Message):
        await help_command(message)
        
    # Handle help callback
    @dp.callback_query(lambda c: c.data == "help")
    async def help_callback_handler(callback_query):
        await help_command(callback_query.message)
        await callback_query.answer()
        
    logger.info("Commands setup completed")