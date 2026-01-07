"""
Comprehensive tests for validation utilities.
"""

import pytest
from mojo_validator.validation_utils import ValidationUtils, ImageVideoValidator


class TestValidationUtils:
    """Test suite for ValidationUtils class."""
    
    def test_validate_url_valid(self):
        """Test valid URL validation."""
        utils = ValidationUtils()
        
        # Valid URLs
        valid_urls = [
            "https://example.com",
            "http://example.com",
            "https://www.example.com/path",
            "https://example.com/path?query=value",
            "https://subdomain.example.com",
        ]
        
        for url in valid_urls:
            is_valid, error = utils.validate_url(url)
            assert is_valid, f"URL {url} should be valid, got error: {error}"
            assert error is None
    
    def test_validate_url_invalid(self):
        """Test invalid URL detection."""
        utils = ValidationUtils()
        
        # Invalid URLs
        invalid_urls = [
            "example.com",  # Missing protocol
            "ftp://example.com",  # Wrong protocol
            "https://",  # Missing domain
            "https:// example.com",  # Space in URL
            "http://example .com",  # Space in domain
            "",  # Empty
            None,  # None
        ]
        
        for url in invalid_urls:
            is_valid, error = utils.validate_url(url)
            assert not is_valid, f"URL {url} should be invalid"
            assert error is not None
    
    def test_check_excessive_capitalization(self):
        """Test capitalization checking."""
        utils = ValidationUtils()
        
        # Valid capitalization
        valid_texts = [
            "This is a normal sentence",
            "Get 50% OFF today!",
            "FREE Shipping Available",
        ]
        
        for text in valid_texts:
            is_valid, warning = utils.check_excessive_capitalization(text)
            assert is_valid, f"Text '{text}' should pass capitalization check"
        
        # Invalid capitalization
        invalid_texts = [
            "ALL CAPS TEXT HERE",
            "BUY NOW GET 50% OFF",
            "THIS IS VERY IMPORTANT!!!",
        ]
        
        for text in invalid_texts:
            is_valid, warning = utils.check_excessive_capitalization(text, max_ratio=0.5)
            assert not is_valid, f"Text '{text}' should fail capitalization check"
            assert warning is not None
    
    def test_check_special_characters(self):
        """Test special character detection."""
        utils = ValidationUtils()
        
        # Test prohibited characters
        is_valid, warning = utils.check_special_characters("Get 50% off", ["™", "®"])
        assert is_valid
        
        is_valid, warning = utils.check_special_characters("Product™", ["™", "®"])
        assert not is_valid
        assert "™" in warning
        
        # Test excessive punctuation
        is_valid, warning = utils.check_special_characters("Buy now!!!")
        assert not is_valid
        assert "punctuation" in warning.lower()
    
    def test_check_url_length(self):
        """Test URL length validation."""
        utils = ValidationUtils()
        
        # Valid length
        short_url = "https://example.com/path"
        is_valid, error = utils.check_url_length(short_url, max_length=100)
        assert is_valid
        
        # Too long
        long_url = "https://example.com/" + "x" * 2100
        is_valid, error = utils.check_url_length(long_url, max_length=2048)
        assert not is_valid
        assert "2048" in error
    
    def test_extract_domain(self):
        """Test domain extraction from URL."""
        utils = ValidationUtils()
        
        assert utils.extract_domain("https://example.com/path") == "example.com"
        assert utils.extract_domain("https://subdomain.example.com") == "subdomain.example.com"
        assert utils.extract_domain("invalid") is None
    
    def test_validate_number_range(self):
        """Test number range validation."""
        utils = ValidationUtils()
        
        # Valid numbers
        is_valid, error = utils.validate_number_range(50, min_val=10, max_val=100)
        assert is_valid
        
        # Below minimum
        is_valid, error = utils.validate_number_range(5, min_val=10)
        assert not is_valid
        assert "below minimum" in error.lower()
        
        # Above maximum
        is_valid, error = utils.validate_number_range(150, max_val=100)
        assert not is_valid
        assert "exceeds maximum" in error.lower()
        
        # Invalid number
        is_valid, error = utils.validate_number_range("not a number", min_val=0)
        assert not is_valid
        assert "not a valid number" in error.lower()
    
    def test_check_emoji_usage(self):
        """Test emoji detection and counting."""
        utils = ValidationUtils()
        
        # No emojis
        is_valid, warning = utils.check_emoji_usage("Regular text")
        assert is_valid
        
        # Reasonable emoji usage
        is_valid, warning = utils.check_emoji_usage("Great deal! 🎉")
        assert is_valid
        
        # Too many emojis
        is_valid, warning = utils.check_emoji_usage("🎉🎊🎈🎁🎀", max_count=3)
        assert not is_valid
    
    def test_validate_character_encoding(self):
        """Test character encoding validation."""
        utils = ValidationUtils()
        
        # Valid text
        is_valid, warning = utils.validate_character_encoding("Normal text here")
        assert is_valid
        
        # Smart quotes
        is_valid, warning = utils.validate_character_encoding('"Smart quotes"')
        assert not is_valid
        assert "smart quotes" in warning.lower()


class TestImageVideoValidator:
    """Test suite for ImageVideoValidator class."""
    
    def test_validate_image_format(self):
        """Test image format validation."""
        validator = ImageVideoValidator()
        
        # Valid formats
        valid_formats = [
            "image.jpg",
            "image.jpeg",
            "image.png",
            "image.gif",
            "IMAGE.JPG",  # Case insensitive
        ]
        
        for filename in valid_formats:
            is_valid, error = validator.validate_image_format(filename)
            assert is_valid, f"{filename} should be valid"
        
        # Invalid formats
        invalid_formats = [
            "image.bmp",
            "image.tiff",
            "image.webp",
            "document.pdf",
        ]
        
        for filename in invalid_formats:
            is_valid, error = validator.validate_image_format(filename)
            assert not is_valid, f"{filename} should be invalid"
    
    def test_validate_video_format(self):
        """Test video format validation."""
        validator = ImageVideoValidator()
        
        # Valid formats
        valid_formats = [
            "video.mp4",
            "video.mov",
            "VIDEO.MP4",  # Case insensitive
        ]
        
        for filename in valid_formats:
            is_valid, error = validator.validate_video_format(filename)
            assert is_valid, f"{filename} should be valid"
        
        # Invalid formats
        invalid_formats = [
            "video.avi",
            "video.wmv",
            "video.flv",
        ]
        
        for filename in invalid_formats:
            is_valid, error = validator.validate_video_format(filename)
            assert not is_valid, f"{filename} should be invalid"
    
    def test_extract_dimensions_from_filename(self):
        """Test dimension extraction from filename."""
        validator = ImageVideoValidator()
        
        assert validator.extract_dimensions_from_filename("image_1920x1080.jpg") == (1920, 1080)
        assert validator.extract_dimensions_from_filename("photo_800x600.png") == (800, 600)
        assert validator.extract_dimensions_from_filename("no_dimensions.jpg") is None
