## { MODULE

##
## === DEPENDENCIES
##

## stdlib
import argparse
import shlex
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, final

## third-party
from rich.console import Console as rich_Console

## local
from huginn import _manage_terminal, manage_log, manage_shell

##
## === DATA STRUCTURES
## a tool holds groups of cmds, and each cmd holds its arguments.
##


class ValueCount(str, Enum):
    """How many values an argument takes, as the symbol argparse expects."""
    OPTIONAL = "?"
    ANY = "*"
    AT_LEAST_ONE = "+"


@dataclass(frozen=True)
class CommandArgument:
    """One argument of a cmd or a tool: a bare positional, or a `--flag`."""
    name: str
    description: str | None = None
    value_type: type = str
    default_value: Any = None
    value_placeholder: str | None = None
    is_switch: bool = False
    is_required: bool = False
    value_count: ValueCount | None = None

    @property
    def parameter_name(
        self,
    ) -> str:
        """The cmd function parameter this argument is passed to, e.g. `--word-diff` -> `word_diff`."""
        return self.name.lstrip("-").replace("-", "_")

    @property
    def argparse_keyword_arguments(
        self,
    ) -> dict[str, Any]:
        """Build the keyword arguments for `add_argument`; flags with no description get a default-value hint."""
        if self.is_switch:
            keyword_arguments: dict[str, Any] = {
                "action": "store_true",
                "default": False,
            }
        else:
            keyword_arguments = {"type": self.value_type}
            if self.value_count is not None:
                keyword_arguments["nargs"] = self.value_count.value
            if self.value_placeholder is not None:
                keyword_arguments["metavar"] = self.value_placeholder
            if self.is_required:
                keyword_arguments["required"] = True
            else:
                keyword_arguments["default"] = self.default_value
        if self.description is not None:
            keyword_arguments["help"] = self.description
        elif self.name.startswith("--") and not self.is_required:
            keyword_arguments["help"] = "(default: %(default)s)"
        return keyword_arguments


@dataclass(frozen=True)
class Command:
    """One cmd of a tool, run as `<tool> <name> [arguments]`: its description, its arguments, and the function it calls."""
    name: str
    description: str
    fn: Callable[..., None]
    arguments: list[CommandArgument] = field(default_factory=list)

    def call(
        self,
        *,
        run_params: manage_shell.RunParams,
        parsed_arguments: argparse.Namespace,
    ) -> None:
        """Call `fn` with `run_params` and each argument by its parameter name, all as keywords."""
        argument_values = {
            _argument.parameter_name: getattr(parsed_arguments, _argument.parameter_name)
            for _argument in self.arguments
        }
        self.fn(
            run_params=run_params,
            **argument_values,
        )


@dataclass(frozen=True)
class CommandGroup:
    """Cmds listed together in help under one title."""
    title: str
    cmds: list[Command]


@dataclass(frozen=True)
class CommandLineTool:
    """
    One command line tool: what it is, the cmds it offers, and how one run of it is set up.

    Fields
    ---
    - `flags`:
        Flags beyond `--dry-run`, which every tool has.

    - `hidden_cmds`:
        Cmds that can be run but are left out of help.

    - `run_params_type`:
        `RunParams` or a subclass; built from the parsed flags with `from_parsed_arguments`.
    """
    name: str
    description: str
    cmd_groups: list[CommandGroup]
    hidden_cmds: list[Command] = field(default_factory=list)
    flags: list[CommandArgument] = field(default_factory=list)
    run_params_type: type[manage_shell.RunParams] = manage_shell.RunParams
    output_params: manage_log.OutputParams = manage_log.OutputParams()

    @property
    def all_cmds(
        self,
    ) -> list[Command]:
        grouped_cmds = [_cmd for _cmd_group in self.cmd_groups for _cmd in _cmd_group.cmds]
        return [*grouped_cmds, *self.hidden_cmds]


_DRY_RUN_FLAG = CommandArgument(
    name="--dry-run",
    description="print commands without executing them",
    is_switch=True,
)

##
## === HELP
##

_HELP_INDENT = "    "
_MESSAGE_GROUP_INDENT = "  "
_HELP_GAP_WIDTH = 2


