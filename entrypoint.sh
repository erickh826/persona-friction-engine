#!/bin/bash
# Persona Friction Engine — GitHub Action Entrypoint
# This script runs inside the Docker container when the action is triggered.

set -e

echo "=============================================="
echo " Persona Friction Engine — CI/CD Runner"
echo "=============================================="
echo "Python: $(python3 --version)"
echo "Working dir: $(pwd)"
echo ""

# Run the GitHub Action CI runner
python3 -m src.ci.github_action_runner
EXIT_CODE=$?

echo ""
echo "=============================================="
echo " Audit complete. Exit code: $EXIT_CODE"
echo "=============================================="

exit $EXIT_CODE
