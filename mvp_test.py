import requests
import json

# --- MVP Configuration ---
# Hardcoded input for a known GPCR-peptide complex
PDB_ID = "5VAI"
UNIPROT_ID = "P43220"
PEPTIDE_LENGTH_THRESHOLD = 50

# Best practice: Identify our script to APIs
REQUEST_HEADERS = {
    'User-Agent': 'Gemini-Peptide-Analysis-Script/1.3' # Version updated
}

def get_structural_info(pdb_id):
    """Simulates the Structural Agent by calling the PDBe API."""
    print(f"[STRUCT] Querying PDBe API for structure details of {pdb_id}...")
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
            # CORRECTED LOGIC: Check if the molecule_type string starts with 'polypeptide'
            if mol.get('molecule_type', '').startswith('polypeptide'):
                length = mol.get('length', 0)
                chain_ids = mol.get('in_chains', [])
                for chain_id in chain_ids:
                    info = f"{chain_id} ({length} aa)"
                    (peptides if length <= PEPTIDE_LENGTH_THRESHOLD else receptors).append(info)
        
        return {"status": "success", "peptides": peptides, "receptors": receptors}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def get_sifts_summary(uniprot_id):
    """Simulates the Enrichment Agent by calling the PDBe API for SIFTS summary."""
    print(f"[SIFTS] Querying PDBe API for UniProt summary of {uniprot_id}...")
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
            "go_terms": [term['name'] for term in summary.get('go', {}).get('biological_process', [])[:2]]
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

def main():
    """Main function to run the MVP test."""
    print(f"--- MVP Report for PDB ID: {PDB_ID} ---")

    # Step 1: Structural Analysis
    structure_res = get_structural_info(PDB_ID)
    if structure_res['status'] == 'error':
        print(f"[STRUCT] Analysis failed: {structure_res['message']}")
        return

    peptides = structure_res['peptides']
    receptors = structure_res['receptors']
    print(f"[STRUCT] Receptor chains found: {', '.join(receptors) if receptors else 'None'}")
    print(f"[STRUCT] Peptide chains found (<= {PEPTIDE_LENGTH_THRESHOLD} aa): {', '.join(peptides) if peptides else 'None'}")

    if not peptides or not receptors:
        print("\nConclusion: This PDB entry does not appear to be a peptide-receptor complex.")
        return
    else:
        print("\nConclusion: Likely a peptide-receptor complex. Proceeding to enrichment.")

    # Step 2: SIFTS Enrichment
    print("\n--- Enrichment Analysis ---")
    sifts_res = get_sifts_summary(UNIPROT_ID)
    if sifts_res['status'] == 'error':
        print(f"[SIFTS] Enrichment failed: {sifts_res['message']}")
    else:
        print(f"[SIFTS] Protein Name: {sifts_res['name']}")
        if sifts_res['go_terms']:
            for term in sifts_res['go_terms']:
                print(f"[SIFTS] GO Process: {term}")

if __name__ == "__main__":
    main()