# OCR Output Normalization & Evaluation Utilities

This repository provides robust, reusable utilities to **normalize and evaluate OCR outputs**, streamlining extraction, comparison, and validation tasks for various data formats.

---

## 📦 Setup Instructions

1. **(Optional)** Create and activate a virtual environment for project isolation.
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Install the package in editable mode** (to activate flit and ensure module imports work):
   ```bash
   pip install -e .
   # Alternatively, with flit:
   flit install --symlink
   ```

---

## 🚀 Example key Features

- **Number Normalizer**  
  Extracts and standardizes numeric values from diverse formats. Handles thousands separators, decimal points, currencies (€, $, etc.), and percentages.

- **Date Normalizer**  
  Converts a wide range of date formats—including international month names (e.g., French)—into ISO standard using pattern recognition and locale-aware parsing.

- **File Name Normalizer**  
  Generates canonical file keys for consistent matching, including contract number extraction and normalization of casing/whitespace.

- **Optimal Matching (Hungarian Algorithm)**  
  Performs one-to-one assignment between ground truth and predicted values using Levenshtein distance for fair and accurate evaluation, even when duplicates exist.

- **Flexible JSON Loader**  
  Supports object-based and array-based top-level JSON for seamless data ingestion.

- **Flexible Excel Ground-Truth Loader**  
  Handles both 'long' and 'wide' file formats (see `csv_loader.py` for details). **Note:** Specify the correct field name containing ID values.

---

## 🖥️ Usage Modes

This repository contains two main versions:

### 1. **CLI Application**

- Run interactively via `cli.py`:  
  Select a folder containing JSON OCR outputs and provide an Excel ground truth file. Results are saved in the specified `data` folder.
- Alternate execution:  
  Use the `run_app.bat` script for convenience—create a shortcut to this script to launch the app from anywhere on your computer.

### 2. **API & Web Interface**

- Built with **FastAPI** and **Streamlit** frontend.
- **User authentication:**  
  Each user has a personal config file, which can be viewed and modified when logged in.
- **Tech stack:**  
  Utilizes FastAPI Users library, SQLAlchemy ORM, and SQLite database.  
  > **Scalability:** If user volume grows, migrate from SQLite to a more robust database.
- **Password recovery caveat:**  
  Company security may block email reset links. If you use the 'forgot password' feature, copy the token from console logs to reset your password manually.
- **Security warning:**  
  The authentication and account management systems are functional but **require significant security enhancement**—use with caution.
- Similarly, use the `run_app.bat` script for convenience—create a shortcut to this script to launch the app from anywhere on your computer.

---

## 📝 Additional Notes

- For ground truth file formats, refer to documentation and comments in `csv_loader.py`.
- If you encounter issues or have suggestions, feel free to contact me.

---
