"""AI 主题标签生成 — 使用 Claude API 为书籍自动分类"""

import json

import anthropic

from config import ANTHROPIC_API_KEY


SYSTEM_PROMPT = """你是一个读书笔记分类助手。根据书籍信息和划线摘要，为这本书生成 2-5 个主题标签。

要求：
1. 标签用中文
2. 标签要具体有用，能帮助读者按主题检索（如"第一性原理""认知偏差""博弈论"），避免太宽泛的标签（如"好书""有趣"）
3. 可以从以下常用标签中选择，也可以创建新标签：
   思维方式、认知科学、心理学、经济学、商业、管理、哲学、历史、
   科技、人工智能、写作、沟通、习惯养成、个人成长、教育、
   社会学、政治、文学、生物学、数学、投资理财、创业、设计、
   产品思维、领导力、决策、系统思考、进化论、博弈论
4. 只返回 JSON 数组，不要其他文字

示例输出：["思维方式", "第一性原理", "创业"]"""


def generate_labels(
    title: str,
    author: str,
    category: str,
    sample_highlights: list[str],
) -> list[str]:
    """为一本书生成主题标签

    Args:
        title: 书名
        author: 作者
        category: 微信读书分类
        sample_highlights: 前10条划线摘要

    Returns:
        标签列表，如 ["思维方式", "认知科学"]
    """
    if not ANTHROPIC_API_KEY:
        # 没有配置 API key 时跳过标签生成
        return []

    highlights_text = "\n".join(
        f"- {h[:200]}" for h in sample_highlights[:10]
    )

    user_message = f"""书名：{title}
作者：{author}
分类：{category}

划线摘要：
{highlights_text}

请为这本书生成 2-5 个主题标签（JSON 数组）："""

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=200,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    text = response.content[0].text.strip()

    # 解析 JSON 数组
    try:
        labels = json.loads(text)
        if isinstance(labels, list):
            return [str(l) for l in labels][:5]
    except json.JSONDecodeError:
        # 尝试从文本中提取 JSON
        start = text.find("[")
        end = text.rfind("]") + 1
        if start >= 0 and end > start:
            try:
                labels = json.loads(text[start:end])
                return [str(l) for l in labels][:5]
            except json.JSONDecodeError:
                pass

    return []
