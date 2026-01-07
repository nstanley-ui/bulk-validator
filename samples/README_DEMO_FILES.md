# Demo Files - Realistic Ad Data with Intentional Issues

This directory contains 3 realistic demo files (50 ads each) for testing the bulk validator. Each file has mostly valid ads but includes intentional issues to showcase the validator's capabilities.

---

## Files Included

1. **`linkedin_demo_50_realistic.csv`** & `.xlsx` - LinkedIn Ads
2. **`google_ads_demo_50_realistic.csv`** & `.xlsx` - Google Ads (Responsive Search Ads)
3. **`meta_ads_demo_50_realistic.csv`** & `.xlsx` - Meta Ads (Facebook/Instagram)

---

## LinkedIn Ads Demo (50 ads)

**Valid ads**: ~42 (84%)  
**Ads with issues**: ~8 (16%)

### Intentional Issues Included:

| Row | Issue Type | Description | Severity |
|-----|-----------|-------------|----------|
| 41 | Character Limit | Headline exceeds 200 chars + ALL CAPS | BLOCKER + WARNING |
| 42 | Character Limit | Headline exceeds recommended 70 chars | WARNING |
| 43 | Excessive Punctuation | Multiple exclamation marks | WARNING |
| 44 | URL Format | Missing http:// protocol | BLOCKER |
| 45 | URL Format | Wrong protocol (ftp://) | BLOCKER |
| 46 | Required Field | Landing Page URL is NULL | BLOCKER |
| 47 | URL Format | Space in URL | BLOCKER |
| 48 | Required Field | Empty Campaign Name | BLOCKER |
| 49 | Number Range | Budget below $10 minimum | BLOCKER |
| 45-50 | Invalid Status | "active", "pause", "invalid" instead of "ACTIVE", "PAUSED" | WARNING |

### Sample Valid Ad:
```
Campaign Name: Q1 2026 Campaign 01
Status: ACTIVE
Headline: Boost Your Marketing ROI Today
Introduction: Increase your marketing efficiency by 3x with our AI-powered platform. Join 10,000+ companies.
Landing Page URL: https://example-marketing.com/landing
Daily Budget: 150
```

---

## Google Ads Demo (50 ads)

**Valid ads**: ~42 (84%)  
**Ads with issues**: ~8 (16%)

### Intentional Issues Included:

| Row | Issue Type | Description | Severity |
|-----|-----------|-------------|----------|
| 45 | Character Limit | Headline 1 exceeds 30 chars | BLOCKER |
| 46 | Character Limit + Caps | Headline 1 too long + ALL CAPS + punctuation | BLOCKER + WARNING |
| 47 | Excessive Caps | Headline 2 in ALL CAPS | WARNING |
| 47 | Character Limit | Path 1 exceeds 15 chars | BLOCKER |
| 48 | Required Field | Headline 3 is empty | WARNING (optional field) |
| 46 | Character Limit | Description 1 exceeds 90 chars | BLOCKER |
| 47 | Character Limit | Description 2 exceeds 90 chars + caps | BLOCKER + WARNING |
| 48 | URL Format | Missing http:// protocol | BLOCKER |
| 49 | Required Field | Final URL is NULL | BLOCKER |
| 45-50 | Invalid Status | "active", "deleted" instead of "Enabled", "Removed" | WARNING |

### Sample Valid Ad:
```
Campaign: Search - Brand Terms
Ad Group: CRM Software
Status: Enabled
Headline 1: Best CRM for Small Business
Headline 2: Start Your Free Trial Today
Headline 3: Get Started in Minutes
Description 1: Transform your sales process with our intuitive CRM. Trusted by 50,000+ businesses worldwide.
Description 2: Free trial. No credit card required. Cancel anytime. 24/7 support included.
Final URL: https://example-crm.com/trial
Path 1: trial
Path 2: get-started
Max CPC: 1.50
```

---

## Meta Ads Demo (50 ads)

**Valid ads**: ~40 (80%)  
**Ads with issues**: ~10 (20%)

### Intentional Issues Included:

| Row | Issue Type | Description | Severity |
|-----|-----------|-------------|----------|
| 45 | Character Limit | Primary Text way over 125 char preview | WARNING |
| 45 | Character Limit | Headline exceeds 27 chars (29 chars) | BLOCKER |
| 46 | Excessive Caps | Primary Text ALL CAPS + excessive punctuation | WARNING |
| 46 | Excessive Caps | Headline ALL CAPS | WARNING |
| 46 | Character Limit | Link Description at 30 char limit | OK |
| 47 | Required Field | Primary Text is empty | BLOCKER |
| 47 | Character Limit | Headline exceeds 27 chars (29 chars) | BLOCKER |
| 47 | Character Limit | Link Description exceeds 30 chars | BLOCKER |
| 48 | Excessive Caps + Punctuation | Headline ALL CAPS + punctuation (29 chars) | BLOCKER + WARNING |
| 48 | URL Format | Missing http:// protocol | BLOCKER |
| 49 | Required Field | Website URL is NULL | BLOCKER |
| 45-50 | Invalid Status | "active", "pause" instead of "ACTIVE", "PAUSED" | WARNING |

### Sample Valid Ad:
```
Campaign Name: Brand Awareness Q1 2026
Ad Set Name: Audience: Tech Decision Makers
Ad Name: Ad Variation A01
Campaign Status: ACTIVE
Primary Text: Transform your business with our AI-powered CRM. Join 50,000+ companies seeing 3x ROI. Try it free for 14 days! 🚀
Headline: Transform Your Business
Link Description: Start your free trial today
Website URL: https://example-crm.com/fb-trial
Call to Action: LEARN_MORE
```

---

## How to Use These Files

### 1. Via Streamlit UI
```bash
streamlit run app.py
```
Then upload any of the demo files and review the validation results.

### 2. Via Command Line
```python
from mojo_validator.engine import ValidatorEngine

engine = ValidatorEngine("configs")
result, verified_df = engine.validate_file(
    "samples/linkedin_demo_50_realistic.csv",
    auto_fix=False
)

# Print summary
print(f"Platform detected: {result.platform}")
print(f"Total issues: {result.summary.total_issues}")
print(f"Blockers: {result.summary.severity_counts['BLOCKER']}")
print(f"Warnings: {result.summary.severity_counts['WARNING']}")

# Print issues
for issue in result.issues:
    print(f"\nRow {issue.row_idx + 1}: {issue.column}")
    print(f"  Severity: {issue.severity}")
    print(f"  Message: {issue.message}")
    if issue.suggested_fix:
        print(f"  Suggested fix: {issue.suggested_fix}")
```

### 3. Expected Results

**LinkedIn Demo**:
- Should detect ~8-12 issues
- Platform detection: "LinkedIn Ads"
- Issues: URL format, character limits, invalid status, required fields

**Google Ads Demo**:
- Should detect ~10-15 issues  
- Platform detection: "Google Ads"
- Issues: Headline/description lengths, URL format, invalid status, path lengths

**Meta Ads Demo**:
- Should detect ~12-18 issues
- Platform detection: "Meta Ads"
- Issues: Headline length (27 chars!), primary text length, caps, URL format

---

## Issue Type Breakdown

### BLOCKER Issues (Must Fix Before Upload)
- ❌ Missing required fields (URL, Campaign Name, etc.)
- ❌ Character limits exceeded (hard limits)
- ❌ Invalid URL format (missing protocol, spaces, wrong protocol)
- ❌ Invalid status values (need mapping)
- ❌ Number range violations (budget too low)

### WARNING Issues (Should Fix for Better Performance)
- ⚠️ Excessive capitalization (ALL CAPS)
- ⚠️ Excessive punctuation (multiple !!!)
- ⚠️ Character limits exceeded (recommended limits)
- ⚠️ Emoji overuse
- ⚠️ Problematic characters (smart quotes, etc.)

---

## Testing Different Scenarios

### Test Auto-Fix Feature
```python
# With auto-fix enabled (opt-in)
result, verified_df = engine.validate_file(
    "samples/meta_ads_demo_50_realistic.csv",
    auto_fix=True  # Status values will be auto-mapped
)

# Check what was fixed
print(verified_df["Campaign Status"].value_counts())
# Should show "ACTIVE", "PAUSED" (lowercase converted)
```

### Test Platform Detection
```python
# Without override - should auto-detect
result, _ = engine.validate_file("samples/linkedin_demo_50_realistic.csv")
print(result.platform)  # Should print "LinkedIn Ads"

# With override
result, _ = engine.validate_file(
    "samples/linkedin_demo_50_realistic.csv",
    platform_override="Google Ads"  # Force wrong platform
)
# Will validate as Google Ads (many errors expected)
```

### Filter by Severity
```python
result, _ = engine.validate_file("samples/linkedin_demo_50_realistic.csv")

# Only blockers (must fix)
blockers = [i for i in result.issues if i.severity == "BLOCKER"]
print(f"Must fix: {len(blockers)} issues")

# Only warnings (nice to fix)
warnings = [i for i in result.issues if i.severity == "WARNING"]
print(f"Recommended: {len(warnings)} issues")
```

---

## Realistic Ad Copy

All demo files use realistic ad copy for real-world scenarios:
- ✅ Professional business language
- ✅ Common CTAs (Free Trial, Demo, Learn More)
- ✅ Realistic budgets and bids
- ✅ Industry-standard messaging
- ✅ Platform-appropriate tone

This makes the demo files suitable for:
- Training new team members
- Testing validation rules
- Demonstrating the tool to stakeholders
- Benchmarking performance

---

## File Formats

Each platform has both CSV and Excel formats:
- **CSV**: Faster to load, smaller file size
- **Excel**: Better for manual editing, preserves formatting

Both formats work identically with the validator.

---

## Need Different Data?

To generate custom demo data:

```python
import pandas as pd

# Create your custom data
data = {
    "Campaign Name": ["Test 1", "Test 2"],
    "Status": ["ACTIVE", "PAUSED"],
    # ... add more fields
}

df = pd.DataFrame(data)
df.to_csv("my_custom_demo.csv", index=False)

# Validate
result, verified = engine.validate_file("my_custom_demo.csv")
```

---

## Questions?

If you find issues with the demo data or have suggestions:
1. Check if the issue is intentional (see tables above)
2. Review the config files in `configs/` for validation rules
3. Run tests to verify: `pytest tests/ -v`

Enjoy testing! 🚀
