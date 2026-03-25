#!/usr/bin/env python3
# Copyright © 2026 - Author: Andreas Nilsen - Github: https://www.github.com/adde88 - adde88@gmail.com - @adde88 (25.03.26)

import os
import sys
import re
import shutil
import hashlib
import argparse
import tempfile
import subprocess
from pathlib import Path

# Enable ANSI colors in Windows Terminal
os.system('')

class Colors:
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    MAGENTA = '\033[95m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

# --- CONFIGURATION LOGIC ---
# The script prioritizes Environment Variables if set.
# If they are not set, it falls back to the static DEFAULT paths below.
#
# Environment Variable Rules:
# 1. MODELS_DIR: Uses %HF_HOME% if exists.
# 2. BLOBS_DIR: Uses %BLOBS_DIR% if exists. If not, uses %HF_HOME%\blobs.
# 3. MODELFILES_DIR: Uses %MODELFILES_DIR% if exists.
#
# To set environment variables in Windows (Command Prompt / PowerShell):
# setx HF_HOME "C:\Your\Models\Path"
# setx BLOBS_DIR "C:\Your\Blobs\Path"
# setx MODELFILES_DIR "C:\Your\Modelfiles\Path"

# STATIC FALLBACK PATHS (Modify these if you don't use environment variables!)
DEFAULT_MODELS = Path(r"C:\CHANGE_ME_1")
DEFAULT_BLOBS = Path(r"C:\CHANGE_ME_2")
DEFAULT_MODELFILES = Path(r"C:\CHANGE_ME_3")

# Resolve MODELS_DIR
hf_home_env = os.environ.get("HF_HOME")
MODELS_DIR = Path(hf_home_env) if hf_home_env else DEFAULT_MODELS

# Resolve BLOBS_DIR
blobs_dir_env = os.environ.get("BLOBS_DIR")
if blobs_dir_env:
    BLOBS_DIR = Path(blobs_dir_env)
elif hf_home_env:
    BLOBS_DIR = Path(hf_home_env) / "blobs"
else:
    BLOBS_DIR = DEFAULT_BLOBS

# Resolve MODELFILES_DIR
modelfiles_dir_env = os.environ.get("MODELFILES_DIR")
MODELFILES_DIR = Path(modelfiles_dir_env) if modelfiles_dir_env else DEFAULT_MODELFILES

