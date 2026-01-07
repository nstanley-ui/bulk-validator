import streamlit as st
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
import zipfile
import tempfile
import os
from pathlib import Path
import pandas as pd
from datetime import datetime
import io
import traceback

# --- Page Config ---
st.set_page_config(page_title="Minimal Creative Validator", page_icon="🎨", layout="wide")

# --- CSS ---
st.markdown("""
<style>
    .main-header { font-size: 2.5rem; font-weight: bold; color: #4285f4; margin-bottom: 1rem; }
    .stProgress > div > div > div > div { background-color: #34a853; }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-header">🎨 Minimal Creative Validator</h1>', unsafe_allow_html=True)

# --- Sidebar Credentials ---
with st.sidebar:
    st.header("🔐 API Credentials")
    use_secrets = st.checkbox("Use Streamlit Secrets", value=True)
    
    if use_secrets:
        try:
            secrets = st.secrets["google_ads"]
            developer_token = secrets["developer_token"]
            client_id = secrets["client_id"]
            client_secret = secrets["client_secret"]
            refresh_token = secrets["refresh_token"]
            st.success("✅ Secrets Loaded")
        except:
            st.error("❌ Secrets not found")
    else:
        developer_token = st.text_input("Developer Token", type="password")
        client_id = st.text_input("Client ID")
        client_secret = st.text_input("Client Secret", type="password")
        refresh_token = st.text_input("Refresh Token", type="password")

# --- Functions ---

def initialize_client(dev_token, c_id, c_secret, r_token, login_id):
    try:
        creds = {
            "developer_token": dev_token,
            "client_id": c_id,
            "client_secret": c_secret,
            "refresh_token": r_token,
            "login_customer_id": login_id.replace("-", ""),
            "use_proto_plus": True
        }
        return GoogleAdsClient.load_from_dict(creds), None
    except Exception as e:
        return None, str(e)

def find_or_create_ad_group(client, customer_id, campaign_id, ad_group_name, ad_group_type_enum):
    """
    Minimal logic: Finds existing ad group OR creates one WITHOUT setting bids.
    This prevents conflicts with Target CPA/Smart Campaigns.
    """
    ga_service = client.get_service("GoogleAdsService")
    
    # 1. Try to find existing
    query = f"""
        SELECT ad_group.id, ad_group.resource_name 
        FROM ad_group 
        WHERE campaign.id = {campaign_id} AND ad_group.name = '{ad_group_name}' 
        LIMIT 1
    """
    try:
        response = ga_service.search(customer_id=customer_id, query=query)
        for row in response:
            return row.ad_group.resource_name, None 

        # 2. If not found, Create New (Minimal Settings)
        ad_group_service = client.get_service("AdGroupService")
        campaign_service = client.get_service("CampaignService")
        operation = client.get_type("AdGroupOperation")
        ad_group = operation.create
        
        ad_group.name = ad_group_name
        ad_group.campaign = campaign_service.campaign_path(customer_id, campaign_id)
        ad_group.status = client.enums.AdGroupStatusEnum.ENABLED
        
        # Set Type from Dropdown (Necessary for creation)
        try:
            ad_group.type_ = getattr(client.enums.AdGroupTypeEnum, ad_group_type_enum)
        except:
            ad_group.type_ = client.enums.AdGroupTypeEnum.DISPLAY_STANDARD

        # NOTE: No Bid Setting here! (Safe for Target CPA)

        response = ad_group_service.mutate_ad_groups(customer_id=customer_id, operations=[operation])
        return response.results[0].resource_name, None
        
    except GoogleAdsException as ex:
        return None, "\n".join([e.message for e in ex.failure.errors])

def upload_image(client, customer_id, image_data, image_name):
    asset_service = client.get_service("AssetService")
    try:
        operation = client.get_type("AssetOperation")
        asset = operation.create
        asset.type_ = client.enums.AssetTypeEnum.IMAGE
        asset.image_asset.data = image_data
        asset.name = f"Validation_{image_name}_{datetime.now().strftime('%M%S')}" # Unique name
        
        response = asset_service.mutate_assets(customer_id=customer_id, operations=[operation])
        return response.results[0].resource_name, None
    except GoogleAdsException as ex:
        return None, "\n".join([e.message for e in ex.failure.errors])

def create_paused_ad(client, customer_id, ad_group_rn, asset_rn, final_url):
    """
    Creates a basic Responsive Display Ad to trigger validation.
    Status is PAUSED so it never spends money.
    """
    ad_service = client.get_service("AdGroupAdService")
    try:
        op = client.get_type("AdGroupAdOperation")
        op.create.ad_group = ad_group_rn
        op.create.status = client.enums.AdGroupAdStatusEnum.PAUSED
        
        ad = op.create.ad
        ad.final_urls.append(final_url)
        
        # RDA Essentials
        rda = ad.responsive_display_ad
        rda.business_name = "Validator"
        
        # Minimal Text Assets (Required by Google)
        headline = client.get_type("AdTextAsset")
        headline.text = "Validation Test Ad"
        rda.headlines.append(headline)
        
        desc = client.get_type("AdTextAsset")
        desc.text = "This is a creative validation test."
        rda.descriptions.append(desc)
        
        # Attach the Image
        img_asset = client.get_type("AdImageAsset")
        img_asset.asset = asset_rn
        rda.marketing_images.append(img_asset)
        
        response = ad_service.mutate_ad_group_ads(customer_id=customer_id, operations=[op])
        return response.results[0].resource_name, None
    except GoogleAdsException as ex:
        return None, "\n".join([e.message for e in ex.failure.errors])

def get_images(zip_file):
    images = []
    with tempfile.TemporaryDirectory() as temp:
        with zipfile.ZipFile(zip_file, 'r') as z:
            z.extractall(temp)
        for r, d, f in os.walk(temp):
            for file in f:
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                    with open(Path(r)/file, 'rb') as img:
                        images.append({'name': file, 'data': img.read()})
    return images

# --- UI Layout ---

col1, col2 = st.columns(2)

# Ad Group Types
AD_TYPES = {
    "Display": "DISPLAY_STANDARD",
    "Display Smart": "DISPLAY_SMART_ADS", # Try this if 'Display' fails
    "Video Responsive": "VIDEO_RESPONSIVE"
}

with col1:
    st.subheader("1. Configuration")
    cust_id = st.text_input("Customer ID", value="4368944560")
    camp_id = st.text_input("Campaign ID", value="23438621203")
    ag_name = st.text_input("Ad Group Name", value="Test_Bin", help="Use an existing ad group if possible!")
    ag_type = st.selectbox("Ad Group Type", options=list(AD_TYPES.keys()))
    url = st.text_input("Final URL", value="https://example.com")

with col2:
    st.subheader("2. Upload")
    uploaded_zip = st.file_uploader("Upload ZIP", type="zip")

if st.button("🚀 Run Validation", type="primary"):
    if not uploaded_zip:
        st.error("Please upload a ZIP file.")
        st.stop()
        
    images = get_images(uploaded_zip)
    st.info(f"Processing {len(images)} images...")
    
    # Init Client
    clean_cid = cust_id.replace("-", "")
    client, err = initialize_client(developer_token, client_id, client_secret, refresh_token, clean_cid)
    
    if err:
        st.error(f"Auth Failed: {err}")
        st.stop()
        
    # Get Ad Group
    ag_rn, err = find_or_create_ad_group(client, clean_cid, camp_id, ag_name, AD_TYPES[ag_type])
    if err:
        st.error(f"Ad Group Error: {err}")
        st.stop()
        
    # Process Images
    results = []
    progress = st.progress(0)
    
    for i, img in enumerate(images):
        res = {'Name': img['name'], 'Status': 'Pending', 'Details': ''}
        
        # Upload Asset
        asset_rn, err = upload_image(client, clean_cid, img['data'], img['name'])
        if err:
            res.update({'Status': '❌ Upload Fail', 'Details': err})
        else:
            # Create Test Ad
            ad_rn, err = create_paused_ad(client, clean_cid, ag_rn, asset_rn, url)
            if err:
                 res.update({'Status': '❌ Rejected', 'Details': err})
            else:
                 res.update({'Status': '✅ Valid', 'Details': 'Ad Created (Paused)'})
        
        results.append(res)
        progress.progress((i + 1) / len(images))
        
    st.balloons()
    st.dataframe(pd.DataFrame(results), use_container_width=True)
