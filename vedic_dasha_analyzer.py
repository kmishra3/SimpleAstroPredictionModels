#!/usr/bin/env python3
"""
Vedic Astrology Dasha Analyzer

Analyzes dasha periods and calculates auspiciousness/inauspiciousness
based on classical Vedic astrology principles from B.V. Raman and Parashari texts.

Usage: python vedic_dasha_analyzer.py <json_file>
"""

import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any
import argparse
import sys

class VedicDashaAnalyzer:
    def __init__(self):
        # Planetary strength mappings based on sign positions
        self.exaltation_signs = {
            'Sun': 'Aries', 'Moon': 'Taurus', 'Mercury': 'Virgo', 'Venus': 'Pisces',
            'Mars': 'Capricorn', 'Jupiter': 'Cancer', 'Saturn': 'Libra',
            'Rahu': 'Gemini', 'Ketu': 'Sagittarius'
        }
        
        self.debilitation_signs = {
            'Sun': 'Libra', 'Moon': 'Scorpio', 'Mercury': 'Pisces', 'Venus': 'Virgo',
            'Mars': 'Cancer', 'Jupiter': 'Capricorn', 'Saturn': 'Aries',
            'Rahu': 'Sagittarius', 'Ketu': 'Gemini'
        }
        
        self.own_signs = {
            'Sun': ['Leo'], 'Moon': ['Cancer'], 'Mercury': ['Gemini', 'Virgo'],
            'Venus': ['Taurus', 'Libra'], 'Mars': ['Aries', 'Scorpio'],
            'Jupiter': ['Sagittarius', 'Pisces'], 'Saturn': ['Capricorn', 'Aquarius'],
            'Rahu': [], 'Ketu': []
        }
        
        # Planetary friendships (simplified)
        self.friendships = {
            'Sun': {'friends': ['Moon', 'Mars', 'Jupiter'], 'enemies': ['Saturn', 'Venus'], 'neutral': ['Mercury']},
            'Moon': {'friends': ['Sun', 'Mercury'], 'enemies': [], 'neutral': ['Mars', 'Jupiter', 'Venus', 'Saturn']},
            'Mercury': {'friends': ['Sun', 'Venus'], 'enemies': ['Moon'], 'neutral': ['Mars', 'Jupiter', 'Saturn']},
            'Venus': {'friends': ['Mercury', 'Saturn'], 'enemies': ['Sun', 'Moon'], 'neutral': ['Mars', 'Jupiter']},
            'Mars': {'friends': ['Sun', 'Moon', 'Jupiter'], 'enemies': ['Mercury'], 'neutral': ['Venus', 'Saturn']},
            'Jupiter': {'friends': ['Sun', 'Moon', 'Mars'], 'enemies': ['Mercury', 'Venus'], 'neutral': ['Saturn']},
            'Saturn': {'friends': ['Mercury', 'Venus'], 'enemies': ['Sun', 'Moon', 'Mars'], 'neutral': ['Jupiter']},
            'Rahu': {'friends': ['Saturn'], 'enemies': ['Sun', 'Moon', 'Mars'], 'neutral': ['Mercury', 'Jupiter', 'Venus']},
            'Ketu': {'friends': ['Mars'], 'enemies': ['Sun', 'Moon'], 'neutral': ['Mercury', 'Jupiter', 'Venus', 'Saturn']}
        }
        
        # Natural benefic/malefic classification
        self.natural_benefics = ['Jupiter', 'Venus', 'Mercury', 'Moon']
        self.natural_malefics = ['Sun', 'Mars', 'Saturn', 'Rahu', 'Ketu']
        
    def calculate_planetary_strength(self, planet: str, sign: str) -> float:
        """Calculate planetary strength on a scale of 1-10"""
        base_strength = 5.0  # Neutral strength
        
        # Exaltation/Debilitation factor (40% weightage)
        if sign == self.exaltation_signs.get(planet):
            exaltation_factor = 10.0
        elif sign == self.debilitation_signs.get(planet):
            exaltation_factor = 1.0
        elif sign in self.own_signs.get(planet, []):
            exaltation_factor = 8.0
        else:
            # Check friendship
            if planet in self.friendships:
                # Simplified: assume sign ruler friendship
                exaltation_factor = 6.0 if sign in ['Gemini', 'Virgo', 'Taurus', 'Libra'] else 5.0
            else:
                exaltation_factor = 5.0
        
        # Natural benefic/malefic factor (20% weightage)
        natural_factor = 6.0 if planet in self.natural_benefics else 4.0
        
        # Calculate weighted strength
        strength = (exaltation_factor * 0.4) + (natural_factor * 0.2) + (base_strength * 0.4)
        
        return min(10.0, max(1.0, strength))
    
    def get_planetary_compatibility(self, planet1: str, planet2: str) -> str:
        """Get compatibility between two planets"""
        if planet1 not in self.friendships or planet2 not in self.friendships:
            return 'neutral'
        
        friends1 = self.friendships[planet1]['friends']
        enemies1 = self.friendships[planet1]['enemies']
        
        if planet2 in friends1:
            return 'friend'
        elif planet2 in enemies1:
            return 'enemy'
        else:
            return 'neutral'
    
    def calculate_dasha_auspiciousness(self, maha_lord: str, antar_lord: str, 
                                    prayant_lord: str, planetary_strengths: Dict[str, float]) -> Tuple[float, float]:
        """Calculate auspiciousness and inauspiciousness for a dasha period"""
        
        # Get planetary strengths
        maha_strength = planetary_strengths.get(maha_lord, 5.0)
        antar_strength = planetary_strengths.get(antar_lord, 5.0)
        prayant_strength = planetary_strengths.get(prayant_lord, 5.0)
        
        # Calculate base auspiciousness (weighted average)
        base_auspiciousness = (maha_strength * 0.5) + (antar_strength * 0.3) + (prayant_strength * 0.2)
        
        # Compatibility bonuses/penalties
        maha_antar_compatibility = self.get_planetary_compatibility(maha_lord, antar_lord)
        antar_prayant_compatibility = self.get_planetary_compatibility(antar_lord, prayant_lord)
        maha_prayant_compatibility = self.get_planetary_compatibility(maha_lord, prayant_lord)
        
        compatibility_bonus = 0.0
        
        # Apply compatibility adjustments
        compatibilities = [maha_antar_compatibility, antar_prayant_compatibility, maha_prayant_compatibility]
        friend_count = compatibilities.count('friend')
        enemy_count = compatibilities.count('enemy')
        
        if friend_count >= 2:
            compatibility_bonus += 1.0
        elif friend_count == 1 and enemy_count == 0:
            compatibility_bonus += 0.5
        elif enemy_count >= 2:
            compatibility_bonus -= 1.0
        elif enemy_count == 1:
            compatibility_bonus -= 0.5
        
        # Final auspiciousness score
        auspiciousness = min(10.0, max(1.0, base_auspiciousness + compatibility_bonus))
        
        # Inauspiciousness is inverse with additional penalties
        malefic_penalty = 0.0
        if maha_lord in self.natural_malefics:
            malefic_penalty += 0.5
        if antar_lord in self.natural_malefics:
            malefic_penalty += 0.3
        if prayant_lord in self.natural_malefics:
            malefic_penalty += 0.2
        
        inauspiciousness = min(10.0, max(1.0, (10.0 - auspiciousness) + malefic_penalty))
        
        return auspiciousness, inauspiciousness
    
    def analyze_json_file(self, file_path: str) -> pd.DataFrame:
        """Analyze a JSON file and return comprehensive dasha analysis"""
        
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Extract entity information
        entity_name = data.get('companyName', data.get('symbol', 'Unknown'))
        birth_date = data['metadata']['company']['ipoDate']
        birth_datetime = datetime.strptime(birth_date, '%Y-%m-%d')
        
        # Calculate planetary strengths from birth positions
        positions = data['planetaryPositions']['positions']
        planetary_strengths = {}
        
        for planet, pos_data in positions.items():
            if planet != 'Ascendant':  # Skip Ascendant for now
                sign = pos_data['zodiacSign']
                strength = self.calculate_planetary_strength(planet, sign)
                planetary_strengths[planet] = strength
        
        # Process dasha data
        dasha_data = data['dashaData']
        results = []
        
        # Get all periods and create comprehensive analysis
        maha_periods = dasha_data['mahaDasha']
        antar_periods = dasha_data['bhukti']
        prayant_periods = dasha_data['antaram']
        
        # Create a mapping of dates to periods
        period_mapping = {}
        
        # Map all periods by date
        for date_str, period_info in maha_periods.items():
            if date_str not in period_mapping:
                period_mapping[date_str] = {}
            period_mapping[date_str]['maha'] = period_info
        
        for date_str, period_info in antar_periods.items():
            if date_str not in period_mapping:
                period_mapping[date_str] = {}
            period_mapping[date_str]['antar'] = period_info
        
        for date_str, period_info in prayant_periods.items():
            if date_str not in period_mapping:
                period_mapping[date_str] = {}
            period_mapping[date_str]['prayant'] = period_info
        
        # Analyze each period combination
        for date_str in sorted(period_mapping.keys()):
            period_date = datetime.strptime(date_str, '%Y-%m-%d')
            
            # Check if within entity lifetime (120 years)
            lifetime_end = birth_datetime + timedelta(days=120*365)
            is_active = period_date <= lifetime_end
            
            # Get period information
            period_data = period_mapping[date_str]
            
            # Find the active maha, antar, and prayant lords for this date
            maha_lord = None
            antar_lord = None
            prayant_lord = None
            
            # Find active mahadasha
            for maha_date_str, maha_info in maha_periods.items():
                maha_date = datetime.strptime(maha_date_str, '%Y-%m-%d')
                maha_end = datetime.strptime(maha_info['endDate'], '%Y-%m-%d')
                if maha_date <= period_date <= maha_end:
                    maha_lord = maha_info['lord']
                    break
            
            # Find active antardasha
            for antar_date_str, antar_info in antar_periods.items():
                antar_date = datetime.strptime(antar_date_str, '%Y-%m-%d')
                antar_end = datetime.strptime(antar_info['endDate'], '%Y-%m-%d')
                if antar_date <= period_date <= antar_end:
                    antar_lord = antar_info['lord']
                    break
            
            # Find active prayantardasha
            for prayant_date_str, prayant_info in prayant_periods.items():
                prayant_date = datetime.strptime(prayant_date_str, '%Y-%m-%d')
                prayant_end = datetime.strptime(prayant_info['endDate'], '%Y-%m-%d')
                if prayant_date <= period_date <= prayant_end:
                    prayant_lord = prayant_info['lord']
                    break
            
            # Skip if we don't have all three lords
            if not all([maha_lord, antar_lord, prayant_lord]):
                continue
            
            # Calculate auspiciousness
            auspiciousness, inauspiciousness = self.calculate_dasha_auspiciousness(
                maha_lord, antar_lord, prayant_lord, planetary_strengths
            )
            
            # Create result record
            result = {
                'Date': date_str,
                'Maha_Lord': maha_lord,
                'Antar_Lord': antar_lord,
                'Prayant_Lord': prayant_lord,
                'Maha_Strength': round(planetary_strengths.get(maha_lord, 5.0), 2),
                'Antar_Strength': round(planetary_strengths.get(antar_lord, 5.0), 2),
                'Prayant_Strength': round(planetary_strengths.get(prayant_lord, 5.0), 2),
                'Auspiciousness': round(auspiciousness, 2),
                'Inauspiciousness': round(inauspiciousness, 2),
                'Active_Status': 'Active' if is_active else 'Post-Lifetime',
                'Entity': entity_name,
                'Birth_Date': birth_date
            }
            
            results.append(result)
        
        return pd.DataFrame(results)

