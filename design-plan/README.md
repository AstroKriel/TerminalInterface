# Design Plan

Index of the design notes for `TerminalInterface`, its scope, and the principles every part follows.

Each entry in a design note carries one of three states: **decided** (agreed and ready to build), **proposed** (a suggested default awaiting a decision), or **open** (a question with no suggested answer yet).

---

## What TerminalInterface Is

`TerminalInterface` is the layer between a command line tool and the terminal. It has three jobs:

1. Output: every message a tool prints goes through one set of functions, one per message type, so all tools look and read the same.
2. Running commands: every command a tool runs is announced in full before it runs, so the user always sees what happens underneath and can rerun or inspect it.
3. Building the interface: a tool describes its subcommands once, and gets argument parsing, grouped help, flags, and dry-run support from that description.

It grew out of a terminal layer that had been copied between tools and had drifted apart. One shared copy means an improvement made for one tool reaches all of them.

---

## Scope

| Belongs | Does not belong |
|---|---|
| Printing messages, steps, outcomes, items, returns, and errors | Anything that knows about the subject of one tool, such as git state or package managers |
| Running commands: mutating, read-only, captured, and probing | File actions such as creating symlinks or backing up files |
| Dry-run behaviour for mutating commands | Config files of any one tool |
| Building a subcommand interface with grouped help and global flags | |
| A log file of output for every tool | |

A feature belongs here only if it is about the terminal and at least two tools need it. State: decided.

---

## Principles

| Principle | Detail | State |
|---|---|---|
| Show every command | each command is printed in full before it runs, styled by kind: mutating, skipped in dry-run, or read-only | decided |
| Narration and returns are separate | narration always goes to stderr; a return, what the tool hands back to the user or a pipe, always goes to stdout | decided |
| Dry-run is built in | every tool gets `--dry-run`; mutating runners print the command and skip it; read-only runners still run | decided |
| Stable names | the functions tools already call keep their names, so adopting this package is an import change plus a mechanical rename (see [`<terminal-interface>/design-plan/adopting.md`](adopting.md)) | decided |
| One vocabulary | params: a container of options, named by what it is for, e.g. `BuiltInParams` for the values of the built-in flags in one run, or the argparse params an argument hands to `add_argument`; a tool: one command line tool, described by `CommandLineTool` | decided |
| Cmd and message forms | a cmd starts as `cmd_parts`, e.g. `["git", "push"]`, and is shown as `cmd`, the joined `git push`; a message starts as raw text a tool or runner supplies, e.g. `sim_b: it has no input file`, passed as `text` to a function about one message, such as `log_outcome` or `MessageStyle.render`, and held as `msg_text` where it is built from other things, such as an item line `<name> = <value>`; a style turns it into `msg_rendered`, markup with the text escaped and the style's symbol, label, and colour added, e.g. `[#B86B00]↪ skipped: sim_b: it has no input file[/]`; that is then printed to the terminal as is, and for the log becomes `msg_plain`, with the markup removed, then `msg_for_log_file`, with a time stamp in front; markup is the format rich reads, and only huginn produces it | decided |
| Light to install | one third-party dependency (`rich`), so it installs on a fresh machine through `uv` alone | decided |

---

## Index

| Note | Covers |
|---|---|
| [`<terminal-interface>/design-plan/manage_log.md`](manage_log.md) | output functions, message types, built-in params, and the log file |
| [`<terminal-interface>/design-plan/manage_shell.md`](manage_shell.md) | command runners |
| [`<terminal-interface>/design-plan/cmd_args.md`](cmd_args.md) | the args of a cmd: input value types and how a tool extends them, positional arguments, named arguments, flags, and their checks |
| [`<terminal-interface>/design-plan/manage_cli.md`](manage_cli.md) | the tool and its cmds, the built-in flags, grouped help, and the entry point |
| [`<terminal-interface>/design-plan/jormi_log.md`](jormi_log.md) | moving the jormi log layer onto huginn: usage, mapping, grouped messages, library code, and uncaught exceptions |
| [`<terminal-interface>/design-plan/adopting.md`](adopting.md) | how an existing tool moves onto this package, and how it pins a version |

---

## Project Layout

```text
TerminalInterface/
├── pyproject.toml  # one dependency: rich
├── README.md
├── design-plan/  # these notes
├── demos/  # runnable examples: a small tool that keeps dated backups of a notes file, and every output function
├── src/
│   └── huginn/
│       ├── cmd_args.py  # the args of a cmd: input value types, positional arguments, named arguments, and flags
│       ├── _message_styles.py  # private: palette and message kinds, each style drawing its own lines, and the groups the style legend is built from
│       ├── _manage_output.py  # private: the built-in params, the active state of a run, the consoles, and routing each message to the terminal and the log file
│       ├── manage_log.py  # output functions
│       ├── manage_shell.py  # command runners
│       └── manage_cli.py  # the tool and its cmds, grouped help, and the entry point
└── utests/
```

| Decision | Detail | State |
|---|---|---|
| Package name | `huginn`, the raven of Odin who flies out and reports back, so imports read `from huginn import manage_log, manage_shell`; renamed from `heimdall` on 2026-10-27, which passes to a planned types and validation package | decided |
| Python | `>=3.11`, the oldest version any planned user declares; tests run on 3.11 and 3.14 | decided |
| Module names | a module that does things is named `manage_<noun>` (`manage_log`, `manage_shell`, `manage_cli`, and the private `_manage_output`); a module that only defines the types a tool author writes is named after them, plain (`cmd_args`); a module only huginn itself uses is private, with a leading `_` (`_manage_output`, `_message_styles`), while the names inside it stay plain, since other huginn modules use them; `manage_log` and `manage_shell` also match the jormi modules expected to move in, so that move merges into same-named modules | decided |
| Message styles and output | the private `_message_styles` defines what each kind of message looks like and draws lines in those styles; a tool never picks a style, since each `manage_log` function and shell runner brings its own, and the one choice a tool makes, the outcome status, it reaches as `manage_log.OutcomeStatus`; the private `_manage_output` holds what the public modules share for routing messages: the active state (the built-in params and the log file), and the consoles; neither public module depends on another, and a later message layer can be added on the same styles and output | decided |
| Params beside their active copy | `BuiltInParams` is defined in `_manage_output`, beside the one active copy huginn reads; a tool author never writes it. A second group gets its own module only once two groups exist, e.g. if the block width and the log file path become one group set by the tool author | decided |
| First version | the existing terminal layer, generalised in three places, plus the additions described in the module notes: runners named for what happens to their output, `working_directory` on every runner, `query_cmd_and_capture_outcome`, quoted command printing, and the log file | decided |
