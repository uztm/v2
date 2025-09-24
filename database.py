import aiosqlite
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str = "bot_database.db"):
        self.db_path = db_path
    
    async def init_db(self):
        """Initialize database tables"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Users table
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        last_name TEXT,
                        is_bot BOOLEAN DEFAULT 0,
                        language_code TEXT,
                        is_premium BOOLEAN DEFAULT 0,
                        first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        is_active BOOLEAN DEFAULT 1
                    )
                """)
                
                # Groups table
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS groups (
                        chat_id INTEGER PRIMARY KEY,
                        title TEXT,
                        type TEXT,
                        username TEXT,
                        member_count INTEGER DEFAULT 0,
                        first_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        is_active BOOLEAN DEFAULT 1
                    )
                """)
                
                # User-Group relations table
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS user_groups (
                        user_id INTEGER,
                        chat_id INTEGER,
                        joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        is_admin BOOLEAN DEFAULT 0,
                        PRIMARY KEY (user_id, chat_id),
                        FOREIGN KEY (user_id) REFERENCES users (user_id),
                        FOREIGN KEY (chat_id) REFERENCES groups (chat_id)
                    )
                """)
                
                # Statistics table
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS statistics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date DATE DEFAULT CURRENT_DATE,
                        total_users INTEGER DEFAULT 0,
                        total_groups INTEGER DEFAULT 0,
                        active_users INTEGER DEFAULT 0,
                        active_groups INTEGER DEFAULT 0,
                        messages_deleted INTEGER DEFAULT 0,
                        spam_detected INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                await db.commit()
                logger.info("Database initialized successfully")
                
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    async def add_user(self, user_id: int, username: str = None, first_name: str = None, 
                      last_name: str = None, is_bot: bool = False, language_code: str = None,
                      is_premium: bool = False):
        """Add or update user in database"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO users 
                    (user_id, username, first_name, last_name, is_bot, language_code, is_premium, last_seen)
                    VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (user_id, username, first_name, last_name, is_bot, language_code, is_premium))
                
                await db.commit()
                logger.info(f"User {user_id} ({username}) added/updated in database")
                
        except Exception as e:
            logger.error(f"Error adding user {user_id}: {e}")
    
    async def add_group(self, chat_id: int, title: str = None, chat_type: str = None, 
                       username: str = None, member_count: int = 0):
        """Add or update group in database"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO groups 
                    (chat_id, title, type, username, member_count, last_active)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (chat_id, title, chat_type, username, member_count))
                
                await db.commit()
                logger.info(f"Group {chat_id} ({title}) added/updated in database")
                
        except Exception as e:
            logger.error(f"Error adding group {chat_id}: {e}")
    
    async def update_user_activity(self, user_id: int):
        """Update user's last seen timestamp"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    UPDATE users SET last_seen = CURRENT_TIMESTAMP WHERE user_id = ?
                """, (user_id,))
                await db.commit()
                
        except Exception as e:
            logger.error(f"Error updating user activity {user_id}: {e}")
    
    async def update_group_activity(self, chat_id: int):
        """Update group's last active timestamp"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    UPDATE groups SET last_active = CURRENT_TIMESTAMP WHERE chat_id = ?
                """, (chat_id,))
                await db.commit()
                
        except Exception as e:
            logger.error(f"Error updating group activity {chat_id}: {e}")
    
    async def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all users for broadcasting"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("""
                    SELECT user_id, username, first_name, last_name 
                    FROM users 
                    WHERE is_active = 1 AND is_bot = 0
                """) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
                    
        except Exception as e:
            logger.error(f"Error getting users: {e}")
            return []
    
    async def get_analytics(self) -> Dict[str, Any]:
        """Get bot analytics"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                
                # Total users
                async with db.execute("SELECT COUNT(*) as count FROM users WHERE is_bot = 0") as cursor:
                    total_users = (await cursor.fetchone())['count']
                
                # Active users (last 7 days)
                async with db.execute("""
                    SELECT COUNT(*) as count FROM users 
                    WHERE is_bot = 0 AND last_seen >= datetime('now', '-7 days')
                """) as cursor:
                    active_users = (await cursor.fetchone())['count']
                
                # Total groups
                async with db.execute("SELECT COUNT(*) as count FROM groups") as cursor:
                    total_groups = (await cursor.fetchone())['count']
                
                # Active groups (last 7 days)
                async with db.execute("""
                    SELECT COUNT(*) as count FROM groups 
                    WHERE last_active >= datetime('now', '-7 days')
                """) as cursor:
                    active_groups = (await cursor.fetchone())['count']
                
                # Top groups by member count
                async with db.execute("""
                    SELECT title, member_count FROM groups 
                    WHERE member_count > 0 
                    ORDER BY member_count DESC 
                    LIMIT 5
                """) as cursor:
                    top_groups = [dict(row) for row in await cursor.fetchall()]
                
                return {
                    'total_users': total_users,
                    'active_users': active_users,
                    'total_groups': total_groups,
                    'active_groups': active_groups,
                    'top_groups': top_groups
                }
                
        except Exception as e:
            logger.error(f"Error getting analytics: {e}")
            return {}
    
    async def increment_spam_counter(self):
        """Increment spam detection counter"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                today = datetime.now().date()
                await db.execute("""
                    INSERT OR IGNORE INTO statistics (date) VALUES (?)
                """, (today,))
                
                await db.execute("""
                    UPDATE statistics SET spam_detected = spam_detected + 1 
                    WHERE date = ?
                """, (today,))
                
                await db.commit()
                
        except Exception as e:
            logger.error(f"Error incrementing spam counter: {e}")
    
    async def increment_deleted_messages_counter(self):
        """Increment deleted messages counter"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                today = datetime.now().date()
                await db.execute("""
                    INSERT OR IGNORE INTO statistics (date) VALUES (?)
                """, (today,))
                
                await db.execute("""
                    UPDATE statistics SET messages_deleted = messages_deleted + 1 
                    WHERE date = ?
                """, (today,))
                
                await db.commit()
                
        except Exception as e:
            logger.error(f"Error incrementing deleted messages counter: {e}")

# Global database instance
db = Database()