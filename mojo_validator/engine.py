import pandas as pd
from typing import List, Optional, Tuple, Dict, Any
from .models import Issue, ValidationResult, SummaryStats
from .config_loader import ConfigLoader
from .validation_utils import ValidationUtils, ImageVideoValidator
import re


class ValidatorEngine:
    def __init__(self, config_dir: str):
        self.config_loader = ConfigLoader(config_dir)
        self.validation_utils = ValidationUtils()
        self.image_video_validator = ImageVideoValidator()

    def validate_file(self, file_path: str, platform_override: Optional[str] = None, auto_fix: bool = False) -> Tuple[ValidationResult, pd.DataFrame]:
        """
        Core pipeline to validate and fix a file.
        
        Args:
            file_path: Path to CSV or Excel file
            platform_override: Optional platform name to skip detection
            auto_fix: If True, automatically apply fixes (default: False for safety)
        """
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
            
            # Apply Fixes to verified_df (only if auto_fix is True)
            if auto_fix:
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
        """
        Enhanced heuristic to detect platform based on headers.
        Uses weighted scoring for better accuracy.
        """
        headers = set(df.columns)
        
        # Scoring system
        scores = {
            "Google Ads": 0,
            "Meta Ads": 0,
            "LinkedIn Ads": 0,
            "Generic": 0
        }
        
        # Google Ads indicators (weight by uniqueness)
        if "Ad Group" in headers:
            scores["Google Ads"] += 10  # Very unique to Google
        if "Campaign" in headers and "Ad Group" in headers:
            scores["Google Ads"] += 5
        if "Final URL" in headers:
            scores["Google Ads"] += 3
        if "Headline 1" in headers or "Headline 2" in headers:
            scores["Google Ads"] += 5
        if "Description 1" in headers:
            scores["Google Ads"] += 5
        if "Your YouTube video" in headers:
            scores["Google Ads"] += 10
            
        # Meta Ads indicators
        if "Ad Set Name" in headers:
            scores["Meta Ads"] += 10  # Very unique to Meta
        if "Campaign Name" in headers and "Ad Set Name" in headers and "Ad Name" in headers:
            scores["Meta Ads"] += 5
        if "Primary Text" in headers:
            scores["Meta Ads"] += 5
        if "Video URL" in headers or "Video ID" in headers:
            scores["Meta Ads"] += 3
        if "Website URL" in headers:
            scores["Meta Ads"] += 3
            
        # LinkedIn Ads indicators
        if "Landing Page URL" in headers:
            scores["LinkedIn Ads"] += 10  # Very unique to LinkedIn
        if "Introduction" in headers and "Campaign Name" in headers:
            scores["LinkedIn Ads"] += 5
        if "Headline" in headers and "Introduction" in headers:
            scores["LinkedIn Ads"] += 5
        
        # Determine winner
        winner = max(scores, key=scores.get)
        max_score = scores[winner]
        
        # If score is too low, fall back to Generic
        if max_score < 8:
            return "Generic"
        
        return winner

    def _validate_row(self, idx: int, row: pd.Series, config: Dict[str, Any]) -> List[Issue]:
        """Enhanced row validation with advanced checks."""
        row_issues = []
        
        for validator in config.get('validators', []):
            col = validator['column']
            
            # Check if column exists
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
            
            # Null Check (early exit for required fields)
            if pd.isna(val):
                if validator.get('required', False):
                    row_issues.append(Issue(
                        issue_id=f"{idx}_{col}_null",
                        row_idx=idx,
                        column=col,
                        severity="BLOCKER",
                        message=validator.get('message', f"Value in {col} cannot be empty"),
                        original_value=val
                    ))
                    continue  # Skip further validation for this field
                else:
                    continue  # Skip optional null fields

            # Convert to string for text checks
            val_str = str(val).strip()
            
            # Empty string check for required fields
            if not val_str and validator.get('required', False):
                row_issues.append(Issue(
                    issue_id=f"{idx}_{col}_empty",
                    row_idx=idx,
                    column=col,
                    severity="BLOCKER",
                    message=validator.get('message', f"Value in {col} cannot be empty"),
                    original_value=val
                ))
                continue
            
            # Type-specific validation
            val_type = validator.get('type', 'string')
            
            # URL Validation
            if val_type == 'url' and val_str:
                is_valid, error_msg = self.validation_utils.validate_url(val_str)
                if not is_valid:
                    row_issues.append(Issue(
                        issue_id=f"{idx}_{col}_url",
                        row_idx=idx,
                        column=col,
                        severity="BLOCKER",
                        message=error_msg,
                        original_value=val
                    ))
                
                # Check URL length
                max_url_len = validator.get('max_length', 2048)
                is_valid, error_msg = self.validation_utils.check_url_length(val_str, max_url_len)
                if not is_valid:
                    row_issues.append(Issue(
                        issue_id=f"{idx}_{col}_url_len",
                        row_idx=idx,
                        column=col,
                        severity="WARNING",
                        message=error_msg,
                        original_value=val
                    ))
            
            # Number Validation
            if val_type in ['number', 'float', 'integer']:
                min_val = validator.get('min')
                max_val = validator.get('max')
                is_valid, error_msg = self.validation_utils.validate_number_range(val, min_val, max_val)
                if not is_valid:
                    row_issues.append(Issue(
                        issue_id=f"{idx}_{col}_number",
                        row_idx=idx,
                        column=col,
                        severity="BLOCKER",
                        message=error_msg,
                        original_value=val
                    ))

            # Value list check
            if 'values' in validator and val not in validator['values']:
                # Try case-insensitive match
                val_lower = str(val).lower()
                valid_values_lower = [str(v).lower() for v in validator['values']]
                
                if val_lower not in valid_values_lower:
                    row_issues.append(Issue(
                        issue_id=f"{idx}_{col}_value",
                        row_idx=idx,
                        column=col,
                        severity="BLOCKER",
                        message=validator.get('message', f"Value '{val}' not in allowed list: {validator['values']}"),
                        original_value=val,
                        suggested_fix=f"Change to one of {validator['values']}"
                    ))

            # Length check
            if 'max_length' in validator and isinstance(val, str):
                val_len = len(val_str)
                max_len = validator['max_length']
                recommended_max = validator.get('recommended_max', max_len)
                
                if val_len > max_len:
                    # Generate intelligent truncation suggestion
                    truncated = self._smart_truncate(val_str, max_len)
                    
                    row_issues.append(Issue(
                        issue_id=f"{idx}_{col}_len",
                        row_idx=idx,
                        column=col,
                        severity="BLOCKER",
                        message=validator.get('message', f"Value exceeds max length of {max_len} characters (currently {val_len})"),
                        original_value=val,
                        suggested_fix=f'"{truncated}"'
                    ))
                elif val_len > recommended_max:
                    # Warning for exceeding recommended length
                    truncated_recommended = self._smart_truncate(val_str, recommended_max)
                    
                    row_issues.append(Issue(
                        issue_id=f"{idx}_{col}_len_warn",
                        row_idx=idx,
                        column=col,
                        severity="WARNING",
                        message=f"Value exceeds recommended length of {recommended_max} characters (currently {val_len}). May be truncated on some devices.",
                        original_value=val,
                        suggested_fix=f'"{truncated_recommended}"'
                    ))
            
            # Regex check
            if 'regex' in validator and isinstance(val, str):
                if not re.match(validator['regex'], val_str):
                    row_issues.append(Issue(
                        issue_id=f"{idx}_{col}_regex",
                        row_idx=idx,
                        column=col,
                        severity="BLOCKER",
                        message=validator.get('message', f"Value does not match required format"),
                        original_value=val
                    ))
            
            # Advanced validations (only for text fields)
            if isinstance(val, str) and val_str:
                # Capitalization check
                is_valid, warning = self.validation_utils.check_excessive_capitalization(val_str)
                if not is_valid:
                    row_issues.append(Issue(
                        issue_id=f"{idx}_{col}_caps",
                        row_idx=idx,
                        column=col,
                        severity="WARNING",
                        message=warning,
                        original_value=val
                    ))
                
                # Special characters check
                prohibited = validator.get('prohibited_chars', [])
                if prohibited:
                    is_valid, warning = self.validation_utils.check_special_characters(val_str, prohibited)
                    if not is_valid:
                        row_issues.append(Issue(
                            issue_id=f"{idx}_{col}_special",
                            row_idx=idx,
                            column=col,
                            severity="WARNING",
                            message=warning,
                            original_value=val
                        ))
                
                # Character encoding check
                is_valid, warning = self.validation_utils.validate_character_encoding(val_str)
                if not is_valid:
                    row_issues.append(Issue(
                        issue_id=f"{idx}_{col}_encoding",
                        row_idx=idx,
                        column=col,
                        severity="WARNING",
                        message=warning,
                        original_value=val
                    ))
                
                # Emoji check
                is_valid, warning = self.validation_utils.check_emoji_usage(val_str)
                if not is_valid:
                    row_issues.append(Issue(
                        issue_id=f"{idx}_{col}_emoji",
                        row_idx=idx,
                        column=col,
                        severity="WARNING",
                        message=warning,
                        original_value=val
                    ))
            
            # Image/Video format validation
            if 'Image' in col and val_str:
                is_valid, error = self.image_video_validator.validate_image_format(val_str)
                if not is_valid:
                    row_issues.append(Issue(
                        issue_id=f"{idx}_{col}_format",
                        row_idx=idx,
                        column=col,
                        severity="WARNING",
                        message=error,
                        original_value=val
                    ))
            
            if 'Video' in col and val_str:
                is_valid, error = self.image_video_validator.validate_video_format(val_str)
                if not is_valid:
                    row_issues.append(Issue(
                        issue_id=f"{idx}_{col}_format",
                        row_idx=idx,
                        column=col,
                        severity="WARNING",
                        message=error,
                        original_value=val
                    ))

        return row_issues

    def _apply_fixes(self, idx: int, df: pd.DataFrame, issues: List[Issue], config: Dict[str, Any]):
        """
        Applies deterministic fixes based on config.
        Now respects auto_apply flag to prevent unwanted changes.
        """
        for issue in issues:
            if not issue.suggested_fix:
                continue

            # Check if this fix type should auto-apply
            auto_apply = False
            for fix in config.get('fixes', []):
                if fix['target_column'] == issue.column:
                    auto_apply = fix.get('auto_apply', False)
                    break
            
            if not auto_apply:
                # Don't auto-apply, just mark the issue
                continue

            # Apply the fix
            if issue.suggested_fix.startswith('"') and issue.suggested_fix.endswith('"'):
                # Truncated text suggestion (remove quotes)
                df.at[idx, issue.column] = issue.suggested_fix[1:-1]
            
            elif "Change to one of" in issue.suggested_fix:
                # Value mapping fix logic
                for fix in config.get('fixes', []):
                    if fix['target_column'] == issue.column:
                        if fix['rule'] == "map_values":
                            mapping = fix.get('mapping', {})
                            orig = str(issue.original_value).lower()
                            for key, replacement in mapping.items():
                                if key.lower() == orig:
                                    df.at[idx, issue.column] = replacement
                                    break
                        elif fix['rule'] == "lowercase_to_uppercase":
                            df.at[idx, issue.column] = str(df.at[idx, issue.column]).upper()

    def _smart_truncate(self, text: str, max_length: int) -> str:
        """
        Intelligently truncate text to max_length, trying to preserve whole words.
        Adds ellipsis (...) if truncated.
        
        Args:
            text: Original text
            max_length: Maximum character length
            
        Returns:
            Truncated text with ellipsis if needed
        """
        if len(text) <= max_length:
            return text
        
        # Reserve 3 characters for ellipsis
        target_length = max_length - 3
        
        if target_length < 10:
            # If too short for smart truncation, just hard truncate
            return text[:max_length]
        
        # Truncate to target length
        truncated = text[:target_length]
        
        # Try to truncate at last complete word
        last_space = truncated.rfind(' ')
        if last_space > target_length * 0.7:  # Only if we don't lose more than 30%
            truncated = truncated[:last_space]
        
        # Add ellipsis
        return truncated.rstrip() + "..."

    def _generate_summary(self, df: pd.DataFrame, issues: List[Issue]) -> SummaryStats:
        """Generate validation summary statistics."""
        total_rows = len(df)
        rows_with_issues = len(set(i.row_idx for i in issues))
        
        severity_counts = {"BLOCKER": 0, "WARNING": 0}
        for i in issues:
            severity_counts[i.severity] = severity_counts.get(i.severity, 0) + 1

        return SummaryStats(
            total_rows=total_rows,
            clean_rows=total_rows - rows_with_issues,
            rows_with_issues=rows_with_issues,
            total_issues=len(issues),
            severity_counts=severity_counts
        )
