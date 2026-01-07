import streamlit as st
import pandas as pd
import json
import os
import random
import re
import requests
from io import BytesIO

# --- CONFIGURATION & HIGH CONTRAST THEME ---
st.set_page_config(page_title="Mojo Validator Pro", page_icon="🧬", layout="wide")

# CUSTOM CSS
st.markdown("""
<style>
    /* Main Background */
    .stApp {
        background-color: #F8F9FA;
        color: #212529;
    }
    /* Headers */
    h1, h2, h3 {
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        color: #0d1117;
        font-weight: 800;
        letter-spacing: -0.5px;
    }
    /* Cards */
    div[data-testid="stBorder"] {
        background-color: #FFFFFF;
        border: 1px solid #D1D5DB;
        border-radius: 6px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    /* Badges */
    .platform-badge {
        font-size: 0.75rem;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    /* Buttons */
    div.stButton > button {
        width: 100%;
        border-radius: 4px;
        font-weight: 600;
    }
    /* Fix Button */
    button[kind="primary"] {
        background-color: #2563EB; 
        border: none;
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

# --- 2. LINK CHECKER (Cached) ---
@st.cache_data(show_spinner=False, ttl=600) # Cache results for 10 mins
def check_link_health(url):
    """
    Pings the URL to check for 404s, timeouts, or redirects.
    Returns: (Proposed Fix, Reason) or (None, None)
    """
    if not url or not isinstance(url, str):
        return None, None
        
    # 1. Basic Syntax Check
    if not url.startswith(('http://', 'https://')):
        return "https://" + url, "Missing Protocol (https://)"
    
    if " " in url:
        return url.replace(" ", ""), "Space in URL"

    # 2. Live Connectivity Check
    # We pretend httpstat.us URLs are real failures for the demo
    try:
        # User-Agent to avoid getting blocked by some firewalls
        headers = {'User-Agent': 'MojoValidator/1.0'}
        response = requests.head(url, headers=headers, timeout=2.0, allow_redirects=True)
        
        # Fallback to GET if HEAD fails (some servers block HEAD)
        if response.status_code == 405:
            response = requests.get(url, headers=headers, timeout=2.0, stream=True)
            
        code = response.status_code
        
        if code == 404:
            return None, "❌ Dead Link (404 Not Found)"
        elif code >= 500:
            return None, f"❌ Server Error ({code})"
        elif code == 403:
            return None, "⚠️ Access Forbidden (403) - Check Permissions"
            
    except requests.Timeout:
        return None, "🟠 Slow Response (>2s Timeout)"
    except requests.ConnectionError:
        return None, "❌ Connection Failed (DNS/Network)"
    except Exception as e:
        return None, f"⚠️ Error: {str(e)}"

    return None, None

# --- 3. PLATFORM DETECTION ---
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

# --- 4. REJECTION LOGIC & POLICY CHECKS ---
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

# --- 5. MAIN ANALYZER ---
def analyze_row(row, index, platform, memory, filename, ignored_set, check_links_enabled):
    issues = []
    
    def is_ignored(col_name):
        key = f"{filename}|{index}|{col_name}"
        return key in ignored_set

    # URL CHECK (COMMON)
    url_col = None
    if 'Final URL' in row: url_col = 'Final URL'
    elif 'Destination URL' in row: url_col = 'Destination URL'
    elif 'Link URL' in row: url_col = 'Link URL'
    
    if url_col and pd.notna(row[url_col]) and not is_ignored(url_col):
        url = str(row[url_col])
        
        # 1. Syntax Check (Always run)
        if ' ' in url:
            issues.append({'col': url_col, 'original': url, 'proposed': url.replace(' ', ''), 'reason': 'Space in URL'})
        elif not url.startswith(('http://', 'https://')):
            issues.append({'col': url_col, 'original': url, 'proposed': 'https://' + url, 'reason': 'Missing Protocol'})
        
        # 2. Live Health Check (If enabled)
        elif check_links_enabled:
            fix, reason = check_link_health(url)
            if reason:
                 # If it's a fixable protocol error (returned by function)
                 if fix: 
                     issues.append({'col': url_col, 'original': url, 'proposed': fix, 'reason': reason})
                 else:
                     # If it's a Dead Link (404), we don't have a proposed fix, just a flag
                     issues.append({'col': url_col, 'original': url, 'proposed': url, 'reason': reason})

    # PLATFORM SPECIFIC
    if platform == "Google Ads":
        if 'Headline' in row and pd.notna(row['Headline']) and not is_ignored('Headline'):
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

        if 'Max CPC' in row and pd.notna(row['Max CPC']) and not is_ignored('Max CPC'):
             issues.append({'col': 'Max CPC', 'original': row['Max CPC'], 'proposed': None, 'reason': 'Manual Bid in Auto Campaign'})

    elif platform == "LinkedIn Ads":
        if 'Headline' in row and pd.notna(row['Headline']) and not is_ignored('Headline'):
            text = str(row['Headline'])
            fix, reason = check_policy_violations(text, platform)
            if fix:
                issues.append({'col': 'Headline', 'original': text, 'proposed': fix, 'reason': f"Policy: {reason}"})
            elif len(text) > 70:
                issues.append({'col': 'Headline', 'original': text, 'proposed': text[:70], 'reason': f'Mobile Truncation Risk ({len(text)}/70)'})

        if 'Introductory Text' in row and pd.notna(row['Introductory Text']) and not is_ignored('Introductory Text'):
            text = str(row['Introductory Text'])
            if len(text) > 150:
                 issues.append({'col': 'Introductory Text', 'original': text, 'proposed': text, 'reason': f'Will get "See More" cut-off ({len(text)}/150)'})

        valid_ctas = ['APPLY', 'DOWNLOAD', 'VIEW_QUOTE', 'LEARN_MORE', 'SIGN_UP', 'SUBSCRIBE', 'REGISTER', 'JOIN', 'ATTEND', 'REQUEST_DEMO']
        if 'Call to Action' in row and not is_ignored('Call to Action'):
            cta = str(row['Call to Action']).upper().replace(' ', '_')
            if pd.isna(row['Call to Action']) or row['Call to Action'] == '':
                 issues.append({'col': 'Call to Action', 'original': '', 'proposed': 'LEARN_MORE', 'reason': 'Missing Required CTA'})
            elif cta not in valid_ctas:
                 issues.append({'col': 'Call to Action', 'original': row['Call to Action'], 'proposed': 'LEARN_MORE', 'reason': 'Invalid CTA Format'})

        if 'Image File Name' in row and not is_ignored('Image File Name'):
             img = str(row['Image File Name'])
             if pd.isna(img) or img == 'nan' or img == '':
                  issues.append({'col': 'Image File Name', 'original': '', 'proposed': 'creative_placeholder.jpg', 'reason': 'Missing Image File'})

    elif platform == "Meta Ads (Facebook/Instagram)":
        if 'Title' in row and pd.notna(row['Title']) and not is_ignored('Title'):
            text = str(row['Title'])
            fix, reason = check_policy_violations(text, platform)
            if fix:
                issues.append({'col': 'Title', 'original': text, 'proposed': fix, 'reason': f"Policy: {reason}"})
            elif len(text) > 40:
                issues.append({'col': 'Title', 'original': text, 'proposed': text[:40], 'reason': f'Too Long ({len(text)}/40)'})

        if 'Body' in row and pd.notna(row['Body']) and not is_ignored('Body'):
            text = str(row['Body'])
            fix, reason = check_policy_violations(text, platform)
            if fix:
                issues.append({'col': 'Body', 'original': text, 'proposed': fix, 'reason': f"Policy: {reason}"})
                
        if 'Image' in row and not is_ignored('Image'):
             img = str(row['Image'])
             if pd.isna(img) or img == 'nan' or img == '':
                  issues.append({'col': 'Image', 'original': '', 'proposed': 'creative_placeholder.jpg', 'reason': 'Missing Image File'})

    return issues

# --- 6. DEMO GENERATOR ---
def generate_demo(platform):
    output = BytesIO()
    data = []
    
    # We use httpstat.us to simulate real HTTP errors
    broken_url = "https://httpstat.us/404"
    server_err_url = "https://httpstat.us/500"
    good_url = "https://www.google.com"
    
    if platform == 'google':
        for i in range(50):
            row = {'Headline': f"Valid Headline {i}", 'Description': "Desc", 'Final URL': good_url, 'Max CPC': None}
            if i == 0: 
                row['Headline'] = "Invest in Bitcoin"
                row['Final URL'] = broken_url # 404
            if i == 1: 
                row['Headline'] = "Prescription Meds"
                row['Final URL'] = server_err_url # 500
            if i == 2: row['Headline'] = "THIS IS SHOUTING"
            if i == 3: row['Headline'] = "Headline Too Long For Google Ads"
            if i == 4: row['Max CPC'] = 1.50
            data.append(row)
            
    elif platform == 'linkedin':
        for i in range(50):
            row = {'Campaign Name': 'Q1', 'Headline': f"Professional Update {i}", 'Introductory Text': "Intro", 'Destination URL': good_url, 'Image File Name': f"img_{i}.jpg", 'Call to Action': 'LEARN_MORE'}
            if i == 0: 
                row['Headline'] = "You won't believe this shocking trick"
                row['Destination URL'] = broken_url # 404
            if i == 1: row['Headline'] = "This headline is way too long for LinkedIn mobile devices and will cut off"
            if i == 2: row['Call to Action'] = "CLICK HERE"
            data.append(row)

    elif platform == 'meta':
        for i in range(50):
            row = {'Campaign Name': 'Social', 'Title': f"Fresh Look {i}", 'Body': "Vibes.", 'Link URL': good_url, 'Image': f"pic_{i}.jpg"}
            if i == 0: 
                row['Body'] = "Are you tired of being overweight?"
                row['Link URL'] = broken_url # 404
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

if 'file_cache' not in st.session_state:
    st.session_state.file_cache = {}
if 'ignored_issues' not in st.session_state:
    st.session_state.ignored_issues = set()
if 'user_edits' not in st.session_state:
    st.session_state.user_edits = {}

# SIDEBAR
with st.sidebar:
    st.markdown("### 🧬 Mojo Validator Pro")
    st.caption("Internal Release v1.3")
    
    st.info("""
    **HOW TO FIX:**
    
    1. **Accept AI Fix:** Click '✅ Fix' to use our suggestion.
    2. **Write Your Own:** Edit the text box, then click '🔄 Recheck'.
    3. **Ignore:** Whitelist the error.
    """)
    
    st.divider()
    
    # NEW: LINK CHECKER TOGGLE
    check_links = st.toggle("Live Link Checker", value=True, help="Pings every URL to check for 404s. Disable for faster processing on massive files.")
    if check_links:
        st.caption("🟢 Link Checks Active")
    else:
        st.caption("⚪ Link Checks Paused")

# MAIN HEADER
st.title("Mojo // Creative Validator")
st.markdown("Multi-platform compliance engine. Upload your bulk sheets to automatically fix API errors, policy violations, and broken landing pages.")

# DEMO DOWNLOADS
with st.expander("📂 Download Test Data (With 404 Errors)", expanded=False):
    c1, c2, c3 = st.columns(3)
    c1.download_button("Google Ads .xlsx", generate_demo('google'), "mojo_google_demo.xlsx")
    c2.download_button("LinkedIn Ads .xlsx", generate_demo('linkedin'), "mojo_linkedin_demo.xlsx")
    c3.download_button("Meta Ads .xlsx", generate_demo('meta'), "mojo_meta_demo.xlsx")

st.divider()

# MULTI-UPLOAD
uploaded_files = st.file_uploader("Drop Excel Files Here (Batch Processing)", type=['xlsx'], accept_multiple_files=True)

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
    
    file_keys = list(st.session_state.file_cache.keys())
    
    for filename in file_keys:
        file_data = st.session_state.file_cache[filename]
        df = file_data['df']
        platform = file_data['platform']
        
        # --- FILE HEADER ---
        st.markdown(f"### 📄 {filename}")
        
        badge_style = "background:#E9ECEF; color:#495057; border:1px solid #CED4DA"
        if platform == "Google Ads":
            badge_style = "background:#E8F0FE; color:#1A73E8; border:1px solid #1A73E8"
        elif platform == "LinkedIn Ads":
            badge_style = "background:#E1F5FE; color:#0077B5; border:1px solid #0077B5"
        elif platform == "Meta Ads (Facebook/Instagram)":
            badge_style = "background:#F3E5F5; color:#833AB4; border:1px solid #833AB4"
            
        st.markdown(f'<span class="platform-badge" style="{badge_style}">{platform}</span>', unsafe_allow_html=True)
        st.write("") 

        # ANALYZE (With Link Checker if enabled)
        rows_with_issues = []
        clean_rows_indices = []
        
        for idx in df.index:
            row = df.loc[idx]
            issues = analyze_row(row, idx, platform, memory, filename, st.session_state.ignored_issues, check_links)
            if issues:
                rows_with_issues.append({'index': idx, 'row': row, 'issues': issues})
            else:
                clean_rows_indices.append(idx)
        
        # --- ERROR REVIEW SECTION ---
        if rows_with_issues:
            st.markdown(f"##### 🔴 Detected Issues ({len(rows_with_issues)})")
            
            for item in rows_with_issues:
                idx = item['index']
                issues = item['issues']
                
                with st.container(border=True):
                    cols = st.columns([0.5, 2, 2.5, 1.5])
                    
                    # Col 1: Row Num
                    cols[0].caption(f"Row {idx+2}")
                    
                    # Col 2: The Problem
                    with cols[1]:
                        for issue in issues:
                            st.markdown(f"**{issue['col']}**")
                            st.code(issue['original'], language=None)
                            st.caption(f"⚠️ {issue['reason']}")
                    
                    # Col 3: The Fix (EDITABLE)
                    with cols[2]:
                        for i_issue, issue in enumerate(issues):
                            st.markdown("**Proposed Fix (Edit to Change)**")
                            
                            edit_key = f"edit_{filename}_{idx}_{issue['col']}"
                            default_val = str(issue['proposed']) if issue['proposed'] is not None else ""
                            
                            new_val = st.text_input(
                                label="Edit Fix", 
                                value=default_val, 
                                key=edit_key, 
                                label_visibility="collapsed"
                            )
                            
                            if f"{filename}_{idx}" not in st.session_state.user_edits:
                                st.session_state.user_edits[f"{filename}_{idx}"] = {}
                            st.session_state.user_edits[f"{filename}_{idx}"][issue['col']] = new_val

                            if new_val != default_val:
                                st.caption("✏️ Manual edit detected")

                    # Col 4: ACTIONS
                    with cols[3]:
                        st.write("") 
                        
                        # FIX / RECHECK
                        if st.button("✅ Fix / Recheck", key=f"fix_{filename}_{idx}", type="primary", use_container_width=True):
                            updates = st.session_state.user_edits.get(f"{filename}_{idx}", {})
                            
                            for issue in issues:
                                final_val = updates.get(issue['col'], issue['proposed'])
                                st.session_state.file_cache[filename]['df'].at[idx, issue['col']] = final_val
                                
                                if str(final_val) != str(issue['proposed']) and issue['col'] in ['Headline', 'Title', 'Headline']:
                                    save_memory({issue['original']: final_val})
                                    st.toast("🧠 Brain trained with your manual fix!")
                            st.rerun()

                        # IGNORE
                        if st.button("🙈 Ignore", key=f"ignore_{filename}_{idx}", use_container_width=True):
                            for issue in issues:
                                key = f"{filename}|{idx}|{issue['col']}"
                                st.session_state.ignored_issues.add(key)
                            st.rerun()

                        # EXCLUDE
                        if st.button("🗑️ Exclude Row", key=f"drop_{filename}_{idx}", use_container_width=True):
                            st.session_state.file_cache[filename]['df'].drop(idx, inplace=True)
                            st.rerun()
        else:
            st.success("✨ No errors detected.")

        # --- VALID ROWS SECTION (Expandable Bar) ---
        st.write("")
        with st.expander(f"✅ Valid Data ({len(clean_rows_indices)}) - Click to View", expanded=False):
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
                    df.loc[clean_rows_indices],
                    use_container_width=True,
                    column_config=config,
                    key=f"data_{filename}"
                )
            else:
                st.caption("No valid rows yet.")

        # EXPORT
        if not rows_with_issues:
            st.download_button(
                f"📥 Download Clean {filename}", 
                to_excel(st.session_state.file_cache[filename]['df']), 
                f"clean_{filename}", 
                key=f"dl_{filename}",
                type="primary"
            )
        else:
            st.warning(f"Resolve remaining items in {filename} to enable download.")
            
        st.divider()

    # GLOBAL RESET
    if st.button("Clear All Files"):
        st.session_state.file_cache = {}
        st.session_state.ignored_issues = set()
        st.session_state.user_edits = {}
        st.rerun()
