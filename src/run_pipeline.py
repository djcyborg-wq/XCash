#!/usr/bin/env python3
"""Main pipeline runner for transaction analysis.

Orchestrates the complete analysis pipeline:
1. Data loading and standardization
2. Data cleaning and deduplication
3. Exploratory data analysis
4. (Placeholder) Clustering and anomaly detection
5. (Placeholder) Forecasting
6. (Placeholder) Visualization and reporting
"""

import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('outputs/pipeline.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def main():
    """Run the complete transaction analysis pipeline."""
    logger.info("=" * 60)
    logger.info("Starting Transaction Analysis Pipeline")
    logger.info("=" * 60)

    # Ensure output directories exist
    for d in ['outputs', 'models', 'notebooks']:
        Path(d).mkdir(exist_ok=True)

    try:
        # Phase 1: Data Loading
        logger.info("\n--- Phase 1: Data Loading and Standardization ---")
        from data_loader import TransactionDataLoader
        loader = TransactionDataLoader(data_dir="data")
        files = loader.discover_files()
        if not files:
            logger.error("No CSV files found in data/ directory")
            sys.exit(1)

        catalog = loader.build_metadata_catalog(files)
        logger.info(f"Cataloged {len(catalog)} files")

        df = loader.load_and_standardize()
        logger.info(f"Loaded {len(df)} total transactions")

        # Save raw combined data
        raw_output = "data/raw_combined.csv"
        df.to_csv(raw_output, index=False)
        logger.info(f"Saved raw combined data to {raw_output}")

        # Phase 2: Data Cleaning
        logger.info("\n--- Phase 2: Data Cleaning ---")
        from data_cleaner import TransactionCleaner
        cleaner = TransactionCleaner()
        df_clean, clean_report = cleaner.clean(
            df, remove_duplicates=True, handle_missing='flag'
        )
        logger.info(f"Cleaned dataset: {len(df_clean)} transactions")
        logger.info(f"Duplicates removed: {clean_report['duplicates_removed']}")

        # Save cleaned data
        clean_output = "data/cleaned_transactions.csv"
        df_clean.to_csv(clean_output, index=False)
        logger.info(f"Saved cleaned data to {clean_output}")

        # Save cleaning report
        import json
        with open('outputs/cleaning_report.json', 'w') as f:
            json.dump(clean_report, f, indent=2, default=str)

        # Phase 3: Exploratory Data Analysis (Basic)
        logger.info("\n--- Phase 3: Exploratory Data Analysis ---")
        from eda import TransactionEDA
        eda = TransactionEDA(df_clean)
        eda_results = eda.run_full_analysis()

        print("\n" + eda.get_summary_report())

        # Save EDA results
        class NumpyEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, (int, float, str)):
                    return obj
                elif hasattr(obj, 'item'):
                    return obj.item()
                return str(obj)
        
        def convert_to_serializable(obj):
            """Recursively convert numpy/pandas types to JSON-serializable types."""
            import numpy as np
            import pandas as pd
            
            if isinstance(obj, (str, int, float, bool, type(None))):
                return obj
            elif isinstance(obj, dict):
                return {str(k): convert_to_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, (list, tuple, np.ndarray, pd.Series)):
                return [convert_to_serializable(v) for v in obj]
            elif isinstance(obj, (np.integer,)):
                return int(obj)
            elif isinstance(obj, (np.floating,)):
                return float(obj)
            elif hasattr(obj, 'item'):
                return obj.item()
            else:
                return str(obj)
        
        with open('outputs/eda_results.json', 'w') as f:
            json.dump(convert_to_serializable(eda_results), f, indent=2)
        logger.info("Saved EDA results to outputs/eda_results.json")

        # Phase 4: Clustering (Basic categorization already done)
        logger.info("\n--- Phase 4: Transaction Categorization ---")
        cat_counts = df_clean['category'].value_counts()
        logger.info(f"Categorized {len(cat_counts)} unique categories")
        logger.info("Top 10 categories:")
        for cat, count in cat_counts.head(10).items():
            logger.info(f"  {cat}: {count} transactions")

        # Phase 5: Save Final Dataset
        logger.info("\n--- Phase 5: Save Processed Dataset ---")
        final_output = "data/final_transactions.csv"
        df_clean.to_csv(final_output, index=False)
        logger.info(f"Saved final dataset to {final_output}")

        # Phase 6: Recurring Payments Detection
        logger.info("\n--- Phase 6: Recurring Payments Detection ---")
        from recurring_detector import detect_recurring_payments, save_recurring_payments, print_summary
        recurring_df = detect_recurring_payments(df_clean)
        save_recurring_payments(recurring_df)
        logger.info(f"Detected {len(recurring_df)} recurring payment groups")

        # Print summary to console
        print_summary(recurring_df)

        # Phase 7: Anomaly Detection
        logger.info("\n--- Phase 7: Anomaly Detection ---")
        from anomaly_detector import detect_all_anomalies, save_anomalies, print_anomaly_summary
        anomalies_df = detect_all_anomalies(df_clean)
        save_anomalies(anomalies_df)
        logger.info(f"Detected {len(anomalies_df)} anomalies")
        
        # Print summary to console
        print_anomaly_summary(anomalies_df)

        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("Pipeline Complete!")
        logger.info("=" * 60)
        logger.info(f"Output files:")
        logger.info(f"  - data/raw_combined.csv")
        logger.info(f"  - data/cleaned_transactions.csv")
        logger.info(f"  - data/final_transactions.csv")
        logger.info(f"  - outputs/cleaning_report.json")
        logger.info(f"  - outputs/eda_results.json")
        logger.info(f"  - outputs/recurring_payments.csv")
        logger.info(f"  - outputs/anomalies.csv")
        logger.info(f"  - outputs/pipeline.log")

    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
