from collections import Counter, deque
from copy import deepcopy
import hashlib
import json
import math
import re
import sqlite3
import time


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def validate(suite):
    if not isinstance(suite, dict) or not isinstance(suite.get("tables"), dict) or not 1 <= len(suite["tables"]) <= 10:
        raise ValueError("invalid_tables")
    tables = suite["tables"]
    total = 0
    for name, table in tables.items():
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z_]\w{0,63}", name) or not isinstance(table, dict):
            raise ValueError("invalid_table")
        columns = table.get("columns")
        if not isinstance(columns, dict) or not 1 <= len(columns) <= 20:
            raise ValueError("invalid_columns")
        for column, kind in columns.items():
            if not isinstance(column, str) or not re.fullmatch(r"[A-Za-z_]\w{0,63}", column) or kind not in ("INTEGER", "TEXT", "REAL"):
                raise ValueError("invalid_column")
        primary = table.get("primary_key")
        if primary not in columns or columns[primary] not in ("INTEGER", "TEXT"):
            raise ValueError("invalid_primary_key")
        nullable = table.get("nullable", [])
        if not isinstance(nullable, list) or any(c not in columns or c == primary for c in nullable):
            raise ValueError("invalid_nullable")
        refs = table.get("references", {})
        if not isinstance(refs, dict):
            raise ValueError("invalid_references")
        for column, ref in refs.items():
            if column not in columns or not isinstance(ref, list) or len(ref) != 2 or any(not isinstance(x, str) for x in ref):
                raise ValueError("invalid_reference")
            if ref[0] not in tables or ref[1] != tables[ref[0]].get("primary_key"):
                raise ValueError("invalid_reference")
        rows = table.get("rows")
        if not isinstance(rows, list):
            raise ValueError("invalid_rows")
        total += len(rows)
        if total > 200:
            raise ValueError("invalid_row_limit")
        for row in rows:
            if not isinstance(row, dict) or set(row) != set(columns):
                raise ValueError("invalid_row")
            for c, value in row.items():
                if value is None:
                    if c not in nullable:
                        raise ValueError("invalid_null")
                elif columns[c] == "TEXT":
                    if not isinstance(value, str) or len(value) > 4096:
                        raise ValueError("invalid_text")
                elif columns[c] == "INTEGER":
                    if type(value) is not int or abs(value) > 10**12:
                        raise ValueError("invalid_integer")
                elif type(value) not in (float, int) or not math.isfinite(value) or abs(value) > 10**12:
                    raise ValueError("invalid_real")
    for field in ("reference_sql", "candidate_sql"):
        if not isinstance(suite.get(field), str) or not 0 < len(suite[field]) <= 20000:
            raise ValueError("invalid_query")
    mutate = suite.get("mutate_tables", list(tables))
    if not isinstance(mutate, list) or any(t not in tables for t in mutate):
        raise ValueError("invalid_mutation_tables")
    boundaries = suite.get("numeric_boundaries", [0, 1, 100])
    if not isinstance(boundaries, list) or len(boundaries) > 16 or any(type(x) is not int or abs(x) > 10**9 for x in boundaries):
        raise ValueError("invalid_boundaries")
    rules = suite.get("required_children", [])
    if not isinstance(rules, list) or len(rules) > 20:
        raise ValueError("invalid_business_constraints")
    for rule in rules:
        if not isinstance(rule, list) or len(rule) != 3 or any(not isinstance(x, str) for x in rule):
            raise ValueError("invalid_business_constraint")
        parent, child, foreign_key = rule
        if parent not in tables or child not in tables or tables[child].get("references", {}).get(foreign_key) != [parent, tables[parent]["primary_key"]]:
            raise ValueError("invalid_business_constraint")
    return tables


