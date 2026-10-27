# manage_cli

Design notes for `heimdall.manage_cli`: describing a tool and its cmds once, and getting argument parsing, grouped help, and flags from that description.

---

## Structure

A tool is described as nested frozen dataclasses, one per concept, so the structure itself enforces what used to need checks: a visible cmd cannot be ungrouped, and a group exists once instead of being stamped onto each cmd. Inside each dataclass, field names drop the owner prefix, since the type already qualifies them (`cmd.name`, not `cmd.cmd_name`). Within `manage_cli`, a cmd is a cmd of the tool: it runs as `<tool> <cmd> [arguments]`.

```text
CommandLineTool
├── name, description
├── flags: list[CommandArgument]
├── cmd_groups: list[CommandGroup]
│   └── CommandGroup(title, cmds: list[Command])
│       └── Command(name, description, fn, arguments: list[CommandArgument])
├── hidden_cmds: list[Command]
├── run_params_type: type[RunParams]
└── output_params: OutputParams(show_timestamps, log_path)
```

| Part | Detail | State |
|---|---|---|
| `CommandArgument` | one argument of a cmd or a tool: a bare positional or a `--flag`, with `name`, `description`, `value_type`, `default_value`, `value_placeholder`, `is_switch`, `is_required`, and `value_count` | decided |
| `ValueCount` | how many values an argument takes: `OPTIONAL`, `ANY`, or `AT_LEAST_ONE`, each holding the argparse symbol (`?`, `*`, `+`) | decided |
| `Command` | one cmd: `name`, `description`, `fn`, and `arguments` | decided |
| `CommandGroup` | cmds listed together in help under one `title`; a `str` enum title prints its value | decided |
| Hidden cmds | `hidden_cmds` on the tool: registered and runnable, left out of help | decided |
| Run params | `run_params_type` names `RunParams` or a subclass; `run_cli` builds it with the classmethod `from_parsed_arguments`, which a subclass overrides to read its own flags | decided |
| Output params | `output_params` holds an `OutputParams` (`show_timestamps`, `log_path`), also available as `manage_log.OutputParams` | decided |
| Failed cmd | `run_cli` reports an error outcome naming the shell cmd that failed, then exits with its exit status | decided |
| How a cmd function is called | `fn(run_params=..., <parameter_1>=..., <parameter_2>=...)`, every argument by keyword under its `parameter_name` (`--base-ref` becomes `base_ref`) | decided |
| Type name | `CommandLineTool`; a variable holding one is named `command_line_tool` | decided |

Calling by keyword means a cmd function declares its parameters keyword-only and names them after the arguments they receive, so a mismatch fails loudly instead of passing a value to the wrong parameter.

```text
run_cli(command_line_tool=command_line_tool)
```

`run_cli` builds the parser, registers every cmd and its arguments, parses, builds the run params, sets the output for the run, dispatches, and exits with the return code of a failed shell cmd when one raises. State: decided.

---

## Help Output

| Section | Contents | State |
|---|---|---|
| When shown | on `-h` or `--help`, and when no command is given | decided |
| Header | tool name and description | decided |
| Usage | `<tool_name> [--dry-run] [<extra-flags>] <command> [args]`, built from `flags` | decided |
| Cmd groups | one heading per group title, each cmd with its description, in declaration order | decided |
| Flags | `--dry-run` and each extra flag with its description | decided |
| Output legend | one line per message type, generated from the message types | decided |
| Indent | four spaces before every row | decided |
| Separator | spaces only, never tabs, so the layout is the same width on every machine | decided |
| Column width | computed per help screen: the longest label on the screen (command, flag, or legend label) plus two spaces; every section shares it, so descriptions line up across the whole screen | decided |

The column width is never hardcoded, so a long command name widens the column instead of breaking the alignment.

The third generalisation: generating the legend from the message types removes the second copy of the colour values that the existing help kept.
