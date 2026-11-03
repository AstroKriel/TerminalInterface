## { MODULE

##
## === DEPENDENCIES
##

## stdlib
import argparse
import dataclasses
from dataclasses import dataclass
from typing import Self

##
## === PARAMS
## every params group of huginn: the user sets `ToolParams` by the built-in flags.
##


@dataclass(frozen=True)
class ToolParams:
    """The values of the built-in flags for one run, e.g. `--dry-run`; huginn reads them, so a cmd never needs them."""
    dry_run: bool = False
    hide_actions: bool = False

    @classmethod
    def from_parsed_args(
        cls,
        parsed_args: argparse.Namespace,
    ) -> Self:
        """Fill every field from the flag of the same name; a field with no flag raises `AttributeError`."""
        flag_values = {
            _field.name: getattr(parsed_args, _field.name)
            for _field in dataclasses.fields(cls)
        }
        return cls(**flag_values)


## } MODULE
