# Dasha Stock Performance Analysis

This script analyzes Vedic astrology dasha periods and correlates them with actual stock price performance using historical data from the Financial Modeling Prep (FMP) API. It works with any technology company data from the data/Technology directory.

## Files Required

1. `dasha_stock_analysis.py` - Main analysis script
2. `data/Technology/*.json` - JSON files containing dasha analysis data for various tech companies
3. `requirements.txt` - Python dependencies

## Setup Instructions

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

Or install manually:
```bash
pip install pandas requests
```

### 2. Run the Analysis

```bash
python dasha_stock_analysis.py SYMBOL
```

Replace `SYMBOL` with the stock symbol of the company you want to analyze. For example:
```bash
python dasha_stock_analysis.py PLTR  # Analyze Palantir Technologies
python dasha_stock_analysis.py MSFT  # Analyze Microsoft
python dasha_stock_analysis.py AAPL  # Analyze Apple
```

## Available Companies

The script can analyze any company that has a corresponding JSON file in the `data/Technology` directory. Some examples include:
- PLTR (Palantir Technologies)
- MSFT (Microsoft)
- UBER (Uber)
- SNOW (Snowflake)
- NET (Cloudflare)
- And many more...

## What the Script Does

1. **Reads Company JSON**: Loads the company's dasha analysis data from the JSON file
2. **Processes Dasha Data**: Converts JSON data into a structured dasha period analysis
3. **Determines Period End Dates**: Calculates end dates for each dasha period
4. **Filters Elapsed Periods**: Only analyzes dasha periods that have completely finished
5. **Fetches Stock Prices**: Uses FMP API to get stock prices for start and end dates
6. **Calculates Performance**: Computes percent change in stock price for each period
7. **Generates Analysis**: Creates summary statistics and correlations

## Output

The script generates:
- **`{SYMBOL}_Dasha_Stock_Performance.csv`** - CSV file with stock performance data
- Console output with summary statistics and analysis

## Output CSV Format

The output CSV contains:
- `Date` - Start date of the dasha period
- `Maha_Lord/Antar_Lord/Prayant_Lord` - Ruling planets for each level
- `*_Strength` - Strength scores for each planetary ruler
- `Auspiciousness/Inauspiciousness` - Astrological scores
- `End_Date` - End date of the dasha period
- `Start_Price` - Stock price at period start
- `End_Price` - Stock price at period end  
- `Percent_Change` - Percentage change in stock price

## Sample Analysis Output

The script provides:
- Summary statistics (average, median, best/worst performance)
- Top 5 most auspicious periods and their stock performance
- Top 5 most inauspicious periods and their stock performance
- Correlation analysis between astrological factors and stock performance

## API Information

- Uses Financial Modeling Prep API for historical stock data
- API key is embedded in the script: `xfdfuV6azioH4OBRuFQvnovkwJMC2cqn`
- Includes rate limiting to avoid API restrictions
- Handles weekends/holidays by finding closest trading days

## Error Handling

The script includes robust error handling for:
- Missing JSON files
- API rate limiting
- Invalid dates
- Missing stock price data
- Network connectivity issues

## Notes

- The script only analyzes **completed** dasha periods (those that have ended before today's date)
- Stock prices are adjusted for weekends/holidays by finding the nearest trading day
- A small delay is added between API calls to respect rate limits
- All dates are in YYYY-MM-DD format
- The script automatically processes the JSON data to create the same format as the original Palantir analysis