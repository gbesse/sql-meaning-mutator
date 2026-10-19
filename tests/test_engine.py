from copy import deepcopy
import json
from pathlib import Path
import sqlite3
import unittest

from sql_meaning.__main__ import example
from sql_meaning.engine import cascade_delete, compare, database, search


class MeaningTests(unittest.TestCase):
    def test_seed_passes_but_mutation_exposes_fanout(self):
        suite = example()
        self.assertTrue(compare(suite)["equal"])
        result = search(suite)
        self.assertEqual(result["status"], "counterexample")
        self.assertEqual(result["mutation_path"][0]["operation"], "clone_row")
        self.assertEqual(result["comparison"]["reference"], [(1, 2000)])
        self.assertEqual(result["comparison"]["candidate"], [(1, 4000)])
        self.assertEqual(result["row_count"], 4)
        self.assertTrue(result["row_deletion_minimal"])
        self.assertFalse(result["is_business_correctness_proof"])

    def test_minimal_witness_preserves_symptom_and_declared_business_constraints(self):
        result = search(example())
        witness = result["witness"]
        self.assertEqual(result["comparison"]["mismatch_kind"], "row_values")
        db = database(witness)
        self.assertEqual(db.execute("PRAGMA foreign_key_check").fetchall(), [])
        db.close()
        for table, data in witness["tables"].items():
            for index in range(len(data["rows"])):
                trial = cascade_delete(witness, table, index)
                try:
                    result = compare(trial)
                except (ValueError, sqlite3.Error):
                    continue
                self.assertNotEqual(result["mismatch_kind"], "row_values")

    def test_reference_against_itself_never_claims_correctness(self):
        suite = example()
        suite["candidate_sql"] = suite["reference_sql"]
        result = search(suite, max_depth=1)
        self.assertEqual(result["status"], "no_counterexample_found")
        self.assertTrue(result["search_complete"])
        self.assertFalse(result["is_business_correctness_proof"])

    def test_numeric_boundary_finds_strict_comparison_error(self):
        suite = {"tables":{"items":{"columns":{"id":"INTEGER","price":"INTEGER"},"primary_key":"id","rows":[{"id":1,"price":50}]}},
                 "numeric_boundaries":[100], "reference_sql":"SELECT id FROM items WHERE price>=100", "candidate_sql":"SELECT id FROM items WHERE price>100"}
        result = search(suite)
        self.assertEqual(result["status"], "counterexample")
        self.assertEqual(result["witness"]["tables"]["items"]["rows"][0]["price"], 100)

    def test_nullable_value_exposes_three_valued_logic(self):
        suite = {"tables":{"items":{"columns":{"id":"INTEGER","status":"TEXT"},"primary_key":"id","nullable":["status"],"rows":[{"id":1,"status":"active"}]}},
                 "reference_sql":"SELECT id FROM items WHERE status IS NULL OR status!='cancelled'", "candidate_sql":"SELECT id FROM items WHERE status NOT IN ('cancelled')"}
        result = search(suite)
        self.assertEqual(result["status"], "counterexample")
        self.assertIsNone(result["witness"]["tables"]["items"]["rows"][0]["status"])

    def test_bag_comparison_preserves_duplicate_multiplicity(self):
        suite = example()
        suite["reference_sql"] = "SELECT 1 UNION ALL SELECT 1"
        suite["candidate_sql"] = "SELECT 1"
        self.assertFalse(compare(suite)["equal"])

    def test_order_is_opt_in(self):
        suite = example()
        suite["reference_sql"] = "SELECT id FROM customers ORDER BY id"
        suite["candidate_sql"] = "SELECT id FROM customers ORDER BY id DESC"
        self.assertTrue(compare(suite)["equal"])
        suite["ordered"] = True
        self.assertFalse(compare(suite)["equal"])

    def test_numeric_sqlite_equivalence(self):
        suite = example()
        suite["reference_sql"] = "SELECT 1"
        suite["candidate_sql"] = "SELECT 1.0"
        self.assertTrue(compare(suite)["equal"])

    def test_write_attach_and_extension_queries_denied(self):
        for sql in ("DELETE FROM customers", "ATTACH DATABASE '/tmp/should-not-exist.db' AS external", "SELECT load_extension('anything')", "PRAGMA database_list"):
            suite = example()
            suite["candidate_sql"] = sql
            self.assertEqual(search(suite)["status"], "query_or_fixture_error")

    def test_recursive_runaway_is_interrupted(self):
        suite = example()
        suite["candidate_sql"] = "WITH RECURSIVE x(a) AS (VALUES(1) UNION ALL SELECT a+1 FROM x) SELECT SUM(a) FROM x"
        self.assertEqual(search(suite)["status"], "query_or_fixture_error")

    def test_large_result_is_not_truncated_into_false_pass(self):
        suite = example()
        suite["candidate_sql"] = "WITH RECURSIVE x(a) AS (VALUES(1) UNION ALL SELECT a+1 FROM x WHERE a<1001) SELECT a FROM x"
        self.assertEqual(search(suite)["status"], "query_or_fixture_error")

    def test_budget_exhaustion_is_explicit(self):
        result = search(example(), max_cases=1)
        self.assertEqual(result["status"], "no_counterexample_found")
        self.assertFalse(result["search_complete"])

    def test_found_witness_is_kept_when_minimizer_budget_exhausted(self):
        result = search(example(), max_cases=3)
        self.assertEqual(result["status"], "counterexample")
        self.assertFalse(result["row_deletion_minimal"])

    def test_invalid_foreign_keys_do_not_become_counterexamples(self):
        suite = example()
        suite["tables"]["lines"]["rows"][0]["order_id"] = 999
        self.assertEqual(search(suite)["status"], "query_or_fixture_error")

    def test_schema_identifier_injection_rejected(self):
        suite = example()
        suite["tables"]["x;DROP TABLE orders"] = suite["tables"].pop("lines")
        with self.assertRaises(ValueError):
            search(suite)

    def test_witness_is_json_replayable(self):
        result = search(example())
        replay = json.loads(json.dumps(result["witness"]))
        self.assertFalse(compare(replay)["equal"])


if __name__ == "__main__":
    unittest.main()
