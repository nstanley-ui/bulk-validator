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
            
            # NEW: Check for intra-row consistency (values within same row that don't match)
            intra_row = self._detect_intra_row_inconsistency(row, df, idx)
            if intra_row:
                issues.extend(intra_row)
        
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


    def _detect_intra_row_inconsistency(self, row: pd.Series, df: pd.DataFrame, idx: int) -> List[Dict]:
        """
        Detect when values within the same row are inconsistent with each other.
        
        Examples:
        - Campaign: "Summer Sale - Electronics", Ad Group: "Winter Clearance - Furniture"
        - Headline: "CRM Software", Description: "Accounting Platform"
        - Campaign 5, Ad Group 12, Ad 3 (numbers don't align)
        """
        issues = []
        
        # Extract key naming columns
        campaign_col = None
        ad_group_col = None
        ad_name_col = None
        
        for col in df.columns:
            col_lower = col.lower()
            if 'campaign' in col_lower and 'status' not in col_lower:
                campaign_col = col
            elif 'ad group' in col_lower or 'adgroup' in col_lower or 'ad set' in col_lower:
                ad_group_col = col
            elif 'ad name' in col_lower:
                ad_name_col = col
        
        # Check for product/brand name inconsistencies
        text_cols = [c for c in self._find_text_columns(df) if c in row]
        name_cols = [c for c in [campaign_col, ad_group_col, ad_name_col] if c]
        all_text_cols = text_cols + name_cols
        
        # Extract potential product/brand names from all text fields
        products = self._extract_product_names(row, all_text_cols)
        
        # Only flag if we have clear evidence of DIFFERENT product categories
        if len(products) >= 2:
            product_list = list(products.keys())
            
            # Check if products are actually different categories
            different_products = []
            for i, prod1 in enumerate(product_list):
                for prod2 in product_list[i+1:]:
                    # Skip if these are likely related (e.g., "CRM" and "Software")
                    if self._are_related_products(prod1, prod2):
                        continue
                    
                    # Calculate similarity - only flag if very different
                    similarity = self._calculate_similarity(prod1.lower(), prod2.lower())
                    if similarity < 0.25:  # Very different
                        different_products.append((prod1, prod2, products[prod1], products[prod2]))
            
            # Only report if we found truly different products (high confidence)
            if len(different_products) >= 1:
                prod1, prod2, col1, col2 = different_products[0]
                confidence = 0.91 + min(0.04, len(different_products) * 0.02)
                
                issues.append({
                    'row_idx': idx,
                    'column': 'Multiple',
                    'severity': 'WARNING',
                    'message': f'Row contains references to different products/categories: "{prod1}" in {col1}, "{prod2}" in {col2}. Data may be mixed from different rows.',
                    'current_value': f'{col1}: "{prod1}" vs {col2}: "{prod2}"',
                    'suggestion': 'Verify all values in this row belong to the same product/campaign',
                    'confidence': confidence,
                    'mismatch_type': 'intra_row_product'
                })
        
        # Check for theme/season inconsistencies
        themes = self._extract_themes(row, all_text_cols)
        
        if len(themes) >= 2:
            theme_list = list(themes.keys())
            conflicting_themes = []
            
            # Check for obviously conflicting themes
            conflicts = [
                (['summer', 'spring'], ['winter', 'fall', 'autumn']),
                (['sale', 'discount', 'clearance'], ['premium', 'luxury', 'exclusive']),
                (['new', 'launch'], ['clearance', 'closeout', 'discontinued']),
            ]
            
            for theme1 in theme_list:
                for theme2 in theme_list:
                    if theme1 != theme2:
                        for conflict_set1, conflict_set2 in conflicts:
                            if any(t in theme1.lower() for t in conflict_set1) and \
                               any(t in theme2.lower() for t in conflict_set2):
                                conflicting_themes.append((theme1, theme2, themes[theme1], themes[theme2]))
            
            if conflicting_themes:
                theme1, theme2, col1, col2 = conflicting_themes[0]
                
                issues.append({
                    'row_idx': idx,
                    'column': 'Multiple',
                    'severity': 'WARNING',
                    'message': f'Row contains conflicting themes: "{theme1}" in {col1}, "{theme2}" in {col2}. May indicate mixed data.',
                    'current_value': f'{col1}: "{theme1}" vs {col2}: "{theme2}"',
                    'suggestion': 'Check if campaign theme is consistent across all fields',
                    'confidence': 0.91,
                    'mismatch_type': 'intra_row_theme'
                })
        
        # Check for numbering inconsistencies in campaign/ad group/ad names
        if campaign_col and ad_group_col and ad_name_col:
            campaign_num = self._extract_number(str(row.get(campaign_col, "")))
            ad_group_num = self._extract_number(str(row.get(ad_group_col, "")))
            ad_name_num = self._extract_number(str(row.get(ad_name_col, "")))
            
            numbers = [n for n in [campaign_num, ad_group_num, ad_name_num] if n is not None]
            
            if len(numbers) >= 2:
                # Check if numbers are wildly different (likely misaligned)
                max_num = max(numbers)
                min_num = min(numbers)
                
                # If difference is large and numbers are significant, flag it
                if max_num > 10 and (max_num - min_num) > max_num * 0.5:
                    issues.append({
                        'row_idx': idx,
                        'column': 'Multiple',
                        'severity': 'WARNING',
                        'message': f'Numbering inconsistency detected: Campaign #{campaign_num}, Ad Group #{ad_group_num}, Ad #{ad_name_num}. Numbers may be misaligned.',
                        'current_value': f'Campaign: {campaign_num}, Group: {ad_group_num}, Ad: {ad_name_num}',
                        'suggestion': 'Verify numbering sequence is correct across campaign/ad group/ad name',
                        'confidence': 0.90,
                        'mismatch_type': 'intra_row_numbering'
                    })
        
        # Check for keyword/topic inconsistencies between headlines and descriptions
        headline_cols = [c for c in df.columns if 'headline' in c.lower() and c in row]
        desc_cols = [c for c in df.columns if ('description' in c.lower() or 'intro' in c.lower() or 'text' in c.lower()) and c in row]
        
        if headline_cols and desc_cols:
            headline_keywords = set()
            for col in headline_cols:
                if not pd.isna(row[col]):
                    headline_keywords.update(self._extract_keywords(str(row[col])))
            
            desc_keywords = set()
            for col in desc_cols:
                if not pd.isna(row[col]):
                    desc_keywords.update(self._extract_keywords(str(row[col])))
            
            # Check for topic overlap
            if headline_keywords and desc_keywords:
                overlap = headline_keywords.intersection(desc_keywords)
                overlap_ratio = len(overlap) / min(len(headline_keywords), len(desc_keywords))
                
                # If there's very little overlap, topics might be different
                if overlap_ratio < 0.15 and len(headline_keywords) >= 2 and len(desc_keywords) >= 3:
                    # Extract non-overlapping keywords
                    headline_only = headline_keywords - desc_keywords
                    desc_only = desc_keywords - headline_keywords
                    
                    issues.append({
                        'row_idx': idx,
                        'column': 'Multiple',
                        'severity': 'WARNING',
                        'message': f'Headlines and descriptions mention different topics. Headlines: {", ".join(list(headline_only)[:3])}, Descriptions: {", ".join(list(desc_only)[:3])}',
                        'current_value': f'Overlap: {overlap_ratio:.0%}',
                        'suggestion': 'Verify headlines and descriptions are about the same product/offer',
                        'confidence': 0.90,
                        'mismatch_type': 'intra_row_topic'
                    })
        
        return issues
    
    def _extract_product_names(self, row: pd.Series, columns: List[str]) -> Dict[str, str]:
        """Extract potential product/brand names from text fields."""
        products = {}
        
        # Look for multi-word capitalized phrases (more likely to be product names)
        for col in columns:
            if col not in row or pd.isna(row[col]):
                continue
            
            text = str(row[col])
            
            # Pattern 1: Multiple consecutive capitalized words (e.g., "CloudStore Pro", "Sales Platform")
            multi_cap = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b', text)
            for phrase in multi_cap:
                # Verify it's not just common sentence structure
                words = phrase.split()
                if len(words) >= 2 and not any(w.lower() in ['the', 'and', 'or', 'for', 'with'] for w in words):
                    if phrase not in products:
                        products[phrase] = col
            
            # Pattern 2: Single capitalized words that appear to be product categories
            # Only flag if they're very different (e.g., "Electronics" vs "Furniture")
            product_categories = {
                'electronics', 'furniture', 'clothing', 'appliances', 'toys', 'books',
                'software', 'hardware', 'automotive', 'sports', 'beauty', 'jewelry',
                'food', 'beverages', 'shoes', 'accessories', 'tools', 'garden',
                'crm', 'accounting', 'marketing', 'analytics', 'project management'
            }
            
            text_lower = text.lower()
            for category in product_categories:
                if category in text_lower:
                    # Capitalize for consistency
                    cat_title = category.title()
                    if cat_title not in products:
                        products[cat_title] = col
        
        return products
    
    def _extract_themes(self, row: pd.Series, columns: List[str]) -> Dict[str, str]:
        """Extract themes/keywords from text fields."""
        themes = {}
        
        theme_keywords = {
            'summer', 'winter', 'spring', 'fall', 'autumn',
            'sale', 'discount', 'clearance', 'deal',
            'new', 'launch', 'release',
            'premium', 'luxury', 'exclusive',
            'back to school', 'holiday', 'black friday',
            'closeout', 'discontinued'
        }
        
        for col in columns:
            if col not in row or pd.isna(row[col]):
                continue
            
            text = str(row[col]).lower()
            
            for theme in theme_keywords:
                if theme in text:
                    if theme not in themes:
                        themes[theme] = col
        
        return themes
    
    def _extract_number(self, text: str) -> Optional[int]:
        """Extract the first significant number from text."""
        if not text:
            return None
        
        # Look for numbers in the text
        numbers = re.findall(r'\d+', text)
        
        if numbers:
            # Return the first number found
            return int(numbers[0])
        
        return None
    
    def _extract_keywords(self, text: str) -> set:
        """Extract meaningful keywords from text (excluding common words)."""
        common_words = {
            'the', 'and', 'or', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from',
            'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should',
            'can', 'could', 'may', 'might', 'must', 'your', 'our', 'their'
        }
        
        # Extract words, convert to lowercase, remove common words
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        keywords = {w for w in words if w not in common_words}
        
        return keywords
    
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate simple similarity between two strings."""
        if not str1 or not str2:
            return 0.0
        
        # Simple character overlap ratio
        set1 = set(str1)
        set2 = set(str2)
        
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        return intersection / union if union > 0 else 0.0
    
    def _are_related_products(self, prod1: str, prod2: str) -> bool:
        """Check if two product names/categories are related (same general category)."""
        prod1_lower = prod1.lower()
        prod2_lower = prod2.lower()
        
        # Filter out common column names or generic terms that aren't products
        generic_terms = {'ad group', 'campaign', 'group', 'tools', 'platform', 'software'}
        if prod1_lower in generic_terms or prod2_lower in generic_terms:
            return True  # Treat as related (ignore)
        
        # Define related product groups
        related_groups = [
            {'crm', 'software', 'sales', 'marketing', 'platform', 'automation', 'tools'},
            {'electronics', 'laptop', 'phone', 'tablet', 'computer', 'tech'},
            {'furniture', 'desk', 'chair', 'table', 'office'},
            {'clothing', 'fashion', 'apparel', 'shoes', 'accessories'},
            {'accounting', 'finance', 'bookkeeping', 'invoice', 'payroll'},
        ]
        
        # Check if both products belong to the same group
        for group in related_groups:
            in_group1 = any(term in prod1_lower for term in group)
            in_group2 = any(term in prod2_lower for term in group)
            
            if in_group1 and in_group2:
                return True
        
        return False


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
