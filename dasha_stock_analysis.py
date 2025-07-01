#!/usr/bin/env python3
"""
Enhanced Dasha Stock Price Analysis Script - Multi-House System Support

Analyzes company dasha periods across different house systems and correlates them with stock price performance.
Uses local JSON stock data files instead of external API calls.

Usage: python dasha_stock_analysis.py [analysis_folder_path] [optional: house_systems]
Example: python dasha_stock_analysis.py analysis/PLTR lagna,chandra_lagna
"""

import pandas as pd
import json
from datetime import datetime, timedelta
import time
import sys
import os
import argparse
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
from pathlib import Path

class EnhancedDashaStockAnalyzer:
    def __init__(self):
        self.stock_data = {}
        self.stock_symbol = None
        
    def load_stock_data_from_json(self, symbol):
        """Load stock data from local JSON file"""
        json_files = []
        
        # Search for the symbol in all sector folders
        data_path = Path("data")
        if data_path.exists():
            for sector_folder in data_path.iterdir():
                if sector_folder.is_dir():
                    json_file = sector_folder / f"{symbol}.json"
                    if json_file.exists():
                        json_files.append(json_file)
        
        if not json_files:
            print(f"❌ Error: Could not find {symbol}.json in any data folder")
            return False
            
        # Use the first matching file
        json_file = json_files[0]
        print(f"📁 Loading stock data from: {json_file}")
        
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            self.stock_symbol = data['symbol']
            stock_data = data.get('stockData', {})
            
            if not stock_data:
                print(f"❌ Error: No stock data found in {json_file}")
                return False
            
            # Convert to the format expected by the rest of the script
            self.stock_data = {}
            for date_str, day_data in stock_data.items():
                if day_data.get('price') is not None:
                    self.stock_data[date_str] = {
                        'price': float(day_data['price']),
                        'volume': day_data.get('volume', 0),
                        'date': date_str
                    }
            
            print(f"✅ Loaded {len(self.stock_data)} trading days of data for {symbol}")
            
            # Show data range
            dates = sorted(self.stock_data.keys())
            if dates:
                print(f"📅 Data range: {dates[0]} to {dates[-1]}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error loading {json_file}: {str(e)}")
            return False

    def get_nearest_trading_day_price(self, target_date):
        """Get stock price for the nearest trading day to the target date"""
        target_date_str = target_date.strftime('%Y-%m-%d')
        
        # Check if we have data for the exact date
        if target_date_str in self.stock_data:
            return self.stock_data[target_date_str]['price']
        
        # Find the nearest trading day
        all_dates = sorted(self.stock_data.keys())
        target_datetime = datetime.strptime(target_date_str, '%Y-%m-%d')
        
        # Find the closest date
        closest_date = None
        min_diff = float('inf')
        
        for date_str in all_dates:
            date_datetime = datetime.strptime(date_str, '%Y-%m-%d')
            diff = abs((target_datetime - date_datetime).days)
            if diff < min_diff:
                min_diff = diff
                closest_date = date_str
        
        if closest_date and min_diff <= 7:  # Within a week
            return self.stock_data[closest_date]['price']
        
        return None

    def calculate_period_performance(self, start_date, end_date):
        """Calculate performance metrics for a dasha period"""
        try:
            start_price = self.get_nearest_trading_day_price(start_date)
            end_price = self.get_nearest_trading_day_price(end_date)
            
            if start_price is None or end_price is None:
                return None, None, None, None, None, None
            
            # Calculate percentage change
            percent_change = ((end_price - start_price) / start_price) * 100
            
            # Find period high and low
            period_high = start_price
            period_low = start_price
            period_high_date = start_date.strftime('%Y-%m-%d')
            period_low_date = start_date.strftime('%Y-%m-%d')
            
            current_date = start_date
            while current_date <= end_date:
                date_str = current_date.strftime('%Y-%m-%d')
                if date_str in self.stock_data:
                    price = self.stock_data[date_str]['price']
                    if price > period_high:
                        period_high = price
                        period_high_date = date_str
                    if price < period_low:
                        period_low = price
                        period_low_date = date_str
                current_date += timedelta(days=1)
            
            return percent_change, period_high, period_low, period_high_date, period_low_date, start_price
            
        except Exception as e:
            print(f"Error calculating performance for period {start_date} to {end_date}: {str(e)}")
            return None, None, None, None, None, None

    def read_dasha_csv(self, csv_file):
        """Read dasha CSV file and return DataFrame"""
        try:
            df = pd.read_csv(csv_file)
            
            # Handle different CSV formats
            required_columns = ['Date', 'End_Date']
            if not all(col in df.columns for col in required_columns):
                print(f"❌ Error: CSV file missing required columns: {required_columns}")
                return None
            
            return df
            
        except Exception as e:
            print(f"❌ Error reading CSV file {csv_file}: {str(e)}")
            return None

    def analyze_periods(self, df, output_file, chart_file, period_type):
        """Analyze dasha periods and generate output"""
        results = []
        chart_data = []
        
        print(f"\n📊 Analyzing {len(df)} {period_type} periods...")
        
        for index, row in df.iterrows():
            try:
                start_date = pd.to_datetime(row['Date']).date()
                end_date = pd.to_datetime(row['End_Date']).date()
                
                # Skip future periods
                if start_date > datetime.now().date():
                    print(f"   Skipping future period: {start_date} to {end_date}")
                    continue
                
                # Adjust end date if it's in the future
                if end_date > datetime.now().date():
                    end_date = datetime.now().date()
                    print(f"   Adjusted end date to today: {end_date}")
                
                percent_change, period_high, period_low, high_date, low_date, start_price = \
                    self.calculate_period_performance(start_date, end_date)
                
                if percent_change is not None:
                    print(f"   ✓ Valid period: {start_date} to {end_date}, change: {percent_change:.2f}%")
                    # Create result row with appropriate columns based on period type
                    result_row = {
                        'Period_Type': period_type,
                        'Start_Date': start_date.strftime('%Y-%m-%d'),
                        'End_Date': end_date.strftime('%Y-%m-%d'),
                        'Start_Price': round(start_price, 2),
                        'Period_High': round(period_high, 2),
                        'Period_Low': round(period_low, 2),
                        'High_Date': high_date,
                        'Low_Date': low_date,
                        'Percent_Change': round(percent_change, 2)
                    }
                    
                    # Add dasha-specific columns based on what's available in the CSV
                    for col in df.columns:
                        if col not in ['Date', 'End_Date'] and col in row:
                            if period_type == 'MahaDasha' and col in ['antardasha_lord', 'pratyantardasha_lord']:
                                result_row[col] = ''  # Empty for MahaDasha
                            elif period_type == 'AntarDasha' and col == 'pratyantardasha_lord':
                                result_row[col] = ''  # Empty for AntarDasha
                            else:
                                result_row[col] = row[col] if pd.notna(row[col]) else ''
                    
                    results.append(result_row)
                    
                    # Chart data
                    chart_data.append({
                        'start_date': start_date,
                        'end_date': end_date,
                        'percent_change': percent_change,
                        'period_label': self.get_period_label(row, period_type),
                        'auspiciousness': row.get('Auspiciousness_Score', 0) if 'Auspiciousness_Score' in row else 0
                    })
                
            except Exception as e:
                print(f"Error processing row {index}: {str(e)}")
                continue
        
        if results:
            # Save CSV
            results_df = pd.DataFrame(results)
            results_df.to_csv(output_file, index=False)
            print(f"✅ Saved {len(results)} analyzed periods to {output_file}")
            
            # Generate chart
            self.create_stock_chart(chart_data, chart_file, period_type)
            
            return True
        else:
            print(f"❌ No valid periods found for {period_type}")
            return False

    def get_period_label(self, row, period_type):
        """Generate appropriate label for the period"""
        try:
            if period_type == 'Enhanced':
                return f"{row.get('mahadasha_lord', 'Unknown')}-{row.get('antardasha_lord', 'Unknown')}-{row.get('pratyantardasha_lord', 'Unknown')}"
            elif period_type == 'MahaDasha':
                return f"{row.get('mahadasha_lord', 'Unknown')}"
            elif period_type == 'AntarDasha':
                return f"{row.get('mahadasha_lord', 'Unknown')}-{row.get('antardasha_lord', 'Unknown')}"
            elif period_type == 'PratyantarDasha':
                return f"{row.get('antardasha_lord', 'Unknown')}-{row.get('pratyantardasha_lord', 'Unknown')}"
            else:
                return f"Period {row.name}"
        except:
            return f"Period {getattr(row, 'name', 'Unknown')}"

    def create_stock_chart(self, chart_data, chart_file, period_type):
        """Create enhanced stock price chart with dasha periods"""
        if not chart_data:
            print(f"❌ No data to chart for {period_type}")
            return
        
        # Get stock price data for the chart period
        start_date = min(item['start_date'] for item in chart_data)
        end_date = max(item['end_date'] for item in chart_data)
        
        # Extend the range slightly
        start_date -= timedelta(days=30)
        end_date += timedelta(days=30)
        
        # Get price data
        dates = []
        prices = []
        current_date = start_date
        
        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            if date_str in self.stock_data:
                dates.append(current_date)
                prices.append(self.stock_data[date_str]['price'])
            current_date += timedelta(days=1)
        
        if not dates:
            print(f"❌ No price data available for chart period")
            return
        
        # Create the chart
        plt.figure(figsize=(20, 12))
        
        # Plot stock price
        plt.plot(dates, prices, 'b-', linewidth=2, label=f'{self.stock_symbol} Stock Price', alpha=0.8)
        
        # Color periods based on performance and auspiciousness
        for i, period in enumerate(chart_data):
            start = period['start_date']
            end = period['end_date']
            change = period['percent_change']
            auspiciousness = period.get('auspiciousness', 0)
            
            # Color based on auspiciousness score (if available) or performance
            if auspiciousness != 0:
                # Use auspiciousness score for coloring (1-5 scale)
                if auspiciousness >= 4:
                    color = 'darkgreen'
                    alpha = 0.3
                elif auspiciousness >= 3:
                    color = 'green'
                    alpha = 0.25
                elif auspiciousness >= 2:
                    color = 'yellow'
                    alpha = 0.2
                elif auspiciousness >= 1:
                    color = 'orange'
                    alpha = 0.25
                else:
                    color = 'red'
                    alpha = 0.3
            else:
                # Fall back to performance-based coloring
                if change >= 20:
                    color = 'darkgreen'
                    alpha = 0.3
                elif change >= 0:
                    color = 'lightgreen'
                    alpha = 0.25
                else:
                    color = 'lightcoral'
                    alpha = 0.25
            
            # Add period shading
            plt.axvspan(start, end, color=color, alpha=alpha)
            
            # Add period labels (smart positioning)
            if i % 3 == 0:  # Show every 3rd label to avoid crowding
                mid_date = start + (end - start) / 2
                label_text = f"{period['period_label']}\n{change:+.1f}%"
                
                # Find y position for label
                mid_prices = [p for d, p in zip(dates, prices) if start <= d <= end]
                if mid_prices:
                    y_pos = max(mid_prices) * 1.02
                else:
                    y_pos = max(prices) * 1.02
                
                plt.annotate(label_text, xy=(mid_date, y_pos), 
                           ha='center', va='bottom', fontsize=8, 
                           bbox=dict(boxstyle='round,pad=0.3', facecolor=color, alpha=0.7),
                           rotation=0)
        
        # Formatting
        plt.title(f'{self.stock_symbol} Stock Performance - {period_type} Analysis', fontsize=16, fontweight='bold')
        plt.xlabel('Date', fontsize=12)
        plt.ylabel('Stock Price ($)', fontsize=12)
        plt.legend(fontsize=10)
        plt.grid(True, alpha=0.3)
        
        # Format x-axis
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        plt.gca().xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        plt.savefig(chart_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"✅ Created chart: {chart_file}")

    def process_house_system(self, analysis_path, house_system, symbol):
        """Process a single house system"""
        house_path = analysis_path / house_system
        
        if not house_path.exists():
            print(f"❌ House system folder not found: {house_path}")
            return False
        
        print(f"\n🏠 Processing house system: {house_system}")
        
        # Create output directory
        output_path = Path("verification") / symbol / house_system
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Process each dasha type
        dasha_types = {
            'Enhanced': f'{symbol}_Enhanced_Dasha_Analysis.csv',
            'MahaDasha': f'{symbol}_MahaDashas.csv',
            'AntarDasha': f'{symbol}_AntarDashas.csv',
            'PratyantarDasha': f'{symbol}_PratyantarDashas.csv'
        }
        
        success_count = 0
        
        for dasha_type, csv_filename in dasha_types.items():
            csv_file = house_path / csv_filename
            
            if not csv_file.exists():
                print(f"⚠️  CSV file not found: {csv_file}")
                continue
            
            # Output files
            output_csv = output_path / f"{symbol}_{dasha_type}_Stock_Performance.csv"
            output_chart = output_path / f"{symbol}_{dasha_type}_Stock_Chart.png"
            
            # Read and analyze
            df = self.read_dasha_csv(csv_file)
            if df is not None:
                if self.analyze_periods(df, output_csv, output_chart, dasha_type):
                    success_count += 1
        
        if success_count > 0:
            print(f"✅ Successfully processed {success_count} dasha types for {house_system}")
            return True
        else:
            print(f"❌ No dasha types processed for {house_system}")
            return False

