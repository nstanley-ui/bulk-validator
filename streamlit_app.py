import streamlit as st
import pandas as pd
import json
import os
from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import PatternFill

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
    
    # Fingerprints based on unique/required columns
    if {'Ad Headline', 'Ad Description', 'Landing Page URL'}.issubset(columns):
        return "LinkedIn Ads"
    elif {'Title', 'Body', 'Link URL'}.issubset(columns):
        return "Meta Ads (Facebook/Instagram)"
    elif {'Headline', 'Description', 'Final URL'}.issubset(columns):
        return "Google Ads"
    else:
        return "Unknown"

# --- 3. VALIDATION LOGIC ---
def validate_and_fix(df, platform, memory):
    fixed_df = df.copy()
    error_log = []

    for index, row in df.iterrows():
        
        # --- COMMON: URL CHECK ---
        # Different platforms use different headers for URL
        url_col = None
        if 'Final URL' in row: url_col = 'Final URL'
        elif 'Landing Page URL' in row: url_col = 'Landing Page URL'
        elif 'Link URL' in row: url_col = 'Link URL'
        
        if url_col and pd.notna(row[url_col]):
            url = str(row[url_col])
            if ' ' in url:
                error_log.append((index, url_col, 'Space in URL'))
                fixed_df.at[index, url_col] = url.replace(' ', '')

        # --- GOOGLE ADS LOGIC ---
        if platform == "Google Ads":
            # Headline: Max 30 chars
            if 'Headline' in row and pd.notna(row['Headline']):
                text = str(row['Headline'])
                if text in memory:
                    fixed_df.at[index, 'Headline'] = memory[text]
                elif len(text) > 30:
                    error_log.append((index, 'Headline', f'Too Long ({len(text)}/30)'))
                    fixed_df.at[index, 'Headline'] = text[:30]

            # Manual Bid Check
            if 'Max CPC' in row and pd.notna(row['Max CPC']):
                 error_log.append((index, 'Max CPC', 'Manual Bid in Auto Campaign'))
                 fixed_df.at[index, 'Max CPC'] = None

        # --- LINKEDIN ADS LOGIC ---
        elif platform == "LinkedIn Ads":
            # Headline: Max 70 chars (Mobile truncation risk)
            if 'Ad Headline' in row and pd.notna(row['Ad Headline']):
                text = str(row['Ad Headline'])
                if text in memory:
                    fixed_df.at[index, 'Ad Headline'] = memory[text]
                elif len(text) > 70:
                    error_log.append((index, 'Ad Headline', f'Truncation Risk ({len(text)}/70)'))
                    fixed_df.at[index, 'Ad Headline'] = text[:70]
            
            # Description: Max 150 chars (Best practice)
            if 'Ad Description' in row and pd.notna(row['Ad Description']):
                text = str(row['Ad Description'])
                if len(text) > 150:
                    error_log.append((index, 'Ad Description', f'Too Long ({len(text)}/150)'))
                    fixed_df.at[index, 'Ad Description'] = text[:150]

        # --- META ADS LOGIC ---
        elif platform == "Meta Ads (Facebook/Instagram)":
            # Title (Headline): Max 40 chars
            if 'Title' in row and pd.notna(row['Title']):
                text = str(row['Title'])
                if text in memory:
                    fixed_df.at[index, 'Title'] = memory[text]
                elif len(text) > 40:
                    error_log.append((index, 'Title', f'Too Long ({len(text)}/40)'))
                    fixed_df.at[index, 'Title'] = text[:40]
            
            # Body (Primary Text): Max 125 chars (before "See More")
            if 'Body' in row and pd.notna(row['Body']):
                text = str(row['Body'])
                if len(text) > 125:
                    error_log.append((index, 'Body', f'Truncation Risk ({len(text)}/125)'))
                    # We don't auto-truncate body text usually, just warn

    return fixed_df, error_log

