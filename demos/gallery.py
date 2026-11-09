## { SCRIPT
"""
Every message type once, in the order of the style legend, for judging the visuals side by side.

Run it with `uv run gallery.py`; it asks one question, so pipe an answer in to skip it, e.g.
`echo y | uv run gallery.py`. Nothing is logged, and the one folder it makes, `/tmp/huginn_gallery`, is
removed again at the end.
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
    gallery_dir = "/tmp/huginn_gallery"
    manage_log.set_log_file_path(log_file_path=None)
    manage_log.log_task("start of a task")
    manage_log.log_note("note about the work")
    manage_log.ask(
        "question for the user?",
        input_value_type=cmd_args.InputValueTypes.YES_OR_NO,
    )
    manage_log.log_task(
        "actions: inspections run and their output is captured; changes show their output",
        prepend_empty_line=True,
    )
    manage_shell.query_cmd_and_discard_output(cmd_parts=["test", "-d", gallery_dir])
    kernel_name = manage_shell.query_cmd_and_capture_output(cmd_parts=["uname", "-s"])
    manage_shell.run_cmd_and_show_output(cmd_parts=["mkdir", "-p", gallery_dir])
    ## a tool gets dry-run from `--dry-run`; the gallery turns it on directly to show a skipped change
    _manage_output.set_built_in_params(_manage_output.BuiltInParams(dry_run=True))
    manage_shell.run_cmd_and_show_output(cmd_parts=["rm", "-r", gallery_dir])
    _manage_output.set_built_in_params(_manage_output.BuiltInParams(dry_run=False))
    manage_shell.run_cmd_and_show_output(cmd_parts=["rm", "-r", gallery_dir])
    manage_log.log_task(
        "outcomes: one per status, then items and a return",
        prepend_empty_line=True,
    )
    for outcome_status in manage_log.OutcomeStatus:
        manage_log.log_outcome(
            outcome_status.value.description,
            status=outcome_status,
        )
    manage_log.log_outcome(
        "outcome with items",
        status=manage_log.OutcomeStatus.SUCCESS,
        items={
            "kernel": kernel_name,
            "path": gallery_dir,
        },
    )
    manage_log.log_note(
        "note with items",
        items={
            "resolution": 64,
            "solver": "hll",
        },
    )
    manage_log.log_return("what the tool returns, plain on stdout")


##
## === ENTRY POINT
##

if __name__ == "__main__":
    main()

## } SCRIPT
