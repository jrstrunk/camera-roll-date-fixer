#!/usr/bin/env python3
"""
File Renamer: YY-MM-DD to YYYY-MM-DD Format

This script recursively finds files with 2-digit year format (YY-MM-DD HH-MM-SS)
and renames them to 4-digit year format (YYYY-MM-DD HH-MM-SS).

It makes intelligent assumptions about the century:
- Years 00-30: Assumes 2000-2030 (this century)
- Years 31-99: Assumes 1931-1999 (last century)

Usage:
    python rename_year_format.py /path/to/directory [--dry-run] [--verbose]
"""

import os
import re
import sys
import argparse
from pathlib import Path
from datetime import datetime


class YearFormatRenamer:
    def __init__(self, dry_run=False, verbose=False):
        self.dry_run = dry_run
        self.verbose = verbose
        self.current_year = datetime.now().year
        self.cutoff_year = 30  # Years 00-30 = 2000s, 31-99 = 1900s

        # Pattern to match YY-MM-DD HH-MM-SS format in filenames
        # This will match patterns like: 23-12-25 14-30-45 or 98-06-15 09-22-33
        # Uses negative lookbehind/lookahead to ensure we don't match 4-digit years
        self.pattern = re.compile(
            r'(?<!\d)(\d{2})-(\d{2})-(\d{2})\s+(\d{2})-(\d{2})-(\d{2})(?!\d)'
        )

        # Statistics
        self.files_processed = 0
        self.files_renamed = 0
        self.errors = []

    def determine_century(self, two_digit_year):
        """
        Determine the full 4-digit year from a 2-digit year.

        Args:
            two_digit_year (int): 2-digit year (0-99)

        Returns:
            int: 4-digit year
        """
        if two_digit_year <= self.cutoff_year:
            return 2000 + two_digit_year
        else:
            return 1900 + two_digit_year

    def convert_date_format(self, match):
        """
        Convert YY-MM-DD HH-MM-SS to YYYY-MM-DD HH-MM-SS format.

        Args:
            match: Regex match object

        Returns:
            str: Converted date string
        """
        yy, mm, dd, hh, min_val, ss = match.groups()

        # Convert 2-digit year to 4-digit year
        full_year = self.determine_century(int(yy))

        # Return the converted format
        return f"{full_year:04d}-{mm}-{dd} {hh}-{min_val}-{ss}"

    def should_rename_file(self, filename):
        """
        Check if a file should be renamed based on its name pattern.

        Args:
            filename (str): The filename to check

        Returns:
            bool: True if file should be renamed
        """
        return bool(self.pattern.search(filename))

    def generate_new_filename(self, old_filename):
        """
        Generate a new filename with 4-digit years.

        Args:
            old_filename (str): Original filename

        Returns:
            str: New filename with 4-digit years
        """
        return self.pattern.sub(self.convert_date_format, old_filename)

    def rename_file(self, file_path):
        """
        Rename a single file if it matches the pattern.

        Args:
            file_path (Path): Path to the file

        Returns:
            bool: True if file was renamed successfully
        """
        old_filename = file_path.name

        if not self.should_rename_file(old_filename):
            return False

        new_filename = self.generate_new_filename(old_filename)
        new_file_path = file_path.parent / new_filename

        # Check if new filename would conflict with existing file
        if new_file_path.exists() and new_file_path != file_path:
            error_msg = f"Cannot rename {file_path} - target file already exists: {new_file_path}"
            self.errors.append(error_msg)
            if self.verbose:
                print(f"ERROR: {error_msg}")
            return False

        # If new filename is the same as old filename, skip
        if old_filename == new_filename:
            if self.verbose:
                print(f"SKIP: {file_path} (already in correct format)")
            return False

        try:
            if self.dry_run:
                print(f"DRY RUN: Would rename {file_path} -> {new_file_path}")
            else:
                file_path.rename(new_file_path)
                if self.verbose:
                    print(f"RENAMED: {file_path} -> {new_file_path}")
                else:
                    print(f"Renamed: {old_filename} -> {new_filename}")

            return True

        except Exception as e:
            error_msg = f"Failed to rename {file_path}: {str(e)}"
            self.errors.append(error_msg)
            print(f"ERROR: {error_msg}")
            return False

    def process_directory(self, directory_path):
        """
        Recursively process all files in a directory.

        Args:
            directory_path (Path): Directory to process
        """
        if not directory_path.exists():
            print(f"ERROR: Directory does not exist: {directory_path}")
            return

        if not directory_path.is_dir():
            print(f"ERROR: Path is not a directory: {directory_path}")
            return

        print(f"Processing directory: {directory_path}")
        if self.dry_run:
            print("DRY RUN MODE - No files will be actually renamed")
        print()

        # Walk through all files recursively
        for file_path in directory_path.rglob('*'):
            if file_path.is_file():
                self.files_processed += 1

                if self.rename_file(file_path):
                    self.files_renamed += 1

    def print_summary(self):
        """Print a summary of the renaming operation."""
        print("\n" + "="*50)
        print("SUMMARY")
        print("="*50)
        print(f"Files processed: {self.files_processed}")
        print(f"Files renamed: {self.files_renamed}")
        print(f"Errors encountered: {len(self.errors)}")

        if self.errors:
            print("\nErrors:")
            for error in self.errors:
                print(f"  - {error}")

        if self.dry_run:
            print("\nThis was a dry run - no files were actually renamed.")


def main():
    parser = argparse.ArgumentParser(
        description="Rename files from YY-MM-DD HH-MM-SS to YYYY-MM-DD HH-MM-SS format",
        epilog="""
Examples:
  python rename_year_format.py /path/to/photos
  python rename_year_format.py /path/to/photos --dry-run --verbose
  python rename_year_format.py . --verbose
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        'directory',
        help='Directory to process (will search recursively)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be renamed without actually renaming files'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show detailed output for each file processed'
    )

    parser.add_argument(
        '--cutoff-year',
        type=int,
        default=30,
        help='Cutoff year for century determination (default: 30). '
             'Years 00-30 become 2000s, 31-99 become 1900s'
    )

    args = parser.parse_args()

    # Validate directory path
    directory_path = Path(args.directory).resolve()

    # Create renamer instance
    renamer = YearFormatRenamer(dry_run=args.dry_run, verbose=args.verbose)
    renamer.cutoff_year = args.cutoff_year

    # Show configuration
    print("Year Format Renamer")
    print("="*50)
    print(f"Directory: {directory_path}")
    print(f"Cutoff year: {args.cutoff_year} (00-{args.cutoff_year:02d} -> 2000s, {args.cutoff_year+1:02d}-99 -> 1900s)")
    print(f"Dry run: {args.dry_run}")
    print(f"Verbose: {args.verbose}")
    print()

    try:
        # Process the directory
        renamer.process_directory(directory_path)

        # Print summary
        renamer.print_summary()

        # Exit with error code if there were errors
        if renamer.errors:
            sys.exit(1)

    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
