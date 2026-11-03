# cmd_args

Design notes for `huginn.cmd_args`: the args of a cmd, and the input value types they take, as a tool author writes them in a command table. How a tool, its cmds, and its flags use them is in [`<terminal-interface>/design-plan/manage_cli.md`](manage_cli.md).

---

## Input Value Types

| Detail | Choice | State |
|---|---|---|
| Input value | a value the user types for an argument, as opposed to one huginn supplies: the `True` or `False` of a flag, or a `default_value` used when nothing is typed | decided |
| Type | `InputValueType(placeholder_name, convert_fn)`, frozen: `placeholder_name` is the name shown in help, and `convert_fn` turns the typed text into the value the cmd receives; neither has a default, since the conversion is what makes an input value type, so each one states it, even `TEXT` with `convert_fn=str` | decided |
| Placeholder name | letters, digits, `_`, and `-` only, checked when the input value type is made; huginn adds the brackets, so a tool cannot pass its own | decided |
| Basic set | grouped in the class `InputValueTypes`, which is never made: `TEXT`, `NUMBER` (`int`), `DATE` (`datetime.date`, from `YYYY-MM-DD`), `PATH` and `DIR` (both `Path`; `<dir>` tells the user more), used as `cmd_args.InputValueTypes.DATE` | decided |
| Extending | a tool subclasses `InputValueTypes` under the same name and adds its own, e.g. `class InputValueTypes(cmd_args.InputValueTypes)` with `BRANCH: ClassVar[cmd_args.InputValueType] = cmd_args.InputValueType(placeholder_name="branch", convert_fn=str)`; each type is annotated `ClassVar`, since the class is meant to be subclassed and so cannot be marked final; its command table then reaches every type, its own and the basic ones, through its one class; domain types stay in the tool, so huginn names no tool-specific concept | decided |
| Shown as | always `<placeholder name>`, so every tool prints input values the same way | decided |
| Required | every positional and named argument states its input value type; there is no default, so a tool picks `TEXT` on purpose rather than by leaving it out; a flag has no input value and so no input value type | decided |
| Bad input value | `convert_fn` raises `argparse.ArgumentTypeError` with a message for the user, so a bad input value is a usage error before the cmd runs, e.g. ``date must be YYYY-MM-DD; got `2026-13-01`.`` | decided |
| One module | input value types live in `cmd_args` with the args that take them, since only args use them and both are what a tool author writes in a command table | decided |

The label and the conversion live together, so they cannot disagree: `NUMBER` always shows `<number>` and always gives an `int`. A shared set of generic types grows only when several tools show the same need.

---

## Kinds of Argument

```text
Argument(description)
├── _ArgumentWithInputValue(input_value_type, allowed_num_input_values, default_value)
├── _ArgumentWithNames(long_arg_name, short_arg_name)
│
├── PositionalArgument(_ArgumentWithInputValue)                         + param_name
├── NamedArgument(_ArgumentWithNames, _ArgumentWithInputValue)           + is_required
└── FlagArgument(_ArgumentWithNames)
```

