import streamlit as st
import pandas as pd
import json
import os
from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import PatternFill

# --- CONFIGURATION ---
st.set_page_config(page_title="Smart Excel Validator", page_icon="🧠", layout="wide")

# File path for the "Brain"
MEMORY_FILE = 'validator_memory.json'

# --- 1. THE "BRAIN" (Learning System) ---
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

# --- 2. VALIDATION LOGIC ---
def validate_and_fix(df, memory):
    """
    Applies rules AND checks memory for past overrides.
    """
    fixed_df = df.copy()
    error_log = []

    for index, row in df.iterrows():
        # --- Rule: Headline Length ---
        if 'Headline' in row and pd.notna(row['Headline']):
            original_text = str(row['Headline'])
            
            # CHECK MEMORY FIRST: Have we seen this exact bad text before?
            if original_text in memory:
                fixed_df.at[index, 'Headline'] = memory[original_text] # Use learned fix
            
            # ELSE: Apply Standard Rule
            elif len(original_text) > 30:
                error_log.append((index, 'Headline', 'Too Long'))
                # Default Logic: Truncate
                fixed_df.at[index, 'Headline'] = original_text[:30]

        # --- Rule: URL Fixer ---
        if 'Final URL' in row:
            url = str(row['Final URL'])
            if ' ' in url:
                error_log.append((index, 'Final URL', 'Space in URL'))
                fixed_df.at[index, 'Final URL'] = url.replace(' ', '')
    
    return fixed_df, error_log

# --- 3. DEMO FILE GENERATOR ---
def generate_demo_file():
    data = {
        'Headline': [
            'Perfect Headline', 
            'This Headline Is Way Too Long And Needs To Be Shortened By The AI',  # Error 1
            'Another Way Too Long Headline That Needs Fixing' # Error 2
        ],
        'Final URL': [
            'https://example.com',
            'https://broken url.com', # Error 3
            'https://good-site.com'
        ],
        'Max CPC': [None, 1.50, None] # Error 4 (Manual Bid)
    }
    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

# --- 4. EXCEL DOWNLOADER ---
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Clean_Data')
    return output.getvalue()

# --- APP UI ---
st.title("🧠 Smart Validator that Learns")
st.markdown("This tool **remembers your edits**. If you manually fix a headline today, it will apply that same fix automatically tomorrow.")

# SECTION A: GET THE DEMO FILE
st.info("Don't have a file? Start here.")
st.download_button(
    "📥 Download Broken Demo Excel", 
    generate_demo_file(), 
    "broken_demo.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

st.markdown("---")

# SECTION B: UPLOAD & PROCESS
uploaded_file = st.file_uploader("Upload your Excel file", type=['xlsx'])

if uploaded_file:
    # Load Data & Memory
    df_original = pd.read_excel(uploaded_file)
    memory = load_memory()
    
    st.subheader("1. Analysis")
    
    # Run Validation
    df_fixed_auto, errors = validate_and_fix(df_original, memory)
    
    if not errors:
        st.success("✅ No errors found! Your file is perfect.")
    else:
        st.warning(f"⚠️ Found {len(errors)} issues. Applying Auto-Fixes...")
        
        # Show "Before & After" for the first few errors
        st.write("Preview of Changes:")
        comparison = pd.DataFrame({
            'Original': df_original['Headline'],
            'Auto-Fixed': df_fixed_auto['Headline']
        })
        st.dataframe(comparison.head())

    st.markdown("---")
    st.subheader("2. Review & Teach")
    st.markdown("Review the 'Auto-Fixed' data below. **Edit any cells** that look wrong. The system will learn from your edits.")

    # EDITABLE DATAFRAME
    # This is where the user "Teaches" the system
    df_user_edited = st.data_editor(df_fixed_auto, num_rows="dynamic", use_container_width=True)

    # DETECT LEARNING OPPORTUNITIES
    # Compare "Auto-Fixed" vs "User-Edited"
    new_rules = {}
    
    if st.button("💾 Save Fixes & Train Brain"):
        # Find differences
        for index, row in df_user_edited.iterrows():
            original_val = str(df_original.at[index, 'Headline'])
            auto_val = str(df_fixed_auto.at[index, 'Headline'])
            user_val = str(row['Headline'])
            
            # If User changed the Auto-Fix, learn it!
            if user_val != auto_val:
                new_rules[original_val] = user_val
        
        # Save to Memory
        if new_rules:
            save_memory(new_rules)
            st.success(f"🧠 Learned {len(new_rules)} new corrections! Next time, I will apply these automatically.")
            st.json(new_rules) # Show what was learned
        
        # Download Final
        final_excel = to_excel(df_user_edited)
        st.download_button("📥 Download Final Clean Excel", final_excel, "clean_upload.xlsx")
