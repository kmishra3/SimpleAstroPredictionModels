# Dasha Stock Analysis Tool - Verification Guide

This guide explains how to use the `dasha_stock_analysis.py` script to verify correlations between Vedic astrology dasha periods and stock market performance. The tool provides both numerical analysis and visual verification capabilities.

## Overview

The dasha stock analysis tool takes a company's dasha period data and correlates it with historical stock prices to:
1. Calculate performance metrics for each dasha period
2. Generate visual representations of stock performance during different periods
3. Identify potential correlations between astrological factors and market movements

## Running the Analysis

### Basic Usage
```bash
python dasha_stock_analysis.py [input_csv_file] [output_csv_file]
```

Example:
```bash
python dasha_stock_analysis.py data/Technology/LYFT_dasha_analysis.csv LYFT_Dasha_Stock_Performance.csv
```

### Required Input Format
Your input CSV file should contain the following columns:
- `Date`: Start date of the dasha period (YYYY-MM-DD)
- `End_Date`: End date of the dasha period (YYYY-MM-DD)
- `Auspiciousness`: Numerical score indicating positive astrological factors
- `Inauspiciousness`: Numerical score indicating challenging astrological factors

## Output Files and Their Interpretation

### 1. Performance CSV File
The script generates a detailed CSV file (e.g., `LYFT_Dasha_Stock_Performance.csv`) containing:

- Period Information:
  - Start and end dates
  - Opening and closing prices
  - Period high price and date
  - Period low price and date
  - Percentage change during the period
  - Auspiciousness metrics

This file helps you:
- Track actual price movements during each dasha period
- Identify periods of significant gains or losses
- Correlate astrological factors with market performance

### 2. Visualization Chart
A PNG file (e.g., `LYFT_Dasha_Stock_Chart.png`) is generated showing:

- Stock price movement over time
- Color-coded dasha periods based on auspiciousness:
  - Dark Green: Very auspicious (difference > 2)
  - Light Green: Moderately auspicious (difference > 1)
  - Yellow: Neutral (difference between -1 and 1)
  - Light Red: Moderately inauspicious (difference > -2)
  - Dark Red: Very inauspicious (difference ≤ -2)

The chart features:
- Clear period boundaries with vertical lines
- Smart label positioning to avoid overlaps
- Period labels for intervals longer than 30 days
- Automatic scaling for readability

## Verification Process

To verify dasha period correlations:

1. **Data Quality Check**
   - Ensure your input CSV has all required columns
   - Verify date formats are correct (YYYY-MM-DD)
   - Check that auspiciousness scores are properly calculated

2. **Run the Analysis**
   - Execute the script with your input file
   - Wait for both output files to be generated

3. **Review the Results**
   - Check the performance CSV for numerical correlations
   - Examine the visualization chart for visual patterns
   - Look for consistency between auspiciousness scores and actual performance

4. **Interpret Patterns**
   - Note periods of strong correlation
   - Identify any anomalies or unexpected results
   - Consider external factors that might affect correlations

## Technical Details

The script handles several technical aspects automatically:

- Missing Trading Days: Finds nearest available price data
- Weekend/Holiday Adjustments: Uses closest trading day data
- API Rate Limiting: Includes appropriate delays between requests
- Error Handling: Manages missing data and connection issues

## Common Issues and Solutions

1. **Missing Price Data**
   - The script will search for the nearest trading day's price
   - Maximum search range is 5 days before/after target date

2. **Period Labeling**
   - Periods shorter than 30 days may not show labels in the chart
   - This prevents overcrowding in the visualization

3. **Data Gaps**
   - The script will note any periods where price data is unavailable
   - Check the console output for warnings about missing data

## Best Practices

1. **Data Preparation**
   - Use consistent date formats
   - Ensure auspiciousness scores are properly normalized
   - Verify period end dates are accurate

2. **Analysis Review**
   - Start with shorter time periods for initial verification
   - Cross-reference CSV data with the visualization
   - Look for patterns across multiple dasha periods

3. **Interpretation**
   - Consider market conditions during each period
   - Account for company-specific events
   - Look for consistent patterns rather than isolated instances

## Notes

- The tool requires a Financial Modeling Prep (FMP) API key for stock data
- Visualization quality improves with longer periods of data
- Color intensity indicates the strength of astrological factors
- The tool focuses on completed dasha periods for accurate analysis 