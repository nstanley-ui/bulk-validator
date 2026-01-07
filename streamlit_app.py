import streamlit as st
import pandas as pd
import json
import os
import random
import re
from io import BytesIO
from openpyxl import Workbook

# --- CONFIGURATION ---
st.set_page_config(page_title="Universal Ad Validator", page_icon="🛡️", layout="wide")

MEMORY_FILE = 'validator_memory.json'

# --- 1. THE BRAIN (Memory System) ---
def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_memory(new_rules):
    current_memory = load_memory()
    current_memory.update(new_rules)
    with open(MEMORY_FILE, 'w') as f:
        json.dump(current_memory, f)

# --- 2. PLATFORM DETECTION ---
def detect_platform(df):
    columns = set(df.columns)
    if {'Ad Headline', 'Ad Description', 'Landing Page URL'}.issubset(columns):
        return "LinkedIn Ads"
    elif {'Title', 'Body', 'Link URL'}.issubset(columns):
        return "Meta Ads (Facebook/Instagram)"
    elif {'Headline', 'Description', 'Final URL'}.issubset(columns):
        return "Google Ads"
    else:
        return "Unknown"

# --- 3. REJECTION LOGIC & POLICY CHECKS ---
def check_policy_violations(text, platform):
    """
    Scans text for specific keywords/patterns that cause rejection.
    Returns: (Proposed Fix, Reason) or (None, None)
    """
    text_lower = text.lower()
    
    # --- GOOGLE ADS RESTRICTIONS ---
    if platform == "Google Ads":
        # Financial / Crypto (Partial Rejection)
        if re.search(r'\b(crypto|bitcoin|eth|ico)\b', text_lower):
            return text.replace("Bitcoin", "Digital Assets").replace("Crypto", "Digital Assets"), "Restricted Financial Term"
        
        # Restricted Medical (Prescription/Botox)
        if re.search(r'\b(botox|prescription|drugs)\b', text_lower):
            return text.replace("Botox", "Treatments").replace("Prescription", "Medication"), "Restricted Medical Term"
        
        # Superlatives (Need 3rd party verification usually)
        if "best" in text_lower or "#1" in text:
            return text.replace("Best", "Top").replace("#1", "Leading"), "Unsubstantiated Superlative"
            
        # Gimmicky punctuation
        if "!!" in text:
            return text.replace("!!", "!"), "Excessive Punctuation"

    # --- META (FACEBOOK/IG) RESTRICTIONS ---
    elif platform == "Meta Ads (Facebook/Instagram)":
        # Personal Attributes (MAJOR Rejection trigger)
        # Meta forbids "asserting" anything about the user. e.g. "Are you tired?"
        if re.search(r'\b(are you|do you have|do you suffer)\b', text_lower):
            return text.replace("Are you", "For those").replace("Do you have", "Help for"), "Personal Attribute Policy (High Rejection Risk)"
        
        # Get Rich Quick
        if re.search(r'\b(make money|get rich|work from home)\b', text_lower):
            return "Start your career today", "Misleading/MLM Policy"

    # --- LINKEDIN RESTRICTIONS ---
    elif platform == "LinkedIn Ads":
        # Discrimination / Ageism
        if re.search(r'\b(too old|too young)\b', text_lower):
            return text, "Potential Discrimination Policy"
        
        # Clickbait
        if re.search(r'\b(shocking|you won\'t believe)\b', text_lower):
            return "Industry Insights", "Clickbait Policy"

    return None, None

