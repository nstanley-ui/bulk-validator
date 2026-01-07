"""
Pattern Mismatch Detection Module

Detects when values are likely in the wrong column by analyzing patterns
across the entire dataset. Only flags when 90%+ confident of an error.

Examples of detectable mismatches:
- URLs in headline fields
- Headlines in description fields
- Campaign names in ad name fields
- Business names that look like URLs
- Very short descriptions when others are long
- Numbers/IDs in text fields
"""

import re
from typing import List, Dict, Tuple, Optional
from collections import Counter
import pandas as pd


class PatternMismatchDetector:
    """Detects likely data entry errors by analyzing column patterns."""
    
    def __init__(self):
        self.confidence_threshold = 0.90  # 90% confidence required
        
    def detect_mismatches(self, df: pd.DataFrame, platform: str) -> List[Dict]:
        """
        Detect pattern mismatches across all rows.
        
        Returns list of issues with high confidence of being errors.
        """
        issues = []
        
        # Analyze patterns for each column type
        url_columns = self._find_url_columns(df)
        text_columns = self._find_text_columns(df)
        name_columns = self._find_name_columns(df)
        
        # Check each row for mismatches
        for idx, row in df.iterrows():
            # Check for URLs in text fields
            url_in_text = self._detect_url_in_text_field(row, text_columns, idx)
            if url_in_text:
                issues.extend(url_in_text)
            
            # Check for text in URL fields
            text_in_url = self._detect_text_in_url_field(row, url_columns, idx)
            if text_in_url:
                issues.extend(text_in_url)
            
            # Check for swapped headline/description
            swapped = self._detect_swapped_text_fields(row, df, idx, platform)
            if swapped:
                issues.extend(swapped)
            
            # Check for campaign/ad name confusion
            name_confusion = self._detect_name_confusion(row, df, idx)
            if name_confusion:
                issues.extend(name_confusion)
            
            # Check for pattern outliers
            outliers = self._detect_pattern_outliers(row, df, idx)
            if outliers:
                issues.extend(outliers)
        
        return issues
    
    def _find_url_columns(self, df: pd.DataFrame) -> List[str]:
        """Identify columns that should contain URLs."""
        url_keywords = ['url', 'link', 'website', 'page', 'domain', 'video', 'image', 'logo', 'media', 'thumbnail']
        return [col for col in df.columns if any(kw in col.lower() for kw in url_keywords)]
    
    def _find_text_columns(self, df: pd.DataFrame) -> List[str]:
        """Identify columns that should contain marketing text."""
        text_keywords = ['headline', 'description', 'text', 'intro', 'primary', 'body', 'copy']
        return [col for col in df.columns if any(kw in col.lower() for kw in text_keywords)]
    
    def _find_name_columns(self, df: pd.DataFrame) -> List[str]:
        """Identify columns for names (campaign, ad, etc)."""
        name_keywords = ['campaign', 'ad group', 'ad name', 'name', 'set']
        return [col for col in df.columns if any(kw in col.lower() for kw in name_keywords)]
    
    def _is_url(self, value: str) -> bool:
        """Check if string looks like a URL."""
        if pd.isna(value) or not isinstance(value, str):
            return False
        
        url_pattern = r'https?://|www\.|\.com|\.net|\.org|\.io|//'
        return bool(re.search(url_pattern, value, re.IGNORECASE))
    
    def _detect_url_in_text_field(self, row: pd.Series, text_columns: List[str], idx: int) -> List[Dict]:
        """Detect URLs mistakenly placed in text fields."""
        issues = []
        
        for col in text_columns:
            if col not in row or pd.isna(row[col]):
                continue
            
            value = str(row[col])
            
            # Check if this looks like a URL
            if self._is_url(value):
                # High confidence this is wrong
                issues.append({
                    'row_idx': idx,
                    'column': col,
                    'severity': 'BLOCKER',
                    'message': f'URL detected in text field "{col}". This appears to be a data entry error.',
                    'current_value': value,
                    'suggestion': 'Move this URL to the appropriate URL column',
                    'confidence': 0.95,
                    'mismatch_type': 'url_in_text'
                })
        
        return issues
    
    def _detect_text_in_url_field(self, row: pd.Series, url_columns: List[str], idx: int) -> List[Dict]:
        """Detect marketing text mistakenly placed in URL fields."""
        issues = []
        
        for col in url_columns:
            if col not in row or pd.isna(row[col]):
                continue
            
            value = str(row[col])
            
            # Skip if it's actually a URL
            if self._is_url(value):
                continue
            
            # Check if this looks like marketing text (has marketing words)
            marketing_indicators = [
                'free', 'trial', 'today', 'now', 'get', 'save', 'buy', 'shop',
                'learn', 'discover', 'try', 'start', 'join', 'best', 'top'
            ]
            
            lower_value = value.lower()
            has_marketing_words = sum(1 for word in marketing_indicators if word in lower_value) >= 2
            has_spaces = ' ' in value
            is_sentence = value.count(' ') >= 3
            
            if (has_marketing_words or is_sentence) and has_spaces:
                issues.append({
                    'row_idx': idx,
                    'column': col,
                    'severity': 'BLOCKER',
                    'message': f'Marketing text detected in URL field "{col}". This appears to be a data entry error.',
                    'current_value': value,
                    'suggestion': 'Move this text to the appropriate text column',
                    'confidence': 0.92,
                    'mismatch_type': 'text_in_url'
                })
        
        return issues
    
    def _detect_swapped_text_fields(self, row: pd.Series, df: pd.DataFrame, idx: int, platform: str) -> List[Dict]:
        """Detect when headline and description might be swapped."""
        issues = []
        
        # Find headline and description columns
        headline_cols = [col for col in df.columns if 'headline' in col.lower()]
        desc_cols = [col for col in df.columns if 'description' in col.lower() or 'intro' in col.lower()]
        
        for h_col in headline_cols:
            for d_col in desc_cols:
                if h_col not in row or d_col not in row:
                    continue
                
                headline = str(row[h_col]) if not pd.isna(row[h_col]) else ""
                desc = str(row[d_col]) if not pd.isna(row[d_col]) else ""
                
                if not headline or not desc:
                    continue
                
                # Calculate typical lengths in the dataset
                h_lengths = df[h_col].dropna().astype(str).str.len()
                d_lengths = df[d_col].dropna().astype(str).str.len()
                
                if len(h_lengths) < 3 or len(d_lengths) < 3:
                    continue
                
                avg_h_len = h_lengths.mean()
                avg_d_len = d_lengths.mean()
                
                # Check if this row's values are backwards
                # Headline should typically be shorter than description
                if len(headline) > len(desc) * 1.5 and len(desc) < avg_h_len * 0.8:
                    # This headline is suspiciously long and desc is short
                    confidence = min(0.95, 0.70 + (len(headline) / len(desc)) * 0.1)
                    
                    if confidence >= self.confidence_threshold:
                        issues.append({
                            'row_idx': idx,
                            'column': h_col,
                            'severity': 'WARNING',
                            'message': f'Headline appears too long and description too short. Values may be swapped.',
                            'current_value': headline[:50] + '...' if len(headline) > 50 else headline,
                            'suggestion': f'Consider swapping "{h_col}" with "{d_col}"',
                            'confidence': confidence,
                            'mismatch_type': 'swapped_fields'
                        })
        
        return issues
    
    def _detect_name_confusion(self, row: pd.Series, df: pd.DataFrame, idx: int) -> List[Dict]:
        """Detect when campaign/ad group/ad names might be confused."""
        issues = []
        
        # Look for naming columns
        campaign_col = None
        ad_group_col = None
        ad_name_col = None
        
        for col in df.columns:
            col_lower = col.lower()
            if 'campaign' in col_lower and 'name' in col_lower:
                campaign_col = col
            elif 'ad group' in col_lower or 'adgroup' in col_lower or 'ad set' in col_lower:
                ad_group_col = col
            elif 'ad name' in col_lower:
                ad_name_col = col
        
        # Check if campaign name appears in ad name
        if campaign_col and ad_name_col:
            if campaign_col in row and ad_name_col in row:
                campaign = str(row[campaign_col]) if not pd.isna(row[campaign_col]) else ""
                ad_name = str(row[ad_name_col]) if not pd.isna(row[ad_name_col]) else ""
                
                # Check if ad name looks like a campaign name (has campaign keywords)
                campaign_keywords = ['campaign', 'search', 'display', 'video', 'brand', 'performance']
                ad_has_campaign_words = sum(1 for word in campaign_keywords if word.lower() in ad_name.lower()) >= 2
                
                # Also check if it matches other campaign names
                campaign_names = df[campaign_col].dropna().unique()
                matches_other_campaign = any(ad_name == c for c in campaign_names if c != campaign)
                
                if ad_has_campaign_words or matches_other_campaign:
                    issues.append({
                        'row_idx': idx,
                        'column': ad_name_col,
                        'severity': 'WARNING',
                        'message': f'Ad name "{ad_name}" looks like a campaign name. May be misplaced data.',
                        'current_value': ad_name,
                        'suggestion': 'Verify this is the correct ad name, not a campaign name',
                        'confidence': 0.91,
                        'mismatch_type': 'name_confusion'
                    })
        
        return issues
    
    def _detect_pattern_outliers(self, row: pd.Series, df: pd.DataFrame, idx: int) -> List[Dict]:
        """Detect values that don't match the pattern of other values in the same column."""
        issues = []
        
        text_columns = self._find_text_columns(df)
        
        for col in text_columns:
            if col not in row or pd.isna(row[col]):
                continue
            
            value = str(row[col])
            
            # Get all values in this column
            col_values = df[col].dropna().astype(str)
            
            if len(col_values) < 5:  # Need enough data to detect patterns
                continue
            
            # Check for numeric-heavy outliers in text fields
            digit_ratio = sum(c.isdigit() for c in value) / max(len(value), 1)
            avg_digit_ratio = col_values.apply(lambda x: sum(c.isdigit() for c in x) / max(len(x), 1)).mean()
            
            if digit_ratio > 0.5 and avg_digit_ratio < 0.1:
                # This value is mostly numbers but others aren't
                issues.append({
                    'row_idx': idx,
                    'column': col,
                    'severity': 'WARNING',
                    'message': f'Value in "{col}" is mostly numeric ({int(digit_ratio*100)}%) while others are text. May be wrong column.',
                    'current_value': value,
                    'suggestion': 'Verify this value belongs in this column',
                    'confidence': 0.90,
                    'mismatch_type': 'pattern_outlier'
                })
            
            # Check for very short values when others are long
            lengths = col_values.str.len()
            avg_length = lengths.mean()
            std_length = lengths.std()
            
            if len(value) < avg_length - (2.5 * std_length) and avg_length > 30:
                # This value is abnormally short
                confidence = min(0.95, 0.85 + (avg_length - len(value)) / avg_length * 0.1)
                
                if confidence >= self.confidence_threshold:
                    issues.append({
                        'row_idx': idx,
                        'column': col,
                        'severity': 'WARNING',
                        'message': f'Value in "{col}" is unusually short ({len(value)} chars vs avg {int(avg_length)}). May be incomplete or wrong column.',
                        'current_value': value,
                        'suggestion': 'Verify this value is complete and in the right column',
                        'confidence': confidence,
                        'mismatch_type': 'length_outlier'
                    })
        
        return issues


def detect_pattern_mismatches(df: pd.DataFrame, platform: str) -> List[Dict]:
    """
    Main function to detect pattern mismatches in a dataframe.
    
    Args:
        df: DataFrame to analyze
        platform: Platform name (for context)
    
    Returns:
        List of mismatch issues with high confidence
    """
    detector = PatternMismatchDetector()
    return detector.detect_mismatches(df, platform)
