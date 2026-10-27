# manage_log

Design notes for `heimdall.manage_log`: the output functions, their message types, and the output settings for one run.

---

## Message Types

The model has three concepts: a task (a stage of the work, announced in words before it starts), an action (something done to the system, either changing it or only inspecting it, shown before it happens), and an outcome (how a task or action ended, with a status, optionally carrying a value or a result).

The concepts are layered: each base concept has its own kinds.

```text
task                 a stage of the work, announced in words before it starts
action               something done to the system, shown before it happens
├── change           changes the system; skipped in dry-run
└── inspection       only reads the system; always runs
outcome              how a task or action ended, reported afterwards
├── status           success | warning | skipped | failure
└── content          optional: a value (what an action produced) or a result (for the user, on stdout)
```

The symbol says which concept a line is (open circle: task; hooked arrow: note; right arrow: action; closed circle or middle dot: outcome) and the colour says which type or status. The vocabulary follows the jormi log manager: `MessageStyle` (`colour`, `symbol`, `description`), `Colour`, `Symbol`, notes, and an `ERROR` status beside `FAILURE`. Each base concept has its facets as enums of `MessageStyle` in the private core `_manage_terminal`: `TASK_STYLE`; `NOTE_STYLE`; `Action` (`CHANGE`, `INSPECTION`); `OutcomeStatus` (`SUCCESS`, `WARNING`, `SKIPPED`, `FAILURE`, `ERROR`); `OutcomeContent` (`VALUE`, `RESULT`). There are no named combinations: a change skipped in dry-run is drawn at render time with the change symbol in the skipped colour, and the legend lists only the building blocks. `MESSAGE_GROUPS` lists everything by concept, and the help legend is generated from it, so the legend cannot drift from the output. Lines are drawn by `render_line` and written by `write_line`.

| Concept | Facet | Value | Symbol | Colour | State |
|---|---|---|---|---|---|
| task | | | open circle | white | decided |
| note | | | hooked arrow | white | decided |
| action | type | change | right arrow | blue | decided |
| action | type | inspection | right arrow | grey | decided |
| outcome | status | success | closed circle | green | decided |
| outcome | status | warning | closed circle | yellow | decided |
| outcome | status | skipped | closed circle | orange | decided |
| outcome | status | failure that does not end the run | closed circle | red | decided |
| outcome | status | error that ends the run | closed circle | red | decided |
| outcome | content | value an action produced | middle dot | grey | decided |
| outcome | content | result | none | none: plain text on stdout, never timestamped or wrapped, so a pipe gets clean data | decided |

An inspection exists to produce a value; a change exists to alter the system and may produce a value along the way, e.g. the path of a directory it created. In dry-run a change is skipped, so a value it would have produced is unknown: anything that depends on that value reports a skipped outcome instead of carrying on with a placeholder. State: decided.

> **Note:** a richer message layer, with titled blocks and notes, is expected to move into this package later. These message types and statuses are its first layer, not a closed set.

---

## Output Functions

| Function | Prints | Stream | State |
|---|---|---|---|
| `log_note(text)` | a note about the work, neither a task nor an outcome | narration | decided |
| `log_task(text)` | a task starting | narration | decided |
| `log_outcome(text, *, status)` | how a task or action ended; `status` is required, never assumed | narration | decided |
| `log_value(*, name, value)` | a value an action produced, as `name = value` | narration | decided |
| `log_result(text)` | a result for the user or a pipe | stdout | decided |
| `exit_with_error(text, *, exit_code=1)` | an error outcome, then exits with `exit_code` | narration | decided |
| `escape_markup(text)` | nothing; returns text that prints exactly as written | N/A | decided |

`OutcomeStatus` is available as `manage_log.OutcomeStatus`.

Narration always goes to stderr; whoever runs the tool can merge the two streams, e.g. with `2>&1`. Message text is rich markup, so a caller can style it; anything a function adds itself (commands, resolved values, timestamps) is escaped. Text from outside the tool, such as a news title or a file name, goes through `escape_markup` first, so square brackets in it print as written.

---

## Output for One Run

The entry point sets these once per process, from the fields of the `CommandLineTool`. Timestamps and the log serve tools that keep a history of what they did to a machine.

| Feature | Detail | State |
|---|---|---|
| Timestamps | a `YYYY-MM-DD HH:MM:SS` prefix on every line printed to the terminal, from `datetime.now().isoformat(sep=" ", timespec="seconds")` | decided |
| Log | every line printed, steps and commands included, is also appended to the file at `log_path`, as plain text without colour markup | decided |
| Log format | `[<timestamp>] <line>`, one line per entry, always timestamped whether or not the terminal shows timestamps | decided |
| Log in dry-run | nothing is written: the log is a history of what was done to the machine, and a dry-run does nothing | decided |

Timestamps and the log are off unless a tool turns them on, so tools that do not need them see no change. A script that never calls the entry point gets the defaults: no timestamps, no log.
