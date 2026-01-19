
import pandas as pd
from echo_parser import apply_auto_labels

def test_lvef_grading():
    print("--- Testing LVEF Grading (Male Defaults) ---")
    data = [
        {'LVEF': 60, 'Impression': ''}, # Normal (>= 52)
        {'LVEF': 52, 'Impression': ''}, # Normal Boundary
        {'LVEF': 48, 'Impression': ''}, # Mild (41-51)
        {'LVEF': 41, 'Impression': ''}, # Mild Boundary
        {'LVEF': 35, 'Impression': ''}, # Moderate (30-40)
        {'LVEF': 25, 'Impression': ''}, # Severe (< 30)
    ]
    df = pd.DataFrame(data)
    df = apply_auto_labels(df)
    
    expected_cats = ['Normal', 'Normal', 'Mildly Reduced', 'Mildly Reduced', 'Moderately Reduced', 'Severely Reduced']
    actual_cats = df['LVEF_Category'].tolist()
    
    for i, (exp, act) in enumerate(zip(expected_cats, actual_cats)):
        status = "PASS" if exp == act else f"FAIL (Expected {exp}, got {act})"
        print(f"Case {i+1} (LVEF={data[i]['LVEF']}): {status}")

def test_pasp_grading():
    print("\n--- Testing PASP Grading ---")
    data = [
        {'PASP': 25, 'Impression': ''}, # Normal (< 36)
        {'PASP': 40, 'Impression': ''}, # Mild (36-49)
        {'PASP': 60, 'Impression': ''}, # Moderate (50-69)
        {'PASP': 75, 'Impression': ''}, # Severe (>= 70)
    ]
    df = pd.DataFrame(data)
    df = apply_auto_labels(df)
    
    expected_cats = ['Normal', 'Mild', 'Moderate', 'Severe']
    actual_cats = df['PASP_Severity'].tolist()
    
    for i, (exp, act) in enumerate(zip(expected_cats, actual_cats)):
        status = "PASS" if exp == act else f"FAIL (Expected {exp}, got {act})"
        print(f"Case {i+1} (PASP={data[i]['PASP']}): {status}")

def test_tapse():
    print("\n--- Testing TAPSE ---")
    data = [
        {'TAPSE': 2.0, 'Impression': ''}, # Normal (>= 1.7)
        {'TAPSE': 1.5, 'Impression': ''}, # Abnormal (< 1.7)
    ]
    df = pd.DataFrame(data)
    df = apply_auto_labels(df)
    
    # Check Flag_RV_Dysfunction or Group_RV_Status
    # Note: Logic for RV might need to be explicitly checked or just rely on flags
    # We'll check the 'Flag_RV_Dysfunction' which maps to this
    
    expected_flags = [0, 1]
    actual_flags = df['Flag_RV_Dysfunction'].tolist()
    
    for i, (exp, act) in enumerate(zip(expected_flags, actual_flags)):
        status = "PASS" if exp == act else f"FAIL (Expected {exp}, got {act})"
        print(f"Case {i+1} (TAPSE={data[i]['TAPSE']}): {status}")

