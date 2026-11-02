## { MODULE

##
## === DEPENDENCIES
##

## stdlib
import argparse
import re
import shlex
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, final

## third-party
from rich.console import Console as rich_Console

## local
from huginn import _manage_terminal, input_types, manage_log, params

##
## === DATA STRUCTURES
## a tool holds groups of cmds, and each cmd holds its arguments.
##


class AllowedInputCount(Enum):
    """How many inputs an argument that takes input allows."""
    ONE = auto()
    ZERO_OR_ONE = auto()
    ZERO_OR_MORE = auto()
    ONE_OR_MORE = auto()


_NARGS_SYMBOLS = {
    AllowedInputCount.ZERO_OR_ONE: "?",
    AllowedInputCount.ZERO_OR_MORE: "*",
    AllowedInputCount.ONE_OR_MORE: "+",
}

_PARAM_NAME_PATTERN = re.compile(r"[a-z][a-z0-9_]*")
_LONG_ARG_NAME_PATTERN = re.compile(r"[a-z][a-z0-9-]*")
_SHORT_ARG_NAME_PATTERN = re.compile(r"[A-Za-z]{1,3}")
_INPUT_COUNTS_WITH_NO_INPUT = (AllowedInputCount.ZERO_OR_ONE, AllowedInputCount.ZERO_OR_MORE)


@dataclass(
    frozen=True,
    kw_only=True,
)
class Argument:
    """
    One argument of a cmd or a tool; never made directly.

    Every argument checks itself when made: each class adds its own checks to `__post_init__` and calls
    `super().__post_init__()` first, so every layer of an argument runs its checks once.
    """
    description: str

    def __post_init__(
        self,
    ) -> None:
        return None

    @property
    def param_name(
        self,
    ) -> str:
        """The cmd function parameter this argument is passed to."""
        raise NotImplementedError

    def add_to_parser(
        self,
        parser: argparse.ArgumentParser,
    ) -> None:
        """Register this argument with an argparse parser."""
        raise NotImplementedError


@dataclass(
    frozen=True,
    kw_only=True,
)
class _ArgumentWithInput(Argument):
    """What an argument that takes input adds: what kind of input, how many, and what to fall back to."""
    input_type: input_types.InputType
    allowed_input_count: AllowedInputCount = AllowedInputCount.ONE
    default_value: Any = None

    def _get_input_keyword_arguments(
        self,
    ) -> dict[str, Any]:
        """The `add_argument` keyword arguments for the input: its conversion, placeholder, count, and help."""
        keyword_arguments: dict[str, Any] = {
            "type": self.input_type.convert_fn,
            "metavar": f"<{self.input_type.placeholder_name}>",
            "help": self.description,
        }
        if self.allowed_input_count in _NARGS_SYMBOLS:
            keyword_arguments["nargs"] = _NARGS_SYMBOLS[self.allowed_input_count]
        return keyword_arguments


@dataclass(
    frozen=True,
    kw_only=True,
)
class _ArgumentWithNames(Argument):
    """What an argument the user types by name adds: its long and short arg names; huginn adds the dashes."""
    long_arg_name: str
    short_arg_name: str | None = None

    def __post_init__(
        self,
    ) -> None:
        super().__post_init__()
        argument_label = f"{type(self).__name__} `{self.long_arg_name}`"
        if _LONG_ARG_NAME_PATTERN.fullmatch(self.long_arg_name) is None:
            raise ValueError(
                f"{argument_label}: `long_arg_name` must be lowercase letters, digits, and `-`, starting with a letter; got `{self.long_arg_name}`.",
            )
        if self.short_arg_name is not None and _SHORT_ARG_NAME_PATTERN.fullmatch(self.short_arg_name) is None:
            raise ValueError(
                f"{argument_label}: `short_arg_name` must be one to three letters; got `{self.short_arg_name}`.",
            )

    @property
    def param_name(
        self,
    ) -> str:
        """The long arg name with `-` as `_`, e.g. `dry-run` -> `dry_run`."""
        return self.long_arg_name.replace("-", "_")

    @property
    def arg_names(
        self,
    ) -> list[str]:
        """Every way the user can type it, short first, e.g. `["-o", "--output"]`."""
        long_arg = f"--{self.long_arg_name}"
        if self.short_arg_name is None:
            return [long_arg]
        return [f"-{self.short_arg_name}", long_arg]


