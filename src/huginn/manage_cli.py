## { MODULE

##
## === DEPENDENCIES
##

## stdlib
import argparse
import shlex
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import final

## third-party
from rich.console import Console as rich_Console

## local
from huginn import (
    _manage_output,
    _message_styles,
    cmd_args,
    manage_log,
)

##
## === BUILT-IN FLAGS
##

_DRY_RUN_FLAG = cmd_args.FlagArgument(
    long_arg_name="dry-run",
    description="show each change without running it",
)
_HIDE_ACTIONS_FLAG = cmd_args.FlagArgument(
    long_arg_name="hide-actions",
    description="leave actions off the terminal; the log still records them",
)
_BUILT_IN_FLAGS = (_DRY_RUN_FLAG, _HIDE_ACTIONS_FLAG)

##
## === DATA STRUCTURES
## a tool holds groups of cmds, and each cmd holds its arguments, defined in `cmd_args`.
##


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
        repeated_param_names = {
            _param_name
            for _param_name in param_names
            if param_names.count(_param_name) > 1
        }
        param_names_are_repeated = len(repeated_param_names) > 0
        if param_names_are_repeated:
            repeated_param_names_text = ", ".join(
                f"`{_param_name}`" for _param_name in sorted(repeated_param_names)
            )
            raise ValueError(
                f"{type(self).__name__}: argument parameter names for `{self.name}` must be unique; got {repeated_param_names_text} more than once.",
            )

    def call(
        self,
        *,
        parsed_args: argparse.Namespace,
    ) -> None:
        """Call `fn` with each argument by its parameter name, as keywords."""
        ## the subset of vars(parsed_args) that belongs to this cmd: only the args `fn` takes.
        arg_values_by_param_name = {
            _arg.param_name: getattr(parsed_args, _arg.param_name)
            for _arg in self.args
        }
        self.fn(**arg_values_by_param_name)


@dataclass(frozen=True)
class CommandGroup:
    """Cmds listed together in help under one title."""
    title: str
    cmds: list[Command]


@dataclass(frozen=True)
class CommandLineTool:
    """
    One command line tool: what it is, the cmds it offers, and how one run of it is set up.

    Every tool has the same two flags, `--dry-run` and `--hide-actions`, handled by huginn; anything a cmd needs on
    top is an argument of that cmd.
    """
    name: str
    description: str
    cmd_groups: list[CommandGroup]

    def __post_init__(
        self,
    ) -> None:
        built_in_flags_by_param_name = {
            _built_in_flag.param_name: _built_in_flag
            for _built_in_flag in _BUILT_IN_FLAGS
        }
        for cmd in self.all_cmds:
            ## the args of this cmd that take a param name a built-in flag already has
            reused_param_names = [
                _cmd_arg.param_name
                for _cmd_arg in cmd.args
                if _cmd_arg.param_name in built_in_flags_by_param_name
            ]
            param_names_are_reused = len(reused_param_names) > 0
            if param_names_are_reused:
                ## pair each reused param name with the built-in flag that has it, e.g. `dry_run` with `--dry-run`
                reused_param_names_text = ", ".join(
                    f"`{_param_name}`, which is also `--{built_in_flags_by_param_name[_param_name].long_arg_name}`"
                    for _param_name in sorted(reused_param_names)
                )
                raise ValueError(
                    f"{type(self).__name__}: argument parameter names for cmd `{cmd.name}` must differ from the built-in flags; got {reused_param_names_text}.",
                )

    @property
    def all_cmds(
        self,
    ) -> list[Command]:
        return [_cmd for _cmd_group in self.cmd_groups for _cmd in _cmd_group.cmds]


##
## === HELP
##


