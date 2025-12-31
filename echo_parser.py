import pdfplumber
import pandas as pd
import re
import os
import glob
from datetime import datetime

# Regex Patterns (Expanded)
PATTERNS = {
    # General
    "MRN": r"MRN\s*[:]\s*([A-Za-z0-9]+)",
    # "Name": r"Name\s*[:]\s*(.*?)Height",  # Commented out for privacy
    "Age": r"Age\s*[:]\s*(\d+)",
    "Study Date": r"Procedure Date\s*[:]\s*(\d{4}-\d{2}-\d{2})",
    
    # Left Ventricle
    "LVEF": r"LVEF\s*(?:is)?\s*[:]?\s*(\d+)%",
    "LVIDD": r"LVIDd\s*[:]?\s*([\d.]+)cm", # Note casing LVIDd
    "LVIDS": r"LVIDs\s*[:]?\s*([\d.]+)cm",
    "LVEDVi": r"LVEDVi\s*[:]?\s*([\d.]+)\s*ml/m",
    "LVESVi": r"LVESVi\s*[:]?\s*([\d.]+)\s*ml/m",
    "IVSd": r"IVSd\s*[:]?\s*([\d.]+)cm",
    "LVPWd": r"LVPWd\s*[:]?\s*([\d.]+)cm",
    
    # Diastolic
    "Diastolic Dysfunction Grade": r"Grade\s*(\d+)\s*diastolic",
    "E Velocity": r"E\s*[:]?\s*(\d+)\s*cm/s",
    "E/A Ratio": r"E/A\s*(?:ratio)?\s*[:]?\s*([\d.]+)",
    "DecT": r"DecT\s*[:]?\s*(\d+)\s*ms",
    "e' Medial": r"e'\s*medial\s*[:]?\s*([\d.]+)\s*cm/s",
    "e' Lateral": r"e'\s*lateral\s*[:]?\s*([\d.]+)\s*cm/s",
    "E/e' Average": r"average\s*E/e'\s*[:]?\s*([\d.]+)",
    "LAVi": r"LAVi\s*[:]?\s*([\d.]+)\s*ml/m",
    
    # Right Ventricle
    "TAPSE": r"TAPSE\s*[:]?\s*([\d.]+)\s*cm",
    "TV S'": r"TV\s*S'\s*[:]?\s*([\d.]+)\s*cm/s",
    "RV PLAX": r"RV\s*PLAX\s*[:]?\s*([\d.]+)\s*cm",
    
    # Atria
    "RAVi": r"RAVi\s*[:]?\s*([\d.]+)\s*ml/m",
    "LAd": r"LAd\s*[:]?\s*([\d.]+)\s*cm",
    
    # Pulmonary / Pressures
    "PASP": r"PASP\s*(?:is)?\s*[:]?\s*.*?\s*(\d+)mmHg",
    "TR Vmax": r"TR\s*Vmax\s*[:]?\s*([\d.]+)\s*m/s",
    
    # Aortic Valve
    "AV Vmax": r"AV\s*Vmax\s*[:]?\s*([\d.]+)\s*m/s",
    "AV Mean PG": r"AV\s*mean\s*PG\s*[:]?\s*([\d.]+)\s*mmHg",
    
    # Mitral Valve
    "MV Mean PG": r"MV\s*mean\s*PG\s*[:]?\s*([\d.]+)\s*mmHg",
    "MV Area": r"MVA\s*[:]?\s*([\d.]+)\s*cm",
    
    # Pulmonary Valve
    "PV Vmax": r"PV\s*Vmax\s*[:]?\s*([\d.]+)\s*m/s",
    
    # Vitals
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
    # if data.get("Name"):
    #     data["Name"] = data["Name"].strip()

    # 2. Extract Valve Regurgitation Severity
    valve_map = {
        "Mitral Regurgitation": r"(Trivial|Mild|Moderate|Severe|Minimal)\s*(?:to\s*(?:Mild|Moderate|Severe))?\s*MR",
        "Aortic Regurgitation": r"(Trivial|Mild|Moderate|Severe|Minimal)\s*(?:to\s*(?:Mild|Moderate|Severe))?\s*AR",
        "Tricuspid Regurgitation": r"(Trivial|Mild|Moderate|Severe|Minimal)\s*(?:to\s*(?:Mild|Moderate|Severe))?\s*TR",
        "Pulmonary Regurgitation": r"(Trivial|Mild|Moderate|Severe|Minimal)\s*(?:to\s*(?:Mild|Moderate|Severe))?\s*PR"
    }

    for field, pattern in valve_map.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            data[field] = match.group(0) # Capture the whole phrase e.g. "Mild MR"
        else:
            data[field] = None

    # 3. Extract Impression
    impression_match = re.search(r"Impression\s*(.*?)(?:\* THIS IS A PRELIMINARY|\* This is computer generated|REPORTED BY)", text, re.DOTALL | re.IGNORECASE)
    if impression_match:
        data["Impression"] = impression_match.group(1).strip()
    else:
        data["Impression"] = None

    return data

def apply_auto_labels(df):
    """
    Applies detailed rule-based classification to the dataset.
    
    Generates:
    - Multi-label binary flags for each disease condition
    - Group status for 7 cardiac systems
    - Overall diagnosis (Normal/Abnormal)
    - Legacy Label/Disease_Type for backward compatibility
    """
    
    # Output columns - Group status
    group_lv = []
    group_diastolic = []
    group_rv = []
    group_atria = []
    group_valves = []
    group_pasp = []
    group_structural = []
    overall_diagnosis = []
    
    # New Categorical Columns (ASE)
    lvef_categories = []
    pasp_severities = []
    
    # NEW: BSE Diastolic Column
    bse_diastolic_statuses = []
    
    # NEW: Heart Disease -2 Columns
    hf_subtypes = []
    lv_geometries = []
    as_severities = []
    ms_severities = []
    ps_severities = []
    
    # Multi-label binary flags (NEW)
    flag_normal = []
    flag_hfref = []
    flag_rwma = []
    flag_dcm = []
    flag_rv_dysfunction = []
    flag_diastolic_dysfunction = []
    flag_lvh = []
    flag_hcm = []
    flag_valvular_disease = []
    flag_elevated_pasp = []
    flag_structural_abnormality = []
    
    # Legacy columns (keeping for backward compatibility)
    labels = [] 
    disease_types = []

    for index, row in df.iterrows():
        impression = str(row.get('Impression', '')).lower() if pd.notna(row.get('Impression')) else ""
        
        # --- Helper for parsing floats ---
        def get_val(col, default=None):
            val = row.get(col)
            if pd.isna(val) or val is None:
                return default
            try:
                # Remove non-numeric chars except dot
                clean_val = re.sub(r"[^\d.]", "", str(val))
                return float(clean_val)
            except ValueError:
                return default

        # --- Parameters ---
        lvef = get_val('LVEF', 55.0)
        lvedvi = get_val('LVEDVi')
        lvidd = get_val('LVIDD') # Need LVIDd for RWT
        ivsd = get_val('IVSd', 0.9)
        lvpwd = get_val('LVPWd', 0.9)
        
        diastolic_grade = get_val('Diastolic Dysfunction Grade', 0.0)
        lavi = get_val('LAVi', 20.0)
        e_e_avg = get_val("E/e' Average")
        e_prime_medial = get_val("e' Medial")
        e_prime_lateral = get_val("e' Lateral")
        tr_vmax = get_val("TR Vmax")
        
        # Valve Params
        av_vmax = get_val("AV Vmax")
        av_mean_pg = get_val("AV Mean PG")
        mv_mean_pg = get_val("MV Mean PG")
        mv_area = get_val("MV Area")
        pv_vmax = get_val("PV Vmax")
        
        tapse = get_val('TAPSE', 2.0)
        tv_s = get_val("TV S'", 15.0)
        
        ravi = get_val('RAVi', 20.0)
        lad = get_val('LAd', 3.0)
        
        pasp = get_val('PASP', 25.0)
        
        # Regurgitation Analysis
        mitral_regurg = str(row.get('Mitral Regurgitation', '')).lower()
        aortic_regurg = str(row.get('Aortic Regurgitation', '')).lower()
        tricuspid_regurg = str(row.get('Tricuspid Regurgitation', '')).lower()
        pulm_regurg = str(row.get('Pulmonary Regurgitation', '')).lower()
        
        def is_significant_regurg(text):
            return any(x in text for x in ['mild', 'moderate', 'severe']) and 'trivial' not in text and 'minimal' not in text
        
        # --- ASE GRADING LOGIC (Defaulting to Male if Gender unspecified) ---
        
        # LVEF Categorization
        # LVEF Categorization & HF Subtype
        lvef_cat = "Normal"
        hf_subtype = "Normal"
        
        if lvef is not None:
             # LVEF Grading
             if lvef < 30: lvef_cat = "Severely Reduced"
             elif lvef < 41: lvef_cat = "Moderately Reduced"
             elif lvef < 52: lvef_cat = "Mildly Reduced"
             
             # HF Subtype
             if lvef <= 40: hf_subtype = "HFrEF"
             elif lvef <= 49: hf_subtype = "HFmrEF"
             else: hf_subtype = "HFpEF" # >= 50
             
        # LV Geometry (RWT)
        # RWT = (2 * LVPWd) / LVIDd
        # Normal 0.6-1.0 cm wall thickness provided in doc (refining >1.2 to >1.0)
        wall_thick_threshold = 1.0 
        has_new_lvh = (ivsd is not None and ivsd > wall_thick_threshold) or (lvpwd is not None and lvpwd > wall_thick_threshold)
        
        lv_geometry = "Normal Geometry"
        if lvpwd is not None and lvidd is not None and lvidd > 0:
            rwt = (2 * lvpwd) / lvidd
            if has_new_lvh:
                if rwt > 0.42: lv_geometry = "Concentric Hypertrophy"
                else: lv_geometry = "Eccentric Hypertrophy"
            else:
                 if rwt > 0.42: lv_geometry = "Concentric Remodeling"
                 else: lv_geometry = "Normal Geometry"
                 
        # Valve Stenosis Grading
        as_severity = "Normal"
        if av_vmax is not None or av_mean_pg is not None:
            # Severe: Vmax >= 4.0 or MeanPG >= 40
            if (av_vmax and av_vmax >= 4.0) or (av_mean_pg and av_mean_pg >= 40): as_severity = "Severe"
            # Moderate: Vmax 3.0-3.9, MeanPG 20-39
            elif (av_vmax and av_vmax >= 3.0) or (av_mean_pg and av_mean_pg >= 20): as_severity = "Moderate"
            # Mild: Vmax 2.0-2.9, MeanPG < 20
            elif (av_vmax and av_vmax >= 2.0): as_severity = "Mild"
            
        ms_severity = "Normal"
        if mv_mean_pg is not None or mv_area is not None:
            # Severe: MeanPG > 10, Area < 1.0 (Using 1.5 logic split for severe)
            if (mv_mean_pg and mv_mean_pg > 10) or (mv_area and mv_area < 1.0): ms_severity = "Severe"
            # Moderate: MeanPG 5-10, Area 1.0-1.5
            elif (mv_mean_pg and mv_mean_pg >= 5) or (mv_area and mv_area < 1.5): ms_severity = "Moderate"
            # Mild: MeanPG < 5, Area > 1.5
            elif (mv_mean_pg): ms_severity = "Mild" # Area > 1.5 is normal-ish
            
        ps_severity = "Normal"
        # PS: Mild (Vmax <3, PG <36), Mod (Vmax 3-4, PG 36-64), Sev (Vmax >4, PG >64).
        # We need PG. Can calc or use.
        pv_pg = None
        if pv_vmax: pv_pg = 4 * (pv_vmax ** 2)
        
        if pv_vmax or pv_pg:
             if (pv_vmax and pv_vmax > 4.0) or (pv_pg and pv_pg > 64): ps_severity = "Severe"
             elif (pv_vmax and pv_vmax >= 3.0) or (pv_pg and pv_pg >= 36): ps_severity = "Moderate"
             # Any flow detected? Usually < 3 is Mild/Normal? 
             # Doc: Mild < 3.0 m/s. But > what? Normal is usually < 1.7?
             # Let's assume if > 2.0 it's noteworthy? Or just leave Normal if < 3.
             # Doc says "Mild < 3.0". Implies anything detected?
             # Let's mimic AS mild > 2.0 for consistency if unspecified lower bound.
             elif (pv_vmax and pv_vmax >= 2.0): ps_severity = "Mild"

             
        # PASP Severity
        pasp_sev = "Normal"
        if pasp is not None:
            if pasp >= 70: pasp_sev = "Severe"
            elif pasp >= 50: pasp_sev = "Moderate"
            elif pasp >= 36: pasp_sev = "Mild"

        # --- BSE Diastolic Logic ---
        bse_positive_count = 0
        bse_evaluated = 0
        
        # 1. Avg E/e' > 14
        if e_e_avg is not None:
            bse_evaluated += 1
            if e_e_avg > 14: bse_positive_count += 1
            
        # 2. Septal e' < 7 OR Lateral e' < 10
        # If both are present, we check the condition properly. If only one, we use that.
        # Logic: if ANY available e' is below threshold? Or strict AND? 
        # Guideline says "Septal e' < 7 or Lateral e' < 10". So finding one low is enough to trigger.
        e_prime_cond = False
        if e_prime_medial is not None and e_prime_medial < 7: e_prime_cond = True
        if e_prime_lateral is not None and e_prime_lateral < 10: e_prime_cond = True
        
        # We only count this as a 'criterion evaluated' if we honestly checked it. 
        # But e' is standard. Let's count it if we had either value.
        if e_prime_medial is not None or e_prime_lateral is not None:
            bse_evaluated += 1
            if e_prime_cond: bse_positive_count += 1
        
        # 3. TR Vmax > 2.8 m/s
        if tr_vmax is not None:
            bse_evaluated += 1
            if tr_vmax > 2.8: bse_positive_count += 1
            
        # 4. LAVi > 34
        if lavi is not None:
            bse_evaluated += 1
            if lavi > 34: bse_positive_count += 1
            
        bse_diastolic_status = "Indeterminate/NotEnoughData"
        # Only classify if we have enough data or strong positive signal
        if bse_positive_count >= 3:
             bse_diastolic_status = "Diastolic Dysfunction"
        elif bse_positive_count <= 1 and bse_evaluated >= 3: 
             # Need to have evaluated at least 3 to confidently say normal? 
             # Guideline: "if < 50% positive -> Normal"
             bse_diastolic_status = "Normal"
        elif bse_positive_count == 2 and bse_evaluated >= 3:
             bse_diastolic_status = "Indeterminate"
        else:
             # Fallback if sparse data, but we can make a best guess or leave empty
             if bse_positive_count == 0 and bse_evaluated > 0: bse_diastolic_status = "Normal (Likely)"
             else: bse_diastolic_status = f"Indeterminate ({bse_positive_count}/{bse_evaluated})"

        # --- MULTI-LABEL DISEASE FLAGS ---
        
        # HFrEF: Reduced ejection fraction (< 52% default)
        has_hfref = lvef < 52
        
        # RWMA: Regional wall motion abnormality
        has_rwma = any(x in impression for x in ['hypokinetic', 'akinetic', 'dyskinetic', 'infarction', 'ischemia', 'rwma'])
        
        # DCM: Dilated cardiomyopathy
        # Using LVEDD > 5.9cm (approx 59mm) as moderate dilation for Male, or Volume criteria if available
        # Simplified: 'dilated' in impression or LVEDVi significant
        has_dcm = ('dilated cardiomyopathy' in impression or 'dcm' in impression or (lvedvi and lvedvi > 75))
        
        # RV Dysfunction
        has_rv_dysfunction = ((tapse and tapse < 1.7) or (tv_s and tv_s < 9.5) or 
                              "rv dysfunction" in impression or "right ventricular dysfunction" in impression)
        
        # Diastolic Dysfunction (any grade)
        has_diastolic_dysfunction = (diastolic_grade >= 1 or "diastolic dysfunction" in impression or 
                                      "impaired relaxation" in impression or (lavi and lavi > 34) or
                                      (e_e_avg and e_e_avg > 14))
        
        # LVH: Left ventricular hypertrophy
        has_lvh = (ivsd is not None and ivsd > wall_thick_threshold) or (lvpwd is not None and lvpwd > wall_thick_threshold)
        
        # HCM: Hypertrophic cardiomyopathy
        has_hcm = ('hypertrophic cardiomyopathy' in impression or 'hcm' in impression or 'hocm' in impression)
        
        # Valvular Disease: Any significant regurgitation (>= Mild) or stenosis
        has_stenosis = (as_severity != "Normal" or ms_severity != "Normal" or ps_severity != "Normal" or "stenosis" in impression)
        has_valvular = (is_significant_regurg(mitral_regurg) or is_significant_regurg(aortic_regurg) or 
                        is_significant_regurg(tricuspid_regurg) or is_significant_regurg(pulm_regurg) or 
                        has_stenosis)
        
        # Elevated PASP
        has_elevated_pasp = pasp >= 36 # Used >= 36 for Mild+
        
        # Structural Abnormality: Effusion, thrombus, mass, shunt
        has_structural = any(x in impression for x in ["effusion", "thrombus", "mass", "asd", "vsd", "shunt"])
        
        # Overall Normal: only if ALL flags are false
        is_normal = not any([has_hfref, has_rwma, has_dcm, has_rv_dysfunction, has_diastolic_dysfunction, 
                             has_lvh, has_hcm, has_valvular, has_elevated_pasp, has_structural])
        
        # Append multi-label flags (1 = present, 0 = absent)
        flag_normal.append(1 if is_normal else 0)
        flag_hfref.append(1 if has_hfref else 0)
        flag_rwma.append(1 if has_rwma else 0)
        flag_dcm.append(1 if has_dcm else 0)
        flag_rv_dysfunction.append(1 if has_rv_dysfunction else 0)
        flag_diastolic_dysfunction.append(1 if has_diastolic_dysfunction else 0)
        flag_lvh.append(1 if has_lvh else 0)
        flag_hcm.append(1 if has_hcm else 0)
        flag_valvular_disease.append(1 if has_valvular else 0)
        flag_elevated_pasp.append(1 if has_elevated_pasp else 0)
        flag_structural_abnormality.append(1 if has_structural else 0)
        
        # --- GROUP STATUS (for human readability) ---
        lv_status = "Normal"
        if has_hfref: lv_status = f"Abnormal ({lvef_cat})"
        elif has_rwma: lv_status = "Abnormal (RWMA)"
        elif has_lvh: lv_status = "Abnormal (LVH)"
        elif has_dcm: lv_status = "Abnormal (Dilated)"
        
        diastolic_status = "Normal"
        if diastolic_grade >= 1: diastolic_status = f"Abnormal (Grade {int(diastolic_grade)})"
        elif has_diastolic_dysfunction: diastolic_status = "Abnormal (Impression)"
        
        rv_status = "Normal"
        if tapse and tapse < 1.7: rv_status = "Abnormal (Reduced TAPSE)"
        elif tv_s and tv_s < 9.5: rv_status = "Abnormal (Reduced S')"
        elif has_rv_dysfunction: rv_status = "Abnormal (Impression)"
        
        atria_status = "Normal"
        if ravi and ravi > 34: atria_status = "Abnormal (Dilated RA)"
        elif "atrial enlargement" in impression or "dilated la" in impression or "dilated ra" in impression: 
            atria_status = "Abnormal (Impression)"
        
        valves_status = "Normal"
        abnormal_valves = []
        if is_significant_regurg(mitral_regurg): abnormal_valves.append("MR")
        if is_significant_regurg(aortic_regurg): abnormal_valves.append("AR")
        if is_significant_regurg(tricuspid_regurg): abnormal_valves.append("TR")
        if is_significant_regurg(pulm_regurg): abnormal_valves.append("PR")
        if "stenosis" in impression: abnormal_valves.append("Stenosis")
        if abnormal_valves:
            valves_status = "Abnormal (" + ", ".join(abnormal_valves) + ")"
            
        pasp_status = "Normal"
        if has_elevated_pasp:
            pasp_status = f"Abnormal ({pasp_sev}, {int(pasp)} mmHg)"
            
        structural_status = "Normal"
        struct_issues = []
        if "effusion" in impression: struct_issues.append("Effusion")
        if "thrombus" in impression: struct_issues.append("Thrombus")
        if "mass" in impression: struct_issues.append("Mass")
        if "asd" in impression or "vsd" in impression or "shunt" in impression: struct_issues.append("Shunt")
        if struct_issues:
            structural_status = "Abnormal (" + ", ".join(struct_issues) + ")"

        # Overall diagnosis
        final_diagnosis = "Normal" if is_normal else "Abnormal"
        
        # Append group status
        group_lv.append(lv_status)
        group_diastolic.append(diastolic_status)
        group_rv.append(rv_status)
        group_atria.append(atria_status)
        group_valves.append(valves_status)
        group_pasp.append(pasp_status)
        group_structural.append(structural_status)
        overall_diagnosis.append(final_diagnosis)
        lvef_categories.append(lvef_cat)
        pasp_severities.append(pasp_sev)
        bse_diastolic_statuses.append(bse_diastolic_status)
        hf_subtypes.append(hf_subtype)
        lv_geometries.append(lv_geometry)
        as_severities.append(as_severity)
        ms_severities.append(ms_severity)
        ps_severities.append(ps_severity)
        
        # --- LEGACY MAPPING (backward compatibility) ---
        curr_label = 0
        curr_type = "Normal"
        
        if not is_normal:
            # Prioritize severity types
            if has_hfref:
                curr_label = 2; curr_type = "HFrEF"
            elif has_rwma:
                curr_label = 2; curr_type = "RWMA"
            elif has_dcm:
                curr_label = 2; curr_type = "DCM"
            elif has_rv_dysfunction:
                curr_label = 2; curr_type = "RV Dysfunction"
            elif has_diastolic_dysfunction:
                curr_label = 2; curr_type = "Diastolic Dysfunction"
            elif has_hcm:
                curr_label = 1; curr_type = "HCM"
            elif has_lvh:
                curr_label = 1; curr_type = "LVH"
            else:
                curr_label = 2; curr_type = "Other Abnormality"
        
        labels.append(curr_label)
        disease_types.append(curr_type)

    # Assign all columns to dataframe
    df['Label'] = labels
    df['Disease_Type'] = disease_types
    
    # Multi-label flags
    df['Flag_Normal'] = flag_normal
    df['Flag_HFrEF'] = flag_hfref
    df['Flag_RWMA'] = flag_rwma
    df['Flag_DCM'] = flag_dcm
    df['Flag_RV_Dysfunction'] = flag_rv_dysfunction
    df['Flag_Diastolic_Dysfunction'] = flag_diastolic_dysfunction
    df['Flag_LVH'] = flag_lvh
    df['Flag_HCM'] = flag_hcm
    df['Flag_Valvular_Disease'] = flag_valvular_disease
    df['Flag_Elevated_PASP'] = flag_elevated_pasp
    df['Flag_Structural_Abnormality'] = flag_structural_abnormality
    
    # Group status
    df['Group_LV_Status'] = group_lv
    df['Group_Diastolic_Status'] = group_diastolic
    df['Group_RV_Status'] = group_rv
    df['Group_Atria_Status'] = group_atria
    df['Group_Valves_Status'] = group_valves
    df['Group_PASP_Status'] = group_pasp
    df['Group_Structural_Status'] = group_structural
    df['Overall_Diagnosis'] = overall_diagnosis
    df['LVEF_Category'] = lvef_categories
    df['PASP_Severity'] = pasp_severities
    df['BSE_Diastolic_Status'] = bse_diastolic_statuses
    df['HF_Subtype'] = hf_subtypes
    df['LV_Geometry'] = lv_geometries
    df['AS_Severity'] = as_severities
    df['MS_Severity'] = ms_severities
    df['PS_Severity'] = ps_severities
    
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
        log("Applying detailed classification logic...")
        df = apply_auto_labels(df)
    
    # Reorder columns for better readability
    base_cols = ["Filename", "MRN", "Age", "Study Date", "Overall_Diagnosis", "Label", "Disease_Type"]  # Name removed for privacy
    
    # Multi-label flags (NEW - for ML training)
    flag_cols = ["Flag_Normal", "Flag_HFrEF", "Flag_RWMA", "Flag_DCM", "Flag_RV_Dysfunction", 
                 "Flag_Diastolic_Dysfunction", "Flag_LVH", "Flag_HCM", "Flag_Valvular_Disease", 
                 "Flag_Elevated_PASP", "Flag_Structural_Abnormality"]
    
    group_cols = ["Group_LV_Status", "Group_Diastolic_Status", "Group_RV_Status", "Group_Atria_Status", "Group_Valves_Status", "Group_PASP_Status", "Group_Structural_Status", 
                  "BSE_Diastolic_Status", "HF_Subtype", "LV_Geometry", "AS_Severity", "MS_Severity", "PS_Severity"]
    param_cols = ["LVEF", "LVEF_Category", "LVEDVi", "IVSd", "PASP", "PASP_Severity", "E/A Ratio", "LAVi", "TAPSE", "Impression"]
    
    # Combine and ensure existence
    final_cols = base_cols + flag_cols + group_cols + param_cols + ["Error"]
    
    # Filter only columns that actually exist (handling potential dynamic missingness)
    final_cols = [c for c in final_cols if c in df.columns]
    
    # Add any remaining regex extracted columns at the end if not already included
    existing_cols = list(df.columns)
    for c in existing_cols:
        if c not in final_cols:
            final_cols.append(c)
            
    df = df[final_cols]

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
