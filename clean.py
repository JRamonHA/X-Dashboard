import glob
import pandas as pd
from simpledbf import Dbf5

dbf_files = glob.glob('data/*.dbf')
keys = [f'PC{i+1}' for i in range(len(dbf_files))]

dataframes = []
for file, key in zip(dbf_files, keys):
    dbf = Dbf5(file)
    df_temp = dbf.to_dataframe()
    dataframes.append(df_temp)

df = pd.concat(dataframes, axis=1, keys=keys)

for pc in df.columns.levels[0]:
    df[(pc, 'hora_original')] = df[(pc, 'hora')].copy()
    df[(pc, 'hora')] = df[(pc, 'hora')].replace(24, 0)
    mask = df[(pc, 'hora_original')] == 24
    df.loc[mask, (pc, 'fecha')] = df.loc[mask, (pc, 'fecha')] + pd.Timedelta(days=1)
    df.drop((pc, 'hora_original'), axis=1, inplace=True)

for pc in df.columns.levels[0]:
    df[(pc, 'Fecha')] = pd.to_datetime(
        df[(pc, 'fecha')].astype(str) + ' ' +
        df[(pc, 'hora')].astype(str) + ':' +
        df[(pc, 'min')].astype(str)
    )

df['Fecha'] = df.iloc[:, df.columns.get_level_values(1) == 'Fecha'].iloc[:, 0]
df.set_index('Fecha', inplace=True)
df.drop(columns=df.columns[df.columns.get_level_values(1).isin(['fecha', 'hora', 'min', 'Fecha'])], inplace=True)

df = df.loc[:, df.columns.get_level_values(1) == 'kwh']
df.columns = df.columns.droplevel(1)
df = df[df.index < '2024-01-01']

df.to_csv('consumo_kwh.csv')