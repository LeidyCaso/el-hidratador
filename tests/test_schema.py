"""Tests for the published schemas and the dependency-free validator."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from el_hidratador.core import create_ledger
from el_hidratador.dag import build_dag, handoff_payload
from el_hidratador.errors import ValidationError
from el_hidratador.sandbox import build_sandbox
from el_hidratador.schema import (
    SCHEMAS,
    all_schemas,
    schema_files,
    schema_for,
    validate,
    validate_named,
)


class SchemaPublicationTests(unittest.TestCase):
    def test_every_schema_is_published(self) -> None:
        for name in ("ticket", "packet", "manifest", "sandbox", "handoff"):
            self.assertIn(name, SCHEMAS)

    def test_schema_carries_its_metadata(self) -> None:
        schema = schema_for("handoff")
        self.assertIn("$schema", schema)
        self.assertIn("$id", schema)
        self.assertIn("title", schema)
        self.assertIn("description", schema)

    def test_unknown_schema_is_refused(self) -> None:
        with self.assertRaises(ValidationError):
            schema_for("invented")

    def test_schemas_are_stable_json(self) -> None:
        for name, content in schema_files():
            self.assertTrue(name.endswith(".json"))
            parsed = json.loads(content)
            self.assertEqual(parsed, schema_for(name.removesuffix(".json")))

    def test_all_schemas_is_sorted(self) -> None:
        names = list(all_schemas())
        self.assertEqual(names, sorted(names))


class ValidatorTests(unittest.TestCase):
    def test_type_mismatch_is_reported(self) -> None:
        errors = validate(5, {"type": "string"})
        self.assertTrue(errors)
        self.assertIn("expected type string", errors[0])

    def test_a_valid_instance_has_no_errors(self) -> None:
        self.assertEqual(validate("x", {"type": "string"}), [])

    def test_required_property_is_reported(self) -> None:
        errors = validate({}, {"type": "object", "required": ["id"]})
        self.assertIn("missing the required property 'id'", errors[0])

    def test_additional_properties_can_be_refused(self) -> None:
        errors = validate({"a": 1}, {"type": "object", "additionalProperties": False})
        self.assertIn("not allowed", errors[0])

    def test_const_is_enforced(self) -> None:
        errors = validate(True, {"const": False})
        self.assertTrue(errors)
        self.assertEqual(validate(False, {"const": False}), [])

    def test_enum_is_enforced(self) -> None:
        schema = {"type": "string", "enum": ["a", "b"]}
        self.assertTrue(validate("c", schema))
        self.assertEqual(validate("a", schema), [])

    def test_numeric_bounds_are_enforced(self) -> None:
        schema = {"type": "integer", "minimum": 1, "maximum": 3}
        self.assertTrue(validate(0, schema))
        self.assertTrue(validate(4, schema))
        self.assertEqual(validate(2, schema), [])

    def test_pattern_is_enforced(self) -> None:
        schema = {"type": "string", "pattern": "^[A-Z]+$"}
        self.assertTrue(validate("lower", schema))
        self.assertEqual(validate("UPPER", schema), [])

    def test_nested_property_errors_carry_the_path(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "outer": {"type": "object", "properties": {"inner": {"type": "integer"}}}
            },
        }
        errors = validate({"outer": {"inner": "no"}}, schema)
        self.assertTrue(any("$.outer.inner" in error for error in errors))

    def test_list_items_are_validated(self) -> None:
        schema = {"type": "array", "items": {"type": "integer"}}
        errors = validate([1, "two"], schema)
        self.assertTrue(errors)

    def test_booleans_are_not_integers(self) -> None:
        self.assertTrue(validate(True, {"type": "integer"}))


class ContractTests(unittest.TestCase):
    """The published schemas must describe what the code actually produces."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.ledger = create_ledger(Path(self.tmp.name) / "ledger.sqlite")

    def tearDown(self) -> None:
        self.ledger.close()
        self.tmp.cleanup()

    def test_a_ticket_matches_the_ticket_schema(self) -> None:
        self.ledger.add_task("M-1001", "objective", "acceptance", scope=["repo/api"])
        self.assertEqual(validate_named(self.ledger.task("M-1001"), "ticket"), [])

    def test_a_packet_matches_the_packet_schema(self) -> None:
        self.ledger.add_task("M-1001", "objective", "acceptance", scope=["repo/api"])
        self.ledger.add_context("M-1001", "body", "source")
        packet = self.ledger.pack("M-1001", 12000)["packet"]
        self.assertEqual(validate_named(packet, "packet"), [])

    def test_a_manifest_matches_the_manifest_schema(self) -> None:
        from el_hidratador.dag import manifest

        self.ledger.add_task("M-1001", "objective", "acceptance", scope=["repo/api"])
        dag = build_dag("M-1001", markdown="## Tasks\n- [ ] Do the work\n")
        result = manifest(dag, self.ledger.task("M-1001"))
        self.assertEqual(validate_named(result, "manifest"), [])

    def test_a_sandbox_matches_the_sandbox_schema(self) -> None:
        spec = build_sandbox("M-1001", "/tmp/work")
        self.assertEqual(validate_named(spec, "sandbox"), [])

    def test_a_handoff_matches_the_handoff_schema(self) -> None:
        self.ledger.add_task("M-1001", "objective", "acceptance", scope=["repo/api"])
        ticket = self.ledger.task("M-1001")
        dag = build_dag("M-1001", markdown="## Tasks\n- [ ] Do the work\n")
        packet = self.ledger.pack("M-1001", 12000)["packet"]
        sandbox = build_sandbox("M-1001", "/tmp/work")
        payload = handoff_payload(dag, packet, ticket, sandbox)
        self.assertEqual(validate_named(payload, "handoff"), [])

    def test_a_handoff_never_claims_authorization(self) -> None:
        self.ledger.add_task("M-1001", "objective", "acceptance", scope=["repo/api"])
        dag = build_dag("M-1001", markdown="## Tasks\n- [ ] Do the work\n")
        payload = handoff_payload(
            dag, {}, self.ledger.task("M-1001"), build_sandbox("M-1", "/tmp/w")
        )
        self.assertFalse(payload["authorized"])
        self.assertTrue(validate_named(payload, "handoff"))

    def test_the_published_schema_files_are_current(self) -> None:
        """The copies in the repository must match the module."""
        published = Path(__file__).resolve().parent.parent / "schema"
        if not published.exists():
            self.skipTest("the schema directory is not present")
        for name, content in schema_files():
            path = published / name
            self.assertTrue(path.exists(), f"{name} is missing from {published}")
            self.assertEqual(path.read_text(encoding="utf-8"), content)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
