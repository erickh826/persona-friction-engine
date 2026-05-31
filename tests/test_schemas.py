import json
import os
from jsonschema import validate, Draft7Validator

def test_schemas_are_valid_draft7():
    schemas_dir = os.path.join(os.path.dirname(__file__), "../schemas")
    for filename in os.listdir(schemas_dir):
        if filename.endswith(".json"):
            filepath = os.path.join(schemas_dir, filename)
            with open(filepath, "r") as f:
                schema = json.load(f)
                Draft7Validator.check_schema(schema)
                assert True
