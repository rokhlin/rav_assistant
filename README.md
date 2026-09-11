# 🤖 Telegram Helper Bot: Перевод, Анализ документов и Заметки для ZimaOS

Многофункциональный персональный Telegram-бот, разработанный для домашнего сервера **ZimaBoard / ZimaOS** в Docker.

Бот помогает оперативно переводить иностранные документы, объясняет юридическую и финансовую суть входящих бумаг (квитанции, счета, договоры), сохраняет важные файлы в сетевое хранилище ZimaOS и создает форматированные Markdown-заметки (`.md`) из голосовых и текстовых сообщений.

---

## 🌟 Основные возможности

1. 🔍 **Анализ и перевод документов (По умолчанию)**:
   - Если вы просто отправляете **фотографию, скан, PDF или Word (.docx)** документ (даже без выбора команды), бот автоматически:
     - Определяет **тип документа** (счет, квитанция, штраф, договор, письмо).
     - Выделяет **основную суть** (от кого, о чем, ключевые даты и суммы).
     - Четко сообщает, **что требуется сделать пользователю** (сроки оплаты, явка, подпись или отсутствие обязательств).
     - Приводит **перевод ключевых фрагментов** на русский язык.
   - Поддерживает произвольные вопросы в подписи к файлу (например: *"до какого числа нужно оплатить?"*).

2. 🌐 **Перевод (`/translate`)**:
   - Дословный качественный перевод текста, изображений и документов на выбранный язык с сохранением структуры.

3. 🌍 **Мультиязычность (Русский, Английский, Иврит)**:
   - По умолчанию бот работает на **русском языке** без лишних вопросов.
   - Пользователь в любой момент может переключить язык интерфейса и перевода через кнопку `🌐 Язык` или команду `/lang` (`/language`).
   - Доступны 3 языка: **Русский (RU)**, **English (EN)**, **עברית (HE)**.
   - При выборе языка:
     - Интерфейс, меню и кнопки отображаются на выбранном языке.
     - Документы, фото и файлы переводятся с любого исходного языка на выбранный целевой язык.
     - Структурированный разбор документов (тип, суть, действия) генерируется на выбранном языке.
   - Настройка сохраняется индивидуально для каждого пользователя в `data/config/user_settings.json`.

4. 💾 **Сохранение в облако (`/save`)**:
   - Быстрое сохранение полученных медиафайлов и документов в выделенную папку на сервере ZimaOS.
   - Доступно как через команду `/save`, так и в один клик по инлайн-кнопке `💾 В облако` под любым сообщением.

5. 📝 **Новая заметка (`/note`) в формате Markdown (`.md`)**:
   - Прием **голосовых сообщений (голос / аудио)** или текста.
   - Распознавание речи через STT (Gemini / Whisper).
   - Интеллектуальное структурирование: автоматический подбор емкого заголовка, тегов, списков задач (`- [ ]`) и сохранение готового `.md` файла в вашу папку заметок (отлично интегрируется с **Obsidian**, **Logseq** или **Nextcloud**).

6. 📊 **Статус бота и системы (`/status`)**:
   - Отображение аптайма, потребления памяти (RAM), статуса AI-провайдера, выбранного языка, свободного места на дисках ZimaBoard и счетчиков сохраненных файлов и заметок.

---

## 🏗 Структура проекта

