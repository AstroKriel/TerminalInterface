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
from collections.abc import Callable
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


def _make_command_line_tool_run_params(
    parsed_arguments: argparse.Namespace,
) -> _ToolRunParams:
    return _ToolRunParams(
        dry_run=parsed_arguments.dry_run,
        allow_dirty=parsed_arguments.allow_dirty,
    )


def _get_help(
    command_line_tool: cli_builder.CommandLineTool,
) -> str:
    stdout_buffer = io.StringIO()
    with contextlib.redirect_stdout(stdout_buffer), contextlib.suppress(SystemExit):
        cli_builder.run_cli(command_line_tool=command_line_tool, argv=["--help"])
    return stdout_buffer.getvalue()


def _make_go_command(
    command_fn: Callable[..., None],
    *,
    command_arguments: list[cli_builder.CommandArgument] | None = None,
) -> list[cli_builder.Command]:
    go_command = cli_builder.make_command(
        command_name="go",
        command_fn=command_fn,
        command_arguments=command_arguments,
    )
    return cli_builder.make_command_group(
        section_title="Commands",
        commands=[go_command],
    )


def _make_command_line_tool(
    *,
    commands: list[cli_builder.Command],
    flags: list[cli_builder.CommandArgument] | None = None,
) -> cli_builder.CommandLineTool:
    if flags is None:
        flags = []
    return cli_builder.CommandLineTool(
        name="tool",
        description="a tool",
        commands=commands,
        flags=flags,
    )


##
## === TEST SUITE
##


