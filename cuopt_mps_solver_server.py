import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Import the specific modules and classes needed
from cuopt.linear_programming.cuopt_mps_parser import parser
from cuopt.linear_programming import SolverSettings
from cuopt import linear_programming
from cuopt.linear_programming.solver.solver_parameters import (
    CUOPT_ABSOLUTE_DUAL_TOLERANCE,
    CUOPT_ABSOLUTE_GAP_TOLERANCE,
    CUOPT_ABSOLUTE_PRIMAL_TOLERANCE,
    CUOPT_DUAL_INFEASIBLE_TOLERANCE,
    CUOPT_INFEASIBILITY_DETECTION,
    CUOPT_ITERATION_LIMIT,
    CUOPT_METHOD,
    CUOPT_MIP_HEURISTICS_ONLY,
    CUOPT_PDLP_SOLVER_MODE,
    CUOPT_PRIMAL_INFEASIBLE_TOLERANCE,
    CUOPT_RELATIVE_DUAL_TOLERANCE,
    CUOPT_RELATIVE_GAP_TOLERANCE,
    CUOPT_RELATIVE_PRIMAL_TOLERANCE,
    CUOPT_SOLUTION_FILE,
    CUOPT_TIME_LIMIT,
    CUOPT_USER_PROBLEM_FILE,
)
from cuopt.linear_programming.solver_settings import (
    PDLPSolverMode,
    SolverMethod,
)
import numpy as np


# Initialize the FastAPI app
app = FastAPI()

# Define the structure of the incoming request data
class MPSRequest(BaseModel):
    file_name: str
    time_limit: float = 1.0
    batch_size: int = 1

# Define the endpoint that will receive the POST request
@app.post("/solve_mps")
def solve_from_request(request: MPSRequest):
    """
    Receives a filename, reads it from the mounted volume, and solves it.
    """
    # The base directory where your files are mounted inside the container
    base_directory = "/app"

    # Safely join the base directory and the requested filename
    file_path = os.path.normpath(os.path.join(base_directory, request.file_name))

    # Security Check: Ensure the path is within the allowed directory
    if not file_path.startswith(base_directory):
        raise HTTPException(status_code=400, detail="Invalid file path specified.")

    # Check if the file actually exists
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"File not found inside the container at: {file_path}")

    print(f"Reading file from: {file_path}")

    # Use the parser directly with the file path
    data_model_list = []

    for i in range(request.batch_size):
        data_model_list.append(parser.ParseMps(file_path))

    # Create SolverSettings and call Solve
    solver_settings = SolverSettings()
    solver_settings.set_parameter("time_limit", str(request.time_limit))
    solver_settings.set_parameter(CUOPT_METHOD, SolverMethod.PDLP)
    # solver_settings.set_parameter(CUOPT_PDLP_SOLVER_MODE, PDLPSolverMode.Fast1)
    
    # Solve
    # result_obj = linear_programming.Solve(data_model, solver_settings=solver_settings)
    batch_solution, solve_time = linear_programming.BatchSolve(data_model_list, solver_settings)
    result_obj = batch_solution[0]
    
    # Dynamically build a dictionary from the result object
    result = {}
    for attr_name in dir(result_obj):
        # Find all getter methods
        if attr_name.startswith('get_'):
            method = getattr(result_obj, attr_name)
            if callable(method):
                key = attr_name[4:]
                try:
                    value = method()
                    # Convert numpy arrays to lists for JSON serialization
                    if isinstance(value, np.ndarray):
                        result[key] = value.tolist()
                    else:
                        result[key] = value
                except AttributeError as e:
                    # This catches errors for attributes not supported by the solution type (e.g., MILP vs LP)
                    print(f"Skipping unsupported attribute '{key}': {e}")
                    pass

    print(f"Solver finished with status: {result.get('status', 'N/A')}")
    return result