```
helper_translater/
├── docker-compose.yml         # Манифест Docker Compose для ZimaOS
├── Dockerfile                 # Docker-образ с Python 3.11 и ffmpeg
├── .env.example               # Шаблон настроек и ключей
├── requirements.txt           # Зависимости Python
├── config.py                  # Конфигурация и переменные окружения
├── main.py                    # Точка входа приложения
├── bot/
│   ├── texts.py               # Единый модуль локализации (RU, EN, HE)
│   ├── handlers/
│   │   ├── commands.py        # /start, /help, /status, /translate, /analyze, /save, /note, /lang
│   │   ├── media.py           # Обработка фото, PDF, DOCX (по умолчанию режим analyze)
│   │   ├── notes.py           # Обработка аудио/голоса и текста для заметок
│   │   └── actions.py         # Обработчики интерактивных кнопок под сообщениями и смены языка
│   ├── services/
│   │   ├── ai_service.py      # Модули перевода, анализа и структурирования (Gemini / OpenAI)
│   │   ├── user_settings.py   # Сохранение настроек языка пользователей
│   │   ├── doc_parser.py      # Парсинг PDF, DOCX и валидация изображений
│   │   ├── stt_service.py     # Распознавание речи (STT)
│   │   ├── storage_service.py # Запись файлов в облако и генерация .md заметок
│   │   └── system_status.py   # Мониторинг ресурсов, диска и аптайма для /status
│   ├── middlewares/
│   │   ├── auth.py            # Авторизация доступа
│   │   └── language.py        # Автоматическое определение языка пользователя
│   ├── keyboards/
│   │   ├── reply.py           # Постоянное меню внизу чата
│   │   └── inline.py          # Кнопки быстрых действий под сообщениями и выбор языка
│   ├── middlewares/
│   │   └── auth.py            # Ограничение доступа по ALLOWED_USER_IDS
│   └── states.py              # FSM состояния диалога
└── data/                      # Папки хранения и конфигурации (монтируются в ZimaOS)
    ├── config/                # Конфигурация (.env)
    ├── cloud/                 # Сохраненные медиафайлы
    └── notes/                 # Сохраненные заметки (.md)
```

---

## ⚙️ Настройка окружения (`data/config/.env`)

Файл конфигурации бота располагается по пути: **`data/config/.env`**.

Создайте и заполните его на основе шаблона:
```bash
mkdir -p data/config
cp data/config/.env.example data/config/.env
```
*(или используйте `cp .env.example data/config/.env`)*

Заполните параметры:

