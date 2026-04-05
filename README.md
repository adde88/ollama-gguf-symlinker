# OllamaForge: GGUF Auto-Importer & Symlinker

OllamaForge is a robust CLI tool designed to solve a major storage problem when using [Ollama](https://ollama.com/) alongside other local LLM frontends like [Text Generation WebUI](https://github.com/oobabooga/text-generation-webui) or [LM Studio](https://lmstudio.ai/).

## The Problem
When you create a model in Ollama using a local `.gguf` file via a `Modelfile`, Ollama typically copies the entire multi-gigabyte file into its internal `blobs` directory. If you are also keeping the original `.gguf` file for other software, you end up wasting massive amounts of disk space (e.g., 10-20GB per model). 

Furthermore, Ollama often throws a frustrating `400 Bad Request: invalid model name` error when trying to build local models if it gets confused by the file paths in your `Modelfile`.

## The Solution
OllamaForge automates the import process, fixes Ollama's pathing bugs, and elegantly hacks the storage mechanism:
1. **Dynamic Path Resolution:** It reads your `Modelfile`, creates a temporary background copy with an absolute, safe path to your `.gguf` file, and feeds *that* to Ollama. This completely eliminates the "invalid model name" error.
2. **Pre-calculation & Caching:** It calculates the exact SHA-256 hash of your model while displaying a clean progress bar, and caches Modelfiles in memory for lightning-fast lookups.
3. **Symlink Optimization:** Once Ollama finishes importing the model, the script seamlessly deletes Ollama's duplicated blob and replaces it with a **symlink** pointing back to your original `.gguf` file.

You keep one physical copy of the model, saving terabytes of space over time, while all your software works perfectly.

## Features
* **Symlink Magic:** Reclaim your disk space automatically.
* **Batch Processing:** Install or uninstall multiple models at the same time using comma-separated inputs (e.g., `1, 3, 4`).
* **Interactive UI:** Run the script without arguments for a beautifully color-coded terminal menu that displays the dynamic `[INSTALLED]` or `[NOT INSTALLED]` status of your files.
* **Interactive Uninstaller:** Clean up your Ollama registry effortlessly with a built-in multi-select uninstaller.
* **Headless Mode:** Pass arguments directly for easy automation in batch scripts.
* **Auto-Detect Modelfiles:** Scans your directory to find matching `Modelfile`s for your specific `.gguf` automatically, utilizing intelligent regex quantization tag detection.
* **Pre-Flight Disk Check:** Ensures you have enough temporary space for Ollama to process the file before starting, gracefully skipping models in batch queues if space is insufficient.

## Prerequisites
* **OS:** Windows (Linux/macOS support is native, but default paths in the script are currently configured for Windows).
* **Python:** [Python 3.x](https://www.python.org/downloads/)
* **Ollama:** Must be installed and accessible in your system `PATH`.
* **Permissions:** To create symlinks in Windows, you must either run the script as **Administrator**, or enable **Developer Mode** in Windows Settings (`Privacy & security` -> `For developers` -> `Developer Mode`).

## ⚙️ Configuration
The script uses direct directory paths for maximum stability. You **must** open `ollama_forge.py` (or whatever you named the script) in a text editor and modify the hardcoded paths at the top of the file to match your setup:

```python
MODELS_DIR = Path(r"C:\CHANGE_ME_1")         # Where your .gguf files are stored
BLOBS_DIR = Path(r"C:\CHANGE_ME_2")           # Where Ollama stores its blobs
MODELFILES_DIR = Path(r"C:\CHANGE_ME_3") # Where you keep your 'Ollama Modelfiles'