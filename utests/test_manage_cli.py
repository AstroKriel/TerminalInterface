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
from typing import Self

## local
from heimdall import _manage_terminal, manage_cli, manage_log, manage_shell

##
## === HELPERS
##


def _do_nothing(
    *,
    run_params: manage_shell.RunParams,
) -> None:
    return None


@dataclasses.dataclass(frozen=True)
class _ToolRunParams(manage_shell.RunParams):
    allow_dirty: bool = False

    @classmethod
    def from_parsed_arguments(
        cls,
        parsed_arguments: argparse.Namespace,
    ) -> Self:
        return cls(
            dry_run=parsed_arguments.dry_run,
            allow_dirty=parsed_arguments.allow_dirty,
        )


def _get_help(
    command_line_tool: manage_cli.CommandLineTool,
) -> str:
    stdout_buffer = io.StringIO()
    with contextlib.redirect_stdout(stdout_buffer), contextlib.suppress(SystemExit):
        manage_cli.run_cli(
            command_line_tool=command_line_tool,
            argv=["--help"],
        )
    return stdout_buffer.getvalue()


def _make_cmd_group(
    *cmds: manage_cli.Command,
    title: str = "Commands",
) -> manage_cli.CommandGroup:
    return manage_cli.CommandGroup(
        title=title,
        cmds=list(cmds),
    )


def _make_go_cmd(
    fn: Callable[..., None],
    *,
    arguments: list[manage_cli.CommandArgument] | None = None,
) -> manage_cli.Command:
    if arguments is None:
        arguments = []
    return manage_cli.Command(
        name="go",
        description="go",
        fn=fn,
        arguments=arguments,
    )


def _make_command_line_tool(
    *,
    cmd_groups: list[manage_cli.CommandGroup],
    hidden_cmds: list[manage_cli.Command] | None = None,
    flags: list[manage_cli.CommandArgument] | None = None,
) -> manage_cli.CommandLineTool:
    if hidden_cmds is None:
        hidden_cmds = []
    if flags is None:
        flags = []
    return manage_cli.CommandLineTool(
        name="tool",
        description="a tool",
        cmd_groups=cmd_groups,
        hidden_cmds=hidden_cmds,
        flags=flags,
    )


##
## === TEST SUITE
##


class TestCommand_ArgumentMapping(unittest.TestCase):

    def _call_with(
        self,
        *,
        arguments: list[manage_cli.CommandArgument],
        parsed_values: dict[str, str | None],
    ) -> dict[str, str | None]:
        received: dict[str, str | None] = {}

        def record_arguments(
            *,
            run_params: manage_shell.RunParams,
            **argument_values: str | None,
        ) -> None:
            received.update(argument_values)

        cmd = manage_cli.Command(
            name="test-command",
            description="records its arguments",
            fn=record_arguments,
            arguments=arguments,
        )
        cmd.call(
            run_params=manage_shell.RunParams(),
            parsed_arguments=argparse.Namespace(dry_run=False, **parsed_values),
        )
        return received

    def test_positional_argument_is_passed_by_name(
        self,
    ) -> None:
        received = self._call_with(
            arguments=[manage_cli.CommandArgument(name="branch_name")],
            parsed_values={"branch_name": "feature"},
        )
        self.assertEqual(received, {"branch_name": "feature"})

    def test_named_flag_is_passed_without_dashes(
        self,
    ) -> None:
        received = self._call_with(
            arguments=[manage_cli.CommandArgument(name="--base-ref")],
            parsed_values={"base_ref": "development"},
        )
        self.assertEqual(received, {"base_ref": "development"})

    def test_named_flag_passes_none_when_not_set(
        self,
    ) -> None:
        received = self._call_with(
            arguments=[manage_cli.CommandArgument(name="--base")],
            parsed_values={"base": None},
        )
        self.assertEqual(received, {"base": None})

    def test_unset_flag_reaches_the_cmd_as_none_through_run_cli(
        self,
    ) -> None:
        received: list[str | None] = []

        def record_base(
            *,
            run_params: manage_shell.RunParams,
            base: str | None,
        ) -> None:
            received.append(base)

        go_cmd = _make_go_cmd(
            record_base,
            arguments=[manage_cli.CommandArgument(name="--base")],
        )
        command_line_tool = _make_command_line_tool(cmd_groups=[_make_cmd_group(go_cmd)])
        manage_cli.run_cli(
            command_line_tool=command_line_tool,
            argv=["go"],
        )
        self.assertEqual(received, [None])

    def test_value_count_collects_every_value(
        self,
    ) -> None:
        received: list[list[str]] = []

        def record_paths(
            *,
            run_params: manage_shell.RunParams,
            paths: list[str],
        ) -> None:
            received.append(paths)

        paths_argument = manage_cli.CommandArgument(
            name="paths",
            value_count=manage_cli.ValueCount.AT_LEAST_ONE,
        )
        go_cmd = _make_go_cmd(
            record_paths,
            arguments=[paths_argument],
        )
        command_line_tool = _make_command_line_tool(cmd_groups=[_make_cmd_group(go_cmd)])
        manage_cli.run_cli(
            command_line_tool=command_line_tool,
            argv=["go", "a", "b"],
        )
        self.assertEqual(received, [["a", "b"]])


