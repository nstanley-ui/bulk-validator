# Demo Files - Error Guide

These demo files contain realistic policy violations that the Mojo Validator should detect.

---

## 📊 demo_google_ads.csv

### Row-by-Row Breakdown:

| Row | Campaign | Ad Group | Issues | Severity |
|-----|----------|----------|--------|----------|
| 1 | Summer Sale 2025 | **(NULL)** | 1. Missing protocol in URL<br>2. Excessive caps "EVER!!!"<br>3. Excessive punctuation "!!!"<br>4. Misleading language "Click here", "guaranteed"<br>5. **NULL Ad Group (warning)** | 🟡 Medium + ⚠️ Warning |
| 2 | Summer Sale 2025 | Shoes | 1. **Cryptocurrency** (restricted)<br>2. **Get rich quick** scheme language<br>3. Scam domain | 🔴 Critical |
| 3 | Summer Sale 2025 | Apparel | 1. **Personal attributes** "Are you overweight?"<br>2. **Miracle cure** claims<br>3. **Diet pill** (restricted healthcare)<br>4. Misleading "Doctors hate this trick" | 🔴 Critical |
| 4 | Back to School | **(NULL)** | 1. Missing protocol in URL<br>2. **NULL Ad Group (warning)** | 🟡 Medium + ⚠️ Warning |
| 5 | Tech Products | Laptops | **✅ CLEAN** - No issues | ✅ Pass |
| 6 | Tech Products | Phones | 1. Symbol abuse "$$$ $$$"<br>2. Excessive caps "HUGE", "SMARTPHONES", "LIMITED TIME ONLY"<br>3. Excessive punctuation "!!!!"<br>4. Missing protocol | 🟡 Medium |
| 7 | Holiday Gifts | Electronics | **✅ CLEAN** - No issues | ✅ Pass |
| 8 | Holiday Gifts | Toys | 1. **Weapons** "Gun", "firearms", "weapons"<br>2. Inappropriate for children | 🔴 Critical |
| 9 | Summer Sale 2025 | Outdoor | **✅ CLEAN** - No issues | ✅ Pass |
| 10 | Pet Products | **(NULL)** | 1. **NULL Ad Group (warning)** | ⚠️ Warning only |

### Expected Detections:
- ❌ **3 Critical Issues** (rows 2, 3, 8)
- ⚠️ **3 Upload Warnings** (rows 1, 4, 10 - NULL Ad Group)
- 🟡 **2 Editorial Issues** (rows 1, 6)
- ✅ **3 Clean Rows** (rows 5, 7, 9)

---

## 📘 demo_meta_ads.csv

### Row-by-Row Breakdown:

| Row | Title | Issues | Severity |
|-----|-------|--------|----------|
| 1 | Premium Fitness App | **Personal Attributes Policy**<br>"Are you fat?", "Do you struggle", "overweight people" | 🔴 Critical |
| 2 | Quality Home Services | **✅ CLEAN** - Professional, no issues | ✅ Pass |
| 3 | Dating Services Promo | 1. **Dating service** (restricted)<br>2. Missing protocol in URL | 🟠 High |
| 4 | Investment Opportunity | 1. **Get rich quick** scheme<br>2. Misleading "proven system"<br>3. Scam domain | 🔴 Critical |
| 5 | Healthy Meal Delivery | **✅ CLEAN** - No issues | ✅ Pass |
| 6 | Premium Alcohol Store | **Alcohol** (restricted) | 🟠 High |
| 7 | Educational Platform | **✅ CLEAN** - No issues | ✅ Pass |
| 8 | Adult Entertainment | **Adult content** (prohibited)<br>"XXX rated", "18+ only" | 🔴 Critical |
| 9 | Professional Services | **Personal Attributes Policy**<br>"Do you have debt problems?", "Are you struggling" | 🔴 Critical |
| 10 | Quality Furniture | **✅ CLEAN** - No issues | ✅ Pass |

### Expected Detections:
- ❌ **4 Critical Issues** (rows 1, 4, 8, 9 - personal attributes & prohibited)
- ⚠️ **2 Restricted Content** (rows 3, 6 - dating & alcohol)
- ✅ **4 Clean Rows** (rows 2, 5, 7, 10)

### Meta-Specific Rules Tested:
- ✅ Personal Attributes Policy (most common Meta violation)
- ✅ Prohibited adult content
- ✅ Restricted categories (dating, alcohol)
- ✅ Misleading financial claims

---

## 💼 demo_linkedin_ads.csv

### Row-by-Row Breakdown:

