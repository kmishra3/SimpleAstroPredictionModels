#!/usr/bin/env python3
"""
Dasha Stock Price Analysis Script

Analyzes company dasha periods and correlates them with stock price performance.
Fetches historical stock data from FMP API and calculates percent changes for each completed dasha period.

Usage: python dasha_stock_analysis.py [input_csv_file] [output_csv_file]
Example: python dasha_stock_analysis.py data/Technology/LYFT_dasha_analysis.csv LYFT_Dasha_Stock_Performance.csv
"""

import pandas as pd
import requests
import json
from datetime import datetime, timedelta
import time
import sys
import os
import argparse
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np

class DashaStockAnalyzer:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://financialmodelingprep.com/api/v3"
        
    def get_price_range_data(self, symbol, start_date_str, end_date_str):
        """Get historical price data for a date range"""
        try:
            # Format dates for API
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").strftime("%Y-%m-%d")
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").strftime("%Y-%m-%d")
            
            # Construct API URL for date range
            url = f"{self.base_url}/historical-price-full/{symbol}?from={start_date}&to={end_date}&apikey={self.api_key}"
            
            response = requests.get(url)
            data = response.json()
            
            if "historical" in data and len(data["historical"]) > 0:
                return data["historical"]
            return []
            
        except Exception as e:
            print(f"Error getting price range data from {start_date_str} to {end_date_str}: {str(e)}")
            return []

    def get_nearest_trading_day_price(self, symbol, target_date_str, direction='both', max_days=5):
        """
        Get stock price for the nearest trading day, searching both before and after the target date
        direction: 'before', 'after', or 'both'
        max_days: maximum number of days to look in each direction
        """
        target_date = datetime.strptime(target_date_str, "%Y-%m-%d")
        
        if direction in ['both', 'before']:
            # Try dates before
            for i in range(max_days):
                check_date = target_date - timedelta(days=i)
                price = self.get_stock_price(symbol, check_date.strftime("%Y-%m-%d"))
                if price is not None:
                    return price
                
        if direction in ['both', 'after']:
            # Try dates after
            for i in range(1, max_days + 1):
                check_date = target_date + timedelta(days=i)
                price = self.get_stock_price(symbol, check_date.strftime("%Y-%m-%d"))
                if price is not None:
                    return price
                
        return None
        
    def get_stock_price(self, symbol, date_str):
        """Get stock price for a specific date"""
        try:
            # Convert date string to datetime
            date = datetime.strptime(date_str, "%Y-%m-%d")
            
            # Format date for API
            formatted_date = date.strftime("%Y-%m-%d")
            
            # Construct API URL
            url = f"{self.base_url}/historical-price-full/{symbol}?from={formatted_date}&to={formatted_date}&apikey={self.api_key}"
            
            response = requests.get(url)
            data = response.json()
            
            if "historical" in data and len(data["historical"]) > 0:
                return float(data["historical"][0]["close"])
            return None
            
        except Exception as e:
            print(f"Error getting stock price for {date_str}: {str(e)}")
            return None

    def analyze_period_extremes(self, price_data):
        """Analyze price highs and lows during a period"""
        if not price_data:
            return None, None, None, None
            
        # Convert to DataFrame for easier analysis
        df = pd.DataFrame(price_data)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        # Find highest and lowest prices
        high_idx = df['high'].idxmax()
        low_idx = df['low'].idxmin()
        
        period_high = df.loc[high_idx, 'high']
        period_high_date = df.loc[high_idx, 'date'].strftime("%Y-%m-%d")
        period_low = df.loc[low_idx, 'low']
        period_low_date = df.loc[low_idx, 'date'].strftime("%Y-%m-%d")
        
        return period_high, period_high_date, period_low, period_low_date

    def get_dasha_color_and_alpha(self, auspiciousness, inauspiciousness):
        """Determine color and alpha based on auspiciousness vs inauspiciousness scores"""
        diff = auspiciousness - inauspiciousness
        
        if diff > 2:
            return '#006400', 0.3  # Dark green - Very auspicious
        elif diff > 1:
            return '#32CD32', 0.25  # Light green - Moderately auspicious
        elif diff > -1:
            return '#FFD700', 0.2  # Yellow - Neutral
        elif diff > -2:
            return '#FF6B6B', 0.25  # Light red - Moderately inauspicious
        else:
            return '#8B0000', 0.3  # Dark red - Very inauspicious

    def create_stock_chart(self, all_price_data, dasha_periods, symbol):
        """Create a stock price chart with dasha period indicators"""
        if not all_price_data:
            print("No price data available for chart creation")
            return
            
        # Convert price data to DataFrame and remove duplicates
        df = pd.DataFrame(all_price_data)
        df['date'] = pd.to_datetime(df['date'])
        df = df.drop_duplicates(subset=['date']).sort_values('date')
        
        # Filter price data to only include data within the dasha period range
        min_date = dasha_periods['Date'].min()
        max_date = dasha_periods['End_Date'].max()
        df = df[(df['date'] >= min_date) & (df['date'] <= max_date)]
        
        if df.empty:
            print("No price data available within the dasha period range")
            return
        
        # Create the plot with better sizing
        fig, ax = plt.subplots(figsize=(20, 14))
        
        # Plot the stock price
        ax.plot(df['date'], df['close'], linewidth=2.5, color='#1f77b4', label=f'{symbol} Close Price', zorder=10)
        
        # Get price range for positioning text
        price_min = df['close'].min()
        price_max = df['close'].max()
        price_range = price_max - price_min
        
        # Create alternating text positions to avoid overlap
        text_positions = []
        base_offset = price_range * 0.15  # Base offset from price line
        
        # Add dasha period backgrounds with improved color coding
        labeled_periods = []  # Track periods that will get labels
        
        for _, period in dasha_periods.iterrows():
            start_date = pd.to_datetime(period['Date'])
            end_date = pd.to_datetime(period['End_Date'])
            
            # Get color and alpha based on auspiciousness scores
            color, alpha = self.get_dasha_color_and_alpha(period['Auspiciousness'], period['Inauspiciousness'])
            
            # Add background color
            ax.axvspan(start_date, end_date, alpha=alpha, color=color, zorder=1)
            
            # Add vertical lines at boundaries for clarity
            ax.axvline(start_date, color='black', alpha=0.3, linewidth=0.8, zorder=5)
            ax.axvline(end_date, color='black', alpha=0.3, linewidth=0.8, zorder=5)
            
            # Check if this period should get a label
            period_days = (end_date - start_date).days
            if period_days > 30:  # Only label periods longer than 30 days
                labeled_periods.append((period, start_date, end_date, color, period_days))
        
        # Sort labeled periods by duration (longest first) to prioritize important periods
        labeled_periods.sort(key=lambda x: x[4], reverse=True)
        
        # Position text labels with smart positioning
        used_positions = []  # Track used text positions to avoid overlap
        
        for i, (period, start_date, end_date, color, period_days) in enumerate(labeled_periods):
            # Only show text for periods longer than 45 days to avoid crowding
            if period_days <= 45:
                continue
                
            mid_date = start_date + (end_date - start_date) / 2
            period_data = df[df['date'].between(start_date, end_date)]
            
            if not period_data.empty:
                # Determine label based on color
                if color == '#006400':
                    label = 'Very Auspicious'
                elif color == '#32CD32':
                    label = 'Auspicious'
                elif color == '#FFD700':
                    label = 'Neutral'
                elif color == '#FF6B6B':
                    label = 'Inauspicious'
                else:
                    label = 'Very Inauspicious'
                
                # Calculate average price in this period for baseline positioning
                avg_price = period_data['close'].mean()
                
                # Smart positioning algorithm
                # Try different vertical positions to avoid overlap
                potential_positions = [
                    avg_price + base_offset,  # Above average
                    avg_price - base_offset,  # Below average
                    price_max - base_offset * 0.5,  # Near top
                    price_min + base_offset * 0.5,  # Near bottom
                    avg_price + base_offset * 1.5,  # Higher above
                    avg_price - base_offset * 1.5,  # Lower below
                ]
                
                # Find the best position that doesn't overlap with existing text
                best_position = None
                min_distance = 0
                
                for pos in potential_positions:
                    # Check distance from existing text positions
                    min_dist_to_existing = float('inf')
                    for used_mid, used_pos in used_positions:
                        date_dist = abs((mid_date - used_mid).days)
                        price_dist = abs(pos - used_pos)
                        
                        # Combine date and price distance for overlap detection
                        combined_dist = date_dist / 30.0 + price_dist / (base_offset * 0.5)
                        min_dist_to_existing = min(min_dist_to_existing, combined_dist)
                    
                    # Choose position with maximum distance from existing text
                    if min_dist_to_existing > min_distance:
                        min_distance = min_dist_to_existing
                        best_position = pos
                
                # If no good position found, use alternating strategy
                if best_position is None or min_distance < 2.0:
                    # Alternate between upper and lower positions
                    if len(used_positions) % 2 == 0:
                        best_position = price_max - base_offset * (0.3 + 0.2 * (len(used_positions) // 2))
                    else:
                        best_position = price_min + base_offset * (0.3 + 0.2 * (len(used_positions) // 2))
                
                # Ensure position is within chart bounds
                best_position = max(price_min - base_offset * 0.2, 
                                   min(price_max + base_offset * 0.2, best_position))
                
                # Add the text with improved styling
                text_obj = ax.text(mid_date, best_position, 
                                  f"{period['Maha_Lord']}-{period['Antar_Lord']}\n{label}", 
                                  ha='center', va='center', fontsize=10, fontweight='bold',
                                  bbox=dict(boxstyle="round,pad=0.4", facecolor='white', 
                                           alpha=0.95, edgecolor='gray', linewidth=1),
                                  zorder=15)
                
                # Store this position to avoid future overlaps
                used_positions.append((mid_date, best_position))
                
                # Add a subtle line connecting text to the period if text is far from price line
                price_in_period = period_data['close'].iloc[len(period_data)//2] if len(period_data) > 0 else avg_price
                if abs(best_position - price_in_period) > base_offset * 0.8:
                    ax.annotate('', xy=(mid_date, price_in_period), 
                               xytext=(mid_date, best_position),
                               arrowprops=dict(arrowstyle='-', color='gray', alpha=0.5, lw=1),
                               zorder=12)
        
        # Formatting
        ax.set_title(f'{symbol} Stock Price with Vedic Dasha Periods', fontsize=22, fontweight='bold', pad=30)
        ax.set_xlabel('Date', fontsize=18)
        ax.set_ylabel('Price ($)', fontsize=18)
        ax.grid(True, alpha=0.3, zorder=2)
        
        # Improve x-axis formatting based on data range
        date_range = (df['date'].max() - df['date'].min()).days
        
        if date_range > 1800:  # More than 5 years
            ax.xaxis.set_major_locator(mdates.YearLocator())
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
            ax.xaxis.set_minor_locator(mdates.MonthLocator((1, 7)))
        elif date_range > 730:  # More than 2 years
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            ax.xaxis.set_minor_locator(mdates.MonthLocator())
        elif date_range > 365:  # More than 1 year
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            ax.xaxis.set_minor_locator(mdates.MonthLocator())
        else:  # Less than 1 year
            ax.xaxis.set_major_locator(mdates.MonthLocator())
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            ax.xaxis.set_minor_locator(mdates.WeekdayLocator())
        
        # Rotate labels and set proper spacing
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # Set axis limits to focus on the data with extra space for text
        ax.set_xlim(df['date'].min() - pd.Timedelta(days=15), 
                   df['date'].max() + pd.Timedelta(days=15))
        
        # Add extra padding to y-axis for text labels
        y_padding = price_range * 0.25  # Increased padding for text
        ax.set_ylim(price_min - y_padding, price_max + y_padding)
        
        # Add enhanced legend with color coding
        from matplotlib.patches import Patch
        legend_elements = [
            plt.Line2D([0], [0], color='#1f77b4', lw=3, label=f'{symbol} Price'),
            Patch(facecolor='#006400', alpha=0.3, label='Very Auspicious (>+2)'),
            Patch(facecolor='#32CD32', alpha=0.25, label='Auspicious (+1 to +2)'),
            Patch(facecolor='#FFD700', alpha=0.2, label='Neutral (-1 to +1)'),
            Patch(facecolor='#FF6B6B', alpha=0.25, label='Inauspicious (-1 to -2)'),
            Patch(facecolor='#8B0000', alpha=0.3, label='Very Inauspicious (<-2)')
        ]
        ax.legend(handles=legend_elements, loc='upper left', fontsize=13, framealpha=0.95)
        
        # Adjust layout to prevent label cutoff
        plt.tight_layout()
        
        # Save the chart with better DPI
        chart_filename = f"{symbol}_Dasha_Stock_Chart.png"
        plt.savefig(chart_filename, dpi=300, bbox_inches='tight', facecolor='white')
        print(f"Chart saved to {chart_filename}")
        plt.close()  # Close the figure to free memory

    def get_symbol_from_filename(self, filename):
        """Extract and map company symbol from filename"""
        base_name = os.path.basename(filename)
        
        # Symbol mapping for common company names to their stock tickers
        symbol_mapping = {
            'Palantir': 'PLTR',
            'Palantir_Technologies': 'PLTR',
            'Palantir_Technologies_Inc': 'PLTR',
            'LYFT': 'LYFT',
            'Lyft': 'LYFT',
            'Microsoft': 'MSFT',
            'Apple': 'AAPL',
            'Google': 'GOOGL',
            'Amazon': 'AMZN',
            'Tesla': 'TSLA'
        }
        
        # Try to extract symbol from filename
        # First, try exact matches with the mapping
        for company_name, ticker in symbol_mapping.items():
            if company_name.lower() in base_name.lower():
                print(f"Mapped company name '{company_name}' to ticker '{ticker}'")
                return ticker
        
        # If no mapping found, use the first part of the filename
        symbol = base_name.split('_')[0]
        print(f"Using symbol '{symbol}' from filename")
        return symbol

    def process_dasha_periods(self, input_file, output_file=None):
        """Process dasha periods from input CSV file"""
        try:
            # Read the input CSV file
            df = pd.read_csv(input_file)
            
            # Sort by date
            df['Date'] = pd.to_datetime(df['Date'])
            df = df.sort_values('Date')
            
            # Get company symbol from the filename with proper mapping
            symbol = self.get_symbol_from_filename(input_file)
            
            # Get current date and birth date
            current_date = datetime.now()
            birth_date = pd.to_datetime(df['Birth_Date'].iloc[0])
            
            # Set a reasonable cutoff date (30 years from birth or current date, whichever is earlier)
            cutoff_date = min(current_date, birth_date + pd.DateOffset(years=30))
            
            # Filter out any periods that start beyond the cutoff date
            df = df[df['Date'] <= cutoff_date].copy()
            
            # Check if End_Date column exists, if not create it
            if 'End_Date' not in df.columns:
                print("End_Date column not found, calculating from period transitions...")
                # Calculate end dates based on next period start
                df['End_Date'] = df['Date'].shift(-1)
                # For the last period, don't extend to current date unless it's reasonable
                if pd.isna(df['End_Date'].iloc[-1]):
                    # Exclude the last period if we can't determine its end
                    print("Excluding last period as it appears to be incomplete or current")
                    df = df.iloc[:-1].copy()
            else:
                # Handle existing End_Date column as before
                df['Original_End_Date'] = df['End_Date']  # Save original end dates
                
                # Calculate proper end dates based on next period start
                df['End_Date'] = df['Date'].shift(-1)
                
                # For periods where we have original end dates that are different from calculated ones,
                # and where the original end date is reasonable, prefer the original
                for idx in df.index:
                    original_end = pd.to_datetime(df.loc[idx, 'Original_End_Date'])
                    calculated_end = df.loc[idx, 'End_Date']
                    
                    # If we have a valid original end date that's not too far in the future
                    if pd.notna(original_end) and original_end <= cutoff_date:
                        # Check if there's a significant difference
                        if pd.isna(calculated_end) or abs((original_end - calculated_end).days) > 5:
                            df.loc[idx, 'End_Date'] = original_end
                
                # For the last row, handle carefully
                if pd.isna(df['End_Date'].iloc[-1]):
                    last_original_end = pd.to_datetime(df['Original_End_Date'].iloc[-1])
                    if pd.notna(last_original_end) and last_original_end < current_date:
                        # Use the original end date if it's in the past
                        df.loc[df.index[-1], 'End_Date'] = last_original_end
                    else:
                        # Don't automatically extend to current date
                        # This period should be excluded as it's likely incomplete
                        df = df.iloc[:-1].copy()
                        print(f"Excluding last period as it appears to be incomplete or current")
            
            # Filter for ONLY completely elapsed periods
            # A period is elapsed if its end date is strictly before current date
            elapsed_periods = df[df['End_Date'] < current_date].copy()
            
            # Additional check: remove any period where the end date equals current date
            # unless we're confident it actually ended today
            today = current_date.date()
            elapsed_periods = elapsed_periods[elapsed_periods['End_Date'].dt.date != today].copy()
            
            if len(elapsed_periods) == 0:
                print("No completely elapsed dasha periods found")
                return None
                
            print(f"Processing {len(elapsed_periods)} elapsed dasha periods...")
            print(f"Date range: {elapsed_periods['Date'].min().strftime('%Y-%m-%d')} to {elapsed_periods['End_Date'].max().strftime('%Y-%m-%d')}")
            
            # Store all price data for charting
            all_price_data = []
            
            # Calculate stock performance for each elapsed period
            results = []
            for idx, row in elapsed_periods.iterrows():
                start_date = row['Date'].strftime("%Y-%m-%d")
                end_date = pd.to_datetime(row['End_Date']).strftime("%Y-%m-%d")
                
                print(f"Processing period: {start_date} to {end_date}")
                
                # Get price range data for the entire period
                period_price_data = self.get_price_range_data(symbol, start_date, end_date)
                all_price_data.extend(period_price_data)
                
                # Get start and end prices
                start_price = self.get_nearest_trading_day_price(symbol, start_date, direction='after')
                end_price = self.get_nearest_trading_day_price(symbol, end_date, direction='before')
                
                # Analyze period extremes
                period_high, period_high_date, period_low, period_low_date = self.analyze_period_extremes(period_price_data)
                
                if start_price and end_price:
                    percent_change = ((end_price - start_price) / start_price) * 100
                else:
                    percent_change = None
                    if not start_price:
                        print(f"Warning: No start price found for period starting {start_date}")
                    if not end_price:
                        print(f"Warning: No end price found for period ending {end_date}")
                
                result = row.to_dict()
                result['Start_Price'] = start_price
                result['End_Price'] = end_price
                result['Percent_Change'] = percent_change
                result['Period_High'] = period_high
                result['Period_High_Date'] = period_high_date
                result['Period_Low'] = period_low
                result['Period_Low_Date'] = period_low_date
                results.append(result)
                
                # Add delay to avoid API rate limits
                time.sleep(0.5)
            
            # Create output DataFrame
            output_df = pd.DataFrame(results)
            
            # Define column order with new columns
            columns = [
                'Date', 'Maha_Lord', 'Antar_Lord', 'Prayant_Lord', 
                'Maha_Strength', 'Antar_Strength', 'Prayant_Strength',
                'Auspiciousness', 'Inauspiciousness', 'Active_Status',
                'Entity', 'Birth_Date', 'End_Date', 'Start_Price',
                'End_Price', 'Percent_Change', 'Period_High', 'Period_High_Date',
                'Period_Low', 'Period_Low_Date'
            ]
            
            # Only include columns that exist in the data
            available_columns = [col for col in columns if col in output_df.columns]
            output_df = output_df[available_columns]
            
            # Format dates
            output_df['End_Date'] = pd.to_datetime(output_df['End_Date']).dt.strftime('%Y-%m-%d')
            
            # Save to CSV
            if output_file is None:
                # Use the actual symbol for the default output filename
                output_file = f"{symbol}_Dasha_Stock_Performance.csv"
            output_df.to_csv(output_file, index=False)
            print(f"Analysis saved to {output_file}")
            
            # Create visualization
            print("Creating stock price chart...")
            self.create_stock_chart(all_price_data, elapsed_periods, symbol)
            
            return output_df
            
        except Exception as e:
            print(f"Error processing dasha periods: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

def main():
    parser = argparse.ArgumentParser(description='Analyze stock performance for dasha periods')
    parser.add_argument('input_file', help='Input CSV file with dasha analysis')
    parser.add_argument('--output', '-o', help='Output CSV file name', default=None)
    args = parser.parse_args()
    
    api_key = "xfdfuV6azioH4OBRuFQvnovkwJMC2cqn"
    analyzer = DashaStockAnalyzer(api_key)
    analyzer.process_dasha_periods(args.input_file, args.output)

if __name__ == "__main__":
    main()