## { MODULE

##
## === DEPENDENCIES
##

## stdlib
import argparse
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field, replace
from enum import Enum
from pathlib import Path
from typing import Any, TypeAlias

## third-party
import rich.markup
from rich.console import Console

## local
from heimdall import shell_interface

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
    def dest(self) -> str:
        """The `argparse.Namespace` attribute this arg lands on, e.g. `--word-diff` -> `word_diff`."""
        return self.arg_name.lstrip("-").replace("-", "_")

    @property
    def argparse_kwargs(self) -> dict[str, Any]:
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
    help: str
    cmd_fn: Callable[..., None]
    cmd_args: list[CommandArg]
    section_title: str | None
    is_hidden: bool

    def call(
        self,
        *,
        config: shell_interface.Config,
        parsed_args: argparse.Namespace,
    ) -> None:
        """Call cmd_fn with config first, then each cmd_arg value in order."""
        cmd_arg_values = [getattr(parsed_args, _cmd_arg.dest) for _cmd_arg in self.cmd_args]
        self.cmd_fn(config, *cmd_arg_values)


CommandEntry: TypeAlias = tuple[str, CommandDetails]


def _make_default_config(
    parsed_args: argparse.Namespace,
) -> shell_interface.Config:
    return shell_interface.Config(dry_run=parsed_args.dry_run)


@dataclass(frozen=True)
class ToolSpec:
    tool_name: str
    description: str
    commands: list[CommandEntry]
    global_flags: list[CommandArg] = field(default_factory=list)
    make_config: Callable[[argparse.Namespace], shell_interface.Config] = _make_default_config
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


def cli_command(
    *,
    cmd_name: str,
    cmd_fn: Callable[..., None],
    cmd_help: str = "",
    cmd_args: list[CommandArg] | None = None,
    is_hidden: bool = False,
) -> CommandEntry:
    """Build a (name, details) entry for the command table; command_group stamps its section."""
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


def _get_section_text(
    section_title: str,
) -> str:
    if isinstance(section_title, Enum):
        return str(section_title.value)
    return section_title


_HELP_INDENT = "    "
_HELP_GAP_WIDTH = 2


def _format_help_row(
    *,
    label: str,
    label_style: str,
    column_width: int,
    description: str,
) -> str:
    padding = " " * (column_width - len(label))
    return f"{_HELP_INDENT}[{label_style}]{label}[/]{padding}{description}"


def _get_legend_label(
    legend_entry: shell_interface.LegendEntry,
) -> str:
    return f"{legend_entry.marker} {legend_entry.color_name}"


def _print_tool_help(
    *,
    tool_spec: ToolSpec,
) -> None:
    """Every row on the screen shares one column width: the longest label plus a fixed gap."""
    console = Console(highlight=False)
    all_global_flags = [_DRY_RUN_FLAG, *tool_spec.global_flags]
    visible_rows: list[tuple[str, str, str]] = []
    for cmd_name, cmd_details in tool_spec.commands:
        if cmd_details.is_hidden or cmd_details.section_title is None:
            continue
        visible_row = (cmd_details.section_title, cmd_name, cmd_details.help)
        visible_rows.append(visible_row)
    legend_entries = shell_interface.get_legend()
    all_labels = [
        *[_cmd_name for _, _cmd_name, _ in visible_rows],
        *[_global_flag.arg_name for _global_flag in all_global_flags],
        *[_get_legend_label(_legend_entry) for _legend_entry in legend_entries],
    ]
    column_width = max(len(_label) for _label in all_labels) + _HELP_GAP_WIDTH
    usage_flags = " ".join(f"[{_global_flag.arg_name}]" for _global_flag in all_global_flags)
    usage_text = rich.markup.escape(f"{tool_spec.tool_name} {usage_flags} <command> [args]")
    console.print()
    console.print(f"[bold]{tool_spec.tool_name}[/bold]: {tool_spec.description}")
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
    console.print("[bold]Global flags[/bold]")
    for global_flag in all_global_flags:
        flag_help = global_flag.help
        if flag_help is None:
            flag_help = ""
        flag_row = _format_help_row(
            label=global_flag.arg_name,
            label_style="cyan",
            column_width=column_width,
            description=flag_help,
        )
        console.print(flag_row)
    console.print()
    console.print("[bold]Output legend[/bold]")
    for legend_entry in legend_entries:
        legend_row = _format_help_row(
            label=_get_legend_label(legend_entry),
            label_style=legend_entry.color_hex,
            column_width=column_width,
            description=legend_entry.meaning,
        )
        console.print(legend_row)
    console.print()


def _make_help_action(
    *,
    tool_spec: ToolSpec,
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
            _print_tool_help(tool_spec=tool_spec)
            parser.exit()
    return _GroupedHelpAction


##
## === ENTRY POINT
##


def run_cli(
    *,
    tool_spec: ToolSpec,
    argv: Sequence[str] | None = None,
) -> None:
    """Parse argv (default: sys.argv), build the config, set up output, and dispatch one subcommand."""
    arg_parser = argparse.ArgumentParser(
        prog=tool_spec.tool_name,
        description=tool_spec.description,
        add_help=False,
    )
    arg_parser.add_argument(
        "-h",
        "--help",
        action=_make_help_action(tool_spec=tool_spec),
        default=argparse.SUPPRESS,
    )
    for global_flag in [_DRY_RUN_FLAG, *tool_spec.global_flags]:
        arg_parser.add_argument(global_flag.arg_name, **global_flag.argparse_kwargs)
    sub_parsers = arg_parser.add_subparsers(
        dest="cmd",
        required=True,
        metavar="<command>",
    )
    commands_by_name = dict(tool_spec.commands)
    for cmd_name, cmd_details in commands_by_name.items():
        subparser = sub_parsers.add_parser(cmd_name, help=cmd_details.help)
        for cmd_arg in cmd_details.cmd_args:
            subparser.add_argument(cmd_arg.arg_name, **cmd_arg.argparse_kwargs)
    parsed_args = arg_parser.parse_args(argv)
    config = tool_spec.make_config(parsed_args)
    shell_interface.configure_output(
        tool_name=tool_spec.tool_name,
        show_timestamps=tool_spec.show_timestamps,
        record_path=tool_spec.record_path,
        dry_run=config.dry_run,
    )
    selected_cmd_details = commands_by_name[parsed_args.cmd]
    try:
        selected_cmd_details.call(
            config=config,
            parsed_args=parsed_args,
        )
    except subprocess.CalledProcessError as proc_error:
        sys.exit(proc_error.returncode)


## } MODULE
