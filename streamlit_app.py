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
    if {'Title', 'Body', 'Link URL'}.issubset(columns):
        return "Meta Ads (Facebook/Instagram)"
    elif {'Headline', 'Introductory Text', 'Destination URL'}.issubset(columns):
        return "LinkedIn Ads"
    elif {'Headline', 'Description', 'Final URL'}.issubset(columns):
        return "Google Ads"
    else:
        return "Unknown"

# --- 3. REJECTION LOGIC & POLICY CHECKS ---
def check_policy_violations(text, platform):
    if not isinstance(text, str): return None, None
    text_lower = text.lower()
    
    # GOOGLE
    if platform == "Google Ads":
        if re.search(r'\b(crypto|bitcoin|eth|ico)\b', text_lower):
            return text.replace("Bitcoin", "Digital Assets"), "Restricted Financial Term"
        if re.search(r'\b(botox|prescription|drugs)\b', text_lower):
            return "Medical Treatments", "Restricted Medical Term"
        if "best" in text_lower or "#1" in text:
            return text.replace("Best", "Top").replace("#1", "Leading"), "Unsubstantiated Superlative"
        if "!!" in text:
            return text.replace("!!", "!"), "Excessive Punctuation"

    # META
    elif platform == "Meta Ads (Facebook/Instagram)":
        if re.search(r'\b(are you|do you have|do you suffer)\b', text_lower):
            return text.replace("Are you", "For those").replace("Do you have", "Help for"), "Personal Attribute Policy (Risk)"
        if re.search(r'\b(make money|get rich|work from home)\b', text_lower):
            return "Start your career today", "Misleading/MLM Policy"

    # LINKEDIN
    elif platform == "LinkedIn Ads":
        if re.search(r'\b(too old|too young)\b', text_lower):
            return text, "Potential Discrimination Policy"
        if re.search(r'\b(shocking|you won\'t believe)\b', text_lower):
            return "Industry Insights", "Sensationalism Policy"

    return None, None

# --- 4. MAIN ANALYZER ---
def analyze_row(row, index, platform, memory):
    issues = []
    
    # URL CHECK
    url_col = None
    if 'Final URL' in row: url_col = 'Final URL'
    elif 'Destination URL' in row: url_col = 'Destination URL'
    elif 'Link URL' in row: url_col = 'Link URL'
    
    if url_col and pd.notna(row[url_col]):
        url = str(row[url_col])
        if ' ' in url:
            issues.append({'col': url_col, 'original': url, 'proposed': url.replace(' ', ''), 'reason': 'Space in URL'})
        if not url.startswith(('http://', 'https://')):
            issues.append({'col': url_col, 'original': url, 'proposed': 'https://' + url, 'reason': 'Missing http/https'})

    # PLATFORM SPECIFIC
    if platform == "Google Ads":
        if 'Headline' in row and pd.notna(row['Headline']):
            text = str(row['Headline'])
            fix, reason = check_policy_violations(text, platform)
            if fix:
                issues.append({'col': 'Headline', 'original': text, 'proposed': fix, 'reason': f"Policy: {reason}"})
            elif text in memory:
                 issues.append({'col': 'Headline', 'original': text, 'proposed': memory[text], 'reason': 'Learned Fix'})
            elif len(text) > 30:
                issues.append({'col': 'Headline', 'original': text, 'proposed': text[:30], 'reason': f'Too Long ({len(text)}/30)'})
            elif text.isupper() and len(text) > 4:
                 issues.append({'col': 'Headline', 'original': text, 'proposed': text.title(), 'reason': 'Excessive Capitalization'})

        if 'Max CPC' in row and pd.notna(row['Max CPC']):
             issues.append({'col': 'Max CPC', 'original': row['Max CPC'], 'proposed': None, 'reason': 'Manual Bid in Auto Campaign'})

    elif platform == "LinkedIn Ads":
        if 'Headline' in row and pd.notna(row['Headline']):
            text = str(row['Headline'])
            fix, reason = check_policy_violations(text, platform)
            if fix:
                issues.append({'col': 'Headline', 'original': text, 'proposed': fix, 'reason': f"Policy: {reason}"})
            elif len(text) > 70:
                issues.append({'col': 'Headline', 'original': text, 'proposed': text[:70], 'reason': f'Mobile Truncation Risk ({len(text)}/70)'})

        if 'Introductory Text' in row and pd.notna(row['Introductory Text']):
            text = str(row['Introductory Text'])
            if len(text) > 150:
                 issues.append({'col': 'Introductory Text', 'original': text, 'proposed': text, 'reason': f'Will get "See More" cut-off ({len(text)}/150)'})

        valid_ctas = ['APPLY', 'DOWNLOAD', 'VIEW_QUOTE', 'LEARN_MORE', 'SIGN_UP', 'SUBSCRIBE', 'REGISTER', 'JOIN', 'ATTEND', 'REQUEST_DEMO']
        if 'Call to Action' in row:
            cta = str(row['Call to Action']).upper().replace(' ', '_')
            if pd.isna(row['Call to Action']) or row['Call to Action'] == '':
                 issues.append({'col': 'Call to Action', 'original': '', 'proposed': 'LEARN_MORE', 'reason': 'Missing Required CTA'})
            elif cta not in valid_ctas:
                 issues.append({'col': 'Call to Action', 'original': row['Call to Action'], 'proposed': 'LEARN_MORE', 'reason': 'Invalid CTA Format'})

        if 'Image File Name' in row:
             img = str(row['Image File Name'])
             if pd.isna(img) or img == 'nan' or img == '':
                  issues.append({'col': 'Image File Name', 'original': '', 'proposed': 'creative_placeholder.jpg', 'reason': 'Missing Image File'})

    elif platform == "Meta Ads (Facebook/Instagram)":
        if 'Title' in row and pd.notna(row['Title']):
            text = str(row['Title'])
            fix, reason = check_policy_violations(text, platform)
            if fix:
                issues.append({'col': 'Title', 'original': text, 'proposed': fix, 'reason': f"Policy: {reason}"})
            elif len(text) > 40:
                issues.append({'col': 'Title', 'original': text, 'proposed': text[:40], 'reason': f'Too Long ({len(text)}/40)'})

        if 'Body' in row and pd.notna(row['Body']):
            text = str(row['Body'])
            fix, reason = check_policy_violations(text, platform)
            if fix:
                issues.append({'col': 'Body', 'original': text, 'proposed': fix, 'reason': f"Policy: {reason}"})
                
        if 'Image' in row:
             img = str(row['Image'])
             if pd.isna(img) or img == 'nan' or img == '':
                  issues.append({'col': 'Image', 'original': '', 'proposed': 'creative_placeholder.jpg', 'reason': 'Missing Image File'})

    return issues

