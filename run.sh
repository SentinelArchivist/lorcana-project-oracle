#!/bin/bash

# This script automates the process of running the Project Oracle application.
# It ensures the virtual environment is activated and runs the app as a module.

# Get the absolute path of the directory where the script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Activate the Python virtual environment
# The virtual environment is expected to be in the project root (.venv)
source "$DIR/.venv/bin/activate"

# Run the application using the Python interpreter from the virtual environment
# The -m flag tells Python to run the src.main module as a script
echo "Starting Project Oracle..."
python -m src.main