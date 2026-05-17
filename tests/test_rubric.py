"""Rubric structural tests — schema validation, rule counts, id uniqueness."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import jsonschema
import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
RUBRIC_PATH = REPO_ROOT / "rubric" / "v1.yaml"
SCHEMA_PATH = REPO_ROOT / "rubric" / "schema.json"


@pytest.fixture(scope="module")
def schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def rubric() -> dict:
    return yaml.safe_load(RUBRIC_PATH.read_text(encoding="utf-8"))


def test_rubric_validates_against_schema(rubric: dict, schema: dict) -> None:
    jsonschema.validate(instance=rubric, schema=schema)


def test_rubric_has_fifteen_rules(rubric: dict) -> None:
    assert len(rubric["rules"]) == 15


def test_rubric_category_counts(rubric: dict) -> None:
    counts = Counter(rule["category"] for rule in rubric["rules"])
    assert counts == {
        "contract_spec": 5,
        "quality": 4,
        "security": 3,
        "operational": 3,
    }


def test_rubric_rule_ids_unique(rubric: dict) -> None:
    ids = [rule["rule_id"] for rule in rubric["rules"]]
    assert len(ids) == len(set(ids)), "rule_id values must be unique"


def test_rubric_version_format(rubric: dict) -> None:
    assert rubric["version"].startswith("v")


def test_every_rule_has_at_least_one_control_mapping(rubric: dict) -> None:
    for rule in rubric["rules"]:
        assert rule["control_mapping"], f"{rule['rule_id']} missing control_mapping"
