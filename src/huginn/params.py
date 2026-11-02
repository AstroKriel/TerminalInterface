## { MODULE

##
## === DEPENDENCIES
##

## stdlib
import argparse
import dataclasses
from dataclasses import dataclass
from pathlib import Path
from typing import Self

##
## === PARAMS
## every params group of huginn: the user sets `ToolParams` by flags; the tool author sets `OutputParams`.
##


@dataclass(frozen=True)
class ToolParams:
    """
    The values of the flags of a tool for one run, e.g. `--dry-run`; a cmd gets its own arguments separately.

    A tool with flags of its own subclasses it as `<ToolName>Params` and declares one field per flag.
    """
    dry_run: bool = False
    hide_actions: bool = False

    @classmethod
    def from_parsed_arguments(
        cls,
        parsed_arguments: argparse.Namespace,
    ) -> Self:
        """Fill every field from the flag of the same name; a field with no flag raises `AttributeError`."""
        flag_values = {
            _field.name: getattr(parsed_arguments, _field.name)
            for _field in dataclasses.fields(cls)
        }
        return cls(**flag_values)


@dataclass(frozen=True)
class OutputParams:
    """How a tool sets up its output: timestamps on terminal lines, and the log file."""
    show_timestamps: bool = False
    log_path: Path | None = None


## } MODULE