@dataclass(
    frozen=True,
    kw_only=True,
)
class PositionalArgument(_ArgumentWithInput):
    """An input typed straight after the cmd name; `name` is only the parameter name, never typed."""
    name: str

    def __post_init__(
        self,
    ) -> None:
        super().__post_init__()
        argument_label = f"{type(self).__name__} `{self.name}`"
        if _PARAM_NAME_PATTERN.fullmatch(self.name) is None:
            raise ValueError(
                f"{argument_label}: `name` must be lowercase letters, digits, and `_`, starting with a letter; got `{self.name}`.",
            )
        if self.default_value is not None and self.allowed_input_count not in _INPUT_COUNTS_WITH_NO_INPUT:
            raise ValueError(
                f"{argument_label}: `default_value` must be `None` when `allowed_input_count` is `{self.allowed_input_count.name}`, since the input is always given; got `{self.default_value}`.",
            )

    @property
    def param_name(
        self,
    ) -> str:
        return self.name

    def add_to_parser(
        self,
        parser: argparse.ArgumentParser,
    ) -> None:
        keyword_arguments = self._get_input_keyword_arguments()
        if self.allowed_input_count in _INPUT_COUNTS_WITH_NO_INPUT:
            keyword_arguments["default"] = self.default_value
        parser.add_argument(self.name, **keyword_arguments)


@dataclass(
    frozen=True,
    kw_only=True,
)
class NamedArgument(_ArgumentWithNames, _ArgumentWithInput):
    """An input given after its arg name, e.g. `--output ./notes`."""
    is_required: bool = False

    def __post_init__(
        self,
    ) -> None:
        super().__post_init__()
        if self.is_required and self.default_value is not None:
            raise ValueError(
                f"{type(self).__name__} `{self.long_arg_name}`: `default_value` must be `None` when `is_required` is `True`, since a required argument never falls back; got `{self.default_value}`.",
            )

    def add_to_parser(
        self,
        parser: argparse.ArgumentParser,
    ) -> None:
        keyword_arguments = self._get_input_keyword_arguments()
        if self.is_required:
            keyword_arguments["required"] = True
        else:
            keyword_arguments["default"] = self.default_value
        parser.add_argument(
            *self.arg_names,
            dest=self.param_name,
            **keyword_arguments,
        )


@dataclass(
    frozen=True,
    kw_only=True,
)
class FlagArgument(_ArgumentWithNames):
    """A named argument that takes no input, e.g. `--dry-run`; received as `True` if passed and `False` if not."""

    def add_to_parser(
        self,
        parser: argparse.ArgumentParser,
    ) -> None:
        parser.add_argument(
            *self.arg_names,
            dest=self.param_name,
            action="store_true",
            default=False,
            help=self.description,
        )


_RESERVED_PARAM_NAME = "tool_params"


