## { SCRIPT
"""
A small command line tool built on huginn: it keeps dated backups of a notes file in `/tmp/huginn_demo/`.

Walk through it in order, and try any step with `--dry-run` or `--hide-actions` first:
    uv run demo_tool.py --help
    uv run demo_tool.py create
    uv run demo_tool.py backup
    uv run demo_tool.py create
    uv run demo_tool.py backup
    uv run demo_tool.py status
    uv run demo_tool.py prune --keep 1
    uv run demo_tool.py remove

Every run is logged to `~/.huginn_logs/huginn_demo.log`, except dry runs. Nothing outside `/tmp/huginn_demo/` is
touched.
"""

##
## === DEPENDENCIES
##

## stdlib
import datetime
from pathlib import Path

## local
from huginn import cmd_args, manage_cli, manage_log, manage_shell

##
## === NOTES FILE
##

DEMO_DIR = Path("/tmp/huginn_demo")
NOTES_FILE_PATH = DEMO_DIR / "notes.txt"


def _path_exists(
    *,
    path: Path,
    test_flag: str,
) -> bool:
    exit_code = manage_shell.query_cmd_and_discard_output(cmd_parts=["test", test_flag, str(path)])
    return exit_code == 0


def _list_backup_names() -> list[str]:
    """The backups, oldest first; a backup is named `notes.<date>_<time>.txt`, so name order is time order."""
    dir_listing = manage_shell.query_cmd_and_capture_output(
        cmd_parts=["ls", str(DEMO_DIR)],
        raise_error=False,
    )
    backup_names = [
        _file_name for _file_name in dir_listing.split()
        if _file_name.startswith("notes.") and (_file_name != NOTES_FILE_PATH.name)
    ]
    return sorted(backup_names)


##
## === CMDS
##


def create() -> None:
    manage_log.log_task("creating the notes file")
    if _path_exists(
            path=NOTES_FILE_PATH,
            test_flag="-f",
    ):
        manage_log.log_outcome(
            "the notes file already exists",
            status=manage_log.OutcomeStatus.SKIPPED,
            items={"path": NOTES_FILE_PATH},
        )
        return
    manage_shell.run_cmd_and_show_output(cmd_parts=["mkdir", "-p", str(DEMO_DIR)])
    manage_shell.run_cmd_and_show_output(cmd_parts=["touch", str(NOTES_FILE_PATH)])
    manage_log.log_outcome(
        "created the notes file",
        status=manage_log.OutcomeStatus.SUCCESS,
        items={"path": NOTES_FILE_PATH},
    )


def show_status() -> None:
    manage_log.log_task("checking the notes file and its backups")
    if _path_exists(
            path=NOTES_FILE_PATH,
            test_flag="-f",
    ):
        notes_file_state = "exists"
    else:
        notes_file_state = "missing"
    backup_names = _list_backup_names()
    if len(backup_names) == 0:
        latest_backup_name = "none"
    else:
        latest_backup_name = backup_names[-1]
    manage_log.log_outcome(
        "checked the notes file",
        status=manage_log.OutcomeStatus.SUCCESS,
        items={
            "notes file": notes_file_state,
            "backups": len(backup_names),
            "latest backup": latest_backup_name,
        },
    )


def backup() -> None:
    manage_log.log_task("backing up the notes file")
    if not _path_exists(
            path=NOTES_FILE_PATH,
            test_flag="-f",
    ):
        manage_log.log_outcome(
            "there is no notes file to back up; run `demo_tool.py create` first",
            status=manage_log.OutcomeStatus.SKIPPED,
        )
        return
    time_stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_path = DEMO_DIR / f"notes.{time_stamp}.txt"
    manage_shell.run_cmd_and_show_output(cmd_parts=["mv", str(NOTES_FILE_PATH), str(backup_path)])
    manage_log.log_outcome(
        "backed up the notes file",
        status=manage_log.OutcomeStatus.SUCCESS,
        items={"backup": backup_path},
    )
    manage_log.log_return(str(backup_path))


