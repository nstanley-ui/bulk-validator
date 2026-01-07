import streamlit as st
import pandas as pd
import json
import os
import random
import re
from io import BytesIO

# --- CONFIGURATION & AI THEME ---
st.set_page_config(page_title="Mojo // AI Validator", page_icon="🧬", layout="wide")

# CUSTOM CSS FOR "AI LOOK" (Dark Mode, Neon Accents, Tech Font)
st.markdown("""
<style>
    /* Main Background */
    .stApp {
        background-color: #0E1117;
        color: #E0E0E0;
    }
    /* Headers */
    h1, h2, h3 {
        font-family: 'Source Code Pro', monospace;
        background: -webkit-linear-gradient(45deg, #00D4FF, #00FF94);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
    }
    /* Cards/Containers */
    div[data-testid="stBorder"] {
        background-color: #161B22;
        border: 1px solid #30363D;
        border-radius: 8px;
    }
    /* Buttons */
    div.stButton > button {
        background-color: #21262D;
        color: #58A6FF;
        border: 1px solid #30363D;
        font-family: 'Source Code Pro', monospace;
    }
    div.stButton > button:hover {
        border-color: #58A6FF;
        box-shadow: 0 0 10px rgba(88, 166, 255, 0.2);
    }
    /* Primary Action Button */
    button[kind="primary"] {
        background: linear-gradient(90deg, #00D4FF, #0055FF);
        border: none;
        color: white !important;
        font-weight: bold;
    }
    /* Expander */
    .streamlit-expanderHeader {
        background-color: #161B22;
        color: #8B949E;
        font-family: 'Source Code Pro', monospace;
    }
    /* Badges */
    .platform-badge {
        font-size: 0.8rem;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: bold;
        font-family: monospace;
    }
</style>
""", unsafe_allow_html=True)

MEMORY_FILE = 'mojo_memory.json'

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
            return text.replace("Bitcoin", "Digital Assets").replace("Crypto", "Digital Assets"), "Restricted Financial Term"
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

# --- APP UI START ---

# SIDEBAR (Testing Instructions)
with st.sidebar:
    st.markdown("## 🧪 MOJO TEST PROTOCOL")
    st.info("Internal Build v0.9")
    
    st.markdown("""
    **TESTING POINTERS:**
    
    1. **Download the Demos:** Use the 'Test Data' section to get pre-broken files.
    
    2. **Trigger the 'Policy Engine':**
       - Google: Try words like "Bitcoin" or "Botox".
       - Meta: Try "Are you tired?" (Personal Attribute).
       - LinkedIn: Try "Shocking trick" (Clickbait).
       
    3. **Test Multi-Upload:** Drag all 3 demo files in at once to test the batch processor.
    
    4. **Train the AI:**
       - Fix an error manually (e.g., Change a headline).
       - Re-upload the same file.
       - Verify the AI *auto-fixes* it the second time.
    """)
    
    st.divider()
    st.caption("Mojo Creative Sandbox // Confidential")

# MAIN HEADER
st.title("MOJO // VALIDATOR")
st.caption("AI-Powered Compliance & Creative Validation Engine")

if 'file_cache' not in st.session_state:
    st.session_state.file_cache = {}

# DEMO DOWNLOADS
with st.expander("📂 GENERATE TEST DATA (50 ROWS)", expanded=False):
    st.markdown("Use these files to stress-test the validation logic.")
    c1, c2, c3 = st.columns(3)
    c1.download_button("Google Ads .xlsx", generate_demo('google'), "mojo_google_demo.xlsx")
    c2.download_button("LinkedIn Ads .xlsx", generate_demo('linkedin'), "mojo_linkedin_demo.xlsx")
    c3.download_button("Meta Ads .xlsx", generate_demo('meta'), "mojo_meta_demo.xlsx")

st.divider()

# MULTI-UPLOAD
uploaded_files = st.file_uploader("DROP FILES HERE // BATCH PROCESSING ENABLED", type=['xlsx'], accept_multiple_files=True)

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
    
    for filename, file_data in st.session_state.file_cache.items():
        
        df = file_data['df']
        platform = file_data['platform']
        
        # --- UI FOR EACH FILE ---
        st.markdown(f"### 📄 {filename}")
        
        # CHANNEL BADGE (Neon Style)
        if platform == "Google Ads":
            st.markdown('<span class="platform-badge" style="background:#4285F4; color:white">GOOGLE ADS</span>', unsafe_allow_html=True)
        elif platform == "LinkedIn Ads":
            st.markdown('<span class="platform-badge" style="background:#0077B5; color:white">LINKEDIN ADS</span>', unsafe_allow_html=True)
        elif platform == "Meta Ads (Facebook/Instagram)":
            st.markdown('<span class="platform-badge" style="background:#833AB4; color:white">META ADS</span>', unsafe_allow_html=True)
        else:
            st.error("UNKNOWN TEMPLATE")
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
        
        # RESULTS TABS
        tab1, tab2 = st.tabs([f"🔴 REJECTIONS ({len(rows_with_issues)})", f"✅ APPROVED ({len(clean_rows_indices)})"])
        
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
                                st.markdown("**AI Proposal**")
                                st.markdown(f":green[{issue['proposed']}]")
                        
                        with cols[3]:
                            if st.button("EXECUTE FIX", key=f"fix_{filename}_{idx}"):
                                for issue in issues:
                                    st.session_state.file_cache[filename]['df'].at[idx, issue['col']] = issue['proposed']
                                    if issue['col'] in ['Headline', 'Title', 'Headline']:
                                        save_memory({issue['original']: issue['proposed']})
                                st.rerun()
            else:
                st.success("NO VIOLATIONS DETECTED.")

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
                f"📥 DOWNLOAD CLEAN {filename}", 
                to_excel(st.session_state.file_cache[filename]['df']), 
                f"clean_{filename}", 
                key=f"dl_{filename}",
                type="primary"
            )
        else:
            st.warning(f"RESOLVE ISSUES IN {filename} TO ENABLE DOWNLOAD.")
            
        st.divider()

    # GLOBAL RESET
    if st.button("RESET SESSION"):
        st.session_state.file_cache = {}
        st.rerun()
