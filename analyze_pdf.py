import pdfplumber
import os
import glob

def analyze_pdf(pdf_path):
    print(f"--- Analyzing {pdf_path} ---")
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                print(f"Page {i+1} Text:\n{text}\n")
    except Exception as e:
        print(f"Error reading {pdf_path}: {e}")

# List files in reports directory
print("Files in reports directory:")
files = glob.glob("reports/*.pdf")
print(files)

for f in files:
    analyze_pdf(f)