def database(suite):
    tables = validate(suite)
    db = sqlite3.connect(":memory:")
    try:
        db.execute("PRAGMA foreign_keys=ON")
        for name, table in tables.items():
            fields = [f'"{c}" {kind}' + (" NOT NULL" if c not in table.get("nullable", []) else "")
                      for c, kind in table["columns"].items()]
            fields.append(f'PRIMARY KEY ("{table["primary_key"]}")')
            fields += [f'FOREIGN KEY ("{c}") REFERENCES "{ref[0]}" ("{ref[1]}")'
                       for c, ref in table.get("references", {}).items()]
            db.execute(f'CREATE TABLE "{name}" ({", ".join(fields)})')
        db.execute("BEGIN")
        db.execute("PRAGMA defer_foreign_keys=ON")
        for name, table in tables.items():
            columns = list(table["columns"])
            names = ",".join(f'"{c}"' for c in columns)
            db.executemany(f'INSERT INTO "{name}" ({names}) VALUES ({",".join("?" for _ in columns)})',
                           [[row[c] for c in columns] for row in table["rows"]])
        db.commit()
        if db.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("invalid_foreign_keys")
        for parent, child, foreign_key in suite.get("required_children", []):
            pk = tables[parent]["primary_key"]
            missing = db.execute(f'SELECT 1 FROM "{parent}" p WHERE NOT EXISTS (SELECT 1 FROM "{child}" c WHERE c."{foreign_key}"=p."{pk}") LIMIT 1').fetchone()
            if missing:
                raise ValueError("invalid_required_child")
        return db
    except Exception:
        db.close()
        raise


def query(db, sql):
    """Read-only authorizer + VM step budget; extensions and external files denied."""
    allowed = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION, sqlite3.SQLITE_RECURSIVE}

    def authorize(action, arg1, arg2, *_):
        if action not in allowed or action == sqlite3.SQLITE_FUNCTION and str(arg2).lower() in ("load_extension", "writefile", "readfile"):
            return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK

    steps = 0

    def progress():
        nonlocal steps
        steps += 100
        return steps > 100_000

    db.set_authorizer(authorize)
    db.set_progress_handler(progress, 100)
    try:
        cursor = db.execute(sql)
        rows = cursor.fetchmany(1001)
        if len(rows) > 1000:
            raise ValueError("invalid_result_limit")
        canonical(rows)
        return rows
    finally:
        db.set_authorizer(None)
        db.set_progress_handler(None, 0)


def row_key(row):
    # SQLite INTEGER 1 and REAL 1.0 compare numerically; preserve that equivalence.
    return canonical([int(x) if isinstance(x, float) and x.is_integer() else x for x in row])


def compare(suite):
    db = database(suite)
    try:
        reference = query(db, suite["reference_sql"])
        candidate = query(db, suite["candidate_sql"])
        if suite.get("ordered", False):
            equal = [row_key(r) for r in reference] == [row_key(r) for r in candidate]
        else:
            equal = Counter(row_key(r) for r in reference) == Counter(row_key(r) for r in candidate)
        return {"equal": equal, "reference": reference, "candidate": candidate,
                "mismatch_kind": "equal" if equal else "row_count" if len(reference) != len(candidate) else "row_values"}
    finally:
        db.close()


def mutations(suite):
    """Single-row mutations, retaining all declared schema constraints."""
    for name in suite.get("mutate_tables", list(suite["tables"])):
        table = suite["tables"][name]
        primary = table["primary_key"]
        for i, row in enumerate(table["rows"]):
            new = deepcopy(suite)
            del new["tables"][name]["rows"][i]
            yield {"operation": "delete_row", "table": name, "key": row[primary]}, new
            clone = deepcopy(row)
            existing = {r[primary] for r in table["rows"]}
            if table["columns"][primary] == "INTEGER":
                clone[primary] = max(existing, default=0) + 1
            else:
                value = str(row[primary]) + "_copy"
                while value in existing:
                    value += "_copy"
                clone[primary] = value
            new = deepcopy(suite)
            new["tables"][name]["rows"].append(clone)
            yield {"operation": "clone_row", "table": name, "key": row[primary], "new_key": clone[primary]}, new
            for column, value in row.items():
                if column == primary or column in table.get("references", {}):
                    continue
                options = []
                if column in table.get("nullable", []) and value is not None:
                    options.append(None)
                if table["columns"][column] in ("INTEGER", "REAL"):
                    options += suite.get("numeric_boundaries", [0, 1, 100])
                    if value is not None:
                        options += [value - 1, value + 1]
                for replacement in dict.fromkeys(options):
                    if replacement == value:
                        continue
                    new = deepcopy(suite)
                    new["tables"][name]["rows"][i][column] = replacement
                    yield {"operation": "set_cell", "table": name, "key": row[primary], "column": column,
                           "before": value, "after": replacement}, new


