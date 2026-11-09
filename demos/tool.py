## { SCRIPT
"""
A small command line tool built on huginn: its cmds, a cmd flag, a prompt, and the built-in flags.

Try:
    uv run python demos/tool.py --help
    uv run python demos/tool.py status
    uv run python demos/tool.py --dry-run clean
    uv run python demos/tool.py --hide-actions clean --keep-cache

Each run is also logged to `~/.huginn_logs/huginn_demo.log`, except dry runs.
"""

##
## === DEPENDENCIES
##

## local
from huginn import cmd_args, manage_cli, manage_log, manage_shell

##
## === CMDS
##


def show_status() -> None:
    manage_log.log_task("checking the workspace")
    workspace_name = manage_shell.query_cmd_and_capture_output(cmd_parts=["echo", "demo-workspace"])
    manage_log.log_outcome(
        "workspace found",
        status=manage_log.OutcomeStatus.SUCCESS,
        values={"name": workspace_name},
    )


def clean(
    *,
    keep_cache: bool,
) -> None:
    manage_log.log_task("cleaning the workspace")
    clean_is_confirmed = manage_log.ask(
        "remove the build files?",
        input_value_type=cmd_args.InputValueTypes.YES_OR_NO,
    )
    if not clean_is_confirmed:
        manage_log.log_outcome("nothing removed", status=manage_log.OutcomeStatus.SKIPPED)
        return
    manage_shell.run_cmd_and_show_output(cmd_parts=["echo", "removing build/"])
    if keep_cache:
        manage_log.log_note("keeping the cache, as asked")
    else:
        manage_shell.run_cmd_and_show_output(cmd_parts=["echo", "removing cache/"])
    manage_log.log_outcome("workspace cleaned", status=manage_log.OutcomeStatus.SUCCESS)


##
## === TOOL
##

COMMAND_LINE_TOOL = manage_cli.CommandLineTool(
    name="huginn_demo",
    description="a small tool that shows what huginn does",
    cmd_groups=[
        manage_cli.CommandGroup(
            title="Inspecting",
            cmds=[
                manage_cli.Command(
                    name="status",
                    description="show the state of the workspace",
                    fn=show_status,
                ),
            ],
        ),
        manage_cli.CommandGroup(
            title="Changing",
            cmds=[
                manage_cli.Command(
                    name="clean",
                    description="remove the build files, after asking",
                    fn=clean,
                    args=[
                        cmd_args.FlagArgument(
                            long_arg_name="keep-cache",
                            description="leave the cache in place",
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
