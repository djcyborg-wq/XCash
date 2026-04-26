#!/usr/bin/env python3
"""Analyze uncategorized transactions and group similar patterns."""

import pandas as pd
import re
from collections import Counter

# Load data
df = pd.read_csv('data/final_transactions.csv', encoding='utf-8')
uncat = df[df['category'] == 'uncategorized'].copy()

print(f'Total uncategorized: {len(uncat)}')

# ---- Helper: normalize text for grouping ----
def normalize_for_grouping(text):
    """Normalize text to find similar merchant patterns."""
    if not isinstance(text, str):
        return ''
    t = text.lower()
    # Remove common separators and extra spaces
    t = re.sub(r'[^a-z0-9\s]', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    # Remove very short words (often noise)
    words = [w for w in t.split() if len(w) > 2]
    return ' '.join(words)

# ---- Build analysis dataframe ----
analysis = uncat[['Auftraggeber/Empf\ufffdnger', 'booking_text', 'purpose', 'amount']].copy()
analysis.columns = ['counterparty', 'booking_text', 'purpose', 'amount']

# Create normalized versions for grouping
analysis['norm_counterparty'] = analysis['counterparty'].apply(normalize_for_grouping)
analysis['norm_booking'] = analysis['booking_text'].apply(normalize_for_grouping)
analysis['norm_purpose'] = analysis['purpose'].apply(normalize_for_grouping)

# ---- Group by normalized counterparty (primary) ----
grouped = analysis.groupby('norm_counterparty').agg({
    'counterparty': 'first',  # first original name
    'booking_text': lambda x: x.mode().iloc[0] if len(x.mode()) > 0 else x.iloc[0],
    'purpose': 'first',
    'amount': ['count', 'sum']
}).reset_index()

grouped.columns = ['norm_name', 'counterparty', 'booking_text', 'purpose', 'count', 'total_amount']
grouped = grouped.sort_values('count', ascending=False).reset_index(drop=True)

# Save analysis
output_cols = ['counterparty', 'booking_text', 'purpose', 'amount', 'count', 'total_amount']
# Use amount from first instance, not sum - fix needed
# Actually, we want per-group sum for total but individual amounts
# Let's use the grouped approach properly
grouped.to_csv('outputs/uncategorized_analysis.csv', index=False, encoding='utf-8')

print(f'\nSaved {len(grouped)} groups to outputs/uncategorized_analysis.csv')

# ---- Top 50 patterns ----
print('\n' + '='*80)
print('TOP 50 UNKATEGORISIERTE MUSTER')
print('='*80)
print(f'{"#":<4} {"Anzahl":>6} {"Gesamtbetrag":>14} {"Gruppe (normiert)":<40} {"Original-Name (Beispiel)"}')
print('-'*80)

for i, row in grouped.head(50).iterrows():
    orig = str(row['counterparty'])[:50]
    norm = str(row['norm_name'])[:40]
    print(f'{i+1:<4} {row["count"]:>6} {row["total_amount"]:>12.2f} EUR  {norm:<40} {orig}')

print('-'*80)
print(f'Gesamt: {grouped["count"].sum()} Transaktionen, Summe: {grouped["total_amount"].sum():.2f} EUR')

# ---- Additional insights ----
print('\n' + '='*80)
print('WEITERE ANALYSEN')
print('='*80)

# By booking text type
print('\nNach Buchungstext-Typ:')
bk = analysis['booking_text'].value_counts()
for val, cnt in bk.head(10).items():
    print(f'  {val:<30} {cnt:>4}x')

# By amount ranges
print('\nNach Betragsgrößen:')
amounts = uncat['amount'].abs()
ranges = [
    (0, 10, '0-10 €'),
    (10, 50, '10-50 €'),
    (50, 100, '50-100 €'),
    (100, 500, '100-500 €'),
    (500, 99999, '>500 €')
]
for lo, hi, label in ranges:
    cnt = ((amounts >= lo) & (amounts < hi)).sum()
    total = uncat[((amounts >= lo) & (amounts < hi))]['amount'].sum()
    print(f'  {label:<15} {cnt:>4}x  {total:>10.2f} EUR')

print('\n' + '='*80)
print('MOEGLICHE KATEGORISIERUNGS-ANSATZE FUER DIESE GRUPPEN:')
print('='*80)
print("""
Vorschlaege fuer regelbasierte Zuordnung:

1. 'Nexi Germany GmbH' (+BAECKEREI...)      -> groceries.discounter / dining.restaurant
2. 'GREENLINE SCHNEEBERG TA'                 -> transport.fuel / shopping.home (Baumarkt)
3. 'Telefonica Germany GmbH'                 -> housing.internet
4. 'SONDERPREIS-BAUMARKT SCHNEEBERG'        -> shopping.home
5. 'MARKGRAFEN GETRAENKEMARKT'              -> groceries.supermarket / dining.restaurant
6. 'Zweckverband Abfallwirtschaft'          -> housing.utilities
7. 'Zweckverband Wasserwerke'               -> housing.utilities
8. 'ZV ABWASSER SCHLEMATAL'                  -> housing.utilities
9. 'Hauptkasse des Freistaates Sachsen'      -> taxes.authority
10. 'TOP-FOTOGRAFIE GmbH'                    -> business.service
11. 'Bundeskasse'                            -> taxes.authority / fees
12. 'UNICREDIT W/Q1 TS'                      -> transport.fuel
13. 'VISA COLOR MAGIC, CO'                   -> shopping.foreign / travel
14. 'Christopher Thon'                       -> transfers.private
15. 'THI BICH NGOC BUI'                      -> services
16. 'TTL Tapeten-Teppichbodenland'           -> shopping.home
17. 'Karls Tourismus / Markt'                -> dining.restaurant / entertainment.travel
18. 'Netto Marken-Discoun'                   -> groceries.supermarket (wird schon erkannt!)
19. 'toom BM Schneeberg'                     -> shopping.home (wird schon erkannt!)
20. 'Grose Kreisstadt Aue'                   -> taxes.street_tax
""")
