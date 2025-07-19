from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import urllib.parse

from database.user_manager import UserManager
from config.settings import WEBAPP_URL

router = Router()
user_manager = UserManager()

class RegistrationStates(StatesGroup):
    waiting_for_name = State()

@router.message(Command("start"))
async def start_command(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    if user_manager.is_registered(user_id):
        # User is already registered, show main menu
        user = user_manager.get_user(user_id)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="🍼 Open Baby Sleep Tracker",
                web_app=WebAppInfo(url=f"{WEBAPP_URL}?telegram_user_id={user_id}&custom_name={urllib.parse.quote(user['custom_name'])}")
            )],
            [InlineKeyboardButton(text="⚙️ Settings", callback_data="settings")]
        ])
        
        await message.answer(
            f"Welcome back, {user['custom_name']}! 👋\n\n"
            f"Track your baby's sleep patterns with our app.",
            reply_markup=keyboard
        )
    else:
        # New user, start registration
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Yes, let's start!", callback_data="start_registration")],
            [InlineKeyboardButton(text="❌ Not now", callback_data="cancel_registration")]
        ])
        
        await message.answer(
            f"Hello {message.from_user.first_name}! 👋\n\n"
            f"Welcome to Baby Sleep Tracker Bot! 🍼\n\n"
            f"This bot helps you track your baby's sleep patterns and provides "
            f"intelligent predictions for optimal sleep times.\n\n"
            f"Would you like to get started?",
            reply_markup=keyboard
        )

@router.callback_query(F.data == "start_registration")
async def start_registration(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
    except Exception:
        pass  # Ignore callback answer errors (query too old)
    
    await state.set_state(RegistrationStates.waiting_for_name)
    await callback.message.edit_text(
        "Great! 🎉\n\n"
        "To personalize your experience, please tell me what you'd like me to call you.\n"
        "You can use your first name, a nickname, or any name you prefer."
    )

@router.callback_query(F.data == "cancel_registration")
async def cancel_registration(callback: CallbackQuery):
    try:
        await callback.answer()
    except Exception:
        pass  # Ignore callback answer errors (query too old)
    
    await callback.message.edit_text(
        "No problem! You can always start the registration later by sending /start again."
    )

@router.message(StateFilter(RegistrationStates.waiting_for_name))
async def process_name(message: Message, state: FSMContext):
    custom_name = message.text.strip()
    
    if len(custom_name) > 50:
        await message.answer(
            "That name is a bit too long. Please choose a shorter name (up to 50 characters)."
        )
        return
    
    if not custom_name:
        await message.answer(
            "Please enter a valid name."
        )
        return
    
    # Register the user
    user_data = {
        "id": message.from_user.id,
        "username": message.from_user.username,
        "first_name": message.from_user.first_name,
        "last_name": message.from_user.last_name
    }
    
    user_manager.register_user(message.from_user.id, user_data, custom_name)
    await state.clear()
    
    # Show success message with main menu
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🍼 Open Baby Sleep Tracker",
            web_app=WebAppInfo(url=f"{WEBAPP_URL}?telegram_user_id={message.from_user.id}&custom_name={urllib.parse.quote(custom_name)}")
        )],
        [InlineKeyboardButton(text="⚙️ Settings", callback_data="settings")]
    ])
    
    await message.answer(
        f"Perfect! Nice to meet you, {custom_name}! ✨\n\n"
        f"You're all set up! You can now:\n"
        f"• Track your baby's sleep patterns\n"
        f"• Get intelligent sleep predictions\n"
        f"• View sleep history and analytics\n\n"
        f"Click the button below to open the app:",
        reply_markup=keyboard
    )