def main():
    analyzer = EnhancedDashaStockAnalyzer()
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Enhanced Dasha Stock Analysis - Multi-House System')
    parser.add_argument('analysis_path', help='Path to analysis folder (e.g., analysis/PLTR)')
    parser.add_argument('house_systems', nargs='?', 
                       help='Comma-separated house systems (e.g., lagna,chandra_lagna). Default: all available')
    
    args = parser.parse_args()
    
    # Extract symbol from path
    analysis_path = Path(args.analysis_path)
    if not analysis_path.exists():
        print(f"❌ Analysis path not found: {analysis_path}")
        return
    
    symbol = analysis_path.name
    print(f"🎯 Analyzing symbol: {symbol}")
    
    # Load stock data
    if not analyzer.load_stock_data_from_json(symbol):
        return
    
    # Determine house systems to process
    if args.house_systems:
        house_systems = [hs.strip() for hs in args.house_systems.split(',')]
    else:
        # Auto-detect available house systems
        house_systems = []
        for item in analysis_path.iterdir():
            if item.is_dir():
                house_systems.append(item.name)
    
    if not house_systems:
        print(f"❌ No house systems found in {analysis_path}")
        return
    
    print(f"🏠 Processing house systems: {', '.join(house_systems)}")
    
    # Process each house system
    total_success = 0
    for house_system in house_systems:
        if analyzer.process_house_system(analysis_path, house_system, symbol):
            total_success += 1
    
    if total_success > 0:
        print(f"\n🎉 Analysis complete! Successfully processed {total_success}/{len(house_systems)} house systems")
        print(f"📁 Output saved to: verification/{symbol}/")
    else:
        print(f"\n❌ Analysis failed - no house systems processed successfully")

if __name__ == "__main__":
    main()