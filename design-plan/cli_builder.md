# cli_builder

Design notes for `heimdall.cli_builder`: describing subcommands once, and getting argument parsing, grouped help, and global flags from that description.

---

## Describing a Subcommand

| Part | Detail | State |
|---|---|---|
| `CommandArg` | one argument: a bare positional or a `--flag`, with type, default, metavar, help, `store_true`, `required`, and `nargs` | decided |
| `cli_command(cmd_name=..., cmd_fn=..., cmd_help=..., cmd_args=..., is_hidden=...)` | one entry in the command table | decided |
| `command_group(section_title=..., commands=[...])` | stamps a section title onto a list of entries, so each group names its section once | decided |
| Section titles | plain strings, so a tool does not need its own enum type | proposed |
| Hidden commands | registered and callable, left out of the help listing | decided |
| How a command function is called | `cmd_fn(config, <arg-1>, <arg-2>, ...)`, positional arguments in the order of `cmd_args` | decided |

`CommandArg` is public here; in the existing layer it was private to one tool.

---

## Describing a Tool

The second generalisation: the existing entry point hardcoded the name, usage line, and global flags of one tool. Here a tool describes itself once and hands that description to the entry point.

| Field | Holds | State |
|---|---|---|
| `tool_name` | the command typed, e.g. `<tool_name>`; shown in help and usage | decided |
| `description` | one line, shown at the top of help | decided |
| `global_flags` | extra flags beyond `--dry-run`, as `CommandArg`s | decided |
| `make_config` | builds the `Config` of the tool (or a subclass) from the parsed global flags | decided |
| `commands` | the command table: groups and hidden commands, in help order | decided |
| Type name | `ToolSpec` | proposed |

```text
run_cli(tool_spec=<tool-spec>)
```

`run_cli` builds the parser, registers every subcommand and its arguments, parses, builds the config through `make_config`, dispatches, and exits with the return code of a failed command when one raises. State: decided.

---

## Help Output

| Section | Contents | State |
|---|---|---|
| Header | tool name and description | decided |
| Usage | `<tool_name> [--dry-run] [<extra-flags>] <command> [args]`, built from `global_flags` | decided |
| Command groups | one heading per section, each command with its help, in table order | decided |
| Global flags | `--dry-run` and each extra flag with its help | decided |
| Output legend | one line per theme, generated from the theme table | decided |

The third generalisation: generating the legend from the themes removes the second copy of the colour values that the existing help kept.

> **Note:** help lines currently align command names with padded columns. Whether to keep that or switch to a single tab separator is open.
