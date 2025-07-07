import sys
import os
import pytest
import subprocess

if __name__ == "__main__":
    print(f"--- run_api_service_tests.py starting ---")

    # Define service root
    service_root = "/app/api-service" # This script is in /app, target is /app/api-service

    # Change Current Working Directory to the service's root
    os.chdir(service_root)
    print(f"--- Changed CWD to: {os.getcwd()}") # Should be /app/api-service

    # Install requirements from within the service_root (now CWD)
    requirements_path = "requirements.txt"
    print(f"--- Installing requirements from: {os.path.join(os.getcwd(), requirements_path)}")
    install_command = [sys.executable, "-m", "pip", "install", "-r", requirements_path, "--quiet", "--disable-pip-version-check", "--no-user"]
    install_process = subprocess.run(install_command, capture_output=True, text=True)
    if install_process.returncode != 0:
        print("--- PIP Install STDOUT: ---")
        print(install_process.stdout)
        print("--- PIP Install STDERR: ---")
        print(install_process.stderr)
        print(f"--- PIP install failed in {os.getcwd()}, exiting. ---")
        sys.exit(install_process.returncode)
    print(f"--- Requirements installed successfully (or already satisfied) in {os.getcwd()}. ---")

    # Run pytest on the "tests/" directory relative to the CWD (service_root)
    # Python's import mechanism should find 'main.py' and 'endpoints/' directly from CWD.
    print(f"--- Running pytest on 'tests/' from CWD: {os.getcwd()}")
    # sys.path is automatically prepended with CWD by Python when running scripts.
    # For pytest.main(), it should also respect this CWD for top-level module discovery.
    print(f"--- sys.path before pytest.main: {sys.path}")
    exit_code = pytest.main(["-v", "tests/"])
    sys.exit(exit_code)
