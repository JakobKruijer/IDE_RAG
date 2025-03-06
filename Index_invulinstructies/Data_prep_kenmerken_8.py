import pandas as pd

# Read the Excel file (set fourth row as header)
df = pd.read_excel("./Data/invulinstructies.xlsx", header=0)

# reset index
df.reset_index(drop=True, inplace=True)

# keep only relevant columns
df = df[["Identificatie", "Naam", "Generieke invulinstructie"]]

df.dropna(subset=['Generieke invulinstructie'], inplace=True)

print(df.head())
print(len(df))

# Rename columns
df.rename(columns={'Generieke invulinstructie': 'Invulinstructie',
                   'Naam': 'Object'}, inplace=True)

# Save the resulting DataFrame to an Excel file
df.to_excel("./Index_invulinstructies/data/invulinstructies_formatted.xlsx", index=False)