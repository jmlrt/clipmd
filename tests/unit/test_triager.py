"""Unit tests for the triage orchestration module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from clipmd.config import Config, TriageConfig
from clipmd.core.triager import (
    FetchStepResult,
    MoveStepResult,
    PreprocessStepResult,
    TriageResult,
    run_triage,
)


class TestTriageResult:
    """Tests for TriageResult dataclass."""

    def test_default_construction(self) -> None:
        """Test default TriageResult construction."""
        result = TriageResult()
        assert result.fetch.rss_fetched == 0
        assert result.fetch.inbox_fetched == 0
        assert result.preprocess.processed == 0
        assert result.move.domain_matched == 0
        assert result.move.staged == 0
        assert result.dry_run is False


class TestRunTriage:
    """Tests for run_triage orchestrator."""

    def test_with_no_rss_no_inbox(self, tmp_path: Path) -> None:
        """Test triage with empty config (no RSS/INBOX)."""
        config = Config(
            vault=tmp_path,
            cache=tmp_path / "cache.json",
            triage=TriageConfig(rss_sources=[], inbox_file=None),
        )

        with patch("clipmd.core.triager.stats.collect_folder_stats") as mock_stats:
            from clipmd.core.stats import Stats

            mock_stats.return_value = Stats()

            result = run_triage(config, tmp_path, dry_run=True)

            assert result.fetch.rss_fetched == 0
            assert result.fetch.inbox_fetched == 0
            assert result.preprocess.processed == 0
            assert result.dry_run is True

    def test_with_staging_override(self, tmp_path: Path) -> None:
        """Test triage with --staging override."""
        config = Config(
            vault=tmp_path,
            cache=tmp_path / "cache.json",
            triage=TriageConfig(
                rss_sources=[],
                inbox_file=None,
                staging_folder="default-staging",
            ),
        )

        with patch("clipmd.core.triager.stats.collect_folder_stats") as mock_stats:
            from clipmd.core.stats import Stats

            mock_stats.return_value = Stats()

            result = run_triage(config, tmp_path, dry_run=True, staging_folder="override-staging")

            # The override is applied but we'd need to check move step
            # This test mainly ensures the function signature works
            assert result.dry_run is True

    def test_no_domain_rules_flag(self, tmp_path: Path) -> None:
        """Test triage with --no-domain-rules flag."""
        config = Config(
            vault=tmp_path,
            cache=tmp_path / "cache.json",
            triage=TriageConfig(rss_sources=[], inbox_file=None),
            domain_rules={"example.com": "TestFolder"},
        )

        with patch("clipmd.core.triager.stats.collect_folder_stats") as mock_stats:
            from clipmd.core.stats import Stats

            mock_stats.return_value = Stats()

            result = run_triage(config, tmp_path, dry_run=True, no_domain_rules=True)

            # With no_domain_rules, apply_domain_rules_fallback should not be called
            assert result.move.domain_matched == 0

    def test_with_articles_to_move(self, tmp_path: Path) -> None:
        """Test triage with articles in vault root."""
        config = Config(
            vault=tmp_path,
            cache=tmp_path / "cache.json",
            triage=TriageConfig(rss_sources=[], inbox_file=None),
            domain_rules={"example.com": "Example"},
        )

        # Create test article with domain rule match
        article = tmp_path / "test-article.md"
        article.write_text("---\nsource: https://example.com/article\n---\nContent")

        with patch("clipmd.core.triager.stats.collect_folder_stats") as mock_stats:
            from clipmd.core.stats import Stats

            mock_stats.return_value = Stats()
            # Patch mover/preprocessor functions to avoid actual file operations
            with (
                patch("clipmd.core.triager.mover.apply_domain_rules_fallback") as mock_apply,
                patch("clipmd.core.triager.mover.execute_moves") as mock_execute,
                patch("clipmd.core.triager.preprocessor.preprocess_directory") as mock_preprocess,
            ):
                from clipmd.core.mover import MoveInstruction, MoveStats
                from clipmd.core.preprocessor import PreprocessStats

                # Mock returns
                mock_apply.return_value = [
                    MoveInstruction(
                        index=0, category="Example", filename="test-article.md", line_number=-1
                    )
                ]
                mock_execute.return_value = MoveStats(
                    total=1, moved=1, trashed=0, folders_created=["Example"]
                )
                mock_preprocess.return_value = PreprocessStats(scanned=1)

                result = run_triage(config, tmp_path, dry_run=False)

                # Verify moves were attempted
                assert result.move.domain_matched == 1
                mock_execute.assert_called_once()

    def test_with_rss_sources(self, tmp_path: Path) -> None:
        """Test triage with RSS source configured."""
        config = Config(
            vault=tmp_path,
            cache=tmp_path / "cache.json",
            triage=TriageConfig(rss_sources=["https://example.com/feed.xml"], inbox_file=None),
        )

        with (
            patch("clipmd.core.triager.asyncio.run") as mock_async,
            patch("clipmd.core.triager.stats.collect_folder_stats") as mock_stats,
            patch("clipmd.core.triager.preprocessor.preprocess_directory") as mock_preprocess,
            patch("clipmd.core.triager.mover.apply_domain_rules_fallback") as mock_apply,
            patch("clipmd.core.triager.mover.execute_moves") as mock_execute,
        ):
            from clipmd.core.fetcher import FetchOrchestrationResult, FetchStats, ProcessResult
            from clipmd.core.mover import MoveStats
            from clipmd.core.preprocessor import PreprocessStats
            from clipmd.core.stats import Stats

            # Mock the asyncio.run(orchestrate_fetch(...)) return
            fetch_result = FetchOrchestrationResult(
                rss_error=None,
                process_result=ProcessResult(
                    stats=FetchStats(total=5, saved=5, skipped=0, errors=[]), saved_files=[]
                ),
                fetch_results=[],
            )
            mock_async.return_value = fetch_result

            mock_stats.return_value = Stats()
            mock_preprocess.return_value = PreprocessStats(scanned=5)
            mock_apply.return_value = []
            mock_execute.return_value = MoveStats()

            result = run_triage(config, tmp_path, dry_run=True)

            # Verify RSS was fetched
            assert result.fetch.rss_fetched == 5
            # Verify asyncio.run was called for the RSS source
            mock_async.assert_called()

    def test_with_inbox_file(self, tmp_path: Path) -> None:
        """Test triage with INBOX.md configured."""
        config = Config(
            vault=tmp_path,
            cache=tmp_path / "cache.json",
            triage=TriageConfig(rss_sources=[], inbox_file="INBOX.md"),
        )

        # Create INBOX.md
        inbox = tmp_path / "INBOX.md"
        inbox.write_text("https://example.com/article1\nhttps://example.com/article2")

        with (
            patch("clipmd.core.triager.asyncio.run") as mock_async,
            patch("clipmd.core.triager.stats.collect_folder_stats") as mock_stats,
            patch("clipmd.core.triager.preprocessor.preprocess_directory") as mock_preprocess,
            patch("clipmd.core.triager.mover.apply_domain_rules_fallback") as mock_apply,
            patch("clipmd.core.triager.mover.execute_moves") as mock_execute,
        ):
            from clipmd.core.fetcher import FetchOrchestrationResult, FetchStats, ProcessResult
            from clipmd.core.mover import MoveStats
            from clipmd.core.preprocessor import PreprocessStats
            from clipmd.core.stats import Stats

            # Mock the asyncio.run(orchestrate_fetch(...)) return
            fetch_result = FetchOrchestrationResult(
                rss_error=None,
                process_result=ProcessResult(
                    stats=FetchStats(total=2, saved=2, skipped=0, errors=[]), saved_files=[]
                ),
                fetch_results=[],
            )
            mock_async.return_value = fetch_result

            mock_stats.return_value = Stats()
            mock_preprocess.return_value = PreprocessStats(scanned=2)
            mock_apply.return_value = []
            mock_execute.return_value = MoveStats()

            result = run_triage(config, tmp_path, dry_run=False)

            # Verify inbox was fetched and file was cleared
            assert result.fetch.inbox_fetched == 2
            assert inbox.read_text() == ""  # Should be cleared after successful fetch

    def test_rss_fetch_error(self, tmp_path: Path) -> None:
        """Test triage handles RSS fetch errors gracefully."""
        config = Config(
            vault=tmp_path,
            cache=tmp_path / "cache.json",
            triage=TriageConfig(rss_sources=["https://example.com/feed.xml"], inbox_file=None),
        )

        with (
            patch("clipmd.core.triager.asyncio.run") as mock_async,
            patch("clipmd.core.triager.stats.collect_folder_stats") as mock_stats,
            patch("clipmd.core.triager.preprocessor.preprocess_directory") as mock_preprocess,
            patch("clipmd.core.triager.mover.apply_domain_rules_fallback") as mock_apply,
            patch("clipmd.core.triager.mover.execute_moves") as mock_execute,
        ):
            from clipmd.core.fetcher import FetchOrchestrationResult, FetchStats, ProcessResult
            from clipmd.core.mover import MoveStats
            from clipmd.core.preprocessor import PreprocessStats
            from clipmd.core.stats import Stats

            # Mock RSS error
            fetch_result = FetchOrchestrationResult(
                rss_error="Failed to fetch RSS: connection timeout",
                process_result=ProcessResult(
                    stats=FetchStats(total=0, saved=0, skipped=0, errors=[]), saved_files=[]
                ),
                fetch_results=[],
            )
            mock_async.return_value = fetch_result

            mock_stats.return_value = Stats()
            mock_preprocess.return_value = PreprocessStats(scanned=0)
            mock_apply.return_value = []
            mock_execute.return_value = MoveStats()

            result = run_triage(config, tmp_path, dry_run=True)

            # Verify error was captured
            assert len(result.fetch.errors) == 1
            assert "Failed to fetch RSS" in result.fetch.errors[0]

    def test_inbox_fetch_error_with_partial_success(self, tmp_path: Path) -> None:
        """Test triage preserves failed URLs in INBOX.md on partial error."""
        config = Config(
            vault=tmp_path,
            cache=tmp_path / "cache.json",
            triage=TriageConfig(rss_sources=[], inbox_file="INBOX.md"),
        )

        inbox = tmp_path / "INBOX.md"
        inbox.write_text("https://example.com/article1\nhttps://example.com/article2")

        with (
            patch("clipmd.core.triager.asyncio.run") as mock_async,
            patch("clipmd.core.triager.stats.collect_folder_stats") as mock_stats,
            patch("clipmd.core.triager.preprocessor.preprocess_directory") as mock_preprocess,
            patch("clipmd.core.triager.mover.apply_domain_rules_fallback") as mock_apply,
            patch("clipmd.core.triager.mover.execute_moves") as mock_execute,
        ):
            from clipmd.core.fetcher import FetchOrchestrationResult, FetchStats, ProcessResult
            from clipmd.core.mover import MoveStats
            from clipmd.core.preprocessor import PreprocessStats
            from clipmd.core.stats import Stats

            # Mock partial fetch with one failure
            fetch_result = FetchOrchestrationResult(
                rss_error=None,
                process_result=ProcessResult(
                    stats=FetchStats(
                        total=2,
                        saved=1,
                        skipped=0,
                        errors=[("https://example.com/article2", "Connection timeout")],
                    ),
                    saved_files=[],
                ),
                fetch_results=[],
            )
            mock_async.return_value = fetch_result

            mock_stats.return_value = Stats()
            mock_preprocess.return_value = PreprocessStats(scanned=1)
            mock_apply.return_value = []
            mock_execute.return_value = MoveStats()

            result = run_triage(config, tmp_path, dry_run=False)

            # Verify partial results
            assert result.fetch.inbox_fetched == 1
            # Verify failed URL was preserved in INBOX.md
            inbox_content = inbox.read_text()
            assert "https://example.com/article2" in inbox_content
            assert "[KO]" in inbox_content
            assert "Connection timeout" in inbox_content


class TestFetchStepResult:
    """Tests for FetchStepResult dataclass."""

    def test_default_construction(self) -> None:
        """Test default FetchStepResult construction."""
        result = FetchStepResult()
        assert result.rss_fetched == 0
        assert result.inbox_fetched == 0
        assert result.skipped == 0
        assert result.errors == []

    def test_with_values(self) -> None:
        """Test FetchStepResult with values."""
        result = FetchStepResult(rss_fetched=5, inbox_fetched=3, skipped=2, errors=["error1"])
        assert result.rss_fetched == 5
        assert result.inbox_fetched == 3
        assert result.skipped == 2
        assert result.errors == ["error1"]


class TestPreprocessStepResult:
    """Tests for PreprocessStepResult dataclass."""

    def test_default_construction(self) -> None:
        """Test default PreprocessStepResult construction."""
        result = PreprocessStepResult()
        assert result.processed == 0
        assert result.duplicates_removed == 0
        assert result.errors == []


class TestMoveStepResult:
    """Tests for MoveStepResult dataclass."""

    def test_default_construction(self) -> None:
        """Test default MoveStepResult construction."""
        result = MoveStepResult()
        assert result.domain_matched == 0
        assert result.staged == 0
        assert result.trashed == 0
        assert result.errors == []
        assert result.folders_created == []

    def test_with_values(self) -> None:
        """Test MoveStepResult with values."""
        result = MoveStepResult(
            domain_matched=5,
            staged=3,
            trashed=1,
            errors=["error1"],
            folders_created=["Folder1"],
        )
        assert result.domain_matched == 5
        assert result.staged == 3
        assert result.trashed == 1
        assert result.errors == ["error1"]
        assert result.folders_created == ["Folder1"]


class TestFormatTriageSummary:
    """Tests for format_triage_summary output formatting."""

    def test_empty_result(self) -> None:
        """Test formatting empty triage result."""
        from clipmd.core.stats import Stats
        from clipmd.core.triager import format_triage_summary

        result = TriageResult()
        result.stats_result = Stats()

        lines = format_triage_summary(result)

        assert len(lines) > 0
        assert any("complete" in line.lower() for line in lines)

    def test_with_dry_run(self) -> None:
        """Test formatting result with dry_run flag."""
        from clipmd.core.stats import Stats
        from clipmd.core.triager import format_triage_summary

        result = TriageResult(dry_run=True)
        result.stats_result = Stats()

        lines = format_triage_summary(result)

        assert any("dry" in line.lower() for line in lines)

    def test_with_fetch_results(self) -> None:
        """Test formatting with fetch results."""
        from clipmd.core.stats import Stats
        from clipmd.core.triager import format_triage_summary

        result = TriageResult()
        result.fetch = FetchStepResult(rss_fetched=5, inbox_fetched=3, skipped=2)
        result.stats_result = Stats()

        lines = format_triage_summary(result)

        output = "\n".join(lines)
        assert "5" in output or "Fetched" in output

    def test_with_move_results(self) -> None:
        """Test formatting with move results."""
        from clipmd.core.stats import Stats
        from clipmd.core.triager import format_triage_summary

        result = TriageResult()
        result.move = MoveStepResult(domain_matched=10, staged=5, trashed=2)
        result.stats_result = Stats()

        lines = format_triage_summary(result)

        output = "\n".join(lines)
        assert "Organized" in output or "10" in output

    def test_with_fetch_errors(self) -> None:
        """Test formatting with fetch errors."""
        from clipmd.core.stats import Stats
        from clipmd.core.triager import format_triage_summary

        result = TriageResult()
        result.fetch = FetchStepResult(errors=["RSS fetch failed", "Network error"])
        result.stats_result = Stats()

        lines = format_triage_summary(result)

        output = "\n".join(lines)
        assert "warning" in output.lower() or "error" in output.lower()

    def test_with_move_errors(self) -> None:
        """Test formatting with move errors."""
        from clipmd.core.stats import Stats
        from clipmd.core.triager import format_triage_summary

        result = TriageResult()
        result.move = MoveStepResult(errors=["Permission denied", "Folder not found"])
        result.stats_result = Stats()

        lines = format_triage_summary(result)

        # Errors are only shown via exit code, but result should format without crash
        assert len(lines) > 0
        assert any("complete" in line.lower() for line in lines)
