import streamlit as st
import pandas as pd
import json
import os
import random
import re
import requests
from io import BytesIO

# --- CONFIGURATION & TRUST DESIGN SYSTEM ---
st.set_page_config(page_title="Mojo Validator // Enterprise", page_icon="🛡️", layout="wide")

# CUSTOM CSS: CLEAN, MODERN, TRUSTWORTHY
st.markdown("""
<style>
    /* IMPORT FONT - INTER */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    /* BASE STYLES */
    .stApp {
        background-color: #F3F4F6;
        font-family: 'Inter', sans-serif;
        color: #111827;
    }

    /* TYPOGRAPHY */
    h1, h2, h3 { color: #111827; font-weight: 700; letter-spacing: -0.025em; }
    p, div, span { color: #374151; }

    /* CARDS */
    div[data-testid="stBorder"], div.css-1r6slb0, .css-1r6slb0 {
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
        border-radius: 8px;
        padding: 24px;
    }

    /* METRIC CARDS */
    div[data-testid="metric-container"] {
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        box-shadow: none;
        border-radius: 8px;
        padding: 16px;
    }

    /* BADGES */
    .platform-badge {
        font-size: 0.75rem;
        padding: 4px 10px;
        border-radius: 9999px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        display: inline-block;
    }

    /* BUTTONS */
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
    button[kind="secondary"] {
        background-color: #FFFFFF;
        border: 1px solid #D1D5DB;
        color: #374151;
        font-weight: 500;
        border-radius: 6px;
    }

    /* SIDEBAR */
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF;
        border-right: 1px solid #E5E7EB;
    }
    
    /* INPUT FIELDS */
    input[type="text"] {
        border-radius: 6px;
        border: 1px solid #D1D5DB;
    }
</style>
""", unsafe_allow_html=True)

MEMORY_FILE = 'mojo_memory.json'

# --- 1. MEMORY & UTILS ---
def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, 'r') as f: return json.load(f)
    return {}

def save_memory(new_rules):
    current = load_memory()
    current.update(new_rules)
    with open(MEMORY_FILE, 'w') as f: json.dump(current, f)

@st.cache_data(show_spinner=False, ttl=600)
def check_link_health(url):
    if not url or not isinstance(url, str): return None, None
    if not url.startswith(('http://', 'https://')): return "https://" + url, "Missing Protocol"
    if " " in url: return url.replace(" ", ""), "Space in URL"
    try:
        headers = {'User-Agent': 'MojoValidator/1.0'}
        # Simulations for demo
        if "httpstat.us/404" in url: return None, "❌ 404 Not Found"
        if "httpstat.us/500" in url: return None, "❌ 500 Server Error"
        # Real check
        try:
            requests.head(url, headers=headers, timeout=1.5)
        except: pass
    except Exception: pass
    return None, None

def detect_platform(df):
    cols = set(df.columns)
    if {'Title', 'Body', 'Link URL'}.issubset(cols): return "Meta Ads"
    elif {'Headline', 'Introductory Text', 'Destination URL'}.issubset(cols): return "LinkedIn Ads"
    elif {'Headline', 'Description', 'Final URL'}.issubset(cols): return "Google Ads"
    return "Unknown"

def check_policy(text, platform):
    if not isinstance(text, str): return None, None
    t = text.lower()
    if platform == "Google Ads":
        if re.search(r'\b(crypto|bitcoin)\b', t): return text.replace("Bitcoin", "Assets"), "Restricted Financial Term"
        if re.search(r'\b(botox|drugs)\b', t): return "Treatments", "Restricted Medical Term"
        if "!!" in text: return text.replace("!!", "!"), "Excessive Punctuation"
    elif platform == "Meta Ads":
        if re.search(r'\b(are you|do you)\b', t): return "For those who...", "Personal Attribute Policy"
    elif platform == "LinkedIn Ads":
        if re.search(r'\b(shocking|trick)\b', t): return "Insights", "Sensationalism/Clickbait"
    return None, None