class TestRunCli_Dispatch(unittest.TestCase):

    def setUp(
        self,
    ) -> None:
        _manage_terminal.reset_output_params()
        self.addCleanup(_manage_terminal.reset_output_params)

    def test_dispatches_with_default_run_params(
        self,
    ) -> None:
        received: list[manage_shell.RunParams] = []

        def record_run_params(
            *,
            run_params: manage_shell.RunParams,
        ) -> None:
            received.append(run_params)

        go_cmd = _make_go_cmd(record_run_params)
        command_line_tool = _make_command_line_tool(cmd_groups=[_make_cmd_group(go_cmd)])
        manage_cli.run_cli(
            command_line_tool=command_line_tool,
            argv=["--dry-run", "go"],
        )
        self.assertEqual(received, [manage_shell.RunParams(dry_run=True)])

    def test_extra_flag_reaches_run_params(
        self,
    ) -> None:
        received: list[manage_shell.RunParams] = []

        def record_run_params(
            *,
            run_params: manage_shell.RunParams,
        ) -> None:
            received.append(run_params)

        go_cmd = _make_go_cmd(record_run_params)
        allow_dirty_flag = manage_cli.CommandArgument(
            name="--allow-dirty",
            is_switch=True,
        )
        command_line_tool = manage_cli.CommandLineTool(
            name="tool",
            description="a tool",
            cmd_groups=[_make_cmd_group(go_cmd)],
            flags=[allow_dirty_flag],
            run_params_type=_ToolRunParams,
        )
        manage_cli.run_cli(
            command_line_tool=command_line_tool,
            argv=["--allow-dirty", "go"],
        )
        self.assertEqual(
            received,
            [
                _ToolRunParams(
                    dry_run=False,
                    allow_dirty=True,
                ),
            ],
        )

    def test_hidden_cmd_can_be_run(
        self,
    ) -> None:
        received: list[manage_shell.RunParams] = []

        def record_run_params(
            *,
            run_params: manage_shell.RunParams,
        ) -> None:
            received.append(run_params)

        command_line_tool = _make_command_line_tool(
            cmd_groups=[],
            hidden_cmds=[_make_go_cmd(record_run_params)],
        )
        manage_cli.run_cli(
            command_line_tool=command_line_tool,
            argv=["go"],
        )
        self.assertEqual(received, [manage_shell.RunParams()])

    def test_failed_cmd_exits_with_its_return_code(
        self,
    ) -> None:

        def fail(
            *,
            run_params: manage_shell.RunParams,
        ) -> None:
            raise subprocess.CalledProcessError(
                returncode=3,
                cmd=["false"],
            )

        command_line_tool = _make_command_line_tool(cmd_groups=[_make_cmd_group(_make_go_cmd(fail))])
        stderr_buffer = io.StringIO()
        with contextlib.redirect_stderr(stderr_buffer), self.assertRaises(SystemExit) as exit_context:
            manage_cli.run_cli(
                command_line_tool=command_line_tool,
                argv=["go"],
            )
        self.assertEqual(exit_context.exception.code, 3)
        self.assertEqual(stderr_buffer.getvalue(), "● error: `false` failed with exit status 3.\n")

    def test_log_is_started_from_the_tool(
        self,
    ) -> None:
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        log_path = Path(temporary_directory.name) / "tool.log"

        def narrate(
            *,
            run_params: manage_shell.RunParams,
        ) -> None:
            manage_log.log_task("logged")

        command_line_tool = manage_cli.CommandLineTool(
            name="tool",
            description="a tool",
            cmd_groups=[_make_cmd_group(_make_go_cmd(narrate))],
            output_params=manage_log.OutputParams(log_path=log_path),
        )
        with contextlib.redirect_stderr(io.StringIO()):
            manage_cli.run_cli(
                command_line_tool=command_line_tool,
                argv=["go"],
            )
        self.assertIn("○ logged", log_path.read_text())


