## { MODULE

##
## === DEPENDENCIES
##

## stdlib
import argparse
import shlex
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field, replace
from enum import Enum
from pathlib import Path
from typing import Any, final

## third-party
from rich.console import Console as rich_Console

## local
from heimdall import _manage_terminal, manage_log, manage_shell

##
## === DATA STRUCTURES
##


class ValueCount(str, Enum):
    """How many values an argument takes, as the symbol argparse expects."""
    OPTIONAL = "?"
    ANY = "*"
    AT_LEAST_ONE = "+"


@dataclass(frozen=True)
class CommandArgument:
    """One argparse argument for a subcommand: a bare positional, or a `--flag`."""
    argument_name: str
    value_type: type = str
    default_value: Any = None
    value_placeholder: str | None = None
    argument_help: str | None = None
    is_switch: bool = False
    is_required: bool = False
    value_count: ValueCount | None = None

    @property
    def parameter_name(
        self,
    ) -> str:
        """The command function parameter this argument is passed to, e.g. `--word-diff` -> `word_diff`."""
        return self.argument_name.lstrip("-").replace("-", "_")

    @property
    def argparse_keyword_arguments(
        self,
    ) -> dict[str, Any]:
        """Build the keyword arguments for `add_argument`; flags with no explicit help get a default-value hint."""
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
        if self.argument_help is not None:
            keyword_arguments["help"] = self.argument_help
        elif self.argument_name.startswith("--") and not self.is_required:
            keyword_arguments["help"] = "(default: %(default)s)"
        return keyword_arguments


@dataclass(frozen=True)
class Command:
    """One subcommand: its name, its help, its arguments, and the function it calls."""
    cmd_name: str
    cmd_help: str
    cmd_fn: Callable[..., None]
    cmd_arguments: list[CommandArgument]
    section_title: str | None
    is_hidden: bool

    def call(
        self,
        *,
        run_params: manage_shell.RunParams,
        parsed_arguments: argparse.Namespace,
    ) -> None:
        """Call `cmd_fn` with `run_params` and each argument by its argparse name, all as keywords."""
        cmd_argument_values = {
            _cmd_argument.parameter_name: getattr(parsed_arguments, _cmd_argument.parameter_name)
            for _cmd_argument in self.cmd_arguments
        }
        self.cmd_fn(
            run_params=run_params,
            **cmd_argument_values,
        )


##
## === TOOL
##


def _make_default_run_params(
    parsed_arguments: argparse.Namespace,
) -> manage_shell.RunParams:
    return manage_shell.RunParams(dry_run=parsed_arguments.dry_run)


@dataclass(frozen=True)
class CommandLineTool:
    """
    One command line tool: its name, its commands, its flags, and how its output behaves.

    Fields
    ---
    - `flags`:
        Flags beyond `--dry-run`, which every tool has.

    - `make_run_params`:
        Builds the `RunParams` of the tool (or a subclass) from the parsed flags.

    - `log_path`:
        Where every printed line is also appended as plain text; `None` writes no log.
    """
    name: str
    description: str
    cmds: list[Command]
    flags: list[CommandArgument] = field(default_factory=list)
    make_run_params: Callable[[argparse.Namespace], manage_shell.RunParams] = _make_default_run_params
    show_timestamps: bool = False
    log_path: Path | None = None


_DRY_RUN_FLAG = CommandArgument(
    argument_name="--dry-run",
    is_switch=True,
    argument_help="print commands without executing them",
)

##
## === COMMAND TABLE
##


def make_cmd(
    *,
    cmd_name: str,
    cmd_fn: Callable[..., None],
    cmd_help: str = "",
    cmd_arguments: list[CommandArgument] | None = None,
    is_hidden: bool = False,
) -> Command:
    """Build one command for the command table; `make_cmd_group` stamps its section."""
    if cmd_arguments is None:
        cmd_arguments = []
    return Command(
        cmd_name=cmd_name,
        cmd_help=cmd_help,
        cmd_fn=cmd_fn,
        cmd_arguments=cmd_arguments,
        section_title=None,
        is_hidden=is_hidden,
    )


