from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, BotCommand
from aiogram.fsm.context import FSMContext
from bot.keyboards.reply import get_main_menu_keyboard
from bot.keyboards.inline import get_cancel_keyboard
from bot.states import BotStates
from bot.services.system_status import status_service

router = Router(name="commands_router")

BOT_COMMANDS = [
    BotCommand(command="analyze", description="🔍 Анализ и перевод документа (по умолчанию)"),
    BotCommand(command="translate", description="🌐 Перевод текста / фото / документа"),
    BotCommand(command="save", description="💾 Сохранить файл в облако"),
    BotCommand(command="note", description="📝 Новая заметка (голос или текст -> .md)"),
    BotCommand(command="status", description="📊 Статус бота и хранилища ZimaOS"),
    BotCommand(command="help", description="ℹ️ Инструкция и справка"),
]

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    welcome_text = (
        f"👋 Здравствуйте, {message.from_user.first_name}!\n\n"
        "Я ваш персональный ассистент-переводчик и секретарь для **ZimaOS**.\n\n"
        "✨ **Что я умею**:\n"
        "• 📄 **Анализ и перевод** (по умолчанию): отправьте фото, PDF или Word-документ — я объясню, что это за документ, что требуется сделать, и переведу суть на русский язык.\n"
        "• 🌐 **Перевод**: точный перевод документов, картинок или текста.\n"
        "• 💾 **Сохранение в облако**: надежное сохранение файлов в вашу сетевую папку.\n"
        "• 📝 **Новые заметки**: отправьте голосовое сообщение или текст — я структурирую мысль и сохраню красивый `.md` файл в ваше хранилище.\n\n"
        "💡 *Подсказка: Вы можете просто отправить любой файл или фото, и я автоматически выполню анализ и перевод!*"
    )
    await message.answer(welcome_text, reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")

@router.message(Command("help"))
@router.message(F.text == "ℹ️ Справка")
async def cmd_help(message: Message):
    help_text = (
        "📖 **Руководство пользователя**\n\n"
        "1️⃣ **Анализ и перевод документов** (Режим по умолчанию):\n"
        "Просто отправьте боту фото, скан, PDF или Word-файл. Если нужно, добавьте подпись с вашим вопросом. Бот объяснит суть документа, выделит действия/сроки/суммы и даст перевод.\n\n"
        "2️⃣ **Чистый перевод** (`/translate`):\n"
        "Нажмите кнопку или команду, затем отправьте текст или файл для дословного перевода на русский язык.\n\n"
        "3️⃣ **Сохранение в облако** (`/save`):\n"
        "Отправьте файл в этом режиме или нажмите кнопку `💾 В облако` под любым сообщением — файл будет записан в вашу папку на ZimaBoard.\n\n"
        "4️⃣ **Голосовые и текстовые заметки** (`/note`):\n"
        "Запишите голосовое сообщение (аудио) или напишите мысль. Бот расшифрует голос, красиво отформатирует Markdown (с чекбоксами и тегами) и сохранит файл в папку заметок.\n\n"
        "5️⃣ **Статус системы** (`/status`):\n"
        "Показывает свободное место на дисках ZimaOS, количество сохраненных файлов и состояние AI-сервисов."
    )
    await message.answer(help_text, parse_mode="Markdown")

@router.message(Command("status"))
@router.message(F.text == "📊 Статус бота")
async def cmd_status(message: Message):
    status_text = status_service.format_status_message()
    await message.answer(status_text, parse_mode="Markdown")

@router.message(Command("translate"))
@router.message(F.text == "🌐 Перевод")
async def cmd_translate(message: Message, state: FSMContext):
    await state.set_state(BotStates.waiting_for_translate)
    await message.answer(
        "🌐 **Режим перевода активен**\n\n"
        "Отправьте текст, фото, PDF или Word-файл, который необходимо перевести на русский язык.",
        reply_markup=get_cancel_keyboard(),
        parse_mode="Markdown"
    )

@router.message(Command("analyze"))
@router.message(F.text == "🔍 Анализ и перевод")
async def cmd_analyze(message: Message, state: FSMContext):
    await state.set_state(BotStates.waiting_for_analyze)
    await message.answer(
        "🔍 **Режим анализа и перевода активен**\n\n"
        "Отправьте фото, PDF или Word-документ. Бот определит тип документа, выделит обязательства, сроки и ключевые моменты с переводом.",
        reply_markup=get_cancel_keyboard(),
        parse_mode="Markdown"
    )

@router.message(Command("save"))
@router.message(F.text == "💾 Сохранить в облако")
async def cmd_save(message: Message, state: FSMContext):
    await state.set_state(BotStates.waiting_for_save)
    await message.answer(
        "💾 **Режим сохранения в облако**\n\n"
        "Отправьте любой файл (документ, фото, архив), и он будет сохранен в настроенную папку хранилища ZimaOS.",
        reply_markup=get_cancel_keyboard(),
        parse_mode="Markdown"
    )

@router.message(Command("note"))
@router.message(F.text == "📝 Новая заметка")
async def cmd_note(message: Message, state: FSMContext):
    await state.set_state(BotStates.waiting_for_note)
    await message.answer(
        "📝 **Создание новой заметки**\n\n"
        "Отправьте **голосовое сообщение** 🎙 или **текст** ✍️.\n"
        "Бот распознает речь, красиво отформатирует текст в Markdown и сохранит `.md` файл в вашу папку заметок.",
        reply_markup=get_cancel_keyboard(),
        parse_mode="Markdown"
    )
