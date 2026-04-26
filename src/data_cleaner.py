import pandas as pd
import numpy as np
from typing import Optional, Dict, List, Tuple
import logging
import re

from category_rules import CATEGORY_RULES, get_special_patterns, normalize_text, get_exclusion_keywords, categorize_generic_provider

logger = logging.getLogger(__name__)


def _repair_mojibake_text(value) -> str:
    """Repariert haeufige Encoding-Artefakte fuer robustes Matching."""
    if value is None:
        return ''
    text = str(value)
    replacements = {
        'Echtzeit�berweisung': 'Echtzeitueberweisung',
        '�berweisung': 'ueberweisung',
        'Empf�nger': 'Empfaenger',
        'Grundsteue r': 'Grundsteuer',
        'grundsteue r': 'grundsteuer',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


class TransactionCleaner:
    """Clean and validate transaction data.

    Provides methods for:
    - Duplicate detection and removal
    - Missing value handling
    - Category standardization
    - Amount and date validation
    - Outlier detection
    """

    # Common German transaction keywords for categorization
    CATEGORY_KEYWORDS = {
        'income': {
            'salary': ['gehalt', 'lohn', 'rente', 'einkommen'],
            'refund': ['gutschrift', 'erstattung', 'zurückzahlung'],
            'transfer': ['überweisung', 'dauerauftrag'],
            'investment': ['dividende', 'zins', 'gewinn'],
        },
        'groceries': {
            'supermarket': ['netto', 'aldi', 'lidl', 'rewe', 'edeka', 'kaufland',
                           'penny', 'norma', 'famila', 'marktkauf', 'nahkauf'],
            'discounter': ['netto', 'aldi', 'lidl', 'penny'],
        },
        'dining': {
            'restaurant': ['restaurant', 'café', 'cafe', 'gaststätte', 'lokal'],
            'fast_food': ['mcdonalds', 'burger king', 'subway', 'kfc'],
        },
        'shopping': {
            'amazon': ['amazon', 'amzn'],
            'ebay': ['ebay'],
            'clothing': ['h&m', 'zara', 'c&a'],
            'electronics': ['mediamarkt', 'saturn', 'cyberport'],
            'home': ['toom', 'obi', 'bauhaus', 'hornbach'],
            'drugstore': ['dm', 'rossmann', 'douglas'],
        },
        'transport': {
            'fuel': ['aral', 'shell', 'total', 'agip', 'esso', 'stark'],
            'parking': ['parking'],
            'toll': ['maut'],
        },
        'housing': {
            'rent': ['miete', 'warmmiete', 'kaltmiete'],
            'utilities': ['strom', 'gas', 'wasser', 'heizung', 'stromanbieter'],
            'internet': ['telekom', 'vodafone', 'o2', 'unitymedia'],
        },
        'insurance': {
            'health': ['krankenkasse', 'gesundheitskasse', 'allianz'],
            'car': ['kfz-versicherung', 'autoversicherung'],
            'life': ['lebensversicherung', 'risikolebensversicherung'],
        },
        'entertainment': {
            'streaming': ['netflix', 'spotify', 'prime video', 'disney+'],
            'gaming': ['steam', 'epic games', 'origin'],
            'travel': ['booking', 'expedia', 'airbnb', 'hotel'],
        },
        'health': {
            'pharmacy': ['apotheke', 'dm-drogerie'],
            'doctor': ['arzt', 'klinik', 'praxis'],
        },
        'subscriptions': {
            'software': ['adobe', 'microsoft', 'github', 'cursor', 'openai'],
            'membership': ['mitgliedschaft', 'verein', 'beitrag'],
        },
        'fees': {
            'bank_fees': ['entgelt', 'gebühr', 'spesen', 'provision'],
            'atm': ['geldautomat'],
        },
    }

    def __init__(self):
        """Initialize the cleaner."""
        self.duplicates_log: List[Dict] = []
        self.issues_log: List[Dict] = []
        self.assignments_log: Dict[str, int] = {}
        self.income_corrected = 0

    def clean(self, df: pd.DataFrame, remove_duplicates: bool = True,
              handle_missing: str = 'flag', remove_outliers: bool = False) -> Tuple[pd.DataFrame, Dict]:
        """Main cleaning pipeline.

        Args:
            df: Input DataFrame with transaction data.
            remove_duplicates: Whether to remove detected duplicates.
            handle_missing: Strategy for missing values: 'flag', 'drop', or 'keep'.
            remove_outliers: Whether to flag outliers (not remove).

        Returns:
            Tuple of (cleaned DataFrame, cleaning report dict).
        """
        df = df.copy()
        report = {
            'total_records': len(df),
            'duplicates_removed': 0,
            'duplicates_flagged': 0,
            'missing_values': {},
            'outliers_flagged': 0,
            'categories_assigned': 0,
        }
        self.income_corrected = 0

        # 1. Detect and handle duplicates
        dup_mask = self.detect_duplicates(df)
        report['duplicates_flagged'] = int(dup_mask.sum())
        if remove_duplicates:
            df = df[~dup_mask].copy()
            report['duplicates_removed'] = report['duplicates_flagged']
            logger.info(f"Removed {report['duplicates_removed']} duplicate transactions")

        # 2. Validate amounts and dates
        df = self._validate_basic(df)

        # 3. Handle missing values
        df, missing_report = self._handle_missing(df, strategy=handle_missing)
        report['missing_values'] = missing_report

        # 4. Assign categories
        df['category'] = df.apply(self._assign_category, axis=1)
        cat_counts = df['category'].value_counts().to_dict()
        report['category_distribution'] = cat_counts
        report['categories_assigned'] = int((df['category'] != 'uncategorized').sum())
        report['income_corrected'] = self.income_corrected

        # 5. Detect outliers (flag only)
        if remove_outliers:
            df['is_outlier'] = self.detect_outliers(df)
            report['outliers_flagged'] = int(df['is_outlier'].sum())

        # 6. Add derived fields
        df = self._add_derived_fields(df)

        logger.info(f"Cleaning complete. {len(df)} records retained.")
        logger.info(f"Categories assigned: {report['categories_assigned']}/{len(df)}")
        if self.income_corrected > 0:
            logger.info(f"Income corrections: {self.income_corrected}")
        return df, report

    def _assign_category(self, row: pd.Series) -> Optional[str]:
        """Assign a category to a transaction based on keywords.
        
        Uses weighted text matching (purpose/booking text count double).
        Special handling for payment service providers.
        """
        text_parts = []
        
        # Normal weight fields (counterparty, etc.)
        normal_fields = ['counterparty', 'Auftraggeber/Empfänger', 'Auftraggeber/Empf�nger', 'Auftraggeber/Empfanger']
        for field in normal_fields:
            if field in row.index and pd.notna(row[field]):
                text_parts.append(_repair_mojibake_text(row[field]).lower())
        
        # Double weight fields (purpose, booking text)
        important_fields = ['purpose', 'booking_text', 'Buchungstext', 'Verwendungszweck']
        for field in important_fields:
            if field in row.index and pd.notna(row[field]):
                val = _repair_mojibake_text(row[field]).lower()
                text_parts.append(val)
                text_parts.append(val)  # Double weight
        
        text = ' '.join(text_parts)
        if not text or text.strip() in ['nan', '']:
            return 'uncategorized'
        
        # Special regex patterns first (from special_patterns)
        for pattern, category in get_special_patterns():
            try:
                if re.search(pattern, text, re.IGNORECASE):
                    return category
            except re.error:
                continue
        
        # Generic payment provider categorization (before normal rules)
        purpose = _repair_mojibake_text(row.get('purpose', '') or row.get('Verwendungszweck', '') or '').lower()
        booking_text = _repair_mojibake_text(row.get('booking_text', '') or row.get('Buchungstext', '') or '').lower()
        
        # Find counterparty - try multiple column name variants (encoding issues in CSV)
        counterparty = ''
        for col in ['counterparty', 'Auftraggeber/Empfänger', 'Auftraggeber/Empf�nger', 'Auftraggeber/Empfanger']:
            if col in row.index and pd.notna(row.get(col)):
                counterparty = _repair_mojibake_text(row[col]).lower()
                break
        
        # Generic provider immer mit separaten Feldern aufrufen:
        # purpose + booking_text haben Vorrang, counterparty ist nur Ergaenzung/Fallback.
        result = categorize_generic_provider(
            text=counterparty,
            counterparty=counterparty,
            purpose=purpose,
            booking_text=booking_text,
        )
        if result:
            return result
        
        # Payment service provider detection
        psp_names = ['first data', 'nexi', 'otto payments', 'smartbroker']
        is_psp = any(psp in text for psp in psp_names)
        
        # Try centralized category rules
        for category, rule in CATEGORY_RULES.items():
            keywords = rule['keywords']
            match_type = rule.get('match_type', 'any')
            case_sensitive = rule.get('case_sensitive', False)
            
            search_text = text if case_sensitive else text.lower()
            
            # For PSPs, filter out generic payment keywords
            if is_psp:
                keywords = [kw for kw in keywords 
                           if not any(sk in kw.lower() for sk in ['payment', 'paypal', 'first data', 'data'])]
                if not keywords:
                    continue
            
            matched = False
            if match_type == 'any':
                for kw in keywords:
                    check_kw = kw if case_sensitive else kw.lower()
                    if check_kw in search_text:
                        matched = True
                        break
            else:  # all
                matched_all = True
                for kw in keywords:
                    check_kw = kw if case_sensitive else kw.lower()
                    if check_kw not in search_text:
                        matched_all = False
                        break
                matched = matched_all
            
            if matched:
                # Fix: Negative salary -> transfer.private
                if category == 'income.salary':
                    try:
                        amt = float(row['amount']) if 'amount' in row.index else 0
                        if amt < 0:
                            self.income_corrected += 1
                            return 'transfer.private'
                    except (ValueError, TypeError):
                        pass
                return category
        
        # Legacy fallback
        for category, subcats in self.CATEGORY_KEYWORDS.items():
            for subcat, keywords in subcats.items():
                for kw in keywords:
                    if kw in text:
                        cand = f"{category}.{subcat}"
                        if cand == 'income.salary':
                            try:
                                amt = float(row['amount']) if 'amount' in row.index else 0
                                if amt < 0:
                                    self.income_corrected += 1
                                    return 'transfer.private'
                            except (ValueError, TypeError):
                                pass
                        return cand
        
        return 'uncategorized'

    def detect_duplicates(self, df: pd.DataFrame, threshold_days: int = 1) -> pd.Series:
        """Detect potential duplicate transactions."""
        if len(df) < 2:
            return pd.Series([False] * len(df), index=df.index)
        
        df = df.copy()
        df['_amt_round'] = df['amount'].astype(float).round(2)
        
        date_col = 'value_date'
        if date_col in df.columns:
            df['_date_round'] = pd.to_datetime(df[date_col]).dt.floor('D')
        elif 'booking_date' in df.columns:
            df['_date_round'] = pd.to_datetime(df['booking_date']).dt.floor('D')
        else:
            df['_date_round'] = pd.NaT
        
        df = df.sort_values(['_date_round', '_amt_round'])
        is_dup = pd.Series([False] * len(df), index=df.index)
        
        for (date, amt), group in df.groupby(['_date_round', '_amt_round']):
            if len(group) > 1:
                parties = group['counterparty'].fillna('').str.lower().str.strip()
                if len(parties.unique()) <= 1:
                    is_dup.loc[group.index[1:]] = True
                else:
                    for i in range(len(group)):
                        for j in range(i + 1, len(group)):
                            if self._similar_strings(parties.iloc[i], parties.iloc[j]):
                                is_dup.loc[group.index[j]] = True
        
        df.drop(['_amt_round', '_date_round'], axis=1, inplace=True, errors='ignore')
        return is_dup

    def _similar_strings(self, s1: str, s2: str, threshold: float = 0.8) -> bool:
        if not s1 or not s2:
            return False
        if s1 == s2:
            return True
        max_len = max(len(s1), len(s2))
        if max_len == 0:
            return False
        common = sum(1 for a, b in zip(s1, s2) if a == b)
        return (common / max_len) >= threshold

    def _validate_basic(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        if 'amount' in df.columns:
            df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
            invalid_amt = df['amount'].isna()
            if invalid_amt.any():
                logger.warning(f"{invalid_amt.sum()} transactions with invalid amounts")
        for col in ['value_date', 'booking_date']:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        return df

    def _handle_missing(self, df: pd.DataFrame, strategy: str = 'flag') -> Tuple[pd.DataFrame, Dict]:
        missing_report = {}
        for col in df.columns:
            missing_count = df[col].isna().sum()
            if missing_count > 0:
                missing_report[col] = {'count': int(missing_count), 'percentage': round(missing_count / len(df) * 100, 2)}
        if strategy == 'drop':
            before = len(df)
            df = df.dropna(subset=['amount', 'value_date', 'booking_date']).copy()
            dropped = before - len(df)
            if dropped > 0:
                logger.info(f"Dropped {dropped} rows with missing critical values")
        elif strategy == 'flag':
            critical_cols = ['amount', 'value_date', 'booking_date']
            missing_critical = df[critical_cols].isna().any(axis=1)
            if missing_critical.any():
                df.loc[missing_critical, 'has_missing_critical'] = True
        return df, missing_report

    def _add_derived_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        if 'amount' in df.columns:
            df['txn_type'] = np.where(df['amount'] >= 0, 'income', 'expense')
            df['amount_abs'] = df['amount'].abs()
        # Add date column for downstream analysis (use value_date, fallback to booking_date)
        if 'value_date' in df.columns:
            df['date'] = df['value_date']
        elif 'booking_date' in df.columns:
            df['date'] = df['booking_date']
            
        if 'value_date' in df.columns:
            df['month'] = df['value_date'].dt.to_period('M')
            df['year'] = df['value_date'].dt.year
            df['week'] = df['value_date'].dt.isocalendar().week
            df['day_of_week'] = df['value_date'].dt.day_name()
            
        # Ensure counterparty column is populated from Auftraggeber/Empfanger (handle encoding variations)
        auftrag_col = None
        for col in df.columns:
            if 'auftrag' in col.lower():
                auftrag_col = col
                break
        if auftrag_col:
            df['counterparty'] = df['counterparty'].astype('object')
            mask = df['counterparty'].isna() | (df['counterparty'] == '')
            df.loc[mask, 'counterparty'] = df.loc[mask, auftrag_col]
        return df

    def detect_outliers(self, df: pd.DataFrame, method: str = 'iqr', column: str = 'amount_abs') -> pd.Series:
        if column not in df.columns:
            return pd.Series([False] * len(df), index=df.index)
        values = df[column].dropna()
        outliers = pd.Series([False] * len(df), index=df.index)
        if method == 'iqr':
            Q1 = values.quantile(0.25)
            Q3 = values.quantile(0.75)
            IQR = Q3 - Q1
            lower = Q1 - 1.5 * IQR
            upper = Q3 + 1.5 * IQR
            outliers.loc[df[column].notna()] = ((df[column] < lower) | (df[column] > upper))
        elif method == 'zscore':
            mean = values.mean()
            std = values.std()
            if std > 0:
                z_scores = (df[column] - mean).abs() / std
                outliers.loc[df[column].notna()] = z_scores > 3
        return outliers

    def generate_quality_report(self, df: pd.DataFrame) -> Dict:
        report = {
            'total_records': len(df),
            'columns': list(df.columns),
            'missing_values': {},
            'duplicates': int(df.duplicated().sum()) if 'is_duplicate' not in df.columns else int(df['is_duplicate'].sum()),
            'data_types': df.dtypes.astype(str).to_dict(),
        }
        for col in df.columns:
            missing = df[col].isna().sum()
            if missing > 0:
                report['missing_values'][col] = {'count': int(missing), 'percentage': round(missing / len(df) * 100, 2)}
        if 'category' in df.columns:
            report['category_distribution'] = df['category'].value_counts().to_dict()
        if 'txn_type' in df.columns:
            report['txn_type_distribution'] = df['txn_type'].value_counts().to_dict()
        return report


def main():
    from data_loader import TransactionDataLoader
    loader = TransactionDataLoader(data_dir="data")
    df = loader.load_and_standardize()
    print(f"\n=== Original Data ===")
    print(f"Records: {len(df)}")
    cleaner = TransactionCleaner()
    df_clean, report = cleaner.clean(df, remove_duplicates=True, handle_missing='flag')
    print(f"\n=== Cleaning Report ===")
    for key, value in report.items():
        print(f"{key}: {value}")
    output_path = "data/cleaned_transactions.csv"
    df_clean.to_csv(output_path, index=False)
    print(f"\nSaved to {output_path}")


if __name__ == "__main__":
    main()

