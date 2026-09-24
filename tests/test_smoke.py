import alarmclock


def test_package_has_version():
    assert alarmclock.__version__ == "0.1.0"


def test_cli_main_runs():
    from alarmclock.cli import main

    assert main([]) == 0
