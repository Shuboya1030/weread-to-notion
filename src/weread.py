"""微信读书非官方 API 封装"""

import requests

from config import WEREAD_BASE_URL, WEREAD_HEADERS


class CookieExpiredError(Exception):
    """Cookie 已过期，需要手动刷新"""
    pass


def _get(path: str, params: dict | None = None) -> dict:
    """发送 GET 请求到微信读书 API，自动检测 cookie 过期"""
    url = f"{WEREAD_BASE_URL}{path}"
    resp = requests.get(url, headers=WEREAD_HEADERS, params=params, allow_redirects=False)

    print(f"  [DEBUG] {path} -> HTTP {resp.status_code}")

    if resp.status_code in (401, 302, 403):
        print(f"  [DEBUG] Response: {resp.text[:500]}")
        raise CookieExpiredError(
            "微信读书 cookie 已过期！请重新登录 https://weread.qq.com/ 并更新 WEREAD_COOKIE。"
        )

    resp.raise_for_status()
    data = resp.json()

    # 部分接口过期时返回 errCode 而非 HTTP 401
    if isinstance(data, dict) and data.get("errCode"):
        print(f"  [DEBUG] errCode={data.get('errCode')}, errMsg={data.get('errMsg', '')}")
        raise CookieExpiredError(
            f"微信读书 API 错误（errCode={data['errCode']}）。请重新登录 https://weread.qq.com/ 并更新 WEREAD_COOKIE。"
        )

    return data


def get_notebooks() -> list[dict]:
    """获取所有有笔记的书籍列表

    返回格式：[{bookId, book: {title, author, cover, ...}, noteCount, reviewCount, ...}]
    """
    data = _get("/user/notebooks")
    return data.get("books", [])


def get_book_info(book_id: str) -> dict:
    """获取书籍元数据（书名、作者、封面、分类等）"""
    return _get("/book/info", params={"bookId": book_id})


def get_bookmarks(book_id: str) -> list[dict]:
    """获取指定书的所有划线（highlights）

    返回格式：[{bookmarkId, chapterUid, chapterName, markText, createTime, ...}]
    """
    data = _get("/book/bookmarklist", params={"bookId": book_id})
    return data.get("updated", [])


def get_reviews(book_id: str) -> list[dict]:
    """获取指定书的所有想法/笔记（thoughts）

    返回格式：[{reviewId, chapterUid, chapterName, content, createTime, ...}]
    """
    data = _get(
        "/review/list",
        params={
            "bookId": book_id,
            "listType": 11,
            "mine": 1,
            "synckey": 0,
        },
    )
    return data.get("reviews", [])


def get_chapters(book_id: str) -> list[dict]:
    """获取书籍章节结构

    返回格式：[{chapterUid, chapterIdx, title, ...}]
    """
    data = _get("/book/chapterInfos", params={"bookIds": book_id})
    # API 返回 {data: [{bookId, updated: [chapters]}]}
    book_data = data.get("data", [])
    if book_data:
        return book_data[0].get("updated", [])
    return []


def get_all_book_data(book_id: str) -> dict:
    """一次性获取一本书的所有数据：元数据 + 划线 + 想法 + 章节"""
    info = get_book_info(book_id)
    bookmarks = get_bookmarks(book_id)
    reviews = get_reviews(book_id)
    chapters = get_chapters(book_id)

    return {
        "info": info,
        "bookmarks": bookmarks,
        "reviews": reviews,
        "chapters": chapters,
    }
