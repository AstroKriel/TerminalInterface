# Design Plan

Index of the design notes for `TerminalInterface`, its scope, and the principles every part follows.

Each entry in a design note carries one of three states: **decided** (agreed and ready to build), **proposed** (a suggested default awaiting a decision), or **open** (a question with no suggested answer yet).

---

## What TerminalInterface Is

`TerminalInterface` is the layer between a command line tool and the terminal. It has three jobs:

1. Output: every message a tool prints goes through one set of themed functions, so all tools look and read the same.
2. Running commands: every command a tool runs is announced in full before it runs, so the user always sees what happens underneath and can rerun or inspect it.
3. Building the interface: a tool describes its subcommands once, and gets argument parsing, grouped help, flags, and dry-run support from that description.

It grew out of a terminal layer that had been copied between tools and had drifted apart. One shared copy means an improvement made for one tool reaches all of them.

---

## Scope

| Belongs | Does not belong |
|---|---|
| Printing messages, steps, outcomes, resolved values, results, and errors | Anything that knows about the subject of one tool, such as git state or package managers |
| Running commands: mutating, read-only, captured, and probing | File actions such as creating symlinks or backing up files |
| Dry-run behaviour for mutating commands | Config files of any one tool |
| Building a subcommand interface with grouped help and global flags | |
| Optional timestamps and an optional persistent record of output | |

A feature belongs here only if it is about the terminal and at least two tools need it. State: decided.

---

## Principles

| Principle | Detail | State |
|---|---|---|
| Show every command | each command is printed in full before it runs, styled by kind: mutating, skipped in dry-run, or read-only | decided |
| Diagnostics and results are separate | narration goes to stderr unless a tool sends it to stdout; results meant for the user or a pipe always go to stdout | decided |
| Dry-run is built in | every tool gets `--dry-run`; mutating runners print the command and skip it; read-only runners still run | decided |
| Stable names | the functions tools already call keep their names, so adopting this package is an import change plus a mechanical rename (see [`<terminal-interface>/design-plan/adopting.md`](adopting.md)) | decided |
| One vocabulary | params: a container of options, named by what it is for, e.g. `RunParams` for one run of a tool; a tool: one command line tool, described by `Tool` | decided |
| Light to install | one third-party dependency (`rich`), so it installs on a fresh machine through `uv` alone | decided |

---

## Index

| Note | Covers |
|---|---|
| [`<terminal-interface>/design-plan/shell_interface.md`](shell_interface.md) | run params, output functions, themes, command runners, timestamps, and the persistent record |
| [`<terminal-interface>/design-plan/cli_builder.md`](cli_builder.md) | subcommand descriptions, the tool, flags, grouped help, and the entry point |
| [`<terminal-interface>/design-plan/adopting.md`](adopting.md) | how an existing tool moves onto this package, and how it pins a version |

---

## Project Layout

```text
TerminalInterface/
├── pyproject.toml  # one dependency: rich
├── README.md
├── design-plan/  # these notes
├── src/
│   └── heimdall/
│       ├── _terminal_output.py  # private core: palette, themes, consoles, the active run, timestamps, emit and record
│       ├── shell_interface.py  # run params, output functions, command runners
│       └── cli_builder.py  # subcommand interface and grouped help
└── utests/
```

| Decision | Detail | State |
|---|---|---|
| Package name | `heimdall`, so imports read `from heimdall import shell_interface` | decided |
| Python | `>=3.11`, the oldest version any planned user declares; tests run on 3.11 and 3.14 | decided |
| Module names | `shell_interface` keeps the name tools already import | decided |
| Private core | `_terminal_output` holds everything both public modules share, so a later message layer can be added as its own module on the same palette, consoles, and record without touching `shell_interface` | decided |
| First version | the existing terminal layer, generalised in three places, plus the additions described in the module notes: runners named for what happens to their output, `cwd` on every runner, `query_cmd_and_capture_outcome`, quoted command printing, timestamps, and the persistent record | decided |
