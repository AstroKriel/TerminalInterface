## { MODULE

##
## === DEPENDENCIES
##

## stdlib
import argparse
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field, replace
from enum import Enum
from pathlib import Path
from typing import Any, TypeAlias

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
            kwargs: dict[str, Any] = {"action": "store_true", "default": False}
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
    cmd_fn: Callable[..., None]
    cmd_args: list[CommandArg]
    section_title: str | None
    is_hidden: bool

    def call(
        self,
        *,
        run_params: shell_interface.RunParams,
        parsed_args: argparse.Namespace,
    ) -> None:
        """Call cmd_fn with `run_params` and each argument by its argparse name, all as keywords."""
        cmd_arg_values = {_cmd_arg.dest: getattr(parsed_args, _cmd_arg.dest) for _cmd_arg in self.cmd_args}
        self.cmd_fn(
            run_params=run_params,
            **cmd_arg_values,
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
    narration_stream: _terminal_output.OutputStream = _terminal_output.OutputStream.STDERR


_DRY_RUN_FLAG = CommandArg(
    arg_name="--dry-run",
    store_true=True,
    help="print commands without executing them",
)

##
## === COMMAND TABLE
##


def cli_command(
    *,
    cmd_name: str,
    cmd_fn: Callable[..., None],
    cmd_help: str = "",
    cmd_args: list[CommandArg] | None = None,
    is_hidden: bool = False,
) -> CommandEntry:
    """Build a (name, details) entry for the command table; `command_group` stamps its section."""
    if cmd_args is None:
        cmd_args = []
    cmd_details = CommandDetails(
        help=cmd_help,
        cmd_fn=cmd_fn,
        cmd_args=cmd_args,
        section_title=None,
        is_hidden=is_hidden,
    )
    return (cmd_name, cmd_details)


def command_group(
    *,
    section_title: str,
    commands: list[CommandEntry],
) -> list[CommandEntry]:
    """Stamp section_title onto each command so a group names its section exactly once."""
    return [
        (_cmd_name, replace(_cmd_details, section_title=section_title))
        for _cmd_name, _cmd_details in commands
    ]


##
## === HELP
##

_HELP_INDENT = "    "
_LEGEND_GROUP_INDENT = "  "
_HELP_GAP_WIDTH = 2


def _get_section_text(
    section_title: str,
) -> str:
    if isinstance(section_title, Enum):
        return str(section_title.value)
    return section_title


def _format_help_row(
    *,
    label: str,
    label_style: str,
    column_width: int,
    description: str,
) -> str:
    padding = " " * (column_width - len(label))
    return f"{_HELP_INDENT}[{label_style}]{label}[/]{padding}{description}"


def _get_legend_params() -> list[_terminal_output.MessageParams]:
    """Every message params in the legend, across all groups, in legend order."""
    return [
        _message_params
        for _legend_group in _terminal_output.LEGEND_GROUPS
        for _message_params in _legend_group.grouped_message_params
    ]


def _get_legend_label(
    message_params: _terminal_output.MessageParams,
) -> str:
    return f"{message_params.marker.value} {message_params.color.name.lower()}"


def _print_tool_help(
    tool: Tool,
) -> None:
    """Every row on the screen shares one column width: the longest label plus a fixed gap."""
    console = rich_Console(highlight=False)
    all_flags = [_DRY_RUN_FLAG, *tool.flags]
    visible_rows: list[tuple[str, str, str]] = []
    for cmd_name, cmd_details in tool.commands:
        if cmd_details.is_hidden or cmd_details.section_title is None:
            continue
        visible_row = (cmd_details.section_title, cmd_name, cmd_details.help)
        visible_rows.append(visible_row)
    all_labels = [
        *[_cmd_name for _, _cmd_name, _ in visible_rows],
        *[_flag.arg_name for _flag in all_flags],
        *[_get_legend_label(_message_params) for _message_params in _get_legend_params()],
    ]
    column_width = max(len(_label) for _label in all_labels) + _HELP_GAP_WIDTH
    usage_flags = " ".join(f"[{_flag.arg_name}]" for _flag in all_flags)
    usage_text = shell_interface.escape_markup(f"{tool.name} {usage_flags} <command> [args]")
    console.print()
    console.print(f"[bold]{tool.name}[/bold]: {tool.description}")
    console.print()
    console.print(f"[dim]usage:[/dim] {usage_text}")
    current_section = None
    for section_title, cmd_name, cmd_help in visible_rows:
        if section_title != current_section:
            console.print()
            console.print(f"[bold]{_get_section_text(section_title)}[/bold]")
            current_section = section_title
        command_row = _format_help_row(
            label=cmd_name,
            label_style="cyan",
            column_width=column_width,
            description=cmd_help,
        )
        console.print(command_row)
    console.print()
    console.print("[bold]Flags[/bold]")
    for flag in all_flags:
        flag_help = flag.help
        if flag_help is None:
            flag_help = ""
        flag_row = _format_help_row(
            label=flag.arg_name,
            label_style="cyan",
            column_width=column_width,
            description=flag_help,
        )
        console.print(flag_row)
    console.print()
    console.print("[bold]Output legend[/bold]")
    for legend_group in _terminal_output.LEGEND_GROUPS:
        console.print(f"{_LEGEND_GROUP_INDENT}[dim]{legend_group.title}[/dim]")
        for message_params in legend_group.grouped_message_params:
            legend_row = _format_help_row(
                label=_get_legend_label(message_params),
                label_style=message_params.color.value,
                column_width=column_width,
                description=message_params.description,
            )
            console.print(legend_row)
    console.print()


def _make_help_action(
    tool: Tool,
) -> type[argparse.Action]:

    class _GroupedHelpAction(argparse.Action):
        """Replace the default --help with a section-grouped command listing."""

        def __init__(
            self,
            option_strings: list[str],
            dest: str = argparse.SUPPRESS,
            default: str = argparse.SUPPRESS,
            help: str = "show this help message and exit",
        ) -> None:
            super().__init__(
                option_strings=option_strings,
                dest=dest,
                default=default,
                nargs=0,
                help=help,
            )

        def __call__(
            self,
            parser: argparse.ArgumentParser,
            namespace: argparse.Namespace,
            values: str | Sequence[str] | None,
            option_string: str | None = None,
        ) -> None:
            _print_tool_help(tool)
            parser.exit()

    return _GroupedHelpAction


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
        action=_make_help_action(tool),
        default=argparse.SUPPRESS,
    )
    for flag in [_DRY_RUN_FLAG, *tool.flags]:
        arg_parser.add_argument(flag.arg_name, **flag.argparse_kwargs)
    sub_parsers = arg_parser.add_subparsers(
        dest="cmd",
        required=True,
        metavar="<command>",
    )
    for cmd_name, cmd_details in dict(tool.commands).items():
        subparser = sub_parsers.add_parser(cmd_name, help=cmd_details.help)
        for cmd_arg in cmd_details.cmd_args:
            subparser.add_argument(cmd_arg.arg_name, **cmd_arg.argparse_kwargs)
    return arg_parser


def run_cli(
    *,
    tool: Tool,
    argv: Sequence[str] | None = None,
) -> None:
    """Parse argv (default: `sys.argv`), build the run params, start output for the run, and dispatch one subcommand."""
    parsed_args = _build_parser(tool).parse_args(argv)
    run_params = tool.make_run_params(parsed_args)
    _terminal_output.set_output_params(
        tool_name=tool.name,
        show_timestamps=tool.show_timestamps,
        record_path=tool.record_path,
        narration_stream=tool.narration_stream,
        dry_run=run_params.dry_run,
    )
    selected_cmd_details = dict(tool.commands)[parsed_args.cmd]
    try:
        selected_cmd_details.call(
            run_params=run_params,
            parsed_args=parsed_args,
        )
    except subprocess.CalledProcessError as proc_error:
        raise SystemExit(proc_error.returncode) from proc_error


## } MODULE
