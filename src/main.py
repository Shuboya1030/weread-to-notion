"""微信读书 → Notion 同步主流程"""

import sys
import time

from weread import get_shelf_books, get_all_book_data, CookieExpiredError
from notion_sync import get_synced_books, create_book_page, append_new_notes
from labeler import generate_labels


def main():
    print("🔄 开始同步微信读书笔记到 Notion...")

    # 1. 从微信读书获取书架上的所有书
    try:
        shelf_books = get_shelf_books()
    except CookieExpiredError as e:
        print(f"\n❌ {e}")
        print("请更新 WEREAD_COOKIE 环境变量（或 GitHub Secrets）后重试。")
        sys.exit(1)

    print(f"📚 微信读书书架上有 {len(shelf_books)} 本书")

    if not shelf_books:
        print("书架为空，退出。")
        return

    # 2. 从 Notion 获取已同步的书籍
    synced = get_synced_books()
    print(f"📋 Notion 中已同步 {len(synced)} 本书")

    new_books = 0
    updated_books = 0
    skipped_books = 0

    # 3. 逐本处理
    for book in shelf_books:
        book_id = str(book.get("bookId", ""))
        title = book.get("title", "未知")

        if not book_id:
            continue

        try:
            # 获取该书的笔记数据
            book_data = get_all_book_data(book_id)
            bookmarks = book_data["bookmarks"]
            reviews = book_data["reviews"]
            total_notes = len(bookmarks) + len(reviews)

            # 没有笔记的书跳过
            if total_notes == 0:
                continue

            if book_id not in synced:
                # 新书：AI 打标签 + 创建页面
                print(f"\n📖 新书：{title}")

                sample_highlights = [
                    bm.get("markText", "") for bm in bookmarks[:10]
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
                    book_info=book,
                    bookmarks=bookmarks,
                    reviews=reviews,
                    chapters=book_data["chapters"],
                    labels=labels,
                )
                print(f"   ✅ 已创建（{len(bookmarks)} 条划线，{len(reviews)} 条想法）")
                new_books += 1

            else:
                # 已有书：检查是否有新笔记
                existing = synced[book_id]
                if total_notes > existing["note_count"]:
                    new_count = total_notes - existing["note_count"]
                    print(f"\n📝 更新：{title}（新增 {new_count} 条笔记）")

                    added = append_new_notes(
                        page_id=existing["page_id"],
                        bookmarks=bookmarks,
                        reviews=reviews,
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
