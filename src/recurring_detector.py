"""Recurring payments detector.

Detects fixed costs, subscriptions, and regular payments from transaction data.
Uses only pandas and standard library.
"""

import pandas as pd
import numpy as np
import re
from typing import List


def normalize_counterparty(text) -> str:
    """Normalize counterparty name for grouping.

    Steps:
    1. Lowercase
    2. Remove numbers and special characters
    3. Remove common stopwords (gmbh, ag, sepa, visa, etc.)
    4. Collapse whitespace

    Args:
        text: Original counterparty name.

    Returns:
        Normalized name for grouping.
    """
    if not isinstance(text, str) or not text.strip():
        return "unknown"

    # Lowercase
    t = str(text).lower().strip()

    # Remove numbers
    t = re.sub(r'\d+', '', t)

    # Remove special characters (keep spaces and letters)
    t = re.sub(r'[^a-z\s]', ' ', t)

    # Stopwords to remove
    stopwords = {
        'gmbh', 'ag', 'sepa', 'visa', 'ug', 'gruppe', 'deutschland', 'de',
        'kg', 'ohg', 'partg', 'mbh', 'co', 'kgaa', 'ltd', 'inc', 'corp',
        'ab', 'sa', 'nv', 'bv', 'spa', 'srl', 'oy', 'as', 'aps',
        'sarl', 'e.u.', 'b.v.', 'n.v.', 's.p.a.', 's.c.', 's.n.c.',
        's.s.', 'p.c.', 'v.o.f.', 'l.p.', 's.a.', 's.r.o.', 'g.b.r.',
        'a.b.', 'aktiengesellschaft', 'gesellschaft', 'firma',
        'unternehmen', 'betrieb', 'handel', 'service', 'gruppe',
        'verein', 'e.v.', 'eingetragener', 'verein', 'genossenschaft',
        'e.g.', 'u.g.', 'ohg', 'kgaa', 'gmbh co', 'kg'
    }

    words = [w for w in t.split() if w not in stopwords and len(w) > 2]
    t = ' '.join(words)
    t = re.sub(r'\s+', ' ', t).strip()

    return t if t else "unknown"


def amounts_match(amounts: List[float]) -> bool:
    """Check if all amounts are similar (±2 EUR or ±5%).

    Args:
        amounts: List of amounts to compare.

    Returns:
        True if all amounts are within tolerance.
    """
    if len(amounts) < 2:
        return True

    for i in range(len(amounts)):
        for j in range(i + 1, len(amounts)):
            a1, a2 = abs(amounts[i]), abs(amounts[j])
            abs_diff = abs(a1 - a2)
            rel_diff = abs_diff / a1 if a1 != 0 else float('inf')

            if not (abs_diff <= 2 or rel_diff <= 0.05):
                return False

    return True


def calculate_frequency(dates: List[pd.Timestamp]) -> str:
    """Determine payment frequency based on date differences.

    Args:
        dates: Sorted list of transaction dates.

    Returns:
        'monthly', 'weekly', or 'irregular'.
    """
    if len(dates) < 3:
        return "irregular"

    diffs = []
    for i in range(1, len(dates)):
        diff = (dates[i] - dates[i - 1]).days
        if diff > 0:
            diffs.append(diff)

    if not diffs:
        return "irregular"

    # Check monthly (25-35 days)
    monthly_count = sum(1 for d in diffs if 25 <= d <= 35)
    if monthly_count >= len(diffs) * 0.6:  # At least 60% monthly
        return "monthly"

    # Check weekly (6-8 days)
    weekly_count = sum(1 for d in diffs if 6 <= d <= 8)
    if weekly_count >= len(diffs) * 0.6:  # At least 60% weekly
        return "weekly"

    return "irregular"


def calculate_confidence(amounts: List[float], dates: List[pd.Timestamp], frequency: str) -> float:
    """Calculate confidence score for recurring payment detection.

    Score components:
    - Amount consistency (std / mean): up to 50%
    - Temporal consistency (frequency match): up to 50%

    Args:
        amounts: List of transaction amounts.
        dates: List of transaction dates.
        frequency: Detected frequency.

    Returns:
        Confidence score between 0 and 1.
    """
    if len(amounts) < 2:
        return 0.5

    # Amount consistency
    mean_amount = np.mean(amounts)
    if mean_amount != 0:
        amount_cv = np.std(amounts) / abs(mean_amount)
        amount_score = max(0, 1 - amount_cv)  # Lower CV = higher score
    else:
        amount_score = 0.5

    # Temporal consistency
    if len(dates) >= 3:
        diffs = [(dates[i] - dates[i - 1]).days for i in range(1, len(dates))
                 if (dates[i] - dates[i - 1]).days > 0]
        if diffs:
            avg_diff = np.mean(diffs)
            if frequency == "monthly":
                temporal_score = max(0, 1 - abs(avg_diff - 30) / 30)
            elif frequency == "weekly":
                temporal_score = max(0, 1 - abs(avg_diff - 7) / 7)
            else:
                temporal_score = 0.3
        else:
            temporal_score = 0.3
    else:
        temporal_score = 0.3

    confidence = 0.5 * amount_score + 0.5 * temporal_score
    return round(min(max(confidence, 0), 1), 2)


