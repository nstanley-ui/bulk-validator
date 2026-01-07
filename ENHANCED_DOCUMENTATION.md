# Enhanced Mojo Validator - Documentation

## 🎯 What's New in v4.0

### 1. **Realistic Policy Detection**
- Based on actual Google Ads, Meta, and LinkedIn advertising policies
- Comprehensive pattern matching for prohibited, restricted, and editorial issues
- Platform-specific rules (e.g., Meta's personal attributes policy, LinkedIn's sensationalism rules)

### 2. **Learning System**
- Tracks every user action (accept/reject/ignore)
- Builds confidence scores for suggested fixes
- Automatically suggests fixes that users have accepted 3+ times
- SQLite database stores learning data persistently

### 3. **Better Error Categorization**
- **Severity Levels**: Critical, High, Medium, Low
- **Issue Types**: Prohibited, Restricted, Policy, Editorial, Schema, URL
- Color-coded visual indicators for quick assessment

### 4. **Schema Validation**
- Validates against platform-specific bulk upload formats
- Checks for required vs recommended columns
- Identifies missing or misnamed columns

---

## 📚 Policy Detection Details

### Google Ads

**Prohibited Content** (❌ Critical):
- Counterfeit goods
- Weapons, ammunition, explosives
- Illegal drugs
- Tobacco products
- Adult/sexual content
- Hacking tools
- Child exploitation

**Restricted Content** (⚠️ Requires Certification):
- Alcohol (country restrictions apply)
- Gambling
- Cryptocurrency
- Healthcare/pharmaceuticals
- Financial services (loans, credit repair)

**Editorial Issues** (Auto-fixable):
- Excessive capitalization (4+ caps in a row)
- Excessive punctuation (!! or ??)
- Symbol abuse ($$$, @@@)
- Misleading language ("click here", "amazing", "guaranteed")

### Meta (Facebook/Instagram)

**Prohibited Content**:
- Discrimination based on protected attributes
- Adult content, nudity
- Illegal drugs
- Weapons
- Tobacco products

**Restricted Content**:
- Dating services
- Alcohol
- Gambling
- Weight loss/health supplements
- Financial products

**Special Policies**:
- **Personal Attributes Policy**: Cannot target based on personal hardships
  - ❌ "Are you overweight?"
  - ✅ "For those focused on health"

### LinkedIn

**Prohibited Content**:
- Political advertising (ALL political content banned)
- Adult services
- Gambling
- Drugs/pharmaceuticals
- Weapons
- MLM/pyramid schemes
- Fortune telling, horoscopes

**Restricted Content**:
- Alcohol (select countries only)
- Dating services
- Cryptocurrency

**Special Policies**:
- **Sensationalism**: Avoid clickbait language
  - ❌ "Shocking secret revealed!"
  - ✅ "Interesting insights shared"

---

## 🧠 How Learning Works

### Data Collection
Every user action is logged:
```python
user_action = {
    'timestamp': '2025-01-07T10:30:00',
    'platform': 'Google Ads',
    'column': 'Headline',
    'original': 'Bitcoin trading opportunity',
    'suggested': 'Digital asset trading opportunity',
    'action': 'accept',  # or 'ignore', 'delete'
    'final_value': 'Digital asset trading opportunity',
    'issue_type': 'policy',
    'severity': 'critical'
}
```

### Confidence Scoring
- **Formula**: `confidence = (accepts + 1) / (accepts + rejects + 2)`
- **High Confidence**: 3+ accepts, confidence > 0.7
- **Auto-Suggestion**: When confidence ≥ 3 uses, suggestion appears automatically

### Pattern Recognition
When you accept a fix multiple times, the system learns:
```
Original: "Are you overweight?"
Fix Accepted: "For those focused on health"
Times Used: 5
Confidence: 0.83

Next time it sees "Are you overweight?", it auto-suggests
"For those focused on health" with confidence indicator.
```

---

## 📋 Schema Requirements

### Google Ads
**Required**:
- Campaign
- Ad Group
- Final URL

**Recommended**:
- Headline
- Description
- Ad Group ID

**Text Fields** (policy-checked):
- Headline (30 chars)
- Description (90 chars)
- Path 1, Path 2

### Meta Ads
**Required**:
- Title
- Body
- Link URL

**Recommended**:
- Call to Action
- Image

**Text Fields**:
- Title
- Body
- Description

### LinkedIn Ads
**Required**:
- Campaign Group
- Campaign
- Introductory Text
- Destination URL

**Recommended**:
- Headline
- Ad Status

**Text Fields**:
- Headline (70 chars)
- Introductory Text (150 chars)
- Description

---

## 🚀 Usage Guide

