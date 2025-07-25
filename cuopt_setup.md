# Setting up NVIDIA cuOpt with Docker and WSL2
## This guide provides a walkthrough for setting up and running the NVIDIA cuOpt containerized development environment on a Windows machine using WSL2 (Windows Subsystem for Linux).

## 1. Introduction
*   **WSL2**: A feature in Windows that allows you to run a genuine Linux kernel and distributions directly on Windows without the overhead of a traditional virtual machine.
*   **NVIDIA cuOpt**: A GPU-accelerated logistics and route optimization engine that can solve complex vehicle routing problems, LPs and MILPs.

### This setup allows you to leverage your computer's NVIDIA GPU for intensive computation within a clean, isolated Linux environment, all managed from your Windows desktop.

## 2. Prerequisites
### Before you begin, ensure you have the following:
*   **Windows 10 (version 21H2 or higher) or Windows 11**.
*   **An NVIDIA GPU with CUDA capabilities**.
*   **The latest NVIDIA Driver installed on your Windows host**. This is crucial as WSL2 accesses the GPU through the host driver.
*   Virtualization enabled in your computer's BIOS/UEFI. This is usually enabled by default on modern systems.

## 3. Step-by-Step Installation
### Step 1a: Install WSL2 (which should include a Linux Distribution)
#### If you don't have WSL installed, you can install it and the default Ubuntu distribution with a single command.
1.  Open PowerShell or Windows Terminal as an Administrator.
2.  Run the following command:
    ```bash
    wsl --install
    ```
    URL for Microsoft: `https://learn.microsoft.com/en-us/windows/wsl/install`
    This command will enable the required Windows features, download the latest Linux kernel, set WSL2 as your default, and install the Ubuntu distribution.

3.  Restart your computer after the process is complete.
4.  After rebooting, the Ubuntu installation will continue. You will be prompted to create a username and password for your new Linux distribution. (You might have been asked to do this in the previous step also)
#### To verify your installation:
1.  Open PowerShell and run `wsl -l -v`. You should see your distribution listed with `VERSION` set to 2.
    ```
    PS C:\> wsl -l -v   NAME      STATE           VERSION
    * Ubuntu    Running         2
    ```
    If `state = Stopped`, then open your WSL2 terminal (e.g., open the Start Menu and type "Ubuntu").

### Step 1b: Updates and Docker install on WSL environment
1.  Open your WSL2 terminal (e.g., open the Start Menu and type "Ubuntu"). Update your ubuntu environment.
    ```bash
    sudo apt update
    ```
2.  Install Docker from APT repo
    ```bash
    sudo apt install docker.io -y
    ```
### Step 2: Verify GPU Access in WSL2
#### With a modern NVIDIA driver and Docker Desktop, GPU access should be configured automatically. Let's verify it.
1.  Open your WSL2 terminal (e.g., open the Start Menu and type "Ubuntu").
2.  Run the `nvidia-smi` command. You should see the same output as you would on a native Linux machine, detailing your GPU and driver version.
    ```bash
    nvidia-smi
    ```
    If this command fails, it usually indicates an issue with the host NVIDIA driver installation. Ensure it's up to date.

### Step 3: Pull and Run the NVIDIA cuOpt Container
#### Now you are ready to pull the cuOpt environment.
1.  Pull the cuOpt Developer Container. This command downloads the latest cuOpt image (I’m using cuda 12.8). This can take a few minutes.
    ```bash
    sudo docker pull nvidia/cuopt:latest-cuda12.8-py312
    ```
2.  Install the NVIDIA Container Toolkit. Follow the steps on the following website (a and b below are the steps I followed on the website): `https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html`
    a) Installation: I used: “With apt: Ubuntu, Debian” steps.
    b) Configuration: I used “Configuring Docker”, there were two steps.

3.  Run the Container. This command starts the container, enables GPU access, maps a port to access the Jupyter server, and mounts a local directory for persistent storage of your work. Run the container:
    **IMPORTANT**: Replace “`-v /mnt/c/GitHub/TestCuOpt:/app \`” with the proper location to the REPO (mine is at `C:\GitHub\TestCuOpt`).
    ```bash
    sudo docker run --gpus all -it --rm \
    -p 8000:8000 \
    -v /mnt/c/GitHub/TestCuOpt:/app \
    -w /app \
    nvidia/cuopt:latest-cuda12.8-py312 \
    uvicorn cuopt_mps_solver_server:app --host 0.0.0.0 --port 8000
    ```

#### Command Breakdown:
*   **`--gpus all`**: This is the flag that gives the container access to all available GPUs.
*   **`-it`**: Runs the container in interactive mode with a terminal.
*   **`--rm`**: Automatically removes the container when you exit, keeping things clean. Your work is saved in the mounted directory.
*   **`-v ~/[CHANGE_THIS_TO_LOCAL_REPO_LOCATION]`**: Mounts the repo directory you pulled.
*   **`-p 8000:8000`**: Maps port 8000 on your local machine to port 8000 in the container.
*   **IMPORTANT**: If you get the following error,“`docker: Error response from daemon: could not select device driver "" with capabilities: [[gpu]]`” please make sure you followed the “Install the NVIDIA Container Toolkit” steps.

### Step 4: Access the cuOpt Examples
#### Example usage:
*   `python Solve.py solve-cuopt example_model.mps`
*   `python Solve.py solve-scip example_model.mps my_solution.sol`
*   `python Solve.py presolve-and-solve example_model.mps presolved.mps`
### Now, you should be ready to run the command line operations from the repo's [README](readme.md).
