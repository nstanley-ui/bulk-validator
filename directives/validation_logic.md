# SOP: Validation and Fixing Logic

The Mojo Validator engine operates in three distinct phases:

## 1. Ingestion & Detection
- Files (CSV/Excel) are loaded into Memory using `pandas`.
- The platform is detected using a heuristic based on column headers in `ValidatorEngine._detect_platform`.

## 2. Validation Cycle
- Each row is iterated.
- The `_validate_row` method checks each cell against the rules defined in the platform's YAML configuration.
- Issues are categorized as `BLOCKER` (missing data) or `WARNING` (formatting/limits).

## 3. Deterministic Fixing
- For every issue found, the engine checks if a `suggested_fix` is available.
- If the column has an associated `fixes` rule in the config, the `verified_df` is modified in-place.
- All fixes are logged in the `ErrorReport`.
