"""微信读书 → Notion 同步主流程"""

import sys
import time

from weread import get_notebooks, get_all_book_data, CookieExpiredError
from notion_sync import get_synced_books, create_book_page, append_new_notes
from labeler import generate_labels


def main():
    print("🔄 开始同步微信读书笔记到 Notion...")

    # 1. 从微信读书获取有笔记的书籍列表
    try:
        notebooks = get_notebooks()
    except CookieExpiredError as e:
        print(f"\n❌ {e}")
        print("请更新 WEREAD_COOKIE 环境变量（或 GitHub Secrets）后重试。")
        sys.exit(1)

    print(f"📚 微信读书中有 {len(notebooks)} 本书包含笔记")

    if not notebooks:
        print("没有需要同步的笔记，退出。")
        return

    # 2. 从 Notion 获取已同步的书籍
    synced = get_synced_books()
    print(f"📋 Notion 中已同步 {len(synced)} 本书")

    new_books = 0
    updated_books = 0
    skipped_books = 0

    # 3. 逐本处理
    for notebook in notebooks:
        book = notebook.get("book", {})
        book_id = str(book.get("bookId", ""))
        title = book.get("title", "未知")

        if not book_id:
            continue

        try:
            if book_id not in synced:
                # 新书：获取全部数据 + AI 打标签 + 创建页面
                print(f"\n📖 新书：{title}")
                book_data = get_all_book_data(book_id)

                # AI 生成主题标签
                sample_highlights = [
                    bm.get("markText", "")
                    for bm in book_data["bookmarks"][:10]
                ]
                labels = generate_labels(
                    title=title,
                    author=book.get("author", ""),
                    category=book.get("category", ""),
                    sample_highlights=sample_highlights,
                )
                if labels:
                    print(f"   🏷️  标签：{', '.join(labels)}")

                create_book_page(
                    book_info={**book, **book_data["info"]},
                    bookmarks=book_data["bookmarks"],
                    reviews=book_data["reviews"],
                    chapters=book_data["chapters"],
                    labels=labels,
                )
                print(f"   ✅ 已创建（{len(book_data['bookmarks'])} 条划线，{len(book_data['reviews'])} 条想法）")
                new_books += 1

            else:
                # 已有书：检查是否有新笔记
                existing = synced[book_id]
                current_count = (
                    notebook.get("bookmarkCount", 0)
                    + notebook.get("reviewCount", 0)
                )

                if current_count > existing["note_count"]:
                    print(f"\n📝 更新：{title}（新增 {current_count - existing['note_count']} 条笔记）")
                    book_data = get_all_book_data(book_id)

                    added = append_new_notes(
                        page_id=existing["page_id"],
                        bookmarks=book_data["bookmarks"],
                        reviews=book_data["reviews"],
                        chapters=book_data["chapters"],
                        existing_note_count=existing["note_count"],
                    )
                    print(f"   ✅ 已追加 {added} 条笔记")
                    updated_books += 1
                else:
                    skipped_books += 1

            # 避免请求过快被限流
            time.sleep(1)

        except CookieExpiredError as e:
            print(f"\n❌ {e}")
            sys.exit(1)
        except Exception as e:
            print(f"\n⚠️  处理《{title}》时出错：{e}")
            continue

    # 4. 同步摘要
    print(f"\n{'='*40}")
    print(f"✅ 同步完成！")
    print(f"   新增：{new_books} 本书")
    print(f"   更新：{updated_books} 本书")
    print(f"   跳过：{skipped_books} 本书（无变化）")


if __name__ == "__main__":
    main()
