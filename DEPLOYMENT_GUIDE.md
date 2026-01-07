# 🚀 Deploy Bulk Creative Validator to Streamlit Cloud

## 🎯 What This Does Differently

This **BULK** version lets you:
- Upload a **ZIP file** with multiple creatives (10, 50, 100+)
- Process them **all at once**
- Get a **summary report** with pass/fail for each
- **Download CSV** with all results

Perfect for agencies and teams validating multiple creatives!

---

## ⚡ Quick Deploy (3 Steps)

### Step 1: Push to GitHub

```bash
cd bulk_creative_validator

git init
git add .
git commit -m "Bulk creative validator for Google Ads"
git remote add origin https://github.com/YOUR_USERNAME/bulk-creative-validator.git
git branch -M main
git push -u origin main
```

### Step 2: Deploy on Streamlit

1. Go to: **https://share.streamlit.io/**
2. Click **"New app"**
3. Fill in:
   - Repository: `YOUR_USERNAME/bulk-creative-validator`
   - Branch: `main`
   - Main file: `streamlit_app.py` ← **IMPORTANT!**
4. Click **"Deploy!"**

### Step 3: Add Secrets

While deploying, click **Settings** → **Secrets**:

```toml
[google_ads]
developer_token = "YOUR_DEVELOPER_TOKEN"
client_id = "YOUR_CLIENT_ID.apps.googleusercontent.com"
client_secret = "YOUR_CLIENT_SECRET"
refresh_token = "YOUR_REFRESH_TOKEN"
```

**Done!** Your bulk validator is live! 🎉

---

## 📦 How to Use

### 1. Prepare Your ZIP

```
my-creatives.zip
├── creative-001.jpg
├── creative-002.png
├── product-banner.jpg
└── more-images/
    └── promo.gif
```

### 2. Upload & Process

1. Open your app URL
2. Enter campaign details
3. Upload ZIP file
4. Click "Validate All Creatives"
5. Wait for processing (shows progress)

### 3. Review Results

You'll see:
- **Summary**: Total, Success, Failed counts
- **Table**: Each creative's status
- **CSV Download**: Export results
- **Link to Google Ads**: Check final status

---

## 🎯 Sample Workflow

### For Agencies:
```
Client sends → 50 banner variations
              ↓
Upload ZIP   → Bulk validator processes all
              ↓
Get report   → 47 passed, 3 failed
              ↓
Fix 3 issues → Re-upload those 3
              ↓
All approved → Launch campaign
```

### Time Saved:
- **Old way**: 50 creatives × 2 min each = 100 minutes
- **Bulk way**: 1 ZIP upload = 5 minutes
- **Savings**: 95 minutes! ⏰

---

## 📊 What the Output Looks Like

```
📊 Validation Results

Total Creatives: 50
Successfully Uploaded: 47  
Failed: 3

| Creative Name      | Size    | Status         | Ad ID | Error        |
|--------------------|---------|----------------|-------|--------------|
| banner-001.jpg     | 245 KB  | ✅ Uploaded    | 12345 | -            |
| banner-002.jpg     | 312 KB  | ✅ Uploaded    | 12346 | -            |
| too-large.jpg      | 6.2 MB  | ❌ Failed      | -     | Size > 5MB   |
| ...                | ...     | ...            | ...   | ...          |

📥 [Download Results as CSV]

📋 Next Steps:
1. Go to campaign: [Link]
2. Check each ad's status
3. Fix any disapproved creatives
```

---

## 🔧 Troubleshooting

### ZIP has no images
**Problem**: "No valid images found in ZIP"  
**Solution**: Ensure images are .jpg, .png, or .gif

### Some creatives fail
**Common reasons**:
- Image > 5MB (compress it)
- Wrong format (.bmp, .tiff not supported)
- Corrupted file
- Policy violation (check error message)

### App times out
**Problem**: Processing 200+ creatives  
**Solution**: 
- Process in batches of 50-100
- Upgrade to Streamlit Cloud paid tier
- Optimize images before uploading

---

## 💡 Pro Tips

1. **Naming Convention**: Use descriptive names
   - ✅ `product-banner-variant-A.jpg`
   - ❌ `img001.jpg`

2. **Batch Sizes**: 
   - Free tier: 50-75 creatives per batch
   - Paid tier: 100-150 creatives per batch

3. **Pre-optimize**: Compress images to < 1MB before zipping

4. **Test First**: Try 5-10 images first to ensure setup works

5. **Save Report**: Download CSV for records/client reports

---

## 🆚 Single vs Bulk Version

| Feature | Single Version | Bulk Version |
|---------|----------------|--------------|
| Upload | One image at a time | ZIP with many images |
| Processing | Individual | Batch |
| Results | Immediate per image | Summary table + CSV |
| Best for | Quick tests | Large campaigns |
| Time (50 images) | ~100 minutes | ~5 minutes |

---

## 📈 Scaling Tips

### For Large Agencies:
- Create separate campaigns for different clients
- Use descriptive ad group names (`Client_Campaign_Validator`)
- Keep CSV reports for audit trail
- Process overnight for very large batches (500+)

### For In-House Teams:
- Run weekly validation batches
- Create naming conventions with team
- Share CSV reports in Slack/Teams
- Set up separate validator campaigns per product line

---

## 🔗 Resources

- [Your App URL]: `https://YOUR_APP.streamlit.app`
- [GitHub Repo]: Link to your repo
- [Google Ads API Docs](https://developers.google.com/google-ads/api/docs/start)
- [Image Specifications](https://support.google.com/google-ads/answer/7031480)

---

## ❓ FAQ

**Q: How many creatives can I process at once?**  
A: Streamlit free tier: 50-75. Paid tier: 100-150. For more, process in batches.

**Q: Do I get charged for these ads?**  
A: No! All ads are created with PAUSED status.

**Q: Can I validate videos?**  
A: Currently only images (JPG, PNG, GIF). Video support coming soon!

**Q: Where are the ads created?**  
A: In the campaign and ad group you specify. They appear as PAUSED ads.

**Q: Can I delete them after validation?**  
A: Yes! Go to Google Ads and delete the ads once you've checked results.

---

**Happy bulk validating! 🎨📦**

Questions? Open an issue on GitHub!
