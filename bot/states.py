from aiogram.fsm.state import State, StatesGroup

class BotStates(StatesGroup):
    waiting_for_translate = State()  # Ожидание текста/файла для чистого перевода
    waiting_for_analyze = State()    # Ожидание текста/файла для анализа и перевода
    waiting_for_save = State()       # Ожидание файла для прямого сохранения в облако
    waiting_for_note = State()       # Ожидание текста или голоса для заметки
