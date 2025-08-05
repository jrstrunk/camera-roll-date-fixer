# Year Format Renamer

A Python utility to rename files from 2-digit year format (YY-MM-DD HH-MM-SS) to 4-digit year format (YYYY-MM-DD HH-MM-SS) with intelligent century detection.

## Features

- **Recursive processing**: Searches through all subdirectories
- **Smart century detection**: Automatically determines if a 2-digit year belongs to the 1900s or 2000s
- **Dry run mode**: Preview changes before applying them
- **Verbose output**: Detailed logging of all operations
- **Error handling**: Comprehensive error reporting and handling
- **Conflict detection**: Prevents overwriting existing files

## Century Detection Logic

The script uses intelligent heuristics to determine the correct century for 2-digit years:

- **Years 00-30**: Assumed to be 2000-2030 (this century)
- **Years 31-99**: Assumed to be 1931-1999 (last century)

This cutoff can be customized using the `--cutoff-year` parameter.

## Usage

### Basic Usage

```bash
python rename_year_format.py /path/to/directory
```

### Dry Run (Preview Changes)

```bash
python rename_year_format.py /path/to/directory --dry-run
```

### Verbose Output

```bash
python rename_year_format.py /path/to/directory --verbose
```

### Custom Century Cutoff

```bash
python rename_year_format.py /path/to/directory --cutoff-year 25
```

### Combined Options

```bash
python rename_year_format.py /path/to/directory --dry-run --verbose --cutoff-year 25
```

## Examples

### File Renaming Examples

| Original Filename | Renamed Filename | Explanation |
|-------------------|------------------|-------------|
| `23-12-25 14-30-45.jpg` | `2023-12-25 14-30-45.jpg` | 23 → 2023 (this century) |
| `98-06-15 09-22-33.mp4` | `1998-06-15 09-22-33.mp4` | 98 → 1998 (last century) |
| `IMG_05-08-10 10-30-00.png` | `IMG_2005-08-10 10-30-00.png` | 05 → 2005 (this century) |
| `VID_85-03-20 16-45-12.mov` | `VID_1985-03-20 16-45-12.mov` | 85 → 1985 (last century) |

### Files That Won't Be Renamed

- `2023-12-25 14-30-45.jpg` (already 4-digit year)
- `23-12-25.jpg` (no time component)
- `IMG_20231225_143045.jpg` (different format)
- `regular_file.jpg` (no date pattern)

## Command Line Options

- `directory`: Directory to process (required)
- `--dry-run`: Show what would be renamed without actually renaming files
- `--verbose`, `-v`: Show detailed output for each file processed
- `--cutoff-year`: Set the cutoff year for century determination (default: 30)

## Pattern Matching

The script looks for filenames containing the pattern:
```
YY-MM-DD HH-MM-SS
```

Where:
- `YY`: 2-digit year (00-99)
- `MM`: 2-digit month (01-12)
- `DD`: 2-digit day (01-31)
- `HH`: 2-digit hour (00-23)
- `MM`: 2-digit minute (00-59)
- `SS`: 2-digit second (00-59)

The pattern can appear anywhere in the filename and will be converted while preserving the rest of the filename.

## Testing

Run the test script to see the renamer in action:

```bash
python test_rename_year_format.py
```

This will:
1. Create temporary test files with various naming patterns
2. Show century determination logic
3. Demonstrate pattern matching
4. Run both dry-run and actual renaming operations

## Error Handling

The script handles various error conditions:

- **File conflicts**: Won't overwrite existing files
- **Permission errors**: Reports files that can't be renamed
- **Invalid paths**: Validates directory existence
- **Pattern validation**: Only processes files matching the expected pattern

## Integration with Camera Roll Date Fixer

This utility can be used as a preprocessing step before running the main Camera Roll Date Fixer:

1. Run the year format renamer to standardize filename formats
2. Run the main date fixer to process metadata and organize files

```bash
# Step 1: Standardize year formats
python rename_year_format.py input/ --verbose

# Step 2: Run main date fixer
python main.py config.ini
```

## Requirements

- Python 3.6 or higher
- No external dependencies (uses only standard library)

## Safety Features

- **Dry run mode**: Always test changes before applying them
- **Backup recommendation**: Always backup your files before running
- **Non-destructive**: Original files are renamed, not modified
- **Conflict avoidance**: Won't overwrite existing files
- **Detailed logging**: Track all operations and errors