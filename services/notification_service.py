import asyncio
import os
from datetime import datetime, timedelta
from typing import List, Dict
from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter, TelegramBadRequest
from database.user_manager import UserManager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import logging
from config.settings import NOTIFICATION_INTERVAL_MINUTES

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.user_manager = UserManager()
        self.scheduler = AsyncIOScheduler()
        
    async def send_sleep_reminder(self, user_id: int, children_info: List[Dict]):
        """Send sleep session reminder to user"""
        try:
            if len(children_info) == 1:
                child = children_info[0]['child']
                
                message = f"⏰ Hi! It's time to log a sleep session for {child['name']}.\n\n"
                
                if children_info[0]['last_session_time']:
                    last_time = datetime.fromisoformat(children_info[0]['last_session_time'].replace('Z', '+00:00'))
                    time_ago = datetime.now() - last_time.replace(tzinfo=None)
                    hours_ago = int(time_ago.total_seconds() // 3600)
                    message += f"Last session was {hours_ago} hours ago. "
                else:
                    message += "No sleep sessions recorded yet. "
                    
                message += "Don't forget to track your baby's sleep patterns! 💤"
                
            else:
                child_names = [info['child']['name'] for info in children_info]
                message = f"⏰ Hi! It's time to log sleep sessions for {', '.join(child_names)}.\n\n"
                message += "Don't forget to track your babies' sleep patterns! 💤"
            
            # Get user info for consistent URL parameters
            user = self.user_manager.get_user(user_id)
            custom_name = user['custom_name'] if user and user['custom_name'] else 'User'
            
            # Create inline keyboard with link to webapp (consistent with start button)
            from config.settings import WEBAPP_URL
            import urllib.parse
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
            
            webapp_url = f"{WEBAPP_URL}?telegram_user_id={user_id}&custom_name={urllib.parse.quote(custom_name)}"
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text="📝 Log Sleep Session",
                    web_app=WebAppInfo(url=webapp_url)
                )
            ]])
            
            await self.bot.send_message(
                chat_id=user_id,
                text=message,
                reply_markup=keyboard
            )
            
            logger.info(f"Sleep reminder sent to user {user_id} for {len(children_info)} children")
            
        except TelegramRetryAfter as e:
            logger.warning(f"Rate limited when sending to {user_id}, retrying after {e.retry_after} seconds")
            await asyncio.sleep(e.retry_after)
            await self.send_sleep_reminder(user_id, children_info)
            
        except TelegramBadRequest as e:
            if "chat not found" in str(e).lower():
                logger.warning(f"Chat not found for user {user_id} - user may have blocked bot or deleted account")
                # You could optionally disable notifications for this user
                # self.user_manager.update_user_settings(user_id, {"notifications_enabled": False})
            else:
                logger.error(f"Bad request when sending to {user_id}: {e}")
            
        except Exception as e:
            logger.error(f"Error sending sleep reminder to {user_id}: {e}")

    async def check_and_send_reminders(self):
        """Check all users and send reminders where needed"""
        try:
            logger.info("Checking for users who need sleep reminders...")
            
            users_for_notifications = self.user_manager.get_users_for_notifications()
            reminders_sent = 0
            
            for user in users_for_notifications:
                telegram_user_id = user['telegram_user_id']
                children_needing_reminders = self.user_manager.get_children_needing_reminders(telegram_user_id)
                
                if children_needing_reminders:
                    # Check if we should send reminder (prevent duplicates)
                    child_ids = [info['child']['id'] for info in children_needing_reminders]
                    
                    if self.user_manager.should_send_reminder(telegram_user_id, child_ids):
                        await self.send_sleep_reminder(telegram_user_id, children_needing_reminders)
                        
                        # Mark reminder as sent
                        self.user_manager.mark_reminder_sent(telegram_user_id, child_ids)
                        reminders_sent += 1
                        
                        # Small delay between messages to avoid rate limiting
                        await asyncio.sleep(0.5)
                    else:
                        logger.info(f"Skipping duplicate reminder for user {telegram_user_id}")
            
            logger.info(f"Sleep reminder check completed. Sent {reminders_sent} reminders.")
            
        except Exception as e:
            logger.error(f"Error in check_and_send_reminders: {e}")

    def start_scheduler(self):
        """Start the notification scheduler"""
        try:
            # Check for reminders based on environment variable
            self.scheduler.add_job(
                self.check_and_send_reminders,
                trigger=IntervalTrigger(minutes=NOTIFICATION_INTERVAL_MINUTES),
                id='sleep_reminders',
                name='Check and send sleep reminders',
                replace_existing=True
            )
            
            self.scheduler.start()
            logger.info(f"Notification scheduler started. Will check every {NOTIFICATION_INTERVAL_MINUTES} minutes.")
            
        except Exception as e:
            logger.error(f"Error starting notification scheduler: {e}")

    def stop_scheduler(self):
        """Stop the notification scheduler"""
        try:
            if self.scheduler.running:
                self.scheduler.shutdown()
                logger.info("Notification scheduler stopped.")
        except Exception as e:
            logger.error(f"Error stopping notification scheduler: {e}")

    async def send_test_reminder(self, user_id: int):
        """Send a test reminder to a specific user (for testing purposes)"""
        children_needing_reminders = self.user_manager.get_children_needing_reminders(user_id)
        
        if children_needing_reminders:
            await self.send_sleep_reminder(user_id, children_needing_reminders)
            return f"Test reminder sent for {len(children_needing_reminders)} children"
        else:
            return "No children need reminders at this time"