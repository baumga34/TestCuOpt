import pytest
from unittest.mock import patch
from pathlib import Path
import configparser
import Solve

# --- Test Setup ---

@pytest.fixture
def mock_config():
    """A pytest fixture to create a reusable mock config object."""
    config = configparser.ConfigParser()
    config.add_section("Paths")
    config.set("Paths", "scip_solver_exe", "dummy/path/to/scip.exe")
    config.set("Paths", "highs_solver_exe", "dummy/path/to/highs.exe")
    config.add_section("cuOpt")
    config.set("cuOpt", "server_url", "http://dummy-url:8000/solve_mps")
    return config

# --- Test Cases ---

@patch('Solve.solve_with_cuopt_server')
@patch('Solve.load_config')
def test_main_solve_cuopt_command(mock_load_config, mock_solve_cuopt, monkeypatch, mock_config):
    """
    Tests if the 'solve-cuopt' command correctly calls the cuOpt solver function.
    """
    # Arrange: Set up the mocks and command-line arguments
    mock_load_config.return_value = mock_config
    test_args = ['Solve.py', 'solve-cuopt', 'my_model.mps']
    monkeypatch.setattr('sys.argv', test_args)

    # Act: Run the main function from the script
    Solve.main()

    # Assert: Verify that our mocked functions were called with the correct parameters
    mock_load_config.assert_called_once()
    mock_solve_cuopt.assert_called_once_with(
        Path('my_model.mps'),
        'http://dummy-url:8000/solve_mps'
    )

@patch('Solve.execute_scip_command')
@patch('Solve.load_config')
def test_main_solve_scip_command(mock_load_config, mock_execute_scip, monkeypatch, mock_config):
    """
    Tests if the 'solve-scip' command correctly calls the SCIP execution function.
    """
    # Arrange
    mock_load_config.return_value = mock_config
    test_args = ['Solve.py', 'solve-scip', 'my_model.mps', 'my_solution.sol']
    monkeypatch.setattr('sys.argv', test_args)

    # Act
    Solve.main()

    # Assert
    mock_load_config.assert_called_once()
    mock_execute_scip.assert_called_once_with(
        Path('dummy/path/to/scip.exe'),
        Path('my_model.mps'),
        Path('my_solution.sol'),
        'solve'
    )

@patch('Solve.execute_highs_command')
@patch('Solve.load_config')
def test_main_solve_highs_command(mock_load_config, mock_execute_highs, monkeypatch, mock_config):
    """
    Tests if the 'solve-highs' command correctly calls the HiGHS execution function.
    """
    # Arrange
    mock_load_config.return_value = mock_config
    test_args = ['Solve.py', 'solve-highs', 'my_model.mps', 'my_solution.sol']
    monkeypatch.setattr('sys.argv', test_args)

    # Act
    Solve.main()

    # Assert
    mock_load_config.assert_called_once()
    mock_execute_highs.assert_called_once_with(
        Path('dummy/path/to/highs.exe'),
        Path('my_model.mps'),
        Path('my_solution.sol'),
        'solve'
    )

@patch('pathlib.Path.exists', return_value=True) # Assume the presolved file is created
@patch('Solve.solve_with_cuopt_server')
@patch('Solve.execute_scip_command')
@patch('Solve.load_config')
def test_main_presolve_and_solve_command(mock_load_config, mock_execute_scip, mock_solve_cuopt, mock_path_exists, monkeypatch, mock_config):
    """
    Tests the 'presolve-and-solve' two-step workflow.
    """
    # Arrange
    mock_load_config.return_value = mock_config
    test_args = ['Solve.py', 'presolve-and-solve', 'my_model.mps', 'presolved.mps']
    monkeypatch.setattr('sys.argv', test_args)

    # Act
    Solve.main()

    # Assert
    # 1. Check that SCIP was called first for presolving
    mock_execute_scip.assert_called_once_with(
        Path('dummy/path/to/scip.exe'),
        Path('my_model.mps'),
        Path('presolved.mps'),
        'presolve'
    )

    # 2. Check that the script verified the existence of the output file
    mock_path_exists.assert_called_with()

    # 3. Check that cuOpt was called second with the presolved file
    mock_solve_cuopt.assert_called_once_with(
        Path('presolved.mps'),
        'http://dummy-url:8000/solve_mps'
    )

@patch('Solve.load_config', side_effect=FileNotFoundError("Config not found"))
def test_main_config_error_handling(mock_load_config, monkeypatch, capsys):
    """
    Tests that a configuration error is caught and a message is printed.
    """
    # Arrange
    test_args = ['Solve.py', 'solve-cuopt', 'my_model.mps']
    monkeypatch.setattr('sys.argv', test_args)

    # Act
    Solve.main()

    # Assert
    captured = capsys.readouterr() # Capture print() output
    assert "Configuration Error: Config not found" in captured.out
