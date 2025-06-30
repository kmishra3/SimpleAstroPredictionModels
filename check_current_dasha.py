#!/usr/bin/env python3
"""
Quick script to check which dasha periods should be considered elapsed vs current
"""

import pandas as pd
from datetime import datetime

# Read the current CSV file
df = pd.read_csv('LYFT_Dasha_Stock_Performance.csv')
df['Date'] = pd.to_datetime(df['Date'])
df['End_Date'] = pd.to_datetime(df['End_Date'])

current_date = datetime.now()
print(f"Current date: {current_date.strftime('%Y-%m-%d')}")
print(f"Total periods in file: {len(df)}")

# Find which period we should currently be in
current_period_found = False
elapsed_count = 0
future_count = 0

print("\nAnalyzing all periods:")
for i, row in df.iterrows():
    start_date = row['Date']
    end_date = row['End_Date']
    
    if start_date <= current_date <= end_date:
        status = "CURRENT (ongoing)"
        current_period_found = True
    elif end_date < current_date:
        status = "ELAPSED"
        elapsed_count += 1
    else:
        status = "FUTURE"
        future_count += 1
    
    # Only print last 10 periods and any current period
    if i >= len(df) - 10 or status == "CURRENT (ongoing)":
        print(f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')} - {row['Maha_Lord']}-{row['Antar_Lord']}-{row['Prayant_Lord']} - {status}")

print(f"\nSummary:")
print(f"Elapsed periods: {elapsed_count}")
print(f"Future periods: {future_count}")
print(f"Current period found: {current_period_found}")

# Check for gaps
if not current_period_found:
    last_elapsed = df[df['End_Date'] < current_date].iloc[-1] if elapsed_count > 0 else None
    first_future = df[df['Date'] > current_date].iloc[0] if future_count > 0 else None
    
    if last_elapsed is not None:
        print(f"Last elapsed period ended: {last_elapsed['End_Date'].strftime('%Y-%m-%d')}")
    if first_future is not None:
        print(f"Next future period starts: {first_future['Date'].strftime('%Y-%m-%d')}")
    
    if last_elapsed is not None and first_future is not None:
        gap_days = (first_future['Date'] - last_elapsed['End_Date']).days
        print(f"Gap between periods: {gap_days} days")
        
        if gap_days > 0:
            print(f"We appear to be in a gap period from {last_elapsed['End_Date'].strftime('%Y-%m-%d')} to {first_future['Date'].strftime('%Y-%m-%d')}") 