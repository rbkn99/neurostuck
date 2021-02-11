import pandas as pd
from os import listdir


def list_files(directory, extension):
    return (f for f in listdir(directory) if f.endswith('.' + extension))


csv_files = list_files('data', 'csv')
df = pd.DataFrame()
for file in csv_files:
    chunk_df = pd.read_csv('data/' + file, sep='\t', index_col=None)
    df = df.append(chunk_df)

df.drop(df.columns.difference(['Title', 'Url', 'Pairings', 'Content']), 1, inplace=True)
df.to_csv('data/all_pages.csv', sep='\t', index=False)