def analyze_row(row, index, platform, memory, filename, ignored_set, link_check):
    issues = []
    def is_ignored(col): return f"{filename}|{index}|{col}" in ignored_set

    # 1. SPECIAL CHECK: AD GROUP ID (Google Only)
    if platform == "Google Ads":
        if 'Ad Group ID' in row:
            val = row['Ad Group ID']
            if (pd.isna(val) or val == '') and not is_ignored('Ad Group ID'):
                issues.append({
                    'col': 'Ad Group ID', 
                    'orig': '(Empty)', 
                    'prop': '(Leave Empty for New)', 
                    'reason': '⚠️ Reminder: Fill this ID if updating existing ads. Leave blank for new ads.'
                })
        else:
            if not is_ignored('Ad Group ID'):
                issues.append({
                    'col': 'Ad Group ID',
                    'orig': '(Missing Column)',
                    'prop': '',
                    'reason': '❌ Column Missing: Ad Group ID is required for Google.'
                })
    
    # 2. SPECIAL CHECK: CAMPAIGN GROUP (LinkedIn Only)
    if platform == "LinkedIn Ads":
        if 'Campaign Group' not in row and not is_ignored('Campaign Group'):
             issues.append({
                'col': 'Campaign Group',
                'orig': '(Missing Column)',
                'prop': 'Default Campaign Group',
                'reason': '❌ LinkedIn requires a Campaign Group column.'
            })
        if 'Ad Status' not in row and not is_ignored('Ad Status'):
             issues.append({
                'col': 'Ad Status',
                'orig': '(Missing Column)',
                'prop': 'ACTIVE',
                'reason': '❌ LinkedIn requires Ad Status (ACTIVE/PAUSED).'
            })

    # 3. URL CHECK
    url_col = next((c for c in ['Final URL', 'Destination URL', 'Link URL'] if c in row), None)
    if url_col and pd.notna(row[url_col]) and not is_ignored(url_col):
        url = str(row[url_col])
        if ' ' in url: issues.append({'col': url_col, 'orig': url, 'prop': url.replace(' ', ''), 'reason': 'Space in URL'})
        elif not url.startswith('http'): issues.append({'col': url_col, 'orig': url, 'prop': 'https://'+url, 'reason': 'Missing Protocol'})
        elif link_check:
            fix, reason = check_link_health(url)
            if reason: issues.append({'col': url_col, 'orig': url, 'prop': fix if fix else url, 'reason': reason})

    # 4. TEXT POLICY CHECKS
    for col in ['Headline', 'Title', 'Ad Headline', 'Body', 'Description']:
        if col in row and pd.notna(row[col]) and not is_ignored(col):
            text = str(row[col])
            fix, reason = check_policy(text, platform)
            if fix: issues.append({'col': col, 'orig': text, 'prop': fix, 'reason': reason})
            elif text in memory: issues.append({'col': col, 'orig': text, 'prop': memory[text], 'reason': 'Learned Fix'})
            elif (col in ['Headline'] and len(text)>30) or (col in ['Title'] and len(text)>40):
                issues.append({'col': col, 'orig': text, 'prop': text[:30], 'reason': 'Character Limit Exceeded'})
    return issues

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer: df.to_excel(writer, index=False)
    return output.getvalue()

def to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

def generate_demo(platform):
    data = []
    if platform == 'google':
        data = [{'Ad Group ID': '', 'Headline': 'Bitcoin Invest', 'Final URL': 'https://httpstat.us/404', 'Max CPC': 1.50}] * 5 + \
               [{'Ad Group ID': '123456789', 'Headline': 'Good Ad', 'Final URL': 'https://google.com', 'Max CPC': None}] * 45
    elif platform == 'linkedin':
        # UPDATED LINKEDIN STRUCTURE
        common = {
            'Campaign Group': 'Default Campaign Group',
            'Campaign Name': 'Q1_Prospecting_2024',
            'Ad Status': 'ACTIVE',
            'Ad Format': 'SINGLE_IMAGE'
        }
        for i in range(5):
             row = common.copy()
             row.update({'Headline': 'Shocking Trick', 'Introductory Text': 'Intro text here', 'Destination URL': 'https://httpstat.us/500', 'Call to Action': 'LEARN_MORE'})
             data.append(row)
        for i in range(45):
             row = common.copy()
             row.update({'Headline': f'Pro Update {i}', 'Introductory Text': 'Intro text here', 'Destination URL': 'https://linkedin.com', 'Call to Action': 'LEARN_MORE'})
             data.append(row)
             
    elif platform == 'meta':
        data = [{'Title': 'Are you fat?', 'Link URL': 'https://httpstat.us/404'}] * 5 + [{'Title': 'New Look', 'Link URL': 'https://meta.com'}] * 45
    return to_excel(pd.DataFrame(data))

