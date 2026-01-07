from mojo_validator.engine import ValidatorEngine
import os

def test_engine():
    engine = ValidatorEngine("configs")
    test_file = ".tmp/test_linkedin.csv"
    
    print(f"Testing validation on {test_file}...")
    result, verified_df = engine.validate_file(test_file)
    
    print(f"Platform Detected: {result.platform}")
    print(f"Total Issues: {result.summary.total_issues}")
    
    for issue in result.issues:
        print(f"Row {issue.row_idx} | {issue.column}: {issue.message} (Value: {issue.original_value})")

    print("\nVerified Data (First 2 rows):")
    print(verified_df.head(2))
    
    # Check if "paused" was fixed to "PAUSED" if we implemented that (let's check config)
    # Actually my engine implementation for fixes was a placeholder for "truncate".
    # I'll update the engine to support more fixes if needed.

if __name__ == "__main__":
    test_engine()
