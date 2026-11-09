# TerminalInterface

Shared building blocks for command line tools, as the `huginn` package. A tool supplies the text and picks what kind of message it is; huginn handles the styling.

It does three jobs:

1. Output: every message goes through one function per message type, e.g. `manage_log.log_task`, and each type has its own symbol and colour.
2. Running commands: every shell command is shown in full before it runs; a command that changes the system is skipped in a dry run.
3. Building the interface: a tool describes its cmds once and gets argument parsing, grouped help, and the built-in flags `--dry-run` and `--hide-actions`.

## Example

```python
from huginn import cmd_args, manage_cli, manage_log, manage_shell


def pull(
    *,
    rebase: bool,
) -> None:
    manage_log.log_task("updating the working tree")
    cmd_parts = ["git", "pull"]
    if rebase:
        cmd_parts.append("--rebase")
    manage_shell.run_cmd_and_show_output(cmd_parts=cmd_parts)
    manage_log.log_outcome("up to date", status=manage_log.OutcomeStatus.SUCCESS)


COMMAND_LINE_TOOL = manage_cli.CommandLineTool(
    name="example_tool",
    description="an example tool",
    cmd_groups=[
        manage_cli.CommandGroup(
            title="Syncing",
            cmds=[
                manage_cli.Command(
                    name="pull",
                    description="update the working tree from its remote",
                    fn=pull,
                    args=[
                        cmd_args.FlagArgument(
                            long_arg_name="rebase",
                            description="rebase instead of merging",
                        ),
                    ],
                ),
            ],
        ),
    ],
)


def main() -> None:
    log_file_path = manage_log.get_home_log_file_path(tool_name="example_tool")
    manage_log.set_log_file_path(log_file_path=log_file_path)
    manage_cli.run_cli(command_line_tool=COMMAND_LINE_TOOL)
```

```text
$ example_tool --dry-run pull --rebase
● updating the working tree
→ skipped: git pull --rebase
↪ success: up to date
```

Every tool and script sets its log file path before its first message: a path to log there, or `None` to log nothing. A message before that raises `LogFileError`. `get_home_log_file_path` gives `~/.huginn_logs/<tool name>.log`; a job script can instead pass a folder of its own, so parallel jobs never share one file.

`example_tool --help` lists the cmds, the built-in flags, and a style legend for reading the output.

## Demos

[`demos/`](demos/) has two runnable examples: `demo.py` is a small command line tool that keeps dated backups of one file, `/tmp/huginn_demo/notes.txt`, so every cmd can be tried with `--dry-run` and `--hide-actions`; `gallery.py` shows every message type once. Each one says how to run it at the top.

## Design

The design notes are in [`design-plan/`](design-plan/README.md).