# --- 4. MAIN ANALYZER ---
def analyze_row(row, index, platform, memory):
    issues = []
    
    # --- COMMON: URL CHECK ---
    url_col = None
    if 'Final URL' in row: url_col = 'Final URL'
    elif 'Landing Page URL' in row: url_col = 'Landing Page URL'
    elif 'Link URL' in row: url_col = 'Link URL'
    
    if url_col and pd.notna(row[url_col]):
        url = str(row[url_col])
        if ' ' in url:
            issues.append({'col': url_col, 'original': url, 'proposed': url.replace(' ', ''), 'reason': 'Space in URL'})

    # --- PLATFORM SPECIFIC CHECKS ---
    
    # 1. Google Ads
    if platform == "Google Ads":
        # Headline Checks
        if 'Headline' in row and pd.notna(row['Headline']):
            text = str(row['Headline'])
            
            # Policy Check
            fix, reason = check_policy_violations(text, platform)
            if fix:
                issues.append({'col': 'Headline', 'original': text, 'proposed': fix, 'reason': f"Policy: {reason}"})
            
            # Learned Memory
            elif text in memory:
                 issues.append({'col': 'Headline', 'original': text, 'proposed': memory[text], 'reason': 'Learned Fix'})
            # Length
            elif len(text) > 30:
                issues.append({'col': 'Headline', 'original': text, 'proposed': text[:30], 'reason': f'Too Long ({len(text)}/30)'})
            # CAPS
            elif text.isupper() and len(text) > 4:
                 issues.append({'col': 'Headline', 'original': text, 'proposed': text.title(), 'reason': 'Excessive Capitalization'})

        # Manual Bid
        if 'Max CPC' in row and pd.notna(row['Max CPC']):
             issues.append({'col': 'Max CPC', 'original': row['Max CPC'], 'proposed': None, 'reason': 'Manual Bid in Auto Campaign'})

    # 2. LinkedIn Ads
    elif platform == "LinkedIn Ads":
        if 'Ad Headline' in row and pd.notna(row['Ad Headline']):
            text = str(row['Ad Headline'])
            # Policy
            fix, reason = check_policy_violations(text, platform)
            if fix:
                issues.append({'col': 'Ad Headline', 'original': text, 'proposed': fix, 'reason': f"Policy: {reason}"})
            # Length
            elif len(text) > 70:
                issues.append({'col': 'Ad Headline', 'original': text, 'proposed': text[:70], 'reason': f'Truncation Risk ({len(text)}/70)'})

    # 3. Meta Ads
    elif platform == "Meta Ads (Facebook/Instagram)":
        # Check Title
        if 'Title' in row and pd.notna(row['Title']):
            text = str(row['Title'])
            # Policy
            fix, reason = check_policy_violations(text, platform)
            if fix:
                issues.append({'col': 'Title', 'original': text, 'proposed': fix, 'reason': f"Policy: {reason}"})
            # Length
            elif len(text) > 40:
                issues.append({'col': 'Title', 'original': text, 'proposed': text[:40], 'reason': f'Too Long ({len(text)}/40)'})

        # Check Body for "Are you..." questions (Strict Meta Policy)
        if 'Body' in row and pd.notna(row['Body']):
            text = str(row['Body'])
            fix, reason = check_policy_violations(text, platform)
            if fix:
                issues.append({'col': 'Body', 'original': text, 'proposed': fix, 'reason': f"Policy: {reason}"})

    return issues

# --- 5. DEMO GENERATOR (With Rejection Flags) ---
def generate_demo(platform):
    output = BytesIO()
    data = []
    
    def rand_url(): return random.choice(['https://site.com', 'https://broken url.com', 'https://mysite.org'])

    if platform == 'google':
        for i in range(50):
            row = {'Headline': f"Valid Headline {i}", 'Description': "Desc", 'Final URL': "https://site.com", 'Max CPC': None}
            
            # Inject Specific Errors
            if i == 0: row['Headline'] = "Buy Bitcoin Now" # Crypto Flag
            if i == 1: row['Headline'] = "Get Best Botox" # Medical Flag
            if i == 2: row['Headline'] = "THIS IS SHOUTING" # Caps Flag
            if i == 3: row['Headline'] = "Headline Too Long For Google Ads" # Length Flag
            if i == 4: row['Max CPC'] = 1.50 # Bid Flag
            
            data.append(row)
            
    elif platform == 'linkedin':
        for i in range(50):
            row = {'Campaign Name': 'Q1', 'Ad Headline': f"Professional Update {i}", 'Ad Description': "Desc", 'Landing Page URL': "https://li.com"}
            
            if i == 0: row['Ad Headline'] = "You won't believe this shocking trick" # Clickbait Flag
            if i == 1: row['Ad Headline'] = "This headline is way too long for LinkedIn mobile devices and will cut off" # Length Flag
            
            data.append(row)

    elif platform == 'meta':
        for i in range(50):
            row = {'Campaign Name': 'Social', 'Title': f"Fresh Look {i}", 'Body': "Great vibes only.", 'Link URL': "https://meta.com"}
            
            if i == 0: row['Body'] = "Are you tired of being overweight?" # Personal Attribute Flag (High Risk)
            if i == 1: row['Title'] = "Work from home get rich" # MLM Flag
            if i == 2: row['Title'] = "This Title Is Too Long For Meta Feed" # Length Flag
            
            data.append(row)
        
    df = pd.DataFrame(data)
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