def main():
    parser = argparse.ArgumentParser(description='Vedic Astrology Dasha Analyzer')
    parser.add_argument('json_file', help='Path to the JSON file to analyze')
    parser.add_argument('--output', '-o', help='Output CSV file path', default=None)
    
    args = parser.parse_args()
    
    # Initialize analyzer
    analyzer = VedicDashaAnalyzer()
    
    try:
        # Analyze the file
        results_df = analyzer.analyze_json_file(args.json_file)
        
        # Display summary
        print(f"\\n{'='*80}")
        print(f"VEDIC ASTROLOGY DASHA ANALYSIS")
        print(f"{'='*80}")
        
        if not results_df.empty:
            entity_name = results_df['Entity'].iloc[0]
            birth_date = results_df['Birth_Date'].iloc[0]
            
            print(f"Entity: {entity_name}")
            print(f"Birth Date: {birth_date}")
            print(f"Total Periods Analyzed: {len(results_df)}")
            print(f"Active Periods: {len(results_df[results_df['Active_Status'] == 'Active'])}")
            
            # Show top 10 most auspicious periods
            print(f"\\n{'='*80}")
            print("TOP 10 MOST AUSPICIOUS PERIODS")
            print(f"{'='*80}")
            
            top_auspicious = results_df.nlargest(10, 'Auspiciousness')
            print(top_auspicious[['Date', 'Maha_Lord', 'Antar_Lord', 'Prayant_Lord', 'Auspiciousness', 'Active_Status']].to_string(index=False))
            
            # Show top 10 most inauspicious periods
            print(f"\\n{'='*80}")
            print("TOP 10 MOST INAUSPICIOUS PERIODS")
            print(f"{'='*80}")
            
            top_inauspicious = results_df.nlargest(10, 'Inauspiciousness')
            print(top_inauspicious[['Date', 'Maha_Lord', 'Antar_Lord', 'Prayant_Lord', 'Inauspiciousness', 'Active_Status']].to_string(index=False))
            
            # Save to CSV if requested
            if args.output:
                results_df.to_csv(args.output, index=False)
                print(f"\\nResults saved to: {args.output}")
            else:
                # Save with default name
                default_output = f"{entity_name.replace(' ', '_')}_dasha_analysis.csv"
                results_df.to_csv(default_output, index=False)
                print(f"\\nResults saved to: {default_output}")
        
        else:
            print("No valid dasha periods found in the data.")
            
    except Exception as e:
        print(f"Error analyzing file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 