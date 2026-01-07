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

# Page configuration
st.set_page_config(
    page_title="Google Ads Bulk Creative Validator",
    page_icon="🎨",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 1rem;
        background: linear-gradient(90deg, #4285f4, #34a853, #fbbc05, #ea4335);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .stProgress > div > div > div > div {
        background-color: #4285f4;
    }
</style>
""", unsafe_allow_html=True)

# Title
st.markdown('<h1 class="main-header">🎨 Google Ads Bulk Creative Validator</h1>', unsafe_allow_html=True)
st.markdown("### Upload a ZIP with multiple creatives - Get instant validation feedback for all of them!")

# Sidebar for credentials
with st.sidebar:
    st.header("🔐 API Credentials")
    
    use_secrets = st.checkbox("Use Streamlit Secrets", value=True)
    
    if use_secrets:
        try:
            developer_token = st.secrets["google_ads"]["developer_token"]
            client_id = st.secrets["google_ads"]["client_id"]
            client_secret = st.secrets["google_ads"]["client_secret"]
            refresh_token = st.secrets["google_ads"]["refresh_token"]
            st.success("✅ Using secrets from Streamlit Cloud")
        except Exception as e:
            st.error("❌ Secrets not configured. Switch to manual entry.")
            use_secrets = False
    
    if not use_secrets:
        developer_token = st.text_input("Developer Token", type="password")
        client_id = st.text_input("Client ID")
        client_secret = st.text_input("Client Secret", type="password")
        refresh_token = st.text_input("Refresh Token", type="password")
    
    st.markdown("---")
    st.markdown("### 📚 Resources")
    st.markdown("- [Get API Credentials](https://developers.google.com/google-ads/api/docs/first-call/overview)")
    st.markdown("- [GitHub Repo](https://github.com/nstanley-ui/google_ads_api_checker)")


def initialize_client(developer_token, client_id, client_secret, refresh_token, login_customer_id):
    """Initialize Google Ads API client"""
    try:
        credentials = {
            "developer_token": developer_token,
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "login_customer_id": login_customer_id.replace("-", ""),
            "use_proto_plus": True
        }
        client = GoogleAdsClient.load_from_dict(credentials)
        return client, None
    except Exception as e:
        return None, str(e)


def find_or_create_ad_group(client, customer_id, campaign_id, ad_group_name):
    """Find existing ad group or create a new one"""
    ga_service = client.get_service("GoogleAdsService")
    
    query = f"""
        SELECT 
            ad_group.id,
            ad_group.name,
            ad_group.resource_name
        FROM ad_group
        WHERE campaign.id = {campaign_id}
          AND ad_group.name = '{ad_group_name}'
        LIMIT 1
    """
    
    try:
        response = ga_service.search(customer_id=customer_id, query=query)
        
        for row in response:
            return row.ad_group.resource_name, row.ad_group.id, None
        
        # Create new ad group
        ad_group_service = client.get_service("AdGroupService")
        campaign_service = client.get_service("CampaignService")
        
        ad_group_operation = client.get_type("AdGroupOperation")
        ad_group = ad_group_operation.create
        
        ad_group.name = ad_group_name
        ad_group.campaign = campaign_service.campaign_path(customer_id, campaign_id)
        ad_group.status = client.enums.AdGroupStatusEnum.ENABLED
        ad_group.type_ = client.enums.AdGroupTypeEnum.DISPLAY_STANDARD

        
        response = ad_group_service.mutate_ad_groups(
            customer_id=customer_id,
            operations=[ad_group_operation]
        )
        
        ad_group_resource_name = response.results[0].resource_name
        ad_group_id = ad_group_resource_name.split('/')[-1]
        
        return ad_group_resource_name, ad_group_id, None
        
    except GoogleAdsException as ex:
        error_msg = "\n".join([f"- {error.message}" for error in ex.failure.errors])
        return None, None, error_msg


def upload_image_asset(client, customer_id, image_data, image_name):
    """Upload image to Google Ads"""
    asset_service = client.get_service("AssetService")
    
    try:
        asset_operation = client.get_type("AssetOperation")
        asset = asset_operation.create
        asset.type_ = client.enums.AssetTypeEnum.IMAGE
        asset.image_asset.data = image_data
        asset.name = image_name
        
        response = asset_service.mutate_assets(
            customer_id=customer_id,
            operations=[asset_operation]
        )
        
        asset_resource_name = response.results[0].resource_name
        asset_id = asset_resource_name.split('/')[-1]
        
        return asset_resource_name, asset_id, None
        
    except GoogleAdsException as ex:
        error_msg = "\n".join([error.message for error in ex.failure.errors])
        return None, None, error_msg


def create_paused_ad(client, customer_id, ad_group_resource_name, image_asset_resource_name,
                     creative_name, final_url):
    """Create a paused responsive display ad"""
    ad_group_ad_service = client.get_service("AdGroupAdService")
    
    try:
        ad_group_ad_operation = client.get_type("AdGroupAdOperation")
        ad_group_ad = ad_group_ad_operation.create
        ad_group_ad.ad_group = ad_group_resource_name
        ad_group_ad.status = client.enums.AdGroupAdStatusEnum.PAUSED
        
        ad = ad_group_ad.ad
        ad.final_urls.append(final_url)
        
        responsive_display_ad = ad.responsive_display_ad
        
        # Add headlines (using creative name as base)
        for i in range(1, 4):
            ad_text_asset = client.get_type("AdTextAsset")
            ad_text_asset.text = f"{creative_name} - Headline {i}"
            responsive_display_ad.headlines.append(ad_text_asset)
        
        # Add descriptions
        for i in range(1, 3):
            ad_text_asset = client.get_type("AdTextAsset")
            ad_text_asset.text = f"Creative validation test for {creative_name}"
            responsive_display_ad.descriptions.append(ad_text_asset)
        
        responsive_display_ad.business_name = "Test Business"
        
        # Add image
        marketing_image = client.get_type("AdImageAsset")
        marketing_image.asset = image_asset_resource_name
        responsive_display_ad.marketing_images.append(marketing_image)
        
        response = ad_group_ad_service.mutate_ad_group_ads(
            customer_id=customer_id,
            operations=[ad_group_ad_operation]
        )
        
        ad_resource_name = response.results[0].resource_name
        return ad_resource_name, None
        
    except GoogleAdsException as ex:
        error_msg = "\n".join([error.message for error in ex.failure.errors])
        return None, error_msg


def extract_images_from_zip(zip_file):
    """Extract all images from uploaded ZIP file"""
    images = []
    valid_extensions = {'.jpg', '.jpeg', '.png', '.gif'}
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = Path(root) / file
                    if file_path.suffix.lower() in valid_extensions:
                        with open(file_path, 'rb') as f:
                            images.append({
                                'name': file,
                                'data': f.read(),
                                'size': os.path.getsize(file_path)
                            })
    except Exception as e:
        st.error(f"Error extracting ZIP: {str(e)}")
        return []
    
    return images


# Main form
st.markdown("---")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📋 Campaign Details")
    customer_id = st.text_input("Customer ID", value="4368944560", help="Your Google Ads Customer ID (no hyphens)")
    campaign_id = st.text_input("Campaign ID", value="23438621203", help="Campaign where ads will be created")
    ad_group_name = st.text_input("Ad Group Name", value="Creative_Validator_Bin", help="Ad group for validation")
    final_url = st.text_input("Final URL", value="https://www.example.com", help="Landing page URL for all ads")

with col2:
    st.subheader("📦 Upload ZIP File")
    st.info("📁 ZIP should contain: image files (.jpg, .png, .gif)")
    uploaded_zip = st.file_uploader("Upload ZIP with Creatives", type=["zip"])
    
    if uploaded_zip:
        images = extract_images_from_zip(uploaded_zip)
        st.success(f"✅ Found {len(images)} images in ZIP")
        
        # Show preview
        with st.expander("🔍 Preview Images"):
            cols = st.columns(4)
            for idx, img in enumerate(images[:8]):  # Show first 8
                with cols[idx % 4]:
                    st.image(io.BytesIO(img['data']), caption=img['name'], width=150)
            if len(images) > 8:
                st.info(f"+ {len(images) - 8} more images...")

st.markdown("---")

# Validate button
if st.button("🚀 Validate All Creatives", type="primary", use_container_width=True):
    
    # Validation
    errors = []
    
    if not use_secrets and not all([developer_token, client_id, client_secret, refresh_token]):
        errors.append("❌ Please provide all API credentials")
    
    if not uploaded_zip:
        errors.append("❌ Please upload a ZIP file with creatives")
    
    if not customer_id or not campaign_id:
        errors.append("❌ Please provide Customer ID and Campaign ID")
    
    if errors:
        for error in errors:
            st.error(error)
    else:
        # Extract images
        images = extract_images_from_zip(uploaded_zip)
        
        if not images:
            st.error("❌ No valid images found in ZIP file")
            st.stop()
        
        # Progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Results tracking
        results = []
        
        try:
            # Step 1: Initialize client
            status_text.text("🔄 Connecting to Google Ads API...")
            progress_bar.progress(5)
            
            if use_secrets:
                client, error = initialize_client(
                    st.secrets["google_ads"]["developer_token"],
                    st.secrets["google_ads"]["client_id"],
                    st.secrets["google_ads"]["client_secret"],
                    st.secrets["google_ads"]["refresh_token"],
                    customer_id
                )
            else:
                client, error = initialize_client(
                    developer_token, client_id, client_secret, refresh_token, customer_id
                )
            
            if error:
                st.error(f"❌ Authentication failed: {error}")
                st.stop()
            
            progress_bar.progress(10)
            
            # Step 2: Find/Create Ad Group
            status_text.text("🔍 Setting up ad group...")
            clean_customer_id = customer_id.replace("-", "")
            ad_group_resource_name, ad_group_id, error = find_or_create_ad_group(
                client, clean_customer_id, campaign_id, ad_group_name
            )
            
            if error:
                st.error(f"❌ Ad Group error: {error}")
                st.stop()
            
            progress_bar.progress(15)
            
            # Step 3: Process each image
            total_images = len(images)
            
            for idx, image in enumerate(images):
                current_progress = 15 + int((idx / total_images) * 80)
                status_text.text(f"📤 Processing {idx + 1}/{total_images}: {image['name']}")
                progress_bar.progress(current_progress)
                
                result = {
                    'creative_name': image['name'],
                    'file_size': f"{image['size'] / 1024:.1f} KB",
                    'status': '⏳ Processing',
                    'ad_id': '',
                    'error_message': ''
                }
                
                # Upload image
                asset_resource_name, asset_id, upload_error = upload_image_asset(
                    client, clean_customer_id, image['data'], image['name']
                )
                
                if upload_error:
                    result['status'] = '❌ Upload Failed'
                    result['error_message'] = upload_error
                    results.append(result)
                    continue
                
                # Create paused ad
                ad_resource_name, ad_error = create_paused_ad(
                    client, clean_customer_id, ad_group_resource_name, 
                    asset_resource_name, image['name'], final_url
                )
                
                if ad_error:
                    result['status'] = '❌ Ad Creation Failed'
                    result['error_message'] = ad_error
                else:
                    result['status'] = '✅ Uploaded (Paused)'
                    result['ad_id'] = ad_resource_name.split('/')[-1]
                
                results.append(result)
            
            progress_bar.progress(100)
            status_text.text("✅ Processing complete!")
            
            # Show results
            st.balloons()
            
            st.markdown("---")
            st.subheader("📊 Validation Results")
            
            # Create DataFrame
            df = pd.DataFrame(results)
            
            # Summary metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Creatives", len(results))
            with col2:
                success_count = len([r for r in results if '✅' in r['status']])
                st.metric("Successfully Uploaded", success_count)
            with col3:
                failed_count = len([r for r in results if '❌' in r['status']])
                st.metric("Failed", failed_count)
            
            # Results table
            st.dataframe(
                df,
                use_container_width=True,
                column_config={
                    "creative_name": "Creative Name",
                    "file_size": "File Size",
                    "status": "Status",
                    "ad_id": "Ad ID",
                    "error_message": "Error Details"
                }
            )
            
            # Download CSV
            csv = df.to_csv(index=False)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            st.download_button(
                label="📥 Download Results as CSV",
                data=csv,
                file_name=f"creative_validation_{timestamp}.csv",
                mime="text/csv"
            )
            
            # Next steps
            st.markdown("---")
            st.subheader("📋 Next Steps")
            
            campaign_url = f"https://ads.google.com/aw/ads?campaignId={campaign_id}"
            
            st.markdown(f"""
            1. **Go to your campaign**: [{campaign_url}]({campaign_url})
            2. **Click 'Ads'** in the left menu
            3. **Check each ad's Status column**:
               - ✅ **"Eligible"** = Creative PASSED validation
               - ❌ **"Disapproved"** = Creative FAILED (hover for reason)
            4. All ads are **PAUSED** - no money will be spent
            """)
            
            if failed_count > 0:
                st.warning(f"⚠️ {failed_count} creatives failed to upload. Check the error details in the table above.")
            
        except Exception as e:
            st.error(f"❌ Unexpected error: {str(e)}")
            import traceback
            with st.expander("📋 Error Details"):
                st.code(traceback.format_exc())

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666;">
    Made with ❤️ for advertisers | 
    <a href="https://github.com/nstanley-ui/google_ads_api_checker" target="_blank">GitHub</a> | 
    <a href="https://developers.google.com/google-ads/api/docs/start" target="_blank">API Docs</a>
</div>
""", unsafe_allow_html=True)
