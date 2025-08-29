
import requests
import json
import time

# --- Final MVP Configuration ---
PDB_ID = "5VAI"
PEPTIDE_LENGTH_THRESHOLD = 50
REQUEST_HEADERS = {
    'User-Agent': 'Gemini-Peptide-Analysis-Script/1.6' # Resilient version
}
MAX_RETRIES = 3
BACKOFF_FACTOR = 2 # Initial wait time in seconds

def make_api_request(url):
    """Makes a robust API request with retry logic for server errors."""
    for i in range(MAX_RETRIES):
        try:
            response = requests.get(url, headers=REQUEST_HEADERS, timeout=20)
            # Raise an exception for 4xx (client) or 5xx (server) errors
            response.raise_for_status()
            return {"status": "success", "data": response.json()}
        except requests.exceptions.HTTPError as e:
            # Only retry on server-side errors (5xx)
            if 500 <= e.response.status_code < 600:
                if i < MAX_RETRIES - 1:
                    wait_time = BACKOFF_FACTOR * (2 ** i)
                    print(f"[WARN] Received server error {e.response.status_code}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    return {"status": "error", "message": f"API server error after {MAX_RETRIES} retries: {e}"}
            else:
                # It was a client-side error (e.g., 404 Not Found), don't retry
                return {"status": "error", "message": f"API client error: {e}"}
        except requests.exceptions.RequestException as e:
            # Handle other network errors like timeouts
            if i < MAX_RETRIES - 1:
                wait_time = BACKOFF_FACTOR * (2 ** i)
                print(f"[WARN] Network error: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                return {"status": "error", "message": f"A network error occurred after {MAX_RETRIES} retries: {e}"}
    return {"status": "error", "message": "Exited retry loop unexpectedly."}

def get_structural_info(pdb_id):
    print(f"[Step 1] Analyzing structure for {pdb_id}...")
    url = f"https://www.ebi.ac.uk/pdbe/api/pdb/entry/molecules/{pdb_id.lower()}"
    response = make_api_request(url)
    if response['status'] == 'error': return response
    
    entry_data = response['data'].get(pdb_id.lower(), [])
    peptides, receptors, receptor_chain_id = [], [], None
    for mol in entry_data:
        if mol.get('molecule_type', '').startswith('polypeptide'):
            length, chain_id = mol.get('length', 0), mol.get('in_chains', [])[0]
            (peptides if length <= PEPTIDE_LENGTH_THRESHOLD else receptors).append(f"{chain_id} ({length} aa)")
            if length > PEPTIDE_LENGTH_THRESHOLD and receptor_chain_id is None: receptor_chain_id = chain_id
    return {"status": "success", "peptides": peptides, "receptors": receptors, "receptor_chain_id": receptor_chain_id}

def get_uniprot_id_for_chain(pdb_id, chain_id):
    print(f"[Step 2] Discovering UniProt ID for chain {chain_id} in {pdb_id}...")
    url = f"https://www.ebi.ac.uk/pdbe/api/mappings/uniprot/{pdb_id.lower()}"
    response = make_api_request(url)
    if response['status'] == 'error': return response

    sifts_data = response['data'].get(pdb_id.lower(), {}).get("UniProt", {})
    for uniprot_id, details in sifts_data.items():
        for mapping in details.get('mappings', []):
            if mapping.get('chain_id') == chain_id: return {"status": "success", "uniprot_id": uniprot_id}
    return {"status": "error", "message": f"No UniProt mapping for chain {chain_id}."}

def get_sifts_summary(uniprot_id):
    print(f"[Step 3] Enriching discovered UniProt ID: {uniprot_id}...")
    url = f"https://www.ebi.ac.uk/pdbe/api/uniprot/summary/{uniprot_id}"
    response = make_api_request(url)
    if response['status'] == 'error': return response

    summary_data = response['data'].get(uniprot_id, [])
    summary = summary_data[0]['summary']
    return {
        "status": "success",
        "name": summary.get('recommended_name', {}).get('full', 'N/A'),
        "go_terms": [term['name'] for term in summary.get('go', {}).get('biological_process', [])[:2]]
    }

def main():
    print(f"--- Final MVP Report for PDB ID: {PDB_ID} (Resilient Edition) ---")
    structure_res = get_structural_info(PDB_ID)
    if structure_res.get('status') == 'error':
        print(f"[FAIL] Step 1 failed: {structure_res['message']}")
        return
    print(f"  -> Receptor(s) found: {', '.join(structure_res['receptors'])}")
    print(f"  -> Peptide(s) found: {', '.join(structure_res['peptides'])}")
    
    receptor_chain = structure_res.get('receptor_chain_id')
    if not receptor_chain or not structure_res['peptides']:
        print("\nMVP Conclusion: PDB entry is not a peptide-receptor complex.")
        return

    uniprot_res = get_uniprot_id_for_chain(PDB_ID, receptor_chain)
    if uniprot_res.get('status') == 'error':
        print(f"[FAIL] Step 2 failed: {uniprot_res['message']}")
        return
    discovered_uniprot_id = uniprot_res['uniprot_id']
    print(f"[SUCCESS] Step 2 discovered UniProt ID for chain {receptor_chain}: {discovered_uniprot_id}")

    summary_res = get_sifts_summary(discovered_uniprot_id)
    if summary_res.get('status') == 'error':
        print(f"[FAIL] Step 3 failed: {summary_res['message']}")
        return
    
    print("\n--- Final Enriched Data ---")
    print(f"  Protein Name: {summary_res['name']}")
    for term in summary_res.get('go_terms', []):
        print(f"  GO Process: {term}")
    print("\nMVP Conclusion: Successfully processed and enriched the entry.")

if __name__ == "__main__":
    main()
