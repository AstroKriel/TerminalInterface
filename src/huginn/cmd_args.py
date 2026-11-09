## { MODULE

##
## === DEPENDENCIES
##

## stdlib
import argparse
import datetime
import re
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Any, ClassVar, TypeAlias

##
## === INPUT VALUE TYPES
## what kind of value the user types for an arg; a tool adds its own by subclassing `InputValueTypes`.
##


@dataclass(frozen=True)
class InputValueType:
    """
    What kind of value the user types: the name of its placeholder in help, shown as `<name>`, and its conversion.

    `convert_fn` receives the text exactly as the user typed it, and returns the value the cmd function receives.
    """
    placeholder_name: str
    convert_fn: Callable[[str], Any]

    def __post_init__(
        self,
    ) -> None:
        placeholder_name_is_valid = re.fullmatch(r"[A-Za-z0-9_-]+", self.placeholder_name) is not None
        if not placeholder_name_is_valid:
            raise ValueError(
                f"{type(self).__name__}: `placeholder_name` must be letters, digits, `_`, or `-`; got `{self.placeholder_name}`.",
            )


def _convert_str_to_date(
    text: str,
) -> datetime.date:
    try:
        return datetime.date.fromisoformat(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"date must be YYYY-MM-DD; got `{text}`.") from None


def _convert_str_to_yes_or_no(
    text: str,
) -> bool:
    return text.strip().lower().startswith("y")


class InputValueTypes:
    """
    The basic input value types every tool can use.

    A tool extends them by subclassing, e.g. `class InputValueTypes(cmd_args.InputValueTypes)`, so its command table
    reaches every type, its own and the basic ones, through one class.
    """
    TEXT: ClassVar[InputValueType] = InputValueType(
        placeholder_name="text",
        convert_fn=str,
    )
    NUMBER: ClassVar[InputValueType] = InputValueType(
        placeholder_name="number",
        convert_fn=int,
    )
    DATE: ClassVar[InputValueType] = InputValueType(
        placeholder_name="date",
        convert_fn=_convert_str_to_date,
    )
    PATH: ClassVar[InputValueType] = InputValueType(
        placeholder_name="path",
        convert_fn=Path,
    )
    DIR: ClassVar[InputValueType] = InputValueType(
        placeholder_name="dir",
        convert_fn=Path,
    )
    YES_OR_NO: ClassVar[InputValueType] = InputValueType(
        placeholder_name="yes-or-no",
        convert_fn=_convert_str_to_yes_or_no,
    )


##
## === INPUT VALUE COUNTS
##


class AllowedNumInputValues(Enum):
    """How many input values an argument allows the user to type."""
    ONE = auto()
    ZERO_OR_ONE = auto()
    ZERO_OR_MORE = auto()
    ONE_OR_MORE = auto()

    @property
    def nargs_symbol(
        self,
    ) -> str | None:
        """The symbol argparse expects for this many input values; `None` for `ONE`, which argparse takes by default."""
        match self:
            case AllowedNumInputValues.ONE:
                return None
            case AllowedNumInputValues.ZERO_OR_ONE:
                return "?"
            case AllowedNumInputValues.ZERO_OR_MORE:
                return "*"
            case AllowedNumInputValues.ONE_OR_MORE:
                return "+"

    @property
    def is_zero_allowed(
        self,
    ) -> bool:
        """Whether the user may type no input value at all, so a default value can be used."""
        return (self is AllowedNumInputValues.ZERO_OR_ONE) or (self is AllowedNumInputValues.ZERO_OR_MORE)


##
## === ARGUMENTS
## the args of a cmd: a positional argument, a named argument, or a flag, each built from the building blocks below.
##


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

    def add_to_arg_parser(
        self,
        arg_parser: argparse.ArgumentParser,
    ) -> None:
        """Register this argument with an arg parser."""
        raise NotImplementedError


