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

## Configuration

Platform rules are defined in `configs/*.yaml`. You can add new validators or platforms by creating a new YAML file following the existing schema.

## License

MIT
