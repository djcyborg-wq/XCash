import pandas as pd
df = pd.read_csv('data/final_transactions.csv')
print('=== TOP 20 KATEGORIEN ===')
print(df['category'].value_counts().head(20))
print()
print('=== UNCATEGORIZED ===')
print(f'Anzahl: {len(df[df["category"] == "uncategorized"])}')
print()
print('=== VISA BEISPIELE ===')
visa = df[df['counterparty'].str.contains('visa', case=False, na=False) | df['booking_text'].str.contains('visa', case=False, na=False)]
print(visa[['counterparty', 'booking_text', 'purpose', 'amount', 'category']].head(10).to_string())
print()
print('=== PAYPAL BEISPIELE ===')
pp = df[df['counterparty'].str.contains('paypal', case=False, na=False)]
print(pp[['counterparty', 'booking_text', 'purpose', 'amount', 'category']].head(10).to_string())
print()
print('=== ING BEISPIELE ===')
ing = df[df['counterparty'].str.contains('ing', case=False, na=False)]
print(ing[['counterparty', 'booking_text', 'purpose', 'amount', 'category']].head(10).to_string())