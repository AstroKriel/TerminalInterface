# cli_builder

Design notes for `heimdall.cli_builder`: describing a tool and its subcommands once, and getting argument parsing, grouped help, and flags from that description.

---

## Describing a Subcommand

| Part | Detail | State |
|---|---|---|
| `CommandArgument` | one argument: a bare positional or a `--flag`, with `argument_name`, `value_type`, `default_value`, `value_placeholder`, `argument_help`, `is_switch`, `is_required`, and `value_count` | decided |
| `ValueCount` | how many values an argument takes: `OPTIONAL`, `ANY`, or `AT_LEAST_ONE`, each holding the argparse symbol (`?`, `*`, `+`) | decided |
| `make_command(command_name=..., command_fn=..., command_help=..., command_arguments=..., is_hidden=...)` | one entry in the command table | decided |
| `make_command_group(section_title=..., commands=[...])` | stamps a section title onto a list of entries, so each group names its section once | decided |
| Ungrouped commands | a visible command must be in a group; `run_cli` rejects one that is not, so a command never drops out of help silently | decided |
| Section titles | plain strings, so a tool does not need its own enum type; a `str` enum still works, since its values are strings | decided |
| Hidden commands | registered and callable, left out of the help listing | decided |
| Failed command | `run_cli` reports an error outcome naming the command that failed, then exits with its exit status | decided |
| How a command function is called | `command_fn(run_params=..., <arg_1>=..., <arg_2>=...)`, every argument by keyword, named after its argparse destination (`--base-ref` becomes `base_ref`) | decided |

`CommandArgument` is public here; in the existing layer it was private to one tool. Calling by keyword means a command function declares its parameters keyword-only and names them after the arguments they receive, so a mismatch fails loudly instead of passing a value to the wrong parameter.

---

## Describing a Tool

The second generalisation: the existing entry point hardcoded the name, usage line, and global flags of one tool. Here a tool describes itself once and hands that description to the entry point.

| Field | Holds | State |
|---|---|---|
| `name` | the command typed, e.g. `<tool_name>`; shown in help and usage | decided |
| `description` | one line, shown at the top of help | decided |
| `commands` | the command table: groups and hidden commands, in help order | decided |
| `flags` | flags beyond `--dry-run`, which every tool has, as `CommandArgument`s | decided |
| `make_run_params` | builds the `RunParams` of the tool (or a subclass) from the parsed flags | decided |
| `show_timestamps` | whether terminal lines carry a timestamp; off by default | decided |
| `record_path` | where the persistent record is appended; `None` (the default) writes no record | decided |
| Type name | `CommandLineTool`; a variable holding one is named `command_line_tool` | decided |

```text
run_cli(command_line_tool=command_line_tool)
```

`run_cli` builds the parser, registers every subcommand and its arguments, parses, builds the run params through `make_run_params`, sets the output for the run, dispatches, and exits with the return code of a failed command when one raises. State: decided.

---

## Help Output

| Section | Contents | State |
|---|---|---|
| When shown | on `-h` or `--help`, and when no command is given | decided |
| Header | tool name and description | decided |
| Usage | `<tool_name> [--dry-run] [<extra-flags>] <command> [args]`, built from `flags` | decided |
| Command groups | one heading per section, each command with its help, in table order | decided |
| Flags | `--dry-run` and each extra flag with its help | decided |
| Output legend | one line per message type, generated from the message types | decided |
| Indent | four spaces before every row | decided |
| Separator | spaces only, never tabs, so the layout is the same width on every machine | decided |
| Column width | computed per help screen: the longest label on the screen (command, flag, or legend label) plus two spaces; every section shares it, so descriptions line up across the whole screen | decided |

The column width is never hardcoded, so a long command name widens the column instead of breaking the alignment.

The third generalisation: generating the legend from the message types removes the second copy of the colour values that the existing help kept.
