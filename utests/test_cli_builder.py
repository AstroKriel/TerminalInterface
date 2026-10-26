## { U-TEST

##
## === DEPENDENCIES
##

## stdlib
import argparse
import contextlib
import dataclasses
import io
import re
import subprocess
import tempfile
import unittest
from enum import Enum
from pathlib import Path

## local
from heimdall import _terminal_output, cli_builder, shell_interface

##
## === HELPERS
##


def _do_nothing(
    *,
    run_params: shell_interface.RunParams,
) -> None:
    return None


@dataclasses.dataclass(frozen=True)
class _ToolRunParams(shell_interface.RunParams):
    allow_dirty: bool = False


def _make_tool_run_params(
    parsed_args: argparse.Namespace,
) -> _ToolRunParams:
    return _ToolRunParams(
        dry_run=parsed_args.dry_run,
        allow_dirty=parsed_args.allow_dirty,
    )


def _get_help(
    tool: cli_builder.Tool,
) -> str:
    stdout_buffer = io.StringIO()
    with contextlib.redirect_stdout(stdout_buffer), contextlib.suppress(SystemExit):
        cli_builder.run_cli(tool=tool, argv=["--help"])
    return stdout_buffer.getvalue()


def _make_tool(
    *,
    commands: list[cli_builder.CommandEntry],
    flags: list[cli_builder.CommandArg] | None = None,
) -> cli_builder.Tool:
    if flags is None:
        flags = []
    return cli_builder.Tool(
        name="tool",
        description="a tool",
        commands=commands,
        flags=flags,
    )


##
## === TEST SUITE
##


class TestCommandDetails_ArgMapping(unittest.TestCase):

    def _call_with(
        self,
        *,
        cmd_args: list[cli_builder.CommandArg],
        parsed_values: dict[str, str | None],
    ) -> dict[str, str | None]:
        received: dict[str, str | None] = {}

        def record_args(
            *,
            run_params: shell_interface.RunParams,
            **cmd_arg_values: str | None,
        ) -> None:
            received.update(cmd_arg_values)

        _, cmd_details = cli_builder.cli_command(
            cmd_name="test-cmd",
            cmd_fn=record_args,
            cmd_args=cmd_args,
        )
        cmd_details.call(
            run_params=shell_interface.RunParams(),
            parsed_args=argparse.Namespace(dry_run=False, **parsed_values),
        )
        return received

    def test_positional_arg_is_passed_by_name(
        self,
    ) -> None:
        received = self._call_with(
            cmd_args=[cli_builder.CommandArg(arg_name="branch_name")],
            parsed_values={"branch_name": "feature"},
        )
        self.assertEqual(received, {"branch_name": "feature"})

    def test_named_flag_is_passed_without_dashes(
        self,
    ) -> None:
        received = self._call_with(
            cmd_args=[cli_builder.CommandArg(arg_name="--base-ref")],
            parsed_values={"base_ref": "development"},
        )
        self.assertEqual(received, {"base_ref": "development"})

    def test_named_flag_passes_none_when_not_set(
        self,
    ) -> None:
        received = self._call_with(
            cmd_args=[cli_builder.CommandArg(arg_name="--base")],
            parsed_values={"base": None},
        )
        self.assertEqual(received, {"base": None})

    def test_unset_flag_reaches_the_command_as_none_through_run_cli(
        self,
    ) -> None:
        received: list[str | None] = []

        def record_base(
            *,
            run_params: shell_interface.RunParams,
            base: str | None,
        ) -> None:
            received.append(base)

        tool = _make_tool(
            commands=[
                cli_builder.cli_command(
                    cmd_name="go",
                    cmd_fn=record_base,
                    cmd_args=[cli_builder.CommandArg(arg_name="--base")],
                ),
            ],
        )
        cli_builder.run_cli(tool=tool, argv=["go"])
        self.assertEqual(received, [None])


class TestCommandGroup_SectionStamping(unittest.TestCase):

    def test_stamps_section_title_and_keeps_order(
        self,
    ) -> None:
        commands = cli_builder.command_group(
            section_title="Syncing",
            commands=[
                cli_builder.cli_command(cmd_name="alpha", cmd_fn=_do_nothing),
                cli_builder.cli_command(cmd_name="beta", cmd_fn=_do_nothing),
            ],
        )
        self.assertEqual([_cmd_name for _cmd_name, _ in commands], ["alpha", "beta"])
        self.assertEqual([_cmd_details.section_title for _, _cmd_details in commands], ["Syncing", "Syncing"])


