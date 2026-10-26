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
from typing import Any, TypeAlias, final

## third-party
from rich.console import Console as rich_Console

## local
from heimdall import _terminal_output, shell_interface

##
## === DATA STRUCTURES
##


@dataclass(frozen=True)
class CommandArg:
    """One argparse argument for a subcommand: a bare positional, or a `--flag`."""
    arg_name: str
    value_type: type = str
    default: Any = None
    metavar: str | None = None
    help: str | None = None
    store_true: bool = False
    required: bool = False
    nargs: str | None = None

    @property
    def dest(
        self,
    ) -> str:
        """The `argparse.Namespace` attribute this arg lands on, e.g. `--word-diff` -> `word_diff`."""
        return self.arg_name.lstrip("-").replace("-", "_")

    @property
    def argparse_kwargs(
        self,
    ) -> dict[str, Any]:
        """Build the kwargs for `add_argument`; flags with no explicit help get a default-value hint."""
        if self.store_true:
            kwargs: dict[str, Any] = {
                "action": "store_true",
                "default": False,
            }
        else:
            kwargs = {"type": self.value_type}
            if self.nargs is not None:
                kwargs["nargs"] = self.nargs
            if self.metavar is not None:
                kwargs["metavar"] = self.metavar
            if self.required:
                kwargs["required"] = True
            else:
                kwargs["default"] = self.default
        if self.help is not None:
            kwargs["help"] = self.help
        elif self.arg_name.startswith("--") and not self.required:
            kwargs["help"] = "(default: %(default)s)"
        return kwargs


@dataclass(frozen=True)
class CommandDetails:
    """One subcommand: its help, its arguments, and the function it calls."""
    help: str
    command_fn: Callable[..., None]
    command_args: list[CommandArg]
    section_title: str | None
    is_hidden: bool

    def call(
        self,
        *,
        run_params: shell_interface.RunParams,
        parsed_args: argparse.Namespace,
    ) -> None:
        """Call command_fn with `run_params` and each argument by its argparse name, all as keywords."""
        command_arg_values = {_command_arg.dest: getattr(parsed_args, _command_arg.dest) for _command_arg in self.command_args}
        self.command_fn(
            run_params=run_params,
            **command_arg_values,
        )


##
## === TYPE ALIASES
##

CommandEntry: TypeAlias = tuple[str, CommandDetails]

##
## === TOOL
##


def _make_default_run_params(
    parsed_args: argparse.Namespace,
) -> shell_interface.RunParams:
    return shell_interface.RunParams(dry_run=parsed_args.dry_run)


@dataclass(frozen=True)
class Tool:
    """
    One command line tool: its name, its commands, its flags, and how its output behaves.

    Fields
    ---
    - `flags`:
        Flags beyond `--dry-run`, which every tool has.

    - `make_run_params`:
        Builds the `RunParams` of the tool (or a subclass) from the parsed flags.

    - `record_path`:
        Where every printed line is also appended as plain text; `None` writes no record.
    """
    name: str
    description: str
    commands: list[CommandEntry]
    flags: list[CommandArg] = field(default_factory=list)
    make_run_params: Callable[[argparse.Namespace], shell_interface.RunParams] = _make_default_run_params
    show_timestamps: bool = False
    record_path: Path | None = None


_DRY_RUN_FLAG = CommandArg(
    arg_name="--dry-run",
    store_true=True,
    help="print commands without executing them",
)

##
## === COMMAND TABLE
##


def make_command(
    *,
    command_name: str,
    command_fn: Callable[..., None],
    command_help: str = "",
    command_args: list[CommandArg] | None = None,
    is_hidden: bool = False,
) -> CommandEntry:
    """Build a (name, details) entry for the command table; `make_command_group` stamps its section."""
    if command_args is None:
        command_args = []
    command_details = CommandDetails(
        help=command_help,
        command_fn=command_fn,
        command_args=command_args,
        section_title=None,
        is_hidden=is_hidden,
    )
    return (command_name, command_details)


def make_command_group(
    *,
    section_title: str,
    commands: list[CommandEntry],
) -> list[CommandEntry]:
    """Stamp `section_title` onto each command so a group names its section exactly once."""
    return [
        (_command_name, replace(_command_details, section_title=section_title))
        for _command_name, _command_details in commands
    ]


##
## === HELP
##

_HELP_INDENT = "    "
_MESSAGE_GROUP_INDENT = "  "
_HELP_GAP_WIDTH = 2


