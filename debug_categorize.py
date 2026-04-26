import pandas as pd
from src.category_rules import categorize_generic_provider

# Check row data
df = pd.read_csv('data/final_transactions.csv')
row = df.iloc[66]  # VISA CURSOR row
print('Row data:')
print('counterparty:', row.get('counterparty'))
print('purpose:', row.get('purpose'))
print('booking_text:', row.get('booking_text'))
print('Buchungstext:', row.get('Buchungstext'))
print()

# Test the function directly
purpose = str(row.get('purpose', '') or '').lower()
booking_text = str(row.get('booking_text', '') or row.get('Buchungstext', '') or '').lower()
counterparty = str(row.get('counterparty', '') or '').lower()
combined = purpose + ' ' + booking_text + ' ' + counterparty
combined = combined.strip()
print('Combined text:', combined[:150])
print()
result = categorize_generic_provider(combined, counterparty, purpose, booking_text)
print('Result:', result)