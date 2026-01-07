"""
Comprehensive tests for the validation engine.
"""

import pytest
import pandas as pd
import os
from mojo_validator.engine import ValidatorEngine


@pytest.fixture
def engine():
    """Create engine instance with test configs."""
    return ValidatorEngine("configs")


class TestPlatformDetection:
    """Test platform auto-detection."""
    
    def test_detect_google_ads(self, engine):
        """Test Google Ads detection."""
        df = pd.DataFrame(columns=["Campaign", "Ad Group", "Headline 1", "Description 1", "Final URL"])
        assert engine._detect_platform(df) == "Google Ads"
    
    def test_detect_meta_ads(self, engine):
        """Test Meta Ads detection."""
        df = pd.DataFrame(columns=["Campaign Name", "Ad Set Name", "Ad Name", "Primary Text", "Headline"])
        assert engine._detect_platform(df) == "Meta Ads"
    
    def test_detect_linkedin_ads(self, engine):
        """Test LinkedIn Ads detection."""
        df = pd.DataFrame(columns=["Campaign Name", "Headline", "Introduction", "Landing Page URL"])
        assert engine._detect_platform(df) == "LinkedIn Ads"
    
    def test_detect_generic_fallback(self, engine):
        """Test fallback to Generic for ambiguous files."""
        df = pd.DataFrame(columns=["Name", "Status", "Budget"])
        assert engine._detect_platform(df) == "Generic"


class TestLinkedInValidation:
    """Test LinkedIn Ads validation rules."""
    
    def test_linkedin_required_fields(self, engine):
        """Test required field validation."""
        df = pd.DataFrame({
            "Campaign Name": ["Test Campaign"],
            "Status": ["ACTIVE"],
            "Headline": ["Valid Headline"],
            "Landing Page URL": [None],  # Missing required field
        })
        
        tmp_path = ".tmp/test_linkedin_required.csv"
        os.makedirs(".tmp", exist_ok=True)
        df.to_csv(tmp_path, index=False)
        
        result, verified_df = engine.validate_file(tmp_path, platform_override="LinkedIn Ads")
        
        # Should have issue for missing Landing Page URL
        url_issues = [i for i in result.issues if "Landing Page URL" in i.column]
        assert len(url_issues) > 0
        assert any("required" in i.message.lower() for i in url_issues)
    
    def test_linkedin_headline_length(self, engine):
        """Test headline length validation."""
        df = pd.DataFrame({
            "Campaign Name": ["Test"],
            "Status": ["ACTIVE"],
            "Headline": ["This is a very long headline that exceeds the maximum character limit of 200 characters for LinkedIn ads and should trigger a validation error because it is way too long and will be rejected by the platform"],
            "Landing Page URL": ["https://example.com"],
        })
        
        tmp_path = ".tmp/test_linkedin_headline.csv"
        df.to_csv(tmp_path, index=False)
        
        result, verified_df = engine.validate_file(tmp_path, platform_override="LinkedIn Ads")
        
        # Should have length issue
        length_issues = [i for i in result.issues if i.column == "Headline" and "length" in i.message.lower()]
        assert len(length_issues) > 0
    
    def test_linkedin_url_validation(self, engine):
        """Test URL format validation."""
        df = pd.DataFrame({
            "Campaign Name": ["Test"],
            "Status": ["ACTIVE"],
            "Headline": ["Valid Headline"],
            "Landing Page URL": ["example.com"],  # Missing protocol
        })
        
        tmp_path = ".tmp/test_linkedin_url.csv"
        df.to_csv(tmp_path, index=False)
        
        result, verified_df = engine.validate_file(tmp_path, platform_override="LinkedIn Ads")
        
        # Should have URL format issue
        url_issues = [i for i in result.issues if "Landing Page URL" in i.column]
        assert len(url_issues) > 0
        assert any("http" in i.message.lower() for i in url_issues)
    
    def test_linkedin_status_validation(self, engine):
        """Test status value validation."""
        df = pd.DataFrame({
            "Campaign Name": ["Test"],
            "Status": ["invalid_status"],
            "Headline": ["Valid"],
            "Landing Page URL": ["https://example.com"],
        })
        
        tmp_path = ".tmp/test_linkedin_status.csv"
        df.to_csv(tmp_path, index=False)
        
        result, verified_df = engine.validate_file(tmp_path, platform_override="LinkedIn Ads")
        
        # Should have status value issue
        status_issues = [i for i in result.issues if i.column == "Status"]
        assert len(status_issues) > 0


