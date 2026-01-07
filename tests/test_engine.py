import pytest
import pandas as pd
import os
from mojo_validator.engine import ValidatorEngine

@pytest.fixture
def engine():
    return ValidatorEngine("configs")

def test_google_ads_detection(engine):
    df = pd.DataFrame(columns=["Campaign", "Ad Group", "Status"])
    # Note: detect_platform is private, but we can test it via engine logic or expose it
    assert engine._detect_platform(df) == "Google Ads"

def test_linkedin_validation(engine):
    # Mock data that matches LinkedIn detection heuristic
    df = pd.DataFrame({
        "Campaign Name": ["Test"],
        "Status": ["active"],
        "Headline": ["A" * 100],
        "Introduction": ["Some intro"]
    })
    tmp_path = ".tmp/test_unit.csv"
    df.to_csv(tmp_path, index=False)
    
    result, verified_df = engine.validate_file(tmp_path)
    
    assert result.platform == "LinkedIn Ads"
    assert verified_df.at[0, "Status"] == "ACTIVE"
    assert len(verified_df.at[0, "Headline"]) == 70
