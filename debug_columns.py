import pandas as pd

# Load the final transactions file
df = pd.read_csv("data/final_transactions.csv")
print("Columns in final_transactions.csv:")
print(df.columns.tolist())
print()
print("First few rows:")
print(df.head())
print()
print("Data types:")
print(df.dtypes)