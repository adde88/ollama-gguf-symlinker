#!/usr/bin/env python3
# Copyright © 2026 - Author: Andreas Nilsen - Github: https://www.github.com/adde88 - adde88@gmail.com - @adde88 (05.04.26)

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

# ==========================================
# PATH CONFIGURATION (CHANGE THESE IF NEEDED)
# ==========================================
MODELS_DIR = Path(r"CHANGE_ME_1")
BLOBS_DIR = Path(r"CHANGE_ME_2")
MODELFILES_DIR = Path(r"CHANGE_ME_3")

# Cache for Modelfiles to avoid repeated file operations
_MODELFILE_CACHE = []

def format_bytes(size_in_bytes: int) -> str:
    """Converts bytes to MB, GB, or TB format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_in_bytes < 1024.0:
            if size_in_bytes % 1 == 0 and unit != 'GB': 
                return f"{int(size_in_bytes)}{unit}"
            return f"{size_in_bytes:.2f}{unit}"
        size_in_bytes /= 1024.0

def print_header():
    """Prints header and storage status."""
    target_drive = BLOBS_DIR.anchor
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
    print(f"{Colors.BLUE}Date: (05.04.26){Colors.RESET}")
    print(f"{Colors.GREEN}{Colors.BOLD}Storage Capacity ({target_drive}): {storage_str} Free{Colors.RESET}\n")

def check_disk_space(model_path: Path):
    """Checks if there is enough disk space before starting the import."""
    target_drive = BLOBS_DIR.anchor
    try:
        free_space = shutil.disk_usage(target_drive).free
        model_size = os.path.getsize(model_path)
        required_space = model_size + (2 * 1024**3) # Model size + 2GB buffer
        
        if free_space < required_space:
            print(f"\n{Colors.RED}[!] CRITICAL ERROR: Not enough storage space on {target_drive} for {model_path.name}{Colors.RESET}")
            print(f"{Colors.RED}    Free space: {format_bytes(free_space)}{Colors.RESET}")
            print(f"{Colors.RED}    Required space (Model + Buffer): {format_bytes(required_space)}{Colors.RESET}")
            return False
        return True
    except Exception as e:
        print(f"{Colors.YELLOW}[!] Could not verify disk space for {model_path.name}: {e}. Continuing anyway...{Colors.RESET}")
        return True

def get_installed_ollama_models() -> set:
    """Fetches a list of installed models directly from Ollama."""
    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True, check=True)
        lines = result.stdout.strip().split('\n')[1:] # Skip the header row
        return {line.split()[0].lower() for line in lines if line}
    except Exception:
        return set()

def get_model_name_from_modelfile(mf_path: Path) -> str:
    """Generates a valid Ollama model name based on the Modelfile filename."""
    raw_name = mf_path.stem.lower().replace(' ', '-')
    
    # If it already has a colon, keep it
    if ':' in raw_name:
        return raw_name
        
    # Regex that finds common quantization tags at the end of the filename (e.g. .q5_k_m, -q6_k, .i1-q4_k_s)
    # This ensures models get the correct tag in Ollama, without ruining e.g. "qwen2.5"
    match = re.search(r'[-.](q[0-9]+[a-z0-9_]*|i[0-9]+[-_]q[0-9]+[a-z0-9_]*|fp[0-9]+)$', raw_name)
    if match:
        base = raw_name[:match.start()]
        tag = match.group(1)
        return f"{base}:{tag}"
        
    # Fallback if the file does not end with a standard GGUF tag
    return f"{raw_name}:latest"

def preload_modelfiles():
    """Loads all Modelfiles into memory to optimize search."""
    global _MODELFILE_CACHE
    if not _MODELFILE_CACHE and MODELFILES_DIR.exists():
        for mf in MODELFILES_DIR.rglob("*"):
            if mf.is_file():
                try:
                    content = mf.read_text(encoding='utf-8', errors='ignore')
                    _MODELFILE_CACHE.append((mf, content))
                except Exception:
                    continue

def normalize_name(name: str) -> str:
    """Removes file extensions, paths, and special characters for bulletproof searching."""
    name = Path(name.replace('\\', '/')).name
    name = re.sub(r'(?i)\.(gguf|modelfile)$', '', name)
    return re.sub(r'[^a-z0-9]', '', name.lower())

def get_modelfiles_for_gguf(gguf_name: str) -> list[Path]:
    """Finds Modelfiles by comparing normalized filenames."""
    preload_modelfiles()
    matches = []
    norm_target = normalize_name(gguf_name)
    
    for mf, content in _MODELFILE_CACHE:
        if normalize_name(mf.name) == norm_target:
            matches.append(mf)
            continue
            
        from_match = re.search(r'^\s*(?i:FROM)\s+["\']?(.*?)["\']?\s*$', content, re.MULTILINE)
        if from_match:
            from_path_str = from_match.group(1).strip()
            if normalize_name(from_path_str) == norm_target:
                matches.append(mf)
                continue
                
    return list(set(matches))

def is_gguf_installed(gguf_name: str, installed_models: set) -> bool:
    """Checks if any of the associated Modelfiles for this GGUF are already installed in Ollama."""
    mfs = get_modelfiles_for_gguf(gguf_name)
    for mf in mfs:
        # Fetches the exact name our script would give the model
        expected_name = get_model_name_from_modelfile(mf)
        if expected_name in installed_models:
            return True
    return False

def interactive_uninstall_models():
    """Lists and uninstalls selected Ollama models."""
    installed_models = sorted(list(get_installed_ollama_models()))

    if not installed_models:
        print(f"{Colors.YELLOW}[!] No models are currently installed in Ollama.{Colors.RESET}")
        sys.exit(0)

    print(f"\n{Colors.CYAN}[*] Installed Ollama models:{Colors.RESET}")
    for index, model in enumerate(installed_models, start=1):
        print(f"{Colors.YELLOW}[{index}]{Colors.RESET} {Colors.GREEN}{model}{Colors.RESET}")

    while True:
        try:
            print(f"\n{Colors.BOLD}Enter the numbers of the models you want to remove, separated by commas (e.g., 1, 3, 4).")
            choice = input(f"Press Enter to cancel:\n> {Colors.RESET}").strip()

            if not choice:
                print(f"{Colors.YELLOW}[*] Canceling uninstallation.{Colors.RESET}")
                sys.exit(0)

            # Secure input sanitization and parsing
            raw_selections = [x.strip() for x in choice.split(',')]
            valid_indices = set()
            invalid_inputs = []

            for sel in raw_selections:
                if sel.isdigit():
                    idx = int(sel)
                    if 1 <= idx <= len(installed_models):
                        valid_indices.add(idx - 1)
                    else:
                        invalid_inputs.append(sel)
                elif sel:
                    invalid_inputs.append(sel)

            if invalid_inputs:
                print(f"{Colors.RED}[!] Invalid choices ignored: {', '.join(invalid_inputs)}{Colors.RESET}")

            if not valid_indices:
                print(f"{Colors.RED}[!] No valid models selected. Try again.{Colors.RESET}")
                continue

            models_to_remove = [installed_models[i] for i in valid_indices]

            # Confirmation
            print(f"\n{Colors.RED}{Colors.BOLD}The following models will be deleted:{Colors.RESET}")
            for m in models_to_remove:
                print(f" - {m}")

            confirm = input(f"\n{Colors.BOLD}Are you sure you want to remove these? (y/N): {Colors.RESET}").strip().lower()
            if confirm != 'y':
                print(f"{Colors.YELLOW}[*] Canceling deletion.{Colors.RESET}")
                continue

            # Perform secure deletion
            for model in models_to_remove:
                print(f"{Colors.CYAN}[*] Deleting '{model}'...{Colors.RESET}")
                try:
                    subprocess.run(["ollama", "rm", model], check=True, capture_output=True)
                    print(f"{Colors.GREEN}[+] '{model}' was successfully deleted!{Colors.RESET}")
                except subprocess.CalledProcessError:
                    print(f"{Colors.RED}[!] Could not remove '{model}'. It might be in use.{Colors.RESET}")

            print(f"\n{Colors.GREEN}{Colors.BOLD}[+] Uninstallation complete.{Colors.RESET}")
            sys.exit(0)

        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}[*] Process aborted.{Colors.RESET}")
            sys.exit(0)

def interactive_model_selection(installed_models: set) -> list[Path]:
    """Lists .gguf files and allows installation of multiple models via comma-separation."""
    print(f"{Colors.CYAN}[*] Searching for .gguf files in {MODELS_DIR}...{Colors.RESET}\n")
    gguf_files = list(MODELS_DIR.rglob("*.gguf"))
    
    if not gguf_files:
        print(f"{Colors.RED}[!] No .gguf files found in the directory.{Colors.RESET}")
        sys.exit(1)
        
    for index, file_path in enumerate(gguf_files, start=1):
        rel_path = file_path.relative_to(MODELS_DIR)
        file_size = format_bytes(os.path.getsize(file_path))
        
        installed = is_gguf_installed(file_path.name, installed_models)
        if installed:
            status = f"{Colors.GREEN}[INSTALLED]{Colors.RESET}"
            color = Colors.GREEN
        else:
            status = f"{Colors.RED}[NOT INSTALLED]{Colors.RESET}"
            color = Colors.RED
            
        print(f"{Colors.YELLOW}[{index}]{Colors.RESET} {color}{rel_path} {Colors.CYAN}({file_size}) {status}")
        
    while True:
        try:
            print(f"\n{Colors.BOLD}Select the numbers of the models you want to install, separated by commas (e.g., 1, 3, 4).")
            choice = input(f"Press Enter to cancel:\n> {Colors.RESET}").strip()
            
            if not choice:
                print(f"{Colors.YELLOW}[*] Canceling installation.{Colors.RESET}")
                sys.exit(0)

            # Secure input sanitization and parsing
            raw_selections = [x.strip() for x in choice.split(',')]
            valid_indices = set()
            invalid_inputs = []

            for sel in raw_selections:
                if sel.isdigit():
                    idx = int(sel)
                    if 1 <= idx <= len(gguf_files):
                        valid_indices.add(idx - 1)
                    else:
                        invalid_inputs.append(sel)
                elif sel:
                    invalid_inputs.append(sel)

            if invalid_inputs:
                print(f"{Colors.RED}[!] Invalid choices ignored: {', '.join(invalid_inputs)}{Colors.RESET}")

            if not valid_indices:
                print(f"{Colors.RED}[!] No valid files selected. Try again.{Colors.RESET}")
                continue

            return [gguf_files[i] for i in valid_indices]

        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}[*] Process aborted.{Colors.RESET}")
            sys.exit(0)

def interactive_modelfile_selection(matches: list[Path], installed_models: set) -> Path:
    """Lists Modelfiles and shows which ones are installed."""
    print(f"\n{Colors.CYAN}[*] Multiple Modelfiles found for this model. Select version:{Colors.RESET}")
    
    for index, file_path in enumerate(matches, start=1):
        rel_path = file_path.relative_to(MODELFILES_DIR)
        model_name = get_model_name_from_modelfile(file_path)
        
        if model_name in installed_models:
            status = f"{Colors.GREEN}[INSTALLED]{Colors.RESET}"
            color = Colors.GREEN
        else:
            status = f"{Colors.RED}[NOT INSTALLED]{Colors.RESET}"
            color = Colors.RED
            
        print(f"{Colors.YELLOW}[{index}]{Colors.RESET} {color}{rel_path} -> ({model_name}) {status}")
        
    while True:
        try:
            choice = input(f"\n{Colors.BOLD}Select Modelfile (1-{len(matches)}) or press Ctrl+C to skip this one:\n> {Colors.RESET}")
            index = int(choice)
            if 1 <= index <= len(matches):
                return matches[index - 1]
            print(f"{Colors.RED}[!] Invalid choice.{Colors.RESET}")
        except ValueError:
            print(f"{Colors.RED}[!] Please enter a number.{Colors.RESET}")
        except KeyboardInterrupt:
            return None

def calculate_sha256(file_path: Path) -> str:
    """Calculates SHA256 with a dynamic progress indicator."""
    print(f"\n{Colors.CYAN}[*] Calculating SHA256 for {file_path.name}...{Colors.RESET}")
    sha256_hash = hashlib.sha256()
    
    try:
        file_size = os.path.getsize(file_path)
        processed_bytes = 0
        
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(8192 * 1024), b""):
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
        print(f"\n{Colors.RED}[!] Error during hash calculation for {file_path.name}: {e}{Colors.RESET}")
        return None

def sanitize_path(path_str: str) -> Path:
    if not path_str:
        return None
    clean_str = path_str.strip(' \'"')
    path = Path(clean_str).resolve()
    if not path.exists():
        print(f"{Colors.RED}[!] Error: Cannot find path -> {path}{Colors.RESET}")
        return None
    return path

def replace_blob_with_symlink(original_file: Path, blob_hash: str):
    """Deletes Ollama's blob copy and replaces it with a symlink to save space."""
    blob_path = BLOBS_DIR / f"sha256-{blob_hash}"
    
    if not blob_path.exists():
        print(f"{Colors.RED}[!] Could not find blob '{blob_path.name}' in Ollama. Something went wrong during import.{Colors.RESET}")
        return

    if blob_path.is_symlink():
        print(f"{Colors.GREEN}[+] The blob is already a symlink. No action required.{Colors.RESET}")
        return

    print(f"\n{Colors.CYAN}[*] Replacing Ollama blob with symlink to free up storage space...{Colors.RESET}")
    try:
        os.remove(blob_path)
        print(f"{Colors.YELLOW}    [+] Deleted Ollama's physical copy ({blob_path.name}){Colors.RESET}")
        
        os.symlink(original_file, blob_path)
        print(f"{Colors.GREEN}    [+] Symlink created!{Colors.RESET}")
        
        saved_space = format_bytes(os.path.getsize(original_file))
        print(f"{Colors.GREEN}{Colors.BOLD}[+] Success: You saved {saved_space} of storage space!{Colors.RESET}")
        
    except OSError as e:
        print(f"{Colors.RED}[!] Error creating symlink: {e}{Colors.RESET}")
        print(f"{Colors.RED}    Ensure the script is run as Administrator, or that Developer Mode is enabled in Windows.{Colors.RESET}")

