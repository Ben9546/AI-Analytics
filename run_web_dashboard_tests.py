import subprocess
import sys
import os

if __name__ == "__main__":
    print(f"--- run_web_dashboard_tests.py starting ---")
    current_cwd = os.getcwd()
    print(f"--- Initial CWD for script: {current_cwd}")

    # Define the project root and the target test directory
    project_root = "/app"
    test_dir = os.path.join(project_root, "web-dashboard/backend/tests/") # Use os.path.join for robustness

    # Create a new environment dictionary inheriting current environment
    env = os.environ.copy()
    # Set/override PYTHONPATH for the subprocess
    env["PYTHONPATH"] = project_root + (os.pathsep + env["PYTHONPATH"] if "PYTHONPATH" in env else "")

    print(f"--- Effective PYTHONPATH for subprocess: {env['PYTHONPATH']}")
    print(f"--- Target test directory: {test_dir}")

    # Command to execute pytest
    # We explicitly use the python interpreter that runs this script
    # to invoke pytest as a module.
    # Pytest will be run with CWD being the directory of this script,
    # but with PYTHONPATH correctly set, it should find web_dashboard.
    # Alternatively, set CWD for the subprocess if necessary.
    command = [sys.executable, "-m", "pytest", "-v", test_dir]

    print(f"--- Executing command: {' '.join(command)} from CWD: {current_cwd}")

    # Execute pytest as a subprocess with the modified environment
    # Running from the script's CWD, relying on PYTHONPATH for module resolution
    process = subprocess.run(command, capture_output=True, text=True, env=env, cwd=project_root)
    # Changed cwd to project_root for the subprocess call as well.

    print("--- Pytest STDOUT: ---")
    print(process.stdout)
    print("--- Pytest STDERR: ---")
    print(process.stderr)

    sys.exit(process.returncode)