def make_cmd_group(
    *,
    section_title: str,
    cmds: list[Command],
) -> list[Command]:
    """Stamp `section_title` onto each command so a group names its section exactly once."""
    return [replace(_cmd, section_title=section_title) for _cmd in cmds]


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
        self.visible_cmds = [_cmd for _cmd in command_line_tool.cmds if not _cmd.is_hidden]
        legend_labels = [
            self._get_legend_label(_message_style)
            for _message_group in _manage_terminal.MESSAGE_GROUPS
            for _message_style in _message_group.grouped_message_styles
        ]
        all_labels = [
            *[_cmd.cmd_name for _cmd in self.visible_cmds],
            *[_flag.argument_name for _flag in self.all_flags],
            *legend_labels,
        ]
        self.column_width = max(len(_label) for _label in all_labels) + _HELP_GAP_WIDTH

    @staticmethod
    def _get_section_text(
        section_title: str,
    ) -> str:
        if isinstance(section_title, Enum):
            return str(section_title.value)
        return section_title

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
        usage_flags = " ".join(f"[{_flag.argument_name}]" for _flag in self.all_flags)
        usage_text = manage_log.escape_markup(f"{self.command_line_tool.name} {usage_flags} <command> [args]")
        self.console.print()
        self.console.print(
            f"[bold]{self.command_line_tool.name}[/bold]: {self.command_line_tool.description}",
        )
        self.console.print()
        self.console.print(f"[dim]usage:[/dim] {usage_text}")

    def _print_cmds(
        self,
    ) -> None:
        current_section = None
        for cmd in self.visible_cmds:
            section_title = cmd.section_title
            assert section_title is not None
            if section_title != current_section:
                self.console.print()
                self.console.print(f"[bold]{self._get_section_text(section_title)}[/bold]")
                current_section = section_title
            self._print_row(
                label=cmd.cmd_name,
                label_style=_manage_terminal.Colour.CYAN.value,
                description=cmd.cmd_help,
            )

    def _print_flags(
        self,
    ) -> None:
        self.console.print()
        self.console.print("[bold]Flags[/bold]")
        for flag in self.all_flags:
            flag_help = flag.argument_help
            if flag_help is None:
                flag_help = ""
            self._print_row(
                label=flag.argument_name,
                label_style=_manage_terminal.Colour.CYAN.value,
                description=flag_help,
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
        """Print the header, the commands by section, the flags, and the output legend."""
        self._print_header()
        self._print_cmds()
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
        argument_parser.add_argument(flag.argument_name, **flag.argparse_keyword_arguments)
    subparsers = argument_parser.add_subparsers(
        dest="cmd",
        required=False,
        metavar="<command>",
    )
    for cmd in command_line_tool.cmds:
        subparser = subparsers.add_parser(cmd.cmd_name, help=cmd.cmd_help)
        for cmd_argument in cmd.cmd_arguments:
            subparser.add_argument(
                cmd_argument.argument_name,
                **cmd_argument.argparse_keyword_arguments,
            )
    return argument_parser


def _ensure_visible_cmds_grouped(
    command_line_tool: CommandLineTool,
) -> None:
    for cmd in command_line_tool.cmds:
        if not cmd.is_hidden and cmd.section_title is None:
            raise ValueError(f"command `{cmd.cmd_name}` must be hidden or in a command group.")


def run_cli(
    *,
    command_line_tool: CommandLineTool,
    argv: Sequence[str] | None = None,
) -> None:
    """Parse argv (default: `sys.argv`), build the run params, start output for the run, and dispatch one subcmd."""
    _ensure_visible_cmds_grouped(command_line_tool)
    parsed_arguments = _build_parser(command_line_tool).parse_args(argv)
    if parsed_arguments.help or parsed_arguments.cmd is None:
        command_line_tool_help = _CommandLineToolHelp(command_line_tool)
        command_line_tool_help.print_help()
        return
    run_params = command_line_tool.make_run_params(parsed_arguments)
    _manage_terminal.set_output_params(
        show_timestamps=command_line_tool.show_timestamps,
        log_path=command_line_tool.log_path,
        dry_run=run_params.dry_run,
    )
    cmds_by_name = {_cmd.cmd_name: _cmd for _cmd in command_line_tool.cmds}
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
