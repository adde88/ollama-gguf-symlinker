# Changelog

All notable changes to the OllamaForge GGUF Auto-Importer & Symlinker project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to Semantic Versioning.

## [Released] - 2026-04-05

### Added
* Batch installation support allowing multiple models to be queued and processed sequentially using comma-separated input.
* Interactive uninstallation menu (`-u`, `--uninstall`, `-U`) to securely delete multiple installed models at once.
* State awareness functionality querying Ollama directly to display `[INSTALLED]` or `[NOT INSTALLED]` tags in the interactive menus.
* In-memory caching system (`_MODELFILE_CACHE`) to drastically speed up Modelfile searching.
* Intelligent model naming logic capturing standard quantization tags (e.g., `q4_k_m`) directly from the filename.
* Automatic reinstallation prompt if a selected model already exists in the Ollama registry.

### Changed
* Transitioned from environment variable-based pathing to direct, hardcoded volume paths for specialized setups.
* Rewrote Modelfile generation to process line-by-line instead of using broad Regex replacements.
* Improved progress and UI feedback to handle sequential model processing gracefully.

### Fixed
* Script no longer terminates completely if a single model fails during a batch operation; it safely skips to the next item.
* Modelfile parsing now utilizes `utf-8-sig` encoding to silently strip invisible Byte Order Mark (BOM) characters that previously caused Ollama import failures.
* Sanitized Modelfile generation to automatically strip out markdown code blocks (like ` ```dockerfile `) from existing texts.
* Enforced strict Linux newlines (`\n`) during temporary Modelfile creation to guarantee cross-platform compatibility with the Ollama engine.

### Security
* Strengthened input sanitization for all interactive prompts, explicitly verifying integers and array boundaries before execution.
* Maintained isolated `subprocess.run` execution paths to prevent shell injection vulnerabilities during model handling.