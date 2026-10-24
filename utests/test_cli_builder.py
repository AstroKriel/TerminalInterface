## { U-TEST

##
## === DEPENDENCIES
##

## stdlib
import argparse
import re
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

## third-party
import pytest

## local
from heimdall import cli_builder, shell_interface

##
## === HELPERS
##


def _do_nothing(
    config: shell_interface.Config,
) -> None:
    return None


@dataclass
class _ToolConfig(shell_interface.Config):
    allow_dirty: bool = False


def _make_tool_config(
    parsed_args: argparse.Namespace,
) -> _ToolConfig:
    return _ToolConfig(
        dry_run=parsed_args.dry_run,
        allow_dirty=parsed_args.allow_dirty,
    )


##
## === TEST SUITE
##


class TestCommandDetails_ArgMapping:

    def test_positional_arg_is_passed_to_fn(
        self,
    ) -> None:
        received: list[str] = []
        def record_branch(
            config: shell_interface.Config,
            branch_name: str,
        ) -> None:
            received.append(branch_name)
        _, cmd_details = cli_builder.cli_command(
            cmd_name="test-cmd",
            cmd_fn=record_branch,
            cmd_args=[cli_builder.CommandArg(arg_name="branch_name")],
        )
        parsed_args = argparse.Namespace(dry_run=False, branch_name="feature")
        cmd_details.call(config=shell_interface.Config(), parsed_args=parsed_args)
        assert received == ["feature"]

    def test_named_flag_is_passed_to_fn(
        self,
    ) -> None:
        received: list[str | None] = []
        def record_base(
            config: shell_interface.Config,
            base: str | None = None,
        ) -> None:
            received.append(base)
        _, cmd_details = cli_builder.cli_command(
            cmd_name="test-cmd",
            cmd_fn=record_base,
            cmd_args=[cli_builder.CommandArg(arg_name="--base")],
        )
        parsed_args = argparse.Namespace(dry_run=False, base="development")
        cmd_details.call(config=shell_interface.Config(), parsed_args=parsed_args)
        assert received == ["development"]

    def test_named_flag_and_positional_arg_together(
        self,
    ) -> None:
        received: list[str | None] = []
        def record_both(
            config: shell_interface.Config,
            base: str | None,
            path: str | None,
        ) -> None:
            received.extend([base, path])
        _, cmd_details = cli_builder.cli_command(
            cmd_name="test-cmd",
            cmd_fn=record_both,
            cmd_args=[
                cli_builder.CommandArg(arg_name="--base"),
                cli_builder.CommandArg(arg_name="path", nargs="?"),
            ],
        )
        parsed_args = argparse.Namespace(dry_run=False, base="main", path="src/foo.py")
        cmd_details.call(config=shell_interface.Config(), parsed_args=parsed_args)
        assert received == ["main", "src/foo.py"]


class TestCommandGroup_SectionStamping:

    def test_stamps_section_title_on_every_command(
        self,
    ) -> None:
        commands = cli_builder.command_group(
            section_title="Syncing",
            commands=[
                cli_builder.cli_command(cmd_name="alpha", cmd_fn=_do_nothing),
                cli_builder.cli_command(cmd_name="beta", cmd_fn=_do_nothing),
            ],
        )
        assert [_cmd_details.section_title for _, _cmd_details in commands] == ["Syncing", "Syncing"]

    def test_preserves_command_names_and_order(
        self,
    ) -> None:
        commands = cli_builder.command_group(
            section_title="Syncing",
            commands=[
                cli_builder.cli_command(cmd_name="alpha", cmd_fn=_do_nothing),
                cli_builder.cli_command(cmd_name="beta", cmd_fn=_do_nothing),
            ],
        )
        assert [_cmd_name for _cmd_name, _ in commands] == ["alpha", "beta"]


class TestRunCli_Dispatch:

    def test_dispatches_with_default_config(
        self,
    ) -> None:
        received: list[shell_interface.Config] = []
        def record_config(
            config: shell_interface.Config,
        ) -> None:
            received.append(config)
        tool_spec = cli_builder.ToolSpec(
            tool_name="tool",
            description="a tool",
            commands=[cli_builder.cli_command(cmd_name="go", cmd_fn=record_config)],
        )
        cli_builder.run_cli(tool_spec=tool_spec, argv=["--dry-run", "go"])
        assert received == [shell_interface.Config(dry_run=True)]

    def test_extra_global_flag_reaches_config(
        self,
    ) -> None:
        received: list[shell_interface.Config] = []
        def record_config(
            config: shell_interface.Config,
        ) -> None:
            received.append(config)
        tool_spec = cli_builder.ToolSpec(
            tool_name="tool",
            description="a tool",
            commands=[cli_builder.cli_command(cmd_name="go", cmd_fn=record_config)],
            global_flags=[cli_builder.CommandArg(arg_name="--allow-dirty", store_true=True)],
            make_config=_make_tool_config,
        )
        cli_builder.run_cli(tool_spec=tool_spec, argv=["--allow-dirty", "go"])
        assert received == [_ToolConfig(dry_run=False, allow_dirty=True)]

    def test_failed_command_exits_with_its_return_code(
        self,
    ) -> None:
        def fail(
            config: shell_interface.Config,
        ) -> None:
            raise subprocess.CalledProcessError(returncode=3, cmd=["false"])
        tool_spec = cli_builder.ToolSpec(
            tool_name="tool",
            description="a tool",
            commands=[cli_builder.cli_command(cmd_name="go", cmd_fn=fail)],
        )
        with pytest.raises(SystemExit) as exit_info:
            cli_builder.run_cli(tool_spec=tool_spec, argv=["go"])
        assert exit_info.value.code == 3

    def test_record_is_configured_from_tool_spec(
        self,
        tmp_path: Path,
    ) -> None:
        def narrate(
            config: shell_interface.Config,
        ) -> None:
            shell_interface.log_step("recorded")
        record_path = tmp_path / "record.log"
        tool_spec = cli_builder.ToolSpec(
            tool_name="tool",
            description="a tool",
            commands=[cli_builder.cli_command(cmd_name="go", cmd_fn=narrate)],
            record_path=record_path,
        )
        cli_builder.run_cli(tool_spec=tool_spec, argv=["go"])
        assert "(tool): ○ recorded" in record_path.read_text()