# --- 4. DEMO GENERATORS ---
def generate_demo(platform):
    output = BytesIO()
    
    if platform == 'google':
        data = {
            'Headline': ['Perfect Length', 'This Google Headline Is Way Too Long And Will Fail', 'Discount'],
            'Description': ['Good description', 'This description is fine', ''],
            'Final URL': ['https://google.com', 'https://broken url.com', 'https://site.com'],
            'Max CPC': [None, 1.50, None]
        }
    elif platform == 'linkedin':
        data = {
            'Campaign Name': ['Q1 Campaign', 'Q1 Campaign', 'Q1 Campaign'],
            'Ad Headline': ['Great B2B Offer', 'This LinkedIn Headline Is Extremely Long And Will Definitely Get Cut Off On Mobile Devices Because It Exceeds 70 Characters', 'Join Us'],
            'Ad Description': ['Short desc', 'This description is acceptable', 'This description is way too long for a LinkedIn Sponsored Content post and users will have to click see more which reduces conversion rates.'],
            'Landing Page URL': ['https://linkedin.com', 'https://broken link.com', 'https://linkedin.com']
        }
    elif platform == 'meta':
        data = {
            'Campaign Name': ['Retargeting', 'Retargeting', 'Retargeting'],
            'Title': ['Free Shipping', 'This Facebook Headline Is Too Long For Feed', 'Shop Now'],
            'Body': ['Great summer vibes', 'This primary text is going to be hidden behind the See More button because it is simply too long for the standard mobile feed placement.', 'Short body'],
            'Link URL': ['https://meta.com', 'https://meta.com', 'https://broken .com']
        }
        
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
st.title("🌎 Universal Ad Validator")
st.markdown("Upload any bulk sheet. I will **auto-detect** if it's Google, LinkedIn, or Meta, and apply the correct rules.")

# --- SECTION 1: DOWNLOAD DEMOS ---
st.subheader("1. Get a Broken Demo File")
col1, col2, col3 = st.columns(3)

with col1:
    st.download_button("📥 Google Ads Demo", generate_demo('google'), "broken_google.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
with col2:
    st.download_button("📥 LinkedIn Ads Demo", generate_demo('linkedin'), "broken_linkedin.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
with col3:
    st.download_button("📥 Meta Ads Demo", generate_demo('meta'), "broken_meta.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

st.markdown("---")

# --- SECTION 2: PROCESS ---
uploaded_file = st.file_uploader("Upload Excel File", type=['xlsx'])

if uploaded_file:
    df_original = pd.read_excel(uploaded_file)
    memory = load_memory()
    
    # 1. Detect
    platform = detect_platform(df_original)
    
    if platform == "Unknown":
        st.error("❌ Could not detect platform. Ensure your headers match standard Google, LinkedIn, or Meta templates.")
        st.stop()
        
    st.success(f"✅ Detected Platform: **{platform}**")
    
    # 2. Validate
    df_fixed, errors = validate_and_fix(df_original, platform, memory)
    
    if not errors:
        st.balloons()
        st.success("✨ Your file is perfect! No errors found.")
    else:
        st.warning(f"⚠️ Found {len(errors)} issues based on {platform} rules.")
        
        # Show Editor
        st.markdown("### Review & Teach")
        st.markdown("Edit the **'Auto-Fixed'** values below. I will learn your preferences.")
        
        # We present the fixed data for user review
        df_user_edited = st.data_editor(df_fixed, num_rows="dynamic", use_container_width=True)
        
        # 3. Learn & Download
        if st.button("💾 Save Fixes & Download"):
            # Learning Logic
            new_rules = {}
            target_col = 'Headline' if platform == 'Google Ads' else ('Ad Headline' if platform == 'LinkedIn Ads' else 'Title')
            
            if target_col in df_user_edited.columns:
                for idx, row in df_user_edited.iterrows():
                    orig_val = str(df_original.at[idx, target_col]) if idx in df_original.index else ""
                    user_val = str(row[target_col])
                    auto_val = str(df_fixed.at[idx, target_col])
                    
                    # If user overrode the auto-fix, learn it
                    if user_val != auto_val and orig_val:
                        new_rules[orig_val] = user_val
            
            if new_rules:
                save_memory(new_rules)
                st.toast(f"🧠 Learned {len(new_rules)} new preferences!")
            
            final_data = to_excel(df_user_edited)
            st.download_button(
                f"📥 Download Clean {platform} File", 
                final_data, 
                f"clean_{platform.replace(' ', '_').lower()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
