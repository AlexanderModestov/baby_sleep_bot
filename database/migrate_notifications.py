#!/usr/bin/env python3
"""
Migration script to move existing user notification settings from JSON to notifications table
Run this script once after deploying the new notification system
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Add parent directory to path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.user_manager import UserManager
from database.notification_manager import NotificationManager

load_dotenv()

def migrate_user_notifications():
    """Migrate all existing users from JSON settings to notifications table"""
    
    print("Starting notification migration...")
    
    user_manager = UserManager()
    notification_manager = NotificationManager()
    
    try:
        # Get all users
        result = user_manager.supabase.table('users').select('*').execute()
        users = result.data
        
        if not users:
            print("No users found to migrate.")
            return
        
        print(f"Found {len(users)} users to migrate...")
        
        migrated_count = 0
        error_count = 0
        
        for user in users:
            telegram_user_id = user['telegram_user_id']
            settings = user.get('settings', {})
            
            try:
                print(f"Migrating user {telegram_user_id}...")
                
                # Get user UUID
                user_uuid_result = user_manager.supabase.table('users').select('id').eq('telegram_user_id', telegram_user_id).single().execute()
                if not user_uuid_result.data:
                    print(f"  - Could not find user UUID for telegram_user_id {telegram_user_id}")
                    error_count += 1
                    continue
                
                user_uuid = user_uuid_result.data['id']
                
                # Create notification preferences based on existing settings
                notifications_to_create = [
                    {
                        'user_id': user_uuid,
                        'notification_type': 'sleep_reminders',
                        'enabled': settings.get('sleep_reminders', True),
                        'settings': {},
                        'created_at': datetime.now().isoformat(),
                        'updated_at': datetime.now().isoformat()
                    },
                    {
                        'user_id': user_uuid,
                        'notification_type': 'bedtime_alerts',
                        'enabled': settings.get('sleep_reminders', True),  # Use same setting as sleep_reminders
                        'settings': {},
                        'created_at': datetime.now().isoformat(),
                        'updated_at': datetime.now().isoformat()
                    },
                    {
                        'user_id': user_uuid,
                        'notification_type': 'wake_reminders',
                        'enabled': settings.get('wake_reminders', True),
                        'settings': {},
                        'created_at': datetime.now().isoformat(),
                        'updated_at': datetime.now().isoformat()
                    }
                ]
                
                # Insert notification preferences (upsert to avoid duplicates)
                for notification in notifications_to_create:
                    result = user_manager.supabase.table('notifications').upsert(
                        notification,
                        on_conflict='user_id,notification_type'
                    ).execute()
                    
                    if result.data:
                        print(f"  - Created {notification['notification_type']}: {notification['enabled']}")
                    else:
                        print(f"  - Failed to create {notification['notification_type']}")
                
                migrated_count += 1
                print(f"  - Successfully migrated user {telegram_user_id}")
                
            except Exception as e:
                print(f"  - Error migrating user {telegram_user_id}: {e}")
                error_count += 1
        
        print(f"\nMigration completed!")
        print(f"Successfully migrated: {migrated_count} users")
        print(f"Errors: {error_count} users")
        
        if error_count == 0:
            print("\n✅ All users migrated successfully!")
        else:
            print(f"\n⚠️  {error_count} users had errors. Check the output above for details.")
        
    except Exception as e:
        print(f"Fatal error during migration: {e}")
        return False
    
    return error_count == 0

def verify_migration():
    """Verify that the migration worked correctly"""
    print("\nVerifying migration...")
    
    user_manager = UserManager()
    
    try:
        # Count total users
        users_result = user_manager.supabase.table('users').select('telegram_user_id').execute()
        total_users = len(users_result.data) if users_result.data else 0
        
        # Count notifications
        notifications_result = user_manager.supabase.table('notifications').select('*').execute()
        total_notifications = len(notifications_result.data) if notifications_result.data else 0
        
        print(f"Total users: {total_users}")
        print(f"Total notification preferences: {total_notifications}")
        print(f"Expected notification preferences: {total_users * 3}")  # 3 types per user
        
        if total_notifications >= total_users * 3:
            print("✅ Migration verification passed!")
            return True
        else:
            print("❌ Migration verification failed - missing notification preferences")
            return False
            
    except Exception as e:
        print(f"Error during verification: {e}")
        return False

def main():
    """Main migration function"""
    print("=" * 60)
    print("NOTIFICATION SYSTEM MIGRATION")
    print("=" * 60)
    print()
    
    # Check if tables exist
    user_manager = UserManager()
    try:
        # Test if notifications table exists
        test_result = user_manager.supabase.table('notifications').select('id').limit(1).execute()
        print("✅ Notifications table found")
    except Exception as e:
        print("❌ Notifications table not found. Please run the database migration first:")
        print("   SQL file: database/migrations/001_create_notifications_tables.sql")
        print(f"   Error: {e}")
        return False
    
    # Run migration
    success = migrate_user_notifications()
    
    if success:
        # Verify migration
        verify_migration()
    
    return success

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)