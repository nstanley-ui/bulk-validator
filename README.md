# 🎨 Google Ads Bulk Creative Validator

Upload a ZIP file with multiple creatives and get instant validation feedback for ALL of them at once!

## 🚀 What's New - BULK Processing!

Instead of validating one creative at a time, now you can:
- ✅ Upload a **ZIP file** with 10, 50, 100+ creatives
- ✅ Process them **all at once**
- ✅ Get a **summary report** with validation status for each
- ✅ Download results as **CSV** for your records
- ✅ See which creatives passed/failed Google's policies

## 📦 How to Structure Your ZIP

```
my-creatives.zip
├── creative-001.jpg
├── creative-002.png
├── product-banner.jpg
├── promo-image.png
└── folder/
    ├── more-images.jpg
    └── another-creative.gif
```

**Supported formats**: JPG, PNG, GIF

## 🎯 What You Get

After processing, you'll see:

### 📊 Summary Dashboard
- Total creatives processed
- Successfully uploaded count
- Failed uploads count

### 📋 Detailed Results Table
| Creative Name | File Size | Status | Ad ID | Error Details |
|--------------|-----------|---------|-------|---------------|
| creative-001.jpg | 245.3 KB | ✅ Uploaded | 12345 | - |
| creative-002.png | 512.1 KB | ❌ Failed | - | Image too large |

### 📥 Downloadable CSV Report
Export results for sharing with your team!

## 🚀 Quick Start

### 1. Deploy to Streamlit Cloud

```bash
# Clone or create new repo
git init
git add bulk_creative_validator_app.py requirements.txt
git commit -m "Bulk creative validator"
git remote add origin https://github.com/YOUR_USERNAME/bulk-validator.git
git push -u origin main
```

### 2. Deploy on Streamlit

1. Go to https://share.streamlit.io/
2. Click "New app"
3. Select your repo
4. **Main file**: `bulk_creative_validator_app.py`
5. Deploy!

### 3. Add Secrets

Settings → Secrets:
```toml
[google_ads]
developer_token = "YOUR_TOKEN"
client_id = "YOUR_CLIENT_ID.apps.googleusercontent.com"
client_secret = "YOUR_SECRET"
refresh_token = "YOUR_REFRESH_TOKEN"
```

## 📋 How to Use

1. **Enter Campaign Details**
   - Customer ID
   - Campaign ID  
   - Ad Group Name
   - Final URL (landing page)

2. **Upload ZIP File**
   - Drag & drop your ZIP
   - See preview of images found

3. **Click "Validate All Creatives"**
   - Watch progress bar
   - See real-time status updates

4. **Review Results**
   - Check summary metrics
   - Review detailed table
   - Download CSV report

5. **Check in Google Ads**
   - Open your campaign
   - Find PAUSED ads
   - Check Status column:
     - ✅ "Eligible" = Passed
     - ❌ "Disapproved" = Failed

## 💡 Use Cases

### Agency Workflows
- Validate client creatives before campaign launch
- Bulk test creative variations
- Quality control for design team

### E-commerce
- Test product images en masse
- Validate seasonal campaign creatives
- Check promotional banner compliance

### Marketing Teams
- Pre-approve creative batches
- Test A/B variations
- Campaign preparation

## 🔧 Features

- **Bulk Processing**: Handle 100+ creatives in one go
- **Safety First**: All ads created as PAUSED
- **Detailed Reporting**: CSV export with all results
- **Error Handling**: Clear error messages for failures
- **Image Preview**: See what's in your ZIP before processing
- **Progress Tracking**: Real-time status updates
- **Summary Metrics**: Quick overview of results

## 📊 Sample Output

```
✅ Processing Complete!

Total Creatives: 50
Successfully Uploaded: 47
Failed: 3

Failed Creatives:
- banner-too-large.jpg: Image exceeds 5MB limit
- invalid-format.bmp: Unsupported file format
- broken-link.jpg: File corrupted
```

## 🐛 Troubleshooting

### "No images found in ZIP"
- Ensure images are .jpg, .png, or .gif
- Check images aren't in nested folders (though this is supported)

### "Upload failed" for specific images
- Check file size < 5MB
- Verify image isn't corrupted
- Ensure proper format (JPG/PNG/GIF)

### Processing takes too long
- Reduce ZIP size (process in batches)
- Streamlit Cloud has resource limits
- Consider upgrading to paid tier

## 📈 Best Practices

1. **Batch Size**: Process 50-100 creatives at a time for best performance
2. **File Naming**: Use descriptive names (creative-product-variant.jpg)
3. **File Size**: Optimize images before uploading (< 1MB ideal)
4. **Testing**: Test with small batch first (5-10 images)
5. **Backup**: Keep original ZIP as backup

## 🔗 Resources

- [Google Ads Image Requirements](https://support.google.com/google-ads/answer/7031480)
- [Advertising Policies](https://support.google.com/adspolicy/answer/6008942)
- [API Documentation](https://developers.google.com/google-ads/api/docs/start)

## 📄 License

MIT License

---

Made with ❤️ for agencies and advertisers who need to validate creatives at scale
