# envyeet

*envyeet* is a depedency free python script that allows you to merge environment variable files together.

## Installation

1. **Copy the script** to your desired location:
   ```bash
   # Download and save the script
   curl -O https://raw.githubusercontent.com/yourusername/envyeet/main/envyeet.py
   # or copy it directly to your machine
   ```

2. **Make it executable** (recommended):
   ```bash
   chmod +x envyeet.py
   ```

3. **Choose one of the following methods to call it from anywhere**:

   **Option A: Add to PATH**
   ```bash
   # Move to a directory in your PATH (e.g., /usr/local/bin or ~/bin)
   sudo mv envyeet.py /usr/local/bin/envyeet
   # or
   mkdir -p ~/bin && mv envyeet.py ~/bin/envyeet
   # Add ~/bin to your PATH if not already present
   export PATH="$HOME/bin:$PATH"
   ```

   **Option B: Create an alias** (add to your shell config: ~/.bashrc, ~/.zshrc, etc.)
   ```bash
   alias envyeet='python3 /path/to/envyeet.py'
   ```

   **Option C: Add to your personal bin directory**
   ```bash
   mkdir -p ~/.local/bin
   cp envyeet.py ~/.local/bin/envyeet
   chmod +x ~/.local/bin/envyeet
   export PATH="$HOME/.local/bin:$PATH"
   ```

After installation, you can call it as:
```bash
envyeet merge .env.staging .env
```

## Usage

```bash
# Merge staging env into local env (stdout)
python3 envyeet.py merge .env.staging .env.local

# Merge with overwrite
python3 envyeet.py merge .env.staging .env --overwrite

# Merge with squash (add new keys)
python3 envyeet.py merge .env.staging .env --squash

# Backup an env file
python3 envyeet.py backup .env

# Dry run preview
python3 envyeet.py merge .env.staging .env --dry-run -v
```