| Переменная | Описание | Пример / По умолчанию |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Токен бота от [@BotFather](https://t.me/BotFather) | `123456789:ABCdef...` |
| `ALLOWED_USER_IDS` | Разрешенные ID пользователей (через запятую). Если пусто — бот публичный | `123456789,987654321` |
| `AI_PROVIDER` | AI-провайдер: `gemini` (рекомендуется) или `openai` | `gemini` |
| `GEMINI_API_KEY` | API-ключ Google AI Studio (для Gemini) | `AIzaSy...` |
| `GEMINI_MODEL` | Модель Gemini для Vision, аудио и текста | `gemini-3.8-flash` |
| `GEMINI_FALLBACK_MODELS` | Резервные модели через запятую при перегрузке (503/429) | `gemini-3.7-flash,gemini-3.6-flash,gemini-3.5-flash,gemini-flash-latest` |
| `OPENAI_API_KEY` | API-ключ OpenAI (если выбран провайдер openai) | `sk-...` |
| `DEFAULT_ACTION` | Действие по умолчанию при отправке документов | `analyze` |
| `HOST_CONFIG_PATH` | Путь к папке config на сервере ZimaOS | `/DATA/AppData/helper_translater/config` или `./data/config` |
| `HOST_CLOUD_PATH` | Путь к папке облака на сервере ZimaOS | `/DATA/AppData/helper_translater/cloud` или `./data/cloud` |
| `HOST_NOTES_PATH` | Путь к папке заметок на сервере ZimaOS | `/DATA/AppData/helper_translater/notes` или `./data/notes` |
| `TZ` | Часовой пояс | `Europe/Moscow` |

---

## 🐳 Запуск в Docker: Подробная инструкция

Приложение упаковано в легковесный Docker-образ на базе `python:3.11-slim` со встроенным `ffmpeg` для обработки голосовых сообщений и поддержкой multi-arch (`linux/amd64` и `linux/arm64` — ZimaBoard, Raspberry Pi, VPS, локальный ПК).

---

### 📋 1. Предварительные требования

Перед запуском убедитесь, что на целевой системе установлены:
- **Docker Engine** (версия 20.10+) и **Docker Compose** (рекомендуется плагин `docker compose` v2).
  ```bash
  docker --version
  docker compose version
  ```
- **Telegram Bot Token**: создайте бота в Telegram через [@BotFather](https://t.me/BotFather) и скопируйте токен вида `123456789:ABCdef...`.
- **API-ключ искусственного интеллекта**:
  - **Google Gemini** *(рекомендуется)*: бесплатный ключ в [Google AI Studio](https://aistudio.google.com/).
  - или **OpenAI**: ключ на платформе [OpenAI Platform](https://platform.openai.com/).

---

### 📁 2. Подготовка файлов и окружения

1. **Склонируйте репозиторий** (или загрузите архив с проектом):
   ```bash
   git clone https://github.com/rokhlin/helper_translater.git
   cd helper_translater
   ```

2. **Создайте необходимые локальные директории**:
   Контейнер монтирует три директории на хосте для сохранения настроек, загруженных документов и Markdown-заметок:
   ```bash
   mkdir -p data/config data/cloud data/notes
   ```

3. **Создайте и настройте файл переменных окружения `.env`**:
   Скопируйте эталонный шаблон `.env.example` в `data/config/.env`:
   ```bash
   cp .env.example data/config/.env
   ```
   > [!IMPORTANT]
   > Файл конфигурации должен находиться именно по пути **`data/config/.env`** (либо в корне проекта как `.env`).

   Откройте файл в любом текстовом редакторе (например, `nano`):
   ```bash
   nano data/config/.env
   ```
   Заполните обязательные параметры:
   ```dotenv
   TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ
   ALLOWED_USER_IDS=123456789              # Ваш Telegram ID (узнать можно у @userinfobot)
   AI_PROVIDER=gemini
   GEMINI_API_KEY=AIzaSyD-Ваш-Ключ-Gemini
   GEMINI_MODEL=gemini-3.8-flash
   DEFAULT_ACTION=analyze                  # Режим по умолчанию при отправке фото/документов
   TZ=Europe/Moscow
   ```

4. **Настройте права доступа (для Linux / ZimaOS)**:
   Чтобы контейнер без ошибок записывал файлы в `data/cloud` и `data/notes`:
   ```bash
   chmod -R 775 data
   ```

---

### 🚀 3. Варианты запуска контейнера

Выберите наиболее удобный для вас вариант запуска:

#### Вариант А: Запуск через Docker Compose (Рекомендуемый)

Файл [`docker-compose.yml`](file:///c:/projects/helper_translater/docker-compose.yml) уже настроен со всеми монтируемыми томами, автоматическим перезапуском и ротацией логов.

1. **Сборка образа и запуск в фоновом режиме (daemon)**:
   ```bash
   docker compose up -d --build
   ```
   *Параметр `--build` гарантирует сборку актуального локального кода.*

2. **Проверка статуса контейнера**:
   ```bash
   docker compose ps
   ```
   Вы должны увидеть сервис `helper_translater_bot` со статусом `Up`.

3. **Просмотр логов в реальном времени**:
   ```bash
   docker compose logs -f telegram-helper-bot
   ```
   *(Для выхода из просмотра логов нажмите `Ctrl + C`).*

4. **Управление контейнером**:
   - **Остановить контейнер**:
     ```bash
     docker compose down
     ```
   - **Перезапустить бота** (например, после изменения `.env`):
     ```bash
     docker compose restart
     ```
   - **Обновить бота до последней версии из Git**:
     ```bash
     git pull
     docker compose up -d --build
     ```

---

#### Вариант Б: Запуск напрямую через Docker CLI (`docker run`)

Если вы предпочитаете управлять контейнером без Docker Compose:

1. **Соберите Docker-образ вручную**:
   ```bash
   docker build -t helper_translater_bot:latest .
   ```

2. **Запустите контейнер с привязкой папок и файла конфигурации**:
   - **Для Linux / macOS / ZimaOS (Bash)**:
     ```bash
     docker run -d \
       --name helper_translater_bot \
       --restart unless-stopped \
       --env-file ./data/config/.env \
       -e TZ=Europe/Moscow \
       -v "$(pwd)/data/config:/app/data/config" \
       -v "$(pwd)/data/cloud:/app/data/cloud" \
       -v "$(pwd)/data/notes:/app/data/notes" \
       helper_translater_bot:latest
     ```
   - **Для Windows (PowerShell)**:
     ```powershell
     docker run -d `
       --name helper_translater_bot `
       --restart unless-stopped `
       --env-file ./data/config/.env `
       -e TZ=Europe/Moscow `
       -v "${PWD}/data/config:/app/data/config" `
       -v "${PWD}/data/cloud:/app/data/cloud" `
       -v "${PWD}/data/notes:/app/data/notes" `
       helper_translater_bot:latest
     ```

3. **Команды управления**:
   ```bash
   # Просмотр логов
   docker logs -f helper_translater_bot

   # Остановка
   docker stop helper_translater_bot

   # Перезапуск
   docker restart helper_translater_bot

   # Удаление контейнера
   docker rm -f helper_translater_bot
   ```

---

#### Вариант В: Запуск готового Multi-Arch образа из GitHub Packages (GHCR)

Если вы не хотите собирать образ из исходников (например, на сервере со слабой мощностью), используйте готовый предсобранный образ из GitHub Container Registry:

1. **Скачайте актуальный образ**:
   ```bash
   docker pull ghcr.io/rokhlin/rav_assistant:latest
   ```

2. **Запустите готовый образ одной командой**:
   ```bash
   docker run -d \
     --name helper_translater_bot \
     --restart unless-stopped \
     --env-file ./data/config/.env \
     -v "$(pwd)/data/config:/app/data/config" \
     -v "$(pwd)/data/cloud:/app/data/cloud" \
     -v "$(pwd)/data/notes:/app/data/notes" \
     ghcr.io/rokhlin/rav_assistant:latest
   ```

3. **Или используйте в `docker-compose.yml`**:
   Замените секцию `build: .` на:
   ```yaml
   image: ghcr.io/rokhlin/rav_assistant:latest
   ```
   и выполните `docker compose up -d`.

---

#### Вариант Г: Установка через Web-интерфейс ZimaOS / CasaOS / Portainer

Если бот развертывается на домашнем сервере **ZimaBoard / ZimaOS**:

1. Откройте веб-панель ZimaOS (`http://<IP-адрес-ZimaBoard>`).
2. Перейдите в **App Store** ➔ в правом верхнем углу нажмите **Custom Install** (Пользовательская установка).
3. Нажмите кнопку **Import** в левом верхнем углу модального окна и вставьте содержимое файла [`docker-compose.yml`](file:///c:/projects/helper_translater/docker-compose.yml).
   > [!NOTE]
   > Благодаря блоку `x-casaos` и секции `ports`, ZimaOS автоматически заполнит порт веб-интерфейса (`8080`), название и иконку бота.
4. Проверьте проброс портов (**Ports**):
   - Хост `8080` ➔ Контейнер `8080` (веб-дашборд статуса и мониторинга)
5. Настройте пути монтирования папок (**Volumes**):
   - Хост `/DATA/AppData/helper_translater/config` ➔ Контейнер `/app/data/config`
   - Хост `/DATA/Documents/TelegramCloud` ➔ Контейнер `/app/data/cloud` *(сюда будут сохраняться файлы)*
   - Хост `/DATA/Documents/ObsidianVault` ➔ Контейнер `/app/data/notes` *(сюда будут записываться заметки `.md`)*
6. В разделе **Environment Variables** добавьте переменные:
   - `TELEGRAM_BOT_TOKEN`: ваш токен бота
   - `GEMINI_API_KEY`: ваш ключ Gemini API
   - `ALLOWED_USER_IDS`: ваш Telegram ID
   - `TZ`: `Europe/Moscow`
7. Нажмите **Submit / Install**. Контейнер автоматически скачается, настроится и запустится.
   При клике на карточку приложения на рабочем столе ZimaOS откроется страница статуса и мониторинга бота (`http://<IP-ZimaBoard>:8080`).

---

### 🔍 4. Проверка работы и мониторинг

1. **Веб-интерфейс мониторинга**:
   Откройте в браузере `http://<IP-ZimaBoard>:8080` — отобразится дашборд с Uptime, потреблением памяти, статусом AI-провайдера, количеством сохраненных файлов и заметок. Также доступен эндпоинт здоровья `/health`.

2. **Логи контейнера**:
   Выполните `docker compose logs -f` (или `docker logs -f helper_translater_bot`). При корректном старте вывод будет содержать:
   ```text
   [INFO] helper_bot: Команды меню бота успешно зарегистрированы в Telegram
   [INFO] helper_bot: Запуск бота... Провайдер AI: gemini
   [INFO] helper_bot: Папка облака: /app/data/cloud
   [INFO] helper_bot: Папка заметок: /app/data/notes
   ```
2. **Проверка в Telegram**:
   - Откройте вашего бота в Telegram и отправьте команду `/start`.
   - Отправьте команду `/status` — бот пришлет сообщение с информацией о времени непрерывной работы (uptime), используемом AI-провайдере, свободной RAM и объеме свободного места на диске.

---

### 🛠 5. Частые проблемы и их решение (Troubleshooting)

| Проблема / Ошибка | Причина | Решение |
|---|---|---|
| `Критическая ошибка: TELEGRAM_BOT_TOKEN не задан` | Контейнер не видит `.env` или токен пустой | Проверьте, что файл `data/config/.env` создан, не содержит пробелов вокруг `=` и смонтирован по пути `/app/data/config/.env`. |
| `PermissionError: [Errno 13] Permission denied` | У пользователя в контейнере нет прав на запись в смонтированные папки хоста | Выполните на хосте `chmod -R 775 ./data` или `chown -R 1000:1000 ./data`. |
| Бот не отвечает в Telegram при отправке сообщений | Ваш Telegram ID не указан в списке разрешенных пользователей | Если заполнена переменная `ALLOWED_USER_IDS`, бот игнорирует всех посторонних. Узнайте свой ID через [@userinfobot](https://t.me/userinfobot) и добавьте его в `.env`. Оставьте пустым, если бот должен отвечать всем. |
| Ошибка вызова Gemini / OpenAI API | Неверный API-ключ или отсутствие доступа к сети/DNS | Проверьте валидность API ключа, лимиты в консоли провайдера и доступность внешних хостов из контейнера (`docker run --rm alpine ping -c 2 api.telegram.org`). |
| Изменения в `.env` не вступили в силу | Переменные окружения считываются только при старте процесса | Перезапустите контейнер: `docker compose restart` (или `docker compose up -d` при изменении compose-файла). |

---

## 📱 Меню и команды в Telegram

- `/start` — Перезапуск бота и отображение главного меню.
- `/analyze` — Включение режима «Анализ и перевод».
- `/translate` — Включение режима «Перевод».
- `/save` — Включение режима прямого сохранения в облако.
- `/note` — Создание новой заметки (текст или голос).
- `/status` — Просмотр состояния бота, хранилища и свободной памяти.
- `/help` — Подробная справка.

### Инлайн-кнопки
Под каждым сообщением с анализом документа бот предлагает кнопки:
- `[ 🌐 Перевести ]` — получить чистый полный перевод.
- `[ 🔍 Анализ и перевод ]` — повторно разобрать документ.
- `[ 💾 В облако ]` — сохранить исходный файл в сетевую папку.
- `[ 📝 Сохранить как заметку ]` — сформировать Markdown-заметку из результатов анализа.

---

## 🧪 Запуск тестов локально

```bash
python -m pytest tests/test_core.py -v
```
Все тесты парсеров (DOCX, PDF, изображения), генерации заметок и статуса системы проходят успешно.