def test_bse_diastolic():
    print("\n--- Testing BSE Diastolic Logic ---")
    # Criteria: Avg E/e' > 14, Septal e' < 7 or Lat e' < 10, TR > 2.8, LAVi > 34
    data = [
        # Case 1: Normal (0 criteria)
        {'E/e\' Average': 10, 'e\' Medial': 9, 'e\' Lateral': 12, 'TR Vmax': 2.5, 'LAVi': 25, 'Impression': ''},
        
        # Case 2: Indeterminate (2 criteria: E/e' > 14, LAVi > 34)
        {'E/e\' Average': 15, 'e\' Medial': 9, 'e\' Lateral': 12, 'TR Vmax': 2.5, 'LAVi': 36, 'Impression': ''},
        
        # Case 3: Dysfunction (3 criteria: E/e', e', TR)
        {'E/e\' Average': 16, 'e\' Medial': 5, 'e\' Lateral': 12, 'TR Vmax': 3.0, 'LAVi': 25, 'Impression': ''},
    ]
    df = pd.DataFrame(data)
    df = apply_auto_labels(df)
    
    # We expect 'Group_Diastolic_Status' to reflect these if we map them there, 
    # OR we can add a specific column for testing.
    # For now let's assume mapping to "BSE Normal", "BSE Indeterminate", "BSE Dysfunction" or similar in new column
    # Checking 'BSE_Diastolic_Status' column which we will verify exists
    
    expected_status = ['Normal', 'Indeterminate', 'Diastolic Dysfunction']
    
    if 'BSE_Diastolic_Status' not in df.columns:
        print("FAIL: 'BSE_Diastolic_Status' column missing")
        return

    actual_status = df['BSE_Diastolic_Status'].tolist()
    
    for i, (exp, act) in enumerate(zip(expected_status, actual_status)):
        status = "PASS" if exp == act else f"FAIL (Expected {exp}, got {act})"
        print(f"Case {i+1}: {status}")

def test_new_heart_disease_logic():
    print("\n--- Testing Heart Disease -2 Logic ---")
    data = [
        # Case 1: HFrEF (EF=35), Conc Hypertrophy (Wall=1.2, RWT>0.42), AS Severe
        {'LVEF': 35, 'IVSd': 1.2, 'LVPWd': 1.2, 'LVIDD': 4.5, 
         'AV Vmax': 4.5, 'AV Mean PG': 45, 'Impression': 'Severe AS'},
         
        # Case 2: HFmrEF (EF=45), Ecc Hypertrophy (Wall=1.2, LVIDd large -> RWT<=0.42)
        # RWT = 2*1.2 / 6.0 = 0.4
        {'LVEF': 45, 'IVSd': 1.2, 'LVPWd': 1.2, 'LVIDD': 6.0, 'Impression': ''},
        
        # Case 3: HFpEF (EF=60), Normal Geometry (Wall=0.9, RWT<=0.42)
        # RWT = 2*0.9 / 4.5 = 0.4
        {'LVEF': 60, 'IVSd': 0.9, 'LVPWd': 0.9, 'LVIDD': 4.5, 'Impression': ''},
    ]
    
    df = pd.DataFrame(data)
    df = apply_auto_labels(df)
    
    # Checks
    print("Checking HF Subtypes...")
    expected_hf = ['HFrEF', 'HFmrEF', 'HFpEF']
    if 'HF_Subtype' in df.columns:
        actual_hf = df['HF_Subtype'].tolist()
        for i, (exp, act) in enumerate(zip(expected_hf, actual_hf)):
            print(f"Case {i+1}: {'PASS' if exp == act else f'FAIL ({exp} vs {act})'}")
    else:
        print("FAIL: HF_Subtype column missing")

    print("Checking LV Geometry...")
    expected_geo = ['Concentric Hypertrophy', 'Eccentric Hypertrophy', 'Normal Geometry']
    if 'LV_Geometry' in df.columns:
        actual_geo = df['LV_Geometry'].tolist()
        for i, (exp, act) in enumerate(zip(expected_geo, actual_geo)):
            print(f"Case {i+1}: {'PASS' if exp == act else f'FAIL ({exp} vs {act})'}")
    else:
        print("FAIL: LV_Geometry column missing")

    print("Checking AS Severity...")
    # Case 1 has Severe AS params
    if 'AS_Severity' in df.columns:
        as_sev = df['AS_Severity'].tolist()[0]
        print(f"Case 1 AS: {'PASS' if as_sev == 'Severe' else f'FAIL (Expected Severe, got {as_sev})'}")
    else:
        print("FAIL: AS_Severity column missing")

