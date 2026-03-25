# OllamaForge: GGUF Auto-Importer & Symlinker

OllamaForge is a robust CLI tool designed to solve a major storage problem when using [Ollama](https://ollama.com/) alongside other local LLM frontends like [Text Generation WebUI](https://github.com/oobabooga/text-generation-webui) or [LM Studio](https://lmstudio.ai/).

## The Problem
When you create a model in Ollama using a local `.gguf` file via a `Modelfile`, Ollama typically copies the entire multi-gigabyte file into its internal `blobs` directory. If you are also keeping the original `.gguf` file for other software, you end up wasting massive amounts of disk space (e.g., 10-20GB per model). 

Furthermore, Ollama often throws a frustrating `400 Bad Request: invalid model name` error when trying to build local models if it gets confused by the file paths in your `Modelfile`.

## The Solution
OllamaForge automates the import process, fixes Ollama's pathing bugs, and elegantly hacks the storage mechanism:
1. **Dynamic Path Resolution:** It reads your `Modelfile`, creates a temporary background copy with an absolute, safe path to your `.gguf` file, and feeds *that* to Ollama. This completely eliminates the "invalid model name" error.
2. **Pre-calculation:** It calculates the exact SHA-256 hash of your model while displaying a clean progress bar.
3. **Symlink Optimization:** Once Ollama finishes importing the model, the script seamlessly deletes Ollama's duplicated blob and replaces it with a **symlink** pointing back to your original `.gguf` file.

You keep one physical copy of the model, saving terabytes of space over time, while all your software works perfectly.

## Features
* **Symlink Magic:** Reclaim your disk space.
* **Environment Variable Support:** Automatically detects paths like `HF_HOME` to find your models.
* **Interactive UI:** Run the script without arguments for a beautifully color-coded terminal menu.
* **Headless Mode:** Pass arguments directly for easy automation in batch scripts.
* **Auto-Detect Modelfiles:** Scans your directory to find matching `Modelfile`s for your specific `.gguf` automatically.
* **Pre-Flight Disk Check:** Ensures you have enough temporary space for Ollama to process the file before starting.

## Prerequisites
* **OS:** Windows (Linux/macOS support is native, but default paths in the script are currently configured for Windows).
* **Python:** [Python 3.x](https://www.python.org/downloads/)
* **Ollama:** Must be installed and accessible in your system `PATH`.
* **Permissions:** To create symlinks in Windows, you must either run the script as **Administrator**, or enable **Developer Mode** in Windows Settings (`Privacy & security` -> `For developers` -> `Developer Mode`).

## ⚙️ Configuration
The script is designed to be plug-and-play if you use standard environment variables. It prioritizes paths in the following order:

1. **`MODELS_DIR`**: Uses the `HF_HOME` environment variable if it exists.
2. **`BLOBS_DIR`**: Uses `BLOBS_DIR` if set. If not, it defaults to the `blobs` folder inside `HF_HOME`.
3. **`MODELFILES_DIR`**: Uses the `MODELFILES_DIR` environment variable if set.

### How to set Environment Variables in Windows
Open Command Prompt or PowerShell and use `setx` to define your paths permanently:
```powershell
setx HF_HOME "C:\Your\Models\Path"
setx BLOBS_DIR "C:\Your\Blobs\Path"
setx MODELFILES_DIR "C:\Your\Modelfiles\Path"
```
*(Note: You will need to restart your terminal after running `setx` for the changes to take effect).*

### Hardcoded Fallback Paths
If you prefer not to use environment variables, you **must** open `ollama_forge.py` in a text editor and modify the hardcoded fallback paths at the top of the file:

```python
DEFAULT_MODELS = Path(r"C:\CHANGE_ME_1")       	# Where your .gguf files are stored
DEFAULT_BLOBS = Path(r"C:\CHANGE_ME_2")         # Where Ollama stores its blobs
DEFAULT_MODELFILES = Path(r"C:\CHANGE_ME_3") 	# Where you keep your 'Ollama Modelfiles'
```

## Usage

### Interactive Mode
Simply run the script from your terminal. It will scan your directories, provide a numbered list of available models, and guide you through the process.
```powershell
python ollama_forge.py
```

### Headless Mode
Provide the paths directly as arguments. This skips the menus entirely.
```powershell
python ollama_forge.py "C:\path\to\your\model.gguf" "C:\path\to\your\Modelfile"
```
*Note: The Modelfile argument is optional. If omitted, the script will attempt to auto-detect it based on the .gguf filename.*

## Security & Reliability
All user input and paths are strictly sanitized to prevent directory traversal or injection attacks. Temporary files generated during the build process are safely destroyed regardless of whether the build succeeds or fails.

## License and Author
This project is licensed under the MIT License.

Copyright © 2026 - Author: Andreas Nilsen - Github: https://www.github.com/adde88 - adde88@gmail.com - @adde88 (25.03.26)