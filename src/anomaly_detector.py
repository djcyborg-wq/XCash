#!/usr/bin/env python3
"""Anomaly detection for financial transactions.

Implements simple statistical and rule-based anomaly detection without ML.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)

def load_transactions(filepath="data/final_transactions.csv"):
    """Load transactions from CSV, handling date column."""
    df = pd.read_csv(filepath, encoding='utf-8')
    
    # Use booking_date if date column doesn't exist
    if 'date' not in df.columns and 'booking_date' in df.columns:
        df['date'] = df['booking_date']
    elif 'date' not in df.columns:
        raise ValueError("Neither 'date' nor 'booking_date' column found")
    
    # Ensure date is datetime
    df['date'] = pd.to_datetime(df['date'])
    
    return df

def category_amount_outlier(df):
    """Detect outliers in transaction amounts per category using MAD.
    
    Args:
        df: DataFrame with columns ['category', 'amount', 'date']
        
    Returns:
        DataFrame with anomaly flags and reasons
    """
    anomalies = []
    
    # Only consider categories with at least 10 transactions (was 5)
    # Exclude 'uncategorized' category
    category_counts = df['category'].value_counts()
    valid_categories = [c for c in category_counts[category_counts >= 10].index 
                       if c != 'uncategorized']
    
    # Determine counterparty column for display
    if 'counterparty' in df.columns and df['counterparty'].notna().any():
        display_col = 'counterparty'
    elif 'Auftraggeber/Empfanger' in df.columns:
        display_col = 'Auftraggeber/Empfanger'
    elif 'counterparty' in df.columns:
        display_col = 'counterparty'
    else:
        display_col = None
    
    for category in valid_categories:
        cat_df = df[df['category'] == category]
        amounts = cat_df['amount'].values
        
        # Calculate median and MAD (Median Absolute Deviation)
        median = np.median(amounts)
        mad = np.median(np.abs(amounts - median))
        
        # Avoid division by zero
        if mad == 0:
            mad = np.std(amounts) if np.std(amounts) > 0 else 1
            
        # Modified Z-score using MAD
        modified_z_scores = 0.6745 * (amounts - median) / mad
        
        for idx, (_, row) in enumerate(cat_df.iterrows()):
            abs_z = np.abs(modified_z_scores[idx])
            
            # Determine severity based on deviation
            if abs_z > 5:  # More than 5x median
                severity = 'high'
            elif abs_z > 3:  # More than 3x median
                severity = 'medium'
            else:
                severity = 'low'
            
            # Only flag as outlier if deviation > 3 (modified z-score)
            if abs_z > 3:
                # Get display counterparty name
                if display_col and display_col in row.index:
                    display_val = row[display_col]
                    if pd.isna(display_val) or display_val == '':
                        display_val = row.get('counterparty', '')
                else:
                    display_val = row.get('counterparty', '')
                
                anomalies.append({
                    'index': row.name,
                    'date': row['date'],
                    'counterparty': display_val,
                    'category': row['category'],
                    'amount': row['amount'],
                    'anomaly_type': 'category_amount_outlier',
                    'severity': severity,
                    'reason': f'Amount {row["amount"]:.2f} EUR deviates from category median {median:.2f} EUR (MAD={mad:.2f}, {abs_z:.1f}x)',
                    'confidence': min(0.95, 0.5 + abs_z / 10)
                })
    
    return pd.DataFrame(anomalies)

def merchant_amount_outlier(df):
    """Detect outliers in transaction amounts per merchant (counterparty).
    
    Args:
        df: DataFrame with transaction data
        
    Returns:
        DataFrame with anomaly flags and reasons
    """
    anomalies = []
    
    # Determine which column to use for counterparty
    text_col = None
    if 'counterparty' in df.columns and df['counterparty'].notna().any():
        text_col = 'counterparty'
    elif 'Auftraggeber/Empfanger' in df.columns:
        text_col = 'Auftraggeber/Empfanger'
    elif 'counterparty' in df.columns:
        text_col = 'counterparty'
    else:
        return pd.DataFrame(anomalies)
    
    # Normalize counterparty: handle NaN, uppercase and strip whitespace
    df_norm = df.copy()
    df_norm['counterparty_norm'] = df_norm[text_col].fillna('').astype(str).str.upper().str.strip()
    
    # Remove empty counterparties
    df_norm = df_norm[df_norm['counterparty_norm'] != '']
    
    # Payment service providers to ignore (they bundle multiple merchants)
    psp_keywords = ['paypal', 'amazon payment', 'first data', 'nexi']
    
    # Only consider merchants with at least 5 transactions (was 3)
    merchant_counts = df_norm['counterparty_norm'].value_counts()
    valid_merchants = [m for m in merchant_counts[merchant_counts >= 5].index
                       if not any(psp in m.lower() for psp in psp_keywords)]
    
    for merchant in valid_merchants:
        merchant_df = df_norm[df_norm['counterparty_norm'] == merchant]
        amounts = merchant_df['amount'].values
        
        if len(amounts) < 5:
            continue
        
        # Calculate median and MAD
        median = np.median(amounts)
        mad = np.median(np.abs(amounts - median))
        
        # Avoid division by zero
        if mad == 0:
            mad = np.std(amounts) if np.std(amounts) > 0 else 1
            
        # Modified Z-score
        modified_z_scores = 0.6745 * (amounts - median) / mad
        
        # Flag as outlier if modified Z-score > 3.5
        outlier_threshold = 3.5
        outlier_mask = np.abs(modified_z_scores) > outlier_threshold
        
        for idx, (_, row) in enumerate(merchant_df.iterrows()):
            if outlier_mask[idx]:
                display_name = row[text_col]
                if pd.isna(display_name) or display_name == '':
                    display_name = row['counterparty_norm']
                anomalies.append({
                    'index': row.name,
                    'date': row['date'],
                    'counterparty': display_name,
                    'category': row['category'],
                    'amount': row['amount'],
                    'anomaly_type': 'merchant_amount_outlier',
                    'severity': 'low',
                    'reason': f'Amount {row["amount"]:.2f} EUR deviates from merchant median {median:.2f} EUR (MAD={mad:.2f})',
                    'confidence': min(0.9, 0.4 + np.abs(modified_z_scores[idx]) / 15)
                })
    
    return pd.DataFrame(anomalies)

def possible_duplicate_charge(df):
    """Detect possible duplicate charges based on similar counterparty, amount, and date.
    
    Args:
        df: DataFrame with columns ['date', 'counterparty', 'amount']
        
    Returns:
        DataFrame with anomaly flags and reasons
    """
    anomalies = []
    
    # Determine which column to use for counterparty
    if 'counterparty' in df.columns and df['counterparty'].notna().any():
        text_col = 'counterparty'
    elif 'Auftraggeber/Empfanger' in df.columns:
        text_col = 'Auftraggeber/Empfanger'
    elif 'counterparty' in df.columns:
        text_col = 'counterparty'
    else:
        return pd.DataFrame(anomalies)
    
    # Sort by date for efficient comparison
    df_sorted = df.sort_values('date').reset_index(drop=True)
    
    # Precompute normalized counterparty (handle NaN)
    df_sorted['counterparty_norm'] = df_sorted[text_col].fillna('').astype(str).str.upper().str.strip()
    
    # Only process rows with non-empty counterparty
    df_sorted = df_sorted[df_sorted['counterparty_norm'] != '']
    
    # Categories where similar amounts at nearby dates are NORMAL (not duplicates)
    exclude_categories = {
        'groceries.supermarket',
        'shopping.amazon',
        'dining.bakery',
        'transport.fuel',
        'uncategorized'
    }
    
    # Compare each transaction with others within 2 days window (was 3)
    for i in range(len(df_sorted)):
        row_i = df_sorted.iloc[i]
        date_i = row_i['date']
        category_i = str(row_i.get('category', ''))
        
        # Skip excluded categories
        if category_i in exclude_categories:
            continue
        
        # Look forward only to avoid duplicate pairs and self-comparison
        for j in range(i+1, len(df_sorted)):
            row_j = df_sorted.iloc[j]
            date_j = row_j['date']
            category_j = str(row_j.get('category', ''))
            
            # Skip excluded categories
            if category_j in exclude_categories:
                continue
            
            # Break if date difference > 2 days (stricter: was 3)
            if (date_j - date_i).days > 2:
                break
                
            # Skip if same transaction
            if row_i.name == row_j.name:
                continue
                
            # Check counterparty similarity (exact match after normalization)
            if row_i['counterparty_norm'] != row_j['counterparty_norm']:
                continue
                
            # Check amount similarity: diff <= 1 EUR (stricter: was 2 EUR or 5%)
            amount_i = row_i['amount']
            amount_j = row_j['amount']
            abs_diff = abs(amount_i - amount_j)
            
            if abs_diff <= 1.0:
                display_name = row_j[text_col]
                if pd.isna(display_name) or display_name == '':
                    display_name = row_j['counterparty_norm']
                anomalies.append({
                    'index': row_j.name,
                    'date': row_j['date'],
                    'counterparty': display_name,
                    'category': row_j['category'],
                    'amount': row_j['amount'],
                    'anomaly_type': 'possible_duplicate_charge',
                    'severity': 'high',
                    'reason': f'Possible duplicate: {amount_i:.2f} EUR on {date_i.date()} (diff: {abs_diff:.2f} EUR)',
                    'confidence': 0.95
                })
    
    return pd.DataFrame(anomalies)

def large_single_transaction(df):
    """Detect large single transactions (expenses > 1000 EUR).
    
    Args:
        df: DataFrame with transaction data
        
    Returns:
        DataFrame with anomaly flags and reasons
    """
    anomalies = []
    
    # Only consider expenses (negative amounts)
    expense_df = df[df['amount'] < 0].copy()
    
    # Categories to ignore (these are expected to have large amounts)
    ignore_categories = {
        'finance.investment',
        'transfer.private',
        'income.salary'
    }
    
    # Determine counterparty column for display
    if 'counterparty' in df.columns and df['counterparty'].notna().any():
        display_col = 'counterparty'
    elif 'Auftraggeber/Empfanger' in df.columns:
        display_col = 'Auftraggeber/Empfanger'
    elif 'counterparty' in df.columns:
        display_col = 'counterparty'
    else:
        display_col = None
    
    for idx, row in expense_df.iterrows():
        category = row.get('category', '')
        
        # Skip ignored categories
        if category in ignore_categories:
            continue
        
        if abs(row['amount']) > 1000:
            # Get display counterparty name
            if display_col and display_col in row.index:
                display_val = row[display_col]
                if pd.isna(display_val) or display_val == '':
                    display_val = row.get('counterparty', '')
            else:
                display_val = row.get('counterparty', '')
            
            anomalies.append({
                'index': idx,
                'date': row['date'],
                'counterparty': display_val,
                'category': row['category'],
                'amount': row['amount'],
                'anomaly_type': 'large_single_transaction',
                'severity': 'high',
                'reason': f'Large expense: {abs(row["amount"]):.2f} EUR > 1000 EUR threshold',
                'confidence': 0.95
            })
    
    return pd.DataFrame(anomalies)

def detect_all_anomalies(df):
    """Run all anomaly detection checks and combine results.
    
    Args:
        df: DataFrame with transaction data
        
    Returns:
        DataFrame with all anomalies, sorted by severity and confidence
    """
    logger.info("Starting anomaly detection...")
    
    # Run each detection method
    dfs = []
    
    logger.info("Checking category amount outliers...")
    cat_anomalies = category_amount_outlier(df)
    if not cat_anomalies.empty:
        dfs.append(cat_anomalies)
        logger.info(f"Found {len(cat_anomalies)} category amount outliers")
    
    logger.info("Checking merchant amount outliers...")
    merchant_anomalies = merchant_amount_outlier(df)
    if not merchant_anomalies.empty:
        dfs.append(merchant_anomalies)
        logger.info(f"Found {len(merchant_anomalies)} merchant amount outliers")
    
    logger.info("Checking for possible duplicate charges...")
    dup_anomalies = possible_duplicate_charge(df)
    if not dup_anomalies.empty:
        dfs.append(dup_anomalies)
        logger.info(f"Found {len(dup_anomalies)} possible duplicate charges")
    
    logger.info("Checking for large single transactions...")
    large_anomalies = large_single_transaction(df)
    if not large_anomalies.empty:
        dfs.append(large_anomalies)
        logger.info(f"Found {len(large_anomalies)} large single transactions")
    
    # Combine all anomalies
    if dfs:
        anomalies_df = pd.concat(dfs, ignore_index=True)
        
        # Remove duplicates (same transaction flagged by multiple methods)
        # Keep the one with highest severity and confidence
        anomalies_df['severity_rank'] = anomalies_df['severity'].map({'low': 1, 'medium': 2, 'high': 3})
        anomalies_df = anomalies_df.sort_values(
            ['index', 'severity_rank', 'confidence'], 
            ascending=[True, False, False]
        )
        anomalies_df = anomalies_df.drop_duplicates(subset=['index'], keep='first')
        anomalies_df = anomalies_df.drop(columns=['severity_rank'])
        
        # Sort by severity (high first) and confidence
        anomalies_df = anomalies_df.sort_values(
            ['severity', 'confidence'], 
            ascending=[False, False]
        ).reset_index(drop=True)
        
        logger.info(f"Total unique anomalies found: {len(anomalies_df)}")
        return anomalies_df
    else:
        logger.info("No anomalies found")
        return pd.DataFrame(columns=[
            'date', 'counterparty', 'category', 'amount', 
            'anomaly_type', 'severity', 'reason', 'confidence'
        ])

def save_anomalies(anomalies_df, output_path="outputs/anomalies.csv"):
    """Save anomalies to CSV file.
    
    Args:
        anomalies_df: DataFrame with anomalies
        output_path: Path to save CSV
    """
    # Ensure output directory exists
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    # Select and order columns for output
    output_cols = ['date', 'counterparty', 'category', 'amount', 
                   'anomaly_type', 'severity', 'reason', 'confidence']
    
    # Save CSV
    if anomalies_df.empty:
        anomalies_df = pd.DataFrame(columns=output_cols)
    
    anomalies_df[output_cols].to_csv(output_path, index=False)
    logger.info(f"Anomalies saved to {output_path}")
    
    # Save JSON summary
    summary_path = output_path.replace('.csv', '_summary.json')
    summary = {
        'generated_at': datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
        'total_anomalies': int(len(anomalies_df)),
        'anomalies_by_type': {},
        'anomalies_by_severity': {},
        'top_high_severity': []
    }
    
    if not anomalies_df.empty:
        # Count by type
        for atype, count in anomalies_df['anomaly_type'].value_counts().items():
            summary['anomalies_by_type'][atype] = int(count)
        
        # Count by severity
        for sev in ['high', 'medium', 'low']:
            count = int((anomalies_df['severity'] == sev).sum())
            summary['anomalies_by_severity'][sev] = count
        
        # Top 10 high severity
        high_df = anomalies_df[anomalies_df['severity'] == 'high'].head(10)
        for _, row in high_df.iterrows():
            summary['top_high_severity'].append({
                'date': str(row['date'].date()),
                'counterparty': str(row['counterparty']),
                'amount': float(row['amount']),
                'category': str(row['category']),
                'reason': str(row['reason']),
                'confidence': float(row['confidence'])
            })
    
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Anomaly summary saved to {summary_path}")

def print_anomaly_summary(anomalies_df):
    """Print summary of anomalies to console.
    
    Args:
        anomalies_df: DataFrame with anomalies
    """
    print("\n" + "="*60)
    print("ANOMALY DETECTION SUMMARY")
    print("="*60)
    
    if anomalies_df.empty:
        print("No anomalies detected.")
        return
    
    # Total count
    print(f"Total anomalies detected: {len(anomalies_df)}")
    
    # Count by anomaly type
    print("\nBy anomaly type:")
    type_counts = anomalies_df['anomaly_type'].value_counts()
    for anomaly_type, count in type_counts.items():
        print(f"  {anomaly_type}: {count}")
    
    # Count by severity
    print("\nBy severity:")
    severity_counts = anomalies_df['severity'].value_counts()
    for severity in ['high', 'medium', 'low']:
        count = severity_counts.get(severity, 0)
        print(f"  {severity}: {count}")
    
    # Top 10 high severity anomalies
    print("\nTop 10 high severity anomalies:")
    high_severity = anomalies_df[anomalies_df['severity'] == 'high'].head(10)
    if high_severity.empty:
        print("  No high severity anomalies found.")
    else:
        for idx, (_, row) in enumerate(high_severity.iterrows(), 1):
            print(f"  {idx}. {row['date'].date()} | {row['counterparty']} | {row['amount']:8.2f} EUR | {row['anomaly_type']}")
            print(f"      Reason: {row['reason']}")
            print(f"      Confidence: {row['confidence']:.2f}")

def main():
    """Main function to run anomaly detection."""
    try:
        # Load transactions
        df = load_transactions()
        logger.info(f"Loaded {len(df)} transactions for anomaly detection")
        
        # Detect anomalies
        anomalies_df = detect_all_anomalies(df)
        
        # Save anomalies
        save_anomalies(anomalies_df)
        
        # Print summary
        print_anomaly_summary(anomalies_df)
        
        return anomalies_df
        
    except Exception as e:
        logger.error(f"Anomaly detection failed: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    # Configure logging if run directly
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('outputs/pipeline.log'),
            logging.StreamHandler()
        ]
    )
    main()