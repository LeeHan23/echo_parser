import pdfplumber
import pandas as pd
import re
import os
import glob
from datetime import datetime

# Regex Patterns
PATTERNS = {
    "MRN": r"MRN\s*[:]\s*([A-Za-z0-9]+)",
    "Name": r"Name\s*[:]\s*(.*?)Height",  # Adjusted based on layout: Name : ... Height
    "Age": r"Age\s*[:]\s*(\d+)",
    "Study Date": r"Procedure Date\s*[:]\s*(\d{4}-\d{2}-\d{2})",
    "LVEF": r"LVEF\s*is\s*(\d+)%",
    "LVIDD": r"LVIDD:\s*([\d.]+)cm",
    "LVIDS": r"LVIDS:\s*([\d.]+)cm",
    "IVSd": r"IVSd:\s*([\d.]+)cm",
    "LVPWd": r"LVPWd:\s*([\d.]+)cm",
    "PASP": r"PASP\s*is\s*.*?\s*(\d+)mmHg",
    "Diastolic Dysfunction Grade": r"Grade\s*(\d+)\s*diastolic",
    "E/A Ratio": r"E/A\s*ratio\s*[:]\s*([\d.]+)",
    "BP Systolic": r"BP\s*Systolic\s*[:]\s*(\d+)",
    "BP Diastolic": r"BP\s*Diastolic\s*[:]\s*(\d+)",
}

# Keyword mappings for severity (Valves)
VALVE_KEYWORDS = ["Mitral", "Aortic", "Tricuspid"]
SEVERITY_LEVELS = ["Mild", "Moderate", "Severe", "Trivial"]

def extract_text_from_pdf(pdf_path):
    """Extracts text from all pages of a PDF."""
    full_text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"
    except Exception as e:
        print(f"Error reading {pdf_path}: {e}")
        return None
    return full_text

def parse_echo_report(pdf_path):
    """Parses a single Echo report PDF and returns a dictionary of extracted data."""
    text = extract_text_from_pdf(pdf_path)
    if not text:
        return {"Filename": os.path.basename(pdf_path), "Error": "Corrupt or unreadable PDF"}

    data = {"Filename": os.path.basename(pdf_path), "Error": None}

    # 1. Extract Regex Fields
    for field, pattern in PATTERNS.items():
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            data[field] = match.group(1).strip()
        else:
            data[field] = None

    # Special handling for Name (cleanup if needed)
    if data["Name"]:
        data["Name"] = data["Name"].strip()

    # 2. Extract Valve Regurgitation Severity
    # Look for sentences like "Mild MR", "Moderate TR", "Severe AR"
    # Or "Mild to moderate TR"
    # Mapping: MR -> Mitral, AR -> Aortic, TR -> Tricuspid
    # Also look for full names: "Mitral valve... Mild MR"
    
    # Simple approach: search for "Severity KEYWORD" or "KEYWORD Severity" patterns
    # But reports say: "Minimal MR", "Trivial AR", "Mild to moderate TR"
    # Let's try to capture these specific phrases.
    
    valve_map = {
        "Mitral Regurgitation": r"(Trivial|Mild|Moderate|Severe|Minimal)\s*(?:to\s*(?:Mild|Moderate|Severe))?\s*MR",
        "Aortic Regurgitation": r"(Trivial|Mild|Moderate|Severe|Minimal)\s*(?:to\s*(?:Mild|Moderate|Severe))?\s*AR",
        "Tricuspid Regurgitation": r"(Trivial|Mild|Moderate|Severe|Minimal)\s*(?:to\s*(?:Mild|Moderate|Severe))?\s*TR"
    }

    for field, pattern in valve_map.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            data[field] = match.group(0) # Capture the whole phrase e.g. "Mild MR"
        else:
            data[field] = None

    # 3. Extract Impression
    # Look for "Impression" and capture until end or specific footer
    impression_match = re.search(r"Impression\s*(.*?)(?:\* THIS IS A PRELIMINARY|\* This is computer generated|REPORTED BY)", text, re.DOTALL | re.IGNORECASE)
    if impression_match:
        data["Impression"] = impression_match.group(1).strip()
    else:
        data["Impression"] = None

    return data

