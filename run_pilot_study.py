#!/usr/bin/env python3
"""
GLASS Database Peptide Ligand Identifier - Improved Version with Checkpointing

This script identifies peptide ligands from the GLASS GPCR database using InChIKey IDs.
It includes checkpointing, resume functionality, and better error handling for large datasets.

Requirements:
pip install pandas requests rdkit-pypi pubchempy numpy tqdm
"""

import pandas as pd
import requests
import time
import json
import re
import pickle
import signal
import sys
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import numpy as np
from tqdm import tqdm
from datetime import datetime

try:
    from rdkit import Chem
    from rdkit.Chem import Descriptors, rdMolDescriptors
    RDKIT_AVAILABLE = True
except ImportError:
    print("Warning: RDKit not available. Chemical structure analysis will be limited.")
    RDKIT_AVAILABLE = False

try:
    import pubchempy as pcp
    PUBCHEMPY_AVAILABLE = True
except ImportError:
    print("Warning: PubChemPy not available. Using direct API calls instead.")
    PUBCHEMPY_AVAILABLE = False


class GLASSPeptideIdentifier:
    def __init__(self, delay_between_requests: float = 0.1, checkpoint_dir: str = "./checkpoints", 
                 batch_size: int = 50):
        self.delay = delay_between_requests
        self.batch_size = batch_size  # Process in batches for better memory management
        self.peptide_results = []
        self.failed_queries = []
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(exist_ok=True)
        
        # Checkpoint settings
        self.checkpoint_interval = 100  # Save every 100 processed items
        self.processed_count = 0
        self.start_time = None
        
        # Rate limiting and retry settings
        self.max_retries = 3
        self.retry_delay = 1.0
        self.consecutive_failures = 0
        self.max_consecutive_failures = 10
        
        # Cache for API results to avoid re-querying
        self.api_cache = {}
        self.cache_file = self.checkpoint_dir / "api_cache.pkl"
        self.load_cache()
        
        # Setup graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Known peptide patterns and keywords
        self.peptide_keywords = [
            'peptide', 'protein', 'hormone', 'neuropeptide', 'cytokine', 'chemokine',
            'insulin', 'glucagon', 'vasopressin', 'oxytocin', 'endothelin', 'bradykinin',
            'substance p', 'enkephalin', 'dynorphin', 'neuropeptide y', 'somatostatin',
            'calcitonin', 'gastrin', 'cholecystokinin', 'angiotensin', 'endorphin'
        ]
        
        # Amino acid patterns for structure analysis
        self.amino_acid_smarts = [
            '[NX3][CX4H]([CX3](=[OX1])[NX3])[CX4]',  # General amino acid pattern
            '[NX3][CX4H](C(=O)[NX3])[CX4H2][SX2]',   # Cysteine pattern
            '[NX3][CX4H](C(=O)[NX3])c1ccccc1',       # Phenylalanine pattern
            '[NX3][CX4H](C(=O)[NX3])[CX4H2]c1c[nH]c2ccccc12'  # Tryptophan pattern
        ]

    def _signal_handler(self, signum, frame):
        """Handle graceful shutdown on interrupt"""
        print(f"\n\nReceived signal {signum}. Saving progress and shutting down...")
        self.save_checkpoint("interrupted")
        self.save_cache()
        sys.exit(0)

    def load_cache(self):
        """Load API response cache from disk"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'rb') as f:
                    self.api_cache = pickle.load(f)
                print(f"Loaded {len(self.api_cache)} cached API responses")
            except Exception as e:
                print(f"Warning: Could not load cache: {e}")
                self.api_cache = {}

    def save_cache(self):
        """Save API response cache to disk"""
        try:
            with open(self.cache_file, 'wb') as f:
                pickle.dump(self.api_cache, f)
            print(f"Saved {len(self.api_cache)} API responses to cache")
        except Exception as e:
            print(f"Warning: Could not save cache: {e}")

    def save_checkpoint(self, status: str = "running"):
        """Save current progress to checkpoint file"""
        checkpoint_data = {
            'status': status,
            'timestamp': datetime.now().isoformat(),
            'processed_count': self.processed_count,
            'peptide_results': self.peptide_results,
            'failed_queries': self.failed_queries,
            'start_time': self.start_time,
            'checkpoint_interval': self.checkpoint_interval
        }
        
        checkpoint_file = self.checkpoint_dir / f"checkpoint_{status}_{self.processed_count}.pkl"
        try:
            with open(checkpoint_file, 'wb') as f:
                pickle.dump(checkpoint_data, f)
            
            # Also save latest checkpoint
            latest_file = self.checkpoint_dir / "checkpoint_latest.pkl"
            with open(latest_file, 'wb') as f:
                pickle.dump(checkpoint_data, f)
                
            print(f"Checkpoint saved: {checkpoint_file.name}")
        except Exception as e:
            print(f"Error saving checkpoint: {e}")

    def load_checkpoint(self, checkpoint_file: str = None) -> bool:
        """Load progress from checkpoint file"""
        if checkpoint_file:
            checkpoint_path = Path(checkpoint_file)
        else:
            checkpoint_path = self.checkpoint_dir / "checkpoint_latest.pkl"
            
        if not checkpoint_path.exists():
            print("No checkpoint file found. Starting fresh.")
            return False
            
        try:
            with open(checkpoint_path, 'rb') as f:
                checkpoint_data = pickle.load(f)
                
            self.processed_count = checkpoint_data.get('processed_count', 0)
            self.peptide_results = checkpoint_data.get('peptide_results', [])
            self.failed_queries = checkpoint_data.get('failed_queries', [])
            self.start_time = checkpoint_data.get('start_time')
            
            print(f"Loaded checkpoint: {self.processed_count} items processed")
            print(f"Found {len(self.peptide_results)} peptide candidates so far")
            print(f"Checkpoint timestamp: {checkpoint_data.get('timestamp')}")
            
            return True
            
        except Exception as e:
            print(f"Error loading checkpoint: {e}")
            return False

    def list_checkpoints(self):
        """List available checkpoint files"""
        checkpoints = list(self.checkpoint_dir.glob("checkpoint_*.pkl"))
        if checkpoints:
            print("Available checkpoints:")
            for cp in sorted(checkpoints):
                print(f"  {cp.name}")
        else:
            print("No checkpoints found.")

    def estimate_time_remaining(self, total_items: int) -> str:
        """Estimate time remaining based on current progress"""
        if self.processed_count == 0 or not self.start_time:
            return "Unknown"
            
        elapsed = time.time() - self.start_time
        items_per_second = self.processed_count / elapsed
        remaining_items = total_items - self.processed_count
        
        if items_per_second > 0:
            remaining_seconds = remaining_items / items_per_second
            hours = int(remaining_seconds // 3600)
            minutes = int((remaining_seconds % 3600) // 60)
            return f"{hours}h {minutes}m"
        else:
            return "Unknown"

    def load_glass_data(self, file_path: str) -> pd.DataFrame:
        """Load GLASS database file (TSV format expected)"""
        try:
            df = pd.read_csv(file_path, sep='\t')
            print(f"Loaded {len(df)} records from GLASS database")
            print(f"Available columns: {list(df.columns)}")
            return df
        except Exception as e:
            print(f"Error loading file: {e}")
            return pd.DataFrame()

    def get_molecule_info_pubchem(self, inchikey: str) -> Optional[Dict]:
        """Get molecular information from PubChem using InChIKey with caching and retry logic"""
        # Check cache first
        cache_key = f"pubchem_{inchikey}"
        if cache_key in self.api_cache:
            return self.api_cache[cache_key]
            
        for attempt in range(self.max_retries):
            try:
                url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/inchikey/{inchikey}/property/MolecularWeight,MolecularFormula,CanonicalSMILES,IUPACName,Title/JSON"
                
                response = requests.get(url, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    if 'PropertyTable' in data and 'Properties' in data['PropertyTable']:
                        mol_data = data['PropertyTable']['Properties'][0]
                        # Cache the result
                        self.api_cache[cache_key] = mol_data
                        self.consecutive_failures = 0  # Reset failure counter
                        time.sleep(self.delay)
                        return mol_data
                elif response.status_code == 404:
                    # Cache negative result
                    self.api_cache[cache_key] = None
                    time.sleep(self.delay)
                    return None
                elif response.status_code == 429:  # Rate limited
                    wait_time = min(60, self.delay * (2 ** attempt))
                    print(f"Rate limited, waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    if attempt == self.max_retries - 1:
                        print(f"PubChem API error for {inchikey}: HTTP {response.status_code}")
                    
                time.sleep(self.delay * (attempt + 1))
                    
            except requests.Timeout:
                if attempt == self.max_retries - 1:
                    print(f"Timeout querying PubChem for {inchikey}")
                time.sleep(self.retry_delay * (attempt + 1))
            except requests.RequestException as e:
                if attempt == self.max_retries - 1:
                    print(f"Network error querying PubChem for {inchikey}: {e}")
                time.sleep(self.retry_delay * (attempt + 1))
            except Exception as e:
                print(f"Unexpected error querying PubChem for {inchikey}: {e}")
                break
                
        self.consecutive_failures += 1
        
        # If too many consecutive failures, increase delay
        if self.consecutive_failures >= self.max_consecutive_failures:
            print(f"Too many consecutive failures ({self.consecutive_failures}), increasing delay...")
            self.delay = min(self.delay * 2, 2.0)  # Cap at 2 seconds
            self.consecutive_failures = 0
            
        return None

    def get_molecule_info_chembl(self, inchikey: str) -> Optional[Dict]:
        """Get molecular information from ChEMBL using InChIKey with caching"""
        # Check cache first
        cache_key = f"chembl_{inchikey}"
        if cache_key in self.api_cache:
            return self.api_cache[cache_key]
            
        try:
            url = f"https://www.ebi.ac.uk/chembl/api/data/molecule?molecule_structures__standard_inchi_key={inchikey}&format=json"
            
            response = requests.get(url, timeout=15)
            time.sleep(self.delay)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('molecules') and len(data['molecules']) > 0:
                    mol_data = data['molecules'][0]
                    mapped_data = {
                        'MolecularWeight': mol_data.get('molecule_properties', {}).get('mw_freebase'),
                        'MolecularFormula': mol_data.get('molecule_properties', {}).get('molecular_formula'),
                        'CanonicalSMILES': mol_data.get('molecule_structures', {}).get('canonical_smiles'),
                        'Title': mol_data.get('pref_name'),
                        'IUPACName': mol_data.get('pref_name')
                    }
                    # Cache the result
                    self.api_cache[cache_key] = mapped_data
                    return mapped_data
            else:
                # Cache negative result
                self.api_cache[cache_key] = None
                    
        except requests.RequestException as e:
            print(f"Network error querying ChEMBL for {inchikey}: {e}")
        except Exception as e:
            print(f"Error querying ChEMBL for {inchikey}: {e}")
            
        return None

    def analyze_molecular_properties(self, mol_data: Dict) -> Dict:
        """Analyze molecular properties to determine if compound is likely a peptide"""
        analysis = {
            'is_peptide_candidate': False,
            'confidence_score': 0.0,
            'reasons': [],
            'properties': {}
        }
        
        # Extract properties and handle type conversions
        mw_raw = mol_data.get('MolecularWeight', 0)
        try:
            mw = float(mw_raw) if mw_raw else 0
        except (ValueError, TypeError):
            mw = 0
            
        formula = mol_data.get('MolecularFormula', '') or ''
        name = mol_data.get('Title', '') or mol_data.get('IUPACName', '') or mol_data.get('pref_name', '') or ''
        smiles = mol_data.get('CanonicalSMILES', '') or mol_data.get('canonical_smiles', '') or ''
        
        analysis['properties'] = {
            'molecular_weight': mw,
            'formula': formula,
            'name': name,
            'smiles': smiles
        }
        
        score = 0
        
        # 1. Molecular weight check
        if mw > 500:
            score += 2
            analysis['reasons'].append(f'High MW ({mw:.1f} Da)')
        if mw > 1000:
            score += 2
            analysis['reasons'].append('Very high MW (>1000 Da)')
        if mw > 3000:
            score += 3
            analysis['reasons'].append('Extremely high MW (>3000 Da)')
            
        # 2. Name-based identification
        name_lower = name.lower()
        for keyword in self.peptide_keywords:
            if keyword in name_lower:
                score += 3
                analysis['reasons'].append(f'Contains keyword: {keyword}')
                break
                
        # 3. Formula analysis
        if formula:
            try:
                n_count = formula.count('N')
                c_count = formula.count('C') if 'C' in formula else 1
                
                if c_count > 0:
                    n_to_c_ratio = n_count / c_count
                    if n_to_c_ratio > 0.2:
                        score += 2
                        analysis['reasons'].append(f'High N:C ratio ({n_to_c_ratio:.2f})')
            except Exception as e:
                print(f"Formula analysis error for {formula}: {e}")
                    
        # 4. SMILES-based analysis (if RDKit available)
        if RDKIT_AVAILABLE and smiles:
            try:
                mol = Chem.MolFromSmiles(smiles)
                if mol:
                    amide_pattern = Chem.MolFromSmarts('[NX3][CX3](=[OX1])[CX4]')
                    amide_matches = mol.GetSubstructMatches(amide_pattern)
                    
                    if len(amide_matches) >= 2:
                        score += 4
                        analysis['reasons'].append(f'Multiple amide bonds ({len(amide_matches)})')
                    elif len(amide_matches) == 1:
                        score += 1
                        analysis['reasons'].append('Single amide bond detected')
                        
                    aa_count = 0
                    for aa_smart in self.amino_acid_smarts:
                        pattern = Chem.MolFromSmarts(aa_smart)
                        matches = mol.GetSubstructMatches(pattern)
                        aa_count += len(matches)
                        
                    if aa_count >= 2:
                        score += 3
                        analysis['reasons'].append(f'Multiple AA-like structures ({aa_count})')
                        
            except Exception as e:
                print(f"RDKit analysis failed for {smiles}: {e}")
        
        analysis['confidence_score'] = min(score / 10.0, 1.0)
        analysis['is_peptide_candidate'] = score >= 4
        
        return analysis

    def process_inchikeys_batch(self, inchikeys: List[str], start_idx: int = 0, 
                              max_queries: Optional[int] = None) -> List[Dict]:
        """Process InChIKeys with checkpointing and resume capability"""
        results = []
        
        if max_queries:
            end_idx = min(start_idx + max_queries, len(inchikeys))
        else:
            end_idx = len(inchikeys)
            
        # Skip already processed items
        inchikeys_to_process = inchikeys[start_idx:end_idx]
        
        if not self.start_time:
            self.start_time = time.time()
            
        print(f"Processing InChIKeys {start_idx+1} to {end_idx} of {len(inchikeys)} total...")
        
        progress_bar = tqdm(enumerate(inchikeys_to_process), 
                           total=len(inchikeys_to_process),
                           desc="Processing")
        
        for i, inchikey in progress_bar:
            current_idx = start_idx + i
            
            try:
                # Try PubChem first
                mol_data = self.get_molecule_info_pubchem(inchikey)
                data_source = 'pubchem'
                
                # If PubChem fails, try ChEMBL
                if not mol_data:
                    mol_data = self.get_molecule_info_chembl(inchikey)
                    data_source = 'chembl'
                
                if mol_data:
                    analysis = self.analyze_molecular_properties(mol_data)
                    
                    result = {
                        'inchikey': inchikey,
                        'analysis': analysis,
                        'source': data_source
                    }
                    results.append(result)
                    self.peptide_results.append(result)
                    
                else:
                    self.failed_queries.append(inchikey)
                    
                self.processed_count = current_idx + 1
                
                # Update progress bar with time estimate
                time_remaining = self.estimate_time_remaining(len(inchikeys))
                progress_bar.set_postfix({
                    'peptides': len([r for r in results if r['analysis']['is_peptide_candidate']]),
                    'remaining': time_remaining
                })
                
                # Save checkpoint periodically
                if (i + 1) % self.checkpoint_interval == 0:
                    self.save_checkpoint("progress")
                    self.save_cache()
                    
            except Exception as e:
                print(f"Error processing {inchikey}: {e}")
                self.failed_queries.append(inchikey)
                self.processed_count = current_idx + 1
                
        # Save final checkpoint
        self.save_checkpoint("completed")
        self.save_cache()
                
        return results

    def filter_peptide_ligands(self, glass_df: pd.DataFrame, 
                              confidence_threshold: float = 0.4,
                              max_test_queries: Optional[int] = None,
                              resume: bool = False) -> Tuple[pd.DataFrame, Dict]:
        """Main function to filter peptide ligands with resume capability"""
        
        # Identify InChIKey column
        inchikey_col = None
        possible_cols = ['InChIKey', 'inchikey', 'INCHIKEY', 'InChI_Key', 'ligand_inchikey', 'compound_inchikey']
        
        for col in possible_cols:
            if col in glass_df.columns:
                inchikey_col = col
                break
                
        if not inchikey_col:
            print("Available columns:", list(glass_df.columns))
            raise ValueError("Could not find InChIKey column.")
            
        print(f"Using InChIKey column: {inchikey_col}")
        
        # Get unique InChIKeys
        unique_inchikeys = glass_df[inchikey_col].dropna().unique().tolist()
        print(f"Found {len(unique_inchikeys)} unique InChIKeys")
        
        start_idx = 0
        
        # Try to resume from checkpoint
        if resume:
            if self.load_checkpoint():
                start_idx = self.processed_count
                print(f"Resuming from position {start_idx}")
            else:
                print("No checkpoint found, starting fresh")
        
        # Process InChIKeys
        if start_idx < len(unique_inchikeys):
            remaining = len(unique_inchikeys) - start_idx
            if max_test_queries:
                remaining = min(remaining, max_test_queries)
            print(f"Processing {remaining} remaining InChIKeys...")
            
            new_results = self.process_inchikeys_batch(
                unique_inchikeys, 
                start_idx, 
                max_test_queries
            )
        
        # Create peptide mapping
        peptide_mapping = {}
        for result in self.peptide_results:
            inchikey = result['inchikey']
            analysis = result['analysis']
            
            if analysis['is_peptide_candidate'] and analysis['confidence_score'] >= confidence_threshold:
                peptide_mapping[inchikey] = {
                    'is_peptide': True,
                    'confidence': analysis['confidence_score'],
                    'reasons': analysis['reasons'],
                    'properties': analysis['properties']
                }
                
        print(f"\nIdentified {len(peptide_mapping)} peptide ligands out of {len(self.peptide_results)} processed")
        
        # Filter original DataFrame
        peptide_inchikeys = list(peptide_mapping.keys())
        peptide_df = glass_df[glass_df[inchikey_col].isin(peptide_inchikeys)].copy()
        
        # Add peptide classification information
        peptide_df['peptide_confidence'] = peptide_df[inchikey_col].map(
            lambda x: peptide_mapping.get(x, {}).get('confidence', 0)
        )
        peptide_df['peptide_reasons'] = peptide_df[inchikey_col].map(
            lambda x: '; '.join(peptide_mapping.get(x, {}).get('reasons', []))
        )
        
        return peptide_df, peptide_mapping

    def save_results(self, peptide_df: pd.DataFrame, peptide_mapping: Dict, 
                    output_dir: str = "./glass_peptide_results"):
        """Save results to files"""
        Path(output_dir).mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save filtered peptide ligands
        peptide_file = f"{output_dir}/glass_peptide_ligands_{timestamp}.tsv"
        peptide_df.to_csv(peptide_file, sep='\t', index=False)
        print(f"Saved {len(peptide_df)} peptide ligand records to {peptide_file}")
        
        # Save detailed analysis
        analysis_file = f"{output_dir}/peptide_analysis_details_{timestamp}.json"
        with open(analysis_file, 'w') as f:
            json.dump(peptide_mapping, f, indent=2)
        print(f"Saved detailed analysis to {analysis_file}")
        
        # Save processing log
        log_file = f"{output_dir}/processing_log_{timestamp}.txt"
        with open(log_file, 'w') as f:
            f.write("GLASS Database Peptide Ligand Analysis Log\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Analysis completed: {datetime.now().isoformat()}\n")
            f.write(f"Total items processed: {self.processed_count}\n")
            f.write(f"Peptide ligands identified: {len(peptide_df)}\n")
            f.write(f"Failed queries: {len(self.failed_queries)}\n")
            f.write(f"API cache size: {len(self.api_cache)}\n\n")
            
            if self.start_time:
                elapsed = time.time() - self.start_time
                f.write(f"Processing time: {elapsed/3600:.2f} hours\n")
                f.write(f"Processing rate: {self.processed_count/elapsed:.2f} items/second\n\n")
            
            # Confidence distribution
            if len(peptide_df) > 0:
                conf_scores = peptide_df['peptide_confidence'].values
                f.write("Confidence Score Distribution:\n")
                f.write(f"  Mean: {np.mean(conf_scores):.3f}\n")
                f.write(f"  Median: {np.median(conf_scores):.3f}\n")
                f.write(f"  Min: {np.min(conf_scores):.3f}\n")
                f.write(f"  Max: {np.max(conf_scores):.3f}\n\n")
        
        print(f"Saved processing log to {log_file}")


def main():
    """Main execution function with user interaction"""
    
    # Configuration - Modify these as needed
    CONFIG = {
        'glass_file_path': r"D:\peptide project gpcr2\glass2_full.tsv",
        'test_mode': False,  # Set to True for testing
        'max_test_queries': 1000,  # Only used if test_mode is True
        'delay_between_requests': 0.1,  # Seconds between API calls
        'checkpoint_interval': 100,  # Save progress every N items
        'confidence_threshold': 0.4,  # Minimum confidence for peptide classification
        'batch_size': 50,  # Process items in batches
        'max_workers': 1,  # For future parallel processing
    }
    
    print("GLASS Database Peptide Ligand Identifier - Enhanced Version")
    print("=" * 60)
    print(f"Configuration:")
    for key, value in CONFIG.items():
        print(f"  {key}: {value}")
    print("=" * 60)
    
    # Initialize identifier
    identifier = GLASSPeptideIdentifier(
        delay_between_requests=CONFIG['delay_between_requests']
    )
    identifier.checkpoint_interval = CONFIG['checkpoint_interval']
    
    # Check for existing checkpoints
    identifier.list_checkpoints()
    
    # Ask user about resuming
    resume = False
    if (identifier.checkpoint_dir / "checkpoint_latest.pkl").exists():
        response = input("\nFound existing checkpoint. Resume from last position? (y/n): ").lower().strip()
        resume = response == 'y'
    
    # Load GLASS data
    if not Path(CONFIG['glass_file_path']).exists():
        print(f"\nError: File {CONFIG['glass_file_path']} not found.")
        print("Please update the glass_file_path in CONFIG variable.")
        return
    
    glass_df = identifier.load_glass_data(CONFIG['glass_file_path'])
    if glass_df.empty:
        print("Failed to load GLASS data.")
        return
    
    max_queries = CONFIG['max_test_queries'] if CONFIG['test_mode'] else None
    
    if CONFIG['test_mode']:
        print(f"\n*** RUNNING IN TEST MODE (max {max_queries} queries) ***\n")
    
    print(f"Total records in database: {len(glass_df)}")
    
    # Show estimated time
    if not resume and not CONFIG['test_mode']:
        unique_inchikeys = glass_df[glass_df.columns[glass_df.columns.str.contains('inchi', case=False)][0]].dropna().unique()
        estimated_hours = (len(unique_inchikeys) * CONFIG['delay_between_requests']) / 3600
        print(f"Estimated time for full run: {estimated_hours:.1f} hours (assuming {CONFIG['delay_between_requests']}s per request)")
    
    # Confirm before starting
    if not resume:
        proceed = input(f"\nProceed with analysis? (y/n): ").lower().strip()
        if proceed != 'y':
            return
    
    try:
        # Run analysis
        peptide_df, peptide_mapping = identifier.filter_peptide_ligands(
            glass_df, 
            confidence_threshold=CONFIG['confidence_threshold'],
            max_test_queries=max_queries,
            resume=resume
        )
        
        # Save results
        identifier.save_results(peptide_df, peptide_mapping)
        
        # Print summary
        print(f"\n" + "=" * 60)
        print("ANALYSIS COMPLETE")
        print("=" * 60)
        print(f"Total records in database: {len(glass_df)}")
        print(f"Items processed: {identifier.processed_count}")
        print(f"Peptide ligands identified: {len(peptide_df)}")
        print(f"Failed queries: {len(identifier.failed_queries)}")
        print(f"API cache size: {len(identifier.api_cache)}")
        
        if identifier.start_time:
            elapsed = time.time() - identifier.start_time
            print(f"Processing time: {elapsed/3600:.2f} hours")
            print(f"Processing rate: {identifier.processed_count/elapsed:.2f} items/second")
        
        if len(peptide_df) > 0:
            print(f"\nTop 5 peptide candidates:")
            top_peptides = peptide_df.nlargest(5, 'peptide_confidence')
            for _, row in top_peptides.iterrows():
                inchikey_col = next(col for col in peptide_df.columns if 'inchi' in col.lower())
                inchikey = row[inchikey_col]
                conf = row['peptide_confidence']
                reasons = row['peptide_reasons'][:100] + "..." if len(row['peptide_reasons']) > 100 else row['peptide_reasons']
                print(f"  {inchikey}: {conf:.3f} ({reasons})")
        
    except KeyboardInterrupt:
        print("\nProcess interrupted by user. Progress has been saved.")
    except Exception as e:
        print(f"Error during analysis: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()