def test_gender_logic():
    print("\n--- Testing Gender Logic (Generalized) ---")
    data = [
        # Case 1: Male (Last digit 7 is Odd) - Standard 'doc (7).pdf'
        {'Filename': 'doc (7).pdf', 'LVEF': 53, 'LVEDVi': 70, 'RAVi': 24, 'LAd': 3.9, 'Impression': ''},
        
        # Case 2: Female (Last digit 4 is Even) - 'patient 1234.pdf'
        # Female Normal LVEF >= 54. 53 is Mildly Reduced.
        {'Filename': 'patient 1234.pdf', 'LVEF': 53, 'LVEDVi': 65, 'RAVi': 22, 'LAd': 3.9, 'Impression': ''},
        
        # Case 3: Male (Last digit 1 is Odd) - 'report_2025_001.pdf'
        # Abnormal LVEDVi > 74 (M)
        {'Filename': 'report_2025_001.pdf', 'LVEF': 60, 'LVEDVi': 76, 'RAVi': 30, 'LAd': 4.1, 'Impression': ''},
        
        # Case 4: Female (Last digit 0 is Even) - '100.pdf'
        {'Filename': '100.pdf', 'LVEF': 60, 'LVEDVi': 60, 'RAVi': 20, 'LAd': 3.5, 'Impression': ''},
    ]
    
    df = pd.DataFrame(data)
    df = apply_auto_labels(df)
    
    # Check Gender Inferred
    if 'Gender_Inferred' in df.columns:
        genders = df['Gender_Inferred'].tolist()
        expected_genders = ['Male', 'Female', 'Male', 'Female']
        for i, (exp, act) in enumerate(zip(expected_genders, genders)):
             print(f"Case {i+1} ({data[i]['Filename']}) Gender: {'PASS' if exp == act else f'FAIL (Expected {exp}, got {act})'}")
    else:
        print("FAIL: Gender_Inferred column missing")
        return 
        
    # Check LVEF Category
    # Case 1 M (53%): Normal (>=52)
    # Case 2 F (53%): Mildly Reduced (41-53)
    lvef_cats = df['LVEF_Category'].tolist()
    expected_lvef = ['Normal', 'Mildly Reduced', 'Normal']
    for i, (exp, act) in enumerate(zip(expected_lvef, lvef_cats)):
        print(f"Case {i+1} LVEF Cat: {'PASS' if exp == act else f'FAIL (Expected {exp}, got {act})'}")

    # Check DCM Flag (LVEDVi)
    # Case 1 M (70): Normal (<=74) -> No DCM (unless dilated string)
    # Case 2 F (65): Abnormal (>61) -> DCM Flag
    # Case 3 M (76): Abnormal (>74) -> DCM Flag
    dcm_flags = df['Flag_DCM'].tolist()
    expected_dcm = [0, 1, 1]
    for i, (exp, act) in enumerate(zip(expected_dcm, dcm_flags)):
        print(f"Case {i+1} DCM Flag: {'PASS' if exp == act else f'FAIL (Expected {exp}, got {act})'}")

    # Check Atria (RAVi)
    # Case 1 M (24): Normal (<=25)
    # Case 2 F (22): Abnormal (>21)
    atria_status = df['Group_Atria_Status'].tolist()
    # Expect "Abnormal (Dilated RA)" if RAVi triggers
    print(f"Case 1 Atria: {'PASS' if 'Normal' in atria_status[0] else f'FAIL (Expected Normal, got {atria_status[0]})'}")
    print(f"Case 2 Atria: {'PASS' if 'Dilated RA' in atria_status[1] else f'FAIL (Expected Dilated RA, got {atria_status[1]})'}")

if __name__ == "__main__":
    try:
        test_lvef_grading()
        test_pasp_grading()
        test_tapse()
        test_bse_diastolic()
        test_new_heart_disease_logic()
        test_gender_logic()
    except KeyError as e:
        print(f"CRITICAL FAIL: Column not found - {e}")
    except Exception as e:
        print(f"ERROR: {e}")
