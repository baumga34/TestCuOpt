import subprocess
import os
import configparser
import requests
import json
import argparse
from pathlib import Path

# --- Constants ---
CONFIG_FILE = "config.ini"


# --- Configuration Handling ---

def load_config(config_path: Path) -> configparser.ConfigParser:
    """
    Loads the configuration from the specified .ini file.

    Args:
        config_path: The path to the configuration file.

    Returns:
        A ConfigParser object with the loaded configuration.

    Raises:
        FileNotFoundError: If the configuration file does not exist.
    """
    if not config_path.exists():
        raise FileNotFoundError(
            f"Configuration file not found at '{config_path}'. "
            "Please create it based on the repository's example."
        )
    config = configparser.ConfigParser()
    config.read(config_path)
    return config


# --- Core Solver Functions ---

def solve_with_cuopt_server(
        mps_file_path: Path, server_url: str, time_limit: float = 60.0, batch_size: int = 1
):
    """
    Sends an MPS file to a running cuOpt server for solving.

    Args:
        mps_file_path: Path to the .mps model file.
        server_url: The URL of the running cuOpt server.
        time_limit: The time limit for the solver in seconds.
        batch_size: The batch size for the solver.
    """
    """if not os.path.exists(mps_file_path):
        print(f"Error: Input file not found at '{mps_file_path}'")
        return"""

    print(f"-> Sending '{mps_file_path}' to cuOpt server at {server_url}...")

    try:
        response = requests.post(
            server_url,
            json={
                "file_name": str(Path(mps_file_path).name),
                "time_limit": time_limit,
                "batch_size": batch_size,
            },
            timeout=time_limit + 30,  # Add a buffer to the request timeout
        )
        response.raise_for_status()  # Raises an HTTPError for bad responses (4xx or 5xx)

        print(f"Status Code: {response.status_code}")
        print("Response JSON:")
        print(json.dumps(response.json(), indent=2))

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while communicating with the cuOpt server: {e}")
    except json.JSONDecodeError:
        print("Response was not valid JSON:")
        print(response.text)


def execute_scip_command(
        scip_exe_path: Path,
        input_model_path: Path,
        output_path: Path,
        solve_type: str,
):
    """
    Automates running a command in the SCIP command-line tool.

    Args:
        scip_exe_path: Path to the SCIP executable.
        input_model_path: Path to the input model file (.mps, .lp, etc.).
        output_path: Path for the output file (presolved model or solution).
        solve_type: The type of operation, either 'presolve' or 'solve'.
    """
    if not scip_exe_path.exists():
        print(f"Error: SCIP executable not found at '{scip_exe_path}'")
        return

    if not os.path.exists(input_model_path):
        print(f"Error: Input file not found at '{input_model_path}'")
        return

    print(f"-> Starting SCIP process for '{input_model_path}'...")

    command_map = {
        "presolve": f"""
            read {input_model_path}
            set limits nodes 0
            set presolving emphasis aggressive
            set presolving aggregation FALSE
            set presolving maxrounds -1
            set presolving maxrestarts -1
            presolve
            write transproblem {output_path}
            quit
            """,
        "solve": f"""
            read {input_model_path}
            optimize
            display solution
            write solution {output_path}
            quit
            """,
    }

    if solve_type not in command_map:
        raise ValueError("solve_type must be either 'presolve' or 'solve'")

    scip_commands = command_map[solve_type]

    process = subprocess.Popen(
        [str(scip_exe_path)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        universal_newlines=True,
    )

    stdout, _ = process.communicate(scip_commands)
    print(stdout)

    print(f"-> SCIP process finished with return code: {process.returncode}")

    if process.returncode == 0 and output_path.exists():
        print(f"Success! Output saved to: '{output_path}'")
    elif process.returncode == 0:
        print("SCIP ran successfully, but the output file was not created.")
    else:
        print("An error occurred during the SCIP process.")

def execute_highs_command(
        highs_exe_path: Path,
        input_model_path: Path,
        output_path: Path,
):
    """
    Automates running a command in the HiGHS command-line tool.

    Args:
        highs_exe_path: Path to the HiGHS executable.
        input_model_path: Path to the input model file (.mps, .lp, etc.).
        output_path: Path for the output file (presolved model or solution).
    """
    if not highs_exe_path.exists():
        print(f"Error: HiGHS executable not found at '{highs_exe_path}'")
        return

    if not os.path.exists(input_model_path):
        print(f"Error: Input file not found at '{input_model_path}'")
        return

    print(f"-> Starting HiGHS process for '{input_model_path}'...")

    command = [
        str(highs_exe_path),
        str(input_model_path),
        f"--solution_file={output_path}",
    ]

    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        universal_newlines=True,
    )

    stdout, _ = process.communicate()
    print(stdout)

    print(f"-> HiGHS process finished with return code: {process.returncode}")

    if process.returncode == 0 and output_path.exists():
        print(f"Success! Output saved to: '{output_path}'")
    elif process.returncode == 0:
        print("HiGHS ran successfully, but the output file was not created.")
    else:
        print("An error occurred during the HiGHS process.")


