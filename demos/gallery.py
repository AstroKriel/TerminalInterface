## { SCRIPT
"""
Every message type once, in the order of the style legend, for judging the visuals side by side.

Run it with `uv run python demos/gallery.py`; it asks one question, so pipe an answer in to skip it, e.g.
`echo y | uv run python demos/gallery.py`. Nothing is logged.
"""

##
## === DEPENDENCIES
##

## local
from huginn import _manage_output, cmd_args, manage_log, manage_shell

##
## === PROGRAM MAIN
##


def main() -> None:
    manage_log.set_log_file_path(log_file_path=None)
    manage_log.log_task("start of a task")
    manage_log.log_note("note about the work")
    manage_log.ask(
        "question for the user?",
        input_value_type=cmd_args.InputValueTypes.YES_OR_NO,
    )
    manage_shell.run_cmd_and_show_output(cmd_parts=["echo", "change to the system"])
    manage_shell.query_cmd_and_capture_output(cmd_parts=["echo", "inspection of the system"])
    ## a tool gets dry-run from `--dry-run`; the gallery turns it on directly to show a skipped change
    _manage_output.set_built_in_params(_manage_output.BuiltInParams(dry_run=True))
    manage_shell.run_cmd_and_show_output(cmd_parts=["echo", "change skipped in a dry run"])
    _manage_output.set_built_in_params(_manage_output.BuiltInParams(dry_run=False))
    for outcome_status in manage_log.OutcomeStatus:
        manage_log.log_outcome(
            outcome_status.value.description,
            status=outcome_status,
        )
    manage_log.log_outcome(
        "outcome with values",
        status=manage_log.OutcomeStatus.SUCCESS,
        values={
            "path": "/data/sim_a/output.json",
            "num_files": 3,
        },
    )
    manage_log.log_note(
        "note with values",
        values={
            "resolution": 64,
            "solver": "hll",
        },
    )
    manage_log.log_result("result, printed plain on stdout")


##
## === ENTRY POINT
##

if __name__ == "__main__":
    main()

## } SCRIPT
