## { SCRIPT
"""
A job-style script built on huginn: it logs to a folder it is given, carries on past a failed command, and ends
with a result on stdout.

Try:
    uv run python demos/script.py /tmp/huginn_demo
    cat /tmp/huginn_demo/script.log

Run it twice: the log keeps both runs, each starting with the command that ran it.
"""

##
## === DEPENDENCIES
##

## stdlib
import argparse
from pathlib import Path

## local
from huginn import manage_log, manage_shell

##
## === PROGRAM MAIN
##


def main() -> None:
    arg_parser = argparse.ArgumentParser(description="process a few sims, logging to the given folder")
    arg_parser.add_argument("output_dir", type=Path)
    parsed_args = arg_parser.parse_args()
    output_dir: Path = parsed_args.output_dir
    manage_log.set_log_file_path(log_file_path=output_dir / "script.log")
    manage_log.log_task("processing sims")
    sim_names = ["sim_a", "sim_b", "sim_c"]
    processed_sim_names: list[str] = []
    for sim_name in sim_names:
        manage_log.log_task(f"processing {sim_name}")
        ## `false` stands in for a step that fails on one sim
        if sim_name == "sim_b":
            cmd_parts = ["false"]
        else:
            cmd_parts = ["echo", f"processed {sim_name}"]
        cmd_has_succeeded = manage_shell.run_cmd_and_show_output(
            cmd_parts=cmd_parts,
            raise_error=False,
        )
        if not cmd_has_succeeded:
            manage_log.log_outcome(
                f"skipped {sim_name}: the step failed",
                status=manage_log.OutcomeStatus.SKIPPED,
            )
            continue
        processed_sim_names.append(sim_name)
        manage_log.log_outcome(
            f"processed {sim_name}",
            status=manage_log.OutcomeStatus.SUCCESS,
            values={"output": output_dir / f"{sim_name}.json"},
        )
    manage_log.log_result(f"processed {len(processed_sim_names)} of {len(sim_names)} sims")


##
## === ENTRY POINT
##

if __name__ == "__main__":
    main()

## } SCRIPT
