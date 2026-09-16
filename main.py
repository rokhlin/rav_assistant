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
from bot.middlewares.language import LanguageMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("helper_bot")

async def main():
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.error("Critical error: TELEGRAM_BOT_TOKEN is not set in .env file!")
        sys.exit(1)

    # Initialize bot and dispatcher
    bot = Bot(
        token=settings.TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
    )
    dp = Dispatcher()

    # Authorization and language middlewares
    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(AuthMiddleware())
    dp.message.middleware(LanguageMiddleware())
    dp.callback_query.middleware(LanguageMiddleware())

    # Register routers
    dp.include_router(commands_router)
    dp.include_router(actions_router)
    dp.include_router(notes_router)
    dp.include_router(media_router)

    # Set command hints in Telegram menu
    try:
        await bot.set_my_commands(BOT_COMMANDS)
        logger.info("Bot menu commands successfully registered in Telegram")
    except Exception as e:
        logger.warning(f"Failed to set bot menu commands: {e}")

    # Ensure storage folders exist
    settings.cloud_path.mkdir(parents=True, exist_ok=True)
    settings.notes_path.mkdir(parents=True, exist_ok=True)
    (settings.notes_path / "shared").mkdir(parents=True, exist_ok=True)

    logger.info(f"Starting bot... AI Provider: {settings.AI_PROVIDER}")
    logger.info(f"Cloud folder: {settings.cloud_path}")
    logger.info(f"Notes folder: {settings.notes_path}")
    logger.info(f"Shared notes folder: {settings.notes_path / 'shared'}")

    # Start lightweight web status server (for ZimaOS / CasaOS)
    web_runner = None
    if settings.ENABLE_WEB_STATUS:
        try:
            from bot.services.web_server import start_web_server
            web_runner = await start_web_server(port=settings.WEB_PORT)
        except Exception as e:
            logger.warning(f"Failed to start status web server: {e}")

    try:
        # Drop pending updates and start polling
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        if web_runner:
            await web_runner.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped by user.")
