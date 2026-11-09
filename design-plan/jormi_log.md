# jormi_log

Design notes for moving the jormi log layer (`jormi.ww_io.manage_log`) onto huginn, so every message a script prints also reaches its log file. The huginn side is in [`<terminal-interface>/design-plan/manage_log.md`](manage_log.md).

---

## Usage

Counts are calls across the scripts and packages that use jormi, demos and tests included.

| jormi function | Calls | What callers use it for |
|---|---|---|
| `log_task` | 43 | a stage of the work starting |
| `log_note` | 36 | a remark about the work |
| `log_outcome` | 29 | how a step ended, with a status |
| `log_action` | 33 | a block: a step that ended, with a status and key-value notes, e.g. `Save wavenumbers` with its path |
| `log_error` | 14 | a block: an error, often logged by library code right before it raises |
| `log_empty_lines` | 10 | blank lines for spacing |
| `log_hint` | 8 | a heads-up about a choice the script made, e.g. falling back to a default or skipping a field |
| `log_context` | 6 | a block: key-value notes, e.g. the parameters of a run |
| `log_section` | 5 | a heading for a whole run or a part of it |
| `log_summary` | 4 | a block: key-value results at the end of a run, e.g. pass or fail per test |
| `log_warning` | 4 | a block: a warning, sometimes with key-value notes |
| `log_alert` | 3 | a notice right before stopping early, e.g. nothing found to do |
| `log_items` | 2 | a block: a numbered list, e.g. the fields available in a snapshot |
| `log_debug` | 1 | demo only |
| `set_block_width_mode` | 87 | every call sets `PRACTICAL`, which lifts the width cap |

---

## Mapping

| jormi | huginn | State |
|---|---|---|
| `log_task`, `log_note`, `log_outcome` | the same functions; a rename of arguments at each call site, e.g. `outcome=ActionOutcome.SUCCESS` becomes `status=OutcomeStatus.SUCCESS` | proposed |
| `log_hint` | `log_note`: a choice the script made is a remark about the work | proposed |
| `log_alert` | `log_outcome` with `SKIPPED` or `WARNING`, whichever the caller means | proposed |
| `log_debug` | dropped: no caller outside the demos | proposed |
| `log_empty_lines` | dropped: spacing is styling, so huginn places blank lines itself, e.g. before a heading | proposed |
| `set_block_width_mode` | dropped: every caller lifts the cap, so huginn never caps the width | proposed |
| `show_time` on every function | dropped: the terminal shows no time stamps, and the log file has them on every line | proposed |
| `log_section` | `log_task`: a heading for a run is a task that covers the whole run | proposed |
| `log_action`, `log_warning`, `log_error` | `log_outcome` with its status, and its notes as `values`; see [Grouped Messages](#grouped-messages) | proposed |
| `log_context`, `log_summary` | `log_note` with its notes as `values` | proposed |
| `log_items` | `log_note` with its items as `values`, numbered from 1 | proposed |

---

## Grouped Messages

Six jormi functions draw a bordered block: a title, a status colour, and key-value notes inside. huginn carries them over as grouped lines, not blocks, so no new function and no width setting is needed. The two options considered:

| Option | Shape | For | Against |
|---|---|---|---|
| Blocks | a bordered panel, as in jormi | familiar; groups the notes visibly | routing and the log file assume one line per message; a panel has to become several plain lines for the log; a panel has a width, which clashes with never wrapping outside a terminal |
| Grouped lines | one message line, then one indented line per note, e.g. `● Save wavenumbers` then `    · path = <path>` | every line routes and logs as now; nothing has a width; reads the same in a pipe as in a terminal | less visual weight than a border |

Grouped lines reuse what huginn has: the first line is a note or an outcome, and each of its `values` is a line in the value style, one indent deeper (see [`<terminal-interface>/design-plan/manage_log.md`](manage_log.md#output-functions)). The jormi blocks were nice to look at, but in use they mostly caused wrapping problems; grouped lines are lighter, and their look can still be iterated on. State: decided.

---

## Library Code

Library code logs through jormi in three ways. Under huginn, a message before a log file path is set raises `LogFileError`, so every script that uses a library that logs sets its log file path first, even to `None`, the same as a tool.

| Pattern | Example | Under huginn | State |
|---|---|---|---|
| Log an error, then raise | a loader logs `Invalid sim_time` and raises `RuntimeError` with the same text | `report_failure` with the wording and the `raise_error` flag of its caller; see below | proposed |
| Warn and carry on | loaded values break a declared property, or a field is skipped | `log_outcome` with `WARNING`, or `log_note` | proposed |
| Report as the job of the function | listing the fields of a snapshot, or the path parameters were saved to | `log_note` or `log_outcome` with `values` | proposed |

A failure is split across three layers, so its wording is written once and its look is decided once:

| Layer | Owns | Example |
|---|---|---|
| script | whether the failure ends the run, with `raise_error` on the call | `snapshot.get_sim_time(raise_error=False)` |
| library | the wording, written once where the failure is found | `Invalid sim_time for field: nan.` |
| huginn | how a failure and an error look, and where each goes | `report_failure(text, *, raise_error)` |

`manage_log.report_failure(text, *, raise_error)` raises an exception carrying `text` when `raise_error` is `True`, and otherwise logs a failure outcome, so the run carries on and the library function returns `None`. A library function that offers the choice takes `raise_error: bool = True` and returns `<type> | None`; one whose callers never carry on just raises. State: proposed.

```python
msg_text = f"Invalid sim_time for field: {sim_time!r}."
manage_log.report_failure(msg_text, raise_error=raise_error)
return None
```

Each meaning keeps one look wherever it comes from:

| Path | Terminal | Log file |
|---|---|---|
| `raise_error=False` | a failure outcome: `● <text>` in red | the same line |
| raised, and nothing catches it | an error outcome, `● error: <text>`, the same as `exit_with_error`, then the traceback | the same error line, then the traceback (see [Uncaught Exceptions](#uncaught-exceptions)) |
| raised, and the caller catches it | whatever the caller reports | the same |

---

## Uncaught Exceptions

An exception that nothing catches ends the run with a traceback on stderr, and the log file stops at the message before it. huginn installs a hook (`sys.excepthook`) that reports it as an error outcome, `● error: <exception message>`, in the same style as `exit_with_error`, then prints the traceback. The log file gets the error line, then each line of the traceback, indented under it and time-stamped like every other line, so the log keeps why each run crashed even after the piped output of that run is gone. The hook is installed when the log file path is set, so a tool and a script get it the same way. State: proposed.

---

## Out of Scope

`jormi.ww_io.manage_shell` overlaps with `huginn.manage_shell`, and is a separate move.