@final
class _ToolHelp:
    """The help screen of one tool; every row shares one column width."""

    def __init__(
        self,
        tool: Tool,
    ) -> None:
        self.tool = tool
        self.console = rich_Console(highlight=False)
        self.all_flags = [_DRY_RUN_FLAG, *tool.flags]
        self.visible_commands = [
            (_command_name, _command_details)
            for _command_name, _command_details in tool.commands
            if not _command_details.is_hidden
        ]
        legend_labels = [
            self._get_legend_label(_message_style)
            for _message_group in _terminal_output.MESSAGE_GROUPS
            for _message_style in _message_group.grouped_message_styles
        ]
        all_labels = [
            *[_command_name for _command_name, _ in self.visible_commands],
            *[_flag.arg_name for _flag in self.all_flags],
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
        message_style: _terminal_output.MessageStyle,
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
        usage_flags = " ".join(f"[{_flag.arg_name}]" for _flag in self.all_flags)
        usage_text = shell_interface.escape_markup(f"{self.tool.name} {usage_flags} <command> [args]")
        self.console.print()
        self.console.print(f"[bold]{self.tool.name}[/bold]: {self.tool.description}")
        self.console.print()
        self.console.print(f"[dim]usage:[/dim] {usage_text}")

    def _print_commands(
        self,
    ) -> None:
        current_section = None
        for command_name, command_details in self.visible_commands:
            section_title = command_details.section_title
            assert section_title is not None
            if section_title != current_section:
                self.console.print()
                self.console.print(f"[bold]{self._get_section_text(section_title)}[/bold]")
                current_section = section_title
            self._print_row(
                label=command_name,
                label_style=_terminal_output.Colour.CYAN.value,
                description=command_details.help,
            )

    def _print_flags(
        self,
    ) -> None:
        self.console.print()
        self.console.print("[bold]Flags[/bold]")
        for flag in self.all_flags:
            flag_help = flag.help
            if flag_help is None:
                flag_help = ""
            self._print_row(
                label=flag.arg_name,
                label_style=_terminal_output.Colour.CYAN.value,
                description=flag_help,
            )

    def _print_legend(
        self,
    ) -> None:
        self.console.print()
        self.console.print("[bold]Output legend[/bold]")
        for message_group in _terminal_output.MESSAGE_GROUPS:
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
        self._print_commands()
        self._print_flags()
        self._print_legend()


##
## === ENTRY POINT
##


def _build_parser(
    tool: Tool,
) -> argparse.ArgumentParser:
    arg_parser = argparse.ArgumentParser(
        prog=tool.name,
        description=tool.description,
        add_help=False,
    )
    arg_parser.add_argument(
        "-h",
        "--help",
        action="store_true",
    )
    for flag in [_DRY_RUN_FLAG, *tool.flags]:
        arg_parser.add_argument(flag.arg_name, **flag.argparse_kwargs)
    subparsers = arg_parser.add_subparsers(
        dest="command",
        required=False,
        metavar="<command>",
    )
    for command_name, command_details in dict(tool.commands).items():
        subparser = subparsers.add_parser(command_name, help=command_details.help)
        for command_arg in command_details.command_args:
            subparser.add_argument(command_arg.arg_name, **command_arg.argparse_kwargs)
    return arg_parser


def _ensure_visible_commands_grouped(
    tool: Tool,
) -> None:
    for command_name, command_details in tool.commands:
        if not command_details.is_hidden and command_details.section_title is None:
            raise ValueError(f"command `{command_name}` must be hidden or in a command group.")


def run_cli(
    *,
    tool: Tool,
    argv: Sequence[str] | None = None,
) -> None:
    """Parse argv (default: `sys.argv`), build the run params, start output for the run, and dispatch one subcommand."""
    _ensure_visible_commands_grouped(tool)
    parsed_args = _build_parser(tool).parse_args(argv)
    if parsed_args.help or parsed_args.command is None:
        tool_help = _ToolHelp(tool)
        tool_help.print_help()
        return
    run_params = tool.make_run_params(parsed_args)
    _terminal_output.set_output_params(
        show_timestamps=tool.show_timestamps,
        record_path=tool.record_path,
        dry_run=run_params.dry_run,
    )
    selected_command_details = dict(tool.commands)[parsed_args.command]
    try:
        selected_command_details.call(
            run_params=run_params,
            parsed_args=parsed_args,
        )
    except subprocess.CalledProcessError as process_error:
        failed_command = shlex.join(process_error.cmd)
        shell_interface.exit_with_error(
            shell_interface.escape_markup(f"`{failed_command}` failed with exit status {process_error.returncode}."),
            exit_code=process_error.returncode,
        )


## } MODULE
