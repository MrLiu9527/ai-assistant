"""文本处理相关 Skills"""

import re
from collections import Counter

from src.skills.base import SkillResponse, skill


@skill(
    skill_id="common.text.extract_keywords",
    name="关键词提取",
    description="从文本中提取关键词",
    version="1.0.0",
    category="common",
    tags=["text", "nlp", "keywords"],
)
def extract_keywords(
    text: str,
    top_k: int = 10,
    min_length: int = 2,
) -> SkillResponse:
    """从文本中提取关键词

    Args:
        text: 输入文本
        top_k: 返回的关键词数量
        min_length: 关键词最小长度

    Returns:
        SkillResponse: 包含关键词列表
    """
    if not text or not text.strip():
        return SkillResponse.error(
            message="输入文本不能为空",
            code="EMPTY_INPUT",
        )

    # 简单的关键词提取（实际项目中可以使用 jieba、TF-IDF 等）
    # 移除标点符号
    text = re.sub(r"[^\w\s]", " ", text)

    # 分词（简单按空格分割，中文需要用 jieba）
    words = text.split()

    # 过滤短词
    words = [w for w in words if len(w) >= min_length]

    # 统计词频
    word_counts = Counter(words)

    # 获取 top_k 关键词
    keywords = word_counts.most_common(top_k)

    return SkillResponse.success(
        content={
            "keywords": [{"word": word, "count": count} for word, count in keywords],
            "total_words": len(words),
        }
    )


@skill(
    skill_id="common.text.summarize",
    name="文本摘要",
    description="生成文本摘要",
    version="1.0.0",
    category="common",
    tags=["text", "nlp", "summary"],
)
def summarize_text(
    text: str,
    max_length: int = 200,
    method: str = "truncate",
) -> SkillResponse:
    """生成文本摘要

    Args:
        text: 输入文本
        max_length: 摘要最大长度
        method: 摘要方法 (truncate, sentences)

    Returns:
        SkillResponse: 包含文本摘要
    """
    if not text or not text.strip():
        return SkillResponse.error(
            message="输入文本不能为空",
            code="EMPTY_INPUT",
        )

    text = text.strip()

    if method == "truncate":
        # 简单截断
        if len(text) <= max_length:
            summary = text
        else:
            summary = text[:max_length - 3] + "..."

    elif method == "sentences":
        # 按句子截取
        sentences = re.split(r"[。！？.!?]", text)
        sentences = [s.strip() for s in sentences if s.strip()]

        summary = ""
        for sentence in sentences:
            if len(summary) + len(sentence) + 1 <= max_length:
                summary += sentence + "。"
            else:
                break

        if not summary:
            summary = text[:max_length - 3] + "..."

    else:
        return SkillResponse.error(
            message=f"不支持的摘要方法: {method}",
            code="INVALID_METHOD",
        )

    return SkillResponse.success(
        content={
            "summary": summary,
            "original_length": len(text),
            "summary_length": len(summary),
            "compression_ratio": len(summary) / len(text) if text else 0,
        }
    )


@skill(
    skill_id="common.text.translate",
    name="文本翻译",
    description="翻译文本（示例实现）",
    version="1.0.0",
    category="common",
    tags=["text", "translation"],
)
async def translate_text(
    text: str,
    source_lang: str = "auto",
    target_lang: str = "en",
) -> SkillResponse:
    """翻译文本

    这是一个示例实现，实际项目中应该调用翻译 API

    Args:
        text: 输入文本
        source_lang: 源语言
        target_lang: 目标语言

    Returns:
        SkillResponse: 包含翻译结果
    """
    if not text or not text.strip():
        return SkillResponse.error(
            message="输入文本不能为空",
            code="EMPTY_INPUT",
        )

    # 这里只是示例，实际需要调用翻译 API
    # 例如：Google Translate API, DeepL API, 百度翻译 API 等

    return SkillResponse.success(
        content={
            "original": text,
            "translated": f"[Translation of '{text}' to {target_lang}]",
            "source_lang": source_lang,
            "target_lang": target_lang,
            "note": "This is a placeholder. Implement actual translation API.",
        }
    )
