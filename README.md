# Overview

This project provides a Command Line Interface (CLI) tool for testing your optimization problems (saved in .mps format) in SCIP, HiGHS and cuOpt ([see setup instructions here](cuopt_setup.md)). It includes a **FastAPI application for exposing NVIDIA cuOpt capabilities as a service** and a **command-line utility (`Solve.py`)** that can interact with this service or directly invoke local SCIP and HiGHS solvers. The design primarily supports solving **MPS (Mathematical Programming System) model files**.

# Features

*   **FastAPI cuOpt Solver Service**: A web service exposing `cuOpt` for solving Linear Programming problems via a REST API.
*   **Local Solver Integration**: A command-line interface to directly utilize **SCIP** and **HiGHS** for solving optimization models.
*   **Presolving with SCIP**: Capability to **presolve MPS models using SCIP**, which can simplify them before solving with cuOpt or other solvers.
*   **Batch Solving Support**: The `cuOpt` service supports solving multiple models in a single request.
*   **Configurable Paths**: Solver executables and server URLs are managed via a `config.ini` file for easy setup and testing.

# Prerequisites

*   **Python 3.X** (tested in 3.13)
*   **NVIDIA cuOpt**: For the cuOpt server functionality, [please follow the instructions here to setup your local cuOpt Server](cuopt_setup.md)). The code in cuopt_mps_solver_server.py will be used to integrate cuOpt's solver code. The cuOpt server needs to be running and accessible for solving.
*   **SCIP Solver**: If you intend to use SCIP functionalities (solving or presolving) via `Solve.py`, the SCIP executable must be installed and accessible.
*   **HiGHS Solver**: If you intend to use HiGHS functionalities via `Solve.py`, the HiGHS executable must be built and accessible.

# Installation & Setup

1.  **Clone the Repository:**
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

2.  **Install Python Dependencies:**
    ```bash
    pip install requests
    ```
    *Note: `cuopt` is a separate library/SDK and would need to be installed based on the instructions provided here.

3.  **Configure `config.ini`:**
    Update the `config.ini` file in the root directory of the project. This file is crucial for specifying paths to solver executables and the cuOpt server URL. An example structure is:

    ```ini
    [Paths]
    scip_solver_exe = /path/to/your/scip/bin/scip # e.g., /opt/scip/bin/scip
    highs_solver_exe = /path/to/your/highs/bin/highs # e.g., /opt/HiGHS/bin/highs
    example_mps_path = /path/to/your/example_models/model.mps # An optional path to an MPS file for testing

    [cuOpt]
    server_url = http://localhost:8000/solve_mps # The URL where your FastAPI cuOpt server is running
    ```
    Ensure the paths to `scip_solver_exe` and `highs_solver_exe` are correct for your system. The `example_mps_path` is used in integration tests.

# Usage

The project provides a CLI for users to interact with the solvers.

## Using the Command-Line Utility (`Solve.py`)

The `Solve.py` script provides a command-line interface to execute operations with different solvers.

*   **General Usage**:
    ```bash
    python Solve.py <command> <input_file> [--config <config_file>] [command_specific_arguments]
    ```

*   **Available Commands**:

    *   **`solve-cuopt`**: Solves an MPS model by sending it to the configured cuOpt server.
        ```bash
        python Solve.py solve-cuopt path/to/your/model.mps
        ```
        The response (status code and JSON) from the cuOpt server will be printed to the console.

    *   **`solve-scip`**: Solves an MPS model using the local SCIP executable specified in `config.ini`.
        ```bash
        python Solve.py solve-scip path/to/your/model.mps output_solution.sol
        ```
        The SCIP output and the solution will be saved to `output_solution.sol`.

    *   **`solve-highs`**: Solves an MPS model using the local HiGHS executable specified in `config.ini`.
        ```bash
        python Solve.py solve-highs path/to/your/model.mps output_solution.sol
        ```
        The HiGHS output and the solution will be saved to `output_solution.sol`.

    *   **`presolve-and-solve`**: First, presolves an MPS model using SCIP, then sends the resulting presolved model to the cuOpt server for solving.
        ```bash
        python Solve.py presolve-and-solve path/to/your/model.mps intermediate_presolved.mps
        ```
        SCIP's presolve output will be printed, the presolved model saved to `intermediate_presolved.mps`, and subsequently, the cuOpt server's response for the presolved model will be displayed.


## FYI. Introduction to the FastAPI cuOpt Server (for basic testing of cuOpt, you shouldn't need to worry about this)

The FastAPI application exposes the `cuOpt` solver via a REST API.
 The server will start, typically on `http://localhost:8000`.

 *You don't need to worry about interacting directly if you're simply trying to run a .mps file for testing feasibility.*

*   **API Endpoints:**

    *   **`POST /solve_mps`**:
        *   **Description**: Receives an MPS file name, reads it from a mounted volume (expected at `/app` inside the container), solves it using cuOpt, and returns the solution.
        *   **Request Body (`application/json`)**:
            ```json
            {
              "file_name": "your_model.mps",
              "time_limit": 10.0,  // Optional, default 1.0 seconds [4]
              "batch_size": 1      // Optional, default 1 [4]
            }
            ```
        *   **Response Body (`application/json`)**:
            ```json
            {
              "status": "success", // or "optimal", "infeasible", etc. [4, 19]
              "objective_value": 123.45, // Optimal objective value, if found [4, 19]
              "details": {
                "vars": [...],      // Solution variables [20]
                "primal_objective": 123.45,
                "solve_time": 0.05,
                // ... other details from cuOpt solver output [4, 13, 19, 21]
              }
            }
            ```
        *   **Note:** *Your `model.mps` file must be accessible to the FastAPI server, typically by mounting a volume containing your MPS files to the `/app` directory inside the container where the FastAPI server is running. Make sure you place your .mps file in the root directory (same location as example_model.mps)*

    *   **`GET /health`**:
        *   **Description**: A simple health check endpoint to confirm the server is running.
        *   **Response**: `{"status": "healthy"}` with a 200 OK status.

# Testing

Integration tests are available using `pytest` to verify the functionality with real solver executables and a running cuOpt server.

*   **To run tests**:
    Ensure your `config.ini` is correctly set up with paths to SCIP, HiGHS, cuOpt server URL, and an example MPS file.
    ```bash
    pytest tests/test_integration.py
    ```
    Tests will be skipped if prerequisites (e.g., `config.ini` paths, running cuOpt server) are not met.