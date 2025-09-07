import asyncio
import os
from datetime import datetime, timedelta
from typing import List, Dict
from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter, TelegramBadRequest
from database.user_manager import UserManager
from database.notification_manager import NotificationManager
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
        self.notification_manager = NotificationManager()
        self.scheduler = AsyncIOScheduler()
        
        # Notification type constants - use the same as NotificationManager
        self.SLEEP_REMINDERS = self.notification_manager.SLEEP_REMINDERS
        self.BEDTIME_ALERTS = self.notification_manager.BEDTIME_ALERTS
        
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
            
            sent_message = await self.bot.send_message(
                chat_id=user_id,
                text=message,
                reply_markup=keyboard
            )
            
            # Log the notification in the history using NotificationManager
            child_ids = [info['child']['id'] for info in children_info]
            for child_id in child_ids:
                self.notification_manager.log_notification_sent(
                    user_id, self.SLEEP_REMINDERS, message, child_id, 
                    telegram_message_id=sent_message.message_id, success=True
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

    async def send_bedtime_alert(self, user_id: int, children_info: List[Dict]):
        """Send bedtime alert when child should go to bed soon"""
        try:
            if len(children_info) == 1:
                child = children_info[0]['child']
                minutes_until = children_info[0]['minutes_until_bedtime']
                
                if minutes_until == 0:
                    message = f"🌙 It's bedtime for {child['name']}! Time to start the sleep routine. 💤"
                else:
                    message = f"🌙 {child['name']} should go to bed in {minutes_until} minute{'s' if minutes_until != 1 else ''}! Time to start preparing for sleep. 💤"
                
            else:
                child_details = []
                for info in children_info:
                    minutes = info['minutes_until_bedtime']
                    if minutes == 0:
                        child_details.append(f"{info['child']['name']} (now)")
                    else:
                        child_details.append(f"{info['child']['name']} ({minutes}min)")
                
                message = f"🌙 Bedtime approaching for: {', '.join(child_details)}! Time to start preparing for sleep. 💤"
            
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
                    text="🍼 Open Baby Sleep Tracker",
                    web_app=WebAppInfo(url=webapp_url)
                )
            ]])
            
            sent_message = await self.bot.send_message(
                chat_id=user_id,
                text=message,
                reply_markup=keyboard
            )
            
            # Log the notification in the history using NotificationManager
            child_ids = [info['child']['id'] for info in children_info]
            for child_id in child_ids:
                self.notification_manager.log_notification_sent(
                    user_id, self.BEDTIME_ALERTS, message, child_id, 
                    telegram_message_id=sent_message.message_id, success=True
                )
            
            logger.info(f"Bedtime alert sent to user {user_id} for {len(children_info)} children")
            
        except TelegramRetryAfter as e:
            logger.warning(f"Rate limited when sending bedtime alert to {user_id}, retrying after {e.retry_after} seconds")
            await asyncio.sleep(e.retry_after)
            await self.send_bedtime_alert(user_id, children_info)
            
        except TelegramBadRequest as e:
            if "chat not found" in str(e).lower():
                logger.warning(f"Chat not found for user {user_id} - user may have blocked bot or deleted account")
            else:
                logger.error(f"Bad request when sending bedtime alert to {user_id}: {e}")
            
        except Exception as e:
            logger.error(f"Error sending bedtime alert to {user_id}: {e}")

    async def check_and_send_reminders(self):
        """Check all users and send reminders where needed"""
        try:
            logger.info("Checking for users who need sleep reminders...")
            
            # Use new notification system to get users with sleep reminders enabled
            users_for_notifications = self.notification_manager.get_users_for_notification_type(self.SLEEP_REMINDERS)
            reminders_sent = 0
            
            for user in users_for_notifications:
                telegram_user_id = user['telegram_user_id']
                
                children_needing_reminders = self.user_manager.get_children_needing_reminders(telegram_user_id)
                
                if children_needing_reminders:
                    # Check if enough time has passed since last reminder (prevent spam)
                    if self.notification_manager.should_send_notification(
                        telegram_user_id, self.SLEEP_REMINDERS, min_interval_minutes=60
                    ):
                        await self.send_sleep_reminder(telegram_user_id, children_needing_reminders)
                        reminders_sent += 1
                        
                        # Small delay between messages to avoid rate limiting
                        await asyncio.sleep(0.5)
                    else:
                        logger.info(f"Skipping duplicate reminder for user {telegram_user_id} (sent recently)")
            
            logger.info(f"Sleep reminder check completed. Sent {reminders_sent} reminders.")
            
        except Exception as e:
            logger.error(f"Error in check_and_send_reminders: {e}")

    async def check_and_send_bedtime_alerts(self):
        """Check all users and send bedtime alerts where needed"""
        try:
            logger.info("Checking for users who need bedtime alerts...")
            
            # Use new notification system to get users with bedtime alerts enabled
            users_for_notifications = self.notification_manager.get_users_for_notification_type(self.BEDTIME_ALERTS)
            alerts_sent = 0
            
            for user in users_for_notifications:
                telegram_user_id = user['telegram_user_id']
                
                children_needing_bedtime = self.user_manager.get_children_needing_bedtime_alerts(telegram_user_id)
                
                if children_needing_bedtime:
                    # Check if enough time has passed since last bedtime alert (prevent spam)
                    if self.notification_manager.should_send_notification(
                        telegram_user_id, self.BEDTIME_ALERTS, min_interval_minutes=30
                    ):
                        await self.send_bedtime_alert(telegram_user_id, children_needing_bedtime)
                        alerts_sent += 1
                        
                        # Small delay between messages to avoid rate limiting
                        await asyncio.sleep(0.5)
                    else:
                        logger.info(f"Skipping duplicate bedtime alert for user {telegram_user_id} (sent recently)")
            
            logger.info(f"Bedtime alert check completed. Sent {alerts_sent} alerts.")
            
        except Exception as e:
            logger.error(f"Error in check_and_send_bedtime_alerts: {e}")

    async def check_all_notifications(self):
        """Check and send both sleep reminders and bedtime alerts"""
        await self.check_and_send_reminders()
        await self.check_and_send_bedtime_alerts()

    def start_scheduler(self):
        """Start the notification scheduler"""
        try:
            # Check for both reminders and bedtime alerts based on environment variable
            self.scheduler.add_job(
                self.check_all_notifications,
                trigger=IntervalTrigger(minutes=NOTIFICATION_INTERVAL_MINUTES),
                id='all_notifications',
                name='Check and send sleep reminders and bedtime alerts',
                replace_existing=True
            )
            
            self.scheduler.start()
            logger.info(f"Notification scheduler started. Will check for reminders and bedtime alerts every {NOTIFICATION_INTERVAL_MINUTES} minutes.")
            
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