### 1. Upload Files
- Supports Excel (.xlsx) and CSV (.csv)
- Multiple files at once
- Auto-detects platform from column structure

### 2. Review Issues
Issues are categorized by severity:

**🔴 Critical**: Prohibited content - must fix or remove
**🟠 High**: Restricted content or policy violations
**🟡 Medium**: Editorial issues, URL problems
**🟢 Low**: Recommendations, minor issues

### 3. Apply Fixes
- **✅ Apply Fix**: Accept the suggestion (trains the AI)
- **🙈 Ignore**: Keep original, clear warning
- **🗑️ Remove**: Delete the row entirely

### 4. Export Results
- **Verified File**: Only available when all issues resolved
- **Draft File**: Current state with remaining issues

---

## 📊 Learning Statistics

View in the sidebar:
- **Total Actions Logged**: How many decisions tracked
- **High-Confidence Patterns**: Proven fixes (used 3+ times)

---

## 🔧 Technical Details

### Database Schema

**user_actions** table:
```sql
- timestamp TEXT
- platform TEXT
- column_name TEXT
- original_value TEXT
- suggested_fix TEXT
- user_action TEXT (accept/ignore/delete)
- final_value TEXT
- issue_type TEXT
- severity TEXT
```

**policy_patterns** table:
```sql
- platform TEXT
- pattern_type TEXT
- pattern TEXT
- fix_template TEXT
- confidence_score REAL
- times_accepted INTEGER
- times_rejected INTEGER
- last_updated TEXT
```

### URL Checking
- Validates HTTP/HTTPS protocol
- Checks for spaces in URLs
- Sends HEAD request to verify accessibility
- 2-second timeout
- Caches results for 10 minutes

### Platform Detection Logic
1. Check for Google Ads columns (Headline, Description, Final URL)
2. Check for Meta columns (Title, Body, Link URL)
3. Check for LinkedIn columns (Campaign Group, Introductory Text)
4. Return "Unknown" if no match

---

## 💡 Best Practices

### For Agencies
1. **Start with Small Batches**: Test with 10-20 rows first
2. **Use Consistent Naming**: Helps the AI learn patterns
3. **Accept Good Suggestions**: Trains the system for your clients
4. **Regular Exports**: Download verified files for records

### For In-House Teams
1. **Create Standards**: Use ignore feature for approved exceptions
2. **Review Learning Stats**: Check which patterns are high-confidence
3. **Share Knowledge**: Export verified files as templates
4. **Update Regularly**: Policies change, keep files current

### For Avoiding False Positives
1. **Industry-Specific Terms**: Add to ignore list if legitimate
2. **Brand Names**: Ignore if they trigger false matches
3. **Technical Terms**: Context matters - review carefully

---

## 🐛 Troubleshooting

### Issue: "Platform detected as Unknown"
**Solution**: Ensure your CSV has standard column names matching platform templates

### Issue: "Too many false positives"
**Solution**: 
1. Use the Ignore button for legitimate content
2. The system learns from your ignores
3. After 3+ ignores, it stops flagging similar content

### Issue: "Slow link checking"
**Solution**: 
1. Toggle off "Active Link Monitoring" in sidebar
2. Link checks timeout after 2 seconds
3. Results are cached for 10 minutes

### Issue: "Suggestions not improving"
**Solution**: 
1. Accept good suggestions - this trains the AI
2. Edit suggestions before accepting - system learns your edits
3. Need 3+ accepts before auto-suggestions appear

---

## 📈 Roadmap

### Planned Features
- [ ] Export learning data for team sharing
- [ ] Import custom policy rules
- [ ] Batch processing API
- [ ] Integration with ad platforms
- [ ] Video ad validation
- [ ] Multi-language support
- [ ] Custom regex patterns
- [ ] Webhook notifications

---

## 🆘 Support

### Viewing Learning Data
```python
import sqlite3
conn = sqlite3.connect('validator_learning.db')

# See all actions
pd.read_sql("SELECT * FROM user_actions ORDER BY timestamp DESC LIMIT 100", conn)

# See high-confidence patterns
pd.read_sql("SELECT * FROM policy_patterns WHERE confidence_score > 0.7", conn)
```

### Resetting Learning Data
```python
import os
if os.path.exists('validator_learning.db'):
    os.remove('validator_learning.db')
```

---

## 📚 Additional Resources

- [Google Ads Policies](https://support.google.com/adspolicy/answer/6008942)
- [Meta Advertising Standards](https://transparency.meta.com/policies/ad-standards/)
- [LinkedIn Advertising Policies](https://www.linkedin.com/legal/ads-policy)
- [Google Ads Bulk Upload Guide](https://support.google.com/google-ads/answer/10702932)

---

**Version**: 4.0  
**Last Updated**: January 2025  
**License**: MIT
