"""
Validation utilities for advanced checks.
Handles URL validation, capitalization checks, special characters, etc.
"""

import re
from typing import Optional, List, Tuple
from urllib.parse import urlparse


class ValidationUtils:
    """Utility class for advanced validation checks."""
    
    @staticmethod
    def validate_url(url: str) -> Tuple[bool, Optional[str]]:
        """
        Validate if a string is a properly formatted URL.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not url or not isinstance(url, str):
            return False, "URL is required"
        
        url = str(url).strip()
        
        # Check for protocol
        if not re.match(r'^https?://', url, re.IGNORECASE):
            return False, "URL must start with http:// or https://"
        
        # Try to parse URL
        try:
            result = urlparse(url)
            # Check if domain exists
            if not result.netloc:
                return False, "URL must include a domain name"
            
            # Check for spaces (invalid in URLs)
            if ' ' in url:
                return False, "URL cannot contain spaces"
            
            # Check for common mistakes
            if url.count('://') > 1:
                return False, "URL has malformed protocol"
                
            return True, None
            
        except Exception as e:
            return False, f"Invalid URL format: {str(e)}"
    
    @staticmethod
    def check_excessive_capitalization(text: str, max_ratio: float = 0.5) -> Tuple[bool, Optional[str]]:
        """
        Check if text has excessive capitalization (spam trigger).
        
        Args:
            text: Text to check
            max_ratio: Maximum ratio of uppercase letters (default 0.5 = 50%)
            
        Returns:
            Tuple of (is_valid, warning_message)
        """
        if not text or not isinstance(text, str):
            return True, None
        
        # Count letters only (ignore numbers, spaces, punctuation)
        letters = [c for c in text if c.isalpha()]
        if not letters:
            return True, None
        
        uppercase_count = sum(1 for c in letters if c.isupper())
        ratio = uppercase_count / len(letters)
        
        if ratio > max_ratio:
            return False, f"Excessive capitalization ({int(ratio*100)}% uppercase). Recommended: {int(max_ratio*100)}% or less to avoid spam filters"
        
        # Check for ALL CAPS (special case)
        if ratio == 1.0 and len(letters) > 3:
            return False, "ALL CAPS text may be rejected or perform poorly"
        
        return True, None
    
    @staticmethod
    def check_special_characters(text: str, prohibited_chars: List[str] = None) -> Tuple[bool, Optional[str]]:
        """
        Check for prohibited or excessive special characters.
        
        Args:
            text: Text to check
            prohibited_chars: List of prohibited characters
            
        Returns:
            Tuple of (is_valid, warning_message)
        """
        if not text or not isinstance(text, str):
            return True, None
        
        if prohibited_chars is None:
            prohibited_chars = []
        
        found_chars = []
        for char in prohibited_chars:
            if char in text:
                found_chars.append(char)
        
        if found_chars:
            return False, f"Contains prohibited characters: {', '.join(found_chars)}"
        
        # Check for excessive punctuation
        punctuation_count = sum(1 for c in text if c in '!?*')
        if punctuation_count > 2:
            return False, f"Excessive punctuation ({punctuation_count} exclamation/question marks). Use sparingly for better performance"
        
        return True, None
    
    @staticmethod
    def check_url_length(url: str, max_length: int = 2048) -> Tuple[bool, Optional[str]]:
        """
        Check if URL is within acceptable length.
        
        Args:
            url: URL to check
            max_length: Maximum allowed length
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not url:
            return True, None
        
        url_len = len(str(url))
        if url_len > max_length:
            return False, f"URL is {url_len} characters, maximum is {max_length}"
        
        return True, None
    
    @staticmethod
    def extract_domain(url: str) -> Optional[str]:
        """
        Extract domain from URL.
        
        Args:
            url: URL to parse
            
        Returns:
            Domain name or None if invalid
        """
        try:
            parsed = urlparse(url)
            return parsed.netloc
        except:
            return None
    
    @staticmethod
    def validate_number_range(value: any, min_val: float = None, max_val: float = None) -> Tuple[bool, Optional[str]]:
        """
        Validate if a number is within acceptable range.
        
        Args:
            value: Value to check
            min_val: Minimum allowed value
            max_val: Maximum allowed value
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            num = float(value)
            
            if min_val is not None and num < min_val:
                return False, f"Value {num} is below minimum of {min_val}"
            
            if max_val is not None and num > max_val:
                return False, f"Value {num} exceeds maximum of {max_val}"
            
            return True, None
            
        except (ValueError, TypeError):
            return False, f"'{value}' is not a valid number"
    
    @staticmethod
    def check_emoji_usage(text: str, max_count: int = 3) -> Tuple[bool, Optional[str]]:
        """
        Check emoji usage in text.
        
        Args:
            text: Text to check
            max_count: Maximum number of emojis allowed
            
        Returns:
            Tuple of (is_valid, warning_message)
        """
        if not text:
            return True, None
        
        # Simple emoji detection (Unicode ranges)
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "]+",
            flags=re.UNICODE
        )
        
        emojis = emoji_pattern.findall(text)
        emoji_count = len(emojis)
        
        if emoji_count > max_count:
            return False, f"Contains {emoji_count} emojis. Recommended: {max_count} or fewer for professional ads"
        
        return True, None
    
    @staticmethod
    def validate_character_encoding(text: str) -> Tuple[bool, Optional[str]]:
        """
        Check for problematic characters that might not render correctly.
        
        Args:
            text: Text to check
            
        Returns:
            Tuple of (is_valid, warning_message)
        """
        if not text:
            return True, None
        
        # Check for common problematic characters
        problematic = []
        
        # Smart quotes (should use straight quotes)
        if '"' in text or '"' in text or ''' in text or ''' in text:
            problematic.append("smart quotes (use straight quotes instead)")
        
        # Zero-width characters
        if '\u200b' in text or '\u200c' in text or '\u200d' in text:
            problematic.append("invisible zero-width characters")
        
        # Non-breaking spaces
        if '\u00a0' in text:
            problematic.append("non-breaking spaces (use regular spaces)")
        
        if problematic:
            return False, f"Contains problematic characters: {', '.join(problematic)}"
        
        return True, None


class ImageVideoValidator:
    """Validator for image and video file requirements."""
    
    @staticmethod
    def validate_image_format(filename: str) -> Tuple[bool, Optional[str]]:
        """
        Check if image format is acceptable.
        
        Args:
            filename: Image filename or URL
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not filename:
            return True, None
        
        filename_lower = filename.lower()
        valid_extensions = ['.jpg', '.jpeg', '.png', '.gif']
        
        if not any(filename_lower.endswith(ext) for ext in valid_extensions):
            return False, f"Image must be JPG, PNG, or GIF format"
        
        return True, None
    
    @staticmethod
    def validate_video_format(filename: str) -> Tuple[bool, Optional[str]]:
        """
        Check if video format is acceptable.
        
        Args:
            filename: Video filename or URL
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not filename:
            return True, None
        
        filename_lower = filename.lower()
        valid_extensions = ['.mp4', '.mov', '.avi']
        
        if not any(filename_lower.endswith(ext) for ext in valid_extensions):
            return False, f"Video must be MP4 or MOV format"
        
        return True, None
    
    @staticmethod
    def extract_dimensions_from_filename(filename: str) -> Optional[Tuple[int, int]]:
        """
        Try to extract dimensions from filename (e.g., image_1920x1080.jpg).
        
        Args:
            filename: Filename to parse
            
        Returns:
            Tuple of (width, height) or None
        """
        pattern = r'(\d+)x(\d+)'
        match = re.search(pattern, filename)
        if match:
            return int(match.group(1)), int(match.group(2))
        return None
