"""Notion 数据库同步逻辑"""

from datetime import datetime, timezone

from notion_client import Client

from config import NOTION_TOKEN, NOTION_DATABASE_ID


notion = Client(auth=NOTION_TOKEN)


def get_synced_books() -> dict[str, dict]:
    """查询 Notion 数据库中已同步的书籍

    返回：{bookId: {page_id, note_count}} 映射
    """
    synced = {}
    has_more = True
    start_cursor = None

    while has_more:
        kwargs = {"database_id": NOTION_DATABASE_ID, "page_size": 100}
        if start_cursor:
            kwargs["start_cursor"] = start_cursor

        result = notion.databases.query(**kwargs)

        for page in result["results"]:
            props = page["properties"]
            book_id_prop = props.get("BookId", {})
            rich_text = book_id_prop.get("rich_text", [])
            if rich_text:
                book_id = rich_text[0]["plain_text"]
                note_count_prop = props.get("笔记数量", {})
                note_count = note_count_prop.get("number", 0) or 0
                synced[book_id] = {
                    "page_id": page["id"],
                    "note_count": note_count,
                }

        has_more = result.get("has_more", False)
        start_cursor = result.get("next_cursor")

    return synced


def create_book_page(
    book_info: dict,
    bookmarks: list[dict],
    reviews: list[dict],
    chapters: list[dict],
    labels: list[str],
) -> str:
    """在 Notion 数据库中创建一本书的页面

    返回：创建的 page_id
    """
    book_id = str(book_info.get("bookId", ""))
    title = book_info.get("title", "未知书名")
    author = book_info.get("author", "未知作者")
    cover = book_info.get("cover", "")
    category = book_info.get("category", "")
    # category 有时是 categoryName，有时是 category
    if not category:
        category = book_info.get("categoryName", "")

    total_notes = len(bookmarks) + len(reviews)

    # 构建页面属性
    properties = {
        "书名": {"title": [{"text": {"content": title}}]},
        "作者": {"rich_text": [{"text": {"content": author}}]},
        "BookId": {"rich_text": [{"text": {"content": book_id}}]},
        "笔记数量": {"number": total_notes},
        "最后同步": {"date": {"start": datetime.now(timezone.utc).isoformat()}},
    }

    if category:
        properties["分类"] = {"select": {"name": category}}

    if labels:
        properties["主题标签"] = {
            "multi_select": [{"name": label} for label in labels]
        }

    # 构建页面内容（按章节组织）
    children = _build_page_content(bookmarks, reviews, chapters)

    # 封面图片
    page_kwargs = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": properties,
        "children": children[:100],  # Notion API 单次最多 100 个 block
    }

    if cover:
        page_kwargs["cover"] = {"type": "external", "external": {"url": cover}}

    page = notion.pages.create(**page_kwargs)
    page_id = page["id"]

    # 如果内容超过 100 个 block，分批追加
    remaining = children[100:]
    while remaining:
        batch = remaining[:100]
        remaining = remaining[100:]
        notion.blocks.children.append(block_id=page_id, children=batch)

    return page_id