def detect_recurring_payments(df: pd.DataFrame) -> pd.DataFrame:
    """Detect recurring payments from transaction data.

    Args:
        df: DataFrame with columns including date, amount, counterparty/auftraggeber, category.

    Returns:
        DataFrame with recurring payment groups.
    """
    # Determine date column
    if 'date' in df.columns:
        date_col = 'date'
    elif 'booking_date' in df.columns:
        date_col = 'booking_date'
    else:
        raise ValueError("No date column found. Need 'date' or 'booking_date'.")

    # Prepare data
    df = df.copy()
    # Handle German umlaut in column name
    if 'Auftraggeber/Empf\ufffdnger' not in df.columns and 'Auftraggeber/Empfänger' not in df.columns:
        # Try to find any similar column
        for col in df.columns:
            if 'auftrag' in col.lower() or 'empf' in col.lower():
                df = df.rename(columns={col: 'Auftraggeber/Empf\ufffdnger'})
                break

    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce')

    # Drop rows with missing critical data
    df = df.dropna(subset=[date_col, 'amount', 'category'])

    if len(df) == 0:
        return pd.DataFrame(columns=[
            'counterparty', 'normalized_counterparty', 'category',
            'avg_amount', 'std_amount', 'occurrences',
            'frequency', 'first_date', 'last_date', 'confidence'
        ])

    # Determine counterparty source column
    if 'counterparty' in df.columns and df['counterparty'].notna().any():
        # Use counterparty if available and has values
        counter_vals = df['counterparty'].notna().sum()
        auftrag_vals = df['Auftraggeber/Empf\ufffdnger'].notna().sum() if 'Auftraggeber/Empf\ufffdnger' in df.columns else 0
        if counter_vals >= auftrag_vals:
            text_col = 'counterparty'
        else:
            text_col = 'Auftraggeber/Empf\ufffdnger'
    elif 'Auftraggeber/Empf\ufffdnger' in df.columns:
        text_col = 'Auftraggeber/Empf\ufffdnger'
    elif 'counterparty' in df.columns:
        text_col = 'counterparty'
    else:
        text_col = df.columns[2]  # fallback

    # Normalize counterparty
    df['normalized_counterparty'] = df[text_col].apply(normalize_counterparty)

    # Group by normalized counterparty and category
    groups = df.groupby(['normalized_counterparty', 'category'])

    results = []

    for (norm_name, category), group in groups:
        if len(group) < 3:
            continue

        # Sort by date
        group = group.sort_values(date_col)
        dates = group[date_col].tolist()
        amounts = group['amount'].abs().tolist()  # Use absolute for comparison
        original_values = group[text_col].tolist()

        # Check amount similarity
        if not amounts_match(amounts):
            continue

        # Determine frequency
        frequency = calculate_frequency(dates)

        # For monthly/weekly: need valid gaps
        if frequency in ['monthly', 'weekly']:
            diffs = [(dates[i] - dates[i - 1]).days for i in range(1, len(dates))]
            if frequency == 'monthly':
                valid_diffs = [d for d in diffs if 25 <= d <= 35]
                if len(valid_diffs) < 2:
                    continue
            elif frequency == 'weekly':
                valid_diffs = [d for d in diffs if 6 <= d <= 8]
                if len(valid_diffs) < 2:
                    continue

        # Calculate confidence
        confidence = calculate_confidence(amounts, dates, frequency)

        # Only include if confidence is reasonable
        if confidence < 0.35:
            continue

        # Use most common original value
        main_name = max(set(original_values), key=original_values.count)

        results.append({
            'counterparty': main_name,
            'normalized_counterparty': norm_name,
            'category': category,
            'avg_amount': round(np.mean(amounts), 2),
            'std_amount': round(np.std(amounts), 2),
            'occurrences': len(group),
            'frequency': frequency,
            'first_date': dates[0].strftime('%Y-%m-%d'),
            'last_date': dates[-1].strftime('%Y-%m-%d'),
            'confidence': confidence
        })

    result_df = pd.DataFrame(results)

    if len(result_df) > 0:
        result_df = result_df.sort_values('avg_amount', ascending=False).reset_index(drop=True)

    return result_df


def save_recurring_payments(recurring_df: pd.DataFrame, output_path: str = 'outputs/recurring_payments.csv'):
    """Save recurring payments to CSV.

    Args:
        recurring_df: DataFrame with recurring payment data.
        output_path: Path to save CSV file.
    """
    recurring_df.to_csv(output_path, index=False, encoding='utf-8')
    print(f"Saved recurring payments to {output_path}")


def print_summary(recurring_df: pd.DataFrame):
    """Print summary of recurring payments.

    Args:
        recurring_df: DataFrame with recurring payment data.
    """
    print()
    print("=" * 70)
    print("RECURRING PAYMENTS SUMMARY")
    print("=" * 70)
    print()
    print(f"Total recurring payments found: {len(recurring_df)}")
    print()

    if len(recurring_df) == 0:
        print("No recurring payments detected.")
        return

    # Top 10 by amount
    print("-" * 70)
    print("TOP 10 BY AVERAGE AMOUNT:")
    print("-" * 70)
    top10_amount = recurring_df.nlargest(10, 'avg_amount')
    for i, row in enumerate(top10_amount.itertuples(), 1):
        print(f"{i:>3}. {row.counterparty:<40} {row.avg_amount:>10.2f} EUR  ({row.occurrences}x {row.frequency})")

    print()

    # Top 10 by occurrences
    print("-" * 70)
    print("TOP 10 BY OCCURRENCES:")
    print("-" * 70)
    top10_occur = recurring_df.nlargest(10, 'occurrences')
    for i, row in enumerate(top10_occur.itertuples(), 1):
        print(f"{i:>3}. {row.counterparty:<40} {row.occurrences:>4}x  {row.avg_amount:>10.2f} EUR  ({row.frequency})")

    print()
    print("=" * 70)


if __name__ == "__main__":
    df = pd.read_csv('data/final_transactions.csv', encoding='utf-8')
    recurring = detect_recurring_payments(df)
    save_recurring_payments(recurring)
    print_summary(recurring)
