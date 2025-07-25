# tests/test_integration.py
import pytest
from pathlib import Path
import sys
import requests
import os

# Add the root project directory to the path so we can import Solve
sys.path.insert(0, str(Path(__file__).parent.parent))
import Solve

# --- Test Markers ---
pytestmark = pytest.mark.integration

# --- Fixtures for Real Environment ---
@pytest.fixture(scope="module")
def real_config():
    """Loads the real config.ini file. Skips tests if not found."""
    config_path = Path(__file__).parent.parent / "config.ini"
    if not config_path.exists():
        pytest.skip("config.ini not found, skipping integration tests.")
    return Solve.load_config(config_path)

@pytest.fixture(scope="module")
def scip_exe(real_config):
    """Gets the SCIP executable path from the config. Skips if not found."""
    try:
        return real_config.get("Paths", "scip_solver_exe")
    except Exception:
        pytest.skip("scip_solver_exe not found in config.ini. Skipping SCIP tests.")

@pytest.fixture(scope="module")
def highs_exe(real_config):
    """Gets the HiGHS executable path from the config. Skips if not found."""
    try:
        return real_config.get("Paths", "highs_solver_exe")
    except Exception:
        pytest.skip("highs_solver_exe not found in config.ini. Skipping HiGHS tests.")

@pytest.fixture(scope="module")
def cuopt_url(real_config):
    """Gets the cuOpt server URL and checks if it's live. Skips if not."""
    try:
        url = real_config.get("cuOpt", "server_url")
        # Use a health check endpoint if available, otherwise use the main URL
        health_url = url.replace("/solve_mps", "/health")
        requests.get(health_url, timeout=3)
        return url
    except (requests.exceptions.RequestException, KeyError):
        pytest.skip("cuOpt server not running or server_url not in config.ini. Skipping cuOpt tests.")

@pytest.fixture
def example_mps_file(real_config):
    """Gets the example mps path from the config. Skips if not found."""
    try:
        return real_config.get("Paths", "example_mps_path")
    except Exception:
        pytest.skip("example_mps_path not found in config.ini. Skipping test.")

# --- Integration Tests ---
def test_scip_solve(scip_exe, example_mps_file):
    """
    Tests the full 'solve-scip' workflow with the real SCIP executable.
    """
    # Arrange
    output_sol_file = Path(os.path.dirname(example_mps_file)) / "solution.sol"

    # Act
    Solve.execute_scip_command(
        scip_exe_path=Path(scip_exe),
        input_model_path=example_mps_file,
        output_path=output_sol_file,
        solve_type="solve"
    )

    # Assert
    assert output_sol_file.exists(), "SCIP did not create the solution file."

    solution_text = output_sol_file.read_text()
    assert "optimal solution found" in solution_text
    # Check for the known objective value of our sample model
    assert "objective value:" in solution_text

def test_highs_solve(highs_exe, example_mps_file):
    """
    Tests the full 'solve-highs' workflow with the real HiGHS executable.
    """
    # Arrange
    output_sol_file = Path(os.path.dirname(example_mps_file)) / "solution.sol"

    # Act
    Solve.execute_highs_command(
        highs_exe_path=Path(highs_exe),
        input_model_path=example_mps_file,
        output_path=output_sol_file
    )

    # Assert
    assert output_sol_file.exists(), "HiGHS did not create the solution file."

    solution_text = output_sol_file.read_text()
    assert "Optimal" in solution_text
    assert "Objective" in solution_text

def test_cuopt_solve(cuopt_url, example_mps_file, capsys):
    """
    Tests the 'solve-cuopt' workflow with a real, running cuOpt server.
    """
    # Act
    Solve.solve_with_cuopt_server(
        mps_file_path=example_mps_file,
        server_url=cuopt_url
    )

    # Assert
    captured = capsys.readouterr()
    assert "Status Code: 200" in captured.out
    # A real cuOpt success response will contain these keys
    assert '"vars"' in captured.out

def test_presolve_and_solve_full_integration(scip_exe, cuopt_url, example_mps_file, capsys):
    """
    Tests the end-to-end 'presolve-and-solve' workflow with real SCIP and cuOpt.
    """
    # Arrange
    presolved_file = Path(os.path.dirname(example_mps_file)) / "presolved.mps"

    # --- Act & Assert: Step 1 (Presolve with SCIP) ---
    print("\n--- Integration Test: Step 1: Presolving with SCIP ---")
    Solve.execute_scip_command(
        scip_exe_path=Path(scip_exe),
        input_model_path=example_mps_file,
        output_path=presolved_file,
        solve_type="presolve"
    )
    assert presolved_file.exists(), "SCIP did not create the presolved file."

    # --- Act & Assert: Step 2 (Solve with cuOpt) ---
    print("\n--- Integration Test: Step 2: Solving with cuOpt ---")
    Solve.solve_with_cuopt_server(
        mps_file_path=presolved_file,
        server_url=cuopt_url
    )
    captured_cuopt = capsys.readouterr()
    assert "Status Code: 200" in captured_cuopt.out