import streamlit as st
import pandas as pd
import json
import os
import random
from io import BytesIO
from openpyxl import Workbook

# --- CONFIGURATION ---
st.set_page_config(page_title="Universal Ad Validator", page_icon="🌎", layout="wide")

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

# --- 3. VALIDATION LOGIC (Refactored for Review Mode) ---
def analyze_row(row, index, platform, memory):
    """
    Returns a list of issues for a single row.
    Each issue: {'col': 'Headline', 'original': '...', 'proposed': '...', 'reason': 'Too Long'}
    """
    issues = []
    
    # --- COMMON: URL CHECK ---
    url_col = None
    if 'Final URL' in row: url_col = 'Final URL'
    elif 'Landing Page URL' in row: url_col = 'Landing Page URL'
    elif 'Link URL' in row: url_col = 'Link URL'
    
    if url_col and pd.notna(row[url_col]):
        url = str(row[url_col])
        if ' ' in url:
            issues.append({
                'col': url_col,
                'original': url,
                'proposed': url.replace(' ', ''),
                'reason': 'Space in URL'
            })

    # --- GOOGLE ADS LOGIC ---
    if platform == "Google Ads":
        if 'Headline' in row and pd.notna(row['Headline']):
            text = str(row['Headline'])
            if text in memory:
                 # It matches a learned rule, but we still flag it so user can confirm
                 issues.append({'col': 'Headline', 'original': text, 'proposed': memory[text], 'reason': 'Learned Fix'})
            elif len(text) > 30:
                issues.append({
                    'col': 'Headline', 
                    'original': text, 
                    'proposed': text[:30], 
                    'reason': f'Too Long ({len(text)}/30)'
                })

        if 'Max CPC' in row and pd.notna(row['Max CPC']):
             issues.append({
                 'col': 'Max CPC',
                 'original': row['Max CPC'],
                 'proposed': None,
                 'reason': 'Manual Bid in Auto Campaign'
             })

    # --- LINKEDIN ADS LOGIC ---
    elif platform == "LinkedIn Ads":
        if 'Ad Headline' in row and pd.notna(row['Ad Headline']):
            text = str(row['Ad Headline'])
            if text in memory:
                 issues.append({'col': 'Ad Headline', 'original': text, 'proposed': memory[text], 'reason': 'Learned Fix'})
            elif len(text) > 70:
                issues.append({
                    'col': 'Ad Headline', 
                    'original': text, 
                    'proposed': text[:70], 
                    'reason': f'Truncation Risk ({len(text)}/70)'
                })

    # --- META ADS LOGIC ---
    elif platform == "Meta Ads (Facebook/Instagram)":
        if 'Title' in row and pd.notna(row['Title']):
            text = str(row['Title'])
            if text in memory:
                issues.append({'col': 'Title', 'original': text, 'proposed': memory[text], 'reason': 'Learned Fix'})
            elif len(text) > 40:
                issues.append({
                    'col': 'Title', 
                    'original': text, 
                    'proposed': text[:40], 
                    'reason': f'Too Long ({len(text)}/40)'
                })

    return issues

# --- 4. LARGE DEMO GENERATOR (50 Rows) ---
def generate_demo(platform):
    output = BytesIO()
    data = []
    
    # Common helper
    def rand_url():
        return random.choice(['https://site.com', 'https://broken url.com', 'https://mysite.org'])

    if platform == 'google':
        for i in range(50):
            # Create a mix of Good and Bad data
            if i < 5: # First 5 are bad
                row = {
                    'Headline': f"This Google Headline Is Way Too Long For Row {i}",
                    'Description': "Standard description text.",
                    'Final URL': rand_url(),
                    'Max CPC': 1.50 # Bad
                }
            else: # Rest are good
                row = {
                    'Headline': f"Good Headline {i}",
                    'Description': "Standard description text.",
                    'Final URL': "https://site.com",
                    'Max CPC': None
                }
            data.append(row)
            
    elif platform == 'linkedin':
        for i in range(50):
            if i < 5:
                row = {
                    'Campaign Name': 'Q1 Campaign',
                    'Ad Headline': f"This LinkedIn Headline Is Extremely Long And Will Definitely Get Cut Off On Mobile Row {i}",
                    'Ad Description': "Desc",
                    'Landing Page URL': rand_url()
                }
            else:
                row = {
                    'Campaign Name': 'Q1 Campaign',
                    'Ad Headline': f"Professional Update {i}",
                    'Ad Description': "Desc",
                    'Landing Page URL': "https://linkedin.com"
                }
            data.append(row)

    elif platform == 'meta':
        for i in range(50):
            if i < 5:
                row = {
                    'Campaign Name': 'Social',
                    'Title': f"This Facebook Title Is Too Long Row {i}",
                    'Body': "Body text",
                    'Link URL': rand_url()
                }
            else:
                row = {
                    'Campaign Name': 'Social',
                    'Title': f"Fresh Look {i}",
                    'Body': "Body text",
                    'Link URL': "https://meta.com"
                }
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
st.title("🌎 Universal Ad Validator (Review Mode)")
st.markdown("Upload your bulk sheet. Review errors one by one, then export.")