@final
class _CommandLineToolHelp:
    """The help screen of one tool; every row shares one column width."""

    def __init__(
        self,
        command_line_tool: CommandLineTool,
    ) -> None:
        self.command_line_tool = command_line_tool
        self.console = rich_Console(highlight=False)
        self.all_flags = [_DRY_RUN_FLAG, *command_line_tool.flags]
        legend_labels = [
            self._get_legend_label(_message_style)
            for _message_group in _manage_terminal.MESSAGE_GROUPS
            for _message_style in _message_group.grouped_message_styles
        ]
        all_labels = [
            *[_cmd.name for _cmd_group in command_line_tool.cmd_groups for _cmd in _cmd_group.cmds],
            *[_flag.name for _flag in self.all_flags],
            *legend_labels,
        ]
        self.column_width = max(len(_label) for _label in all_labels) + _HELP_GAP_WIDTH

    @staticmethod
    def _get_title_text(
        title: str,
    ) -> str:
        if isinstance(title, Enum):
            return str(title.value)
        return title

    @staticmethod
    def _get_legend_label(
        message_style: _manage_terminal.MessageStyle,
    ) -> str:
        """The symbol and colour name, e.g. `● green`; `plain` for a line with neither."""
        if message_style.symbol is None or message_style.colour is None:
            return "plain"
        return f"{message_style.symbol.value} {message_style.colour.name.lower()}"

    def _print_row(
        self,
        *,
        label: str,
        label_style: str | None,
        description: str,
    ) -> None:
        padding = " " * (self.column_width - len(label))
        styled_label = label
        if label_style is not None:
            styled_label = f"[{label_style}]{label}[/]"
        self.console.print(f"{_HELP_INDENT}{styled_label}{padding}{description}")

    def _print_header(
        self,
    ) -> None:
        usage_flags = " ".join(f"[{_flag.name}]" for _flag in self.all_flags)
        usage_text = manage_log.escape_markup(f"{self.command_line_tool.name} {usage_flags} <command> [args]")
        self.console.print()
        self.console.print(
            f"[bold]{self.command_line_tool.name}[/bold]: {self.command_line_tool.description}",
        )
        self.console.print()
        self.console.print(f"[dim]usage:[/dim] {usage_text}")

    def _print_cmd_groups(
        self,
    ) -> None:
        for cmd_group in self.command_line_tool.cmd_groups:
            self.console.print()
            self.console.print(f"[bold]{self._get_title_text(cmd_group.title)}[/bold]")
            for cmd in cmd_group.cmds:
                self._print_row(
                    label=cmd.name,
                    label_style=_manage_terminal.Colour.CYAN.value,
                    description=cmd.description,
                )

    def _print_flags(
        self,
    ) -> None:
        self.console.print()
        self.console.print("[bold]Flags[/bold]")
        for flag in self.all_flags:
            flag_description = flag.description
            if flag_description is None:
                flag_description = ""
            self._print_row(
                label=flag.name,
                label_style=_manage_terminal.Colour.CYAN.value,
                description=flag_description,
            )

    def _print_legend(
        self,
    ) -> None:
        self.console.print()
        self.console.print("[bold]Output legend[/bold]")
        for message_group in _manage_terminal.MESSAGE_GROUPS:
            self.console.print(f"{_MESSAGE_GROUP_INDENT}[dim]{message_group.title}[/dim]")
            for message_style in message_group.grouped_message_styles:
                legend_colour = None
                if message_style.colour is not None:
                    legend_colour = message_style.colour.value
                self._print_row(
                    label=self._get_legend_label(message_style),
                    label_style=legend_colour,
                    description=message_style.description,
                )
        self.console.print()

    def print_help(
        self,
    ) -> None:
        """Print the header, the cmds by group, the flags, and the output legend."""
        self._print_header()
        self._print_cmd_groups()
        self._print_flags()
        self._print_legend()


##
## === ENTRY POINT
##


def _build_parser(
    command_line_tool: CommandLineTool,
) -> argparse.ArgumentParser:
    argument_parser = argparse.ArgumentParser(
        prog=command_line_tool.name,
        description=command_line_tool.description,
        add_help=False,
    )
    argument_parser.add_argument(
        "-h",
        "--help",
        action="store_true",
    )
    for flag in [_DRY_RUN_FLAG, *command_line_tool.flags]:
        argument_parser.add_argument(flag.name, **flag.argparse_keyword_arguments)
    subparsers = argument_parser.add_subparsers(
        dest="cmd",
        required=False,
        metavar="<command>",
    )
    for cmd in command_line_tool.all_cmds:
        subparser = subparsers.add_parser(cmd.name, help=cmd.description)
        for argument in cmd.arguments:
            subparser.add_argument(argument.name, **argument.argparse_keyword_arguments)
    return argument_parser


def run_cli(
    *,
    command_line_tool: CommandLineTool,
    argv: Sequence[str] | None = None,
) -> None:
    """Parse argv (default: `sys.argv`), build the run params, set up output for the run, and run one cmd."""
    parsed_arguments = _build_parser(command_line_tool).parse_args(argv)
    if parsed_arguments.help or parsed_arguments.cmd is None:
        command_line_tool_help = _CommandLineToolHelp(command_line_tool)
        command_line_tool_help.print_help()
        return
    run_params = command_line_tool.run_params_type.from_parsed_arguments(parsed_arguments)
    _manage_terminal.set_output_params(
        output_params=command_line_tool.output_params,
        dry_run=run_params.dry_run,
    )
    cmds_by_name = {_cmd.name: _cmd for _cmd in command_line_tool.all_cmds}
    selected_cmd = cmds_by_name[parsed_arguments.cmd]
    try:
        selected_cmd.call(
            run_params=run_params,
            parsed_arguments=parsed_arguments,
        )
    except subprocess.CalledProcessError as process_error:
        failed_cmd = shlex.join(process_error.cmd)
        failure_text = manage_log.escape_markup(
            f"`{failed_cmd}` failed with exit status {process_error.returncode}.",
        )
        manage_log.exit_with_error(
            failure_text,
            exit_code=process_error.returncode,
        )


## } MODULE
