import pandas as pd
from typing import List, Optional, Tuple, Dict, Any
from .models import Issue, ValidationResult, SummaryStats, SummaryStats
from .config_loader import ConfigLoader

class ValidatorEngine:
    def __init__(self, config_dir: str):
        self.config_loader = ConfigLoader(config_dir)

    def validate_file(self, file_path: str, platform_override: Optional[str] = None) -> Tuple[ValidationResult, pd.DataFrame]:
        """Core pipeline to validate and fix a file."""
        # Process ingestion
        ext = file_path.split('.')[-1].lower()
        if ext == 'csv':
            df = pd.read_csv(file_path)
        elif ext in ['xls', 'xlsx']:
            df = pd.read_excel(file_path)
        else:
            raise ValueError(f"Unsupported file extension: {ext}")

        # Detect platform if not overridden
        platform = platform_override or self._detect_platform(df)
        config = self.config_loader.get_config(platform)

        issues = []
        verified_df = df.copy()

        # Validation Loop
        for idx, row in df.iterrows():
            row_issues = self._validate_row(idx, row, config)
            issues.extend(row_issues)
            
            # Apply Fixes to verified_df
            self._apply_fixes(idx, verified_df, row_issues, config)

        # Generate Summary
        summary = self._generate_summary(df, issues)
        
        result = ValidationResult(
            platform=platform,
            issues=issues,
            summary=summary
        )

        return result, verified_df

    def _detect_platform(self, df: pd.DataFrame) -> str:
        """Heuristic to detect platform based on headers."""
        headers = set(df.columns)
        # Google Detection
        if "Your YouTube video" in headers:
            return "Google Video Ads"
        if "Campaign" in headers and "Ad Group" in headers:
            return "Google Ads"
        
        # Meta Detection
        if "Video URL" in headers or "Video ID" in headers:
            return "Meta Video Ads"
        if "Campaign Name" in headers and "Ad Set Name" in headers and "Ad Name" in headers:
            return "Meta Ads"
        
        # LinkedIn Detection
        if "Landing Page URL" in headers and "Introduction" in headers:
            return "LinkedIn Video Ads"
        if "Campaign Name" in headers and "Headline" in headers and "Introduction" in headers:
            return "LinkedIn Ads"
        
        return "Generic"

    def _validate_row(self, idx: int, row: pd.Series, config: Dict[str, Any]) -> List[Issue]:
        row_issues = []
        for validator in config.get('validators', []):
            col = validator['column']
            if col not in row:
                if validator.get('required', False):
                    row_issues.append(Issue(
                        issue_id=f"{idx}_{col}_missing",
                        row_idx=idx,
                        column=col,
                        severity="BLOCKER",
                        message=f"Missing required column: {col}",
                        original_value=None
                    ))
                continue

            val = row[col]
            
            # Null Check
            if pd.isna(val) and validator.get('required', False):
                 row_issues.append(Issue(
                        issue_id=f"{idx}_{col}_null",
                        row_idx=idx,
                        column=col,
                        severity="BLOCKER",
                        message=f"Value in {col} cannot be empty",
                        original_value=val
                    ))

            # Value list check
            if 'values' in validator and val not in validator['values']:
                 row_issues.append(Issue(
                        issue_id=f"{idx}_{col}_value",
                        row_idx=idx,
                        column=col,
                        severity="WARNING",
                        message=f"Value '{val}' not in allowed list: {validator['values']}",
                        original_value=val,
                        suggested_fix=f"Change to one of {validator['values']}"
                    ))

            # Length check
            if 'max_length' in validator and isinstance(val, str) and len(val) > validator['max_length']:
                 row_issues.append(Issue(
                        issue_id=f"{idx}_{col}_len",
                        row_idx=idx,
                        column=col,
                        severity="WARNING",
                        message=f"Value exceeds max length of {validator['max_length']}",
                        original_value=val,
                        suggested_fix="Truncate"
                    ))
            
            # Regex check
            if 'regex' in validator and isinstance(val, str):
                import re
                if not re.match(validator['regex'], val):
                    row_issues.append(Issue(
                        issue_id=f"{idx}_{col}_regex",
                        row_idx=idx,
                        column=col,
                        severity="WARNING",
                        message=validator.get('message', f"Value does not match required format"),
                        original_value=val
                    ))

        return row_issues

    def _apply_fixes(self, idx: int, df: pd.DataFrame, issues: List[Issue], config: Dict[str, Any]):
        """Applies deterministic fixes based on config."""
        for issue in issues:
            if not issue.suggested_fix:
                continue

            # Check if there's a specific fix defined in the config for this rule/trigger
            # For now, we map the suggested_fix string to logic
            if issue.suggested_fix == "Truncate":
                max_len = next((v['max_length'] for v in config.get('validators', []) if v['column'] == issue.column), None)
                if max_len:
                    df.at[idx, issue.column] = str(df.at[idx, issue.column])[:max_len]
            
            elif "Change to one of" in issue.suggested_fix:
                # Value mapping fix logic
                # Look for 'fixes' in config
                for fix in config.get('fixes', []):
                    if fix['target_column'] == issue.column:
                        if fix['rule'] == "map_values":
                            mapping = fix.get('mapping', {})
                            orig = str(issue.original_value).lower()
                            # Check if the lowercase version matches any key in our mapping
                            for key, replacement in mapping.items():
                                if key.lower() == orig:
                                    df.at[idx, issue.column] = replacement
                                    break
                        elif fix['rule'] == "lowercase_to_uppercase":
                             df.at[idx, issue.column] = str(df.at[idx, issue.column]).upper()

    def _generate_summary(self, df: pd.DataFrame, issues: List[Issue]) -> SummaryStats:
        total_rows = len(df)
        rows_with_issues = len(set(i.row_idx for i in issues))
        
        severity_counts = {"BLOCKER": 0, "WARNING": 0, "PASS": 0}
        for i in issues:
            severity_counts[i.severity] = severity_counts.get(i.severity, 0) + 1

        return SummaryStats(
            total_rows=total_rows,
            clean_rows=total_rows - rows_with_issues,
            rows_with_issues=rows_with_issues,
            total_issues=len(issues),
            severity_counts=severity_counts
        )
