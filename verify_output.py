import pandas as pd

output_file = "echo_dataset_annotations.xlsx"

try:
    df = pd.read_excel(output_file)
    print("--- Extracted Data ---")
    print(df.to_string())
    print("\n--- Summary ---")
    print(df.info())
except Exception as e:
    print(f"Error reading {output_file}: {e}")
