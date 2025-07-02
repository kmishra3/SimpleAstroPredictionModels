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
from datetime import datetime, timedelta, date
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
        """Calculate stock performance for a given period"""
        try:
            # Get the actual stock data range
            stock_dates = sorted(self.stock_data.keys())
            if not stock_dates:
                return None, None, None, None, None, None
            
            first_stock_date = datetime.strptime(stock_dates[0], '%Y-%m-%d').date()
            last_stock_date = datetime.strptime(stock_dates[-1], '%Y-%m-%d').date()
            
            # If period starts before stock data is available, use stock birth date as start
            effective_start_date = max(start_date, first_stock_date)
            
            # If period ends after available data, use last available date
            effective_end_date = min(end_date, last_stock_date)
            
            # Check if we have any valid period after adjustments
            if effective_start_date > effective_end_date:
                return None, None, None, None, None, None
            
            # Get start price from effective start date
            start_price = self.get_nearest_trading_day_price(effective_start_date)
            if start_price is None:
                return None, None, None, None, None, None
            
            # Get end price
            end_price = self.get_nearest_trading_day_price(effective_end_date)
            if end_price is None:
                return None, None, None, None, None, None
            
            # Calculate performance metrics over the effective period
            period_high = start_price
            period_low = start_price
            high_date = effective_start_date.strftime('%Y-%m-%d')
            low_date = effective_start_date.strftime('%Y-%m-%d')
            
            # Find highest and lowest prices during the effective period
            current_date = effective_start_date
            while current_date <= effective_end_date:
                date_str = current_date.strftime('%Y-%m-%d')
                if date_str in self.stock_data:
                    price = self.stock_data[date_str]['price']
                    if price > period_high:
                        period_high = price
                        high_date = date_str
                    if price < period_low:
                        period_low = price
                        low_date = date_str
                current_date += timedelta(days=1)
            
            # Calculate percentage change
            percent_change = ((end_price - start_price) / start_price) * 100
            
            return percent_change, period_high, period_low, high_date, low_date, start_price
            
        except Exception as e:
            print(f"Error calculating performance: {str(e)}")
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
                
                # Skip future periods (periods that haven't started yet)
                if start_date > datetime.now().date():
                    print(f"   Skipping future period: {start_date} to {end_date}")
                    continue
                
                # Adjust end date if it's in the future (period is ongoing)
                original_end_date = end_date
                if end_date > datetime.now().date():
                    end_date = datetime.now().date()
                    print(f"   Adjusted end date to today: {end_date}")
                
                # Always create the result row for CSV - include all periods regardless of stock data availability
                result_row = {
                    'Date': start_date.strftime('%Y-%m-%d'),
                    'End_Date': original_end_date.strftime('%Y-%m-%d'),  # Use original end date
                    'Type': period_type,
                    'mahadasha_lord': row['mahadasha_lord'] if pd.notna(row['mahadasha_lord']) else '',
                    'antardasha_lord': row['antardasha_lord'] if pd.notna(row['antardasha_lord']) else '',
                    'pratyantardasha_lord': row['pratyantardasha_lord'] if pd.notna(row['pratyantardasha_lord']) else '',
                    'Planet': row['Planet'] if pd.notna(row['Planet']) else '',
                    'Parent_Planet': row['Parent_Planet'] if pd.notna(row['Parent_Planet']) else '',
                    'Auspiciousness_Score': row['Auspiciousness_Score'] if pd.notna(row['Auspiciousness_Score']) else '',
                    'Dasha_Lord_Strength': row['Dasha_Lord_Strength'] if pd.notna(row['Dasha_Lord_Strength']) else '',
                    'Arishta_Protections': row['Arishta_Protections'] if pd.notna(row['Arishta_Protections']) else '',
                    'Protection_Score': row['Protection_Score'] if pd.notna(row['Protection_Score']) else '',
                    'Sun_Moon_Support': row['Sun_Moon_Support'] if pd.notna(row['Sun_Moon_Support']) else '',
                    'Start_Price': None,
                    'End_Price': None,
                    'Period_High': None,
                    'High_Date': None,
                    'Period_Low': None,
                    'Low_Date': None,
                    'Notes': ''
                }
                
                # Handle empty fields for different period types
                if period_type == 'MD':  # MahaDasha
                    result_row['antardasha_lord'] = ''
                    result_row['pratyantardasha_lord'] = ''
                elif period_type == 'MD-AD':  # AntarDasha
                    result_row['pratyantardasha_lord'] = ''
                
                # Try to calculate stock performance if data is available
                percent_change, period_high, period_low, high_date, low_date, start_price = \
                    self.calculate_period_performance(start_date, end_date)
                
                if percent_change is not None:
                    # Check if we had to adjust the start date due to stock availability
                    stock_dates = sorted(self.stock_data.keys())
                    first_stock_date = datetime.strptime(stock_dates[0], '%Y-%m-%d').date()
                    
                    # Get end price
                    end_price = self.get_nearest_trading_day_price(end_date)
                    
                    # Update result row with stock performance data
                    result_row.update({
                        'Start_Price': round(start_price, 2),
                        'End_Price': round(end_price, 2) if end_price is not None else None,
                        'Period_High': round(period_high, 2),
                        'Period_Low': round(period_low, 2),
                        'High_Date': high_date,
                        'Low_Date': low_date
                    })
                    
                    if start_date < first_stock_date:
                        print(f"   ✓ Adjusted period: {start_date} to {end_date} (using stock birth date {first_stock_date} as start)")
                        # Add note about adjustment
                        result_row['Notes'] = f"Period adjusted: using stock birth date {first_stock_date} as start date"
                    else:
                        print(f"   ✓ Valid period: {start_date} to {end_date}")
                    
                    # Chart data (only for Enhanced analysis)
                    if chart_file is not None and period_type == 'Enhanced':
                        # Determine period type based on Type field
                        period_type_label = row.get('Type', '')
                        if not period_type_label:  # Fallback to determining by fields if Type is empty
                            if pd.notna(row.get('pratyantardasha_lord')):
                                period_type_label = 'MD-AD-PD'
                            elif pd.notna(row.get('antardasha_lord')):
                                period_type_label = 'MD-AD'
                            else:
                                period_type_label = 'MD'
                            
                        chart_data.append({
                            'start_date': start_date,
                            'end_date': original_end_date,  # Use original end date for chart data
                            'percent_change': percent_change,
                            'period_label': self.get_period_label(row, period_type),
                            'auspiciousness': float(row.get('Auspiciousness_Score', 0)) if pd.notna(row.get('Auspiciousness_Score')) else 0,
                            'period_type': period_type_label
                        })
                else:
                    print(f"   ⚠️  No price data for period: {start_date} to {end_date}")
                
                # Always add the row to results, regardless of stock data availability
                results.append(result_row)
                
            except Exception as e:
                print(f"Error processing row {index}: {str(e)}")
                continue
        
        if results:
            # Save CSV
            results_df = pd.DataFrame(results)
            results_df.to_csv(output_file, index=False)
            print(f"✅ Saved {len(results)} analyzed periods to {output_file}")
            
            # Generate chart only for Enhanced analysis and only if we have chart data
            if chart_file is not None and period_type == 'Enhanced' and chart_data:
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
        
        # Get the actual stock data date range (not period dates)
        stock_dates = sorted(self.stock_data.keys())
        if not stock_dates:
            print(f"❌ No stock data available for chart")
            return
        
        # Use stock data range for chart scaling
        stock_start_date = datetime.strptime(stock_dates[0], '%Y-%m-%d').date()
        stock_end_date = datetime.strptime(stock_dates[-1], '%Y-%m-%d').date()
        
        # Extend the range slightly for better visualization
        chart_start_date = stock_start_date - timedelta(days=30)
        chart_end_date = min(stock_end_date + timedelta(days=30), datetime.now().date())
        
        # Get price data for the chart range
        dates = []
        prices = []
        current_date = chart_start_date
        
        while current_date <= chart_end_date:
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
        
        # Calculate y-axis ranges for the three sections
        price_range = max(prices) - min(prices)
        section_height = price_range / 3
        
        # Define y-positions for each dasha type
        md_y_base = max(prices) - section_height
        ad_y_base = md_y_base - section_height
        pd_y_base = min(prices)
        
        # Group periods by dasha type
        mahadashas = []
        antardashas = []
        pratyantardashas = []
        
        for period in chart_data:
            period_type = period.get('period_type', '')
            if period_type == 'MD':
                mahadashas.append(period)
            elif period_type == 'MD-AD':
                antardashas.append(period)
            elif period_type == 'MD-AD-PD':
                pratyantardashas.append(period)
        
        # Function to get color based on auspiciousness
        def get_color_and_alpha(auspiciousness):
            if abs(auspiciousness - 5.0) <= 0.5:
                return 'yellow', 0.3  # Neutral
            elif auspiciousness > 5.0:
                if auspiciousness > 6.5:  # More than 1.5 above 5
                    return 'green', 0.4
                else:  # Between 0.5 and 1.5 above 5
                    return 'lightgreen', 0.35
            else:  # auspiciousness < 5.0
                if auspiciousness < 3.5:  # More than 1.5 below 5
                    return 'red', 0.4
                else:  # Between 0.5 and 1.5 below 5
                    return 'lightcoral', 0.35
        
        # Function to check if two periods overlap
        def periods_overlap(period1, period2, min_gap_days=30):
            # Convert dates to datetime objects if they're not already
            def to_datetime(date_val):
                if isinstance(date_val, datetime):
                    return date_val
                elif isinstance(date_val, str):
                    return datetime.strptime(date_val, '%Y-%m-%d')
                elif isinstance(date_val, date):
                    return datetime.combine(date_val, datetime.min.time())
                else:
                    raise ValueError(f"Unexpected date type: {type(date_val)}")
            
            start1 = to_datetime(period1['start_date'])
            end1 = to_datetime(period1['end_date'])
            start2 = to_datetime(period2['start_date'])
            end2 = to_datetime(period2['end_date'])
            
            # Calculate the midpoints
            mid1 = start1 + (end1 - start1) / 2
            mid2 = start2 + (end2 - start2) / 2
            
            # Check if the midpoints are within min_gap_days of each other
            return abs((mid2 - mid1).days) < min_gap_days

        # Function to plot periods in a section
        def plot_section(periods, y_base, height, label_offset=0.02, period_type=''):
            if not periods:
                return
                
            # Sort periods by start date
            periods = sorted(periods, key=lambda x: x['start_date'])
            
            # Different logic for different period types
            if period_type == 'MD-AD-PD':  # Pratyantardashas - show up to 10 strongest, well-distributed
                # Always include first and last
                first_period = periods[0]
                last_period = periods[-1]
                
                # For middle periods, get all periods sorted by strength
                middle_periods = periods[1:-1] if len(periods) > 2 else []
                middle_periods_sorted = sorted(middle_periods, 
                                             key=lambda x: abs(x.get('auspiciousness', 5.0) - 5.0), 
                                             reverse=True)
                
                # Calculate total time span
                total_span = (last_period['end_date'] - first_period['start_date']).days
                min_gap = max(15, total_span / 20)  # Adaptive gap based on total span
                
                # Divide the total span into sections
                num_sections = 8  # Number of sections to aim for
                section_length = total_span / num_sections
                
                # Initialize sections
                sections = [[] for _ in range(num_sections)]
                
                # Distribute periods into sections
                for period in middle_periods:
                    period_mid = period['start_date'] + (period['end_date'] - period['start_date']) / 2
                    section_idx = int((period_mid - first_period['start_date']).days / section_length)
                    if 0 <= section_idx < num_sections:
                        sections[section_idx].append(period)
                
                # Select strongest period from each section
                selected_periods = [first_period]  # Start with first period
                
                # First pass: Get strongest from each section
                for section in sections:
                    if section:
                        # Sort section by auspiciousness
                        section_sorted = sorted(section,
                                             key=lambda x: abs(x.get('auspiciousness', 5.0) - 5.0),
                                             reverse=True)
                        
                        # Try to add strongest period that doesn't overlap
                        for period in section_sorted:
                            is_consecutive = False
                            for selected in selected_periods:
                                if periods_overlap(period, selected, min_gap_days=min_gap):
                                    is_consecutive = True
                                    break
                            
                            if not is_consecutive:
                                selected_periods.append(period)
                                break
                
                # Second pass: Fill remaining slots with strongest periods that maintain spacing
                remaining_slots = 10 - len(selected_periods) - 1  # -1 for last_period
                if remaining_slots > 0:
                    # Get all unselected periods
                    used_periods = set(selected_periods)
                    remaining_candidates = [p for p in middle_periods_sorted if p not in used_periods]
                    
                    for candidate in remaining_candidates:
                        is_consecutive = False
                        for selected in selected_periods:
                            if periods_overlap(candidate, selected, min_gap_days=min_gap):
                                is_consecutive = True
                                break
                        
                        if not is_consecutive:
                            selected_periods.append(candidate)
                            remaining_slots -= 1
                            if remaining_slots <= 0:
                                break
                
                # Add last period if it's not consecutive or if we have room
                if last_period not in selected_periods:
                    is_consecutive = False
                    for selected in selected_periods:
                        if periods_overlap(last_period, selected, min_gap_days=min_gap):
                            is_consecutive = True
                            break
                    
                    if not is_consecutive or len(selected_periods) < 10:
                        selected_periods.append(last_period)
                
                # Sort final selection by date
                periods_to_show = sorted(selected_periods, key=lambda x: x['start_date'])
                
            else:  # Mahadashas and Antardashas - show all with overlap filtering
                # Always show first and last periods
                first_period = periods[0]
                last_period = periods[-1]
                
                # For the remaining periods, filter based on significance and overlap
                middle_periods = periods[1:-1] if len(periods) > 2 else []
                filtered_periods = []
                
                i = 0
                while i < len(middle_periods):
                    current_period = middle_periods[i]
                    auspiciousness = current_period.get('auspiciousness', 5.0)
                    
                    # Check for overlap with previous period
                    if filtered_periods and periods_overlap(filtered_periods[-1], current_period):
                        prev_auspiciousness = filtered_periods[-1].get('auspiciousness', 5.0)
                        # Keep the one that deviates more from neutral (5.0)
                        if abs(auspiciousness - 5.0) > abs(prev_auspiciousness - 5.0):
                            filtered_periods[-1] = current_period
                    else:
                        filtered_periods.append(current_period)
                    i += 1
                
                # Combine first, filtered middle, and last periods
                periods_to_show = [first_period] + filtered_periods + [last_period]
            
            # Plot each period
            for period in periods:
                original_start = period['start_date']
                original_end = period['end_date']
                auspiciousness = period.get('auspiciousness', 0)
                
                # Adjust period dates to stock data availability
                effective_start = max(original_start, stock_start_date)
                effective_end = min(original_end, stock_end_date)
                
                # Skip periods that don't overlap with stock data
                if effective_start > effective_end:
                    continue
                
                # Get color based on auspiciousness
                color, alpha = get_color_and_alpha(auspiciousness)
                
                # Calculate y coordinates for this section
                y_bottom = y_base
                y_top = y_base + height
                
                # Add period shading
                plt.fill_between([effective_start, effective_end], 
                               [y_bottom, y_bottom], 
                               [y_top, y_top], 
                               color=color, alpha=alpha)
                
                # Add vertical line at period end to separate consecutive periods
                plt.axvline(x=effective_end, ymin=(y_bottom-min(prices))/(max(prices)-min(prices)), 
                          ymax=(y_top-min(prices))/(max(prices)-min(prices)), 
                          color='gray', linewidth=1, alpha=0.4)
                
                # Add label if this period should be shown
                if period in periods_to_show:
                    mid_date = effective_start + (effective_end - effective_start) / 2
                    
                    # Position label within the colored region of the section
                    if period_type == 'MD-AD-PD':  # Pratyantardashas - top 1/4 of section
                        label_y = y_bottom + (height * 0.75)  # Top 1/4 of the section
                    else:  # Mahadashas and Antardashas - middle of section
                        label_y = y_bottom + (height * 0.5)  # Middle of the section
                    
                    label_text = f"{period['period_label']}\n{auspiciousness:.1f}"
                    plt.annotate(label_text, xy=(mid_date, label_y),
                               ha='center', va='center', fontsize=8,
                               bbox=dict(boxstyle='round,pad=0.3', facecolor=color, alpha=0.9),
                               rotation=0)
        
        # Plot each section with their respective period types
        plot_section(mahadashas, md_y_base, section_height, 0.02, 'MD')
        plot_section(antardashas, ad_y_base, section_height, 0.02, 'MD-AD')
        plot_section(pratyantardashas, pd_y_base, section_height, 0.02, 'MD-AD-PD')
        
        # Add section boundaries and labels
        # Dark, highly visible boundary lines
        plt.axhline(y=md_y_base, color='black', linestyle='-', linewidth=2, alpha=0.8)
        plt.axhline(y=ad_y_base, color='black', linestyle='-', linewidth=2, alpha=0.8)
        
        # Add section labels
        plt.text(chart_start_date, md_y_base + section_height/2, 'MahaDasha', 
                verticalalignment='center', fontsize=10)
        plt.text(chart_start_date, ad_y_base + section_height/2, 'AntarDasha', 
                verticalalignment='center', fontsize=10)
        plt.text(chart_start_date, pd_y_base + section_height/2, 'PratyantarDasha', 
                verticalalignment='center', fontsize=10)
        
        # Formatting
        plt.title(f'{self.stock_symbol} Stock Performance - {period_type} Analysis\n(Chart scaled to available data: {stock_start_date} to {stock_end_date})', 
                 fontsize=16, fontweight='bold')
        plt.xlabel('Date', fontsize=12)
        plt.ylabel('Stock Price ($)', fontsize=12)
        plt.legend(fontsize=10)
        plt.grid(True, alpha=0.3)
        
        # Set x-axis limits to stock data range
        plt.xlim(chart_start_date, chart_end_date)
        
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
        
        # Process each dasha type and generate CSV files
        dasha_types = {
            'Enhanced': f'{symbol}_Enhanced_Dasha_Analysis.csv',
            'MahaDasha': f'{symbol}_MahaDashas.csv',
            'AntarDasha': f'{symbol}_AntarDashas.csv',
            'PratyantarDasha': f'{symbol}_PratyantarDashas.csv'
        }
        
        success_count = 0
        enhanced_chart_created = False
        
        for dasha_type, csv_filename in dasha_types.items():
            csv_file = house_path / csv_filename
            
            if not csv_file.exists():
                print(f"⚠️  CSV file not found: {csv_file}")
                continue
            
            # Output CSV for each dasha type
            output_csv = output_path / f"{symbol}_{dasha_type}_Stock_Performance.csv"
            
            # Only create chart for Enhanced analysis (one chart per house system)
            if dasha_type == 'Enhanced' and not enhanced_chart_created:
                output_chart = output_path / f"{symbol}_Enhanced_Stock_Chart.png"
                enhanced_chart_created = True
            else:
                output_chart = None
            
            # Read and analyze
            df = self.read_dasha_csv(csv_file)
            if df is not None:
                # Handle gaps in PratyantarDasha and Enhanced data
                if dasha_type in ['PratyantarDasha', 'Enhanced']:
                    df = self.fill_pratyantardasha_gaps(df)
                
                if self.analyze_periods(df, output_csv, output_chart, dasha_type):
                    success_count += 1
        
        if success_count > 0:
            print(f"✅ Successfully processed {success_count} dasha types for {house_system}")
            if enhanced_chart_created:
                print(f"📊 Created Enhanced stock chart for {house_system}")
            return True
        else:
            print(f"❌ No dasha types processed for {house_system}")
            return False

    def fill_pratyantardasha_gaps(self, df):
        """Fill gaps in PratyantarDasha periods to ensure continuous coverage"""
        if len(df) == 0:
            return df
        
        # Sort by date
        df['Date'] = pd.to_datetime(df['Date'])
        df['End_Date'] = pd.to_datetime(df['End_Date'])
        df = df.sort_values('Date').reset_index(drop=True)
        
        filled_rows = []
        
        for i in range(len(df)):
            current_row = df.iloc[i].copy()
            filled_rows.append(current_row)
            
            # Check if there's a gap before the next period
            if i < len(df) - 1:
                next_row = df.iloc[i + 1]
                current_end = current_row['End_Date']
                next_start = next_row['Date']
                
                # If there's a gap of more than 1 day, create a filler period
                if (next_start - current_end).days > 1:
                    gap_start = current_end + pd.Timedelta(days=1)
                    gap_end = next_start - pd.Timedelta(days=1)
                    
                    # Create a filler row based on the previous period's dasha structure
                    filler_row = current_row.copy()
                    filler_row['Date'] = gap_start
                    filler_row['End_Date'] = gap_end
                    
                    # Mark as gap-filled period
                    if 'Notes' in filler_row:
                        filler_row['Notes'] = f"Gap-filled period"
                    
                    filled_rows.append(filler_row)
                    print(f"   🔧 Filled gap: {gap_start.strftime('%Y-%m-%d')} to {gap_end.strftime('%Y-%m-%d')}")
        
        # Convert back to DataFrame
        filled_df = pd.DataFrame(filled_rows)
        
        # Convert dates back to string format for consistency
        filled_df['Date'] = filled_df['Date'].dt.strftime('%Y-%m-%d')
        filled_df['End_Date'] = filled_df['End_Date'].dt.strftime('%Y-%m-%d')
        
        print(f"   📝 Original periods: {len(df)}, After gap-filling: {len(filled_df)}")
        
        return filled_df

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