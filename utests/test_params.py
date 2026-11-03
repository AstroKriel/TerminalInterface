## { U-TEST

##
## === DEPENDENCIES
##

## stdlib
import argparse
import unittest

## local
from huginn import params

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

    def test_fields_fill_from_flags_of_the_same_name(
        self,
    ) -> None:
        parsed_args = argparse.Namespace(
            dry_run=True,
            hide_actions=False,
            cmd="go",
        )
        self.assertEqual(
            params.ToolParams.from_parsed_args(parsed_args),
            params.ToolParams(dry_run=True),
        )

    def test_field_with_no_flag_raises(
        self,
    ) -> None:
        parsed_args = argparse.Namespace(dry_run=False)
        with self.assertRaises(AttributeError):
            params.ToolParams.from_parsed_args(parsed_args)


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
