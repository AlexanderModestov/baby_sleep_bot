import os
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from supabase import create_client, Client
import json

class NotificationManager:
    """Manages user notification preferences and history using dedicated tables"""
    
    def __init__(self):
        url = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
        key = os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
        
        if not url or not key:
            raise ValueError("Supabase URL and key must be provided")
            
        self.supabase: Client = create_client(url, key)
    
    # Notification Types Constants
    SLEEP_REMINDERS = "sleep_reminders"
    BEDTIME_ALERTS = "bedtime_alerts"
    WAKE_REMINDERS = "wake_reminders"
    
    def get_user_notifications(self, user_id: int) -> List[Dict]:
        """Get all notification preferences for a user"""
        try:
            # First get the user's UUID from telegram_user_id
            user_result = self.supabase.table('users').select('id').eq('telegram_user_id', user_id).single().execute()
            if not user_result.data:
                return []
            
            user_uuid = user_result.data['id']
            
            result = self.supabase.table('notifications').select('*').eq('user_id', user_uuid).execute()
            return result.data if result.data else []
        except Exception as e:
            print(f"Error getting user notifications: {e}")
            return []
    
    def is_notification_enabled(self, user_id: int, notification_type: str) -> bool:
        """Check if a specific notification type is enabled for a user"""
        try:
            notifications = self.get_user_notifications(user_id)
            for notif in notifications:
                if notif['notification_type'] == notification_type:
                    return notif['enabled']
            
            # Default to enabled if not found (for backward compatibility)
            return True
        except Exception as e:
            print(f"Error checking notification status: {e}")
            return True
    
    def set_notification_preference(self, user_id: int, notification_type: str, enabled: bool, settings: Optional[Dict] = None) -> bool:
        """Set notification preference for a user"""
        try:
            # Get user UUID
            user_result = self.supabase.table('users').select('id').eq('telegram_user_id', user_id).single().execute()
            if not user_result.data:
                return False
            
            user_uuid = user_result.data['id']
            
            # Prepare data
            data = {
                'user_id': user_uuid,
                'notification_type': notification_type,
                'enabled': enabled,
                'updated_at': datetime.now().isoformat()
            }
            
            if settings:
                data['settings'] = settings
            
            # Upsert (insert or update if exists)
            result = self.supabase.table('notifications').upsert(
                data,
                on_conflict='user_id,notification_type'
            ).execute()
            
            return bool(result.data)
        except Exception as e:
            print(f"Error setting notification preference: {e}")
            return False
    
    def get_users_for_notification_type(self, notification_type: str) -> List[Dict]:
        """Get all users who have a specific notification type enabled"""
        try:
            # Join notifications with users to get telegram_user_id
            result = self.supabase.table('notifications')\
                .select('*, users!inner(telegram_user_id, custom_name, settings)')\
                .eq('notification_type', notification_type)\
                .eq('enabled', True)\
                .execute()
            
            # Transform the result to include telegram_user_id at the top level
            users = []
            for item in result.data:
                user_data = {
                    'telegram_user_id': item['users']['telegram_user_id'],
                    'custom_name': item['users']['custom_name'],
                    'settings': item['users']['settings'],
                    'notification_settings': item['settings']
                }
                users.append(user_data)
            
            return users
        except Exception as e:
            print(f"Error getting users for notification type {notification_type}: {e}")
            return []
    
    def log_notification_sent(self, user_id: int, notification_type: str, message_text: str, 
                            child_id: Optional[str] = None, telegram_message_id: Optional[int] = None,
                            success: bool = True, error_message: Optional[str] = None) -> bool:
        """Log a notification that was sent to the history table"""
        try:
            # Get user UUID
            user_result = self.supabase.table('users').select('id').eq('telegram_user_id', user_id).single().execute()
            if not user_result.data:
                return False
            
            user_uuid = user_result.data['id']
            
            data = {
                'user_id': user_uuid,
                'notification_type': notification_type,
                'message_text': message_text,
                'success': success,
                'sent_at': datetime.now().isoformat()
            }
            
            if child_id:
                data['child_id'] = child_id
            if telegram_message_id:
                data['telegram_message_id'] = telegram_message_id
            if error_message:
                data['error_message'] = error_message
            
            result = self.supabase.table('notification_history').insert(data).execute()
            return bool(result.data)
        except Exception as e:
            print(f"Error logging notification: {e}")
            return False
    
    def get_notification_history(self, user_id: int, notification_type: Optional[str] = None, 
                               limit: int = 50) -> List[Dict]:
        """Get notification history for a user"""
        try:
            # Get user UUID
            user_result = self.supabase.table('users').select('id').eq('telegram_user_id', user_id).single().execute()
            if not user_result.data:
                return []
            
            user_uuid = user_result.data['id']
            
            query = self.supabase.table('notification_history')\
                .select('*')\
                .eq('user_id', user_uuid)\
                .order('sent_at', desc=True)\
                .limit(limit)
            
            if notification_type:
                query = query.eq('notification_type', notification_type)
            
            result = query.execute()
            return result.data if result.data else []
        except Exception as e:
            print(f"Error getting notification history: {e}")
            return []
    
    def should_send_notification(self, user_id: int, notification_type: str, 
                               child_id: Optional[str] = None, 
                               min_interval_minutes: int = 60) -> bool:
        """Check if enough time has passed since last notification to avoid spam"""
        try:
            # Get recent notifications
            history = self.get_notification_history(user_id, notification_type, limit=10)
            
            # If no history, allow sending
            if not history:
                return True
            
            # Check the most recent successful notification
            for notification in history:
                if notification['success']:
                    # If child_id is specified, only consider notifications for that child
                    if child_id and notification['child_id'] != child_id:
                        continue
                    
                    sent_at = datetime.fromisoformat(notification['sent_at'].replace('Z', '+00:00'))
                    time_since = datetime.now() - sent_at.replace(tzinfo=None)
                    
                    if time_since.total_seconds() < (min_interval_minutes * 60):
                        return False
                    break
            
            return True
        except Exception as e:
            print(f"Error checking notification interval: {e}")
            return True
    
    def migrate_user_settings(self, user_id: int) -> bool:
        """Migrate user settings from JSON to notifications table"""
        try:
            # Get user with current settings
            user_result = self.supabase.table('users').select('id, settings').eq('telegram_user_id', user_id).single().execute()
            if not user_result.data:
                return False
            
            user_data = user_result.data
            settings = user_data.get('settings', {})
            
            # Create default notifications if they don't exist
            default_notifications = [
                (self.SLEEP_REMINDERS, settings.get('sleep_reminders', True)),
                (self.BEDTIME_ALERTS, settings.get('sleep_reminders', True)),  # Use same setting for bedtime
                (self.WAKE_REMINDERS, settings.get('wake_reminders', True))
            ]
            
            success = True
            for notif_type, enabled in default_notifications:
                if not self.set_notification_preference(user_id, notif_type, enabled):
                    success = False
            
            return success
        except Exception as e:
            print(f"Error migrating user settings: {e}")
            return False
    
    def initialize_user_notifications(self, user_id: int) -> bool:
        """Initialize default notifications for a new user"""
        try:
            default_notifications = [
                (self.SLEEP_REMINDERS, True),
                (self.BEDTIME_ALERTS, True),
                (self.WAKE_REMINDERS, True)
            ]
            
            success = True
            for notif_type, enabled in default_notifications:
                if not self.set_notification_preference(user_id, notif_type, enabled):
                    success = False
            
            return success
        except Exception as e:
            print(f"Error initializing user notifications: {e}")
            return False