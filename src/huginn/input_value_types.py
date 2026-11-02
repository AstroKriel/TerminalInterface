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
from pathlib import Path
from typing import Any

##
## === INPUT VALUE TYPES
## the basic input value types; a tool defines its own in an `input_value_types` module of its own, the same way.
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
        if re.fullmatch(r"[A-Za-z0-9_-]+", self.placeholder_name) is None:
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


TEXT = InputValueType(
    placeholder_name="text",
    convert_fn=str,
)
NUMBER = InputValueType(
    placeholder_name="number",
    convert_fn=int,
)
DATE = InputValueType(
    placeholder_name="date",
    convert_fn=_convert_str_to_date,
)
PATH = InputValueType(
    placeholder_name="path",
    convert_fn=Path,
)
DIR = InputValueType(
    placeholder_name="dir",
    convert_fn=Path,
)

## } MODULE