@dataclass(frozen=True)
class Command:
    """One cmd of a tool, run as `<tool> <name> [arguments]`: its description, its arguments, and the function it calls."""
    name: str
    description: str
    fn: Callable[..., None]
    arguments: list[Argument] = field(default_factory=list)

    def __post_init__(
        self,
    ) -> None:
        param_names = [_argument.param_name for _argument in self.arguments]
        if _RESERVED_PARAM_NAME in param_names:
            raise ValueError(
                f"cmd `{self.name}`: argument names must not be `{_RESERVED_PARAM_NAME}`, which every cmd function already receives; got `{_RESERVED_PARAM_NAME}`.",
            )
        repeated_param_names = sorted(
            {_param_name
             for _param_name in param_names
             if param_names.count(_param_name) > 1},
        )
        if len(repeated_param_names) > 0:
            repeated_param_names_text = ", ".join(f"`{_param_name}`" for _param_name in repeated_param_names)
            raise ValueError(
                f"cmd `{self.name}`: argument parameter names must be unique; got {repeated_param_names_text} more than once.",
            )

    def call(
        self,
        *,
        tool_params: params.ToolParams,
        parsed_arguments: argparse.Namespace,
    ) -> None:
        """Call `fn` with `tool_params` and each argument by its parameter name, all as keywords."""
        argument_values = {
            _argument.param_name: getattr(parsed_arguments, _argument.param_name)
            for _argument in self.arguments
        }
        self.fn(
            tool_params=tool_params,
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
        Flags beyond `--dry-run` and `--hide-actions`, which every tool has.

    - `hidden_cmds`:
        Cmds that can be run but are left out of help.

    - `tool_params_type`:
        `ToolParams` or a subclass with one field per extra flag; built from the parsed flags with
        `from_parsed_arguments`.
    """
    name: str
    description: str
    cmd_groups: list[CommandGroup]
    hidden_cmds: list[Command] = field(default_factory=list)
    flags: list[FlagArgument] = field(default_factory=list)
    tool_params_type: type[params.ToolParams] = params.ToolParams
    output_params: params.OutputParams = params.OutputParams()

    def __post_init__(
        self,
    ) -> None:
        flags_by_param_name = {_flag.param_name: _flag for _flag in self.all_flags}
        for cmd in self.all_cmds:
            clashing_param_names = sorted(
                {
                    _argument.param_name
                    for _argument in cmd.arguments
                    if _argument.param_name in flags_by_param_name
                },
            )
            if len(clashing_param_names) > 0:
                clash_descriptions = ", ".join(
                    f"`{_param_name}`, which is also `--{flags_by_param_name[_param_name].long_arg_name}`"
                    for _param_name in clashing_param_names
                )
                raise ValueError(
                    f"cmd `{cmd.name}`: argument parameter names must differ from the flags of the tool; got {clash_descriptions}.",
                )

    @property
    def all_flags(
        self,
    ) -> list[FlagArgument]:
        return [*_BUILT_IN_FLAGS, *self.flags]

    @property
    def all_cmds(
        self,
    ) -> list[Command]:
        grouped_cmds = [_cmd for _cmd_group in self.cmd_groups for _cmd in _cmd_group.cmds]
        return [*grouped_cmds, *self.hidden_cmds]


_DRY_RUN_FLAG = FlagArgument(
    long_arg_name="dry-run",
    description="print commands without executing them",
)
_HIDE_ACTIONS_FLAG = FlagArgument(
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
            for _message_group in _manage_terminal.MESSAGE_GROUPS
            for _message_style in _message_group.grouped_message_styles
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
        flag: FlagArgument,
    ) -> str:
        """The forms of a flag, e.g. `-o, --output`."""
        return ", ".join(flag.arg_names)

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
        usage_flags = " ".join(f"[--{_flag.long_arg_name}]" for _flag in self.all_flags)
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
            self._print_row(
                label=self._get_flag_label(flag),
                label_style=_manage_terminal.Colour.CYAN.value,
                description=flag.description,
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
    for flag in command_line_tool.all_flags:
        flag.add_to_parser(argument_parser)
    subparsers = argument_parser.add_subparsers(
        dest="cmd",
        required=False,
        metavar="<command>",
    )
    for cmd in command_line_tool.all_cmds:
        subparser = subparsers.add_parser(cmd.name, help=cmd.description)
        for argument in cmd.arguments:
            argument.add_to_parser(subparser)
    return argument_parser


def run_cli(
    *,
    command_line_tool: CommandLineTool,
    argv: Sequence[str] | None = None,
) -> None:
    """Parse argv (default: `sys.argv`), build the tool params, set up output for the run, and run one cmd."""
    parsed_arguments = _build_parser(command_line_tool).parse_args(argv)
    if parsed_arguments.help or parsed_arguments.cmd is None:
        command_line_tool_help = _CommandLineToolHelp(command_line_tool)
        command_line_tool_help.print_help()
        return
    tool_params = command_line_tool.tool_params_type.from_parsed_arguments(parsed_arguments)
    _manage_terminal.set_params(
        tool_params=tool_params,
        output_params=command_line_tool.output_params,
    )
    cmds_by_name = {_cmd.name: _cmd for _cmd in command_line_tool.all_cmds}
    selected_cmd = cmds_by_name[parsed_arguments.cmd]
    try:
        selected_cmd.call(
            tool_params=tool_params,
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