def main():
    parser = argparse.ArgumentParser(description="Imports GGUF models into Ollama and replaces blobs with symlinks.")
    parser.add_argument("model", nargs="?", help="Full path to .gguf file(s) separated by commas")
    parser.add_argument("modelfile", nargs="?", help="Full path to Modelfile (Optional, best used with only 1 model)")
    parser.add_argument("-u", "--uninstall", "-U", action="store_true", dest="uninstall", help="Opens an interactive menu to delete one or more Ollama models")
    args = parser.parse_args()

    is_interactive = len(sys.argv) == 1
    print_header()

    if args.uninstall:
        interactive_uninstall_models()
        return

    installed_models = get_installed_ollama_models()
    model_paths = []

    if is_interactive:
        model_input = input(f"{Colors.BOLD}1. Enter full path to .gguf file(s) separated by commas (Press Enter to select from list):\n> {Colors.RESET}")
        if not model_input.strip():
            model_paths = interactive_model_selection(installed_models)
        else:
            raw_paths = [p.strip() for p in model_input.split(',')]
            model_paths = [sanitize_path(p) for p in raw_paths if sanitize_path(p)]
    else:
        if args.model:
            raw_paths = [p.strip() for p in args.model.split(',')]
            model_paths = [sanitize_path(p) for p in raw_paths if sanitize_path(p)]

    if not model_paths:
        print(f"{Colors.RED}[!] No valid models specified for installation.{Colors.RESET}")
        sys.exit(1)

    print(f"\n{Colors.GREEN}{Colors.BOLD}[+] Found {len(model_paths)} model(s) in the queue.{Colors.RESET}")

    for index, model_path in enumerate(model_paths, start=1):
        print(f"\n{Colors.MAGENTA}{Colors.BOLD}======================================================================{Colors.RESET}")
        print(f"{Colors.CYAN}{Colors.BOLD} Processing model {index} of {len(model_paths)}: {model_path.name} {Colors.RESET}")
        print(f"{Colors.MAGENTA}{Colors.BOLD}======================================================================{Colors.RESET}")

        if not check_disk_space(model_path):
            print(f"{Colors.RED}[!] Skipping {model_path.name} due to insufficient disk space.{Colors.RESET}")
            continue

        modelfile_path = None
        
        # Only ask for manual Modelfile if installing 1 file, to avoid interrupting a batch process
        if is_interactive and len(model_paths) == 1:
            mf_input = input(f"\n{Colors.BOLD}2. Enter full path to Modelfile (Press Enter for automatic search):\n> {Colors.RESET}")
            modelfile_path = sanitize_path(mf_input) if mf_input.strip() else None
        elif args.modelfile and len(model_paths) == 1:
            modelfile_path = sanitize_path(args.modelfile)

        if not modelfile_path:
            matches = get_modelfiles_for_gguf(model_path.name)
            if not matches:
                print(f"{Colors.RED}[!] Found no matching Modelfile for {model_path.name}. Skipping.{Colors.RESET}")
                continue
            elif len(matches) == 1:
                print(f"{Colors.GREEN}[+] Found exactly one match: {matches[0].name}{Colors.RESET}")
                modelfile_path = matches[0]
            else:
                modelfile_path = interactive_modelfile_selection(matches, installed_models)
                if not modelfile_path:
                    print(f"{Colors.YELLOW}[*] Skipped Modelfile selection. Aborting for {model_path.name}.{Colors.RESET}")
                    continue

        model_name = get_model_name_from_modelfile(modelfile_path)

        if model_name in installed_models:
            print(f"\n{Colors.YELLOW}[!] The model '{model_name}' is already installed. Starting reinstallation...{Colors.RESET}")
            try:
                subprocess.run(["ollama", "rm", model_name], check=True, capture_output=True)
                print(f"{Colors.GREEN}[+] Old version deleted.{Colors.RESET}")
            except subprocess.CalledProcessError:
                print(f"{Colors.RED}[!] Failed to remove the old version of the model. It may be locked by another process.{Colors.RESET}")

        file_hash = calculate_sha256(model_path)
        if not file_hash:
            continue
            
        print(f"{Colors.GREEN}[+] SHA256 Hash: {file_hash}{Colors.RESET}")
        print(f"\n{Colors.CYAN}[*] Preparing absolute paths for Ollama...{Colors.RESET}")
        
        temp_mf_path = None
        try:
            with open(modelfile_path, 'r', encoding='utf-8-sig') as mf:
                lines = mf.readlines()
                
            safe_gguf_path = str(model_path).replace('\\', '/')
            clean_lines = []
            
            for line in lines:
                if re.match(r'^\s*(?i:FROM)\s+', line):
                    continue
                if line.strip() in ['```dockerfile', '```']:
                    continue
                clean_lines.append(line)
            
            temp_mf_path = Path(tempfile.gettempdir()) / f"temp_ollama_{file_hash[:8]}.Modelfile"
            
            with open(temp_mf_path, 'w', encoding='utf-8', newline='\n') as temp_mf:
                temp_mf.write(f'FROM "{safe_gguf_path}"\n')
                temp_mf.writelines(clean_lines)
                
        except Exception as e:
            print(f"{Colors.RED}[!] Error generating temporary Modelfile for {model_path.name}: {e}. Skipping.{Colors.RESET}")
            continue

        print(f"{Colors.CYAN}[*] Starting import to Ollama.{Colors.RESET}")
        print(f"{Colors.CYAN}[*] Building model with name: '{model_name}'...\n{Colors.RESET}")
        
        cmd = ["ollama", "create", model_name, "-f", str(temp_mf_path)]
        
        try:
            subprocess.run(cmd, check=True)
            print(f"\n{Colors.GREEN}{Colors.BOLD}[+] Ollama model '{model_name}' created.{Colors.RESET}")
            
            if temp_mf_path and temp_mf_path.exists():
                os.remove(temp_mf_path)
            
            replace_blob_with_symlink(model_path, file_hash)
            
            # Updates the local list so the next model in the loop knows this was just installed
            installed_models.add(model_name)
            print(f"\n{Colors.GREEN}{Colors.BOLD}Ready to use: ollama run {model_name}{Colors.RESET}")

        except subprocess.CalledProcessError:
            print(f"\n{Colors.RED}[!] Ollama failed during import for {model_name}.{Colors.RESET}")
            print(f"{Colors.RED}    Error message from Ollama is shown above.{Colors.RESET}")
            
            if temp_mf_path and temp_mf_path.exists():
                print(f"\n{Colors.YELLOW}[?] Debug info: This is what the start of the generated file looked like:{Colors.RESET}")
                with open(temp_mf_path, 'r', encoding='utf-8') as debug_f:
                    for i, line in enumerate(debug_f):
                        if i < 10:
                            print(f"    Line {i+1}: {line.strip()}")
                os.remove(temp_mf_path)
            continue

    print(f"\n{Colors.GREEN}{Colors.BOLD}======================================================================{Colors.RESET}")
    print(f"{Colors.GREEN}{Colors.BOLD}[+] All tasks completed!{Colors.RESET}")
    print(f"{Colors.GREEN}{Colors.BOLD}======================================================================{Colors.RESET}\n")

if __name__ == "__main__":
    main()