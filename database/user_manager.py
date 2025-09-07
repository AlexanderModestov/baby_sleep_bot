import os
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions
from dotenv import load_dotenv
from .notification_manager import NotificationManager

load_dotenv()

class UserManager:
    def __init__(self):
        supabase_url = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
        supabase_key = os.getenv('NEXT_PUBLIC_SUPABASE_ANON_KEY')
        
        if not supabase_url or not supabase_key:
            raise ValueError("Supabase URL and key must be provided")
        
        options = ClientOptions()
        self.supabase: Client = create_client(
            supabase_url, 
            supabase_key,
            options
        )
        self.notification_manager = NotificationManager()
    
    def register_user(self, user_id: int, telegram_data: Dict, custom_name: str = None) -> bool:
        """Register a new user or update existing user"""
        try:
            user_data = {
                "telegram_user_id": user_id,
                "username": telegram_data.get("username"),
                "first_name": telegram_data.get("first_name"),
                "last_name": telegram_data.get("last_name"),
                "custom_name": custom_name or telegram_data.get("first_name"),
                "settings": {
                    "notifications_enabled": True,
                    "sleep_reminders": True,
                    "wake_reminders": True,
                    "last_reminder_sent": None
                }
            }
            
            result = self.supabase.table('users').upsert(user_data).execute()
            
            # Initialize notification preferences for new user
            self.notification_manager.initialize_user_notifications(user_id)
            
            return True
        except Exception as e:
            print(f"Error registering user: {e}")
            return False
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """Get user data by ID"""
        try:
            result = self.supabase.table('users').select('*').eq('telegram_user_id', user_id).execute()
            if result.data:
                return result.data[0]
            return None
        except Exception as e:
            print(f"Error getting user: {e}")
            return None
    
    def is_registered(self, user_id: int) -> bool:
        """Check if user is registered"""
        user = self.get_user(user_id)
        return user is not None
    
    def update_user_name(self, user_id: int, custom_name: str) -> bool:
        """Update user's custom name"""
        try:
            result = self.supabase.table('users').update({
                'custom_name': custom_name
            }).eq('telegram_user_id', user_id).execute()
            return True
        except Exception as e:
            print(f"Error updating user name: {e}")
            return False
    
    def update_user_settings(self, user_id: int, settings: Dict) -> bool:
        """Update user's notification settings"""
        try:
            # First get current settings
            user = self.get_user(user_id)
            if user:
                current_settings = user.get('settings', {})
                current_settings.update(settings)
                
                result = self.supabase.table('users').update({
                    'settings': current_settings
                }).eq('telegram_user_id', user_id).execute()
                return True
            return False
        except Exception as e:
            print(f"Error updating user settings: {e}")
            return False

    def get_users_for_notifications(self) -> List[Dict]:
        """Get all users with notifications enabled who need reminders (legacy method)"""
        try:
            result = self.supabase.table('users').select('*').execute()
            users_with_notifications = []
            
            for user in result.data:
                settings = user.get('settings', {})
                if settings.get('notifications_enabled', False):
                    users_with_notifications.append(user)
            
            return users_with_notifications
        except Exception as e:
            print(f"Error getting users for notifications: {e}")
            return []
    
    def get_users_for_notification_type(self, notification_type: str) -> List[Dict]:
        """Get users who have a specific notification type enabled using new notification system"""
        return self.notification_manager.get_users_for_notification_type(notification_type)
    
    def is_notification_enabled(self, user_id: int, notification_type: str) -> bool:
        """Check if a notification type is enabled for a user"""
        return self.notification_manager.is_notification_enabled(user_id, notification_type)
    
    def set_notification_preference(self, user_id: int, notification_type: str, enabled: bool) -> bool:
        """Set notification preference for a user"""
        return self.notification_manager.set_notification_preference(user_id, notification_type, enabled)
    
    def log_notification_sent(self, user_id: int, notification_type: str, message_text: str, 
                            child_id: Optional[str] = None, success: bool = True) -> bool:
        """Log that a notification was sent"""
        return self.notification_manager.log_notification_sent(
            user_id, notification_type, message_text, child_id, success=success
        )

    def get_child_age_in_months(self, child_id: str) -> Optional[int]:
        """Calculate child's age in months from date of birth"""
        try:
            result = self.supabase.table('children').select('date_of_birth').eq('id', child_id).execute()
            if result.data:
                birth_date = datetime.fromisoformat(result.data[0]['date_of_birth'])
                today = datetime.now()
                months = (today.year - birth_date.year) * 12 + (today.month - birth_date.month)
                return max(0, months)
            return None
        except Exception as e:
            print(f"Error calculating child age: {e}")
            return None

    def get_age_based_recommendations(self, age_in_months: int) -> Dict:
        """Get sleep recommendations based on child's age"""
        if age_in_months <= 3:
            return {'wake_window': 45, 'sleep_duration': 120, 'description': 'newborn (0-3 months)'}
        elif age_in_months <= 6:
            return {'wake_window': 90, 'sleep_duration': 90, 'description': 'infant (3-6 months)'}
        elif age_in_months <= 12:
            return {'wake_window': 120, 'sleep_duration': 90, 'description': 'older infant (6-12 months)'}
        elif age_in_months <= 24:
            return {'wake_window': 180, 'sleep_duration': 120, 'description': 'toddler (12-24 months)'}
        else:
            return {'wake_window': 240, 'sleep_duration': 90, 'description': 'young child (2+ years)'}

    def get_children_needing_bedtime_alerts(self, user_id: int) -> List[Dict]:
        """Get children who should go to bed within 10 minutes based on their last sleep session and age-based wake windows"""
        try:
            # Get user's children
            children_result = self.supabase.table('children').select('*').eq('user_id', 
                self.get_user(user_id)['id']).execute()
            
            children_needing_bedtime = []
            
            for child in children_result.data:
                # Get child's age and recommendations
                age_months = self.get_child_age_in_months(child['id'])
                if age_months is None:
                    continue
                    
                recommendations = self.get_age_based_recommendations(age_months)
                wake_window_minutes = recommendations['wake_window']
                
                # Get latest sleep session for this child
                sessions_result = self.supabase.table('sleep_sessions').select('*').eq(
                    'child_id', child['id']
                ).order('end_time', desc=True).limit(1).execute()
                
                if sessions_result.data:
                    last_session = sessions_result.data[0]
                    last_end_time = datetime.fromisoformat(last_session['end_time'].replace('Z', '+00:00'))
                    
                    # Calculate when child should go to bed next (last sleep end + wake window)
                    next_sleep_time = last_end_time.replace(tzinfo=None) + timedelta(minutes=wake_window_minutes)
                    
                    # Check if bedtime is within 10 minutes from now
                    now = datetime.now()
                    time_until_bedtime = next_sleep_time - now
                    
                    # Alert if bedtime is between 0 and 10 minutes away
                    if timedelta(minutes=0) <= time_until_bedtime <= timedelta(minutes=10):
                        child_info = {
                            'child': child,
                            'age_months': age_months,
                            'recommendations': recommendations,
                            'next_sleep_time': next_sleep_time.isoformat(),
                            'minutes_until_bedtime': int(time_until_bedtime.total_seconds() // 60)
                        }
                        children_needing_bedtime.append(child_info)
            
            return children_needing_bedtime
            
        except Exception as e:
            print(f"Error getting children needing bedtime alerts: {e}")
            return []

    def get_children_needing_reminders(self, user_id: int) -> List[Dict]:
        """Get children who haven't had sleep sessions logged recently"""
        try:
            # Get user's children
            children_result = self.supabase.table('children').select('*').eq('user_id', 
                self.get_user(user_id)['id']).execute()
            
            children_needing_reminders = []
            
            for child in children_result.data:
                # Get child's age and recommendations
                age_months = self.get_child_age_in_months(child['id'])
                if age_months is None:
                    continue
                    
                recommendations = self.get_age_based_recommendations(age_months)
                expected_interval_minutes = recommendations['sleep_duration'] * 2  # 2x recommended sleep duration
                
                # Get latest sleep session for this child
                sessions_result = self.supabase.table('sleep_sessions').select('*').eq(
                    'child_id', child['id']
                ).order('end_time', desc=True).limit(1).execute()
                
                should_remind = False
                
                if not sessions_result.data:
                    # No sessions ever - definitely need reminder
                    should_remind = True
                else:
                    last_session = sessions_result.data[0]
                    last_end_time = datetime.fromisoformat(last_session['end_time'].replace('Z', '+00:00'))
                    time_since_last = datetime.now() - last_end_time.replace(tzinfo=None)
                    
                    # Check if time since last session is more than 2x the recommended interval
                    if time_since_last.total_seconds() > (expected_interval_minutes * 60):
                        should_remind = True
                
                if should_remind:
                    child_info = {
                        'child': child,
                        'age_months': age_months,
                        'recommendations': recommendations,
                        'last_session_time': sessions_result.data[0]['end_time'] if sessions_result.data else None
                    }
                    children_needing_reminders.append(child_info)
            
            return children_needing_reminders
            
        except Exception as e:
            print(f"Error getting children needing reminders: {e}")
            return []

    def mark_reminder_sent(self, user_id: int, child_ids: List[str]) -> bool:
        """Mark that a reminder has been sent for specific children"""
        try:
            current_time = datetime.now().isoformat()
            reminder_data = {
                "timestamp": current_time,
                "child_ids": child_ids
            }
            
            return self.update_user_settings(user_id, {"last_reminder_sent": reminder_data})
        except Exception as e:
            print(f"Error marking reminder as sent: {e}")
            return False

    def should_send_reminder(self, user_id: int, child_ids: List[str]) -> bool:
        """Check if we should send a reminder based on previous notifications"""
        try:
            user = self.get_user(user_id)
            if not user:
                return False
                
            settings = user.get('settings', {})
            last_reminder = settings.get('last_reminder_sent')
            
            if not last_reminder:
                return True
                
            # Check if it's the same children
            if set(last_reminder.get('child_ids', [])) == set(child_ids):
                # Check if any new sleep sessions were added since last reminder
                last_reminder_time = datetime.fromisoformat(last_reminder['timestamp'])
                
                for child_id in child_ids:
                    # Get latest sleep session for this child
                    sessions_result = self.supabase.table('sleep_sessions').select('*').eq(
                        'child_id', child_id
                    ).order('end_time', desc=True).limit(1).execute()
                    
                    if sessions_result.data:
                        last_session_time = datetime.fromisoformat(
                            sessions_result.data[0]['end_time'].replace('Z', '+00:00')
                        ).replace(tzinfo=None)
                        
                        # If a new session was added after the last reminder, allow new reminder
                        if last_session_time > last_reminder_time:
                            return True
                
                # Same children, no new sessions - don't send duplicate
                return False
            
            # Different children - send reminder
            return True
            
        except Exception as e:
            print(f"Error checking if should send reminder: {e}")
            return True  # Default to sending if unsure