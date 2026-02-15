"""Unit tests for URL and filename sanitization."""

from __future__ import annotations

from clipmd.config import FilenamesConfig, UrlCleaningConfig
from clipmd.core.sanitizer import clean_url, extract_domain, sanitize_filename


class TestCleanUrl:
    """Tests for clean_url function."""

    def test_remove_utm_params(self) -> None:
        """Test removing UTM parameters."""
        url = "https://example.com/article?utm_source=twitter&utm_medium=social"
        result = clean_url(url)
        assert result == "https://example.com/article"

    def test_keep_other_params(self) -> None:
        """Test keeping non-tracking parameters."""
        url = "https://example.com/article?id=123&utm_source=twitter"
        result = clean_url(url)
        assert "id=123" in result
        assert "utm_source" not in result

    def test_remove_fbclid(self) -> None:
        """Test removing Facebook click ID."""
        url = "https://example.com/page?fbclid=abc123"
        result = clean_url(url)
        assert result == "https://example.com/page"

    def test_remove_trailing_slash(self) -> None:
        """Test removing trailing slash."""
        url = "https://example.com/article/"
        result = clean_url(url)
        assert result == "https://example.com/article"

    def test_keep_root_slash(self) -> None:
        """Test keeping root path slash."""
        url = "https://example.com/"
        result = clean_url(url)
        assert result == "https://example.com/"

    def test_with_config(self) -> None:
        """Test with custom configuration."""
        config = UrlCleaningConfig(remove_params=["custom_param"])
        url = "https://example.com/page?custom_param=value&keep=this"
        result = clean_url(url, config)
        assert "custom_param" not in result
        assert "keep=this" in result


class TestExtractDomain:
    """Tests for extract_domain function."""

    def test_simple_domain(self) -> None:
        """Test extracting simple domain."""
        result = extract_domain("https://example.com/article")
        assert result == "example.com"

    def test_subdomain(self) -> None:
        """Test extracting domain with subdomain."""
        result = extract_domain("https://blog.example.com/post")
        assert result == "blog.example.com"

    def test_with_port(self) -> None:
        """Test extracting domain with port."""
        result = extract_domain("http://localhost:8080/page")
        assert result == "localhost:8080"


class TestSanitizeFilename:
    """Tests for sanitize_filename function."""

    def test_replace_spaces(self) -> None:
        """Test replacing spaces with dashes."""
        result = sanitize_filename("My Article Title.md")
        assert result == "My-Article-Title.md"

    def test_remove_special_chars(self) -> None:
        """Test removing special characters."""
        result = sanitize_filename("Article: Part 1?.md")
        assert result == "Article-Part-1.md"

    def test_collapse_dashes(self) -> None:
        """Test collapsing multiple dashes."""
        result = sanitize_filename("Article---Title.md")
        assert result == "Article-Title.md"

    def test_max_length(self) -> None:
        """Test maximum length enforcement."""
        long_title = "A" * 150 + ".md"
        result = sanitize_filename(long_title)
        assert len(result) <= 100

    def test_preserve_extension(self) -> None:
        """Test extension is preserved when truncating."""
        long_title = "A" * 150 + ".md"
        result = sanitize_filename(long_title)
        assert result.endswith(".md")

    def test_lowercase(self) -> None:
        """Test lowercase option."""
        config = FilenamesConfig(lowercase=True)
        result = sanitize_filename("My ARTICLE.md", config)
        assert result == "my-article.md"

    def test_no_collapse_dashes(self) -> None:
        """Test without dash collapsing."""
        config = FilenamesConfig(collapse_dashes=False)
        result = sanitize_filename("Article--Title.md", config)
        assert "--" in result

    def test_strip_leading_trailing_dashes(self) -> None:
        """Test stripping leading and trailing dashes."""
        result = sanitize_filename("-Article-Title-.md")
        assert result == "Article-Title.md"

    def test_remove_curly_apostrophes(self) -> None:
        """Test replacing curly/smart apostrophes with dashes."""
        result = sanitize_filename("It\u2019s a Test\u2019s Title.md")
        assert result == "It-s-a-Test-s-Title.md"

    def test_remove_curly_quotes(self) -> None:
        """Test removing curly/smart quotes."""
        result = sanitize_filename("The \u201cBest\u201d Article.md")
        assert result == "The-Best-Article.md"

    def test_replace_accented_characters(self) -> None:
        """Test replacing accented characters with non-accented equivalents."""
        result = sanitize_filename("Café René Naïve Résumé.md")
        assert result == "Cafe-Rene-Naive-Resume.md"

    def test_replace_special_chars_with_dashes(self) -> None:
        """Test that special characters are replaced with dashes."""
        result = sanitize_filename("Article@Title#Test!.md")
        assert result == "Article-Title-Test.md"

    def test_underscore_replaced_with_dash(self) -> None:
        """Test that underscores are replaced with dashes."""
        result = sanitize_filename("My_Article_Title.md")
        assert result == "My-Article-Title.md"