# --- 5. DEMO GENERATOR ---
def generate_demo(platform):
    output = BytesIO()
    data = []
    
    if platform == 'google':
        for i in range(50):
            row = {'Headline': f"Valid Headline {i}", 'Description': "Desc", 'Final URL': "https://site.com", 'Max CPC': None}
            if i == 0: row['Headline'] = "Invest in Bitcoin"
            if i == 1: row['Headline'] = "Prescription Meds"
            if i == 2: row['Headline'] = "THIS IS SHOUTING"
            if i == 3: row['Headline'] = "Headline Too Long For Google Ads"
            if i == 4: row['Max CPC'] = 1.50
            data.append(row)
            
    elif platform == 'linkedin':
        for i in range(50):
            row = {'Campaign Name': 'Q1', 'Headline': f"Professional Update {i}", 'Introductory Text': "Intro", 'Destination URL': "https://li.com", 'Image File Name': f"img_{i}.jpg", 'Call to Action': 'LEARN_MORE'}
            if i == 0: row['Headline'] = "You won't believe this shocking trick"
            if i == 1: row['Headline'] = "This headline is way too long for LinkedIn mobile devices and will cut off"
            if i == 2: row['Call to Action'] = "CLICK HERE"
            data.append(row)

    elif platform == 'meta':
        for i in range(50):
            row = {'Campaign Name': 'Social', 'Title': f"Fresh Look {i}", 'Body': "Vibes.", 'Link URL': "https://meta.com", 'Image': f"pic_{i}.jpg"}
            if i == 0: row['Body'] = "Are you tired of being overweight?"
            if i == 1: row['Title'] = "Work from home get rich"
            if i == 2: row['Title'] = "This Title Is Too Long For Meta Feed"
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

if 'file_cache' not in st.session_state:
    st.session_state.file_cache = {}

# DEMO DOWNLOADS
with st.expander("📥 Get Demo Files (50 Rows)", expanded=False):
    c1, c2, c3 = st.columns(3)
    c1.download_button("Google Demo", generate_demo('google'), "demo_google.xlsx")
    c2.download_button("LinkedIn Demo", generate_demo('linkedin'), "demo_linkedin.xlsx")
    c3.download_button("Meta Demo", generate_demo('meta'), "demo_meta.xlsx")

st.divider()

# MULTI-UPLOAD
uploaded_files = st.file_uploader("Upload Excel Files (Batch Processing)", type=['xlsx'], accept_multiple_files=True)

