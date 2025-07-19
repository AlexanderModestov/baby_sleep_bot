from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import urllib.parse

from database.user_manager import UserManager

router = Router()
user_manager = UserManager()

class SettingsStates(StatesGroup):
    waiting_for_name_change = State()

@router.callback_query(F.data == "settings")
async def settings_menu(callback: CallbackQuery):
    try:
        await callback.answer()
    except Exception:
        pass  # Ignore callback answer errors (query too old)
    user_id = callback.from_user.id
    
    if not user_manager.is_registered(user_id):
        await callback.message.edit_text(
            "You need to register first. Please use /start command."
        )
        return
    
    user = user_manager.get_user(user_id)
    settings = user.get("settings", {})
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Change Name", callback_data="change_name")],
        [InlineKeyboardButton(
            text=f"🔔 Notifications: {'ON' if settings.get('notifications_enabled', True) else 'OFF'}",
            callback_data="toggle_notifications"
        )],
        [InlineKeyboardButton(
            text=f"😴 Sleep Reminders: {'ON' if settings.get('sleep_reminders', True) else 'OFF'}",
            callback_data="toggle_sleep_reminders"
        )],
        [InlineKeyboardButton(
            text=f"☀️ Wake Reminders: {'ON' if settings.get('wake_reminders', True) else 'OFF'}",
            callback_data="toggle_wake_reminders"
        )],
        [InlineKeyboardButton(text="🔙 Back to Main", callback_data="back_to_main")]
    ])
    
    await callback.message.edit_text(
        f"⚙️ Settings\n\n"
        f"Current name: {user['custom_name']}\n\n"
        f"Notification Settings:",
        reply_markup=keyboard
    )

@router.callback_query(F.data == "change_name")
async def change_name(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
    except Exception:
        pass  # Ignore callback answer errors (query too old)
    await state.set_state(SettingsStates.waiting_for_name_change)
    await callback.message.edit_text(
        "Please enter your new name:"
    )

@router.callback_query(F.data.startswith("toggle_"))
async def toggle_setting(callback: CallbackQuery):
    try:
        await callback.answer()
    except Exception:
        pass  # Ignore callback answer errors (query too old)
    user_id = callback.from_user.id
    setting_name = callback.data.replace("toggle_", "")
    
    user = user_manager.get_user(user_id)
    current_settings = user.get("settings", {})
    
    # Toggle the setting
    if setting_name == "notifications":
        current_settings["notifications_enabled"] = not current_settings.get("notifications_enabled", True)
    elif setting_name == "sleep_reminders":
        current_settings["sleep_reminders"] = not current_settings.get("sleep_reminders", True)
    elif setting_name == "wake_reminders":
        current_settings["wake_reminders"] = not current_settings.get("wake_reminders", True)
    
    user_manager.update_user_settings(user_id, current_settings)
    
    # Refresh the settings menu
    await settings_menu(callback)

@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    try:
        await callback.answer()
    except Exception:
        pass  # Ignore callback answer errors (query too old)
    user_id = callback.from_user.id
    user = user_manager.get_user(user_id)
    
    from config.settings import WEBAPP_URL
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🍼 Open Baby Sleep Tracker",
            web_app=WebAppInfo(url=f"{WEBAPP_URL}?telegram_user_id={user_id}&custom_name={urllib.parse.quote(user['custom_name'])}")
        )],
        [InlineKeyboardButton(text="⚙️ Settings", callback_data="settings")]
    ])
    
    await callback.message.edit_text(
        f"Welcome back, {user['custom_name']}! 👋\n\n"
        f"Track your baby's sleep patterns with our app.",
        reply_markup=keyboard
    )

@router.message(StateFilter(SettingsStates.waiting_for_name_change))
async def process_name_change(message, state: FSMContext):
    new_name = message.text.strip()
    
    if len(new_name) > 50:
        await message.answer(
            "That name is a bit too long. Please choose a shorter name (up to 50 characters)."
        )
        return
    
    if not new_name:
        await message.answer(
            "Please enter a valid name."
        )
        return
    
    user_manager.update_user_name(message.from_user.id, new_name)
    await state.clear()
    
    await message.answer(
        f"✅ Name updated successfully! You're now known as {new_name}."
    )
    
    # Show main menu
    from config.settings import WEBAPP_URL
    from aiogram.types import WebAppInfo
    
    user = user_manager.get_user(message.from_user.id)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🍼 Open Baby Sleep Tracker",
            web_app=WebAppInfo(url=f"{WEBAPP_URL}?telegram_user_id={message.from_user.id}&custom_name={urllib.parse.quote(new_name)}")
        )],
        [InlineKeyboardButton(text="⚙️ Settings", callback_data="settings")]
    ])
    
    await message.answer(
        f"Welcome back, {new_name}! 👋\n\n"
        f"Track your baby's sleep patterns with our app.",
        reply_markup=keyboard
    )