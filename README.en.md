# SQL Meaning Mutator

[Français](README.md) · [Español](README.es.md)

**A SQL query can pass a test yet double revenue. This lab produces the small database that demonstrates it.**

The engine executes a candidate and a supplied reference query, mutates relational data, and reduces the counterexample. No LLM, key or live database: queries execute in real in-memory SQLite databases.

![Synthetic SQLite counterexample with four rows](docs/preview-fr.png)

## Try it

Python 3.11 or newer, standard library only.

```sh
python3 -m sql_meaning serve --lang en
```

Open `http://127.0.0.1:8766/?lang=en`. The seed fixture passes; click to search for a counterexample. A duplicated order line changes the total from **2,000 to 4,000 cents**. The reduced witness retains four rows and all declared constraints. Then try the reference query: absence of a witness is never presented as correctness proof.

```sh
python3 -m sql_meaning search sql_meaning/examples/revenue.json > report.json
python3 -m sql_meaning search my-contract.json
python3 -m sql_meaning compare sql-counterexample.json
```

Exit **1**: counterexample or difference; **0**: no witness found or equal results; **2**: invalid input or initial query. `pip install .` also provides `sql-meaning`. CLI and UI support FR/EN/ES.

## Executable contract

A JSON case contains `tables`, `reference_sql`, `candidate_sql` and optionally:

- `mutate_tables`: restrict tables that may change;
- `numeric_boundaries`: boundary values to explore;
- `required_children`: business rules requiring each parent row to have a child, represented by `[parent_table, child_table, foreign_key]`;
- `ordered: true`: compare row order. By default, comparison uses multisets and preserves duplicates.

Supported schema: `INTEGER`, `REAL`, `TEXT`, simple primary keys, simple foreign keys and explicit nullability. Every row supplies every column. Mutations clone or delete rows, introduce allowed `NULL` values, and explore numeric boundaries and neighboring values. Primary keys, foreign keys, types and required children are checked before accepting a witness.

Breadth-first search is bounded by depth, cases and time. After a mismatch, reduction attempts deletions with foreign-key dependency closure. It preserves the mismatch category: row count or values. `row_deletion_minimal` is true only after exhausting those reductions; **it is not a global minimum**, nor proof of the business cause. Exhausted budgets preserve the witness and leave minimality unproven.

Reports bind the initial case to a SHA-256 fingerprint, explain the mutation, show both results and include the reduced case. Browser exports replay directly with `compare`.

## What it does not prove

The reference is a supplied hypothesis, not discovered truth. Shared query defects or gaps in mutation coverage may produce no witness. Missing business constraints are not inferred. `search_complete` only means the configured bounded space was explored. Non-integral floats use exact comparison; use integer cents for financial examples.

The search targets SQLite, not general equivalence across PostgreSQL, DuckDB or MariaDB dialects. Writes, `ATTACH`, pragmas and extension/file-loading functions are denied during evaluation; SQL work and result count are bounded. This is not operating-system isolation against adversaries: add process/container isolation for genuinely hostile queries.

## Existing tools and difference

[SQLancer](https://github.com/sqlancer/sqlancer) searches for database-engine defects. [Test Suite SQL Evaluation](https://github.com/taoyds/test-suite-sql-eval) uses execution suites to evaluate queries. This project draws on those ideas without claiming new theory: it searches for **a relational counterexample around two supplied business queries**, preserving declared constraints and exporting a locally minimal case. [Query Contract CI](https://github.com/gbesse/query-contract-ci) checks existing contracts; here, fixtures mutate to challenge their coverage. No SOTA result is claimed.

## Validation

```sh
python3 -m unittest discover -s tests -v
npm ci
npx playwright install chromium
npm run test:browser
npm run format:check
```

Sixteen tests cover the join witness, reduction, numeric boundaries, `NULL`, multiplicity, order, constraints, budgets and write/loading denial. Browser flows cover FR/EN/ES and mobile; CI checks Python 3.11/3.12 and wheel installation outside sources. MIT license; research alpha on synthetic data.
