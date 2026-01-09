# envyeet

*envyeet* is a depedency free python script that allows you to merge environment variable files together.

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

