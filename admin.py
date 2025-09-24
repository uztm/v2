import logging
import asyncio
import os
from aiogram import Dispatcher, Bot
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import db

logger = logging.getLogger(__name__)

# Get super admin ID from environment variable with better error handling
# try:
#     SUPER_ADMIN_ID = int(os.getenv('SUPER_ADMIN_ID', 0))
#     if SUPER_ADMIN_ID == 0:
#         logger.warning("SUPER_ADMIN_ID not set or is 0. Admin features will be disabled.")
#     else:
#         logger.info(f"SUPER_ADMIN_ID loaded: {SUPER_ADMIN_ID}")
# except (ValueError, TypeError):
#     logger.error("Invalid SUPER_ADMIN_ID format. Must be a valid integer.")
#     SUPER_ADMIN_ID = 0

SUPER_ADMIN_ID=5403516004

class BroadcastStates(StatesGroup):
    waiting_for_photo = State()
    waiting_for_text = State()
    confirm_broadcast = State()

def is_super_admin(user_id: int) -> bool:
    result = (user_id == 5403516004 and 5403516004 != 0)
    logger.debug(f"Admin check: user_id={user_id}, 5403516004={5403516004}, result={result}")
    return result


async def admin_command(message: Message, state: FSMContext):
    """Handle /admin command - only for super admin"""
    try:
        user_id = message.from_user.id
        logger.info(f"Admin command called by user {user_id}, SUPER_ADMIN_ID={SUPER_ADMIN_ID}")
        
        if not is_super_admin(user_id):
            logger.warning(f"Unauthorized admin attempt by user {user_id}")
            await message.answer("❌ Bu buyruq faqat super admin uchun!")
            return
        
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📊 Analitika",
                        callback_data="admin_analytics"
                    ),
                    InlineKeyboardButton(
                        text="📢 Xabar yuborish",
                        callback_data="admin_broadcast"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="👥 Foydalanuvchilar",
                        callback_data="admin_users"
                    ),
                    InlineKeyboardButton(
                        text="🔧 Sozlamalar",
                        callback_data="admin_settings"
                    )
                ]
            ]
        )
        
        admin_text = f"""
🔧 **Admin Panel**

Salom, {message.from_user.first_name}!

Admin panelga xush kelibsiz. Bu yerdan botni boshqarishingiz mumkin:

📊 **Analitika** - Bot statistikasini ko'rish
📢 **Xabar yuborish** - Barcha foydalanuvchilarga xabar yuborish
👥 **Foydalanuvchilar** - Foydalanuvchilar ro'yxati
🔧 **Sozlamalar** - Bot sozlamalari

Super Admin ID: `{SUPER_ADMIN_ID}`
Sizning ID: `{user_id}`
Status: ✅ **Tasdiqlangan Admin**
        """
        
        await message.answer(admin_text, reply_markup=keyboard, parse_mode="Markdown")
        logger.info(f"Admin panel sent to user {user_id}")
        
    except Exception as e:
        logger.error(f"Error in admin command: {e}")
        await message.answer("❌ Admin panelni yuklashda xatolik yuz berdi.")

async def analytics_command(message: Message):
    """Handle /analytics command"""
    try:
        user_id = message.from_user.id
        logger.info(f"Analytics command called by user {user_id}")
        
        if not is_super_admin(user_id):
            logger.warning(f"Unauthorized analytics attempt by user {user_id}")
            await message.answer("❌ Bu buyruq faqat super admin uchun!")
            return
            
        analytics = await db.get_analytics()
        
        if not analytics:
            await message.answer("📊 Analitika ma'lumotlarini olishda xatolik yuz berdi.")
            return
        
        # Format top groups
        top_groups_text = ""
        if analytics.get('top_groups'):
            for i, group in enumerate(analytics['top_groups'], 1):
                top_groups_text += f"{i}. {group['title']} - {group['member_count']} a'zo\n"
        else:
            top_groups_text = "Ma'lumot yo'q"
        
        analytics_text = f"""
📊 **Bot Analitikasi**

👥 **Foydalanuvchilar:**
• Jami: {analytics.get('total_users', 0)}
• Faol (7 kun): {analytics.get('active_users', 0)}

💬 **Guruhlar:**
• Jami: {analytics.get('total_groups', 0)}
• Faol (7 kun): {analytics.get('active_groups', 0)}

🏆 **Eng yirik guruhlar:**
{top_groups_text}

📈 **Aktivlik:**
• Faol foydalanuvchilar: {round((analytics.get('active_users', 0) / max(analytics.get('total_users', 1), 1)) * 100, 1)}%
• Faol guruhlar: {round((analytics.get('active_groups', 0) / max(analytics.get('total_groups', 1), 1)) * 100, 1)}%
        """
        
        await message.answer(analytics_text, parse_mode="Markdown")
        logger.info(f"Analytics sent to user {user_id}")
        
    except Exception as e:
        logger.error(f"Error in analytics command: {e}")
        await message.answer("❌ Analitika ma'lumotlarini olishda xatolik yuz berdi.")