def append_new_notes(
    page_id: str,
    bookmarks: list[dict],
    reviews: list[dict],
    chapters: list[dict],
    existing_note_count: int,
) -> int:
    """向已有页面追加新笔记

    返回：新增的笔记数量
    """
    total_notes = len(bookmarks) + len(reviews)
    new_count = total_notes - existing_note_count

    if new_count <= 0:
        return 0

    # 追加一个分隔符 + 新内容
    divider = {"object": "block", "type": "divider", "divider": {}}
    header = {
        "object": "block",
        "type": "heading_3",
        "heading_3": {
            "rich_text": [
                {
                    "text": {
                        "content": f"📌 新增同步 ({datetime.now().strftime('%Y-%m-%d')})"
                    }
                }
            ]
        },
    }

    # 重新构建全部内容中最新的部分
    # 简单策略：取最后 new_count 条 bookmark/review（按时间排序）
    all_items = []
    for bm in bookmarks:
        all_items.append(
            {"type": "bookmark", "chapterUid": bm.get("chapterUid", 0), "data": bm}
        )
    for rv in reviews:
        review_data = rv.get("review", rv)
        all_items.append(
            {
                "type": "review",
                "chapterUid": review_data.get("chapterUid", 0),
                "data": review_data,
            }
        )

    all_items.sort(key=lambda x: x["data"].get("createTime", 0))
    new_items = all_items[-new_count:]

    children = [divider, header]
    for item in new_items:
        if item["type"] == "bookmark":
            children.append(_make_quote_block(item["data"].get("markText", "")))
        else:
            content = item["data"].get("content", "")
            children.append(_make_callout_block(content))

    # 追加到页面
    batch = children[:100]
    notion.blocks.children.append(block_id=page_id, children=batch)

    # 更新笔记数量和同步时间
    notion.pages.update(
        page_id=page_id,
        properties={
            "笔记数量": {"number": total_notes},
            "最后同步": {
                "date": {"start": datetime.now(timezone.utc).isoformat()}
            },
        },
    )

    return new_count


def _build_page_content(
    bookmarks: list[dict],
    reviews: list[dict],
    chapters: list[dict],
) -> list[dict]:
    """按章节组织划线和想法，生成 Notion block 列表"""

    # 建立 chapterUid -> chapter 映射
    chapter_map = {}
    for ch in chapters:
        uid = ch.get("chapterUid", 0)
        chapter_map[uid] = ch

    # 按 chapterUid 分组所有笔记
    notes_by_chapter: dict[int, list[dict]] = {}

    for bm in bookmarks:
        uid = bm.get("chapterUid", 0)
        notes_by_chapter.setdefault(uid, []).append(
            {
                "type": "bookmark",
                "text": bm.get("markText", ""),
                "time": bm.get("createTime", 0),
            }
        )

    for rv in reviews:
        review_data = rv.get("review", rv)
        uid = review_data.get("chapterUid", 0)
        notes_by_chapter.setdefault(uid, []).append(
            {
                "type": "review",
                "text": review_data.get("content", ""),
                "time": review_data.get("createTime", 0),
            }
        )

    # 按章节顺序排列
    sorted_uids = sorted(
        notes_by_chapter.keys(),
        key=lambda uid: chapter_map.get(uid, {}).get("chapterIdx", 999),
    )

    blocks = []
    for uid in sorted_uids:
        # 章节标题
        ch = chapter_map.get(uid, {})
        chapter_title = ch.get("title", "其他笔记")
        blocks.append(_make_heading_block(chapter_title))

        # 该章节的笔记（按时间排序）
        notes = sorted(notes_by_chapter[uid], key=lambda n: n["time"])
        for note in notes:
            if note["type"] == "bookmark":
                blocks.append(_make_quote_block(note["text"]))
            else:
                blocks.append(_make_callout_block(note["text"]))

    return blocks


def _make_heading_block(text: str) -> dict:
    return {
        "object": "block",
        "type": "heading_2",
        "heading_2": {
            "rich_text": [{"text": {"content": _truncate(text, 2000)}}]
        },
    }


def _make_quote_block(text: str) -> dict:
    return {
        "object": "block",
        "type": "quote",
        "quote": {
            "rich_text": [{"text": {"content": _truncate(text, 2000)}}]
        },
    }


def _make_callout_block(text: str) -> dict:
    return {
        "object": "block",
        "type": "callout",
        "callout": {
            "rich_text": [{"text": {"content": _truncate(text, 2000)}}],
            "icon": {"type": "emoji", "emoji": "💭"},
        },
    }


def _truncate(text: str, max_len: int) -> str:
    """Notion API 限制 rich_text 单段最长 2000 字符"""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."
