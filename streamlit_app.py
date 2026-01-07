import streamlit as st
import pandas as pd
import json
import os
import sqlite3
import re
import requests
from io import BytesIO
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import hashlib

# --- CONFIGURATION ---
st.set_page_config(page_title="Mojo Validator // Enterprise", page_icon="🛡️", layout="wide")

# CUSTOM CSS (keeping your design)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    .stApp {
        background-color: #F3F4F6;
        font-family: 'Inter', sans-serif;
        color: #111827;
    }
    h1, h2, h3 { color: #111827; font-weight: 700; letter-spacing: -0.025em; }
    p, div, span { color: #374151; }
    div[data-testid="stBorder"], div.css-1r6slb0, .css-1r6slb0 {
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
        border-radius: 8px;
        padding: 24px;
    }
    div[data-testid="metric-container"] {
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        box-shadow: none;
        border-radius: 8px;
        padding: 16px;
    }
    .platform-badge {
        font-size: 0.75rem;
        padding: 4px 10px;
        border-radius: 9999px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        display: inline-block;
    }
    button[kind="primary"] {
        background-color: #2563EB;
        border: 1px solid #2563EB;
        color: white;
        font-weight: 600;
        border-radius: 6px;
        padding: 0.5rem 1rem;
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
    }
    button[kind="primary"]:hover {
        background-color: #1D4ED8;
        border-color: #1D4ED8;
    }
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF;
        border-right: 1px solid #E5E7EB;
    }
</style>
""", unsafe_allow_html=True)

# --- DATABASE SETUP ---
DB_FILE = 'validator_learning.db'

def init_database():
    """Initialize SQLite database for learning system"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Table for tracking user decisions
    c.execute('''CREATE TABLE IF NOT EXISTS user_actions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  timestamp TEXT NOT NULL,
                  platform TEXT NOT NULL,
                  column_name TEXT NOT NULL,
                  original_value TEXT NOT NULL,
                  suggested_fix TEXT NOT NULL,
                  user_action TEXT NOT NULL,
                  final_value TEXT,
                  issue_type TEXT NOT NULL,
                  severity TEXT NOT NULL)''')
    
    # Table for policy patterns
    c.execute('''CREATE TABLE IF NOT EXISTS policy_patterns
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  platform TEXT NOT NULL,
                  pattern_type TEXT NOT NULL,
                  pattern TEXT NOT NULL,
                  fix_template TEXT NOT NULL,
                  confidence_score REAL DEFAULT 0.5,
                  times_accepted INTEGER DEFAULT 0,
                  times_rejected INTEGER DEFAULT 0,
                  last_updated TEXT NOT NULL)''')
    
    # Table for schema validation errors
    c.execute('''CREATE TABLE IF NOT EXISTS schema_errors
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  timestamp TEXT NOT NULL,
                  platform TEXT NOT NULL,
                  column_name TEXT NOT NULL,
                  error_type TEXT NOT NULL,
                  frequency INTEGER DEFAULT 1)''')
    
    conn.commit()
    conn.close()

def log_user_action(platform: str, column: str, original: str, suggested: str, 
                    action: str, final: str, issue_type: str, severity: str):
    """Log user action for learning"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''INSERT INTO user_actions 
                 (timestamp, platform, column_name, original_value, suggested_fix, 
                  user_action, final_value, issue_type, severity)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (datetime.now().isoformat(), platform, column, original, suggested,
               action, final, issue_type, severity))
    conn.commit()
    conn.close()

def update_pattern_confidence(platform: str, pattern_type: str, pattern: str, accepted: bool):
    """Update confidence score for a pattern based on user feedback"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Check if pattern exists
    c.execute('''SELECT id, times_accepted, times_rejected, confidence_score 
                 FROM policy_patterns 
                 WHERE platform=? AND pattern_type=? AND pattern=?''',
              (platform, pattern_type, pattern))
    result = c.fetchone()
    
    if result:
        # Update existing pattern
        pattern_id, accepted_count, rejected_count, current_score = result
        if accepted:
            accepted_count += 1
        else:
            rejected_count += 1
        
        # Calculate new confidence score (Bayesian-ish approach)
        total = accepted_count + rejected_count
        new_score = (accepted_count + 1) / (total + 2)  # Add-one smoothing
        
        c.execute('''UPDATE policy_patterns 
                     SET times_accepted=?, times_rejected=?, confidence_score=?, last_updated=?
                     WHERE id=?''',
                  (accepted_count, rejected_count, new_score, datetime.now().isoformat(), pattern_id))
    
    conn.commit()
    conn.close()

def get_learned_suggestions(platform: str, column: str, value: str) -> List[Dict]:
    """Get suggestions based on historical user acceptance"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Find similar past cases where user accepted the fix
    c.execute('''SELECT final_value, COUNT(*) as frequency
                 FROM user_actions
                 WHERE platform=? AND column_name=? AND original_value=? 
                       AND user_action='accept'
                 GROUP BY final_value
                 ORDER BY frequency DESC
                 LIMIT 3''',
              (platform, column, value))
    
    results = c.fetchall()
    conn.close()
    
    return [{"suggestion": r[0], "confidence": r[1]} for r in results]

# --- PLATFORM-SPECIFIC POLICIES ---

class PolicyEngine:
    """Comprehensive policy detection based on actual platform rules"""
    
    def __init__(self):
        self.google_prohibited = {
            'counterfeit': r'\b(fake|replica|knock[\s-]?off|counterfeit)\b',
            'weapons': r'\b(gun|firearm|ammunition|explosive|weapon|bomb|grenade)\b',
            'drugs': r'\b(cocaine|heroin|meth|fentanyl|illegal\s+drug)\b',
            'tobacco': r'\b(cigarette|tobacco|vape|e-cigarette|juul)\b',
            'adult': r'\b(porn|xxx|sex\s+toy|adult\s+content)\b',
            'hacking': r'\b(hack|crack|pirat|torrent|warez)\b',
            'child_exploitation': r'\b(child\s+porn|underage|minor\s+dating)\b',
        }
        
        self.google_restricted = {
            'alcohol': r'\b(beer|wine|vodka|whiskey|liquor|alcohol)\b',
            'gambling': r'\b(casino|poker|bet|lottery|gambling)\b',
            'crypto': r'\b(bitcoin|cryptocurrency|crypto|ICO|token\s+sale)\b',
            'healthcare': r'\b(prescription|pharmacy|viagra|drug\s+store)\b',
            'financial': r'\b(loan|credit\s+repair|payday|forex|binary\s+option)\b',
        }
        
        self.google_editorial = {
            'excessive_caps': r'[A-Z]{4,}',
            'excessive_punctuation': r'[!?]{2,}',
            'symbol_abuse': r'[$@#%&*]{2,}',
            'misleading': r'\b(click\s+here|amazing|shocking|miracle|guaranteed)\b',
        }
        
        self.meta_prohibited = {
            'discrimination': r'\b(race|ethnicity|sexual\s+orientation|religion|disability)\s+(excluded|not\s+allowed)\b',
            'adult': r'\b(nude|naked|porn|xxx|escort)\b',
            'drugs': r'\b(cocaine|heroin|meth|marijuana\s+sales|drug\s+dealer)\b',
            'weapons': r'\b(gun\s+sales|firearm|ammunition|explosive)\b',
            'tobacco': r'\b(cigarette|cigar|vape|tobacco\s+products)\b',
        }
        
        self.meta_restricted = {
            'dating': r'\b(dating\s+app|hookup|match\s+maker)\b',
            'alcohol': r'\b(alcohol|beer|wine|vodka)\b',
            'gambling': r'\b(online\s+casino|gambling|betting)\b',
            'health': r'\b(weight\s+loss|diet\s+pill|supplement)\b',
            'financial': r'\b(credit\s+repair|payday\s+loan|get\s+rich)\b',
        }
        
        self.meta_personal_attributes = r'\b(are\s+you|do\s+you\s+have|suffering\s+from|overweight|bald|ugly|poor)\b'
        
        self.linkedin_prohibited = {
            'adult': r'\b(porn|xxx|escort|sex\s+toy|strip\s+club)\b',
            'political': r'\b(vote\s+for|elect|candidate|ballot|political\s+party)\b',
            'gambling': r'\b(casino|poker|sports\s+betting|gambling)\b',
            'drugs': r'\b(marijuana|cannabis|prescription\s+drug|pharmacy)\b',
            'weapons': r'\b(gun|firearm|ammunition|weapon)\b',
            'counterfeit': r'\b(fake|replica|counterfeit)\b',
            'mlm': r'\b(MLM|multi[\s-]?level\s+marketing|pyramid\s+scheme)\b',
            'fortune': r'\b(fortune[\s-]?telling|horoscope|psychic|tarot)\b',
        }
        
        self.linkedin_restricted = {
            'alcohol': r'\b(alcohol|beer|wine|liquor)\b',
            'dating': r'\b(dating\s+service|match\s+maker)\b',
            'crypto': r'\b(cryptocurrency|bitcoin|crypto\s+trading)\b',
        }
        
        self.linkedin_sensationalism = r'\b(shocking|trick|secret|hack|scam|exposed|revealed)\b'
    
    def check_google_ads(self, text: str, column: str) -> Tuple[Optional[str], Optional[str], str, str]:
        """Check Google Ads policies"""
        if not isinstance(text, str):
            return None, None, "", ""
        
        text_lower = text.lower()
        
        # PROHIBITED CONTENT
        for violation, pattern in self.google_prohibited.items():
            if re.search(pattern, text_lower, re.IGNORECASE):
                if violation == 'crypto':
                    fix = re.sub(pattern, 'digital assets', text, flags=re.IGNORECASE)
                    return fix, f"❌ Prohibited: {violation.replace('_', ' ').title()}", "prohibited", "critical"
                elif violation == 'tobacco':
                    return None, f"❌ Prohibited: Tobacco products not allowed", "prohibited", "critical"
                else:
                    return None, f"❌ Prohibited: {violation.replace('_', ' ').title()}", "prohibited", "critical"
        
        # RESTRICTED CONTENT
        for restriction, pattern in self.google_restricted.items():
            if re.search(pattern, text_lower, re.IGNORECASE):
                return None, f"⚠️ Restricted: {restriction.title()} - Requires certification & targeting limits", "restricted", "high"
        
        # EDITORIAL ISSUES
        for issue, pattern in self.google_editorial.items():
            if match := re.search(pattern, text):
                if issue == 'excessive_caps':
                    fix = re.sub(r'([A-Z]{4,})', lambda m: m.group(1).title(), text)
                    return fix, "Editorial: Excessive capitalization", "editorial", "medium"
                elif issue == 'excessive_punctuation':
                    fix = re.sub(r'([!?])[!?]+', r'\1', text)
                    return fix, "Editorial: Excessive punctuation", "editorial", "medium"
                elif issue == 'symbol_abuse':
                    fix = re.sub(r'[$@#%&*]{2,}', '', text)
                    return fix, "Editorial: Symbol abuse", "editorial", "medium"
        
        return None, None, "", ""
    
    def check_meta_ads(self, text: str, column: str) -> Tuple[Optional[str], Optional[str], str, str]:
        """Check Meta (Facebook/Instagram) policies"""
        if not isinstance(text, str):
            return None, None, "", ""
        
        text_lower = text.lower()
        
        # PROHIBITED
        for violation, pattern in self.meta_prohibited.items():
            if re.search(pattern, text_lower, re.IGNORECASE):
                return None, f"❌ Prohibited: {violation.replace('_', ' ').title()}", "prohibited", "critical"
        
        # RESTRICTED
        for restriction, pattern in self.meta_restricted.items():
            if re.search(pattern, text_lower, re.IGNORECASE):
                return None, f"⚠️ Restricted: {restriction.title()} - Special requirements apply", "restricted", "high"
        
        # PERSONAL ATTRIBUTES POLICY (Meta-specific)
        if re.search(self.meta_personal_attributes, text_lower, re.IGNORECASE):
            # Try to fix it
            fixes = {
                r'\bare\s+you\b': 'for those who',
                r'\bdo\s+you\s+have\b': 'for people with',
                r'\bsuffering\s+from\b': 'dealing with',
                r'\boverweight\b': 'focused on health',
                r'\bbald\b': 'hair care',
                r'\bugly\b': 'appearance',
                r'\bpoor\b': 'limited budget',
            }
            fix = text
            for pattern, replacement in fixes.items():
                fix = re.sub(pattern, replacement, fix, flags=re.IGNORECASE)
            return fix, "⚠️ Meta Policy: Personal attributes not allowed", "policy", "high"
        
        return None, None, "", ""
    
    def check_linkedin_ads(self, text: str, column: str) -> Tuple[Optional[str], Optional[str], str, str]:
        """Check LinkedIn Ads policies"""
        if not isinstance(text, str):
            return None, None, "", ""
        
        text_lower = text.lower()
        
        # PROHIBITED
        for violation, pattern in self.linkedin_prohibited.items():
            if re.search(pattern, text_lower, re.IGNORECASE):
                return None, f"❌ Prohibited: {violation.replace('_', ' ').title()}", "prohibited", "critical"
        
        # RESTRICTED
        for restriction, pattern in self.linkedin_restricted.items():
            if re.search(pattern, text_lower, re.IGNORECASE):
                return None, f"⚠️ Restricted: {restriction.title()} - Authorization required", "restricted", "high"
        
        # SENSATIONALISM (LinkedIn-specific)
        if re.search(self.linkedin_sensationalism, text_lower, re.IGNORECASE):
            fixes = {
                r'\bshocking\b': 'interesting',
                r'\btrick\b': 'technique',
                r'\bsecret\b': 'insight',
                r'\bhack\b': 'method',
                r'\bscam\b': 'issue',
                r'\bexposed\b': 'revealed',
            }
            fix = text
            for pattern, replacement in fixes.items():
                fix = re.sub(pattern, replacement, fix, flags=re.IGNORECASE)
            return fix, "LinkedIn Policy: Avoid clickbait/sensationalism", "policy", "medium"
        
        return None, None, "", ""

# --- SCHEMA VALIDATION ---

PLATFORM_SCHEMAS = {
    'Google Ads': {
        'required': ['Campaign', 'Ad Group', 'Final URL'],
        'recommended': ['Headline', 'Description', 'Ad Group ID'],
        'text_fields': ['Headline', 'Description', 'Path 1', 'Path 2'],
        'url_fields': ['Final URL'],
        'numeric_fields': ['Max CPC', 'Budget'],
    },
    'Meta Ads': {
        'required': ['Title', 'Body', 'Link URL'],
        'recommended': ['Call to Action', 'Image'],
        'text_fields': ['Title', 'Body', 'Description'],
        'url_fields': ['Link URL', 'Website URL'],
        'numeric_fields': ['Budget', 'Bid Amount'],
    },
    'LinkedIn Ads': {
        'required': ['Campaign Group', 'Campaign', 'Introductory Text', 'Destination URL'],
        'recommended': ['Headline', 'Ad Status'],
        'text_fields': ['Headline', 'Introductory Text', 'Description'],
        'url_fields': ['Destination URL'],
        'numeric_fields': ['Total Budget', 'Daily Budget'],
    }
}

def detect_platform(df: pd.DataFrame) -> str:
    """Detect platform from column structure"""
    cols = set(df.columns)
    
    # Google Ads
    if {'Headline', 'Description', 'Final URL'}.issubset(cols):
        return "Google Ads"
    elif {'Campaign', 'Ad Group'}.issubset(cols) and 'Final URL' in cols:
        return "Google Ads"
    
    # Meta
    elif {'Title', 'Body', 'Link URL'}.issubset(cols):
        return "Meta Ads"
    
    # LinkedIn
    elif {'Headline', 'Introductory Text', 'Destination URL'}.issubset(cols):
        return "LinkedIn Ads"
    elif 'Campaign Group' in cols:
        return "LinkedIn Ads"
    
    return "Unknown"

def validate_schema(df: pd.DataFrame, platform: str) -> List[Dict]:
    """Validate dataframe against platform schema"""
    issues = []
    schema = PLATFORM_SCHEMAS.get(platform, {})
    
    # Check required columns
    for col in schema.get('required', []):
        if col not in df.columns:
            issues.append({
                'type': 'missing_column',
                'severity': 'critical',
                'column': col,
                'message': f"❌ Missing required column: {col}"
            })
    
    # Check recommended columns
    for col in schema.get('recommended', []):
        if col not in df.columns:
            issues.append({
                'type': 'missing_recommended',
                'severity': 'warning',
                'column': col,
                'message': f"⚠️ Recommended column missing: {col}"
            })
    
    return issues

# --- URL CHECKING ---
@st.cache_data(show_spinner=False, ttl=600)
def check_link_health(url: str) -> Tuple[Optional[str], Optional[str]]:
    """Check URL health"""
    if not url or not isinstance(url, str):
        return None, None
    
    # Fix common issues
    if not url.startswith(('http://', 'https://')):
        return "https://" + url, "Missing Protocol"
    
    if " " in url:
        return url.replace(" ", ""), "Space in URL"
    
    # Check for broken links
    try:
        headers = {'User-Agent': 'MojoValidator/2.0'}
        resp = requests.head(url, headers=headers, timeout=2, allow_redirects=True)
        if resp.status_code >= 400:
            return None, f"❌ HTTP {resp.status_code}"
    except requests.exceptions.Timeout:
        return None, "⚠️ Timeout"
    except requests.exceptions.RequestException:
        return None, "⚠️ Connection Error"
    
    return None, None

# --- ANALYSIS ENGINE ---

def analyze_row(row: pd.Series, index: int, platform: str, policy_engine: PolicyEngine, 
                filename: str, ignored_set: set, link_check: bool) -> List[Dict]:
    """Analyze a single row for issues"""
    issues = []
    
    def is_ignored(col): 
        return f"{filename}|{index}|{col}" in ignored_set
    
    schema = PLATFORM_SCHEMAS.get(platform, {})
    
    # 1. SCHEMA VALIDATION - Required columns
    for col in schema.get('required', []):
        if col not in row.index:
            if not is_ignored(col):
                issues.append({
                    'col': col,
                    'orig': '(Missing Column)',
                    'prop': '',
                    'reason': f'❌ Required column missing: {col}',
                    'type': 'schema',
                    'severity': 'critical'
                })
        elif pd.isna(row[col]) or str(row[col]).strip() == '':
            if not is_ignored(col):
                issues.append({
                    'col': col,
                    'orig': '(Empty)',
                    'prop': '',
                    'reason': f'⚠️ Required field is empty: {col}',
                    'type': 'schema',
                    'severity': 'high'
                })
    
    # 2. URL CHECKING
    for url_col in schema.get('url_fields', []):
        if url_col in row and pd.notna(row[url_col]) and not is_ignored(url_col):
            url = str(row[url_col])
            if link_check:
                fixed_url, error = check_link_health(url)
                if fixed_url:
                    issues.append({
                        'col': url_col,
                        'orig': url,
                        'prop': fixed_url,
                        'reason': f'URL Issue: {error}',
                        'type': 'url',
                        'severity': 'medium'
                    })
                elif error:
                    issues.append({
                        'col': url_col,
                        'orig': url,
                        'prop': url,
                        'reason': error,
                        'type': 'url',
                        'severity': 'high'
                    })
    
    # 3. POLICY CHECKING
    policy_check_map = {
        'Google Ads': policy_engine.check_google_ads,
        'Meta Ads': policy_engine.check_meta_ads,
        'LinkedIn Ads': policy_engine.check_linkedin_ads,
    }
    
    check_func = policy_check_map.get(platform)
    if check_func:
        for text_col in schema.get('text_fields', []):
            if text_col in row and pd.notna(row[text_col]) and not is_ignored(text_col):
                value = str(row[text_col])
                fixed, reason, issue_type, severity = check_func(value, text_col)
                
                if reason:
                    # Check if we have learned suggestions
                    learned = get_learned_suggestions(platform, text_col, value)
                    
                    if learned and learned[0]['confidence'] >= 3:  # Used 3+ times successfully
                        fixed = learned[0]['suggestion']
                        reason += f" (Learned fix: {learned[0]['confidence']} successful uses)"
                    
                    issues.append({
                        'col': text_col,
                        'orig': value,
                        'prop': fixed if fixed else '',
                        'reason': reason,
                        'type': issue_type,
                        'severity': severity
                    })
    
    return issues

# --- HELPER FUNCTIONS ---

def to_excel(df: pd.DataFrame) -> bytes:
    """Convert DataFrame to Excel bytes"""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

def to_csv(df: pd.DataFrame) -> bytes:
    """Convert DataFrame to CSV bytes"""
    return df.to_csv(index=False).encode('utf-8')

# --- INITIALIZE ---
init_database()
policy_engine = PolicyEngine()

if 'file_cache' not in st.session_state:
    st.session_state.file_cache = {}
if 'ignored' not in st.session_state:
    st.session_state.ignored = set()
if 'edits' not in st.session_state:
    st.session_state.edits = {}

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("### 🛡️ Mojo Validator")
    st.caption("Enterprise Edition v4.0 - Learning System")
    st.markdown("---")
    
    st.subheader("Configuration")
    check_links = st.toggle("Active Link Monitoring", value=True, 
                            help="Pings destination URLs to check for 404s.")
    
    st.markdown("---")
    st.subheader("📊 Learning Stats")
    
    # Show learning statistics
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM user_actions")
    total_actions = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM policy_patterns WHERE confidence_score > 0.7")
    high_confidence = c.fetchone()[0]
    
    conn.close()
    
    st.metric("Total Actions Logged", total_actions)
    st.metric("High-Confidence Patterns", high_confidence)
    
    st.markdown("---")
    if st.button("Start New Session", use_container_width=True):
        st.session_state.file_cache = {}
        st.session_state.ignored = set()
        st.session_state.edits = {}
        st.rerun()

# --- MAIN CONTENT ---

st.title("Compliance & Creative Validation")
st.markdown("""
<div style='background-color:#EBF8FF; padding:15px; border-radius:8px; border:1px solid #BEE3F8; color:#2C5282; margin-bottom:25px;'>
    <strong>🧠 AI-Powered Learning System:</strong> This validator learns from your decisions. 
    When you accept fixes, it remembers and improves suggestions over time. Policy detection based on official platform guidelines.
</div>
""", unsafe_allow_html=True)

# UPLOAD ZONE
uploaded_files = st.file_uploader("", type=['xlsx', 'csv'], accept_multiple_files=True, 
                                   label_visibility="collapsed")

if not uploaded_files and not st.session_state.file_cache:
    st.info("👆 Please upload a file (Excel or CSV) to begin.")

if uploaded_files:
    for f in uploaded_files:
        if f.name not in st.session_state.file_cache:
            try:
                if f.name.endswith('.csv'):
                    df = pd.read_csv(f)
                else:
                    df = pd.read_excel(f)
                platform = detect_platform(df)
                schema_issues = validate_schema(df, platform)
                st.session_state.file_cache[f.name] = {
                    'df': df, 
                    'plat': platform,
                    'schema_issues': schema_issues
                }
            except Exception as e:
                st.error(f"Error reading {f.name}: {e}")

# MAIN LOOP
if st.session_state.file_cache:
    for fname in list(st.session_state.file_cache.keys()):
        data = st.session_state.file_cache[fname]
        df = data['df']
        plat = data['plat']
        schema_issues = data.get('schema_issues', [])

        # --- FILE HEADER ---
        st.markdown("---")
        
        col_title, col_badge = st.columns([3, 1])
        with col_title:
            st.markdown(f"### 📄 {fname}")
        with col_badge:
            bg = "#DBEAFE" if "Google" in plat else ("#E0F2FE" if "LinkedIn" in plat else "#F3E8FF")
            text = "#1E40AF" if "Google" in plat else ("#0369A1" if "LinkedIn" in plat else "#7E22CE")
            st.markdown(f"<div style='text-align:right'><span class='platform-badge' style='background:{bg}; color:{text}'>{plat}</span></div>", 
                       unsafe_allow_html=True)
        
        # Show schema issues first
        if schema_issues:
            st.warning(f"⚠️ Found {len(schema_issues)} schema issues")
            with st.expander("View Schema Issues"):
                for issue in schema_issues:
                    st.markdown(f"- {issue['message']}")
        
        rows_issues = []
        clean_indices = []
        
        for idx in df.index:
            row = df.loc[idx]
            issues = analyze_row(row, idx, plat, policy_engine, fname, 
                                st.session_state.ignored, check_links)
            if issues:
                rows_issues.append({'id': idx, 'row': row, 'issues': issues})
            else:
                clean_indices.append(idx)

        # METRICS
        total = len(df)
        err_count = len(rows_issues)
        health_score = int(((total - err_count) / total) * 100) if total > 0 else 100
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Compliance Score", f"{health_score}%")
        m2.metric("Total Ad Rows", total)
        m3.metric("Flagged Issues", err_count, delta_color="inverse")
        
        st.write("")

        # TABS
        t1, t2 = st.tabs([f"⚠️ Review Required ({len(rows_issues)})", 
                         f"✅ Verified Data ({len(clean_indices)})"])
        
        with t1:
            if rows_issues:
                for item in rows_issues:
                    idx = item['id']
                    issues = item['issues']
                    
                    with st.container(border=True):
                        c1, c2, c3, c4 = st.columns([0.5, 2.5, 2.5, 2])
                        c1.markdown(f"**#{idx+2}**")
                        
                        with c2:
                            st.caption("DETECTED ISSUE")
                            for i in issues:
                                severity_colors = {
                                    'critical': '#DC2626',
                                    'high': '#EA580C',
                                    'medium': '#CA8A04',
                                    'low': '#65A30D'
                                }
                                color = severity_colors.get(i.get('severity', 'medium'), '#CA8A04')
                                
                                st.markdown(f"**{i['col']}**")
                                st.markdown(f"<span style='color:{color}; background:#FEF2F2; padding:2px 4px; border-radius:4px;'>{i['orig']}</span>", 
                                           unsafe_allow_html=True)
                                st.caption(f"{i['reason']}")
                        
                        with c3:
                            st.caption("RECOMMENDED FIX (EDITABLE)")
                            for i in issues:
                                key = f"edit_{fname}_{idx}_{i['col']}"
                                def_val = str(i['prop']) if i['prop'] else ""
                                new_val = st.text_input("Edit", value=def_val, key=key, 
                                                        label_visibility="collapsed")
                                if f"{fname}_{idx}" not in st.session_state.edits:
                                    st.session_state.edits[f"{fname}_{idx}"] = {}
                                st.session_state.edits[f"{fname}_{idx}"][i['col']] = new_val
                        
                        with c4:
                            st.caption("RESOLUTION")
                            if st.button("✅ Apply Fix", key=f"fix_{fname}_{idx}", 
                                        type="primary", use_container_width=True):
                                updates = st.session_state.edits.get(f"{fname}_{idx}", {})
                                for i in issues:
                                    val = updates.get(i['col'], i['prop'])
                                    
                                    # Log the action
                                    log_user_action(plat, i['col'], i['orig'], i['prop'], 
                                                   'accept', val, i.get('type', 'unknown'), 
                                                   i.get('severity', 'medium'))
                                    
                                    # Update pattern confidence
                                    if i.get('type') == 'policy':
                                        update_pattern_confidence(plat, i.get('type'), 
                                                                 i['orig'], True)
                                    
                                    # Apply fix
                                    if 'Missing Column' in i['reason']:
                                        st.session_state.file_cache[fname]['df'][i['col']] = i['prop']
                                    else:
                                        st.session_state.file_cache[fname]['df'].at[idx, i['col']] = val
                                
                                st.rerun()
                            
                            c_ign, c_del = st.columns(2)
                            if c_ign.button("🙈 Ignore", key=f"ign_{fname}_{idx}", 
                                           use_container_width=True):
                                for i in issues:
                                    st.session_state.ignored.add(f"{fname}|{idx}|{i['col']}")
                                    log_user_action(plat, i['col'], i['orig'], i['prop'], 
                                                   'ignore', i['orig'], i.get('type', 'unknown'),
                                                   i.get('severity', 'medium'))
                                st.rerun()
                            
                            if c_del.button("🗑️ Remove", key=f"del_{fname}_{idx}", 
                                           use_container_width=True):
                                st.session_state.file_cache[fname]['df'].drop(idx, inplace=True)
                                for i in issues:
                                    log_user_action(plat, i['col'], i['orig'], i['prop'], 
                                                   'delete', '', i.get('type', 'unknown'),
                                                   i.get('severity', 'medium'))
                                st.rerun()
            else:
                st.success("✅ All issues resolved. File is compliant.")

        with t2:
            if clean_indices:
                st.dataframe(df.loc[clean_indices], use_container_width=True)
            else:
                st.info("No verified rows yet. Fix issues in the Review tab.")

        # --- EXPORT SECTION ---
        st.write("")
        with st.container(border=True):
            st.subheader("Export Results")
            col_fmt, col_clean, col_wip = st.columns([1, 2, 2])
            
            with col_fmt:
                default_idx = 1  # CSV
                fmt = st.selectbox("File Format", ["Excel (.xlsx)", "CSV (.csv)"], 
                                  index=default_idx, key=f"fmt_{fname}")
            
            final_df = st.session_state.file_cache[fname]['df']
            mime = "text/csv" if "CSV" in fmt else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            data = to_csv(final_df) if "CSV" in fmt else to_excel(final_df)
            ext = "csv" if "CSV" in fmt else "xlsx"

            with col_clean:
                if not rows_issues:
                    st.download_button(f"📥 Download Verified File", data, 
                                      f"VERIFIED_{fname.split('.')[0]}.{ext}", 
                                      mime=mime, type="primary", 
                                      use_container_width=True, key=f"dl_clean_{fname}")
                else:
                    st.button("Resolve All Issues to Download Verified File", 
                             disabled=True, use_container_width=True, 
                             key=f"dl_disabled_{fname}")
            
            with col_wip:
                st.download_button(f"💾 Download Draft (With Errors)", data, 
                                  f"DRAFT_{fname.split('.')[0]}.{ext}", 
                                  mime=mime, use_container_width=True, 
                                  key=f"dl_wip_{fname}", 
                                  help="Download current progress, including unresolved errors.")