# --- Main Execution Logic ---

def main():
    """
    Main function to parse command-line arguments and run the requested workflow.
    """
    # --- Argument Parsing ---
    parser = argparse.ArgumentParser(
        description="A tool to solve optimization problems using SCIP and NVIDIA cuOpt.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True, help="Available commands")

    # --- Parent parser for common arguments ---
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument(
        "input_file", type=Path, help="Path to the input model file (e.g., model.mps)."
    )
    parent_parser.add_argument(
        "--config", type=Path, default=Path(__file__).parent / CONFIG_FILE, help="Path to the config.ini file."
    )

    # --- Sub-parser for 'solve-cuopt' ---
    parser_cuopt = subparsers.add_parser(
        "solve-cuopt",
        parents=[parent_parser],
        help="Solve a model directly using the cuOpt server.",
    )

    # --- Sub-parser for 'solve-scip' ---
    parser_scip = subparsers.add_parser(
        "solve-scip",
        parents=[parent_parser],
        help="Solve a model using SCIP and save the solution.",
    )
    parser_scip.add_argument(
        "output_file", type=Path, help="Path to save the output solution file (e.g., solution.sol)."
    )
    # --- Sub-parser for 'solve-highs' ---
    parser_highs = subparsers.add_parser(
        "solve-highs",
        parents=[parent_parser],
        help="Solve a model using HiGHS and save the solution.",
    )
    parser_highs.add_argument(
        "output_file", type=Path, help="Path to save the output solution file (e.g., solution.sol)."
    )

    # --- Sub-parser for 'presolve-and-solve' ---
    parser_presolve = subparsers.add_parser(
        "presolve-and-solve",
        parents=[parent_parser],
        help="Presolve a model with SCIP, then solve the result with cuOpt.",
    )
    parser_presolve.add_argument(
        "output_file", type=Path, help="Path to save the intermediate presolved .mps file."
    )

    args = parser.parse_args()

    # --- Load Configuration ---
    try:
        config = load_config(args.config)
        scip_exe = Path(config.get("Paths", "scip_solver_exe"))
        highs_exe = Path(config.get("Paths", "highs_solver_exe"))
        cuopt_url = config.get("cuOpt", "server_url")
    except (FileNotFoundError, configparser.NoSectionError, configparser.NoOptionError) as e:
        print(f"Configuration Error: {e}")
        return

    # --- Execute Command ---
    if args.command == "solve-cuopt":
        solve_with_cuopt_server(args.input_file, cuopt_url)
    elif args.command == "solve-scip":
        execute_scip_command(scip_exe, args.input_file, args.output_file, "solve")
    elif args.command == "solve-highs":
        execute_highs_command(highs_exe, args.input_file, args.output_file, "solve")
    elif args.command == "presolve-and-solve":
        print("--- Step 1: Presolving with SCIP ---")
        execute_scip_command(scip_exe, args.input_file, args.output_file, "presolve")
        presolved_file = args.output_file
        if presolved_file.exists():
            print("\n--- Step 2: Solving with cuOpt ---")
            solve_with_cuopt_server(presolved_file, cuopt_url)
        else:
            print("\nPresolving failed. Skipping cuOpt solve step.")


if __name__ == "__main__":
    main()