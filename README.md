# bigfile-map

`bigfile-map` generates a colorful terminal bar chart of the largest files in a directory tree.

## Installation

```bash
pip install .
```

## Usage

```text
bigfile-map [-n TOP] [-w WIDTH] [-i] [path]
```

- `-n, --top`: how many top files to display (default: 20)
- `-w, --width`: bar width in characters (default: 40)
- `-i, --interactive`: prompt to choose directory
- `path`: directory to scan (default: current directory)

If `--interactive` is used, a menu of subdirectories is shown and you can also enter a custom path.

### Examples

```bash
# interactive mode
bigfile-map --interactive

# scan a specific folder
bigfile-map -n 10 -w 60 ~/my/project
```