class TestHelp_Output(unittest.TestCase):

    def _make_syncing_command_line_tool(
        self,
    ) -> manage_cli.CommandLineTool:
        alpha_cmd = manage_cli.Command(
            name="alpha",
            description="does alpha",
            fn=_do_nothing,
        )
        return _make_command_line_tool(cmd_groups=[_make_cmd_group(alpha_cmd, title="Syncing")])

    def test_lists_name_usage_and_groups(
        self,
    ) -> None:
        help_text = _get_help(self._make_syncing_command_line_tool())
        self.assertIn("tool: a tool", help_text)
        self.assertIn("usage: tool [--dry-run] <command> [args]", help_text)
        self.assertIn("Syncing", help_text.splitlines())
        self.assertRegex(help_text, re.compile(r"^ {4}alpha +does alpha$", flags=re.MULTILINE))

    def test_lists_groups_in_order(
        self,
    ) -> None:
        first_cmd = manage_cli.Command(
            name="first",
            description="first one",
            fn=_do_nothing,
        )
        second_cmd = manage_cli.Command(
            name="second",
            description="second one",
            fn=_do_nothing,
        )
        command_line_tool = _make_command_line_tool(
            cmd_groups=[
                _make_cmd_group(first_cmd, title="First group"),
                _make_cmd_group(second_cmd, title="Second group"),
            ],
        )
        help_lines = _get_help(command_line_tool).splitlines()
        self.assertLess(help_lines.index("First group"), help_lines.index("Second group"))

    def test_no_cmd_prints_the_help(
        self,
    ) -> None:
        stdout_buffer = io.StringIO()
        with contextlib.redirect_stdout(stdout_buffer):
            manage_cli.run_cli(
                command_line_tool=self._make_syncing_command_line_tool(),
                argv=[],
            )
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
        task_description = _manage_terminal.TASK_STYLE.description
        legend_line = next(_line for _line in help_lines if task_description in _line)
        self.assertEqual(alpha_line.index("does alpha"), dry_run_line.index("print commands"))
        self.assertEqual(alpha_line.index("does alpha"), legend_line.index(task_description))

    def test_longest_label_sets_the_column(
        self,
    ) -> None:
        long_cmd = manage_cli.Command(
            name="a-much-longer-command-name",
            description="long one",
            fn=_do_nothing,
        )
        command_line_tool = _make_command_line_tool(cmd_groups=[_make_cmd_group(long_cmd)])
        self.assertIn("    a-much-longer-command-name  long one", _get_help(command_line_tool).splitlines())

    def test_omits_hidden_cmds(
        self,
    ) -> None:
        visible_cmd = manage_cli.Command(
            name="visible",
            description="shown",
            fn=_do_nothing,
        )
        secret_cmd = manage_cli.Command(
            name="secret",
            description="not shown",
            fn=_do_nothing,
        )
        command_line_tool = _make_command_line_tool(
            cmd_groups=[_make_cmd_group(visible_cmd)],
            hidden_cmds=[secret_cmd],
        )
        help_text = _get_help(command_line_tool)
        self.assertIn("visible", help_text)
        self.assertNotIn("secret", help_text)

    def test_lists_extra_flags(
        self,
    ) -> None:
        allow_dirty_flag = manage_cli.CommandArgument(
            name="--allow-dirty",
            description="skip the check",
            is_switch=True,
        )
        command_line_tool = _make_command_line_tool(
            cmd_groups=[],
            flags=[allow_dirty_flag],
        )
        help_text = _get_help(command_line_tool)
        self.assertIn("usage: tool [--dry-run] [--allow-dirty] <command> [args]", help_text)
        self.assertIn("    --allow-dirty  skip the check", help_text.splitlines())

    def test_legend_labels_a_plain_result_as_plain(
        self,
    ) -> None:
        result_description = _manage_terminal.OutcomeContent.RESULT.value.description
        self.assertRegex(
            _get_help(_make_command_line_tool(cmd_groups=[])),
            re.compile(rf"^ {{4}}plain +{re.escape(result_description)}$", flags=re.MULTILINE),
        )

    def test_legend_lists_each_group_under_its_title(
        self,
    ) -> None:
        help_lines = _get_help(_make_command_line_tool(cmd_groups=[])).splitlines()
        for message_group in _manage_terminal.MESSAGE_GROUPS:
            title_index = help_lines.index(f"  {message_group.title}")
            for line_offset, message_style in enumerate(message_group.grouped_message_styles, start=1):
                legend_label = "plain"
                if message_style.symbol is not None and message_style.colour is not None:
                    legend_label = f"{message_style.symbol.value} {message_style.colour.name.lower()}"
                legend_pattern = rf"^ {{4}}{re.escape(legend_label)} +{re.escape(message_style.description)}$"
                self.assertRegex(help_lines[title_index + line_offset], re.compile(legend_pattern))

    def test_str_enum_group_titles_print_their_value(
        self,
    ) -> None:

        class GroupTitle(str, Enum):
            SYNCING = "Syncing with the remote"

        alpha_cmd = manage_cli.Command(
            name="alpha",
            description="does alpha",
            fn=_do_nothing,
        )
        command_line_tool = _make_command_line_tool(
            cmd_groups=[_make_cmd_group(alpha_cmd, title=GroupTitle.SYNCING)]
        )
        help_text = _get_help(command_line_tool)
        self.assertIn("Syncing with the remote", help_text)
        self.assertNotIn("GroupTitle", help_text)


##
## === ENTRY POINT
##

if __name__ == "__main__":
    unittest.main()

## } U-TEST