def format_bytes(size_in_bytes: int) -> str:
    """Formats bytes into readable MB, GB, or TB strings."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_in_bytes < 1024.0:
            if size_in_bytes % 1 == 0 and unit != 'GB': 
                return f"{int(size_in_bytes)}{unit}"
            return f"{size_in_bytes:.2f}{unit}"
        size_in_bytes /= 1024.0

def print_header():
    """Prints the project header, copyright, and current storage status."""
    target_drive = BLOBS_DIR.anchor if BLOBS_DIR.exists() else "C:\\"
    try:
        total, used, free = shutil.disk_usage(target_drive)
        storage_str = f"{format_bytes(free)} / {format_bytes(total)}"
    except Exception:
        storage_str = "Unknown"

    print(f"\n{Colors.MAGENTA}{Colors.BOLD}======================================================================{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}             OllamaForge: GGUF Auto-Importer & Symlinker              {Colors.RESET}")
    print(f"{Colors.MAGENTA}{Colors.BOLD}======================================================================{Colors.RESET}")
    print(f"{Colors.BLUE}Copyright © 2026 - Author: Andreas Nilsen{Colors.RESET}")
    print(f"{Colors.BLUE}GitHub: https://www.github.com/adde88 - adde88@gmail.com - @adde88{Colors.RESET}")
    print(f"{Colors.BLUE}Date: (25.03.26){Colors.RESET}")
    print(f"{Colors.GREEN}{Colors.BOLD}Storage ({target_drive}): {storage_str} Available{Colors.RESET}\n")
    
    # Path summary for transparency
    print(f"{Colors.YELLOW}Active Paths:{Colors.RESET}")
    print(f"  Models:     {MODELS_DIR}")
    print(f"  Blobs:      {BLOBS_DIR}")
    print(f"  Modelfiles: {MODELFILES_DIR}\n")

def check_disk_space(model_path: Path):
    """Checks if there is enough space on the target drive before proceeding."""
    if not BLOBS_DIR.parent.exists():
        print(f"{Colors.YELLOW}[!] Warning: The parent directory for BLOBS_DIR does not exist. Ensure paths are correct.{Colors.RESET}")
        return

    target_drive = BLOBS_DIR.anchor
    try:
        free_space = shutil.disk_usage(target_drive).free
        model_size = os.path.getsize(model_path)
        
        # Require the size of the model + 2GB buffer for safety
        required_space = model_size + (2 * 1024**3)
        
        if free_space < required_space:
            print(f"\n{Colors.RED}[!] CRITICAL ERROR: Insufficient storage space on {target_drive}{Colors.RESET}")
            print(f"{Colors.RED}    Target drive free space: {format_bytes(free_space)}{Colors.RESET}")
            print(f"{Colors.RED}    Required space (Model + Buffer): {format_bytes(required_space)}{Colors.RESET}")
            print(f"{Colors.RED}    Please free up some space and try again.{Colors.RESET}")
            sys.exit(1)
    except Exception as e:
        print(f"{Colors.YELLOW}[!] Could not verify disk space: {e}. Proceeding anyway...{Colors.RESET}")

def calculate_sha256(file_path: Path) -> str:
    """Calculates SHA256 with a progress bar."""
    print(f"{Colors.CYAN}[*] Calculating SHA256 for {file_path.name}...{Colors.RESET}")
    sha256_hash = hashlib.sha256()
    
    try:
        file_size = os.path.getsize(file_path)
        processed_bytes = 0
        
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096 * 1024), b""):
                sha256_hash.update(byte_block)
                processed_bytes += len(byte_block)
                
                percent = (processed_bytes / file_size) * 100
                bar_length = 40
                filled_len = int(bar_length * processed_bytes // file_size)
                bar = '█' * filled_len + '-' * (bar_length - filled_len)
                
                sys.stdout.write(f'\r{Colors.YELLOW}    Progress: |{bar}| {percent:.1f}% Complete{Colors.RESET}')
                sys.stdout.flush()
                
        print() 
        return sha256_hash.hexdigest()
    except Exception as e:
        print(f"\n{Colors.RED}[!] Critical error during hash calculation: {e}{Colors.RESET}")
        sys.exit(1)

def interactive_model_selection() -> Path:
    """Searches through MODELS_DIR and lets the user select a file via a number."""
    if not MODELS_DIR.exists():
        print(f"{Colors.RED}[!] MODELS_DIR does not exist: {MODELS_DIR}{Colors.RESET}")
        print(f"{Colors.YELLOW}    Check your environment variables or fallback paths.{Colors.RESET}")
        sys.exit(1)

    print(f"{Colors.CYAN}[*] Searching for .gguf files in {MODELS_DIR}...{Colors.RESET}\n")
    gguf_files = list(MODELS_DIR.rglob("*.gguf"))
    
    if not gguf_files:
        print(f"{Colors.RED}[!] Found no .gguf files in the directory or subdirectories.{Colors.RESET}")
        sys.exit(1)
        
    for index, file_path in enumerate(gguf_files, start=1):
        try:
            rel_path = file_path.relative_to(MODELS_DIR)
        except ValueError:
            rel_path = file_path.name
        file_size = format_bytes(os.path.getsize(file_path))
        print(f"{Colors.YELLOW}[{index}]{Colors.RESET} {rel_path} {Colors.CYAN}({file_size}){Colors.RESET}")
        
    while True:
        try:
            choice = input(f"\n{Colors.BOLD}Choose a number (1-{len(gguf_files)}) or press Ctrl+C to cancel:\n> {Colors.RESET}")
            index = int(choice)
            if 1 <= index <= len(gguf_files):
                return gguf_files[index - 1]
            else:
                print(f"{Colors.RED}[!] Invalid choice. Must be between 1 and {len(gguf_files)}.{Colors.RESET}")
        except ValueError:
            print(f"{Colors.RED}[!] Please enter a valid number.{Colors.RESET}")

def find_modelfiles(gguf_name: str) -> list[Path]:
    """Finds all Modelfiles that contain the target .gguf filename."""
    print(f"\n{Colors.CYAN}[*] Auto-searching for Modelfiles targeting '{gguf_name}'...{Colors.RESET}")
    matches = []
    
    if not MODELFILES_DIR.exists():
        print(f"{Colors.RED}[!] Modelfile directory does not exist: {MODELFILES_DIR}{Colors.RESET}")
        return matches

    for modelfile in MODELFILES_DIR.rglob("*"):
        if modelfile.is_file():
            try:
                with open(modelfile, "r", encoding="utf-8") as f:
                    if gguf_name in f.read():
                        matches.append(modelfile)
            except Exception:
                continue
    return matches

def interactive_modelfile_selection(matches: list[Path]) -> Path:
    """Prompts the user to select from multiple discovered Modelfiles."""
    print(f"{Colors.GREEN}[+] Found {len(matches)} Modelfiles targeting this model:{Colors.RESET}\n")
    
    for index, file_path in enumerate(matches, start=1):
        try:
            rel_path = file_path.relative_to(MODELFILES_DIR)
        except ValueError:
            rel_path = file_path.name
        print(f"{Colors.YELLOW}[{index}]{Colors.RESET} {rel_path}")
        
    while True:
        try:
            choice = input(f"\n{Colors.BOLD}Choose a Modelfile (1-{len(matches)}) or press Ctrl+C to cancel:\n> {Colors.RESET}")
            index = int(choice)
            if 1 <= index <= len(matches):
                return matches[index - 1]
            else:
                print(f"{Colors.RED}[!] Invalid choice. Must be between 1 and {len(matches)}.{Colors.RESET}")
        except ValueError:
            print(f"{Colors.RED}[!] Please enter a valid number.{Colors.RESET}")

def sanitize_path(path_str: str) -> Path:
    if not path_str:
        return None
    clean_str = path_str.strip(' \'"')
    path = Path(clean_str).resolve()
    if not path.exists():
        print(f"{Colors.RED}[!] Error: Cannot find path -> {path}{Colors.RESET}")
        sys.exit(1)
    return path

def replace_blob_with_symlink(original_file: Path, blob_hash: str):
    """Deletes Ollama's copy of the blob and replaces it with a symlink to the original."""
    blob_path = BLOBS_DIR / f"sha256-{blob_hash}"
    
    if not blob_path.exists():
        print(f"{Colors.RED}[!] Could not find the blob '{blob_path.name}' in Ollama. Something went wrong during import.{Colors.RESET}")
        return

    if blob_path.is_symlink():
        print(f"{Colors.GREEN}[+] The blob is already a symlink. No action needed!{Colors.RESET}")
        return

    print(f"\n{Colors.CYAN}[*] Replacing the Ollama blob with a symlink to save space...{Colors.RESET}")
    try:
        os.remove(blob_path)
        print(f"{Colors.YELLOW}    [+] Deleted Ollama's physical copy ({blob_path.name}){Colors.RESET}")
        
        os.symlink(original_file, blob_path)
        print(f"{Colors.GREEN}    [+] Symlink created successfully!{Colors.RESET}")
        
        saved_space = format_bytes(os.path.getsize(original_file))
        print(f"{Colors.GREEN}{Colors.BOLD}[+] Success: You saved {saved_space} of storage space!{Colors.RESET}")
        
    except OSError as e:
        print(f"{Colors.RED}[!] Error while creating symlink: {e}{Colors.RESET}")
        print(f"{Colors.RED}    Note: Ensure the script is run as Administrator, or that Developer Mode is enabled in Windows.{Colors.RESET}")

