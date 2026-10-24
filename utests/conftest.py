## { U-TEST

##
## === DEPENDENCIES
##

## stdlib
from collections.abc import Iterator

## third-party
import pytest

## local
from heimdall import shell_interface

##
## === FIXTURES
##


@pytest.fixture(autouse=True)
def reset_output_settings() -> Iterator[None]:
    shell_interface.configure_output(tool_name="")
    yield
    shell_interface.configure_output(tool_name="")


## } U-TEST
