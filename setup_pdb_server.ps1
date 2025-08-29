# A PowerShell script to automatically clone, install, and run the PDB-MCP-Server on Windows.
# This is designed to be run from within the "peptide project gpcr2" folder.

# --- Configuration ---
$RepoUrl = "https://github.com/Augmented-Nature/PDB-MCP-Server.git"
$FolderName = "PDB-MCP-Server"

# --- Main Script ---

Write-Host "--- Starting TR(i)P Lab PDB-MCP-Server Setup (Windows) ---" -ForegroundColor Green
Write-Host "This script will clone the repository, install its dependencies, and start the server."
Write-Host "Current location: $(Get-Location)"
Write-Host "----------------------------------------------------" -ForegroundColor Gray

# --- Step 1: Clone the Repository ---
# Check if the folder already exists to avoid errors.
if (Test-Path -Path $FolderName) {
    Write-Host "Folder '$FolderName' already exists. Skipping clone." -ForegroundColor Yellow
} else {
    Write-Host "Step 1: Cloning the repository..." -ForegroundColor Green
    git clone $RepoUrl
    
    # Check if the clone was successful
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error: Failed to clone the repository. Please check your internet connection and git installation." -ForegroundColor Red
        exit 1
    }
    Write-Host "Cloning complete."
}

# --- Step 2: Install Dependencies ---
# Navigate into the new folder. The 'Set-Location' (cd) command is critical.
try {
    Set-Location -Path $FolderName
} catch {
    Write-Host "Error: Could not navigate into the '$FolderName' directory." -ForegroundColor Red
    exit 1
}

Write-Host "`nStep 2: Installing Python dependencies from requirements.txt..." -ForegroundColor Green
Write-Host "Current location: $(Get-Location)"

# Check if requirements.txt exists
if (Test-Path -Path "requirements.txt") {
    pip install -r requirements.txt
    
    # Check if installation was successful
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error: Failed to install dependencies with pip. Please check your Python/pip installation." -ForegroundColor Red
        exit 1
    }
    Write-Host "Dependencies installed successfully."
} else {
    Write-Host "Error: Could not find requirements.txt in the repository. Cannot install dependencies." -ForegroundColor Red
    exit 1
}

# --- Step 3: Run the Server ---
Write-Host "`nStep 3: Starting the PDB-MCP-Server..." -ForegroundColor Green
Write-Host "The server will now start. This PowerShell window will be occupied by the server process."
Write-Host "To stop the server, press CTRL+C in this window." -ForegroundColor Yellow
Write-Host "----------------------------------------------------" -ForegroundColor Gray

python main.py

# This part will only be reached after the server is stopped
Write-Host "`n--- PDB-MCP-Server has been stopped. ---" -ForegroundColor Green 