class TestCommand_ArgumentMapping(unittest.TestCase):

    def _call_with(
        self,
        *,
        command_arguments: list[cli_builder.CommandArgument],
        parsed_values: dict[str, str | None],
    ) -> dict[str, str | None]:
        received: dict[str, str | None] = {}

        def record_arguments(
            *,
            run_params: shell_interface.RunParams,
            **command_argument_values: str | None,
        ) -> None:
            received.update(command_argument_values)

        command = cli_builder.make_command(
            command_name="test-command",
            command_fn=record_arguments,
            command_arguments=command_arguments,
        )
        command.call(
            run_params=shell_interface.RunParams(),
            parsed_arguments=argparse.Namespace(dry_run=False, **parsed_values),
        )
        return received

    def test_positional_argument_is_passed_by_name(
        self,
    ) -> None:
        received = self._call_with(
            command_arguments=[cli_builder.CommandArgument(argument_name="branch_name")],
            parsed_values={"branch_name": "feature"},
        )
        self.assertEqual(received, {"branch_name": "feature"})

    def test_named_flag_is_passed_without_dashes(
        self,
    ) -> None:
        received = self._call_with(
            command_arguments=[cli_builder.CommandArgument(argument_name="--base-ref")],
            parsed_values={"base_ref": "development"},
        )
        self.assertEqual(received, {"base_ref": "development"})

    def test_named_flag_passes_none_when_not_set(
        self,
    ) -> None:
        received = self._call_with(
            command_arguments=[cli_builder.CommandArgument(argument_name="--base")],
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

        command_line_tool = _make_command_line_tool(
            commands=_make_go_command(
                record_base,
                command_arguments=[cli_builder.CommandArgument(argument_name="--base")],
            ),
        )
        cli_builder.run_cli(command_line_tool=command_line_tool, argv=["go"])
        self.assertEqual(received, [None])

    def test_value_count_collects_every_value(
        self,
    ) -> None:
        received: list[list[str]] = []

        def record_paths(
            *,
            run_params: shell_interface.RunParams,
            paths: list[str],
        ) -> None:
            received.append(paths)

        paths_argument = cli_builder.CommandArgument(
            argument_name="paths",
            value_count=cli_builder.ValueCount.AT_LEAST_ONE,
        )
        command_line_tool = _make_command_line_tool(
            commands=_make_go_command(
                record_paths,
                command_arguments=[paths_argument],
            ),
        )
        cli_builder.run_cli(command_line_tool=command_line_tool, argv=["go", "a", "b"])
        self.assertEqual(received, [["a", "b"]])


class TestCommandGroup_SectionStamping(unittest.TestCase):

    def test_stamps_section_title_and_keeps_order(
        self,
    ) -> None:
        commands = cli_builder.make_command_group(
            section_title="Syncing",
            commands=[
                cli_builder.make_command(command_name="alpha", command_fn=_do_nothing),
                cli_builder.make_command(command_name="beta", command_fn=_do_nothing),
            ],
        )
        self.assertEqual([_command.command_name for _command in commands], ["alpha", "beta"])
        self.assertEqual([_command.section_title for _command in commands], ["Syncing", "Syncing"])


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

        command_line_tool = _make_command_line_tool(commands=_make_go_command(record_run_params))
        cli_builder.run_cli(command_line_tool=command_line_tool, argv=["--dry-run", "go"])
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

        command_line_tool = cli_builder.CommandLineTool(
            name="tool",
            description="a tool",
            commands=_make_go_command(record_run_params),
            flags=[cli_builder.CommandArgument(argument_name="--allow-dirty", is_switch=True)],
            make_run_params=_make_command_line_tool_run_params,
        )
        cli_builder.run_cli(command_line_tool=command_line_tool, argv=["--allow-dirty", "go"])
        self.assertEqual(received, [_ToolRunParams(dry_run=False, allow_dirty=True)])

    def test_failed_command_exits_with_its_return_code(
        self,
    ) -> None:
        def fail(
            *,
            run_params: shell_interface.RunParams,
        ) -> None:
            raise subprocess.CalledProcessError(returncode=3, cmd=["false"])

        command_line_tool = _make_command_line_tool(commands=_make_go_command(fail))
        stderr_buffer = io.StringIO()
        with contextlib.redirect_stderr(stderr_buffer), self.assertRaises(SystemExit) as exit_context:
            cli_builder.run_cli(command_line_tool=command_line_tool, argv=["go"])
        self.assertEqual(exit_context.exception.code, 3)
        self.assertEqual(stderr_buffer.getvalue(), "● error: `false` failed with exit status 3.\n")

    def test_visible_command_outside_a_group_is_rejected(
        self,
    ) -> None:
        command_line_tool = _make_command_line_tool(commands=[cli_builder.make_command(command_name="loose", command_fn=_do_nothing)])
        with self.assertRaises(ValueError):
            cli_builder.run_cli(command_line_tool=command_line_tool, argv=["loose"])

    def test_log_is_started_from_the_tool(
        self,
    ) -> None:
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        log_path = Path(temporary_directory.name) / "tool.log"

        def narrate(
            *,
            run_params: shell_interface.RunParams,
        ) -> None:
            shell_interface.log_task("logged")

        command_line_tool = cli_builder.CommandLineTool(
            name="tool",
            description="a tool",
            commands=_make_go_command(narrate),
            log_path=log_path,
        )
        with contextlib.redirect_stderr(io.StringIO()):
            cli_builder.run_cli(command_line_tool=command_line_tool, argv=["go"])
        self.assertIn("○ logged", log_path.read_text())


class TestHelp_Output(unittest.TestCase):

    def _make_syncing_command_line_tool(
        self,
    ) -> cli_builder.CommandLineTool:
        return _make_command_line_tool(
            commands=cli_builder.make_command_group(
                section_title="Syncing",
                commands=[cli_builder.make_command(command_name="alpha", command_fn=_do_nothing, command_help="does alpha")],
            ),
        )

    def test_lists_name_usage_and_sections(
        self,
    ) -> None:
        help_text = _get_help(self._make_syncing_command_line_tool())
        self.assertIn("tool: a tool", help_text)
        self.assertIn("usage: tool [--dry-run] <command> [args]", help_text)
        self.assertRegex(help_text, re.compile(r"^ {4}alpha +does alpha$", flags=re.MULTILINE))

    def test_no_command_prints_the_help(
        self,
    ) -> None:
        stdout_buffer = io.StringIO()
        with contextlib.redirect_stdout(stdout_buffer):
            cli_builder.run_cli(command_line_tool=self._make_syncing_command_line_tool(), argv=[])
        self.assertIn("usage: tool [--dry-run] <command> [args]", stdout_buffer.getvalue())

    def test_separates_with_spaces_only(
        self,
    ) -> None:
        self.assertNotIn("\t", _get_help(self._make_syncing_command_line_tool()))

    def test_descriptions_share_one_column(
        self,
    ) -> None:
        help_lines = _get_help(self._make_syncing_command_line_tool()).splitlines()
        alpha_line = next(_line for _line in help_lines if "does alpha" in _line)
        dry_run_line = next(_line for _line in help_lines if "print commands" in _line)
        task_description = _terminal_output.TASK_STYLE.description
        legend_line = next(_line for _line in help_lines if task_description in _line)
        self.assertEqual(alpha_line.index("does alpha"), dry_run_line.index("print commands"))
        self.assertEqual(alpha_line.index("does alpha"), legend_line.index(task_description))

    def test_longest_label_sets_the_column(
        self,
    ) -> None:
        command_line_tool = _make_command_line_tool(
            commands=cli_builder.make_command_group(
                section_title="Syncing",
                commands=[
                    cli_builder.make_command(
                        command_name="a-much-longer-command-name",
                        command_fn=_do_nothing,
                        command_help="long one",
                    ),
                ],
            ),
        )
        self.assertIn("    a-much-longer-command-name  long one", _get_help(command_line_tool).splitlines())

    def test_omits_hidden_commands(
        self,
    ) -> None:
        command_line_tool = _make_command_line_tool(
            commands=[
                *cli_builder.make_command_group(
                    section_title="Shown",
                    commands=[cli_builder.make_command(command_name="visible", command_fn=_do_nothing)],
                ),
                cli_builder.make_command(command_name="secret", command_fn=_do_nothing, is_hidden=True),
            ],
        )
        help_text = _get_help(command_line_tool)
        self.assertIn("visible", help_text)
        self.assertNotIn("secret", help_text)

    def test_lists_extra_flags(
        self,
    ) -> None:
        command_line_tool = _make_command_line_tool(
            commands=[],
            flags=[cli_builder.CommandArgument(argument_name="--allow-dirty", is_switch=True, argument_help="skip the check")],
        )
        help_text = _get_help(command_line_tool)
        self.assertIn("usage: tool [--dry-run] [--allow-dirty] <command> [args]", help_text)
        self.assertIn("    --allow-dirty  skip the check", help_text.splitlines())

    def test_legend_labels_a_plain_result_as_plain(
        self,
    ) -> None:
        result_description = _terminal_output.OutcomeContent.RESULT.value.description
        self.assertRegex(
            _get_help(_make_command_line_tool(commands=[])),
            re.compile(rf"^ {{4}}plain +{re.escape(result_description)}$", flags=re.MULTILINE),
        )

    def test_legend_lists_each_group_under_its_title(
        self,
    ) -> None:
        help_lines = _get_help(_make_command_line_tool(commands=[])).splitlines()
        for message_group in _terminal_output.MESSAGE_GROUPS:
            title_index = help_lines.index(f"  {message_group.title}")
            for line_offset, message_style in enumerate(message_group.grouped_message_styles, start=1):
                legend_label = "plain"
                if message_style.symbol is not None and message_style.colour is not None:
                    legend_label = f"{message_style.symbol.value} {message_style.colour.name.lower()}"
                legend_pattern = rf"^ {{4}}{re.escape(legend_label)} +{re.escape(message_style.description)}$"
                self.assertRegex(help_lines[title_index + line_offset], re.compile(legend_pattern))

    def test_str_enum_section_titles_print_their_value(
        self,
    ) -> None:
        class SectionTitle(str, Enum):
            SYNCING = "Syncing with the remote"

        command_line_tool = _make_command_line_tool(
            commands=cli_builder.make_command_group(
                section_title=SectionTitle.SYNCING,
                commands=[cli_builder.make_command(command_name="alpha", command_fn=_do_nothing)],
            ),
        )
        help_text = _get_help(command_line_tool)
        self.assertIn("Syncing with the remote", help_text)
        self.assertNotIn("SectionTitle", help_text)


##
## === ENTRY POINT
##

if __name__ == "__main__":
    unittest.main()

## } U-TEST
