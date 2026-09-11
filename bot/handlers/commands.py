from typing import List
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, BotCommand
from aiogram.fsm.context import FSMContext
from bot.keyboards.reply import get_main_menu_keyboard
from bot.keyboards.inline import get_cancel_keyboard, get_language_keyboard
from bot.states import BotStates
from bot.services.system_status import status_service
from bot.texts import (
    get_text,
    BUTTON_HELP_ALL,
    BUTTON_STATUS_ALL,
    BUTTON_TRANSLATE_ALL,
    BUTTON_ANALYZE_ALL,
    BUTTON_SAVE_ALL,
    BUTTON_NOTE_ALL,
    BUTTON_LANG_ALL,
)

router = Router(name="commands_router")

def get_bot_commands(lang: str = "ru") -> List[BotCommand]:
    """Возвращает список команд бота с локализованными описаниями."""
    return [
        BotCommand(command="analyze", description=get_text("cmd_desc_analyze", lang)),
        BotCommand(command="translate", description=get_text("cmd_desc_translate", lang)),
        BotCommand(command="save", description=get_text("cmd_desc_save", lang)),
        BotCommand(command="note", description=get_text("cmd_desc_note", lang)),
        BotCommand(command="language", description=get_text("cmd_desc_language", lang)),
        BotCommand(command="status", description=get_text("cmd_desc_status", lang)),
        BotCommand(command="help", description=get_text("cmd_desc_help", lang)),
    ]

BOT_COMMANDS = get_bot_commands("ru")

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, lang: str = "ru"):
    await state.clear()
    first_name = message.from_user.first_name if message.from_user else "User"
    welcome_text = get_text("welcome", lang, name=first_name)
    await message.answer(welcome_text, reply_markup=get_main_menu_keyboard(lang), parse_mode="Markdown")

@router.message(Command("help"))
@router.message(F.text.in_(BUTTON_HELP_ALL))
async def cmd_help(message: Message, lang: str = "ru"):
    help_text = get_text("help", lang)
    await message.answer(help_text, parse_mode="Markdown")

@router.message(Command("status"))
@router.message(F.text.in_(BUTTON_STATUS_ALL))
async def cmd_status(message: Message, lang: str = "ru"):
    status_text = status_service.format_status_message(lang=lang)
    await message.answer(status_text, parse_mode="Markdown")

@router.message(Command("translate"))
@router.message(F.text.in_(BUTTON_TRANSLATE_ALL))
async def cmd_translate(message: Message, state: FSMContext, lang: str = "ru"):
    await state.set_state(BotStates.waiting_for_translate)
    await message.answer(
        get_text("mode_translate", lang),
        reply_markup=get_cancel_keyboard(lang),
        parse_mode="Markdown"
    )

@router.message(Command("analyze"))
@router.message(F.text.in_(BUTTON_ANALYZE_ALL))
async def cmd_analyze(message: Message, state: FSMContext, lang: str = "ru"):
    await state.set_state(BotStates.waiting_for_analyze)
    await message.answer(
        get_text("mode_analyze", lang),
        reply_markup=get_cancel_keyboard(lang),
        parse_mode="Markdown"
    )

@router.message(Command("save"))
@router.message(F.text.in_(BUTTON_SAVE_ALL))
async def cmd_save(message: Message, state: FSMContext, lang: str = "ru"):
    await state.set_state(BotStates.waiting_for_save)
    await message.answer(
        get_text("mode_save", lang),
        reply_markup=get_cancel_keyboard(lang),
        parse_mode="Markdown"
    )

@router.message(Command("note"))
@router.message(F.text.in_(BUTTON_NOTE_ALL))
async def cmd_note(message: Message, state: FSMContext, lang: str = "ru"):
    await state.set_state(BotStates.waiting_for_note)
    await message.answer(
        get_text("mode_note", lang),
        reply_markup=get_cancel_keyboard(lang),
        parse_mode="Markdown"
    )

@router.message(Command("language"))
@router.message(Command("lang"))
@router.message(F.text.in_(BUTTON_LANG_ALL))
async def cmd_language(message: Message, lang: str = "ru"):
    await message.answer(
        get_text("lang_select_prompt", lang),
        reply_markup=get_language_keyboard(lang),
        parse_mode="Markdown"
    )
