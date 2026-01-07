# Mojo Validator Enterprise 🚀

A bulk-file validation + fixing engine for ad operations. This project provides a headless core engine for validating ad bulk uploads (LinkedIn, Google, Meta) and a Streamlit UI for easy interaction.

## Features

- **Multi-Platform Support**: Built-in rules for LinkedIn Ads, Google Ads, and Meta Ads.
- **Auto-Detection**: Infers the platform based on CSV/Excel headers.
- **Smart Fixes**: Automatically truncates over-length fields and maps incorrect status values.
- **Structured Reports**: Generates detailed error logs with severity levels (BLOCKER/WARNING).
- **UI-Agnostic Core**: The `mojo_validator` package can be used in CLIs, web apps, or batch pipelines.

## Project Structure

- `mojo_validator/`: The core Python package.
- `configs/`: YAML configuration files for platform rules.
- `app.py`: Streamlit dashboard.
- `verify_engine.py`: CLI script for engine verification.

## Setup

1. **Clone the repository**:
   ```bash
   git clone <repo-url>
   cd mojo-validator
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the Dashboard**:
   ```bash
   streamlit run app.py
   ```

## Demo Data

The `samples/` directory contains 50-item demo datasets for each platform:
- `samples/linkedin_demo_50.csv`
- `samples/google_demo_50.csv`
- `samples/meta_demo_50.csv`

Use these files to test the validator and see automatic fixing in action.

## License

MIT