| Row | Campaign | Campaign Group | Issues | Severity |
|-----|----------|----------------|--------|----------|
| 1 | CRM Launch | Enterprise Software | **Sensationalism/Clickbait**<br>"SHOCKING", "won't believe", "one trick", "shocking truth" | 🟡 Medium |
| 2 | (NULL) | Professional Dev | 1. Missing protocol in URL<br>2. **NULL Campaign (warning)** | 🟡 Medium + ⚠️ Warning |
| 3 | Marketing Tools | Enterprise Software | **✅ CLEAN** - Professional language | ✅ Pass |
| 4 | Investment Platform | Financial Services | 1. **Cryptocurrency** (restricted)<br>2. **Get rich quick** language<br>3. "Guaranteed returns" (misleading)<br>4. Missing protocol | 🔴 Critical |
| 5 | Online Courses | Professional Dev | **✅ CLEAN** - No issues | ✅ Pass |
| 6 | Election 2025 | Political Campaign | **Political content** (prohibited on LinkedIn)<br>"Vote for", "Congress", "campaign", "election" | 🔴 Critical |
| 7 | Collaboration Tools | Enterprise Software | 1. **Fortune telling** (prohibited)<br>2. **Sensationalism** "Fortune Telling", "Psychic predictions", "mystical" | 🔴 Critical |
| 8 | Consulting | B2B Services | **MLM/Pyramid Scheme** (prohibited)<br>"Multi-Level Marketing", "recruit", "downside" | 🔴 Critical |
| 9 | (NULL) | Healthcare Tech | 1. **NULL Campaign (warning)** | ⚠️ Warning only |
| 10 | Executive Coaching | Professional Dev | **Sensationalism/Clickbait**<br>"This One Weird Trick", "Exposed", "Scam alert", "secret hack"<br>Missing protocol | 🟡 Medium |

### Expected Detections:
- ❌ **4 Critical Issues** (rows 4, 6, 7, 8)
- ⚠️ **2 Upload Warnings** (rows 2, 9 - NULL Campaign)
- 🟡 **3 Sensationalism Issues** (rows 1, 10, and URL issues)
- ✅ **2 Clean Rows** (rows 3, 5)

### LinkedIn-Specific Rules Tested:
- ✅ **Political content** (ALL political ads banned)
- ✅ **Sensationalism/clickbait** (most common LinkedIn issue)
- ✅ **Fortune telling** (prohibited)
- ✅ **MLM schemes** (prohibited)
- ✅ Professional standards

---

## 🎯 Testing Checklist

When you test these files, the validator should:

### ✅ Schema Validation
- [ ] Warn about NULL Campaign/Ad Group (not block)
- [ ] Show "Upload Requirement" warnings
- [ ] Still allow validation to proceed

### ✅ Policy Detection
- [ ] Flag prohibited content (weapons, adult, political)
- [ ] Flag restricted content (crypto, alcohol, dating)
- [ ] Flag platform-specific violations (Meta personal attributes, LinkedIn sensationalism)
- [ ] Flag editorial issues (caps, punctuation, symbols)

### ✅ URL Checking
- [ ] Detect missing protocols (http/https)
- [ ] Suggest fixes (add https://)
- [ ] Handle various URL formats

### ✅ Learning System
- [ ] Accept a fix → should log the action
- [ ] After 3 accepts → should auto-suggest
- [ ] Ignore an issue → should remember
- [ ] Show confidence scores

### ✅ Export Functionality
- [ ] Allow export with warnings (NULL campaign/ad group okay)
- [ ] Block export only if critical issues exist
- [ ] Generate clean CSV with fixes applied

---

## 🧪 Manual Testing Scenarios

### Scenario 1: Upload Google Ads Demo
1. Upload `demo_google_ads.csv`
2. Should detect platform as "Google Ads"
3. Should show **3 critical**, **3 warnings**, **2 medium**
4. Apply fix to row 3 (personal attributes)
5. Accept the suggestion
6. Upload same file again → should auto-suggest same fix

### Scenario 2: Upload Meta Ads Demo
1. Upload `demo_meta_ads.csv`
2. Should detect platform as "Meta Ads"
3. Should show **4 critical personal attributes** violations
4. Fix all critical issues
5. Export should still work (restricted content just needs warnings)

### Scenario 3: Upload LinkedIn Ads Demo
1. Upload `demo_linkedin_ads.csv`
2. Should detect platform as "LinkedIn Ads"
3. Should show **2 NULL campaign warnings** (but not block)
4. Should flag **political content** as critical
5. Should flag **sensationalism** in multiple rows

---

## 📊 Expected Results Summary

| File | Platform | Critical | High | Medium | Warnings | Clean |
|------|----------|----------|------|--------|----------|-------|
| Google Ads | Google Ads | 3 | 0 | 2-3 | 3 | 3 |
| Meta Ads | Meta Ads | 4 | 2 | 0 | 0 | 4 |
| LinkedIn Ads | LinkedIn Ads | 4 | 0 | 3 | 2 | 2 |

---

## 💡 What Users Should Learn

After testing these demos, users should understand:

1. **NULL Campaign/Ad Group is okay** - Just warns to fill before upload
2. **Critical issues must be fixed** - Prohibited content blocks approval
3. **Platform-specific rules matter** - What's okay on Google may not be okay on Meta
4. **Learning system improves over time** - More accepts = better suggestions
5. **Editorial issues are easy fixes** - Caps, punctuation auto-fixable

---

## 🔄 Continuous Improvement

As you use these demos:
- Accept good suggestions → trains the AI
- Ignore false positives → AI learns your exceptions
- Edit suggestions → AI learns your style
- After ~10 uses → should see confidence scores appear

---

**These demos are production-ready test cases for your validator!**
