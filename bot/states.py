from aiogram.fsm.state import State, StatesGroup

class BotStates(StatesGroup):
    waiting_for_translate = State()  # Waiting for text/file for pure translation
    waiting_for_analyze = State()    # Waiting for text/file for document analysis and translation
    waiting_for_save = State()       # Waiting for file to save directly to cloud
    waiting_for_note = State()       # Waiting for text or voice for note creation
    admin_waiting_for_new_user = State()  # Waiting for "ID:Name" or "ID Name"
    admin_waiting_for_rename = State()    # Waiting for new name for user