def cascade_delete(suite, table_name, row_index):
    trial = deepcopy(suite)
    tables = trial["tables"]
    pk = tables[table_name]["primary_key"]
    removed = {(table_name, tables[table_name]["rows"][row_index][pk])}
    changed = True
    while changed:
        changed = False
        for child_name, child in tables.items():
            for row in child["rows"]:
                identity = (child_name, row[child["primary_key"]])
                if identity in removed:
                    continue
                if any((parent[0], row[column]) in removed for column, parent in child.get("references", {}).items()):
                    removed.add(identity)
                    changed = True
    for name, table in tables.items():
        table["rows"] = [row for row in table["rows"] if (name, row[table["primary_key"]]) not in removed]
    return trial


def minimize(suite, deadline, remaining, target_kind):
    current = deepcopy(suite)
    calls = 0
    changed = True
    complete = True
    while changed:
        changed = False
        for name in list(current["tables"]):
            # Restart after every successful deletion to retain stable indices.
            for i in range(len(current["tables"][name]["rows"])):
                if calls >= remaining or time.monotonic() >= deadline:
                    return current, calls, False
                trial = cascade_delete(current, name, i)
                calls += 1
                try:
                    result = compare(trial)
                    mismatch = not result["equal"] and result["mismatch_kind"] == target_kind
                except (sqlite3.Error, ValueError):
                    continue
                if mismatch:
                    current = trial
                    changed = True
                    break
            if changed:
                break
    return current, calls, complete


def search(suite, max_depth=2, max_cases=256, seconds=3):
    validate(suite)
    if type(max_depth) is not int or not 0 <= max_depth <= 3 or type(max_cases) is not int or not 1 <= max_cases <= 2048:
        raise ValueError("invalid_search_budget")
    if type(seconds) not in (float, int) or not math.isfinite(seconds) or not 0 < seconds <= 20:
        raise ValueError("invalid_time_budget")
    deadline = time.monotonic() + seconds
    fingerprint = hashlib.sha256(canonical(suite).encode()).hexdigest()
    try:
        initial = compare(suite)
    except (sqlite3.Error, ValueError) as error:
        return {"status": "query_or_fixture_error", "error": str(error), "input_sha256": fingerprint,
                "is_business_correctness_proof": False}
    queue = deque([(suite, [], initial)])
    seen = {canonical(suite["tables"])}
    tested, invalid = 1, 0
    complete = True
    while queue:
        state, path, result = queue.popleft()
        if not result["equal"]:
            witness, calls, minimal = minimize(state, deadline, max_cases - tested, result["mismatch_kind"])
            tested += calls
            comparison = compare(witness)
            return {"status": "counterexample", "input_sha256": fingerprint, "seed_equal": initial["equal"],
                    "mutation_path": path, "witness": witness, "comparison": comparison,
                    "row_count": sum(len(t["rows"]) for t in witness["tables"].values()),
                    "row_deletion_minimal": minimal, "cases_checked": tested, "invalid_mutations": invalid,
                    "minimization_scope": "single_row_and_foreign_key_cascade_deletions",
                    "sqlite_version": sqlite3.sqlite_version, "is_business_correctness_proof": False}
        if len(path) >= max_depth:
            continue
        for mutation, trial in mutations(state):
            if tested >= max_cases or time.monotonic() >= deadline:
                complete = False
                queue.clear()
                break
            key = canonical(trial["tables"])
            if key in seen:
                continue
            seen.add(key)
            tested += 1
            try:
                result = compare(trial)
            except (sqlite3.Error, ValueError):
                invalid += 1
                continue
            # A discovered mismatch is handled immediately; exhausting the budget never loses it.
            if not result["equal"]:
                queue.appendleft((trial, path + [mutation], result))
                break
            queue.append((trial, path + [mutation], result))
    return {"status": "no_counterexample_found", "input_sha256": fingerprint, "seed_equal": initial["equal"],
            "cases_checked": tested, "invalid_mutations": invalid, "search_complete": complete,
            "max_depth": max_depth, "sqlite_version": sqlite3.sqlite_version,
            "is_business_correctness_proof": False}