class TestRunCli_Dispatch(unittest.TestCase):

    def setUp(
        self,
    ) -> None:
        _terminal_output.reset_output_params()
        self.addCleanup(_terminal_output.reset_output_params)

    def test_dispatches_with_default_run_params(
        self,
    ) -> None:
        received: list[shell_interface.RunParams] = []

        def record_run_params(
            *,
            run_params: shell_interface.RunParams,
        ) -> None:
            received.append(run_params)

        tool = _make_tool(commands=[cli_builder.cli_command(cmd_name="go", cmd_fn=record_run_params)])
        cli_builder.run_cli(tool=tool, argv=["--dry-run", "go"])
        self.assertEqual(received, [shell_interface.RunParams(dry_run=True)])

    def test_extra_flag_reaches_run_params(
        self,
    ) -> None:
        received: list[shell_interface.RunParams] = []

        def record_run_params(
            *,
            run_params: shell_interface.RunParams,
        ) -> None:
            received.append(run_params)

        tool = cli_builder.Tool(
            name="tool",
            description="a tool",
            commands=[cli_builder.cli_command(cmd_name="go", cmd_fn=record_run_params)],
            flags=[cli_builder.CommandArg(arg_name="--allow-dirty", store_true=True)],
            make_run_params=_make_tool_run_params,
        )
        cli_builder.run_cli(tool=tool, argv=["--allow-dirty", "go"])
        self.assertEqual(received, [_ToolRunParams(dry_run=False, allow_dirty=True)])

    def test_failed_command_exits_with_its_return_code(
        self,
    ) -> None:
        def fail(
            *,
            run_params: shell_interface.RunParams,
        ) -> None:
            raise subprocess.CalledProcessError(returncode=3, cmd=["false"])

        tool = _make_tool(commands=[cli_builder.cli_command(cmd_name="go", cmd_fn=fail)])
        with self.assertRaises(SystemExit) as exit_context:
            cli_builder.run_cli(tool=tool, argv=["go"])
        self.assertEqual(exit_context.exception.code, 3)

    def test_record_is_started_from_the_tool(
        self,
    ) -> None:
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        record_path = Path(temporary_directory.name) / "record.log"

        def narrate(
            *,
            run_params: shell_interface.RunParams,
        ) -> None:
            shell_interface.log_task("recorded")

        tool = cli_builder.Tool(
            name="tool",
            description="a tool",
            commands=[cli_builder.cli_command(cmd_name="go", cmd_fn=narrate)],
            record_path=record_path,
        )
        with contextlib.redirect_stderr(io.StringIO()):
            cli_builder.run_cli(tool=tool, argv=["go"])
        self.assertIn("(tool): ○ recorded", record_path.read_text())


class TestHelp_Output(unittest.TestCase):

    def _make_syncing_tool(
        self,
    ) -> cli_builder.Tool:
        return _make_tool(
            commands=cli_builder.command_group(
                section_title="Syncing",
                commands=[cli_builder.cli_command(cmd_name="alpha", cmd_fn=_do_nothing, cmd_help="does alpha")],
            ),
        )

    def test_lists_name_usage_and_sections(
        self,
    ) -> None:
        help_text = _get_help(self._make_syncing_tool())
        self.assertIn("tool: a tool", help_text)
        self.assertIn("usage: tool [--dry-run] <command> [args]", help_text)
        self.assertRegex(help_text, re.compile(r"^ {4}alpha +does alpha$", flags=re.MULTILINE))

    def test_separates_with_spaces_only(
        self,
    ) -> None:
        self.assertNotIn("\t", _get_help(self._make_syncing_tool()))

    def test_descriptions_share_one_column(
        self,
    ) -> None:
        help_lines = _get_help(self._make_syncing_tool()).splitlines()
        alpha_line = next(_line for _line in help_lines if "does alpha" in _line)
        dry_run_line = next(_line for _line in help_lines if "print commands" in _line)
        task_description = _terminal_output.TASK_PARAMS.description
        legend_line = next(_line for _line in help_lines if task_description in _line)
        self.assertEqual(alpha_line.index("does alpha"), dry_run_line.index("print commands"))
        self.assertEqual(alpha_line.index("does alpha"), legend_line.index(task_description))

    def test_longest_label_sets_the_column(
        self,
    ) -> None:
        tool = _make_tool(
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
        self.assertIn("    a-much-longer-command-name  long one", _get_help(tool).splitlines())

    def test_omits_hidden_commands(
        self,
    ) -> None:
        tool = _make_tool(
            commands=[
                *cli_builder.command_group(
                    section_title="Shown",
                    commands=[cli_builder.cli_command(cmd_name="visible", cmd_fn=_do_nothing)],
                ),
                cli_builder.cli_command(cmd_name="secret", cmd_fn=_do_nothing, is_hidden=True),
            ],
        )
        help_text = _get_help(tool)
        self.assertIn("visible", help_text)
        self.assertNotIn("secret", help_text)

    def test_lists_extra_flags(
        self,
    ) -> None:
        tool = _make_tool(
            commands=[],
            flags=[cli_builder.CommandArg(arg_name="--allow-dirty", store_true=True, help="skip the check")],
        )
        help_text = _get_help(tool)
        self.assertIn("usage: tool [--dry-run] [--allow-dirty] <command> [args]", help_text)
        self.assertIn("    --allow-dirty  skip the check", help_text.splitlines())

    def test_legend_lists_each_group_under_its_title(
        self,
    ) -> None:
        help_lines = _get_help(_make_tool(commands=[])).splitlines()
        for legend_group in _terminal_output.LEGEND_GROUPS:
            title_index = help_lines.index(f"  {legend_group.title}")
            for line_offset, message_params in enumerate(legend_group.grouped_message_params, start=1):
                legend_label = f"{message_params.marker.value} {message_params.color.name.lower()}"
                legend_pattern = rf"^ {{4}}{re.escape(legend_label)} +{re.escape(message_params.description)}$"
                self.assertRegex(help_lines[title_index + line_offset], re.compile(legend_pattern))

    def test_str_enum_section_titles_print_their_value(
        self,
    ) -> None:
        class SectionTitle(str, Enum):
            SYNCING = "Syncing with the remote"

        tool = _make_tool(
            commands=cli_builder.command_group(
                section_title=SectionTitle.SYNCING,
                commands=[cli_builder.cli_command(cmd_name="alpha", cmd_fn=_do_nothing)],
            ),
        )
        help_text = _get_help(tool)
        self.assertIn("Syncing with the remote", help_text)
        self.assertNotIn("SectionTitle", help_text)


##
## === ENTRY POINT
##

if __name__ == "__main__":
    unittest.main()

## } U-TEST