class TestGoogleAdsValidation:
    """Test Google Ads validation rules."""
    
    def test_google_headline_validation(self, engine):
        """Test headline character limit."""
        df = pd.DataFrame({
            "Campaign": ["Test"],
            "Ad Group": ["Group 1"],
            "Status": ["Enabled"],
            "Headline 1": ["This headline is way too long for Google"],  # Over 30 chars
            "Headline 2": ["Valid"],
            "Description 1": ["Valid description"],
            "Final URL": ["https://example.com"],
        })
        
        tmp_path = ".tmp/test_google_headline.csv"
        os.makedirs(".tmp", exist_ok=True)
        df.to_csv(tmp_path, index=False)
        
        result, verified_df = engine.validate_file(tmp_path, platform_override="Google Ads")
        
        # Should have headline length issue
        headline_issues = [i for i in result.issues if "Headline 1" in i.column]
        assert len(headline_issues) > 0
    
    def test_google_description_validation(self, engine):
        """Test description character limit."""
        df = pd.DataFrame({
            "Campaign": ["Test"],
            "Ad Group": ["Group 1"],
            "Status": ["Enabled"],
            "Headline 1": ["Valid"],
            "Headline 2": ["Valid"],
            "Description 1": ["This is a very long description that exceeds the 90 character limit for Google Ads descriptions and should be flagged"],
            "Final URL": ["https://example.com"],
        })
        
        tmp_path = ".tmp/test_google_description.csv"
        df.to_csv(tmp_path, index=False)
        
        result, verified_df = engine.validate_file(tmp_path, platform_override="Google Ads")
        
        # Should have description length issue
        desc_issues = [i for i in result.issues if "Description 1" in i.column]
        assert len(desc_issues) > 0
    
    def test_google_final_url_required(self, engine):
        """Test Final URL is required."""
        df = pd.DataFrame({
            "Campaign": ["Test"],
            "Ad Group": ["Group 1"],
            "Status": ["Enabled"],
            "Headline 1": ["Valid"],
            "Description 1": ["Valid description"],
            "Final URL": [None],  # Missing
        })
        
        tmp_path = ".tmp/test_google_url.csv"
        df.to_csv(tmp_path, index=False)
        
        result, verified_df = engine.validate_file(tmp_path, platform_override="Google Ads")
        
        # Should have URL missing issue
        url_issues = [i for i in result.issues if "Final URL" in i.column]
        assert len(url_issues) > 0


class TestMetaAdsValidation:
    """Test Meta Ads validation rules."""
    
    def test_meta_headline_length(self, engine):
        """Test CORRECTED headline length (27 chars)."""
        df = pd.DataFrame({
            "Campaign Name": ["Test"],
            "Ad Set Name": ["Set 1"],
            "Ad Name": ["Ad 1"],
            "Campaign Status": ["ACTIVE"],
            "Primary Text": ["Valid text"],
            "Headline": ["This headline is too long"],  # 26 chars - should pass
            "Website URL": ["https://example.com"],
        })
        
        tmp_path = ".tmp/test_meta_headline.csv"
        os.makedirs(".tmp", exist_ok=True)
        df.to_csv(tmp_path, index=False)
        
        result, verified_df = engine.validate_file(tmp_path, platform_override="Meta Ads")
        
        # 26 characters should pass
        headline_blockers = [i for i in result.issues if i.column == "Headline" and i.severity == "BLOCKER"]
        assert len(headline_blockers) == 0
    
    def test_meta_headline_too_long(self, engine):
        """Test headline exceeding 27 character limit."""
        df = pd.DataFrame({
            "Campaign Name": ["Test"],
            "Ad Set Name": ["Set 1"],
            "Ad Name": ["Ad 1"],
            "Campaign Status": ["ACTIVE"],
            "Primary Text": ["Valid text"],
            "Headline": ["This headline is definitely too long"],  # Over 27 chars
            "Website URL": ["https://example.com"],
        })
        
        tmp_path = ".tmp/test_meta_headline_long.csv"
        df.to_csv(tmp_path, index=False)
        
        result, verified_df = engine.validate_file(tmp_path, platform_override="Meta Ads")
        
        # Should have headline length issue
        headline_issues = [i for i in result.issues if i.column == "Headline" and "length" in i.message.lower()]
        assert len(headline_issues) > 0
    
    def test_meta_primary_text_truncation_warning(self, engine):
        """Test primary text shows warning for >125 chars."""
        long_text = "x" * 150
        df = pd.DataFrame({
            "Campaign Name": ["Test"],
            "Ad Set Name": ["Set 1"],
            "Ad Name": ["Ad 1"],
            "Campaign Status": ["ACTIVE"],
            "Primary Text": [long_text],
            "Headline": ["Valid"],
            "Website URL": ["https://example.com"],
        })
        
        tmp_path = ".tmp/test_meta_primary.csv"
        df.to_csv(tmp_path, index=False)
        
        result, verified_df = engine.validate_file(tmp_path, platform_override="Meta Ads")
        
        # Should have length issue
        text_issues = [i for i in result.issues if i.column == "Primary Text"]
        assert len(text_issues) > 0


