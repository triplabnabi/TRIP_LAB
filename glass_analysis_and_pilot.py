import pandas as pd
import requests
import random

# --- Configuration ---
GLASS_DB_PATH = "glass2_full.tsv"
PEPTIDE_LENGTH_THRESHOLD = 50
PILOT_STUDY_SAMPLE_SIZE = 10

# Best practice: Identify our script to APIs
REQUEST_HEADERS = {
    'User-Agent': 'Gemini-Peptide-Analysis-Script/1.2'
}

def analyze_glass_db_completeness(file_path):
    """
    Analyzes the entire GLASS database to report on the completeness
    of the pdb_id column.
    """
    print("--- Task 1: Full GLASS Database Analysis ---")
    try:
        chunk_iter = pd.read_csv(file_path, sep='\t', chunksize=100000, low_memory=False)
        total_rows, missing_pdb_id_count = 0, 0
        for chunk in chunk_iter:
            total_rows += len(chunk)
            missing_pdb_id_count += chunk[chunk['pdb_id'].isna() & chunk['target_uniprot_id'].notna()].shape[0]
        if total_rows > 0:
            missing_percentage = (missing_pdb_id_count / total_rows) * 100
            print(f"Total entries in GLASS database: {total_rows:,}")
            print(f"Entries with a UniProt ID but MISSING a PDB ID: {missing_pdb_id_count:,}")
            print(f"Percentage of entries missable by a PDB-only approach: {missing_percentage:.2f}%")
        else:
            print("Could not process any rows.")
    except FileNotFoundError:
        print(f"Error: The file {file_path} was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

def analyze_pdb_structure_via_api(pdb_id):
    """
    Fetches molecular information for a PDB entry to find peptide chains.
    """
    if not pdb_id or pd.isna(pdb_id):
        return {"status": "error", "message": "Invalid PDB ID"}
    url = f"https://www.ebi.ac.uk/pdbe/api/pdb/entry/molecules/{pdb_id.lower()}"
    try:
        response = requests.get(url, headers=REQUEST_HEADERS)
        if response.status_code != 200:
            return {"status": "error", "message": f"PDBe API error ({response.status_code})"}
        entry_data = response.json().get(pdb_id.lower(), [])
        if not entry_data:
            return {"status": "error", "message": "No molecular data in API response."}
        
        peptides, receptors = [], []
        for mol in entry_data:
            if mol.get('molecule_type') == 'polypeptide':
                for chain in mol.get('in_chains', []):
                    info = f"{chain} ({mol.get('length', 0)} aa)"
                    (peptides if mol.get('length', 0) <= PEPTIDE_LENGTH_THRESHOLD else receptors).append(info)
        return {"status": "success", "peptides": peptides, "receptors": receptors}
    except requests.RequestException as e:
        return {"status": "error", "message": f"Network error: {e}"}

def get_sifts_summary(uniprot_id):
    """
    Gets summary annotations for a UniProt ID from the PDBe API.
    """
    if not uniprot_id or pd.isna(uniprot_id):
        return {"status": "error", "message": "Invalid UniProt ID"}
    url = f"https://www.ebi.ac.uk/pdbe/api/uniprot/summary/{uniprot_id}"
    try:
        response = requests.get(url, headers=REQUEST_HEADERS)
        if response.status_code != 200:
            return {"status": "error", "message": f"PDBe API error ({response.status_code})"}
        data = response.json().get(uniprot_id, {})
        if not data:
            return {"status": "error", "message": "No data in API response."}
        summary = data[0]['summary']
        return {
            "status": "success",
            "name": summary.get('recommended_name', {}).get('full', 'N/A'),
            "go_terms": [term['name'] for term in summary.get('go', {}).get('biological_process', [])[:2]],
            "pfam": [pfam['name'] for pfam in summary.get('pfam', [])]
        }
    except requests.RequestException as e:
        return {"status": "error", "message": f"Network error: {e}"}

def run_rich_pilot_study(file_path):
    """
    Runs a pilot study on 10 random entries, gathering rich data.
    """
    print("\n--- Task 2: Rich Pilot Study on 10 Random PDB Entries ---")
    try:
        df = pd.read_csv(file_path, sep='\t', low_memory=False)
        pdb_entries = df.dropna(subset=['pdb_id', 'target_uniprot_id'])
        if len(pdb_entries) == 0:
            print("No entries with both PDB and UniProt IDs found.")
            return

        sample_size = min(len(pdb_entries), PILOT_STUDY_SAMPLE_SIZE)
        random_sample = pdb_entries.sample(n=sample_size)
        print(f"Randomly selected {sample_size} entries to analyze...")

        for _, row in random_sample.iterrows():
            pdb_id, uniprot_id = row['pdb_id'], row['target_uniprot_id']
            print(f"\n------------------------------------------------------")
            print(f"ANALYZING PDB: {pdb_id} | UniProt: {uniprot_id}")
            print(f"------------------------------------------------------")

            # 1. Structural Analysis
            structure_res = analyze_pdb_structure_via_api(pdb_id)
            if structure_res['status'] == 'error':
                print(f"[STRUCT] Error: {structure_res['message']}")
                continue
            
            peptides = structure_res['peptides']
            receptors = structure_res['receptors']
            print(f"[STRUCT] Receptor chains found: {', '.join(receptors) if receptors else 'None'}")
            print(f"[STRUCT] Peptide chains (<=PEPTIDE_LENGTH_THRESHOLD aa) found: {', '.join(peptides) if peptides else 'None'}")
            if not peptides or not receptors:
                print("[STRUCT] Conclusion: Does not appear to be a peptide-receptor complex. Skipping.")
                continue
            print("[STRUCT] Conclusion: Likely a peptide-receptor complex.")

            # 2. SIFTS Metadata Analysis
            sifts_res = get_sifts_summary(uniprot_id)
            if sifts_res['status'] == 'error':
                print(f"[SIFTS] Error: {sifts_res['message']}")
            else:
                print(f"[SIFTS]  Protein Name: {sifts_res['name']}")
                if sifts_res['pfam']: print(f"[SIFTS]  Pfam Family: {', '.join(sifts_res['pfam'])}")
                if sifts_res['go_terms']: print(f"[SIFTS]  GO Process: {', '.join(sifts_res['go_terms'])}")

            # 3. GLASS Binding Data
            doi = row.get('doi', 'N/A')
            activity = f"{row.get('standard_type', '')} {row.get('standard_relation', '')} {row.get('standard_value', 'N/A')} {row.get('standard_units', '')}"
            print(f"[GLASS]  Binding Data: {activity.strip()}")
            if isinstance(doi, str) and doi.startswith('10.'):
                print(f"[GLASS]  Source: https://doi.org/{doi}")

    except FileNotFoundError:
        print(f"Error: The file {file_path} was not found.")
    except Exception as e:
        print(f"An error occurred during the pilot study: {e}")

if __name__ == "__main__":
    analyze_glass_db_completeness(GLASS_DB_PATH)
    run_rich_pilot_study(GLASS_DB_PATH)