@final
class _CommandLineToolHelp:
    """
    The help screen of one tool, laid out as a table.

    Each row is a label and a description, and every row shares one label column width, so the descriptions line up.
    Each row prints as one line.
    """

    def __init__(
        self,
        command_line_tool: CommandLineTool,
        *,
        num_indent_spaces: int = 4,
        col_separation: int = 2,
    ) -> None:
        self.command_line_tool = command_line_tool
        self.num_indent_spaces = num_indent_spaces
        self.console = rich_Console(highlight=False)
        self.console.soft_wrap = not self.console.is_terminal
        message_group_title_widths = [
            len(_message_group.title) for _message_group in _message_styles.MESSAGE_GROUPS
        ]
        self.message_group_col_width = max(message_group_title_widths) + col_separation
        style_label_widths = [
            self.message_group_col_width + len(self._get_style_label(_message_style))
            for _message_group in _message_styles.MESSAGE_GROUPS
            for _message_style in _message_group.message_styles
        ]
        all_label_widths = [
            *[len(_cmd.name) for _cmd in command_line_tool.all_cmds],
            *[len(self._get_flag_label(_built_in_flag)) for _built_in_flag in _BUILT_IN_FLAGS],
            *style_label_widths,
        ]
        self.col_width = max(all_label_widths) + col_separation

    @staticmethod
    def _get_spaces(
        num_spaces: int,
    ) -> str:
        return " " * num_spaces

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
    def _get_style_label(
        message_style: _message_styles.MessageStyle,
    ) -> str:
        """What a line in this style starts with in the output: the symbol, then the label and its colon if it has one, e.g. `↪ success:`; empty for a return, which has neither."""
        if message_style.symbol is None:
            style_label = ""
        elif message_style.label is None:
            style_label = message_style.symbol
        else:
            style_label = f"{message_style.symbol} {message_style.label}:"
        return style_label

    def _print_line(
        self,
        *,
        label: str,
        label_style: str | None,
        description: str,
        label_prefix: str = "",
        description_style: str | None = None,
    ) -> None:
        """
        Print one row of the table as a line.

        `label_prefix` prints plain in front of the styled `label`, inside the same column.
        """
        indent = self._get_spaces(self.num_indent_spaces)
        label_width = len(label_prefix) + len(label)
        description_padding = self._get_spaces(self.col_width - label_width)
        label_prefix_rendered = _manage_output.escape_markup(label_prefix)
        label_markup = _manage_output.escape_markup(label)
        if label_style is None:
            label_rendered = label_markup
        else:
            label_rendered = f"[{label_style}]{label_markup}[/]"
        description_markup = _manage_output.escape_markup(description)
        if description_style is None:
            description_rendered = description_markup
        else:
            description_rendered = f"[{description_style}]{description_markup}[/]"
        line_rendered = f"{indent}{label_prefix_rendered}{label_rendered}{description_padding}{description_rendered}"
        self.console.print(line_rendered)

    def _print_tool_usage(
        self,
    ) -> None:
        tool_name_markup = _manage_output.escape_markup(self.command_line_tool.name)
        tool_description_markup = _manage_output.escape_markup(self.command_line_tool.description)
        built_in_flags_text = " ".join(
            f"[--{_built_in_flag.long_arg_name}]" for _built_in_flag in _BUILT_IN_FLAGS
        )
        tool_usage_markup = _manage_output.escape_markup(
            f"{self.command_line_tool.name} {built_in_flags_text} <command> [args]",
        )
        self.console.print(f"[bold]{tool_name_markup}[/bold]: {tool_description_markup}")
        self.console.print()
        self.console.print(f"[dim]usage:[/dim] {tool_usage_markup}")
        for cmd_group in self.command_line_tool.cmd_groups:
            self.console.print()
            cmd_group_title_text = self._get_title_text(cmd_group.title)
            cmd_group_title_markup = _manage_output.escape_markup(cmd_group_title_text)
            self.console.print(f"[bold]{cmd_group_title_markup}[/bold]")
            for cmd in cmd_group.cmds:
                self._print_line(
                    label=cmd.name,
                    label_style=_message_styles.Colour.CYAN,
                    description=cmd.description,
                )

    def _print_built_in_flags(
        self,
    ) -> None:
        self.console.print()
        self.console.print("[bold]Built-in flags[/bold]")
        for built_in_flag in _BUILT_IN_FLAGS:
            self._print_line(
                label=self._get_flag_label(built_in_flag),
                label_style=_message_styles.Colour.CYAN,
                description=built_in_flag.description,
            )

    def _print_style_legend(
        self,
    ) -> None:
        self.console.print()
        self.console.print("[bold]Style legend[/bold]")
        for message_group in _message_styles.MESSAGE_GROUPS:
            for style_index, message_style in enumerate(message_group.message_styles):
                is_first_style_in_group = style_index == 0
                if is_first_style_in_group:
                    message_group_name = message_group.title
                else:
                    message_group_name = ""
                label_padding = self._get_spaces(
                    self.message_group_col_width - len(message_group_name),
                )
                group_name_prefix = f"{message_group_name}{label_padding}"
                self._print_line(
                    label=self._get_style_label(message_style),
                    label_style=message_style.colour,
                    description=message_style.description,
                    label_prefix=group_name_prefix,
                    description_style=message_style.colour,
                )

    def print_help(
        self,
    ) -> None:
        """Print how to use the tool, the built-in flags, and the style legend."""
        self._print_tool_usage()
        self._print_built_in_flags()
        self._print_style_legend()


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
    for built_in_flag in _BUILT_IN_FLAGS:
        built_in_flag.add_to_arg_parser(arg_parser)
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


