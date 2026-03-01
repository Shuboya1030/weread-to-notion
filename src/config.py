import os


WEREAD_COOKIE = os.environ["WEREAD_COOKIE"]
NOTION_TOKEN = os.environ["NOTION_TOKEN"]
NOTION_DATABASE_ID = os.environ["NOTION_DATABASE_ID"]
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

WEREAD_BASE_URL = "https://i.weread.qq.com"

WEREAD_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Cookie": WEREAD_COOKIE,
}
