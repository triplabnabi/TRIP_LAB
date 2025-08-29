import requests
import json

# --- Final MVP Configuration ---
PDB_ID = "5VAI"
PEPTIDE_LENGTH_THRESHOLD = 50
REQUEST_HEADERS = {
    'User-Agent': 'Gemini-Peptide-Analysis-Script/1.5' # Final version
}

def get_structural_info(pdb_id):
    """Identifies peptide and receptor chains based on length."""
    print(f"[Step 1] Analyzing structure for {pdb_id}...")
    url = f"https://www.ebi.ac.uk/pdbe/api/pdb/entry/molecules/{pdb_id.lower()}"
    try:
        response = requests.get(url, headers=REQUEST_HEADERS)
        response.raise_for_status()
        entry_data = response.json().get(pdb_id.lower(), [])
        if not entry_data: return {"status": "error", "message": "No molecular data in API response."}

        peptides, receptors = [], []
        receptor_chain_id = None
        for mol in entry_data:
            if mol.get('molecule_type', '').startswith('polypeptide'):
                length = mol.get('length', 0)
                chain_id = mol.get('in_chains', [])[0]
                if length > PEPTIDE_LENGTH_THRESHOLD:
                    receptors.append(f"{chain_id} ({length} aa)")
                    if receptor_chain_id is None: receptor_chain_id = chain_id
                else:
                    peptides.append(f"{chain_id} ({length} aa)")
        return {"status": "success", "peptides": peptides, "receptors": receptors, "receptor_chain_id": receptor_chain_id}
    except requests.RequestException as e:
        return {"status": "error", "message": str(e)}

def get_uniprot_id_for_chain(pdb_id, chain_id):
    """Discovers the UniProt ID for a specific chain using the correct SIFTS mapping API."""
    print(f"[Step 2] Discovering UniProt ID for chain {chain_id} in {pdb_id}...")
    # CORRECTED API ENDPOINT
    url = f"https://www.ebi.ac.uk/pdbe/api/mappings/uniprot/{pdb_id.lower()}"
    try:
        response = requests.get(url, headers=REQUEST_HEADERS)
        response.raise_for_status()
        sifts_data = response.json().get(pdb_id.lower(), {}).get("UniProt", {})
        if not sifts_data:
            return {"status": "error", "message": "No UniProt mapping found in SIFTS response."}
        
        for uniprot_id, uniprot_details in sifts_data.items():
            for mapping in uniprot_details.get('mappings', []):
                if mapping.get('chain_id') == chain_id:
                    return {"status": "success", "uniprot_id": uniprot_id}
        return {"status": "error", "message": f"No UniProt mapping found for chain {chain_id}."}
    except requests.RequestException as e:
        return {"status": "error", "message": str(e)}

def get_sifts_summary(uniprot_id):
    """Gets functional enrichment data for a discovered UniProt ID."""
    print(f"[Step 3] Enriching discovered UniProt ID: {uniprot_id}...")
    url = f"https://www.ebi.ac.uk/pdbe/api/uniprot/summary/{uniprot_id}"
    try:
        response = requests.get(url, headers=REQUEST_HEADERS)
        response.raise_for_status()
        summary_data = response.json().get(uniprot_id, [])
        if not summary_data: return {"status": "error", "message": "No summary data in API response."}
        summary = summary_data[0]['summary']
        return {
            "status": "success",
            "name": summary.get('recommended_name', {}).get('full', 'N/A'),
            "go_terms": [term['name'] for term in summary.get('go', {}).get('biological_process', [])[:2]]
        }
    except requests.RequestException as e:
        return {"status": "error", "message": str(e)}

def main():
    print(f"--- Final MVP Report for PDB ID: {PDB_ID} ---")
    
    structure_res = get_structural_info(PDB_ID)
    if structure_res['status'] == 'error':
        print(f"[FAIL] Step 1 failed: {structure_res['message']}")
        return
    print(f"  -> Receptor(s) found: {', '.join(structure_res['receptors'])}")
    print(f"  -> Peptide(s) found: {', '.join(structure_res['peptides'])}")
    
    receptor_chain = structure_res.get('receptor_chain_id')
    if not receptor_chain or not structure_res['peptides']:
        print("\nMVP Conclusion: PDB entry is not a peptide-receptor complex.")
        return

    uniprot_res = get_uniprot_id_for_chain(PDB_ID, receptor_chain)
    if uniprot_res['status'] == 'error':
        print(f"[FAIL] Step 2 failed: {uniprot_res['message']}")
        return
    discovered_uniprot_id = uniprot_res['uniprot_id']
    print(f"[SUCCESS] Step 2 discovered UniProt ID for chain {receptor_chain}: {discovered_uniprot_id}")

    summary_res = get_sifts_summary(discovered_uniprot_id)
    if summary_res['status'] == 'error':
        print(f"[FAIL] Step 3 failed: {summary_res['message']}")
        return
    
    print("\n--- Final Enriched Data ---")
    print(f"  Protein Name: {summary_res['name']}")
    for term in summary_res.get('go_terms', []):
        print(f"  GO Process: {term}")
    print("\nMVP Conclusion: Successfully processed and enriched the entry.")

if __name__ == "__main__":
    main()