import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import numpy as np
from typing import Optional, List, Dict, Any

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


# Initialize the FastAPI app
app = FastAPI()

# Define the structure of the incoming request data
class MPSRequest(BaseModel):
    file_name: str
    time_limit: float = 1.0
    batch_size: int = 1

class SolverResponse(BaseModel):
    """
    Defines the structured response from the solver.
    It includes core fields and a flexible dictionary for all other details.
    """
    # Core fields that should always be present
    status: str
    objective_value: Optional[float] = None

    # A flexible "catch-all" dictionary for any other data from the solver
    details: Dict[str, Any] = {}

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

    # 1. Dynamically build a dictionary of ALL available results.
    full_result_dict = {}
    for attr_name in dir(result_obj):
        if not attr_name.startswith('get_'):
            continue

        method = getattr(result_obj, attr_name)
        if not callable(method):
            continue

        key = attr_name[4:]  # Remove "get_" prefix
        try:
            value = method()
            # Check for basic, JSON-safe types first
            if isinstance(value, (str, int, float, bool, list, dict, type(None))):
                full_result_dict[key] = value
            # Handle numpy arrays specifically
            elif isinstance(value, np.ndarray):
                full_result_dict[key] = value.tolist()
            # For any other complex object, convert it to a string to avoid errors
            else:
                print(
                    f"Warning: Attribute '{key}' returned a non-serializable type ({type(value)}). Converting to string.")
                full_result_dict[key] = str(value)
        except AttributeError as e:
            # This catches errors for attributes not supported by the solution type
            print(f"Skipping unsupported attribute '{key}': {e}")
            pass

    # 2. Create the final, structured response object.
    # The .pop() method removes the key from the dictionary while returning its value.
    # The remaining items in the dictionary are our flexible 'details'.
    response_data = SolverResponse(
        status=full_result_dict.pop('status', 'unknown'),
        objective_value=full_result_dict.pop('objective_value', None),
        details=full_result_dict  # Pass the rest of the items to the details field
    )

    print(f"Solver finished with status: {response_data.status}")
    return response_data

@app.get("/health", status_code=200)
def health_check():
    """
    A simple health check endpoint that returns a 200 OK status
    if the server is running. Useful for load balancers and monitoring.
    """
    return {"status": "healthy"}