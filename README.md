# Echo Report Parser

A Python tool to parse Echocardiogram PDF reports, extract key clinical parameters, and apply automated classification logic based on ASE (American Society of Echocardiography) and BSE guidelines.

## Features
- **PDF Extraction**: Extracts text and structured data from PDF reports.
- **Automated Classification**:
  - **LVEF Grading**: Male/Female specific thresholds.
  - **Diastolic Function**: BSE Algorithm (E/e', e', TR Vmax, LAVi).
  - **Heart Failure Subtypes**: HFrEF, HFmrEF, HFpEF.
  - **Valve Disease**: Graded severity for AS, MS, PS (Mild/Mod/Severe) and Regurgitation.
  - **LV Geometry**: RWT-based classification (Concentric/Eccentric Hypertrophy).
  - **Gender Inference**: Infers gender from filename digits (Odd=Male, Even=Female).
- **GUI**: A simple graphical interface for easy usage.
- **Excel Output**: Generates a detailed annotated Excel dataset.

## Installation

### Prerequisites
- Python 3.9 or higher
- [Git](https://git-scm.com/)

### Steps
1. **Clone the repository**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/echo_parser.git
   cd echo_parser
   ```

2. **Create a Virtual Environment** (Recommended):
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # Mac/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Option 1: Graphical User Interface (GUI)
Run the GUI for a user-friendly experience:
```bash
python gui_app.py
```
1. Click **Browse** to select the folder containing your PDF reports.
2. Click **Start Processing**.
3. Choose where to save the output Excel file.

### Option 2: Command Line (CLI)
Run the script directly:
```bash
python echo_parser.py
```
*Note: You may need to edit the `input_dir` variable in `echo_parser.py` or pass arguments if modified.*

## Output
The script generates an Excel file (`echo_dataset_annotations.xlsx`) with:
- **Parameters**: LVEF, LVIDd, PASP, etc.
- **Classifications**: LVEF_Category, HF_Subtype, BSE_Diastolic_Status, etc.
- **Flags**: Binary flags for ML training (Flag_HFrEF, Flag_LVH, etc.).

## Testing
To verify the logic (ASE/BSE rules, Gender inference):
```bash
python verify_ase_logic.py
```
