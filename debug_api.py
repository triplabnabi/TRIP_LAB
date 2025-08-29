
import requests
import json

# --- Debugging Configuration ---
PDB_ID = "5VAI"

# Best practice: Identify our script to APIs
REQUEST_HEADERS = {
    'User-Agent': 'Gemini-Peptide-Analysis-Script/1.2'
}

def inspect_api_response(pdb_id):
    """Calls the PDBe API and prints the raw JSON response for inspection."""
    print(f"--- Inspecting PDBe API response for: {pdb_id} ---")
    url = f"https://www.ebi.ac.uk/pdbe/api/pdb/entry/molecules/{pdb_id.lower()}"
    try:
        response = requests.get(url, headers=REQUEST_HEADERS)
        if response.status_code == 200:
            # Pretty-print the JSON to make it readable
            parsed_json = response.json()
            print(json.dumps(parsed_json, indent=2))
        else:
            print(f"Error: Failed to fetch data. Status code: {response.status_code}")
            print(f"Response text: {response.text}")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    inspect_api_response(PDB_ID)
