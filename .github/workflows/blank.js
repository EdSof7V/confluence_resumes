name: Upload to Confluence from TXT

on:
  push:
    paths:
      - "*.txt"
  workflow_dispatch:

jobs:
  process-txt-to-confluence:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout Repository
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.x'

      - name: Install Dependencies
        run: |
          python -m pip install --upgrade pip
          pip install requests

      - name: Print Environment Variables
        run: |
          echo "=== Environment Variables ==="
          echo "CONFLUENCE_BASE_URL: $CONFLUENCE_BASE_URL"
          echo "CONFLUENCE_USERNAME: $CONFLUENCE_USERNAME"
          echo "CONFLUENCE_API_TOKEN: $CONFLUENCE_API_TOKEN"
          echo "SPACE_KEY: $SPACE_KEY"
          echo "========================"
        env:
          CONFLUENCE_BASE_URL: ${{ secrets.CONFLUENCE_BASE_URL }}
          CONFLUENCE_USERNAME: ${{ secrets.CONFLUENCE_USERNAME }}
          CONFLUENCE_API_TOKEN: ${{ secrets.CONFLUENCE_API_TOKEN }}
          SPACE_KEY: ${{ secrets.SPACE_KEY }}

      - name: Process TXT and Upload to Confluence
        env:
          CONFLUENCE_BASE_URL: ${{ secrets.CONFLUENCE_BASE_URL }}
          CONFLUENCE_API_TOKEN: ${{ secrets.CONFLUENCE_API_TOKEN }}
          CONFLUENCE_USERNAME: ${{ secrets.CONFLUENCE_USERNAME }}
          SPACE_KEY: ${{ secrets.SPACE_KEY }}
        run: |
          python process_txt_to_confluence.py

      - name: Upload Process Log
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: process-log
          path: |
            *.log
            *.txt
          retention-days: 5