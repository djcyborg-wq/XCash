#!/usr/bin/env python3
"""Exploratory Data Analysis for financial transactions."""

import pandas as pd
import numpy as np
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class TransactionEDA:
    """Performs exploratory data analysis on transaction data."""

    def __init__(self, df: pd.DataFrame):
        """Initialize with transaction DataFrame.
        
        Args:
            df: DataFrame with transaction data
        """
        self.df = df.copy()
        self._validate_data()

    def _validate_data(self) -> None:
        """Validate that required columns are present."""
        if 'amount' not in self.df.columns:
            raise ValueError("DataFrame must contain 'amount' column")

        # Ensure we have a date column
        date_col = None
        for col in ['value_date', 'booking_date', 'date']:
            if col in self.df.columns:
                date_col = col
                break

        if date_col is None:
            raise ValueError(
                "DataFrame must contain a date column "
                "(value_date, booking_date, or date)"
            )

        # Standardize date column name
        if date_col != 'date':
            if 'date' not in self.df.columns:
                self.df = self.df.rename(columns={date_col: 'date'})
            else:
                # date column already exists, drop the duplicate source column
                self.df = self.df.drop(columns=[date_col])

        # Ensure date is datetime
        self.df['date'] = pd.to_datetime(self.df['date'], errors='coerce')

        # Ensure amount is numeric
        self.df['amount'] = pd.to_numeric(self.df['amount'], errors='coerce')

    def run_full_analysis(self) -> Dict:
        """Run complete EDA pipeline.
        
        Returns:
            Dictionary containing all analysis results.
        """
        results = {}
        results['overview'] = self._get_overview()
        results['date_analysis'] = self._analyze_by_date()
        results['category_analysis'] = self._analyze_by_category()
        results['anomaly_detection'] = self._detect_outliers()
        
        logger.info("EDA analysis complete")
        return results

    def _get_overview(self) -> Dict[str, Any]:
        """Get basic overview statistics."""
        total_income = self.df[self.df['amount'] > 0]['amount'].sum()
        total_expense = self.df[self.df['amount'] < 0]['amount'].sum()
        net_flow = total_income + total_expense
        
        income_count = (self.df['amount'] > 0).sum()
        expense_count = (self.df['amount'] < 0).sum()
        
        return {
            'total_transactions': len(self.df),
            'total_income': total_income,
            'total_expense': total_expense,
            'net_cash_flow': net_flow,
            'income_count': income_count,
            'expense_count': expense_count,
            'savings_rate': (net_flow / total_income * 100) if total_income != 0 else 0,
            'date_range': {
                'start': self.df['date'].min().strftime('%Y-%m-%d'),
                'end': self.df['date'].max().strftime('%Y-%m-%d')
            } if self.df['date'].notna().any() else None,
        }

    def _analyze_by_date(self) -> Dict[str, Any]:
        """Analyze transactions by date."""
        if not self.df['date'].notna().any():
            return {'error': 'No valid dates available'}
        
        df = self.df.dropna(subset=['date']).copy()
        df['month'] = df['date'].dt.to_period('M')
        df['year'] = df['date'].dt.year
        df['month_num'] = df['date'].dt.month
        df['day_of_week'] = df['date'].dt.day_name()
        df['week'] = df['date'].dt.isocalendar().week
        
        monthly = df.groupby('month').agg({
            'amount': ['sum', 'mean', 'count']
        }).round(2)
        monthly.columns = ['total', 'avg', 'count']
        
        weekly = df.groupby(['year', 'week']).agg({
            'amount': ['sum', 'count']
        }).round(2)
        
        daily_pattern = df.groupby('day_of_week')['amount'].agg(['sum', 'count']).round(2)
        
        # Daily transactions
        daily_trans = df.groupby(df['date'].dt.date).size().to_dict()
        daily_trans = {str(k): v for k, v in daily_trans.items()}
        
        return {
            'monthly_summary': monthly.to_dict('index'),
            'weekly_summary': weekly.to_dict('index'),
            'daily_pattern': daily_pattern.to_dict('index'),
            'daily_transactions': daily_trans,
        }

    def _analyze_by_category(self) -> Dict[str, Any]:
        """Analyze transactions by category."""
        categories = self.df[self.df['amount'] < 0].groupby('category')['amount'].agg([
            ('total', 'sum'),
            ('avg', 'mean'),
            ('count', 'count'),
            ('max', 'min')
        ]).round(2).sort_values('total')
        
        top_categories = categories.head(10).to_dict('index')
        
        income_categories = self.df[self.df['amount'] > 0].groupby('category')['amount'].agg([
            ('total', 'sum'),
            ('count', 'count')
        ]).round(2).sort_values('total', ascending=False)
        
        top_income = income_categories.head(10).to_dict('index')
        
        return {
            'top_expense_categories': top_categories,
            'top_income_categories': top_income,
        }

    def _detect_outliers(self) -> Dict[str, Any]:
        """Detect outliers in transaction amounts."""
        valid_amounts = self.df['amount'].dropna()
        
        if len(valid_amounts) < 3:
            return {'error': 'Not enough data for outlier detection'}
        
        Q1 = valid_amounts.quantile(0.25)
        Q3 = valid_amounts.quantile(0.75)
        IQR = Q3 - Q1
        lower = Q1 - 1.5 * IQR
        upper = Q3 + 1.5 * IQR
        
        outliers = self.df[
            (self.df['amount'] < lower) | (self.df['amount'] > upper)
        ].copy()
        
        top_outliers = outliers.nlargest(10, 'amount_abs')[['date', 'amount', 'category', 'counterparty']]
        
        return {
            'outlier_count': len(outliers),
            'lower_bound': lower,
            'upper_bound': upper,
            'outlier_transactions': top_outliers.to_dict('records')
        }

    def get_summary_report(self) -> str:
        """Generate a formatted summary report."""
        results = self.run_full_analysis()
        
        if 'error' in results.get('overview', {}):
            return "Error generating report"
        
        overview = results['overview']
        
        lines = []
        lines.append("=" * 60)
        lines.append("TRANSACTION DATA ANALYSIS REPORT")
        lines.append("=" * 60)
        lines.append("")
        lines.append("--- Overview ---")
        lines.append(f"Total Transactions: {overview['total_transactions']}")
        lines.append(f"Date Range: {overview['date_range']['start']} to {overview['date_range']['end']}")
        lines.append(f"Total Income: {overview['total_income']:,.2f} EUR")
        lines.append(f"Total Expenses: {overview['total_expense']:,.2f} EUR")
        lines.append(f"Net Cash Flow: {overview['net_cash_flow']:,.2f} EUR")
        lines.append(f"Savings Rate: {overview['savings_rate']:.2f}%")
        lines.append("")
        
        # Top expense categories
        cat_results = results.get('category_analysis', {})
        if 'top_expense_categories' in cat_results:
            lines.append("--- Top Expense Categories ---")
            for cat, stats in list(cat_results['top_expense_categories'].items())[:10]:
                lines.append(f"  {cat}: {stats['total']:,.2f} EUR ({stats['count']} transactions)")
            lines.append("")
        
        return "\n".join(lines)


def main():
    """Main function to run EDA."""
    from data_loader import TransactionDataLoader
    
    loader = TransactionDataLoader(data_dir="data")
    df = loader.load_and_standardize()
    
    eda = TransactionEDA(df)
    print(eda.get_summary_report())
    
    results = eda.run_full_analysis()
    
    # Save results
    import json
    
    class NumpyEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, (int, float, str, type(None))):
                return obj
            elif hasattr(obj, 'item'):
                return obj.item()
            return str(obj)
    
    with open('outputs/eda_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str, ensure_ascii=False)
    
    print("\nResults saved to outputs/eda_results.json")


if __name__ == "__main__":
    main()