@dataclass(
    frozen=True,
    kw_only=True,
)
class _ArgumentWithInputValue(Argument):
    """What an argument the user types a value for adds: what kind of value, how many, and what to fall back to."""
    input_value_type: InputValueType
    allowed_num_input_values: AllowedNumInputValues = AllowedNumInputValues.ONE
    default_value: Any = None

    def __post_init__(
        self,
    ) -> None:
        super().__post_init__()
        if self.input_value_type is InputValueTypes.YES_OR_NO:
            raise ValueError(
                f"{type(self).__name__}: `input_value_type` must not be `YES_OR_NO`, which is for prompts; a yes or no choice on the command line is a `FlagArgument`.",
            )

    def _get_argparse_params(
        self,
    ) -> dict[str, Any]:
        """The argparse params that come from the input value: its conversion, placeholder, count, and help."""
        argparse_params: dict[str, Any] = {
            "type": self.input_value_type.convert_fn,
            "metavar": f"<{self.input_value_type.placeholder_name}>",
            "nargs": self.allowed_num_input_values.nargs_symbol,
            "help": self.description,
        }
        return argparse_params


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
        long_arg_name_is_valid = re.fullmatch(r"[a-z][a-z0-9-]*", self.long_arg_name) is not None
        if not long_arg_name_is_valid:
            raise ValueError(
                f"{type(self).__name__}: `long_arg_name` must be lowercase letters, digits, and `-`, starting with a letter; got `{self.long_arg_name}`.",
            )
        if self.short_arg_name is None:
            short_arg_name_is_valid = True
        else:
            short_arg_name_is_valid = re.fullmatch(r"[A-Za-z]{1,3}", self.short_arg_name) is not None
        if not short_arg_name_is_valid:
            raise ValueError(
                f"{type(self).__name__}: `short_arg_name` for `{self.long_arg_name}` must be one to three letters; got `{self.short_arg_name}`.",
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
        arg_names: list[str] = []
        if self.short_arg_name is not None:
            arg_names.append(f"-{self.short_arg_name}")
        arg_names.append(f"--{self.long_arg_name}")
        return arg_names


@dataclass(
    frozen=True,
    kw_only=True,
)
class PositionalArgument(_ArgumentWithInputValue):
    """An input value typed straight after the cmd name; only its value is typed, so it has a param name and no arg name."""
    param_name: str

    def __post_init__(
        self,
    ) -> None:
        super().__post_init__()
        param_name_is_valid = re.fullmatch(r"[a-z][a-z0-9_]*", self.param_name) is not None
        if not param_name_is_valid:
            raise ValueError(
                f"{type(self).__name__}: `param_name` must be lowercase letters, digits, and `_`, starting with a letter; got `{self.param_name}`.",
            )
        if (self.default_value is not None) and (not self.allowed_num_input_values.is_zero_allowed):
            raise ValueError(
                f"{type(self).__name__}: `default_value` for `{self.param_name}` must be `None` when `allowed_num_input_values` is `{self.allowed_num_input_values.name}`, since an input value is always given; got `{self.default_value}`.",
            )

    def add_to_arg_parser(
        self,
        arg_parser: argparse.ArgumentParser,
    ) -> None:
        argparse_params = self._get_argparse_params()
        if self.allowed_num_input_values.is_zero_allowed:
            argparse_params["default"] = self.default_value
        arg_parser.add_argument(self.param_name, **argparse_params)


@dataclass(
    frozen=True,
    kw_only=True,
)
class NamedArgument(_ArgumentWithNames, _ArgumentWithInputValue):
    """An input value given after its arg name, e.g. `--output ./notes`."""
    is_required: bool = False

    def __post_init__(
        self,
    ) -> None:
        super().__post_init__()
        if self.is_required and (self.default_value is not None):
            raise ValueError(
                f"{type(self).__name__}: `default_value` for `{self.long_arg_name}` must be `None` when `is_required` is `True`, since a required argument never falls back; got `{self.default_value}`.",
            )

    def add_to_arg_parser(
        self,
        arg_parser: argparse.ArgumentParser,
    ) -> None:
        argparse_params = self._get_argparse_params()
        if self.is_required:
            argparse_params["required"] = True
        else:
            argparse_params["default"] = self.default_value
        arg_parser.add_argument(
            *self.arg_names,
            dest=self.param_name,
            **argparse_params,
        )


@dataclass(
    frozen=True,
    kw_only=True,
)
class FlagArgument(_ArgumentWithNames):
    """A named argument with no input value, e.g. `--dry-run`; received as `True` if passed and `False` if not."""

    def add_to_arg_parser(
        self,
        arg_parser: argparse.ArgumentParser,
    ) -> None:
        arg_parser.add_argument(
            *self.arg_names,
            dest=self.param_name,
            action="store_true",
            default=False,
            help=self.description,
        )


##
## === TYPE ALIASES
##

CommandArgument: TypeAlias = PositionalArgument | NamedArgument | FlagArgument

## } MODULE