class TestEdgeCases:
    """Test edge cases and special scenarios."""
    
    def test_empty_string_handling(self, engine):
        """Test handling of empty strings."""
        df = pd.DataFrame({
            "Campaign Name": [""],  # Empty string
            "Status": ["ACTIVE"],
            "Headline": ["Valid"],
            "Landing Page URL": ["https://example.com"],
        })
        
        tmp_path = ".tmp/test_empty.csv"
        os.makedirs(".tmp", exist_ok=True)
        df.to_csv(tmp_path, index=False)
        
        result, verified_df = engine.validate_file(tmp_path, platform_override="LinkedIn Ads")
        
        # Should catch empty required field
        empty_issues = [i for i in result.issues if "Campaign Name" in i.column]
        assert len(empty_issues) > 0
    
    def test_whitespace_handling(self, engine):
        """Test handling of whitespace in fields."""
        df = pd.DataFrame({
            "Campaign Name": ["   "],  # Only whitespace
            "Status": ["ACTIVE"],
            "Headline": ["Valid"],
            "Landing Page URL": ["https://example.com"],
        })
        
        tmp_path = ".tmp/test_whitespace.csv"
        df.to_csv(tmp_path, index=False)
        
        result, verified_df = engine.validate_file(tmp_path, platform_override="LinkedIn Ads")
        
        # Should catch whitespace-only required field
        issues = [i for i in result.issues if "Campaign Name" in i.column]
        assert len(issues) > 0
    
    def test_capitalization_warning(self, engine):
        """Test excessive capitalization warning."""
        df = pd.DataFrame({
            "Campaign Name": ["TEST CAMPAIGN"],
            "Status": ["ACTIVE"],
            "Headline": ["ALL CAPS HEADLINE"],  # Should trigger warning
            "Landing Page URL": ["https://example.com"],
        })
        
        tmp_path = ".tmp/test_caps.csv"
        df.to_csv(tmp_path, index=False)
        
        result, verified_df = engine.validate_file(tmp_path, platform_override="LinkedIn Ads")
        
        # Should have capitalization warnings
        cap_warnings = [i for i in result.issues if "capitalization" in i.message.lower()]
        assert len(cap_warnings) > 0
    
    def test_special_characters_warning(self, engine):
        """Test special character detection."""
        df = pd.DataFrame({
            "Campaign Name": ["Test Campaign!!!"],  # Excessive punctuation
            "Status": ["ACTIVE"],
            "Headline": ["Valid"],
            "Landing Page URL": ["https://example.com"],
        })
        
        tmp_path = ".tmp/test_special.csv"
        df.to_csv(tmp_path, index=False)
        
        result, verified_df = engine.validate_file(tmp_path, platform_override="LinkedIn Ads")
        
        # Should have punctuation warnings
        punct_warnings = [i for i in result.issues if "punctuation" in i.message.lower()]
        assert len(punct_warnings) > 0


class TestSummaryStats:
    """Test summary statistics generation."""
    
    def test_summary_calculation(self, engine):
        """Test summary stats are calculated correctly."""
        df = pd.DataFrame({
            "Campaign Name": ["Test1", "Test2", "Test3"],
            "Status": ["ACTIVE", "invalid", "ACTIVE"],  # One invalid
            "Headline": ["Valid", "Valid", "x" * 250],  # One too long
            "Landing Page URL": ["https://example.com", "https://example.com", "invalid.com"],
        })
        
        tmp_path = ".tmp/test_summary.csv"
        os.makedirs(".tmp", exist_ok=True)
        df.to_csv(tmp_path, index=False)
        
        result, verified_df = engine.validate_file(tmp_path, platform_override="LinkedIn Ads")
        
        assert result.summary.total_rows == 3
        assert result.summary.rows_with_issues > 0
        assert result.summary.total_issues > 0
        assert result.summary.severity_counts["BLOCKER"] > 0


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
