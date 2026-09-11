import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from config import settings
from bot.handlers.commands import router as commands_router, BOT_COMMANDS
from bot.handlers.notes import router as notes_router
from bot.handlers.media import router as media_router
from bot.handlers.actions import router as actions_router
from bot.middlewares.auth import AuthMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("helper_bot")

async def main():
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.error("Критическая ошибка: TELEGRAM_BOT_TOKEN не задан в .env файле!")
        sys.exit(1)

    # Инициализация бота и диспетчера
    bot = Bot(
        token=settings.TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
    )
    dp = Dispatcher()

    # Middleware авторизации
    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(AuthMiddleware())

    # Регистрация роутеров
    dp.include_router(commands_router)
    dp.include_router(actions_router)
    dp.include_router(notes_router)
    dp.include_router(media_router)

    # Установка подсказок команд в Telegram меню
    try:
        await bot.set_my_commands(BOT_COMMANDS)
        logger.info("Команды меню бота успешно зарегистрированы в Telegram")
    except Exception as e:
        logger.warning(f"Не удалось установить команды меню бота: {e}")

    # Убедимся, что папки хранилищ существуют
    settings.cloud_path
    settings.notes_path

    logger.info(f"Запуск бота... Провайдер AI: {settings.AI_PROVIDER}")
    logger.info(f"Папка облака: {settings.cloud_path}")
    logger.info(f"Папка заметок: {settings.notes_path}")

    # Удаление старых обновлений и запуск polling
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен пользователем.")
