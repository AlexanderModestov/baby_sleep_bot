import os
from typing import Dict, Optional
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

class UserManager:
    def __init__(self):
        supabase_url = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
        supabase_key = os.getenv('NEXT_PUBLIC_SUPABASE_ANON_KEY')
        
        if not supabase_url or not supabase_key:
            raise ValueError("Supabase URL and key must be provided")
        
        self.supabase: Client = create_client(
            supabase_url, 
            supabase_key
        )
    
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
                    "wake_reminders": True
                }
            }
            
            result = self.supabase.table('users').upsert(user_data).execute()
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