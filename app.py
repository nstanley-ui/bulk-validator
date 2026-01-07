import streamlit as st
import pandas as pd
import os
from mojo_validator.engine import ValidatorEngine
import io

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
    .stTable {
        background-color: #1e2130;
    }
    </style>
    """, unsafe_allow_value=True)

# Initialize Engine
CONFIG_DIR = os.path.join(os.getcwd(), "configs")
engine = ValidatorEngine(CONFIG_DIR)

# Sidebar
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
    # Save to .tmp for engine to process
    tmp_path = os.path.join(".tmp", uploaded_file.name)
    with open(tmp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    st.info(f"Processing uploaded file for {platform_override}...")
    
    try:
        # Run Validation
        result, verified_df = engine.validate_file(tmp_path, platform_override=override_val)
        
        # Display Stats
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Rows", result.summary.total_rows)
        col2.metric("Clean Rows", result.summary.clean_rows)
        col3.metric("Issues Found", result.summary.total_issues)
        col4.metric("Platform", result.platform)
        
        # Display Results
        tab1, tab2, tab3 = st.tabs(["Issues Report", "Verified Data Preview", "Download Results"])
        
        with tab1:
            if result.issues:
                issue_data = [
                    {
                        "Row": i.row_idx,
                        "Column": i.column,
                        "Severity": i.severity,
                        "Message": i.message,
                        "Original Value": i.original_value,
                        "Suggested Fix": i.suggested_fix
                    } for i in result.issues
                ]
                st.dataframe(pd.DataFrame(issue_data), use_container_width=True)
            else:
                st.success("No issues found! Your file is perfect.")

        with tab2:
            st.dataframe(verified_df.head(100), use_container_width=True)
            st.caption("Previewing first 100 rows of verified/fixed dataset.")

        with tab3:
            # Download Buttons
            towrite = io.BytesIO()
            verified_df.to_csv(towrite, index=False)
            st.download_button(
                label="Download Verified CSV",
                data=towrite.getvalue(),
                file_name=f"verified_{uploaded_file.name}",
                mime="text/csv"
            )
            
            # TODO: Also provide Error Report PDF/CSV download

    except Exception as e:
        st.error(f"Error during validation: {str(e)}")
else:
    st.write("Please upload a file to begin.")