# --- APP UI ---
st.title("🛡️ Universal Ad Policy Validator")
st.markdown("Checks for **API Errors**, **Policy Violations**, and **Rejection Flags**.")

if 'df_data' not in st.session_state:
    st.session_state.df_data = None
if 'platform' not in st.session_state:
    st.session_state.platform = None

# DEMO DOWNLOADS
with st.expander("📥 Get Demo Files (Includes Policy Violations)", expanded=False):
    c1, c2, c3 = st.columns(3)
    c1.download_button("Google Demo (Crypto/Botox)", generate_demo('google'), "demo_google_policy.xlsx")
    c2.download_button("LinkedIn Demo (Clickbait)", generate_demo('linkedin'), "demo_linkedin_policy.xlsx")
    c3.download_button("Meta Demo (Personal Attributes)", generate_demo('meta'), "demo_meta_policy.xlsx")

st.divider()

# UPLOAD
uploaded_file = st.file_uploader("Upload Excel File", type=['xlsx'])
if uploaded_file and st.session_state.df_data is None:
    df = pd.read_excel(uploaded_file)
    st.session_state.df_data = df
    st.session_state.platform = detect_platform(df)
    st.rerun()

# MAIN INTERFACE
if st.session_state.df_data is not None:
    df = st.session_state.df_data
    platform = st.session_state.platform
    memory = load_memory()
    
    st.info(f"Detected: **{platform}** | Total Rows: {len(df)}")
    
    rows_with_issues = []
    clean_rows_indices = []
    
    for idx, row in df.iterrows():
        issues = analyze_row(row, idx, platform, memory)
        if issues:
            rows_with_issues.append({'index': idx, 'row': row, 'issues': issues})
        else:
            clean_rows_indices.append(idx)
            
    # VIEW: ERRORS
    if rows_with_issues:
        st.subheader(f"🔴 Needs Attention ({len(rows_with_issues)})")
        
        for item in rows_with_issues:
            idx = item['index']
            issues = item['issues']
            
            with st.container(border=True):
                cols = st.columns([1, 2, 2, 1])
                cols[0].markdown(f"**Row {idx+2}**")
                
                with cols[1]:
                    for issue in issues:
                        st.markdown(f"**{issue['col']}**: :red[{issue['original']}]")
                        st.caption(f"⚠️ {issue['reason']}")
                        
                with cols[2]:
                    for issue in issues:
                        st.markdown(f"**Proposed**: :green[{issue['proposed']}]")
                
                with cols[3]:
                    if st.button("✨ Fix", key=f"fix_{idx}"):
                        for issue in issues:
                            st.session_state.df_data.at[idx, issue['col']] = issue['proposed']
                            if issue['col'] in ['Headline', 'Title', 'Ad Headline']:
                                save_memory({issue['original']: issue['proposed']})
                        st.rerun()

    else:
        st.success("🎉 All changes resolved! File is clean.")

    # VIEW: VALID CREATIVES
    st.divider()
    with st.expander(f"✅ Valid Creatives ({len(clean_rows_indices)} hidden)", expanded=False):
        if clean_rows_indices:
            st.dataframe(
                df.iloc[clean_rows_indices],
                use_container_width=True,
                column_config={
                    "Ad Headline": st.column_config.TextColumn("Ad Headline", width="medium"),
                    "Ad Description": st.column_config.TextColumn("Ad Description", width="large"),
                    "Headline": st.column_config.TextColumn("Headline", width="medium"),
                    "Description": st.column_config.TextColumn("Description", width="large"),
                    "Title": st.column_config.TextColumn("Title", width="medium"),
                    "Body": st.column_config.TextColumn("Body", width="large"),
                    "Final URL": st.column_config.TextColumn("Final URL", width="medium"),
                }
            )
        else:
            st.write("No valid rows yet.")

    # EXPORT
    if not rows_with_issues:
        st.download_button("📥 Download Clean Excel", to_excel(st.session_state.df_data), "clean_file.xlsx", type="primary")
    else:
        st.warning("Resolve all Policy Flags above to download.")

    if st.button("Start Over"):
        st.session_state.df_data = None
        st.rerun()