async def start_broadcast(callback_query: CallbackQuery, state: FSMContext):
    """Start broadcast process"""
    try:
        if not is_super_admin(callback_query.from_user.id):
            await callback_query.answer("❌ Ruxsat yo'q!")
            return
            
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📷 Rasm yuklash",
                        callback_data="broadcast_with_photo"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="📝 Faqat matn",
                        callback_data="broadcast_text_only"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="❌ Bekor qilish",
                        callback_data="broadcast_cancel"
                    )
                ]
            ]
        )
        
        await callback_query.message.edit_text(
            "📢 **Xabar yuborish**\n\nXabar turini tanlang:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        await callback_query.answer()
        
    except Exception as e:
        logger.error(f"Error starting broadcast: {e}")
        await callback_query.answer("❌ Xatolik yuz berdi!")

async def broadcast_with_photo(callback_query: CallbackQuery, state: FSMContext):
    """Handle broadcast with photo"""
    try:
        if not is_super_admin(callback_query.from_user.id):
            await callback_query.answer("❌ Ruxsat yo'q!")
            return
            
        await state.set_state(BroadcastStates.waiting_for_photo)
        await callback_query.message.edit_text(
            "📷 **Rasm yuklang**\n\nIltimos, xabar bilan birga yuboriladigan rasmni yuklang:"
        )
        await callback_query.answer()
        
    except Exception as e:
        logger.error(f"Error in broadcast with photo: {e}")
        await callback_query.answer("❌ Xatolik yuz berdi!")

async def broadcast_text_only(callback_query: CallbackQuery, state: FSMContext):
    """Handle text-only broadcast"""
    try:
        if not is_super_admin(callback_query.from_user.id):
            await callback_query.answer("❌ Ruxsat yo'q!")
            return
            
        await state.set_state(BroadcastStates.waiting_for_text)
        await state.update_data(photo=None)
        await callback_query.message.edit_text(
            "📝 **Matn kiriting**\n\nIltimos, barcha foydalanuvchilarga yuboriladigan matnni kiriting:"
        )
        await callback_query.answer()
        
    except Exception as e:
        logger.error(f"Error in text-only broadcast: {e}")
        await callback_query.answer("❌ Xatolik yuz berdi!")

async def handle_photo_upload(message: Message, state: FSMContext):
    """Handle photo upload for broadcast"""
    try:
        if not is_super_admin(message.from_user.id):
            await message.answer("❌ Ruxsat yo'q!")
            return
            
        if not message.photo:
            await message.answer("❌ Iltimos, rasm yuklang yoki /cancel buyrug'ini ishlating.")
            return
        
        # Save photo file_id
        photo_file_id = message.photo[-1].file_id
        await state.update_data(photo=photo_file_id)
        await state.set_state(BroadcastStates.waiting_for_text)
        
        await message.answer(
            "✅ Rasm qabul qilindi!\n\n📝 Endi rasm uchun matn kiriting (caption):"
        )
        
    except Exception as e:
        logger.error(f"Error handling photo upload: {e}")
        await message.answer("❌ Rasmni qayta ishlashda xatolik yuz berdi.")

async def handle_broadcast_text(message: Message, state: FSMContext):
    """Handle broadcast text input"""
    try:
        if not is_super_admin(message.from_user.id):
            await message.answer("❌ Ruxsat yo'q!")
            await state.clear()
            return
            
        if not message.text:
            await message.answer("❌ Iltimos, matn kiriting yoki /cancel buyrug'ini ishlating.")
            return
        
        data = await state.get_data()
        photo = data.get('photo')
        text = message.text
        
        await state.update_data(text=text)
        await state.set_state(BroadcastStates.confirm_broadcast)
        
        # Show preview
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Yuborish",
                        callback_data="confirm_broadcast"
                    ),
                    InlineKeyboardButton(
                        text="❌ Bekor qilish",
                        callback_data="cancel_broadcast"
                    )
                ]
            ]
        )
        
        preview_text = f"📋 **Xabar ko'rinishi:**\n\n{text}\n\n👥 Barcha foydalanuvchilarga yuborilsinmi?"
        
        if photo:
            await message.answer_photo(
                photo=photo,
                caption=preview_text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        else:
            await message.answer(
                preview_text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        
    except Exception as e:
        logger.error(f"Error handling broadcast text: {e}")
        await message.answer("❌ Matnni qayta ishlashda xatolik yuz berdi.")

async def confirm_broadcast(callback_query: CallbackQuery, state: FSMContext, bot: Bot):
    """Confirm and execute broadcast"""
    try:
        if not is_super_admin(callback_query.from_user.id):
            await callback_query.answer("❌ Ruxsat yo'q!")
            return
            
        data = await state.get_data()
        photo = data.get('photo')
        text = data.get('text')
        
        if not text:
            await callback_query.answer("❌ Xabar matni topilmadi!")
            return
        
        users = await db.get_all_users()
        if not users:
            await callback_query.message.edit_text("❌ Foydalanuvchilar topilmadi!")
            await state.clear()
            return
        
        # Start broadcasting
        await callback_query.message.edit_text(
            f"📤 Xabar yuborilmoqda...\n👥 Jami foydalanuvchilar: {len(users)}"
        )
        
        success_count = 0
        failed_count = 0
        
        for user in users:
            try:
                user_id = user['user_id']
                
                if photo:
                    await bot.send_photo(
                        chat_id=user_id,
                        photo=photo,
                        caption=text,
                        parse_mode="Markdown"
                    )
                else:
                    await bot.send_message(
                        chat_id=user_id,
                        text=text,
                        parse_mode="Markdown"
                    )
                
                success_count += 1
                
                # Small delay to avoid rate limits
                await asyncio.sleep(0.05)
                
            except Exception as e:
                failed_count += 1
                logger.warning(f"Failed to send broadcast to user {user_id}: {e}")
        
        # Show results
        result_text = f"""
✅ **Xabar yuborish yakunlandi!**

📊 **Natijalar:**
• Muvaffaqiyatli: {success_count}
• Xatolik: {failed_count}
• Jami: {len(users)}

📈 Muvaffaqiyat darajasi: {round((success_count/len(users))*100, 1)}%
        """
        
        await callback_query.message.edit_text(result_text, parse_mode="Markdown")
        await state.clear()
        await callback_query.answer()
        
    except Exception as e:
        logger.error(f"Error in confirm broadcast: {e}")
        await callback_query.message.edit_text("❌ Xabar yuborishda xatolik yuz berdi!")
        await state.clear()

async def cancel_broadcast(callback_query: CallbackQuery, state: FSMContext):
    """Cancel broadcast"""
    try:
        await state.clear()
        await callback_query.message.edit_text("❌ Xabar yuborish bekor qilindi.")
        await callback_query.answer()
        
    except Exception as e:
        logger.error(f"Error canceling broadcast: {e}")
        await callback_query.answer("❌ Xatolik yuz berdi!")

async def debug_admin_info(message: Message):
    """Debug command to check admin info"""
    try:
        user_id = message.from_user.id
        debug_text = f"""
🔧 **Debug Ma'lumotlari**

Sizning ID: `{user_id}`
Super Admin ID: `{SUPER_ADMIN_ID}`
Admin ekanligingiz: `{is_super_admin(user_id)}`
Environment SUPER_ADMIN_ID: `{os.getenv('SUPER_ADMIN_ID', 'NOT_SET')}`

**Tekshirish:**
- User ID va Super Admin ID bir xilmi? {user_id == SUPER_ADMIN_ID}
- Super Admin ID noldan farqlimi? {SUPER_ADMIN_ID != 0}
        """
        await message.answer(debug_text, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Error in debug info: {e}")
        await message.answer("❌ Debug ma'lumotni olishda xatolik!")

def setup_admin(dp: Dispatcher, bot: Bot):
    """Setup admin handlers"""
    
    if SUPER_ADMIN_ID == 0:
        logger.warning("SUPER_ADMIN_ID is 0 or not set. Admin handlers will not work!")
        return
    
    logger.info(f"Setting up admin handlers for SUPER_ADMIN_ID: {SUPER_ADMIN_ID}")
    
    @dp.message(Command("admin"))
    async def admin_handler(message: Message, state: FSMContext):
        logger.info(f"Admin command handler triggered by user {message.from_user.id}")
        await admin_command(message, state)
    
    @dp.message(Command("analytics"))
    async def analytics_handler(message: Message):
        logger.info(f"Analytics command handler triggered by user {message.from_user.id}")
        await analytics_command(message)
    
    @dp.message(Command("debug_admin"))
    async def debug_admin_handler(message: Message):
        logger.info(f"Debug admin command triggered by user {message.from_user.id}")
        await debug_admin_info(message)
    
    # Admin callback handlers
    @dp.callback_query(lambda c: c.data == "admin_broadcast")
    async def broadcast_callback_handler(callback_query: CallbackQuery, state: FSMContext):
        await start_broadcast(callback_query, state)
    
    @dp.callback_query(lambda c: c.data == "broadcast_with_photo")
    async def broadcast_photo_handler(callback_query: CallbackQuery, state: FSMContext):
        await broadcast_with_photo(callback_query, state)
    
    @dp.callback_query(lambda c: c.data == "broadcast_text_only")
    async def broadcast_text_handler(callback_query: CallbackQuery, state: FSMContext):
        await broadcast_text_only(callback_query, state)
    
    @dp.callback_query(lambda c: c.data == "confirm_broadcast")
    async def confirm_broadcast_handler(callback_query: CallbackQuery, state: FSMContext):
        await confirm_broadcast(callback_query, state, bot)
    
    @dp.callback_query(lambda c: c.data in ["cancel_broadcast", "broadcast_cancel"])
    async def cancel_broadcast_handler(callback_query: CallbackQuery, state: FSMContext):
        await cancel_broadcast(callback_query, state)
    
    @dp.callback_query(lambda c: c.data == "admin_analytics")
    async def analytics_callback_handler(callback_query: CallbackQuery):
        if not is_super_admin(callback_query.from_user.id):
            await callback_query.answer("❌ Ruxsat yo'q!")
            return
        await analytics_command(callback_query.message)
        await callback_query.answer()
    
    @dp.callback_query(lambda c: c.data == "admin_users")
    async def users_callback_handler(callback_query: CallbackQuery):
        try:
            if not is_super_admin(callback_query.from_user.id):
                await callback_query.answer("❌ Ruxsat yo'q!")
                return
                
            analytics = await db.get_analytics()
            users_text = f"""
👥 **Foydalanuvchilar Ma'lumotlari**

📊 **Umumiy statistika:**
• Jami foydalanuvchilar: {analytics.get('total_users', 0)}
• Faol foydalanuvchilar (7 kun): {analytics.get('active_users', 0)}
• Faollik foizi: {round((analytics.get('active_users', 0) / max(analytics.get('total_users', 1), 1)) * 100, 1)}%

📈 **Guruh statistikasi:**
• Jami guruhlar: {analytics.get('total_groups', 0)}
• Faol guruhlar: {analytics.get('active_groups', 0)}
            """
            await callback_query.message.edit_text(users_text, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Error getting users info: {e}")
            await callback_query.message.edit_text("❌ Foydalanuvchilar ma'lumotini olishda xatolik!")
        await callback_query.answer()
    
    @dp.callback_query(lambda c: c.data == "admin_settings")
    async def settings_callback_handler(callback_query: CallbackQuery):
        if not is_super_admin(callback_query.from_user.id):
            await callback_query.answer("❌ Ruxsat yo'q!")
            return
            
        settings_text = """
🔧 **Bot Sozlamalari**

⚡ **Joriy sozlamalar:**
• Anti-spam: Yoqilgan ✅
• Link aniqlash: Yoqilgan ✅
• Mention nazorati: Yoqilgan ✅
• Join/Leave o'chirish: Yoqilgan ✅

📊 **Ma'lumotlar bazasi:**
• SQLite faylda saqlanadi
• Avtomatik backup: Yo'q ❌

ℹ️ Qo'shimcha sozlamalar keyingi yangilanishlarda qo'shiladi.
        """
        await callback_query.message.edit_text(settings_text, parse_mode="Markdown")
        await callback_query.answer()
    
    # State handlers
    @dp.message(BroadcastStates.waiting_for_photo)
    async def photo_upload_handler(message: Message, state: FSMContext):
        await handle_photo_upload(message, state)
    
    @dp.message(BroadcastStates.waiting_for_text)
    async def text_input_handler(message: Message, state: FSMContext):
        await handle_broadcast_text(message, state)
    
    # Cancel command
    @dp.message(Command("cancel"))
    async def cancel_command_handler(message: Message, state: FSMContext):
        current_state = await state.get_state()
        if current_state:
            await state.clear()
            await message.answer("✅ Jarayon bekor qilindi.")
        else:
            await message.answer("❌ Bekor qilinadigan jarayon yo'q.")
    
    logger.info(f"Admin handlers setup completed for super admin: {SUPER_ADMIN_ID}")