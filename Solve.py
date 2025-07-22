import subprocess
import os
import configparser
import requests
import json

def read_and_send_mps_to_cuopt(location, mps_file_name):
    # The URL of your running cuOpt server
    url = "http://localhost:8000/solve_mps"

    response = requests.post(
        url,
        json={
            "file_name": mps_file_name,  # <-- Change this to your .mps filename
            "time_limit": 90.0,
            "batch_size": 1
        }
    )

    print(f"Status Code: {response.status_code}")
    try:
        print("Response JSON:")
        print(json.dumps(response.json(), indent=2))
    except json.JSONDecodeError:
        print("Response was not valid JSON:")
        print(response.text)

def get_config_paths(config_file_path='config.ini'):
    """Reads paths from a configuration file."""
    config = configparser.ConfigParser()

    # Check if the config file exists
    if not os.path.exists(config_file_path):
        print(f"Error: Configuration file not found at {config_file_path}")
        # Optionally, create a default config file or raise an error
        return {}

    config.read(config_file_path)

    paths = {}
    if 'Paths' in config:
        for key, value in config['Paths'].items():
            paths[key] = value
    return paths


def presolve_with_scip(location, input_filepath, output_filepath, solver_path = None):
    """
    Automates using SCIP to presolve a model file and save the result.

    This function starts the SCIP command-line tool, feeds it commands to
    presolve the model and write the transformed problem to a new file,
    and then quits.

    Args:
        location (Path): The path to the original model file (e.g., .mps, .lp).
        input_filepath (str): The name of the original model file to the original model file (e.g., .mps, .lp).
        output_filepath (str): The name of the new presolved model file where the new presolved .mps file will be saved.
    """
    if not solver_path:
        paths = get_config_paths(config_file_path="../../../config.ini")
        solver_path = paths["solver_exe"]
    # Verify the SCIP executable is available in the system's PATH
    try:
        # Use 'scip --version' as a quick, non-interactive check
        subprocess.run([solver_path, '--version'], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: Could not execute 'scip'.")
        print("Please ensure the SCIP Optimization Suite is installed and the 'scip' executable is in your system's PATH.")
        return

    # Check that the input file exists
    if not os.path.exists(location / input_filepath):
        print(f"Error: Input file not found at '{location / input_filepath}'")
        return

    print(f"-> Starting SCIP process for '{location / input_filepath}'...")

    # These are the commands we will send to the SCIP interactive shell
    # 1. Start SCIP, THEN read the problem inside the shell.
    # 2. Set the node limit to 0 to disable the main solver.
    # 3. Presolve, write the transformed file, and quit.
    scip_commands = f"""
        read {location / input_filepath}
        set limits nodes 0
        presolve
        write transproblem {location / output_filepath}
        quit
        """

    # Start the SCIP process
    process = subprocess.Popen(
        [solver_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,  # Redirect stderr to stdout
        text=True,
        bufsize=1,                 # Use line-buffering
        universal_newlines=True
    )

    # Send commands to SCIP and close stdin to signal completion
    if process.stdin:
        process.stdin.write(scip_commands)
        process.stdin.flush()
        process.stdin.close()

    # Read and print output line by line in real-time
    if process.stdout:
        for line in process.stdout:
            print(line, end='')  # Print each line as it's received

    # Wait for the process to terminate and get the final return code
    process.wait()

    print(f"\n\n-> SCIP process finished with return code: {process.returncode}")

    # Check if the process was successful and if the output file was created
    if process.returncode == 0 and os.path.exists(location / output_filepath):
        print(f"Presolving complete. New model saved to: '{location / output_filepath}'")
    elif process.returncode == 0:
        print("SCIP ran successfully but did not create an output file.")
        print("This often means the problem was solved during presolve (e.g., found to be infeasible).")
    else:
        print("An error occurred during the SCIP process.")

def presolve_with_scip_and_solve_with_cuopt(location, input_file, output_file, solver_path=None):
    presolve_with_scip(location, input_file, output_file, solver_path)
    read_and_send_mps_to_cuopt(location, output_file)

def solve_with_cuopt(location, input_file):
    read_and_send_mps_to_cuopt(location, input_file)

