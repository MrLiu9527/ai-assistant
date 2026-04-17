"""文本处理 Skills 测试"""


from src.skills.base import SkillStatus
from src.skills.common.text_processing import (
    extract_keywords,
    summarize_text,
)


class TestExtractKeywords:
    """extract_keywords Skill 测试"""

    def test_extract_keywords_success(self):
        """测试成功提取关键词"""
        text = "Python is a great programming language Python is easy to learn"
        result = extract_keywords(text, top_k=5)

        assert result.status == SkillStatus.SUCCESS
        assert "keywords" in result.content
        assert len(result.content["keywords"]) <= 5

    def test_extract_keywords_empty_input(self):
        """测试空输入"""
        result = extract_keywords("")

        assert result.status == SkillStatus.ERROR
        assert result.error_code == "EMPTY_INPUT"

    def test_extract_keywords_min_length(self):
        """测试最小长度过滤"""
        text = "a b c hello world programming"
        result = extract_keywords(text, min_length=5)

        assert result.status == SkillStatus.SUCCESS
        keywords = [k["word"] for k in result.content["keywords"]]
        assert all(len(k) >= 5 for k in keywords)


class TestSummarizeText:
    """summarize_text Skill 测试"""

    def test_summarize_truncate(self):
        """测试截断摘要"""
        text = "这是一段很长的文本。" * 10
        result = summarize_text(text, max_length=50, method="truncate")

        assert result.status == SkillStatus.SUCCESS
        assert len(result.content["summary"]) <= 50

    def test_summarize_sentences(self):
        """测试按句子摘要"""
        text = "第一句话。第二句话。第三句话。第四句话。"
        result = summarize_text(text, max_length=20, method="sentences")

        assert result.status == SkillStatus.SUCCESS

    def test_summarize_empty_input(self):
        """测试空输入"""
        result = summarize_text("")

        assert result.status == SkillStatus.ERROR
        assert result.error_code == "EMPTY_INPUT"

    def test_summarize_invalid_method(self):
        """测试无效方法"""
        result = summarize_text("测试文本", method="invalid")

        assert result.status == SkillStatus.ERROR
        assert result.error_code == "INVALID_METHOD"

    def test_summarize_short_text(self):
        """测试短文本（不需要摘要）"""
        text = "短文本"
        result = summarize_text(text, max_length=100)

        assert result.status == SkillStatus.SUCCESS
        assert result.content["summary"] == text
