import streamlit as st
import pandas as pd
import os
from mojo_validator.engine import ValidatorEngine
import io
import uuid

# Set Page Config
st.set_page_config(
    page_title="Mojo Validator Enterprise",
    page_icon="🚀",
    layout="wide"
)

# Custom CSS for Premium Look
st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
    }
    .stMetric {
        background-color: #1e2130;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #3e4451;
    }
    .issue-card {
        background-color: #1e2130;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #ff4b4b;
        margin-bottom: 10px;
    }
    .success-bar {
        background-color: #d4edda;
        color: #155724;
        padding: 10px;
        border-radius: 5px;
        margin-top: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# Initialize Engine
CONFIG_DIR = os.path.join(os.getcwd(), "configs")
os.makedirs(".tmp", exist_ok=True)
engine = ValidatorEngine(CONFIG_DIR)

# --- Session State Management ---
if 'processed_file' not in st.session_state:
    st.session_state.processed_file = None
    st.session_state.raw_df = None
    st.session_state.verified_df = None
    st.session_state.issues = []
    st.session_state.handled = {} # issue_id -> status
    st.session_state.deleted_rows = set()
    st.session_state.platform = "Unknown"

def reset_state():
    for key in ['raw_df', 'verified_df', 'issues', 'handled', 'deleted_rows', 'platform']:
        if key == 'handled': st.session_state[key] = {}
        elif key == 'deleted_rows': st.session_state[key] = set()
        elif key == 'issues': st.session_state[key] = []
        else: st.session_state[key] = None

# --- Action Handlers ---
def handle_fix(issue):
    # Apply fix to verified_df
    if issue.suggested_fix == "Truncate":
        # Get max_length from config (simplified for demo)
        # In a real app we'd query the engine for the rule
        st.session_state.verified_df.at[issue.row_idx, issue.column] = str(st.session_state.verified_df.at[issue.row_idx, issue.column])[:70]
    elif "Change to one of" in issue.suggested_fix:
         # Simplified: pick the first one from the list in the message
         # Real implementation would use the config mapping
         st.session_state.verified_df.at[issue.row_idx, issue.column] = issue.suggested_fix.split('[')[1].split(',')[0].strip("'")
    
    st.session_state.handled[issue.issue_id] = "fixed"

def handle_ignore(issue):
    st.session_state.handled[issue.issue_id] = "ignored"

def handle_remove_row(row_idx):
    st.session_state.deleted_rows.add(row_idx)
    # Mark all issues for this row as handled
    for issue in st.session_state.issues:
        if issue.row_idx == row_idx:
            st.session_state.handled[issue.issue_id] = "removed"

def handle_override(issue, new_value):
    st.session_state.verified_df.at[issue.row_idx, issue.column] = new_value
    st.session_state.handled[issue.issue_id] = "overridden"

# --- UI Sidebar ---
st.sidebar.title("Configurations")
platform_override = st.sidebar.selectbox(
    "Select Platform Override (Optional)",
    ["Auto-Detect", "LinkedIn Ads", "Google Ads", "Meta Ads"]
)
override_val = None if platform_override == "Auto-Detect" else platform_override

st.title("🚀 Mojo Validator Enterprise")
st.subheader("Bulk-file validation + fixing engine for ad operations")

# File Upload
uploaded_file = st.file_uploader("Upload Ad Bulk File (CSV or XLSX)", type=["csv", "xlsx"])

if uploaded_file:
    if st.session_state.processed_file != uploaded_file.name:
        reset_state()
        tmp_path = os.path.join(".tmp", uploaded_file.name)
        with open(tmp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        result, verified_df = engine.validate_file(tmp_path, platform_override=override_val)
        st.session_state.raw_df = pd.read_csv(tmp_path) if uploaded_file.name.endswith('.csv') else pd.read_excel(tmp_path)
        st.session_state.verified_df = st.session_state.raw_df.copy()
        st.session_state.issues = result.issues
        st.session_state.platform = result.platform
        st.session_state.processed_file = uploaded_file.name
        st.rerun()

    # --- Calculations ---
    # Rows are "OK" if they have no issues OR all issues are handled AND not deleted
    pending_issues = [i for i in st.session_state.issues if i.issue_id not in st.session_state.handled and i.row_idx not in st.session_state.deleted_rows]
    handled_issue_ids = set(st.session_state.handled.keys())
    
    # Logic for metrics
    total_rows = len(st.session_state.raw_df)
    active_rows_count = total_rows - len(st.session_state.deleted_rows)
    
    rows_with_pending = set(i.row_idx for i in pending_issues)
    clean_active_rows = active_rows_count - len(rows_with_pending)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Rows", total_rows)
    col2.metric("Clean Ads", clean_active_rows)
    col3.metric("Issues Remaining", len(pending_issues))
    col4.metric("Platform", st.session_state.platform)

    tab1, tab2, tab3 = st.tabs(["Issues Report", "Verified Data Preview", "Download Results"])

    with tab1:
        if pending_issues:
            st.write(f"### Found {len(pending_issues)} issues in {len(rows_with_pending)} ads")
            
            # Group pending issues by row for cleaner UI
            from collections import defaultdict
            grouped_issues = defaultdict(list)
            for i in pending_issues:
                grouped_issues[i.row_idx].append(i)
            
            for row_idx in sorted(grouped_issues.keys()):
                issues = grouped_issues[row_idx]
                with st.container():
                    st.markdown(f"**Row {row_idx + 1}**") # User wants Row 1-indexed
                    for issue in issues:
                        c1, c2, c3 = st.columns([3, 1, 1])
                        with c1:
                            st.error(f"**{issue.column}**: {issue.message}")
                            st.caption(f"Original: `{issue.original_value}` | Suggested: `{issue.suggested_fix}`")
                        
                        with c2:
                            if st.button(f"Fix", key=f"fix_{issue.issue_id}"):
                                handle_fix(issue)
                                st.rerun()
                            if st.button(f"Ignore", key=f"ignore_{issue.issue_id}"):
                                handle_ignore(issue)
                                st.rerun()
                        
                        with c3:
                            if st.button(f"Remove Row", key=f"rem_{issue.issue_id}"):
                                handle_remove_row(row_idx)
                                st.rerun()
                            
                        # Manual Override
                        override_val = st.text_input("Manual Override", key=f"in_{issue.issue_id}", label_visibility="collapsed", placeholder="Enter manual fix...")
                        if st.button("Apply & Recheck", key=f"btn_in_{issue.issue_id}"):
                            handle_override(issue, override_val)
                            st.rerun()
                    st.divider()
        else:
            st.success("All issues have been addressed!")

        # Expanding Green Bar for OK ads
        ok_count = clean_active_rows
        if ok_count > 0:
            with st.expander(f"✅ {ok_count} ads ok", expanded=False):
                # Filter Df to show only OK rows
                ok_row_indices = [idx for idx in range(total_rows) if idx not in rows_with_pending and idx not in st.session_state.deleted_rows]
                st.dataframe(st.session_state.verified_df.iloc[ok_row_indices], use_container_width=True, hide_index=True)

    with tab2:
        display_df = st.session_state.verified_df.drop(list(st.session_state.deleted_rows))
        st.dataframe(display_df, use_container_width=True, hide_index=True)

    with tab3:
        final_df = st.session_state.verified_df.drop(list(st.session_state.deleted_rows))
        towrite = io.BytesIO()
        final_df.to_csv(towrite, index=False)
        st.download_button(
            label="Download Verified CSV",
            data=towrite.getvalue(),
            file_name=f"verified_{uploaded_file.name}",
            mime="text/csv"
        )
else:
    st.info("Please upload a file to begin.")
