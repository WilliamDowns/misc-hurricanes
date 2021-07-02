#currently finds earliest calendar year timesteps for each 5kt TC intensity through 160kt

import pandas as pd

with open('hurdat2-1851-2020-052921.txt', 'r') as f:
    contents = f.readlines()
    drop_lines = [l for l in range(len(contents)) if contents[l][:2] == 'AL']

df = pd.read_csv('hurdat2-1851-2020-052921.txt', 
                 names=['date', 'time', 'spec', 'state', 'lat', 
                        'lon', 'wind', 'pres', 'ne34', 'se34', 'sw34', 
                        'nw34', 'ne50', 'se50', 'sw50', 'nw50', 'ne64', 
                        'se64', 'sw64', 'nw64'], 
                 usecols=['date', 'time', 'lat', 'lon', 'wind', 'pres'], 
                 skipinitialspace=True)

df = df.drop(drop_lines)

earliests = {n : 1231 for n in range(35,165,5)}

for k in earliests.keys():
    data = df.where(df['wind'] >= k).dropna()
    data = data.sort_values(by=['date', 'time'], key=lambda col: col.astype('int')%2000)
    earliests[k]=data[0:1]['date']
print(earliests)
    
