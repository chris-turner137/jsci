# Export environment variables for this repository.
# Usage: source export.sh
# Note: The reporistory root must be the current directory!
export PYTHONPATH="$(pwd)/packages:$(pwd)/submodules/packages:$PYTHONPATH"
