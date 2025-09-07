-- Migration: Create notifications and notification_history tables
-- Date: 2025-07-27
-- Purpose: Replace JSON settings with proper notification service architecture

-- Create notifications table for user notification preferences
CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    notification_type TEXT NOT NULL, -- 'sleep_reminders', 'bedtime_alerts', 'wake_reminders', etc.
    enabled BOOLEAN NOT NULL DEFAULT true,
    settings JSONB DEFAULT '{}', -- notification-specific settings
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    
    -- Ensure one row per user per notification type
    UNIQUE(user_id, notification_type)
);

-- Create notification_history table for audit trail
CREATE TABLE IF NOT EXISTS notification_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    notification_type TEXT NOT NULL,
    child_id UUID REFERENCES children(id) ON DELETE CASCADE, -- optional, for child-specific notifications
    sent_at TIMESTAMPTZ DEFAULT now(),
    message_text TEXT,
    success BOOLEAN NOT NULL DEFAULT true,
    error_message TEXT,
    telegram_message_id INTEGER -- Telegram message ID if successful
);

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_notifications_user_type ON notifications(user_id, notification_type);
CREATE INDEX IF NOT EXISTS idx_notifications_type_enabled ON notifications(notification_type, enabled);
CREATE INDEX IF NOT EXISTS idx_notifications_enabled ON notifications(enabled) WHERE enabled = true;

-- Create indexes for notification_history table
CREATE INDEX IF NOT EXISTS idx_notification_history_user_type ON notification_history(user_id, notification_type);
CREATE INDEX IF NOT EXISTS idx_notification_history_sent_at ON notification_history(sent_at);
CREATE INDEX IF NOT EXISTS idx_notification_history_child ON notification_history(child_id);

-- Add comments for documentation
COMMENT ON TABLE notifications IS 'User notification preferences by type';
COMMENT ON COLUMN notifications.notification_type IS 'Type of notification: sleep_reminders, bedtime_alerts, wake_reminders, etc.';
COMMENT ON COLUMN notifications.settings IS 'JSON settings specific to this notification type (e.g., timing, frequency)';

COMMENT ON TABLE notification_history IS 'Audit trail of all sent notifications';
COMMENT ON COLUMN notification_history.child_id IS 'Optional reference to specific child for child-related notifications';
COMMENT ON COLUMN notification_history.telegram_message_id IS 'Telegram message ID for successful deliveries';