def get_built_in_params() -> _manage_output.BuiltInParams:
    """
    The built-in flags as passed for this run, e.g. `dry_run`.

    huginn acts on them itself, e.g. a run is skipped in dry-run; a tool reads them for what huginn cannot see, such
    as a file the tool writes in Python.
    """
    return _manage_output.get_active_built_in_params()


def run_cli(
    *,
    command_line_tool: CommandLineTool,
    argv: Sequence[str] | None = None,
) -> None:
    """Parse argv (default: `sys.argv`), build the built-in params, set up output for the run, and run one cmd."""
    if argv is None:
        argv = sys.argv[1:]
    parsed_args = _build_arg_parser(command_line_tool).parse_args(argv)
    if parsed_args.help:
        command_line_tool_help = _CommandLineToolHelp(command_line_tool)
        command_line_tool_help.print_help()
        return
    elif parsed_args.cmd is None:
        ## a run with no cmd is a usage mistake, so it exits with the status argparse uses for a usage error
        manage_log.exit_with_error(
            f"no command given; run `{command_line_tool.name} --help` to see the commands",
            exit_code=2,
        )
    built_in_params = _manage_output.BuiltInParams.from_parsed_args(parsed_args)
    _manage_output.set_built_in_params(built_in_params)
    cmds_by_name = {_cmd.name: _cmd for _cmd in command_line_tool.all_cmds}
    selected_cmd = cmds_by_name[parsed_args.cmd]
    try:
        ## huginn marks a dry run at both ends, so no tool has to phrase its outcomes for one
        if built_in_params.dry_run:
            manage_log.log_note("dry run: changes are shown, not made")
        selected_cmd.call(parsed_args=parsed_args)
        if built_in_params.dry_run:
            manage_log.log_outcome(
                "dry run; nothing was changed",
                status=manage_log.OutcomeStatus.SKIPPED,
                items={"skipped actions": _manage_output.get_num_skipped_actions()},
            )
    except subprocess.CalledProcessError as process_error:
        failed_cmd = shlex.join(process_error.cmd)
        manage_log.exit_with_error(
            f"`{failed_cmd}` failed with exit status {process_error.returncode}.",
            exit_code=process_error.returncode,
        )
    except _manage_output.LogFileError as log_file_error:
        _manage_output.set_log_file_path(log_file_path=None)
        manage_log.exit_with_error(str(log_file_error))


## } MODULE
