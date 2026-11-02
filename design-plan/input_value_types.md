# input_value_types

Design notes for `huginn.input_value_types`: what kind of value the user types for an argument. Arguments are described in [`<terminal-interface>/design-plan/manage_cli.md`](manage_cli.md).

---

## Input Value Types

| Detail | Choice | State |
|---|---|---|
| Input value | a value the user types for an argument, as opposed to one huginn supplies: the `True` or `False` of a flag, or a `default_value` used when nothing is typed | decided |
| Type | `InputValueType(placeholder_name, convert_fn)`, frozen: `placeholder_name` is the name shown in help, and `convert_fn` turns the typed text into the value the cmd receives; neither has a default, since the conversion is what makes an input value type, so each one states it, even `TEXT` with `convert_fn=str` | decided |
| Placeholder name | letters, digits, `_`, and `-` only, checked when the input value type is made; huginn adds the brackets, so a tool cannot pass its own | decided |
| Basic set | `TEXT`, `NUMBER` (`int`), `DATE` (`datetime.date`, from `YYYY-MM-DD`), `PATH` and `DIR` (both `Path`; `<dir>` tells the user more) | decided |
| Extending | a tool defines its own input value types the same way, in an `input_value_types` module of its own, e.g. `BRANCH = InputValueType(placeholder_name="branch", convert_fn=str)`; domain types stay in the tool, so huginn names no tool-specific concept | decided |
| Shown as | always `<placeholder name>`, so every tool prints input values the same way | decided |
| Required | every positional and named argument states its input value type; there is no default, so a tool picks `TEXT` on purpose rather than by leaving it out; a flag has no input value and so no input value type | decided |
| Bad input value | `convert_fn` raises `argparse.ArgumentTypeError` with a message for the user, so a bad input value is a usage error before the cmd runs, e.g. ``date must be YYYY-MM-DD; got `2026-13-01`.`` | decided |

The label and the conversion live together, so they cannot disagree: `NUMBER` always shows `<number>` and always gives an `int`. A shared set of generic types grows only when several tools show the same need.