def prune(
    *,
    keep: int,
) -> None:
    manage_log.log_task(f"pruning the backups, keeping the newest {keep}")
    if keep < 0:
        manage_log.exit_with_error(f"`--keep` must be 0 or more; got `{keep}`.")
    backup_names = _list_backup_names()
    num_backups_to_delete = max(len(backup_names) - keep, 0)
    if num_backups_to_delete == 0:
        manage_log.log_outcome(
            "there are no old backups to delete",
            status=manage_log.OutcomeStatus.SKIPPED,
            items={"backups": len(backup_names)},
        )
        return
    delete_is_confirmed = manage_log.ask(
        f"delete the oldest {num_backups_to_delete} of {len(backup_names)} backups?",
        input_value_type=cmd_args.InputValueTypes.YES_OR_NO,
    )
    if not delete_is_confirmed:
        manage_log.log_outcome(
            "no backups deleted",
            status=manage_log.OutcomeStatus.SKIPPED,
        )
        return
    old_backup_paths = [str(DEMO_DIR / _backup_name) for _backup_name in backup_names[:num_backups_to_delete]]
    manage_shell.run_cmd_and_show_output(cmd_parts=["rm", *old_backup_paths])
    manage_log.log_outcome(
        "deleted the old backups",
        status=manage_log.OutcomeStatus.SUCCESS,
        items={
            "deleted": num_backups_to_delete,
            "kept": keep,
        },
    )


def remove() -> None:
    manage_log.log_task("removing the notes file and its backups")
    if not _path_exists(
            path=DEMO_DIR,
            test_flag="-d",
    ):
        manage_log.log_outcome(
            "there is nothing to remove",
            status=manage_log.OutcomeStatus.SKIPPED,
        )
        return
    remove_is_confirmed = manage_log.ask(
        f"remove {DEMO_DIR} and everything in it?",
        input_value_type=cmd_args.InputValueTypes.YES_OR_NO,
    )
    if not remove_is_confirmed:
        manage_log.log_outcome(
            "nothing removed",
            status=manage_log.OutcomeStatus.SKIPPED,
        )
        return
    manage_shell.run_cmd_and_show_output(cmd_parts=["rm", "-r", str(DEMO_DIR)])
    manage_log.log_outcome(
        "removed the notes file and its backups",
        status=manage_log.OutcomeStatus.SUCCESS,
    )


##
## === TOOL
##

COMMAND_LINE_TOOL = manage_cli.CommandLineTool(
    name="huginn_demo",
    description="a demo of a huginn tool; keeps dated backups of a notes file in /tmp/huginn_demo",
    cmd_groups=[
        manage_cli.CommandGroup(
            title="Set up and tear down",
            cmds=[
                manage_cli.Command(
                    name="create",
                    description="create an empty notes file",
                    fn=create,
                ),
                manage_cli.Command(
                    name="remove",
                    description="remove the notes file and its backups, after asking",
                    fn=remove,
                ),
            ],
        ),
        manage_cli.CommandGroup(
            title="Check",
            cmds=[
                manage_cli.Command(
                    name="status",
                    description="show the notes file and its backups",
                    fn=show_status,
                ),
            ],
        ),
        manage_cli.CommandGroup(
            title="Back up",
            cmds=[
                manage_cli.Command(
                    name="backup",
                    description="rename the notes file with the date and time",
                    fn=backup,
                ),
                manage_cli.Command(
                    name="prune",
                    description="delete the oldest backups, after asking",
                    fn=prune,
                    args=[
                        cmd_args.NamedArgument(
                            long_arg_name="keep",
                            description="how many of the newest backups to keep",
                            input_value_type=cmd_args.InputValueTypes.NUMBER,
                            is_required=True,
                        ),
                    ],
                ),
            ],
        ),
    ],
)

##
## === PROGRAM MAIN
##


def main() -> None:
    log_file_path = manage_log.get_home_log_file_path(tool_name=COMMAND_LINE_TOOL.name)
    manage_log.set_log_file_path(log_file_path=log_file_path)
    manage_cli.run_cli(command_line_tool=COMMAND_LINE_TOOL)


##
## === ENTRY POINT
##

if __name__ == "__main__":
    main()

## } SCRIPT
