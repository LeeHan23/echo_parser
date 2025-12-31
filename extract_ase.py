
import pdfplumber
import glob
import os

ase_files = glob.glob("ASE*.pdf")
print(f"Found {len(ase_files)} ASE files.")

for f in ase_files:
    print(f"\n--- FILE: {f} ---")
    try:
        with pdfplumber.open(f) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text:
                    print(f"PAGE {i+1}:\n{text[:1000]}...") # Print first 1000 chars per page to avoid spam
                else:
                    print(f"PAGE {i+1}: [No Text]")
    except Exception as e:
        print(f"Error reading {f}: {e}")
