## { U-TEST

##
## === DEPENDENCIES
##

## stdlib
import argparse
import dataclasses
import unittest

## local
from huginn import params

##
## === HELPERS
##


@dataclasses.dataclass(frozen=True)
class _ExampleToolParams(params.ToolParams):
    allow_dirty: bool = False


##
## === TEST SUITE
##


class TestToolParams_Defaults(unittest.TestCase):

    def test_every_flag_is_off(
        self,
    ) -> None:
        tool_params = params.ToolParams()
        self.assertFalse(tool_params.dry_run)
        self.assertFalse(tool_params.hide_actions)


class TestToolParams_FromParsedArguments(unittest.TestCase):

    def test_subclass_fields_fill_from_flags_of_the_same_name(
        self,
    ) -> None:
        parsed_args = argparse.Namespace(
            dry_run=True,
            hide_actions=False,
            allow_dirty=True,
            cmd="go",
        )
        self.assertEqual(
            _ExampleToolParams.from_parsed_args(parsed_args),
            _ExampleToolParams(
                dry_run=True,
                allow_dirty=True,
            ),
        )

    def test_field_with_no_flag_raises(
        self,
    ) -> None:
        parsed_args = argparse.Namespace(
            dry_run=False,
            hide_actions=False,
        )
        with self.assertRaises(AttributeError):
            _ExampleToolParams.from_parsed_args(parsed_args)


class TestOutputParams_Defaults(unittest.TestCase):

    def test_no_time_stamps_and_no_log_file(
        self,
    ) -> None:
        output_params = params.OutputParams()
        self.assertFalse(output_params.show_time_stamps)
        self.assertIsNone(output_params.log_file_path)


##
## === ENTRY POINT
##

if __name__ == "__main__":
    unittest.main()

## } U-TEST