# PROCESS FILES INTO STATE
if uploaded_files:
    for uploaded_file in uploaded_files:
        file_key = uploaded_file.name
        if file_key not in st.session_state.file_cache:
            df = pd.read_excel(uploaded_file)
            platform = detect_platform(df)
            st.session_state.file_cache[file_key] = {
                'df': df,
                'platform': platform
            }

# MAIN INTERFACE LOOP
if st.session_state.file_cache:
    memory = load_memory()
    
    # Iterate through each file in session state
    # Using list() to allow modification of dict during iteration if needed (though we aren't deleting here)
    for filename, file_data in st.session_state.file_cache.items():
        
        df = file_data['df']
        platform = file_data['platform']
        
        # --- UI FOR EACH FILE ---
        st.markdown(f"### 📄 {filename}")
        
        # CHANNEL BADGE
        if platform == "Google Ads":
            st.caption("DETECTED CHANNEL: :blue-background[**GOOGLE ADS**]")
        elif platform == "LinkedIn Ads":
            st.caption("DETECTED CHANNEL: :blue-background[**LINKEDIN ADS**]")
        elif platform == "Meta Ads (Facebook/Instagram)":
            st.caption("DETECTED CHANNEL: :blue-background[**META ADS**]")
        else:
            st.error("Unknown Template Format")
            continue

        # ANALYZE
        rows_with_issues = []
        clean_rows_indices = []
        
        for idx, row in df.iterrows():
            issues = analyze_row(row, idx, platform, memory)
            if issues:
                rows_with_issues.append({'index': idx, 'row': row, 'issues': issues})
            else:
                clean_rows_indices.append(idx)
        
        # RESULTS TABS (Errors vs Valid)
        tab1, tab2 = st.tabs([f"🔴 Errors ({len(rows_with_issues)})", f"✅ Valid ({len(clean_rows_indices)})"])
        
        with tab1:
            if rows_with_issues:
                for item in rows_with_issues:
                    idx = item['index']
                    issues = item['issues']
                    
                    with st.container(border=True):
                        cols = st.columns([1, 2, 2, 1])
                        cols[0].markdown(f"**Row {idx+2}**")
                        
                        with cols[1]:
                            for issue in issues:
                                st.markdown(f"**{issue['col']}**")
                                st.caption(f":red[{issue['original']}]")
                                st.caption(f"⚠️ {issue['reason']}")
                        
                        with cols[2]:
                            for issue in issues:
                                st.markdown("**Proposed**")
                                st.markdown(f":green[{issue['proposed']}]")
                        
                        with cols[3]:
                            # Unique key for every button: filename + row index
                            if st.button("✨ Fix", key=f"fix_{filename}_{idx}"):
                                for issue in issues:
                                    st.session_state.file_cache[filename]['df'].at[idx, issue['col']] = issue['proposed']
                                    if issue['col'] in ['Headline', 'Title', 'Headline']:
                                        save_memory({issue['original']: issue['proposed']})
                                st.rerun()
            else:
                st.info("No errors found in this file.")

        with tab2:
            if clean_rows_indices:
                config = {
                    "Final URL": st.column_config.TextColumn("Final URL", width="medium"),
                    "Destination URL": st.column_config.TextColumn("Destination URL", width="medium"),
                    "Link URL": st.column_config.TextColumn("Link URL", width="medium"),
                }
                if platform == "LinkedIn Ads":
                    config["Headline"] = st.column_config.TextColumn("Headline", width="medium")
                    config["Introductory Text"] = st.column_config.TextColumn("Introductory Text", width="large")
                elif platform == "Meta Ads (Facebook/Instagram)":
                    config["Title"] = st.column_config.TextColumn("Title", width="medium")
                    config["Body"] = st.column_config.TextColumn("Body", width="large")
                elif platform == "Google Ads":
                    config["Headline"] = st.column_config.TextColumn("Headline", width="medium")
                    config["Description"] = st.column_config.TextColumn("Description", width="large")

                st.dataframe(
                    df.iloc[clean_rows_indices],
                    use_container_width=True,
                    column_config=config,
                    key=f"data_{filename}"
                )
            else:
                st.write("No valid rows yet.")

        # EXPORT BUTTON FOR THIS FILE
        if not rows_with_issues:
            st.download_button(
                f"📥 Download Clean {filename}", 
                to_excel(st.session_state.file_cache[filename]['df']), 
                f"clean_{filename}", 
                key=f"dl_{filename}",
                type="primary"
            )
        else:
            st.warning(f"Fix errors in {filename} to download.")
            
        st.divider()

    # GLOBAL RESET
    if st.button("Start Over (Clear All)"):
        st.session_state.file_cache = {}
        st.rerun()