# --- SESSION STATE INITIALIZATION ---
if 'df_data' not in st.session_state:
    st.session_state.df_data = None
if 'platform' not in st.session_state:
    st.session_state.platform = None

# --- SECTION 1: DOWNLOAD DEMOS ---
with st.expander("📥 Get Demo Files (50 Rows)", expanded=False):
    c1, c2, c3 = st.columns(3)
    c1.download_button("Google Demo", generate_demo('google'), "large_google.xlsx")
    c2.download_button("LinkedIn Demo", generate_demo('linkedin'), "large_linkedin.xlsx")
    c3.download_button("Meta Demo", generate_demo('meta'), "large_meta.xlsx")

st.divider()

# --- SECTION 2: UPLOAD ---
uploaded_file = st.file_uploader("Upload Excel File", type=['xlsx'])

if uploaded_file and st.session_state.df_data is None:
    # Load for the first time
    df = pd.read_excel(uploaded_file)
    st.session_state.df_data = df
    st.session_state.platform = detect_platform(df)
    st.rerun()

# --- MAIN INTERFACE ---
if st.session_state.df_data is not None:
    df = st.session_state.df_data
    platform = st.session_state.platform
    memory = load_memory()
    
    st.info(f"Detected: **{platform}** | Total Rows: {len(df)}")
    
    # 1. ANALYZE ALL ROWS
    # We rebuild the list of errors every rerun
    rows_with_issues = []
    clean_rows_indices = []
    
    for idx, row in df.iterrows():
        issues = analyze_row(row, idx, platform, memory)
        if issues:
            rows_with_issues.append({'index': idx, 'row': row, 'issues': issues})
        else:
            clean_rows_indices.append(idx)
            
    # 2. VIEW: PROPOSED CHANGES (The "Errors")
    if rows_with_issues:
        st.subheader(f"🔴 Needs Attention ({len(rows_with_issues)})")
        
        for item in rows_with_issues:
            idx = item['index']
            row = item['row']
            issues = item['issues']
            
            # Create a Card for the Error
            with st.container(border=True):
                cols = st.columns([1, 2, 2, 1])
                cols[0].markdown(f"**Row {idx+2}**") # +2 for Excel header offset
                
                # Show the Error Details
                with cols[1]:
                    for issue in issues:
                        st.markdown(f"**{issue['col']}**: :red[{issue['original']}]")
                        st.caption(f"Error: {issue['reason']}")
                        
                # Show the Proposed Fix
                with cols[2]:
                    for issue in issues:
                        st.markdown(f"**Proposed**: :green[{issue['proposed']}]")
                
                # The Fix Button
                with cols[3]:
                    if st.button("✨ Fix", key=f"fix_{idx}"):
                        # Apply Fixes to Session State
                        for issue in issues:
                            st.session_state.df_data.at[idx, issue['col']] = issue['proposed']
                            
                            # Optional: Learn this fix
                            if issue['col'] in ['Headline', 'Title', 'Ad Headline']:
                                save_memory({issue['original']: issue['proposed']})
                        
                        st.rerun()

        # 3. VIEW: RAW PROBLEMATIC LINES (Requested by User)
        with st.expander("🔎 View Raw Problematic Data", expanded=False):
            st.dataframe(df.iloc[[item['index'] for item in rows_with_issues]], use_container_width=True)

    else:
        st.success("🎉 All changes resolved! File is clean.")

    # 4. VIEW: FINE CREATIVES (Must be expanded)
    st.divider()
    with st.expander(f"✅ Valid Creatives ({len(clean_rows_indices)} hidden)", expanded=False):
        if clean_rows_indices:
            st.dataframe(df.iloc[clean_rows_indices], use_container_width=True)
        else:
            st.write("No valid rows yet.")

    # 5. EXPORT FINAL
    if not rows_with_issues:
        st.download_button(
            "📥 Download Clean Excel", 
            to_excel(st.session_state.df_data), 
            "clean_file.xlsx", 
            type="primary"
        )
    else:
        st.warning("Fix all errors above to download the clean file.")

    # Reset Button
    if st.button("Start Over"):
        st.session_state.df_data = None
        st.rerun()
