"""Data loader module for CSV ingestion and merging.

Handles discovery, loading, validation, and standardization of account
movement CSV files from the data/ directory.
"""

import pandas as pd
import numpy as np
import os
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import logging

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)
logger = logging.getLogger(__name__)


class TransactionDataLoader:
    """Load and standardize transaction CSV files from bank statements."""

    def __init__(self, data_dir: str = "data"):
        """Initialize the data loader.

        Args:
            data_dir: Path to directory containing CSV files.
        """
        self.data_dir = Path(data_dir)
        self.metadata_catalog: List[Dict] = []
        self.combined_df: Optional[pd.DataFrame] = None
        self.source_files: List[str] = []

    def discover_files(self, pattern: str = "*.csv") -> List[Path]:
        """Scan data directory for CSV files.

        Args:
            pattern: Glob pattern for file discovery.

        Returns:
            List of Path objects for discovered CSV files.
        """
        # List all CSV files, but exclude ones that look like output files
        files = sorted([f for f in self.data_dir.glob(pattern) 
                       if not f.name.startswith('processed_') 
                       and not f.name.startswith('cleaned_')
                       and not f.name.startswith('raw_')])
        logger.info(f"Discovered {len(files)} CSV files in {self.data_dir}")
        for f in files:
            logger.info(f"  - {f.name}")
        return files

    def _read_german_bank_csv(self, filepath: Path) -> Tuple[pd.DataFrame, Dict]:
        """Read a German bank CSV file with metadata header.

        German bank CSVs have metadata lines at the top, then a CSV header.
        This function detects where the CSV data starts and reads from there.

        Args:
            filepath: Path to the CSV file.

        Returns:
            Tuple of (DataFrame, metadata dict).
        """
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            lines = [line.rstrip('\n\r') for line in f.readlines()]

        metadata = {}
        csv_start_line = -1
        header = None

        # Find the CSV header line (contains semicolons and key words)
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue
            parts = stripped.split(';')
            # Header should have at least 5 fields and start with date-related column
            if len(parts) >= 5:
                first_col = parts[0].strip().lower()
                if any(kw in first_col for kw in ['buchung', 'date', 'booking']):
                    csv_start_line = i
                    header = [col.strip() for col in parts]
                    break

        if csv_start_line == -1:
            logger.error(f"Could not find CSV header in {filepath.name}")
            return pd.DataFrame(), {}

        # Parse metadata lines before CSV header
        for i in range(csv_start_line):
            line = lines[i].strip()
            if not line or ';' not in line:
                continue
            # Skip empty value fields
            if line.endswith(';'):
                continue
            parts = [p.strip() for p in line.split(';', 1)]
            if len(parts) == 2 and parts[0] and parts[1]:
                metadata[parts[0]] = parts[1]

        logger.info(f"CSV data starts at line {csv_start_line + 1}")
        logger.info(f"Header columns: {len(header)} fields")

        # Read data rows starting after header
        data_rows = []
        for i in range(csv_start_line + 1, len(lines)):
            line = lines[i].strip()
            if not line:
                continue

            parts = line.split(';')
            n_header = len(header)
            n_parts = len(parts)

            if n_parts == n_header:
                # Perfect match
                row = {header[j]: parts[j] for j in range(n_header)}
                data_rows.append(row)
            elif n_parts > n_header:
                # Extra fields - semicolons in text fields
                # Expected 9 fields, if more then text fields contain semicolons
                row = {}
                # First 2: dates
                row[header[0]] = parts[0]
                row[header[1]] = parts[1]
                # Last 3: balance, currency, amount
                row[header[6]] = parts[n_parts - 3]
                row[header[7]] = parts[n_parts - 2]
                row[header[8]] = parts[n_parts - 1]
                # Middle 4 fields (2-5): merge extras
                middle_parts = parts[2:n_parts - 3]
                if len(middle_parts) >= 4:
                    row[header[2]] = middle_parts[0]
                    row[header[3]] = middle_parts[1]
                    row[header[4]] = middle_parts[2]
                    row[header[5]] = middle_parts[3]
                elif len(middle_parts) == 3:
                    row[header[2]] = middle_parts[0]
                    row[header[3]] = middle_parts[1]
                    row[header[4]] = middle_parts[2]
                    row[header[5]] = ''
                elif len(middle_parts) == 2:
                    row[header[2]] = middle_parts[0]
                    row[header[3]] = middle_parts[1]
                    row[header[4]] = ''
                    row[header[5]] = ''
                elif len(middle_parts) == 1:
                    row[header[2]] = middle_parts[0]
                    row[header[3]] = ''
                    row[header[4]] = ''
                    row[header[5]] = ''
                else:
                    row[header[2]] = ''
                    row[header[3]] = ''
                    row[header[4]] = ''
                    row[header[5]] = ''
                data_rows.append(row)
            elif n_parts == n_header - 1:
                # One field missing
                row = {}
                for j in range(n_parts):
                    row[header[j]] = parts[j]
                row[header[n_parts]] = ''
                for j in range(n_parts + 1, n_header):
                    row[header[j]] = ''
                data_rows.append(row)
            else:
                logger.warning(f"Skipping line {i+1}: {n_parts} fields vs {n_header} expected")
                continue

        df = pd.DataFrame(data_rows)
        logger.info(f"Loaded {len(df)} data rows")
        return df, metadata

    def build_metadata_catalog(self, files: List[Path]) -> List[Dict]:
        """Build metadata catalog for discovered CSV files.

        Args:
            files: List of Path objects for CSV files.

        Returns:
            List of metadata dictionaries, one per file.
        """
        catalog = []
        for filepath in files:
            try:
                df, metadata = self._read_german_bank_csv(filepath)

                catalog_entry = {
                    'filename': filepath.name,
                    'filepath': str(filepath),
                    'columns': list(df.columns),
                    'row_count': len(df),
                    'metadata': metadata,
                    'date_range': {}
                }

                # Try to parse dates for range (using Buchung column)
                if 'Buchung' in df.columns and len(df) > 0:
                    # Parse German date format DD.MM.YYYY
                    dates = pd.to_datetime(df['Buchung'], errors='coerce', format='%d.%m.%Y')
                    valid_dates = dates.dropna()
                    if len(valid_dates) > 0:
                        catalog_entry['date_range'] = {
                            'min': valid_dates.min().strftime('%Y-%m-%d'),
                            'max': valid_dates.max().strftime('%Y-%m-%d')
                        }

                catalog.append(catalog_entry)
                logger.info(f"Cataloged {filepath.name}: {len(df)} rows")

            except Exception as e:
                logger.error(f"Error cataloging {filepath}: {e}")
                continue

        self.metadata_catalog = catalog
        return catalog

    def load_and_standardize(self, files: Optional[List[Path]] = None) -> pd.DataFrame:
        """Load all CSV files and create a unified DataFrame.

        Args:
            files: Optional list of Path objects. If None, auto-discovers.

        Returns:
            Unified DataFrame with standardized columns and source tracking.
        """
        if files is None:
            files = self.discover_files()

        if not files:
            raise ValueError("No CSV files found in data directory")

        self.build_metadata_catalog(files)

        all_dfs = []
        for filepath in files:
            try:
                logger.info(f"Loading {filepath.name}...")
                df = self._load_single_file(filepath)
                if df is not None and len(df) > 0:
                    df['source_file'] = filepath.name
                    all_dfs.append(df)
                    logger.info(f"  Loaded {len(df)} transactions from {filepath.name}")
            except Exception as e:
                logger.error(f"Failed to load {filepath.name}: {e}")
                continue

        if not all_dfs:
            raise ValueError("No data could be loaded from any file")

        combined = pd.concat(all_dfs, ignore_index=True)
        logger.info(f"Combined dataset: {len(combined)} total transactions from {len(all_dfs)} files")

        # Check for overlaps
        self._check_overlaps(combined)

        # Detect duplicates
        dup_count = self._detect_duplicates(combined)
        if dup_count > 0:
            logger.warning(f"Detected {dup_count} potential duplicate transactions")

        self.combined_df = combined
        return combined

    def _load_single_file(self, filepath: Path) -> Optional[pd.DataFrame]:
        """Load a single CSV file and standardize its columns.

        Args:
            filepath: Path to CSV file.

        Returns:
            Standardized DataFrame or None if loading fails.
        """
        df, metadata = self._read_german_bank_csv(filepath)

        if df.empty:
            logger.warning(f"Empty DataFrame from {filepath.name}")
            return None

        # Standardize column names
        df = self._standardize_columns(df)

        # Parse dates
        df = self._parse_dates(df)

        # Clean amounts
        df = self._clean_amounts(df)

        # Standardize currency
        df = self._standardize_currency(df)

        return df

    def _standardize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Map German column names to standard English names.

        Args:
            df: Input DataFrame with raw column names.

        Returns:
            DataFrame with standardized column names.
        """
        # German to English column mapping
        column_mapping = {
            'Buchung': 'booking_date',
            'Wertstellungsdatum': 'value_date',
            'Auftraggeber/Empfänger': 'counterparty',
            'Buchungstext': 'booking_text',
            'Verwendungszweck': 'purpose',
            'Saldo': 'balance',
            'Währung': 'currency',
            'Betrag': 'amount',
        }

        # Rename using available columns
        rename_dict = {}
        for old_col, new_col in column_mapping.items():
            if old_col in df.columns:
                rename_dict[old_col] = new_col
        
        df = df.rename(columns=rename_dict)

        # Ensure critical columns exist
        for col in ['booking_date', 'value_date', 'counterparty', 'amount', 'currency']:
            if col not in df.columns:
                df[col] = np.nan

        return df

    def _parse_dates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Parse date columns into datetime objects.

        Args:
            df: Input DataFrame with date columns as strings.

        Returns:
            DataFrame with parsed datetime columns.
        """
        # Try booking_date first
        if 'booking_date' in df.columns:
            df['booking_date'] = pd.to_datetime(
                df['booking_date'],
                errors='coerce',
                format='%d.%m.%Y',  # Try specific German format first
                dayfirst=True
            )

        # Then value_date
        if 'value_date' in df.columns:
            df['value_date'] = pd.to_datetime(
                df['value_date'],
                errors='coerce',
                format='%d.%m.%Y',
                dayfirst=True
            )

        # If booking_date still has issues or is NaT, use value_date as primary
        if 'booking_date' in df.columns and df['booking_date'].isna().all():
            if 'value_date' in df.columns:
                df['booking_date'] = df['value_date']

        return df

    def _clean_amounts(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and standardize amount column.

        Handles German decimal commas, thousands separators.

        Args:
            df: Input DataFrame with raw amount strings.

        Returns:
            DataFrame with cleaned numeric amounts.
        """
        if 'amount' not in df.columns:
            return df

        def parse_amount(val):
            if pd.isna(val):
                return np.nan
            s = str(val).strip()
            # Remove dots (thousands separators), replace comma with dot
            s = s.replace('.', '').replace(',', '.')
            # Remove currency symbols and whitespace
            s = s.replace('€', '').replace('EUR', '').strip()
            try:
                return float(s)
            except ValueError:
                return np.nan

        df['amount'] = df['amount'].apply(parse_amount)
        return df

    def _standardize_currency(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize currency codes to ISO 4217 format.

        Args:
            df: Input DataFrame with currency column.

        Returns:
            DataFrame with standardized currency codes.
        """
        if 'currency' not in df.columns:
            df['currency'] = 'EUR'
            return df

        def standardize_currency(val):
            if pd.isna(val):
                return 'EUR'
            s = str(val).strip().upper()
            if s in ['EUR', 'EURO', '€', '']:
                return 'EUR'
            elif s in ['USD', 'US$', 'DOLLAR']:
                return 'USD'
            elif len(s) == 3 and s.isalpha():
                return s
            return 'EUR'

        df['currency'] = df['currency'].apply(standardize_currency)
        return df

    def _check_overlaps(self, df: pd.DataFrame) -> None:
        """Check for overlapping time periods across source files.

        Args:
            df: Combined DataFrame with source_file column.
        """
        if 'value_date' not in df.columns or 'source_file' not in df.columns:
            return

        file_ranges = {}
        for source in df['source_file'].unique():
            mask = df['source_file'] == source
            dates = df.loc[mask, 'value_date'].dropna()
            if len(dates) > 0:
                file_ranges[source] = {
                    'min': dates.min(),
                    'max': dates.max()
                }

        files = list(file_ranges.keys())
        for i in range(len(files)):
            for j in range(i + 1, len(files)):
                ri = file_ranges[files[i]]
                rj = file_ranges[files[j]]
                if ri['min'] <= rj['max'] and ri['max'] >= rj['min']:
                    overlap_start = max(ri['min'], rj['min'])
                    overlap_end = min(ri['max'], rj['max'])
                    logger.warning(
                        f"Overlapping period between {files[i]} and {files[j]}: "
                        f"{overlap_start.strftime('%Y-%m-%d')} to {overlap_end.strftime('%Y-%m-%d')}"
                    )

    def _detect_duplicates(self, df: pd.DataFrame, threshold_days: int = 1) -> int:
        """Detect potential duplicate transactions.

        Args:
            df: Combined DataFrame.
            threshold_days: Number of days tolerance for date matching.

        Returns:
            Number of potential duplicate groups found.
        """
        if len(df) < 2:
            return 0

        df = df.copy()
        
        # Use the first available date column
        date_col = None
        for col in ['value_date', 'booking_date']:
            if col in df.columns:
                date_col = col
                break
        
        if date_col:
            df['date_rounded'] = df[date_col].dt.floor('D')
        else:
            return 0
        
        df['amount_rounded'] = df['amount'].round(2)

        # Create mask for duplicates based on date, amount, and counterparty
        dup_cols = ['date_rounded', 'amount_rounded', 'counterparty']
        # Only use columns that exist
        dup_cols = [c for c in dup_cols if c in df.columns]
        
        if len(dup_cols) >= 2:
            duplicates = df.duplicated(subset=dup_cols, keep=False)
        else:
            duplicates = pd.Series([False] * len(df), index=df.index)

        dup_count = duplicates.sum()
        if dup_count > 0:
            df['is_duplicate'] = duplicates
            dup_groups = df[df['is_duplicate']].groupby(
                dup_cols
            ).size()
            logger.info(f"Found {len(dup_groups)} duplicate groups")

        return dup_count


def main():
    """Example usage of the data loader."""
    loader = TransactionDataLoader(data_dir="data")
    files = loader.discover_files()
    catalog = loader.build_metadata_catalog(files)

    print("\n=== Metadata Catalog ===")
    for entry in catalog:
        print(f"\nFile: {entry['filename']}")
        print(f"  Rows: {entry['row_count']}")
        print(f"  Columns: {len(entry['columns'])} fields")
        if entry['date_range'].get('min'):
            print(f"  Date Range: {entry['date_range']['min']} to {entry['date_range']['max']}")

    print("\n=== Loading and Standardizing Data ===")
    df = loader.load_and_standardize()

    print(f"\n=== Combined Dataset ===")
    print(f"Total transactions: {len(df)}")
    print(f"Date range: {df['value_date'].min()} to {df['value_date'].max()}")
    print(f"Total amount (outflows): {df[df['amount'] < 0]['amount'].sum():.2f}")
    print(f"Total amount (inflows): {df[df['amount'] > 0]['amount'].sum():.2f}")
    print(f"Sources: {df['source_file'].nunique()} files")
    
    # Show sample data
    print(f"\n=== Sample Data (first 5 rows) ===")
    sample_cols = [c for c in ['value_date', 'counterparty', 'amount', 'purpose'] if c in df.columns]
    print(df[sample_cols].head().to_string())

    # Save processed data
    output_path = "data/processed_transactions.csv"
    df.to_csv(output_path, index=False)
    print(f"\nSaved processed data to {output_path}")


if __name__ == "__main__":
    main()
