import logging
from aiohttp import web
from config import settings
from bot.services.system_status import status_service

logger = logging.getLogger("web_server")

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Telegram Helper Bot — Status</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #0d1117;
            --card-bg: rgba(22, 27, 34, 0.8);
            --card-border: rgba(48, 54, 61, 0.8);
            --text-primary: #f0f6fc;
            --text-secondary: #8b949e;
            --accent-blue: #2f81f7;
            --accent-green: #238636;
            --accent-yellow: #d29922;
            --badge-green: rgba(35, 134, 54, 0.2);
            --badge-text-green: #3fb950;
            --badge-yellow: rgba(210, 153, 34, 0.2);
            --badge-text-yellow: #d29922;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-primary);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 24px;
            background-image: radial-gradient(circle at top right, rgba(47, 129, 247, 0.12), transparent 400px),
                              radial-gradient(circle at bottom left, rgba(35, 134, 54, 0.08), transparent 400px);
        }

        .container {
            width: 100%;
            max-width: 640px;
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 16px;
            padding: 32px;
            backdrop-filter: blur(12px);
            box-shadow: 0 16px 32px rgba(0, 0, 0, 0.4);
        }

        .header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 24px;
            padding-bottom: 20px;
            border-bottom: 1px solid var(--card-border);
        }

        .header-title {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .logo {
            width: 44px;
            height: 44px;
            border-radius: 12px;
            background: linear-gradient(135deg, #2AABEE, #229ED9);
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 4px 12px rgba(42, 171, 238, 0.35);
        }

        .logo svg {
            width: 24px;
            height: 24px;
            fill: #ffffff;
        }

        h1 {
            font-size: 20px;
            font-weight: 700;
            letter-spacing: -0.01em;
        }

        .subtitle {
            font-size: 13px;
            color: var(--text-secondary);
        }

        .badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }

        .badge-online {
            background: var(--badge-green);
            color: var(--badge-text-green);
            border: 1px solid rgba(63, 185, 80, 0.3);
        }

        .badge-warn {
            background: var(--badge-yellow);
            color: var(--badge-text-yellow);
            border: 1px solid rgba(210, 153, 34, 0.3);
        }

        .pulse {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: currentColor;
            animation: pulse 2s infinite ease-in-out;
        }

        @keyframes pulse {
            0% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.4; transform: scale(1.2); }
            100% { opacity: 1; transform: scale(1); }
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }

        .stat-card {
            background: rgba(13, 17, 23, 0.6);
            border: 1px solid var(--card-border);
            border-radius: 12px;
            padding: 16px;
        }

        .stat-label {
            font-size: 12px;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 6px;
        }

        .stat-value {
            font-size: 16px;
            font-weight: 600;
            color: var(--text-primary);
        }

        .footer {
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 12px;
            color: var(--text-secondary);
            padding-top: 16px;
            border-top: 1px solid var(--card-border);
        }

        .btn-telegram {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: #2481cc;
            color: #ffffff;
            text-decoration: none;
            padding: 8px 14px;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 500;
            transition: background 0.2s ease;
        }

        .btn-telegram:hover {
            background: #1e70b3;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="header-title">
                <div class="logo">
                    <svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 00-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.55-.37-.63-.2-1.12-.31-1.08-.66.02-.18.27-.36.75-.55 2.92-1.27 4.86-2.11 5.83-2.52 2.78-1.16 3.35-1.36 3.73-1.36.08 0 .27.02.39.12.1.08.13.19.14.27-.01.06.01.24 0 .37z"/></svg>
                </div>
                <div>
                    <h1>Telegram Helper Bot</h1>
                    <div class="subtitle">ZimaOS / CasaOS Service Container</div>
                </div>
            </div>
            {{STATUS_BADGE}}
        </div>

        <div class="grid">
            <div class="stat-card">
                <div class="stat-label">Время работы (Uptime)</div>
                <div class="stat-value">{{UPTIME}}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Потребление памяти (RAM)</div>
                <div class="stat-value">{{MEMORY_MB}} MB</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">AI Движок</div>
                <div class="stat-value">{{PROVIDER}}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Действие по умолчанию</div>
                <div class="stat-value">{{DEFAULT_ACTION}}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Файлы в Облаке (/cloud)</div>
                <div class="stat-value">{{CLOUD_FILES_COUNT}} шт.</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Заметки Markdown (/notes)</div>
                <div class="stat-value">{{NOTES_COUNT}} шт.</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Свободно на диске</div>
                <div class="stat-value">{{DISK_STR}}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">ОС / Платформа</div>
                <div class="stat-value" style="font-size: 13px;">{{SYSTEM}}</div>
            </div>
        </div>

        <div class="footer">
            <span>Статус: <strong>Работает в фоновом режиме</strong></span>
            <a href="https://t.me" target="_blank" class="btn-telegram">
                Открыть в Telegram
            </a>
        </div>
    </div>
</body>
</html>
"""

async def handle_dashboard(request: web.Request) -> web.Response:
    s = status_service.get_status()
    if s["api_ready"]:
        badge = '<span class="badge badge-online"><span class="pulse"></span>Online</span>'
    else:
        badge = '<span class="badge badge-warn"><span class="pulse"></span>API Key Required</span>'

    disk_str = f"{s['disk_free_gb']} GB из {s['disk_total_gb']} GB" if s["disk_free_gb"] > 0 else "Недоступно"

    html = (
        HTML_TEMPLATE
        .replace("{{STATUS_BADGE}}", badge)
        .replace("{{UPTIME}}", str(s["uptime"]))
        .replace("{{MEMORY_MB}}", str(s["memory_mb"]))
        .replace("{{PROVIDER}}", str(s["provider"]))
        .replace("{{DEFAULT_ACTION}}", str(s["default_action"]))
        .replace("{{CLOUD_FILES_COUNT}}", str(s["cloud_files_count"]))
        .replace("{{NOTES_COUNT}}", str(s["notes_count"]))
        .replace("{{DISK_STR}}", disk_str)
        .replace("{{SYSTEM}}", str(s["system"]))
    )
    return web.Response(text=html, content_type="text/html", charset="utf-8")

async def handle_health(request: web.Request) -> web.Response:
    s = status_service.get_status()
    return web.json_response({
        "status": "healthy",
        "bot": "online",
        "uptime": s["uptime"],
        "api_ready": s["api_ready"],
        "memory_mb": s["memory_mb"],
        "cloud_files": s["cloud_files_count"],
        "notes": s["notes_count"]
    })

async def start_web_server(port: int = 8080) -> web.AppRunner:
    app = web.Application()
    app.router.add_get("/", handle_dashboard)
    app.router.add_get("/health", handle_health)
    app.router.add_get("/api/status", handle_health)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Веб-сервер статуса запущен на http://0.0.0.0:{port}")
    return runner