def main():
    parser = argparse.ArgumentParser(description="Import GGUF models into Ollama and replace blobs with symlinks.")
    parser.add_argument("model", nargs="?", help="Full path to the .gguf file")
    parser.add_argument("modelfile", nargs="?", help="Full path to the Modelfile (Optional)")
    args = parser.parse_args()

    is_interactive = len(sys.argv) == 1
    print_header()

    # 1. Select model
    if is_interactive:
        model_input = input(f"{Colors.BOLD}1. Enter the full path to the .gguf file (Press Enter to list and select from menu):\n> {Colors.RESET}")
        if not model_input.strip():
            model_path = interactive_model_selection()
        else:
            model_path = sanitize_path(model_input)
    else:
        model_path = sanitize_path(args.model)

    if not model_path:
        print(f"{Colors.RED}[!] No model path provided.{Colors.RESET}")
        sys.exit(1)

    # 2. Check disk space immediately to fail fast
    check_disk_space(model_path)

    print(f"\n{Colors.MAGENTA}----------------------------------------------------------------------{Colors.RESET}")
    print(f"{Colors.GREEN}[+] Selected model: {model_path.name} ({format_bytes(os.path.getsize(model_path))}){Colors.RESET}")

    # 3. Find Modelfile(s)
    modelfile_path = None
    if is_interactive:
        mf_input = input(f"\n{Colors.BOLD}2. Enter the full path to the Modelfile (Press Enter to auto-search):\n> {Colors.RESET}")
        modelfile_path = sanitize_path(mf_input) if mf_input.strip() else None
    elif args.modelfile:
        modelfile_path = sanitize_path(args.modelfile)

    if not modelfile_path:
        matches = find_modelfiles(model_path.name)
        if not matches:
            print(f"{Colors.RED}[!] Failed to auto-detect any Modelfile for {model_path.name}.{Colors.RESET}")
            sys.exit(1)
        elif len(matches) == 1:
            print(f"{Colors.GREEN}[+] Found exactly one match: {matches[0].name}{Colors.RESET}")
            modelfile_path = matches[0]
        else:
            modelfile_path = interactive_modelfile_selection(matches)

    # 4. Calculate SHA256 BEFORE running Ollama
    print(f"\n{Colors.MAGENTA}----------------------------------------------------------------------{Colors.RESET}")
    file_hash = calculate_sha256(model_path)
    print(f"{Colors.GREEN}[+] SHA256 Hash: {file_hash}{Colors.RESET}")

    # 5. Build dynamic Modelfile and run Ollama
    print(f"\n{Colors.MAGENTA}----------------------------------------------------------------------{Colors.RESET}")
    
    model_name = model_path.stem.lower().replace('.', ':')
    print(f"{Colors.CYAN}[*] Preparing absolute paths for Ollama...{Colors.RESET}")
    
    temp_mf_path = None
    try:
        # Read the original Modelfile
        with open(modelfile_path, 'r', encoding='utf-8') as mf:
            mf_content = mf.read()
            
        # Convert Windows backslashes to forward slashes for Ollama's parser
        safe_gguf_path = str(model_path).replace('\\', '/')
        
        # Regex to find the FROM line and replace it entirely with the absolute path
        new_mf_content = re.sub(r'^\s*(?i:FROM)\s+.*$', f'FROM "{safe_gguf_path}"', mf_content, flags=re.MULTILINE)
        
        # Save to a temporary Modelfile in the system temp directory
        temp_mf_path = Path(tempfile.gettempdir()) / f"temp_ollama_{file_hash[:8]}.Modelfile"
        with open(temp_mf_path, 'w', encoding='utf-8') as temp_mf:
            temp_mf.write(new_mf_content)
            
    except Exception as e:
        print(f"{Colors.RED}[!] Failed to prepare temporary Modelfile: {e}{Colors.RESET}")
        sys.exit(1)

    print(f"{Colors.CYAN}[*] Starting import to Ollama.{Colors.RESET}")
    print(f"{Colors.CYAN}[*] Building model named: '{model_name}'...{Colors.RESET}\n")
    
    # We now pass the temporary Modelfile to Ollama
    cmd = ["ollama", "create", model_name, "-f", str(temp_mf_path)]
    
    try:
        subprocess.run(cmd, check=True)
        print(f"\n{Colors.GREEN}{Colors.BOLD}[+] Ollama model created.{Colors.RESET}")
        
        # Cleanup temporary Modelfile
        if temp_mf_path and temp_mf_path.exists():
            os.remove(temp_mf_path)
        
        # 6. Execute the symlink hack
        print(f"\n{Colors.MAGENTA}----------------------------------------------------------------------{Colors.RESET}")
        replace_blob_with_symlink(model_path, file_hash)

        print(f"\n{Colors.GREEN}{Colors.BOLD}Ready to use: ollama run {model_name}{Colors.RESET}\n")

    except subprocess.CalledProcessError:
        print(f"\n{Colors.RED}[!] Ollama failed during import. Check the error message above.{Colors.RESET}")
        # Cleanup temporary Modelfile on failure as well
        if temp_mf_path and temp_mf_path.exists():
            os.remove(temp_mf_path)
        sys.exit(1)

if __name__ == "__main__":
    main()