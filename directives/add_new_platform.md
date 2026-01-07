# SOP: Adding a New Ad Platform

To add support for a new ad platform to Mojo Validator, follow these steps:

## 1. Create a Configuration File
Create a new YAML file in `configs/` (e.g., `tiktok_ads.yaml`).

## 2. Define Validators
Specify the expected columns and their constraints:
- `column`: Exact header name.
- `required`: Boolean.
- `type`: `string`, `number`, or `float`.
- `max_length`: Integer (optional).
- `values`: List of allowed values (optional).

## 3. Define Fixes (Optional)
Specify rules for automatic correction:
- `target_column`: Column to fix.
- `rule`: `truncate`, `map_values`, or `lowercase_to_uppercase`.
- `mapping`: Dict of {invalid_value: valid_value} for `map_values` rule.

## 4. Test the Integration
Run the test suite to ensure the new platform is detected and validated:
```bash
pytest tests/
```
