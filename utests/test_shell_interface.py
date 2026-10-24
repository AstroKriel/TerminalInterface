## { U-TEST

##
## === DEPENDENCIES
##

## stdlib
import subprocess
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock, patch

## third-party
import pytest

## local
from heimdall import shell_interface

##
## === TEST SUITE
##


class TestConfig_Defaults:

    def test_dry_run_is_false(
        self,
    ) -> None:
        config = shell_interface.Config()
        assert config.dry_run is False

    def test_subclass_passes_through_runners(
        self,
    ) -> None:
        @dataclass
        class ToolConfig(shell_interface.Config):
            allow_dirty: bool = False
        tool_config = ToolConfig(dry_run=True, allow_dirty=True)
        with patch("subprocess.run") as mock_run:
            shell_interface.run_cmd(config=tool_config, cmd=["git", "push"])
            mock_run.assert_not_called()


class TestLogFunctions_Output:

    def test_log_msg_writes_to_stderr(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        shell_interface.log_msg("hello")
        captured = capsys.readouterr()
        assert captured.out == ""
        assert "hello" in captured.err

    def test_log_step_includes_marker_and_message(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        shell_interface.log_step("doing something")
        captured = capsys.readouterr()
        assert "○" in captured.err
        assert "doing something" in captured.err

    def test_log_outcome_includes_marker_and_message(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        shell_interface.log_outcome("it worked")
        captured = capsys.readouterr()
        assert "●" in captured.err
        assert "it worked" in captured.err

    def test_bind_var_includes_dot_and_values(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        shell_interface.bind_var(var_name="branch_name", var_value="main")
        captured = capsys.readouterr()
        assert "·" in captured.err
        assert "branch_name = main" in captured.err

    def test_bind_var_prints_brackets_literally(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        shell_interface.bind_var(var_name="pattern", var_value="[bold]x")
        captured = capsys.readouterr()
        assert "[bold]x" in captured.err

    def test_log_result_writes_to_stdout(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        shell_interface.log_result("all good")
        captured = capsys.readouterr()
        assert captured.err == ""
        assert "●" in captured.out
        assert "all good" in captured.out

    def test_kill_exits_with_status_one(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        with pytest.raises(SystemExit) as exit_info:
            shell_interface.kill("broken")
        captured = capsys.readouterr()
        assert exit_info.value.code == 1
        assert "error: broken" in captured.err


class TestPrintedCommands_Quoting:

    def test_argument_with_spaces_is_quoted(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="", returncode=0)
            shell_interface.query_cmd(cmd=["git", "commit", "-m", "a message"])
        captured = capsys.readouterr()
        assert "git commit -m 'a message'" in captured.err

    def test_brackets_in_arguments_are_printed_literally(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="", returncode=0)
            shell_interface.query_cmd(cmd=["ls", "[red]"])
        captured = capsys.readouterr()
        assert "[red]" in captured.err


class TestRunCmd_DryRun:

    def test_skips_subprocess(
        self,
    ) -> None:
        config = shell_interface.Config(dry_run=True)
        with patch("subprocess.run") as mock_run:
            shell_interface.run_cmd(config=config, cmd=["git", "push"])
            mock_run.assert_not_called()

    def test_logs_skipped(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        config = shell_interface.Config(dry_run=True)
        shell_interface.run_cmd(config=config, cmd=["git", "push"])
        captured = capsys.readouterr()
        assert "dryrun" in captured.err
        assert "git push" in captured.err

    def test_executes_when_not_dry_run(
        self,
    ) -> None:
        config = shell_interface.Config(dry_run=False)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            shell_interface.run_cmd(config=config, cmd=["git", "status"])
            mock_run.assert_called_once()

    def test_logs_command_before_executing(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        config = shell_interface.Config(dry_run=False)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            shell_interface.run_cmd(config=config, cmd=["git", "status"])
        captured = capsys.readouterr()
        assert "git status" in captured.err


class TestRunCmdAndCaptureOutput_Behaviour:

    def test_skips_subprocess_in_dry_run(
        self,
    ) -> None:
        config = shell_interface.Config(dry_run=True)
        with patch("subprocess.run") as mock_run:
            _ = shell_interface.run_cmd_and_capture_output(
                config=config,
                cmd=["git", "rev-list", "--count", "HEAD"],
            )
            mock_run.assert_not_called()

    def test_returns_empty_string_in_dry_run(
        self,
    ) -> None:
        config = shell_interface.Config(dry_run=True)
        result = shell_interface.run_cmd_and_capture_output(
            config=config,
            cmd=["git", "rev-list", "--count", "HEAD"],
        )
        assert result == ""

    def test_passes_cwd(
        self,
        tmp_path: Path,
    ) -> None:
        config = shell_interface.Config(dry_run=False)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="3\n", returncode=0)
            _ = shell_interface.run_cmd_and_capture_output(
                config=config,
                cmd=["git", "rev-list", "--count", "HEAD"],
                cwd=tmp_path,
            )
            assert mock_run.call_args.kwargs["cwd"] == tmp_path


class TestQueryCmd_Behaviour:

    def test_always_executes(
        self,
    ) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="main\n", returncode=0)
            _ = shell_interface.query_cmd(cmd=["git", "branch", "--show-current"])
            mock_run.assert_called_once()

    def test_passes_cwd(
        self,
        tmp_path: Path,
    ) -> None:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="main\n", returncode=0)
            _ = shell_interface.query_cmd(cmd=["git", "branch", "--show-current"], cwd=tmp_path)
            assert mock_run.call_args.kwargs["cwd"] == tmp_path

    def test_raises_on_failure_by_default(
        self,
    ) -> None:
        with pytest.raises(subprocess.CalledProcessError):
            shell_interface.query_cmd(cmd=["false"])

    def test_returns_empty_string_when_failure_allowed(
        self,
    ) -> None:
        result = shell_interface.query_cmd(cmd=["false"], error_on_failure=False)
        assert result == ""


class TestQueryCmdResult_Outcome:

    def test_records_command_output_and_exit_code(
        self,
        tmp_path: Path,
    ) -> None:
        command_outcome = shell_interface.query_cmd_result(cmd=["echo", "a b"], cwd=tmp_path)
        assert command_outcome.command == "echo 'a b'"
        assert command_outcome.working_directory == tmp_path
        assert command_outcome.exit_code == 0
        assert command_outcome.stdout == "a b\n"
        assert command_outcome.succeeded

    def test_does_not_raise_on_failure(
        self,
    ) -> None:
        command_outcome = shell_interface.query_cmd_result(cmd=["false"])
        assert command_outcome.exit_code != 0
        assert not command_outcome.succeeded

    def test_prints_command(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        _ = shell_interface.query_cmd_result(cmd=["true"])
        captured = capsys.readouterr()
        assert "→ true" in captured.err


class TestTimestamps_Output:

    def test_off_by_default(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        shell_interface.log_step("plain")
        captured = capsys.readouterr()
        assert not captured.err.startswith("[")

    def test_prefix_when_enabled(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        shell_interface.configure_output(tool_name="tool", show_timestamps=True)
        with patch.object(shell_interface, "get_timestamp", return_value="2026-01-02 03:04:05"):
            shell_interface.log_step("stamped")
        captured = capsys.readouterr()
        assert captured.err.startswith("[2026-01-02 03:04:05] ○ stamped")


class TestRecord_File:

    def test_appends_plain_lines(
        self,
        tmp_path: Path,
    ) -> None:
        record_path = tmp_path / "logs" / "record.log"
        shell_interface.configure_output(tool_name="tool", record_path=record_path)
        with patch.object(shell_interface, "get_timestamp", return_value="2026-01-02 03:04:05"):
            shell_interface.log_step("first")
            shell_interface.log_msg("[bold]second[/bold]")
        record_lines = record_path.read_text().splitlines()
        assert record_lines == [
            "[2026-01-02 03:04:05] (tool): ○ first",
            "[2026-01-02 03:04:05] (tool): second",
        ]

    def test_records_commands(
        self,
        tmp_path: Path,
    ) -> None:
        record_path = tmp_path / "record.log"
        shell_interface.configure_output(tool_name="tool", record_path=record_path)
        _ = shell_interface.query_cmd(cmd=["echo", "a b"])
        assert "→ echo 'a b'" in record_path.read_text()

    def test_not_written_in_dry_run(
        self,
        tmp_path: Path,
    ) -> None:
        record_path = tmp_path / "record.log"
        shell_interface.configure_output(tool_name="tool", record_path=record_path, dry_run=True)
        shell_interface.log_step("nothing happens")
        assert not record_path.exists()

    def test_off_by_default(
        self,
        tmp_path: Path,
    ) -> None:
        shell_interface.log_step("nowhere")
        assert list(tmp_path.iterdir()) == []


class TestLegend_Entries:

    def test_one_entry_per_theme(
        self,
    ) -> None:
        legend_entries = shell_interface.get_legend()
        assert [_legend_entry.color_name for _legend_entry in legend_entries] == [
            "white",
            "green",
            "red",
            "blue",
            "orange",
            "gray",
            "gray",
        ]

    def test_markers_match_output(
        self,
    ) -> None:
        legend_entries = shell_interface.get_legend()
        assert legend_entries[0].marker == "○"
        assert legend_entries[3].marker == "→"


## } U-TEST