| Part | Detail | State |
|---|---|---|
| `Argument` | the base of every argument: `description`, which has no default, so every argument states it, and `add_to_arg_parser`, which registers it with the arg parser; never made directly | decided |
| `param_name` | what the cmd function receives an argument as; every concrete kind has one, a field on `PositionalArgument` and derived from the long arg name on the named kinds, so `Command.args` lists the three concrete kinds rather than the base | decided |
| `_ArgumentWithInputValue` | private; what an argument the user types a value for adds: `input_value_type` (an `InputValueType`), `allowed_num_input_values`, and `default_value`, and turning them into argparse params | decided |
| `_ArgumentWithNames` | private; what an argument the user types by name adds: `long_arg_name` (shown as `--<long arg name>`) and optional `short_arg_name` (shown as `-<short arg name>`), their checks, `arg_names` (every typed form, e.g. `["-o", "--output"]`), and a `param_name` from the long arg name | decided |
| `PositionalArgument(_ArgumentWithInputValue)` | an input value typed straight after the cmd name, e.g. `arch-news-since 2026-10-01`; adds `param_name`; only its value is typed, so it has a param name and no arg name | decided |
| `NamedArgument(_ArgumentWithNames, _ArgumentWithInputValue)` | an input value given after its arg name, e.g. `--output ./notes`; adds `is_required` | decided |
| `FlagArgument(_ArgumentWithNames)` | a named argument with no input value, e.g. `--dry-run`; received as `True` if passed and `False` if not | decided |
| Ownership | each class owns the fields it adds, their checks, and their part of the argparse wiring, so no module function does the work of a type; the concrete kinds are the combinations of the two private bases, and tools only ever write the concrete kinds | decided |
| Check chain | each `__post_init__` calls `super().__post_init__()` first, so making a `NamedArgument` runs the arg name checks of `_ArgumentWithNames`, then its own; `Argument.__post_init__` ends the chain | decided |
| Input value type | `input_value_type` has no default and no `None`, and exists only on the kinds the user types a value for, so a flag cannot be given one and an input value cannot be left without one | decided |
| Defaults | a field has a default only when the default means "nothing extra": absent (`short_arg_name=None`, `default_value=None`), off (`is_required=False`), or the plain case (`allowed_num_input_values=ONE`); a field with no neutral value, such as `description` or `input_value_type`, has no default, so every argument states it; this keeps a command table to what is special about each entry | decided |
| `AllowedNumInputValues` | how many input values an argument allows the user to type: `ONE` (the default), `ZERO_OR_ONE`, `ZERO_OR_MORE`, or `ONE_OR_MORE`; the enum answers questions about itself: `nargs_symbol` gives the argparse symbol (`?`, `*`, `+`, or `None` for `ONE`), and `is_zero_allowed` says whether the user may type nothing, so a default value can apply | decided |
| Arg and param | an arg is what the user types on the command line, e.g. `--output`; a param is what the cmd function receives, e.g. `output`; the shorthand marks these concrete things, while the types that define them keep the full word, e.g. `NamedArgument` | decided |

---

## Definition Checks

Each argument checks itself when made, so a mistake in a command table fails when the tool starts. A check catches a definition that would otherwise pass silently or fail later with an unclear message, and raises a `ValueError` that says what went wrong. The scope before the colon is always just the type, as written in the command table; the sentence then names the field, the argument it belongs to as "for `<name>`", what it must be and why, and what it got, e.g. ``NamedArgument: `default_value` for `output` must be `None` when `is_required` is `True`, since a required argument never falls back; got `.`.`` A check on the identifying name itself leaves out the "for", since that name is the bad value, e.g. ``PositionalArgument: `param_name` must be lowercase letters, digits, and `_`, starting with a letter; got `Since`.`` Rules the types already express, such as a flag having no input value type, need no check.

| Where | Check | State |
|---|---|---|
| `PositionalArgument` | `param_name` is lowercase letters, digits, and `_`, starting with a letter, since it is a Python parameter name | decided |
| `PositionalArgument` | `default_value` only with `ZERO_OR_ONE` or `ZERO_OR_MORE`; otherwise an input value is always given and the default is never used | decided |
| `NamedArgument`, `FlagArgument` | `long_arg_name` is lowercase letters, digits, and `-`, starting with a letter, with no dashes passed in | decided |
| `NamedArgument`, `FlagArgument` | `short_arg_name` is one to three letters | decided |
| `NamedArgument` | not `is_required` together with `default_value`: a required argument never falls back | decided |

The checks that involve more than one argument, such as two args of one cmd sharing a param name, belong to `Command` and `CommandLineTool`, and are in [`<terminal-interface>/design-plan/manage_cli.md`](manage_cli.md).
