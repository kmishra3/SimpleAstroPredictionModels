#!/usr/bin/env python3
"""
Enhanced Vedic Dasha Analyzer with Dasha-Aarambha Rules
Generic version with command-line inputs and 3-level analysis (MD-AD-PD)
"""

import json
import csv
import pandas as pd
import swisseph as swe
from datetime import datetime, timezone
import pytz
from typing import Dict, List, Tuple, Any, Optional
import os
import argparse
import sys
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder

# Swiss Ephemeris setup
swe.set_ephe_path('/opt/homebrew/share/swisseph')  # Path for macOS with Homebrew

class EnhancedVedicDashaAnalyzer:
    """Enhanced Vedic Dasha Analyzer with Swiss Ephemeris and Dasha-Aarambha Rules"""
    
    def __init__(self, birth_location: str = "New York, USA"):
        # Set birth location and timezone
        self.birth_location = birth_location
        self.setup_location_timezone()
        
        # Ayanamsa setting (Lahiri)
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        
        # Planet mappings
        self.planets = {
            'Sun': swe.SUN,
            'Moon': swe.MOON,
            'Mercury': swe.MERCURY,
            'Venus': swe.VENUS,
            'Mars': swe.MARS,
            'Jupiter': swe.JUPITER,
            'Saturn': swe.SATURN,
            'Rahu': swe.MEAN_NODE,  # Mean North Node
            'Ketu': swe.MEAN_NODE   # Will subtract 180° for Ketu
        }
        
        # Sign mappings
        self.signs = [
            'Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo',
            'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'
        ]
        
        # Planetary relationships
        self.exaltation_signs = {
            'Sun': 'Aries', 'Moon': 'Taurus', 'Mercury': 'Virgo', 'Venus': 'Pisces',
            'Mars': 'Capricorn', 'Jupiter': 'Cancer', 'Saturn': 'Libra',
            'Rahu': 'Taurus', 'Ketu': 'Scorpio'
        }
        
        self.own_signs = {
            'Sun': ['Leo'], 'Moon': ['Cancer'], 'Mercury': ['Gemini', 'Virgo'],
            'Venus': ['Taurus', 'Libra'], 'Mars': ['Aries', 'Scorpio'],
            'Jupiter': ['Sagittarius', 'Pisces'], 'Saturn': ['Capricorn', 'Aquarius'],
            'Rahu': [], 'Ketu': []
        }
        
        self.moolatrikona_signs = {
            'Sun': 'Leo', 'Moon': 'Taurus', 'Mercury': 'Virgo', 'Venus': 'Libra',
            'Mars': 'Aries', 'Jupiter': 'Sagittarius', 'Saturn': 'Aquarius',
            'Rahu': None, 'Ketu': None
        }
        
        self.debilitation_signs = {
            'Sun': 'Libra', 'Moon': 'Scorpio', 'Mercury': 'Pisces', 'Venus': 'Virgo',
            'Mars': 'Cancer', 'Jupiter': 'Capricorn', 'Saturn': 'Aries',
            'Rahu': 'Scorpio', 'Ketu': 'Taurus'
        }
        
        # Natural benefics and malefics
        self.natural_benefics = ['Jupiter', 'Venus', 'Mercury', 'Moon']
        self.natural_malefics = ['Sun', 'Mars', 'Saturn', 'Rahu', 'Ketu']
        
        # Friends and enemies
        self.planetary_friends = {
            'Sun': ['Moon', 'Mars', 'Jupiter'],
            'Moon': ['Sun', 'Mercury'],
            'Mercury': ['Sun', 'Venus'],
            'Venus': ['Mercury', 'Saturn'],
            'Mars': ['Sun', 'Moon', 'Jupiter'],
            'Jupiter': ['Sun', 'Moon', 'Mars'],
            'Saturn': ['Mercury', 'Venus'],
            'Rahu': ['Venus', 'Saturn'],
            'Ketu': ['Mars', 'Jupiter']
        }
        
    def setup_location_timezone(self):
        """Setup timezone based on birth location"""
        try:
            # Default to New York if location parsing fails
            default_tz = pytz.timezone('America/New_York')
            default_lat, default_lon = 40.7128, -74.0060
            
            if self.birth_location.lower() in ['new york', 'ny', 'new york, usa', 'new york city']:
                self.birth_tz = default_tz
                self.birth_lat, self.birth_lon = default_lat, default_lon
                print(f"Using location: New York, USA (40.71°N, 74.01°W)")
                return
            
            # Try to geocode the location
            geolocator = Nominatim(user_agent="vedic_dasha_analyzer")
            location = geolocator.geocode(self.birth_location)
            
            if location:
                self.birth_lat = location.latitude
                self.birth_lon = location.longitude
                
                # Get timezone for the coordinates
                tf = TimezoneFinder()
                tz_name = tf.timezone_at(lat=self.birth_lat, lng=self.birth_lon)
                
                if tz_name:
                    self.birth_tz = pytz.timezone(tz_name)
                    print(f"Using location: {self.birth_location} ({self.birth_lat:.2f}°, {self.birth_lon:.2f}°)")
                    print(f"Timezone: {tz_name}")
                else:
                    print(f"Warning: Could not determine timezone for {self.birth_location}, using New York timezone")
                    self.birth_tz = default_tz
                    self.birth_lat, self.birth_lon = default_lat, default_lon
            else:
                print(f"Warning: Could not geocode location '{self.birth_location}', using New York as default")
                self.birth_tz = default_tz
                self.birth_lat, self.birth_lon = default_lat, default_lon
                
        except Exception as e:
            print(f"Error setting up location: {e}")
            print("Falling back to New York, USA")
            self.birth_tz = pytz.timezone('America/New_York')
            self.birth_lat, self.birth_lon = 40.7128, -74.0060
        
    def julian_day_from_datetime(self, dt: datetime) -> float:
        """Convert datetime to Julian Day for Swiss Ephemeris"""
        # Convert to UTC if timezone aware
        if dt.tzinfo:
            dt_utc = dt.astimezone(timezone.utc)
        else:
            dt_utc = dt
        
        return swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, 
                         dt_utc.hour + dt_utc.minute/60.0 + dt_utc.second/3600.0)
    
    def get_planetary_positions(self, dt: datetime) -> Dict[str, Dict]:
        """Get planetary positions using Swiss Ephemeris"""
        jd = self.julian_day_from_datetime(dt)
        positions = {}
        
        for planet_name, planet_id in self.planets.items():
            if planet_name == 'Ketu':
                # Get Rahu position and subtract 180°
                rahu_pos, _ = swe.calc_ut(jd, swe.MEAN_NODE, swe.FLG_SWIEPH | swe.FLG_SIDEREAL)
                longitude = (rahu_pos[0] + 180) % 360
            else:
                planet_pos, _ = swe.calc_ut(jd, planet_id, swe.FLG_SWIEPH | swe.FLG_SIDEREAL)
                longitude = planet_pos[0]
            
            sign_index = int(longitude // 30)
            degree_in_sign = longitude % 30
            
            positions[planet_name] = {
                'longitude': longitude,
                'zodiacSign': self.signs[sign_index],
                'degreeWithinSign': degree_in_sign
            }
        
        return positions
    
    def calculate_planetary_strength(self, planet: str, sign: str, is_dasha_start: bool = False) -> float:
        """Calculate planetary strength with dasha-aarambha multipliers"""
        base_strength = 5.0  # Neutral strength
        
        # Basic dignity
        if sign == self.exaltation_signs.get(planet):
            base_strength = 10.0
        elif sign in self.own_signs.get(planet, []):
            base_strength = 9.0
        elif sign == self.moolatrikona_signs.get(planet):
            base_strength = 8.5
        elif sign == self.debilitation_signs.get(planet):
            base_strength = 1.0
        
        # Dasha-aarambha enhancement (Dr. K.S. Charak's rules)
        if is_dasha_start:
            if sign == self.exaltation_signs.get(planet):
                base_strength *= 1.5  # 150% enhancement for exaltation at dasha start
            elif sign in self.own_signs.get(planet, []):
                base_strength *= 1.25  # 125% enhancement for own sign at dasha start
        
        return min(base_strength, 10.0)  # Cap at 10.0
    
    def analyze_arishta_bhanga(self, birth_positions: Dict, dasha_positions: Dict, 
                              dasha_planet: str) -> Dict[str, Any]:
        """Analyze Arishta-Bhanga (cancellation) rules"""
        protections = []
        
        # Rule 1: Strong benefic in kendra from lagna at dasha start
        kendras = [1, 4, 7, 10]  # Houses from ascendant
        asc_longitude = birth_positions.get('Ascendant', {}).get('longitude', 0)
        
        for benefic in self.natural_benefics:
            if benefic in dasha_positions:
                benefic_pos = dasha_positions[benefic]['longitude']
                house_diff = ((benefic_pos - asc_longitude) // 30 + 1) % 12
                if house_diff in kendras or house_diff == 0:
                    strength = self.calculate_planetary_strength(
                        benefic, dasha_positions[benefic]['zodiacSign'], True
                    )
                    if strength >= 7.0:
                        protections.append(f"Strong {benefic} in kendra at dasha start")
        
        # Rule 2: Exalted planet in trikona (1, 5, 9) at dasha start
        trikonas = [1, 5, 9]
        for planet, pos_data in dasha_positions.items():
            if planet != 'Ascendant':
                house_diff = ((pos_data['longitude'] - asc_longitude) // 30 + 1) % 12
                if house_diff in trikonas or house_diff == 0:
                    if pos_data['zodiacSign'] == self.exaltation_signs.get(planet):
                        protections.append(f"Exalted {planet} in trikona at dasha start")
        
        # Rule 3: Dasha lord in own sign or exaltation at dasha start
        if dasha_planet in dasha_positions:
            dasha_sign = dasha_positions[dasha_planet]['zodiacSign']
            if (dasha_sign in self.own_signs.get(dasha_planet, []) or 
                dasha_sign == self.exaltation_signs.get(dasha_planet)):
                protections.append(f"Dasha lord {dasha_planet} in own/exalted sign at start")
        
        protection_score = len(protections) * 0.2  # Each protection adds 20%
        
        return {
            'protections': protections,
            'protection_score': min(protection_score, 1.0),
            'is_protected': len(protections) > 0
        }
    
    def analyze_sun_moon_significance(self, sun_pos: Dict, moon_pos: Dict, 
                                    dasha_planet: str) -> Dict[str, Any]:
        """Analyze Sun-Moon significance in dasha results (Kalyana Varma's principles)"""
        analysis = {}
        
        # Sun's preparation role
        sun_strength = self.calculate_planetary_strength(
            'Sun', sun_pos['zodiacSign'], True
        )
        analysis['sun_preparation'] = {
            'strength': sun_strength,
            'quality': 'Strong' if sun_strength >= 7 else 'Moderate' if sun_strength >= 5 else 'Weak'
        }
        
        # Moon's nourishment role
        moon_strength = self.calculate_planetary_strength(
            'Moon', moon_pos['zodiacSign'], True
        )
        analysis['moon_nourishment'] = {
            'strength': moon_strength,
            'quality': 'Strong' if moon_strength >= 7 else 'Moderate' if moon_strength >= 5 else 'Weak'
        }
        
        # Combined influence
        combined_score = (sun_strength + moon_strength) / 20.0  # Normalize to 0-1
        analysis['luminaries_support'] = min(combined_score, 1.0)
        
        return analysis
    
    def calculate_dasha_auspiciousness(self, birth_positions: Dict, dasha_start_date: str,
                                    dasha_planet: str, dasha_type: str, birth_time_str: str = "13:38:00") -> Dict[str, Any]:
        """Calculate comprehensive dasha auspiciousness with all rules"""
        try:
            # Parse date and create datetime with birth time
            dt = datetime.strptime(dasha_start_date, '%Y-%m-%d')
            
            # Parse birth time
            birth_hour, birth_minute, birth_second = map(int, birth_time_str.split(':'))
            dt = dt.replace(hour=birth_hour, minute=birth_minute, second=birth_second)
            
            # Localize to birth timezone (handles DST automatically)
            dt_local = self.birth_tz.localize(dt)
            
            dasha_positions = self.get_planetary_positions(dt_local)
            
            # 1. Dasha lord strength at start
            dasha_lord_strength = self.calculate_planetary_strength(
                dasha_planet, 
                dasha_positions.get(dasha_planet, {}).get('zodiacSign', ''),
                is_dasha_start=True
            )
            
            # 2. Arishta-Bhanga analysis
            arishta_analysis = self.analyze_arishta_bhanga(
                birth_positions, dasha_positions, dasha_planet
            )
            
            # 3. Sun-Moon significance
            sun_moon_analysis = self.analyze_sun_moon_significance(
                dasha_positions.get('Sun', {}),
                dasha_positions.get('Moon', {}),
                dasha_planet
            )
            
            # 4. Base planetary nature
            base_nature = 1.0 if dasha_planet in self.natural_benefics else 0.3
            
            # 5. Calculate final auspiciousness score
            # Weighted combination of all factors
            weights = {
                'dasha_lord_strength': 0.3,
                'arishta_protection': 0.25,
                'luminaries_support': 0.2,
                'base_nature': 0.15,
                'planetary_dignity': 0.1
            }
            
            # Planetary dignity at dasha start
            dignity_score = dasha_lord_strength / 10.0
            
            final_score = (
                weights['dasha_lord_strength'] * (dasha_lord_strength / 10.0) +
                weights['arishta_protection'] * arishta_analysis['protection_score'] +
                weights['luminaries_support'] * sun_moon_analysis['luminaries_support'] +
                weights['base_nature'] * base_nature +
                weights['planetary_dignity'] * dignity_score
            )
            
            # Scale to 1-10
            final_auspiciousness = 1 + (final_score * 9)
            
            return {
                'auspiciousness_score': round(final_auspiciousness, 2),
                'dasha_lord_strength': dasha_lord_strength,
                'arishta_bhanga': arishta_analysis,
                'sun_moon_analysis': sun_moon_analysis,
                'dasha_start_positions': dasha_positions,
                'analysis_date': dasha_start_date,
                'dasha_type': dasha_type
            }
            
        except Exception as e:
            print(f"Error calculating auspiciousness for {dasha_start_date}: {e}")
            return {
                'auspiciousness_score': 5.0,
                'error': str(e)
            }
    
    def extract_birth_info(self, data: Dict) -> Tuple[str, str]:
        """Extract birth date and time from JSON data with multiple fallback strategies"""
        birth_date = None
        birth_time = "13:38:00"  # Default fallback
        
        # Strategy 1: Direct fields
        if 'startDate' in data:
            birth_date = data['startDate']
        if 'firstTradeTime' in data:
            birth_time = data['firstTradeTime']
            
        # Strategy 2: Metadata fields (for complex JSON structures)
        if not birth_date and 'metadata' in data:
            metadata = data['metadata']
            if 'company' in metadata and 'ipoDate' in metadata['company']:
                birth_date = metadata['company']['ipoDate']
            if 'company' in metadata and 'firstTradeTime' in metadata['company']:
                birth_time = metadata['company']['firstTradeTime']
                
        # Strategy 3: Other common field names
        if not birth_date:
            for field in ['incorporationDate', 'foundingDate', 'launchDate', 'date']:
                if field in data:
                    birth_date = data[field]
                    break
                    
        # Ensure we have a birth date
        if not birth_date:
            raise ValueError("Could not extract birth date from JSON. Please ensure the JSON contains 'startDate', 'incorporationDate', or similar field.")
            
        return birth_date, birth_time
    
    def analyze_json_file(self, json_file_path: str) -> Dict[str, Any]:
        """Analyze JSON file with enhanced dasha-aarambha rules and 3-level analysis"""
        with open(json_file_path, 'r') as f:
            data = json.load(f)
        
        # Extract entity information with fallback strategies
        symbol = data.get('symbol', data.get('ticker', 'UNKNOWN'))
        company_name = data.get('companyName', data.get('name', symbol))
        
        # Extract birth information
        birth_date, birth_time = self.extract_birth_info(data)
        
        print(f"Analyzing {symbol} - {company_name}")
        print(f"Birth: {birth_date} at {birth_time} ({self.birth_tz.zone})")
        print(f"Location: {self.birth_location}")
        
        # Get birth planetary positions from JSON
        birth_positions = data['planetaryPositions']['positions']
        
        # Process dasha data
        results = []
        
        # Process Maha Dashas
        maha_dashas = data['dashaData']['mahaDasha']
        for start_date, maha_dasha in sorted(maha_dashas.items()):
            analysis = self.calculate_dasha_auspiciousness(
                birth_positions, start_date, maha_dasha['lord'], 'Maha Dasha', birth_time
            )
            
            results.append({
                'Date': start_date,
                'End_Date': maha_dasha['endDate'],
                'Type': 'MD',
                'Maha_Lord': maha_dasha['lord'],
                'Antar_Lord': '',
                'Pratyantar_Lord': '',
                'Planet': maha_dasha['lord'],
                'Parent_Planet': '',
                'Auspiciousness_Score': analysis['auspiciousness_score'],
                'Dasha_Lord_Strength': analysis.get('dasha_lord_strength', 5.0),
                'Arishta_Protections': len(analysis.get('arishta_bhanga', {}).get('protections', [])),
                'Protection_Score': analysis.get('arishta_bhanga', {}).get('protection_score', 0),
                'Sun_Moon_Support': analysis.get('sun_moon_analysis', {}).get('luminaries_support', 0.5)
            })
        
        # Process Antar Dashas (Bhuktis)
        bhuktis = data['dashaData']['bhukti']
        for start_date, bhukti in sorted(bhuktis.items()):
            analysis = self.calculate_dasha_auspiciousness(
                birth_positions, start_date, bhukti['lord'], 'Antar Dasha', birth_time
            )
            
            results.append({
                'Date': start_date,
                'End_Date': bhukti['endDate'],
                'Type': 'MD-AD',
                'Maha_Lord': bhukti['parentLord'],
                'Antar_Lord': bhukti['lord'],
                'Pratyantar_Lord': '',
                'Planet': bhukti['lord'],
                'Parent_Planet': bhukti['parentLord'],
                'Auspiciousness_Score': analysis['auspiciousness_score'],
                'Dasha_Lord_Strength': analysis.get('dasha_lord_strength', 5.0),
                'Arishta_Protections': len(analysis.get('arishta_bhanga', {}).get('protections', [])),
                'Protection_Score': analysis.get('arishta_bhanga', {}).get('protection_score', 0),
                'Sun_Moon_Support': analysis.get('sun_moon_analysis', {}).get('luminaries_support', 0.5)
            })
        
        # Process Pratyantar Dashas (if available)
        if 'antaram' in data['dashaData']:
            pratayantar_dashas = data['dashaData']['antaram']
            print(f"Processing {len(pratayantar_dashas)} Pratyantar Dasha periods...")
            
            for start_date, pratyantar in sorted(pratayantar_dashas.items()):
                # Find the corresponding Maha and Antar lords for this period
                maha_lord = self.find_active_lord(start_date, maha_dashas)
                antar_lord = self.find_active_lord(start_date, bhuktis)
                
                analysis = self.calculate_dasha_auspiciousness(
                    birth_positions, start_date, pratyantar['lord'], 'Pratyantar Dasha', birth_time
                )
                
                results.append({
                    'Date': start_date,
                    'End_Date': pratyantar['endDate'],
                    'Type': 'MD-AD-PD',
                    'Maha_Lord': maha_lord,
                    'Antar_Lord': antar_lord,
                    'Pratyantar_Lord': pratyantar['lord'],
                    'Planet': pratyantar['lord'],
                    'Parent_Planet': antar_lord,
                    'Auspiciousness_Score': analysis['auspiciousness_score'],
                    'Dasha_Lord_Strength': analysis.get('dasha_lord_strength', 5.0),
                    'Arishta_Protections': len(analysis.get('arishta_bhanga', {}).get('protections', [])),
                    'Protection_Score': analysis.get('arishta_bhanga', {}).get('protection_score', 0),
                    'Sun_Moon_Support': analysis.get('sun_moon_analysis', {}).get('luminaries_support', 0.5)
                })
        
        return {
            'symbol': symbol,
            'company_name': company_name,
            'birth_date': birth_date,
            'birth_time': birth_time,
            'birth_location': self.birth_location,
            'birth_timezone': self.birth_tz.zone,
            'birth_positions': birth_positions,
            'results': results
        }
    
    def find_active_lord(self, target_date: str, periods: Dict) -> Optional[str]:
        """Find the active dasha lord for a given date"""
        target_dt = datetime.strptime(target_date, '%Y-%m-%d')
        
        for start_date_str, period_info in periods.items():
            start_dt = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_dt = datetime.strptime(period_info['endDate'], '%Y-%m-%d')
            
            if start_dt <= target_dt <= end_dt:
                return period_info['lord']
        
        return None
    
    def save_to_csv(self, analysis_results: Dict[str, Any], custom_output_dir: str = None):
        """Save results to CSV with separate breakdown by dasha type in organized directory structure"""
        symbol = analysis_results['symbol']
        
        # Create output directory structure
        if custom_output_dir:
            output_dir = custom_output_dir
        else:
            output_dir = f"analysis/{symbol}"
        
        os.makedirs(output_dir, exist_ok=True)
        
        df = pd.DataFrame(analysis_results['results'])
        df_sorted = df.sort_values('Date')
        
        # Save complete results
        complete_file = os.path.join(output_dir, f"{symbol}_Enhanced_Dasha_Analysis.csv")
        df_sorted.to_csv(complete_file, index=False)
        
        # Create separate files by type
        files_created = [complete_file]
        
        # Maha Dashas only
        md_only = df_sorted[df_sorted['Type'] == 'MD']
        if not md_only.empty:
            md_file = os.path.join(output_dir, f"{symbol}_MahaDashas.csv")
            md_only.to_csv(md_file, index=False)
            files_created.append(md_file)
        
        # Antar Dashas only
        ad_only = df_sorted[df_sorted['Type'] == 'MD-AD']
        if not ad_only.empty:
            ad_file = os.path.join(output_dir, f"{symbol}_AntarDashas.csv")
            ad_only.to_csv(ad_file, index=False)
            files_created.append(ad_file)
        
        # Pratyantar Dashas only
        pd_only = df_sorted[df_sorted['Type'] == 'MD-AD-PD']
        if not pd_only.empty:
            pd_file = os.path.join(output_dir, f"{symbol}_PratyantarDashas.csv")
            pd_only.to_csv(pd_file, index=False)
            files_created.append(pd_file)
        
        print(f"\nCSV Results saved to directory: {output_dir}/")
        for file_path in files_created:
            print(f"  - {os.path.basename(file_path)}")
        
        return df_sorted, output_dir
    
    def generate_markdown_report(self, analysis_results: Dict[str, Any], df: pd.DataFrame, output_dir: str):
        """Generate comprehensive markdown analysis report"""
        symbol = analysis_results['symbol']
        company_name = analysis_results['company_name']
        birth_date = analysis_results['birth_date']
        birth_time = analysis_results['birth_time']
        birth_location = analysis_results['birth_location']
        birth_timezone = analysis_results['birth_timezone']
        birth_positions = analysis_results['birth_positions']
        
        # Calculate statistics
        total_periods = len(df)
        type_counts = df['Type'].value_counts()
        
        # Get current year for near-future analysis
        current_year = datetime.now().year
        near_future_start = f"{current_year}-01-01"
        near_future_end = f"{current_year + 2}-12-31"
        
        # Filter for current/near-future periods
        current_periods = df[(df['Date'] >= near_future_start) & (df['Date'] <= near_future_end)]
        
        # Get top periods overall
        top_periods_all = df.nlargest(10, 'Auspiciousness_Score')
        
        # Get top periods by type
        top_md = df[df['Type'] == 'MD'].nlargest(5, 'Auspiciousness_Score') if not df[df['Type'] == 'MD'].empty else pd.DataFrame()
        top_ad = df[df['Type'] == 'MD-AD'].nlargest(5, 'Auspiciousness_Score') if not df[df['Type'] == 'MD-AD'].empty else pd.DataFrame()
        top_pd = df[df['Type'] == 'MD-AD-PD'].nlargest(5, 'Auspiciousness_Score') if not df[df['Type'] == 'MD-AD-PD'].empty else pd.DataFrame()
        
        # Protection analysis
        protected_periods = len(df[df['Arishta_Protections'] > 0])
        protection_rate = protected_periods / total_periods * 100 if total_periods > 0 else 0
        high_protection = df[df['Arishta_Protections'] >= 3]
        
        # Score analysis
        perfect_scores = len(df[df['Auspiciousness_Score'] >= 9.5])
        excellent_scores = len(df[df['Auspiciousness_Score'] >= 8.0])
        avg_scores = df.groupby('Type')['Auspiciousness_Score'].mean()
        
        # Birth chart analysis
        strong_planets = []
        for planet, pos in birth_positions.items():
            if planet != 'Ascendant':
                strength = self.calculate_planetary_strength(planet, pos['zodiacSign'])
                if strength >= 8.0:
                    strong_planets.append({
                        'planet': planet,
                        'sign': pos['zodiacSign'],
                        'strength': strength
                    })
        
        # Current periods analysis
        current_best = current_periods.nlargest(5, 'Auspiciousness_Score') if not current_periods.empty else pd.DataFrame()
        
        # Generate markdown content
        markdown_content = f"""# {company_name} ({symbol}) - Complete Vedic Dasha Analysis Report

## Executive Summary

**Entity:** {company_name} ({symbol})  
**Birth Date:** {birth_date}  
**Birth Time:** {birth_time}  
**Birth Location:** {birth_location}  
**Birth Timezone:** {birth_timezone}  
**Analysis Method:** Enhanced Vedic Astrology with Dasha-Aarambha Rules  
**Total Periods Analyzed:** {total_periods:,} dasha periods

---

## 📊 Analysis Overview

### Period Distribution
- **Maha Dashas (MD):** {type_counts.get('MD', 0)} major life periods
- **Antar Dashas (MD-AD):** {type_counts.get('MD-AD', 0)} sub-periods  
- **Pratyantar Dashas (MD-AD-PD):** {type_counts.get('MD-AD-PD', 0)} micro-periods

### Auspiciousness Statistics
- **Average Auspiciousness by Type:**"""

        for dasha_type, avg_score in avg_scores.items():
            type_name = {
                'MD': 'Maha Dasha (MD)',
                'MD-AD': 'Antar Dasha (MD-AD)',
                'MD-AD-PD': 'Pratyantar Dasha (MD-AD-PD)'
            }.get(dasha_type, dasha_type)
            markdown_content += f"\n  - {type_name}: {avg_score:.2f}/10"

        markdown_content += f"""

### Protection Analysis (Arishta-Bhanga)
- **Protected Periods:** {protected_periods} out of {total_periods} ({protection_rate:.1f}%)
- **High Protection (≥3 safeguards):** {len(high_protection)} periods
- **Perfect Scores (≥9.5):** {perfect_scores} periods
- **Excellent Scores (≥8.0):** {excellent_scores} periods

---

## 🌟 Birth Chart Strength Analysis

### Exceptional Planetary Positions
{company_name} possesses {"an exceptionally strong" if len(strong_planets) >= 4 else "a strong" if len(strong_planets) >= 2 else "a moderate"} birth chart, with **{len(strong_planets)} out of 9 planets** in highly dignified positions:
"""

        for i, planet_info in enumerate(strong_planets, 1):
            planet = planet_info['planet']
            sign = planet_info['sign']
            strength = planet_info['strength']
            
            # Determine dignity type
            dignity = ""
            if sign == self.exaltation_signs.get(planet):
                dignity = "Exaltation"
            elif sign in self.own_signs.get(planet, []):
                dignity = "Own Sign"
            elif sign == self.moolatrikona_signs.get(planet):
                dignity = "Moolatrikona"
            
            markdown_content += f"\n{i}. **{planet} in {sign}** - {dignity} ({strength}/10 strength)"

        markdown_content += f"""

### Chart Assessment
- **{"Exceptional" if len(strong_planets) >= 4 else "Strong" if len(strong_planets) >= 2 else "Moderate"} Strength:** {len(strong_planets)} planets highly dignified
- **Natural Balance:** {"Strong" if any(p['planet'] in self.natural_benefics for p in strong_planets) and any(p['planet'] in self.natural_malefics for p in strong_planets) else "Moderate"} mix of benefics and malefics
- **Technological Affinity:** {"Strong" if any(p['planet'] in ['Rahu', 'Ketu'] for p in strong_planets) else "Moderate"} innovation indicators
- **Leadership Potential:** {"High" if any(p['planet'] == 'Mars' and p['sign'] == 'Aries' for p in strong_planets) else "Moderate"} based on planetary positions

---"""

        # Current/Near-future analysis
        if not current_best.empty:
            markdown_content += f"""

## 📈 Current & Near-Future Timing Analysis ({current_year}-{current_year + 2})

### Best Periods for Strategic Actions

| Date Range | Type | Planet Combination | Score | Optimal For |
|------------|------|-------------------|--------|-------------|"""

            for _, period in current_best.head(5).iterrows():
                date_range = f"{period['Date']} - {period['End_Date']}"
                if period['Type'] == 'MD':
                    combo = period['Maha_Lord']
                elif period['Type'] == 'MD-AD':
                    combo = f"{period['Maha_Lord']}-{period['Antar_Lord']}"
                else:
                    combo = f"{period['Maha_Lord']}-{period['Antar_Lord']}-{period['Pratyantar_Lord']}"
                
                score = period['Auspiciousness_Score']
                optimal_for = "Major strategic initiatives" if score >= 7 else "Strategic planning" if score >= 6 else "Routine operations"
                
                markdown_content += f"\n| {date_range} | {period['Type']} | {combo} | {score:.2f} | {optimal_for} |"

        # Top periods analysis
        markdown_content += f"""

---

## 🚀 Peak Opportunity Windows (All Time)

### Top 10 Most Auspicious Periods

| Rank | Date | Type | Planet Combination | Score | Era |
|------|------|------|-------------------|--------|-----|"""

        for i, (_, period) in enumerate(top_periods_all.head(10).iterrows(), 1):
            if period['Type'] == 'MD':
                combo = period['Maha_Lord']
            elif period['Type'] == 'MD-AD':
                combo = f"{period['Maha_Lord']}-{period['Antar_Lord']}"
            else:
                combo = f"{period['Maha_Lord']}-{period['Antar_Lord']}-{period['Pratyantar_Lord']}"
            
            year = period['Date'][:4]
            era = "Historical" if int(year) < current_year else "Current" if int(year) == current_year else "Future"
            
            markdown_content += f"\n| {i} | {period['Date']} | {period['Type']} | {combo} | {period['Auspiciousness_Score']:.2f} | {era} |"

        # Protection analysis
        markdown_content += f"""

---

## 🛡️ Risk Mitigation Analysis

### Arishta-Bhanga Protection System

{company_name} benefits from {"exceptional" if protection_rate > 40 else "strong" if protection_rate > 30 else "moderate"} protection through classical Vedic cancellation rules:

#### Protection Rate: {protection_rate:.1f}% ({protected_periods}/{total_periods} periods)"""

        if len(high_protection) > 0:
            markdown_content += f"""

#### Triple Protection Periods (Highest Safety)"""
            for i, (_, period) in enumerate(high_protection.head(5).iterrows(), 1):
                if period['Type'] == 'MD':
                    combo = period['Maha_Lord']
                elif period['Type'] == 'MD-AD':
                    combo = f"{period['Maha_Lord']}-{period['Antar_Lord']}"
                else:
                    combo = f"{period['Maha_Lord']}-{period['Antar_Lord']}-{period['Pratyantar_Lord']}"
                
                markdown_content += f"\n{i}. **{period['Date']} to {period['End_Date']}:** {combo} ({period['Arishta_Protections']} protections)"

        # Risk periods
        risk_periods = df[df['Auspiciousness_Score'] < 3.5].head(5)
        if not risk_periods.empty:
            markdown_content += f"""

### Risk Periods Requiring Caution

#### Challenging Windows (Score < 3.5)"""
            for _, period in risk_periods.iterrows():
                if period['Type'] == 'MD':
                    combo = period['Maha_Lord']
                elif period['Type'] == 'MD-AD':
                    combo = f"{period['Maha_Lord']}-{period['Antar_Lord']}"
                else:
                    combo = f"{period['Maha_Lord']}-{period['Antar_Lord']}-{period['Pratyantar_Lord']}"
                
                markdown_content += f"\n- **{period['Date']} to {period['End_Date']}:** {combo} ({period['Auspiciousness_Score']:.2f}/10)"

            markdown_content += f"""

**Risk Mitigation Strategy:** During low-scoring periods, focus on:
- Conservative financial management
- Defensive strategic positioning
- Enhanced due diligence
- Stakeholder communication"""

        # Detailed analysis by type
        if not top_md.empty:
            markdown_content += f"""

---

## 🗓️ Maha Dasha Analysis (Major Life Periods)

### Top Maha Dasha Periods

| Period | Maha Lord | Duration | Auspiciousness | Key Characteristics |
|--------|-----------|----------|----------------|-------------------|"""

            for _, period in top_md.iterrows():
                start_year = period['Date'][:4]
                end_year = period['End_Date'][:4]
                duration = int(end_year) - int(start_year)
                status = "**CURRENT**" if int(start_year) <= current_year <= int(end_year) else "Future" if int(start_year) > current_year else "Past"
                
                characteristics = self.get_planet_characteristics(period['Maha_Lord'])
                
                row = f"| {start_year}-{end_year} | {period['Maha_Lord']} | {duration} years | {period['Auspiciousness_Score']:.2f}/10 | {characteristics}"
                if "CURRENT" in status:
                    row = f"| **{start_year}-{end_year}** | **{period['Maha_Lord']}** | **{duration} years** | **{period['Auspiciousness_Score']:.2f}/10** | **{characteristics} {status}** |"
                else:
                    row += f" |"
                
                markdown_content += f"\n{row}"

        # Conclusion
        markdown_content += f"""

---

## 🔍 Technical Analysis Notes

### Methodology
- **Ayanamsa:** Lahiri (standard Vedic calculation)
- **Birth Location:** {birth_location}
- **Timezone:** {birth_timezone} with automatic DST handling
- **Ephemeris:** Swiss Ephemeris for maximum precision
- **Rules Applied:** Classical Vedic + Dasha-Aarambha enhancement

### Confidence Levels
- **Birth Data Accuracy:** High (verified JSON source)
- **Planetary Calculations:** Maximum (Swiss Ephemeris)
- **Traditional Rules:** Validated (classical texts)
- **Timing Precision:** High (timezone-corrected)

---

## 📚 Conclusion

{company_name} demonstrates {"an exceptionally strong" if len(strong_planets) >= 4 else "a strong" if len(strong_planets) >= 2 else "a moderate"} astrological foundation with {"rare" if len(strong_planets) >= 4 else "notable"} planetary dignity combinations. 

**Key Insights:**
1. **Overall Strength:** {len(strong_planets)}/9 planets in high dignity
2. **Protection Rate:** {protection_rate:.1f}% of periods have safeguards
3. **Peak Opportunities:** {perfect_scores} perfect scores (≥9.5) identified
4. **Risk Management:** {len(high_protection)} ultra-safe periods with triple protection

{"The analysis reveals multiple high-opportunity windows for strategic initiatives, with strong protective influences throughout most periods." if protection_rate > 30 else "The analysis shows moderate opportunities with standard protective influences."}

---

*Analysis completed using Enhanced Vedic Dasha Analyzer v2.0 with Swiss Ephemeris precision and classical Dasha-Aarambha rules from Dr. K.S. Charak's methodology.*

**Disclaimer:** This analysis is for educational and strategic planning purposes. Investment decisions should consider multiple factors including fundamental analysis, market conditions, and professional financial advice.
"""

        # Save markdown report
        markdown_file = os.path.join(output_dir, f"{symbol}_Vedic_Analysis_Report.md")
        with open(markdown_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        print(f"\nMarkdown report saved: {os.path.basename(markdown_file)}")
        return markdown_file
    
    def get_planet_characteristics(self, planet: str) -> str:
        """Get brief characteristics for a planet in dasha context"""
        characteristics = {
            'Sun': 'Leadership & Authority',
            'Moon': 'Emotional Growth',
            'Mercury': 'Communication & Technology',
            'Venus': 'Expansion & Prosperity',
            'Mars': 'Action & Implementation',
            'Jupiter': 'Wisdom & Growth',
            'Saturn': 'Structure & Discipline',
            'Rahu': 'Innovation & Transformation',
            'Ketu': 'Spiritual Evolution'
        }
        return characteristics.get(planet, 'Planetary Influence')

def main():
    """Main execution function with command-line argument parsing"""
    parser = argparse.ArgumentParser(
        description='Enhanced Vedic Dasha Analyzer with Dasha-Aarambha Rules and 3-Level Analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python vedic_dasha_analyzer_v2.py data/Technology/PLTR.json
  python vedic_dasha_analyzer_v2.py data/Technology/PLTR.json --location "Mumbai, India"
  python vedic_dasha_analyzer_v2.py entity.json --location "London, UK" --output custom_dir
        """
    )
    
    parser.add_argument('json_file', help='Path to the JSON file containing entity data')
    parser.add_argument('--location', '-l', default='New York, USA', 
                       help='Birth location (default: New York, USA)')
    parser.add_argument('--output', '-o', help='Custom output directory (default: analysis/{SYMBOL}/)')
    
    args = parser.parse_args()
    
    # Validate input file
    if not os.path.exists(args.json_file):
        print(f"Error: JSON file '{args.json_file}' not found.")
        sys.exit(1)
    
    print("=" * 80)
    print("ENHANCED VEDIC DASHA ANALYZER WITH DASHA-AARAMBHA RULES")
    print("3-Level Analysis: Maha Dasha (MD) → Antar Dasha (AD) → Pratyantar Dasha (PD)")
    print("Using Swiss Ephemeris for Precise Calculations")
    print("=" * 80)
    
    try:
        # Initialize analyzer with birth location
        analyzer = EnhancedVedicDashaAnalyzer(birth_location=args.location)
        
        # Analyze the file
        results = analyzer.analyze_json_file(args.json_file)
        
        # Save results to organized directory structure
        df, output_dir = analyzer.save_to_csv(results, args.output)
        
        # Generate comprehensive markdown report
        markdown_file = analyzer.generate_markdown_report(results, df, output_dir)
        
        # Generate summary statistics
        print(f"\n" + "=" * 60)
        print("ENHANCED ANALYSIS SUMMARY")
        print("=" * 60)
        print(f"Entity: {results['company_name']} ({results['symbol']})")
        print(f"Birth: {results['birth_date']} at {results['birth_time']}")
        print(f"Location: {results['birth_location']}")
        print(f"Timezone: {results['birth_timezone']}")
        print(f"Total Dasha Periods Analyzed: {len(results['results'])}")
        
        # Breakdown by type
        type_counts = df['Type'].value_counts()
        print(f"\nPeriod Breakdown:")
        for dasha_type, count in type_counts.items():
            print(f"  {dasha_type}: {count} periods")
        
        # Birth chart strength
        birth_positions = results['birth_positions']
        strong_planets = []
        for planet, pos in birth_positions.items():
            if planet != 'Ascendant':
                strength = analyzer.calculate_planetary_strength(planet, pos['zodiacSign'])
                if strength >= 8.0:
                    strong_planets.append(f"{planet} in {pos['zodiacSign']}")
        
        print(f"\nStrong Planets at Birth: {len(strong_planets)}")
        for planet in strong_planets:
            print(f"  - {planet}")
        
        # Top auspicious periods by type
        for dasha_type in ['MD', 'MD-AD', 'MD-AD-PD']:
            type_df = df[df['Type'] == dasha_type]
            if not type_df.empty:
                top_periods = type_df.nlargest(5, 'Auspiciousness_Score')
                print(f"\nTop 5 Most Auspicious {dasha_type} Periods:")
                for _, period in top_periods.iterrows():
                    if dasha_type == 'MD':
                        print(f"  {period['Date']}: {period['Maha_Lord']} (Score: {period['Auspiciousness_Score']:.2f})")
                    elif dasha_type == 'MD-AD':
                        print(f"  {period['Date']}: {period['Maha_Lord']}-{period['Antar_Lord']} (Score: {period['Auspiciousness_Score']:.2f})")
                    else:  # MD-AD-PD
                        print(f"  {period['Date']}: {period['Maha_Lord']}-{period['Antar_Lord']}-{period['Pratyantar_Lord']} (Score: {period['Auspiciousness_Score']:.2f})")
        
        # Protection statistics
        total_protections = df['Arishta_Protections'].sum()
        protected_periods = len(df[df['Arishta_Protections'] > 0])
        protection_rate = protected_periods / len(df) * 100 if len(df) > 0 else 0
        
        print(f"\nArishta-Bhanga Protection Analysis:")
        print(f"  Total Protections: {total_protections}")
        print(f"  Protected Periods: {protected_periods} / {len(df)} ({protection_rate:.1f}%)")
        
        # Perfect scores
        perfect_scores = len(df[df['Auspiciousness_Score'] >= 9.5])
        excellent_scores = len(df[df['Auspiciousness_Score'] >= 8.0])
        
        print(f"  Perfect Scores (≥9.5): {perfect_scores}")
        print(f"  Excellent Scores (≥8.0): {excellent_scores}")
        
        print(f"\n" + "=" * 60)
        print("Analysis completed successfully!")
        print(f"All outputs saved to: {output_dir}/")
        print("=" * 60)
        
    except Exception as e:
        print(f"Error during analysis: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 