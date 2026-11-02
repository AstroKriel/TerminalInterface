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
## === INPUT TYPES
## the basic input types; a tool defines its own in an `input_types` module of its own, the same way.
##

_PLACEHOLDER_NAME_PATTERN = re.compile(r"[A-Za-z0-9_-]+")


@dataclass(frozen=True)
class InputType:
    """What an input is: the name of its placeholder in help, shown as `<name>`, and the function that converts it."""
    placeholder_name: str
    convert_fn: Callable[[str], Any] = str

    def __post_init__(
        self,
    ) -> None:
        if _PLACEHOLDER_NAME_PATTERN.fullmatch(self.placeholder_name) is None:
            raise ValueError(
                f"input type: `placeholder_name` must be letters, digits, `_`, or `-`; got `{self.placeholder_name}`.",
            )


def _convert_str_to_date(
    text: str,
) -> datetime.date:
    try:
        return datetime.date.fromisoformat(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"date must be YYYY-MM-DD; got `{text}`.") from None


TEXT = InputType(placeholder_name="text")
NUMBER = InputType(
    placeholder_name="number",
    convert_fn=int,
)
DATE = InputType(
    placeholder_name="date",
    convert_fn=_convert_str_to_date,
)
PATH = InputType(
    placeholder_name="path",
    convert_fn=Path,
)
DIR = InputType(
    placeholder_name="dir",
    convert_fn=Path,
)

## } MODULE
