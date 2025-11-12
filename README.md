1. (Optional) Create and activate a virtual environment.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Install the package in editable mode to activate flit and make module imports work:
   ```bash
   pip install -e .
   # or with flit:
   flit install --symlink
   ```
----------
config file currently contains number and date matching scales

# Project Description

This repository provides robust, reusable utilities for document data normalization and evaluation. It is designed to streamline extraction, comparison, and validation tasks in document processing pipelines. Key features include:

- **Number Normalizer:** Accurately extracts and standardizes numeric values from diverse formats, handling thousands/decimal separators, currency symbols (€, $, etc.), and percentages.
- **Date Normalizer:** Converts a wide range of date formats—including French month names—into standardized ISO dates using intelligent pattern recognition and locale-aware parsing.
- **File Name Normalizer:** Generates canonical file keys for consistent matching, supporting contract number extraction and normalization of casing and whitespace.
- **Optimal Matching (Hungarian Algorithm):** Implements one-to-one assignment between ground truth and predicted values for fair and accurate evaluation, even with duplicates.
- **Flexible JSON Loader:** Handles both object- and array-based top-level JSON files for seamless data ingestion.

Whether you are building or evaluating document extraction systems, this toolkit delivers reliable normalization, matching, and evaluation components to enhance your workflow.

---