class TestHelp_Output:

    def _get_help(
        self,
        tool_spec: cli_builder.ToolSpec,
        capsys: pytest.CaptureFixture[str],
    ) -> str:
        with pytest.raises(SystemExit):
            cli_builder.run_cli(tool_spec=tool_spec, argv=["--help"])
        return capsys.readouterr().out

    def test_lists_sections_and_commands_with_tabs(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        tool_spec = cli_builder.ToolSpec(
            tool_name="tool",
            description="a tool",
            commands=cli_builder.command_group(
                section_title="Syncing",
                commands=[cli_builder.cli_command(cmd_name="alpha", cmd_fn=_do_nothing, cmd_help="does alpha")],
            ),
        )
        help_text = self._get_help(tool_spec, capsys)
        assert "tool: a tool" in help_text
        assert "usage: tool [--dry-run] <command> [args]" in help_text
        assert "Syncing" in help_text
        assert re.search(r"^ {4}alpha +does alpha$", help_text, flags=re.MULTILINE)

    def test_separates_with_spaces_only(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        tool_spec = cli_builder.ToolSpec(
            tool_name="tool",
            description="a tool",
            commands=cli_builder.command_group(
                section_title="Syncing",
                commands=[cli_builder.cli_command(cmd_name="alpha", cmd_fn=_do_nothing, cmd_help="does alpha")],
            ),
        )
        help_text = self._get_help(tool_spec, capsys)
        assert "\t" not in help_text

    def test_descriptions_share_one_column(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        tool_spec = cli_builder.ToolSpec(
            tool_name="tool",
            description="a tool",
            commands=cli_builder.command_group(
                section_title="Syncing",
                commands=[cli_builder.cli_command(cmd_name="alpha", cmd_fn=_do_nothing, cmd_help="does alpha")],
            ),
        )
        help_lines = self._get_help(tool_spec, capsys).splitlines()
        alpha_line = next(_line for _line in help_lines if "does alpha" in _line)
        dry_run_line = next(_line for _line in help_lines if "print commands" in _line)
        legend_line = next(_line for _line in help_lines if "action starting" in _line)
        assert alpha_line.index("does alpha") == dry_run_line.index("print commands")
        assert alpha_line.index("does alpha") == legend_line.index("action starting")

    def test_longest_label_sets_the_column(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        tool_spec = cli_builder.ToolSpec(
            tool_name="tool",
            description="a tool",
            commands=cli_builder.command_group(
                section_title="Syncing",
                commands=[
                    cli_builder.cli_command(
                        cmd_name="a-much-longer-command-name",
                        cmd_fn=_do_nothing,
                        cmd_help="long one",
                    ),
                ],
            ),
        )
        help_text = self._get_help(tool_spec, capsys)
        assert "    a-much-longer-command-name  long one" in help_text.splitlines()

    def test_omits_hidden_commands(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        tool_spec = cli_builder.ToolSpec(
            tool_name="tool",
            description="a tool",
            commands=[
                *cli_builder.command_group(
                    section_title="Shown",
                    commands=[cli_builder.cli_command(cmd_name="visible", cmd_fn=_do_nothing)],
                ),
                cli_builder.cli_command(cmd_name="secret", cmd_fn=_do_nothing, is_hidden=True),
            ],
        )
        help_text = self._get_help(tool_spec, capsys)
        assert "visible" in help_text
        assert "secret" not in help_text

    def test_lists_extra_global_flags(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        tool_spec = cli_builder.ToolSpec(
            tool_name="tool",
            description="a tool",
            commands=[],
            global_flags=[cli_builder.CommandArg(arg_name="--allow-dirty", store_true=True, help="skip the check")],
        )
        help_text = self._get_help(tool_spec, capsys)
        assert "usage: tool [--dry-run] [--allow-dirty] <command> [args]" in help_text
        assert "    --allow-dirty  skip the check" in help_text.splitlines()

    def test_legend_comes_from_themes(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        tool_spec = cli_builder.ToolSpec(tool_name="tool", description="a tool", commands=[])
        help_text = self._get_help(tool_spec, capsys)
        for legend_entry in shell_interface.get_legend():
            legend_pattern = rf"^ {{4}}{re.escape(legend_entry.marker)} {legend_entry.color_name} +{re.escape(legend_entry.meaning)}$"
            assert re.search(legend_pattern, help_text, flags=re.MULTILINE)

    def test_str_enum_section_titles_print_their_value(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        class SectionTitle(str, Enum):
            SYNCING = "Syncing with the remote"
        tool_spec = cli_builder.ToolSpec(
            tool_name="tool",
            description="a tool",
            commands=cli_builder.command_group(
                section_title=SectionTitle.SYNCING,
                commands=[cli_builder.cli_command(cmd_name="alpha", cmd_fn=_do_nothing)],
            ),
        )
        help_text = self._get_help(tool_spec, capsys)
        assert "Syncing with the remote" in help_text
        assert "SectionTitle" not in help_text


## } U-TEST
