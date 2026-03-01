"""微信读书 API 封装（使用 weread.qq.com/web/ 接口）"""

import requests

from config import WEREAD_BASE_URL, WEREAD_HEADERS


class CookieExpiredError(Exception):
    """Cookie 已过期，需要手动刷新"""
    pass


def _get(path: str, params: dict | None = None) -> dict:
    """发送 GET 请求到微信读书 API，自动检测 cookie 过期"""
    url = f"{WEREAD_BASE_URL}{path}"
    resp = requests.get(url, headers=WEREAD_HEADERS, params=params, allow_redirects=False)

    if resp.status_code in (401, 302, 403):
        raise CookieExpiredError(
            "微信读书 cookie 已过期！请重新登录 https://weread.qq.com/ 并更新 WEREAD_COOKIE。"
        )

    resp.raise_for_status()
    data = resp.json()

    if isinstance(data, dict) and (data.get("errcode") or data.get("errCode")):
        err = data.get("errcode") or data.get("errCode")
        raise CookieExpiredError(
            f"微信读书 API 错误（errCode={err}）。请重新登录 https://weread.qq.com/ 并更新 WEREAD_COOKIE。"
        )

    return data


def get_shelf_books() -> list[dict]:
    """获取书架上的所有书籍（含元数据）

    返回：[{bookId, title, author, cover, category, ...}]
    """
    data = _get("/web/shelf/sync", params={"synckey": 0, "lectureSynckey": 0})
    return data.get("books", [])


def get_book_info(book_id: str) -> dict:
    """获取书籍元数据"""
    return _get("/web/book/info", params={"bookId": book_id})


def get_bookmarks(book_id: str) -> tuple[list[dict], list[dict]]:
    """获取指定书的划线和章节信息

    返回：(bookmarks, chapters)
    """
    data = _get("/web/book/bookmarklist", params={"bookId": book_id})
    bookmarks = data.get("updated", [])
    chapters = data.get("chapters", [])
    return bookmarks, chapters


def get_reviews(book_id: str) -> list[dict]:
    """获取指定书的想法/笔记"""
    data = _get(
        "/web/review/list",
        params={
            "bookId": book_id,
            "listType": 11,
            "mine": 1,
            "synckey": 0,
        },
    )
    return data.get("reviews", [])


def get_all_book_data(book_id: str) -> dict:
    """一次性获取一本书的所有笔记数据"""
    bookmarks, chapters = get_bookmarks(book_id)
    reviews = get_reviews(book_id)

    return {
        "bookmarks": bookmarks,
        "reviews": reviews,
        "chapters": chapters,
    }
