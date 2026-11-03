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
from typing import final

## third-party
from rich.console import Console as rich_Console

## local
from huginn import _manage_output, _message_styles, cmd_args, manage_log, params

##
## === DATA STRUCTURES
## a tool holds groups of cmds, and each cmd holds its arguments, defined in `cmd_args`.
##

_RESERVED_PARAM_NAME = "tool_params"


@dataclass(frozen=True)
class Command:
    """One cmd of a tool, run as `<tool> <name> [arguments]`: its description, its arguments, and the function it calls."""
    name: str
    description: str
    fn: Callable[..., None]
    args: list[cmd_args.CommandArgument] = field(default_factory=list)

    def __post_init__(
        self,
    ) -> None:
        param_names = [_arg.param_name for _arg in self.args]
        if _RESERVED_PARAM_NAME in param_names:
            raise ValueError(
                f"{type(self).__name__}: argument parameter names for `{self.name}` must not be `{_RESERVED_PARAM_NAME}`, which every cmd function already receives; got `{_RESERVED_PARAM_NAME}`.",
            )
        repeated_param_names = sorted(
            {_param_name
             for _param_name in param_names
             if param_names.count(_param_name) > 1},
        )
        param_names_are_repeated = len(repeated_param_names) > 0
        if param_names_are_repeated:
            repeated_param_names_text = ", ".join(f"`{_param_name}`" for _param_name in repeated_param_names)
            raise ValueError(
                f"{type(self).__name__}: argument parameter names for `{self.name}` must be unique; got {repeated_param_names_text} more than once.",
            )

    def call(
        self,
        *,
        tool_params: params.ToolParams,
        parsed_args: argparse.Namespace,
    ) -> None:
        """Call `fn` with `tool_params` and each argument by its parameter name, all as keywords."""
        arg_values = {
            _arg.param_name: getattr(parsed_args, _arg.param_name)
            for _arg in self.args
        }
        self.fn(
            tool_params=tool_params,
            **arg_values,
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
        Flags beyond `--dry-run` and `--hide-actions`, which every tool has.

    - `hidden_cmds`:
        Cmds that can be run but are left out of help.

    - `tool_params_type`:
        `ToolParams` or a subclass with one field per extra flag; built from the parsed flags with
        `from_parsed_args`.
    """
    name: str
    description: str
    cmd_groups: list[CommandGroup]
    hidden_cmds: list[Command] = field(default_factory=list)
    flags: list[cmd_args.FlagArgument] = field(default_factory=list)
    tool_params_type: type[params.ToolParams] = params.ToolParams
    output_params: params.OutputParams = params.OutputParams()

    def __post_init__(
        self,
    ) -> None:
        flags_by_param_name = {_flag.param_name: _flag for _flag in self.all_flags}
        for cmd in self.all_cmds:
            clashing_param_names = sorted(
                {
                    _arg.param_name
                    for _arg in cmd.args
                    if _arg.param_name in flags_by_param_name
                },
            )
            param_names_are_clashing = len(clashing_param_names) > 0
            if param_names_are_clashing:
                clash_descriptions = ", ".join(
                    f"`{_param_name}`, which is also `--{flags_by_param_name[_param_name].long_arg_name}`"
                    for _param_name in clashing_param_names
                )
                raise ValueError(
                    f"{type(self).__name__}: argument parameter names for cmd `{cmd.name}` must differ from the flags of the tool; got {clash_descriptions}.",
                )

    @property
    def all_flags(
        self,
    ) -> list[cmd_args.FlagArgument]:
        return [*_BUILT_IN_FLAGS, *self.flags]

    @property
    def all_cmds(
        self,
    ) -> list[Command]:
        grouped_cmds = [_cmd for _cmd_group in self.cmd_groups for _cmd in _cmd_group.cmds]
        return [*grouped_cmds, *self.hidden_cmds]


_DRY_RUN_FLAG = cmd_args.FlagArgument(
    long_arg_name="dry-run",
    description="print commands without executing them",
)
_HIDE_ACTIONS_FLAG = cmd_args.FlagArgument(
    long_arg_name="hide-actions",
    description="do not print the commands run; the log still records them",
)
_BUILT_IN_FLAGS = (_DRY_RUN_FLAG, _HIDE_ACTIONS_FLAG)

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
        self.all_flags = command_line_tool.all_flags
        legend_labels = [
            self._get_legend_label(_message_style)
            for _message_group in _message_styles.MESSAGE_GROUPS
            for _message_style in _message_group.message_styles
        ]
        all_labels = [
            *[_cmd.name for _cmd_group in command_line_tool.cmd_groups for _cmd in _cmd_group.cmds],
            *[self._get_flag_label(_flag) for _flag in self.all_flags],
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
    def _get_flag_label(
        flag: cmd_args.FlagArgument,
    ) -> str:
        """The forms of a flag, e.g. `-o, --output`."""
        return ", ".join(flag.arg_names)

    @staticmethod
    def _get_legend_label(
        message_style: _message_styles.MessageStyle,
    ) -> str:
        """The symbol and colour name, e.g. `● green`; `plain` for a line with neither."""
        if (message_style.symbol is None) or (message_style.colour is None):
            return "plain"
        return f"{message_style.symbol} {message_style.colour.name.lower()}"

    def _print_row(
        self,
        *,
        label: str,
        label_style: str | None,
        description: str,
    ) -> None:
        padding = " " * (self.column_width - len(label))
        label_markup = _manage_output.escape_markup(label)
        if label_style is None:
            styled_label = label_markup
        else:
            styled_label = f"[{label_style}]{label_markup}[/]"
        description_markup = _manage_output.escape_markup(description)
        self.console.print(f"{_HELP_INDENT}{styled_label}{padding}{description_markup}")

    def _print_header(
        self,
    ) -> None:
        usage_flags = " ".join(f"[--{_flag.long_arg_name}]" for _flag in self.all_flags)
        usage_markup = _manage_output.escape_markup(
            f"{self.command_line_tool.name} {usage_flags} <command> [args]",
        )
        name_markup = _manage_output.escape_markup(self.command_line_tool.name)
        description_markup = _manage_output.escape_markup(self.command_line_tool.description)
        self.console.print()
        self.console.print(f"[bold]{name_markup}[/bold]: {description_markup}")
        self.console.print()
        self.console.print(f"[dim]usage:[/dim] {usage_markup}")

    def _print_cmd_groups(
        self,
    ) -> None:
        for cmd_group in self.command_line_tool.cmd_groups:
            self.console.print()
            title_markup = _manage_output.escape_markup(self._get_title_text(cmd_group.title))
            self.console.print(f"[bold]{title_markup}[/bold]")
            for cmd in cmd_group.cmds:
                self._print_row(
                    label=cmd.name,
                    label_style=_message_styles.Colour.CYAN,
                    description=cmd.description,
                )

    def _print_flags(
        self,
    ) -> None:
        self.console.print()
        self.console.print("[bold]Flags[/bold]")
        for flag in self.all_flags:
            self._print_row(
                label=self._get_flag_label(flag),
                label_style=_message_styles.Colour.CYAN,
                description=flag.description,
            )

    def _print_legend(
        self,
    ) -> None:
        self.console.print()
        self.console.print("[bold]Output legend[/bold]")
        for message_group in _message_styles.MESSAGE_GROUPS:
            self.console.print(f"{_MESSAGE_GROUP_INDENT}[dim]{message_group.title}[/dim]")
            for message_style in message_group.message_styles:
                legend_colour = None
                if message_style.colour is not None:
                    legend_colour = message_style.colour
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


def _build_arg_parser(
    command_line_tool: CommandLineTool,
) -> argparse.ArgumentParser:
    arg_parser = argparse.ArgumentParser(
        prog=command_line_tool.name,
        description=command_line_tool.description,
        add_help=False,
    )
    arg_parser.add_argument(
        "-h",
        "--help",
        action="store_true",
    )
    for flag in command_line_tool.all_flags:
        flag.add_to_arg_parser(arg_parser)
    cmd_arg_parsers = arg_parser.add_subparsers(
        dest="cmd",
        required=False,
        metavar="<command>",
    )
    for cmd in command_line_tool.all_cmds:
        cmd_arg_parser = cmd_arg_parsers.add_parser(cmd.name, help=cmd.description)
        for arg in cmd.args:
            arg.add_to_arg_parser(cmd_arg_parser)
    return arg_parser


def run_cli(
    *,
    command_line_tool: CommandLineTool,
    argv: Sequence[str] | None = None,
) -> None:
    """Parse argv (default: `sys.argv`), build the tool params, set up output for the run, and run one cmd."""
    parsed_args = _build_arg_parser(command_line_tool).parse_args(argv)
    if parsed_args.help or (parsed_args.cmd is None):
        command_line_tool_help = _CommandLineToolHelp(command_line_tool)
        command_line_tool_help.print_help()
        return
    tool_params = command_line_tool.tool_params_type.from_parsed_args(parsed_args)
    _manage_output.set_params(
        tool_params=tool_params,
        output_params=command_line_tool.output_params,
    )
    cmds_by_name = {_cmd.name: _cmd for _cmd in command_line_tool.all_cmds}
    selected_cmd = cmds_by_name[parsed_args.cmd]
    try:
        selected_cmd.call(
            tool_params=tool_params,
            parsed_args=parsed_args,
        )
    except subprocess.CalledProcessError as process_error:
        failed_cmd = shlex.join(process_error.cmd)
        manage_log.exit_with_error(
            f"`{failed_cmd}` failed with exit status {process_error.returncode}.",
            exit_code=process_error.returncode,
        )


## } MODULE
