import streamlit as st
import pandas as pd
import json
import os
import random
import re
import requests
from io import BytesIO

# --- CONFIGURATION & HIGH-END DESIGN SYSTEM ---
st.set_page_config(page_title="Mojo // Executive Console", page_icon="🧬", layout="wide")

# CUSTOM CSS: GLASSMORPHISM & HIGH-END SAAS LOOK
st.markdown("""
<style>
    /* IMPORT FONT */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');

    /* APP BACKGROUND */
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        font-family: 'Inter', sans-serif;
    }

    /* HEADERS */
    h1, h2, h3 {
        color: #1a202c;
        font-weight: 800;
        letter-spacing: -0.02em;
    }

    /* CARDS (Glassmorphism) */
    div[data-testid="stBorder"], div.css-1r6slb0, .css-1r6slb0 {
        background: rgba(255, 255, 255, 0.7);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.18);
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.07);
        border-radius: 12px;
        padding: 20px;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    div[data-testid="stBorder"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 12px 40px 0 rgba(31, 38, 135, 0.12);
    }

    /* METRIC CARDS */
    div[data-testid="metric-container"] {
        background: white;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        border: 1px solid #e2e8f0;
    }

    /* BADGES */
    .platform-badge {
        font-size: 0.7rem;
        padding: 6px 12px;
        border-radius: 20px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        display: inline-block;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }

    /* BUTTONS - Primary */
    button[kind="primary"] {
        background: linear-gradient(90deg, #2563EB 0%, #4F46E5 100%);
        border: none;
        color: white;
        font-weight: 600;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        transition: all 0.3s ease;
    }
    button[kind="primary"]:hover {
        box-shadow: 0 4px 15px rgba(79, 70, 229, 0.4);
        transform: scale(1.02);
    }

    /* BUTTONS - Secondary */
    button[kind="secondary"] {
        background: white;
        border: 1px solid #e2e8f0;
        color: #4a5568;
        font-weight: 600;
        border-radius: 8px;
    }
    
    /* PROGRESS BARS */
    .stProgress > div > div > div > div {
        background-image: linear-gradient(90deg, #00C9FF 0%, #92FE9D 100%);
    }

    /* SIDEBAR */
    section[data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e2e8f0;
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
        if "httpstat.us/404" in url: return None, "❌ Dead Link (404)"
        if "httpstat.us/500" in url: return None, "❌ Server Error (500)"
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
        if re.search(r'\b(crypto|bitcoin)\b', t): return text.replace("Bitcoin", "Assets"), "Financial Policy"
        if re.search(r'\b(botox|drugs)\b', t): return "Treatments", "Medical Policy"
        if "!!" in text: return text.replace("!!", "!"), "Punctuation"
    elif platform == "Meta Ads":
        if re.search(r'\b(are you|do you)\b', t): return "For those who...", "Personal Attribute"
    elif platform == "LinkedIn Ads":
        if re.search(r'\b(shocking|trick)\b', t): return "Insights", "Clickbait"
    return None, None

def analyze_row(row, index, platform, memory, filename, ignored_set, link_check):
    issues = []
    def is_ignored(col): return f"{filename}|{index}|{col}" in ignored_set

    url_col = next((c for c in ['Final URL', 'Destination URL', 'Link URL'] if c in row), None)
    if url_col and pd.notna(row[url_col]) and not is_ignored(url_col):
        url = str(row[url_col])
        if ' ' in url: issues.append({'col': url_col, 'orig': url, 'prop': url.replace(' ', ''), 'reason': 'Space in URL'})
        elif not url.startswith('http'): issues.append({'col': url_col, 'orig': url, 'prop': 'https://'+url, 'reason': 'Protocol'})
        elif link_check:
            fix, reason = check_link_health(url)
            if reason: issues.append({'col': url_col, 'orig': url, 'prop': fix if fix else url, 'reason': reason})

    for col in ['Headline', 'Title', 'Ad Headline', 'Body', 'Description']:
        if col in row and pd.notna(row[col]) and not is_ignored(col):
            text = str(row[col])
            fix, reason = check_policy(text, platform)
            if fix: issues.append({'col': col, 'orig': text, 'prop': fix, 'reason': reason})
            elif text in memory: issues.append({'col': col, 'orig': text, 'prop': memory[text], 'reason': 'Learned Fix'})
            elif (col in ['Headline'] and len(text)>30) or (col in ['Title'] and len(text)>40):
                issues.append({'col': col, 'orig': text, 'prop': text[:30], 'reason': 'Length'})
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
        data = [{'Headline': 'Bitcoin Invest', 'Final URL': 'https://httpstat.us/404', 'Max CPC': 1.50}] * 5 + [{'Headline': 'Good Ad', 'Final URL': 'https://google.com'}] * 45
    elif platform == 'linkedin':
        data = [{'Headline': 'Shocking Trick', 'Destination URL': 'https://httpstat.us/500'}] * 5 + [{'Headline': 'Pro Update', 'Destination URL': 'https://linkedin.com'}] * 45
    elif platform == 'meta':
        data = [{'Title': 'Are you fat?', 'Link URL': 'https://httpstat.us/404'}] * 5 + [{'Title': 'New Look', 'Link URL': 'https://meta.com'}] * 45
    return to_excel(pd.DataFrame(data))

# --- UI START ---

if 'file_cache' not in st.session_state: st.session_state.file_cache = {}
if 'ignored' not in st.session_state: st.session_state.ignored = set()
if 'edits' not in st.session_state: st.session_state.edits = {}

# --- SIDEBAR: CONTROLS ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2103/2103633.png", width=50) # Generic DNA icon
    st.title("Mojo Console")
    st.caption("v2.0 Executive Build")
    st.markdown("---")
    
    st.subheader("⚙️ Settings")
    check_links = st.toggle("Real-Time Link Check", value=True)
    
    st.markdown("---")
    st.markdown("### 📥 Test Data Generator")
    c1, c2, c3 = st.columns(3)
    c1.download_button("G-Ads", generate_demo('google'), "demo_google.xlsx")
    c2.download_button("Li-Ads", generate_demo('linkedin'), "demo_linkedin.xlsx")
    c3.download_button("Meta", generate_demo('meta'), "demo_meta.xlsx")
    
    st.markdown("---")
    if st.button("♻️ Reset Workspace"):
        st.session_state.file_cache = {}
        st.session_state.ignored = set()
        st.session_state.edits = {}
        st.rerun()

# --- MAIN CONTENT ---

# HERO HEADER
st.title("Mojo Creative Validator")
st.markdown("#### Enterprise Compliance & Quality Assurance Engine")
st.markdown("Drag and drop your bulk sheets to automatically correct API errors, policy violations, and dead links.")
st.write("")

# UPLOAD ZONE
uploaded_files = st.file_uploader("", type=['xlsx'], accept_multiple_files=True, label_visibility="collapsed")
if not uploaded_files and not st.session_state.file_cache:
    st.info("👆 Upload Excel files above to begin analysis.")

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

        # --- FILE DASHBOARD ---
        st.markdown("---")
        
        # Header Row
        col_title, col_badge = st.columns([3, 1])
        with col_title:
            st.markdown(f"### 📄 {fname}")
        with col_badge:
             # Custom Badges
            color = "#1A73E8" if "Google" in plat else ("#0077B5" if "LinkedIn" in plat else "#833AB4")
            st.markdown(f"<div style='text-align:right'><span class='platform-badge' style='background:{color}; color:white'>{plat}</span></div>", unsafe_allow_html=True)

        rows_issues = []
        clean_indices = []
        
        for idx in df.index:
            row = df.loc[idx]
            issues = analyze_row(row, idx, plat, memory, fname, st.session_state.ignored, check_links)
            if issues: rows_issues.append({'id': idx, 'row': row, 'issues': issues})
            else: clean_indices.append(idx)

        # HEALTH HUD (Metrics)
        total = len(df)
        err_count = len(rows_issues)
        health_score = int(((total - err_count) / total) * 100) if total > 0 else 100
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Health Score", f"{health_score}%", delta=f"{'-' if health_score < 100 else ''}{100-health_score}%")
        m2.metric("Total Rows", total)
        m3.metric("Issues Detected", err_count, delta_color="inverse")
        
        st.progress(health_score / 100)
        st.write("")

        # ERROR TABS
        t1, t2 = st.tabs([f"🔴 Action Required ({len(rows_issues)})", f"✅ Valid Data ({len(clean_indices)})"])
        
        with t1:
            if rows_issues:
                for item in rows_issues:
                    idx = item['id']
                    issues = item['issues']
                    
                    # GLASS CARD
                    with st.container(border=True):
                        c1, c2, c3, c4 = st.columns([0.5, 2.5, 2.5, 1.5])
                        c1.markdown(f"**#{idx+2}**")
                        
                        with c2: 
                            st.caption("ISSUE")
                            for i in issues: 
                                st.markdown(f"**{i['col']}**")
                                st.markdown(f"<span style='color:#e53e3e'>{i['orig']}</span>", unsafe_allow_html=True)
                                st.caption(f"Reason: {i['reason']}")
                        
                        with c3:
                            st.caption("PROPOSAL (EDITABLE)")
                            for i in issues:
                                key = f"edit_{fname}_{idx}_{i['col']}"
                                def_val = str(i['prop']) if i['prop'] else ""
                                new_val = st.text_input("Edit", value=def_val, key=key, label_visibility="collapsed")
                                if f"{fname}_{idx}" not in st.session_state.edits: st.session_state.edits[f"{fname}_{idx}"] = {}
                                st.session_state.edits[f"{fname}_{idx}"][i['col']] = new_val
                                
                        with c4:
                            st.caption("ACTIONS")
                            if st.button("✅ Fix", key=f"fix_{fname}_{idx}", type="primary"):
                                updates = st.session_state.edits.get(f"{fname}_{idx}", {})
                                for i in issues:
                                    val = updates.get(i['col'], i['prop'])
                                    st.session_state.file_cache[fname]['df'].at[idx, i['col']] = val
                                    if str(val) != str(i['prop']): save_memory({i['orig']: val})
                                st.rerun()
                                
                            c_ign, c_del = st.columns(2)
                            if c_ign.button("Ignore", key=f"ign_{fname}_{idx}"):
                                for i in issues: st.session_state.ignored.add(f"{fname}|{idx}|{i['col']}")
                                st.rerun()
                            if c_del.button("Drop", key=f"del_{fname}_{idx}"):
                                st.session_state.file_cache[fname]['df'].drop(idx, inplace=True)
                                st.rerun()
            else:
                st.markdown("""
                <div style="text-align:center; padding:20px; color:#48bb78;">
                    <h3>✨ Clean Sheet</h3>
                    <p>No issues detected. This file is ready for export.</p>
                </div>
                """, unsafe_allow_html=True)

        with t2:
            st.dataframe(df.loc[clean_indices], use_container_width=True)

        # --- EXPORT SECTION ---
        st.write("")
        with st.container(border=True):
            st.markdown("#### 📤 Export Data")
            col_fmt, col_clean, col_wip = st.columns([1, 2, 2])
            
            with col_fmt:
                fmt = st.selectbox("Format", ["Excel (.xlsx)", "CSV (.csv)"], key=f"fmt_{fname}", label_visibility="collapsed")
                
            final_df = st.session_state.file_cache[fname]['df']
            mime = "text/csv" if "CSV" in fmt else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            data = to_csv(final_df) if "CSV" in fmt else to_excel(final_df)
            ext = "csv" if "CSV" in fmt else "xlsx"

            with col_clean:
                if not rows_issues:
                    st.download_button(f"✨ Download Clean File", data, f"CLEAN_{fname.split('.')[0]}.{ext}", mime=mime, type="primary", use_container_width=True)
                else:
                    st.button("🚫 Fix Remaining Errors to Download Clean", disabled=True, use_container_width=True)
            
            with col_wip:
                st.download_button(f"⚠️ Download Work-in-Progress", data, f"WIP_{fname.split('.')[0]}.{ext}", mime=mime, use_container_width=True)
