FROM python:3.11-slim

# Установка системных зависимостей (ffmpeg для конвертации аудио, tzdata для таймзоны)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Установка зависимостей Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY . .

# Создание каталогов для данных и конфигурации
RUN mkdir -p /app/data/config /app/data/cloud /app/data/notes

ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]