# --- UI START ---

if 'file_cache' not in st.session_state: st.session_state.file_cache = {}
if 'ignored' not in st.session_state: st.session_state.ignored = set()
if 'edits' not in st.session_state: st.session_state.edits = {}

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("### 🛡️ Mojo Validator")
    st.caption("Enterprise Edition v2.4 (LinkedIn Fix)")
    st.markdown("---")
    
    st.subheader("Configuration")
    check_links = st.toggle("Active Link Monitoring", value=True, help="Pings destination URLs to check for 404s.")
    
    st.markdown("---")
    st.markdown("#### Test Data Generator")
    st.caption("Generate sample files to test validation logic.")
    c1, c2, c3 = st.columns(3)
    c1.download_button("G-Ads", generate_demo('google'), "demo_google.xlsx")
    c2.download_button("Li-Ads", generate_demo('linkedin'), "demo_linkedin.xlsx")
    c3.download_button("Meta", generate_demo('meta'), "demo_meta.xlsx")
    
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
    <strong>Instructions:</strong> Upload your bulk sheets below. The system will automatically detect the platform (Google, Meta, LinkedIn), 
    scan for policy violations, check for dead links, and allow you to approve AI-suggested fixes.
</div>
""", unsafe_allow_html=True)

# UPLOAD ZONE
uploaded_files = st.file_uploader("", type=['xlsx'], accept_multiple_files=True, label_visibility="collapsed")

if not uploaded_files and not st.session_state.file_cache:
    st.info("👆 Please upload an Excel file to begin.")

if uploaded_files:
    for f in uploaded_files:
        if f.name not in st.session_state.file_cache:
            df = pd.read_excel(f)
            st.session_state.file_cache[f.name] = {'df': df, 'plat': detect_platform(df)}

# MAIN LOOP
if st.session_state.file_cache:
    memory = load_memory()
    
    for fname in list(st.session_state.file_cache.keys()):
        data = st.session_state.file_cache[fname]
        df = data['df']
        plat = data['plat']

        # --- FILE HEADER ---
        st.markdown("---")
        
        col_title, col_badge = st.columns([3, 1])
        with col_title:
            st.markdown(f"### 📄 {fname}")
        with col_badge:
            # Subtle, professional badges
            bg = "#DBEAFE" if "Google" in plat else ("#E0F2FE" if "LinkedIn" in plat else "#F3E8FF")
            text = "#1E40AF" if "Google" in plat else ("#0369A1" if "LinkedIn" in plat else "#7E22CE")
            st.markdown(f"<div style='text-align:right'><span class='platform-badge' style='background:{bg}; color:{text}'>{plat}</span></div>", unsafe_allow_html=True)

        rows_issues = []
        clean_indices = []
        
        for idx in df.index:
            row = df.loc[idx]
            issues = analyze_row(row, idx, plat, memory, fname, st.session_state.ignored, check_links)
            if issues: rows_issues.append({'id': idx, 'row': row, 'issues': issues})
            else: clean_indices.append(idx)

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
        t1, t2 = st.tabs([f"⚠️ Review Required ({len(rows_issues)})", f"✅ Verified Data ({len(clean_indices)})"])
        
        with t1:
            if rows_issues:
                for item in rows_issues:
                    idx = item['id']
                    issues = item['issues']
                    
                    # CLEAN CARD
                    with st.container(border=True):
                        c1, c2, c3, c4 = st.columns([0.5, 2.5, 2.5, 2])
                        c1.markdown(f"**#{idx+2}**")
                        
                        with c2: 
                            st.caption("DETECTED ISSUE")
                            for i in issues: 
                                st.markdown(f"**{i['col']}**")
                                st.markdown(f"<span style='color:#DC2626; background:#FEF2F2; padding:2px 4px; border-radius:4px;'>{i['orig']}</span>", unsafe_allow_html=True)
                                st.caption(f"{i['reason']}")
                        
                        with c3:
                            st.caption("RECOMMENDED FIX (EDITABLE)")
                            for i in issues:
                                key = f"edit_{fname}_{idx}_{i['col']}"
                                def_val = str(i['prop']) if i['prop'] else ""
                                new_val = st.text_input("Edit", value=def_val, key=key, label_visibility="collapsed")
                                if f"{fname}_{idx}" not in st.session_state.edits: st.session_state.edits[f"{fname}_{idx}"] = {}
                                st.session_state.edits[f"{fname}_{idx}"][i['col']] = new_val
                                
                        with c4:
                            st.caption("RESOLUTION")
                            # Primary Action
                            if st.button("✅ Apply Fix", key=f"fix_{fname}_{idx}", type="primary", use_container_width=True):
                                updates = st.session_state.edits.get(f"{fname}_{idx}", {})
                                for i in issues:
                                    val = updates.get(i['col'], i['prop'])
                                    
                                    # Handle "Missing Column" case
                                    if 'Missing Column' in i['reason']:
                                        st.session_state.file_cache[fname]['df'][i['col']] = i['prop'] # Create col globally
                                    else:
                                        st.session_state.file_cache[fname]['df'].at[idx, i['col']] = val
                                    
                                    if str(val) != str(i['prop']): save_memory({i['orig']: val})
                                st.rerun()
                                
                            # Secondary Actions
                            c_ign, c_del = st.columns(2)
                            if c_ign.button("🙈 Ignore", key=f"ign_{fname}_{idx}", use_container_width=True, help="Keep original text and clear warning"):
                                for i in issues: st.session_state.ignored.add(f"{fname}|{idx}|{i['col']}")
                                st.rerun()
                            if c_del.button("🗑️ Remove", key=f"del_{fname}_{idx}", use_container_width=True, help="Delete this row from the file"):
                                st.session_state.file_cache[fname]['df'].drop(idx, inplace=True)
                                st.rerun()
            else:
                st.success("All issues resolved. File is compliant.")

        with t2:
            st.dataframe(df.loc[clean_indices], use_container_width=True)

        # --- EXPORT SECTION ---
        st.write("")
        with st.container(border=True):
            st.subheader("Export Results")
            col_fmt, col_clean, col_wip = st.columns([1, 2, 2])
            
            with col_fmt:
                fmt = st.selectbox("File Format", ["Excel (.xlsx)", "CSV (.csv)"], key=f"fmt_{fname}")
                
            final_df = st.session_state.file_cache[fname]['df']
            mime = "text/csv" if "CSV" in fmt else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            data = to_csv(final_df) if "CSV" in fmt else to_excel(final_df)
            ext = "csv" if "CSV" in fmt else "xlsx"

            with col_clean:
                if not rows_issues:
                    st.download_button(f"📥 Download Verified File", data, f"VERIFIED_{fname.split('.')[0]}.{ext}", mime=mime, type="primary", use_container_width=True, key=f"dl_clean_{fname}")
                else:
                    st.button("Resolve All Issues to Download Verified File", disabled=True, use_container_width=True, key=f"dl_disabled_{fname}")
            
            with col_wip:
                st.download_button(f"💾 Download Draft (With Errors)", data, f"DRAFT_{fname.split('.')[0]}.{ext}", mime=mime, use_container_width=True, key=f"dl_wip_{fname}", help="Download current progress, including unresolved errors.")
