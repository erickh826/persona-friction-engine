"""
ScenarioLoader — Loads and validates scenario JSON files against the project schema.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict

from jsonschema import validate, ValidationError as JsonSchemaValidationError


# Resolve the schema path relative to the project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_SCENARIO_SCHEMA_PATH = _PROJECT_ROOT / "schemas" / "scenario.json"


class ScenarioValidationError(Exception):
    """Raised when a scenario JSON file fails schema validation."""

    def __init__(self, message: str, errors: list = None):
        super().__init__(message)
        self.errors = errors or []


class ScenarioLoader:
    """
    Loads scenario JSON files and validates them against the project schema.
    
    Usage:
        loader = ScenarioLoader()
        scenario = loader.load("path/to/scenario.json")
    """

    def __init__(self, schema_path: str = None):
        """
        Initialize the ScenarioLoader.
        
        Args:
            schema_path: Optional custom path to the scenario JSON schema.
                         Defaults to schemas/scenario.json in the project root.
        """
        schema_file = Path(schema_path) if schema_path else _SCENARIO_SCHEMA_PATH

        if not schema_file.exists():
            raise FileNotFoundError(
                f"Scenario schema not found at: {schema_file}"
            )

        with open(schema_file, "r", encoding="utf-8") as f:
            self._schema = json.load(f)

    def load(self, scenario_path: str) -> Dict[str, Any]:
        """
        Load a scenario JSON file and validate it against the schema.
        
        Args:
            scenario_path: Path to the scenario JSON file.
            
        Returns:
            Parsed and validated scenario dictionary.
            
        Raises:
            FileNotFoundError: If the scenario file does not exist.
            ScenarioValidationError: If the scenario fails schema validation.
            json.JSONDecodeError: If the file is not valid JSON.
        """
        path = Path(scenario_path)

        if not path.exists():
            raise FileNotFoundError(f"Scenario file not found: {scenario_path}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self._validate(data)
        return data

    def load_from_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a scenario dictionary directly (useful for programmatic usage).
        
        Args:
            data: Scenario dictionary to validate.
            
        Returns:
            The same dictionary if validation passes.
            
        Raises:
            ScenarioValidationError: If the scenario fails schema validation.
        """
        self._validate(data)
        return data

    def _validate(self, data: Dict[str, Any]) -> None:
        """
        Validate data against the scenario JSON schema.
        
        Raises:
            ScenarioValidationError: If validation fails.
        """
        try:
            validate(instance=data, schema=self._schema)
        except JsonSchemaValidationError as e:
            raise ScenarioValidationError(
                message=f"Scenario validation failed: {e.message}",
                errors=[str(e)]
            )