def apply_auto_labels(df):
    """
    Auto-labels the dataset based on extracted values and keywords.
    
    Classes:
    0: Normal
    1: Structural / Hypertrophy (LVH, HCM)
    2: Abnormal / Functional (RWMA, DCM, HFrEF, RV Dysfunction, Takotsubo, Diastolic Dysfunction >= Gd 2)
    
    Logic & Priority (Sequential check):
    1. RWMA (Ischemia/Infarct) -> Class 2, Type: "RWMA"
    2. Takotsubo Cardiomyopathy -> Class 2, Type: "Takotsubo Cardiomyopathy"
    3. DCM (Dilated Cardiomyopathy) -> Class 2, Type: "Dilated Cardiomyopathy"
    4. RV Dysfunction -> Class 2, Type: "RV Dysfunction"
    5. HFrEF (Systolic Failure, EF < 50) -> Class 2, Type: "HFrEF"
    6. Diastolic Dysfunction (Grade >= 2) -> Class 2, Type: "Diastolic Dysfunction"
    7. HCM (Hypertrophic Cardiomyopathy) -> Class 1, Type: "HCM"
    8. LVH (Hypertrophy) -> Class 1, Type: "LVH"
    9. Normal -> Class 0, Type: "Normal"
    """
    classes = []
    disease_types = []
    
    for index, row in df.iterrows():
        # Safely get values with defaults
        impression = str(row.get('Impression', '')).lower() if pd.notna(row.get('Impression')) else ""
        
        # Helper to strict float conversion
        def safe_float(val, default):
            try:
                return float(val)
            except (ValueError, TypeError):
                return default

        ivsd = safe_float(row.get('IVSd'), 0.0)
        lvpwd = safe_float(row.get('LVPWd'), 0.0)
        lvef = safe_float(row.get('LVEF'), 55.0) # Default to normal (55) if missing
        diastolic_grade = safe_float(row.get('Diastolic Dysfunction Grade'), 0.0)
        
        # --- MEDICAL LOGIC ---
        
        # 1. RWMA / Ischemia / Infarct (Class 2)
        if 'hypokinetic' in impression or 'akinetic' in impression or 'dyskinetic' in impression or 'infarction' in impression or 'ischemia' in impression:
            classes.append(2)
            disease_types.append("RWMA")
            
        # 2. Takotsubo Cardiomyopathy (Class 2)
        elif 'takotsubo' in impression or 'apical ballooning' in impression or 'broken heart' in impression:
            classes.append(2)
            disease_types.append("Takotsubo Cardiomyopathy")

        # 3. Dilated Cardiomyopathy (Class 2)
        elif 'dilated cardiomyopathy' in impression or 'dcm' in impression:
            classes.append(2)
            disease_types.append("Dilated Cardiomyopathy")
            
        # 4. RV Dysfunction (Class 2)
        elif 'rv dysfunction' in impression or 'right ventricular dysfunction' in impression or 'reduced rv function' in impression or 'impaired rv function' in impression:
             classes.append(2)
             disease_types.append("RV Dysfunction")

        # 5. HFrEF / Systolic Failure (Class 2)
        elif lvef < 50:
            classes.append(2)
            disease_types.append("HFrEF")

        # 6. Significant Diastolic Dysfunction (Grade 2 or 3) (Class 2)
        elif diastolic_grade >= 2:
            classes.append(2)
            disease_types.append("Diastolic Dysfunction")

        # 7. HCM - Hypertrophic Cardiomyopathy (Class 1 - Structural)
        elif 'hypertrophic cardiomyopathy' in impression or 'hcm' in impression or 'hocm' in impression:
            classes.append(1)
            disease_types.append("HCM")

        # 8. LVH - Left Ventricular Hypertrophy (Class 1)
        elif ivsd > 1.1 or lvpwd > 1.1:
            classes.append(1)
            disease_types.append("LVH")
            
        # DEFAULT: Normal (Class 0)
        else:
            classes.append(0)
            disease_types.append("Normal")
            
    df['Label'] = classes
    df['Disease_Type'] = disease_types
    return df

def process_directory(input_dir, output_file, log_callback=None):
    """
    Processes all PDFs in the input directory and saves to the output Excel file.
    Optionally accepts a log_callback function to send status updates.
    """
    def log(message):
        print(message)
        if log_callback:
            log_callback(message)

    pdf_files = glob.glob(os.path.join(input_dir, "*.pdf"))
    if not pdf_files:
        log(f"No PDF files found in {input_dir}")
        return

    results = []
    errors = []

    log(f"Found {len(pdf_files)} PDFs. Starting processing...")

    for i, pdf_file in enumerate(pdf_files):
        log(f"Processing ({i+1}/{len(pdf_files)}): {os.path.basename(pdf_file)}...")
        result = parse_echo_report(pdf_file)
        
        # Check for missing MRN
        if not result.get("MRN") and not result.get("Error"):
             result["Error"] = "Missing MRN"
             errors.append(result["Filename"])
        elif result.get("Error"):
             errors.append(result["Filename"])
        
        results.append(result)

    # Create DataFrame
    df = pd.DataFrame(results)
    
    # --- APPLY AUTO-LABELING ---
    if not df.empty:
        log("Applying auto-labeling logic...")
        df = apply_auto_labels(df)
    
    # Reorder columns for better readability (optional)
    # Added 'Label' and 'Disease_Type' to the list
    cols = ["Filename", "MRN", "Label", "Disease_Type", "Name", "Age", "Study Date", "LVEF", "LVIDD", "LVIDS", "IVSd", "LVPWd", "PASP", "BP Systolic", "BP Diastolic", "Diastolic Dysfunction Grade", "E/A Ratio", "Mitral Regurgitation", "Aortic Regurgitation", "Tricuspid Regurgitation", "Impression", "Error"]
    # Filter cols that exist in df
    cols = [c for c in cols if c in df.columns]
    df = df[cols]

    # Save to Excel
    try:
        df.to_excel(output_file, index=False)
        log(f"Successfully saved results to {output_file}")
    except Exception as e:
        log(f"Error saving Excel file: {e}")

    if errors:
        log(f"\nFiles with errors ({len(errors)}):")
        for err in errors:
            log(f"- {err}")
            
    log("Processing Complete.")

def main():
    input_dir = "reports" 
    output_file = "echo_dataset_annotations.xlsx"
    process_directory(input_dir, output_file)

if __name__ == "__main__":
    main()
