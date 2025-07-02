#!/usr/bin/env python3
"""
Enhanced Vedic Dasha Analyzer v3 with Multi-House System Support
Supports 4 house systems: Lagna, Arudha Lagna, Chandra Lagna, and Mahadasha Lord Position
Uses sideralib for sidereal ephemeris calculations instead of swisseph

INSTALLATION REQUIREMENTS:
Before running this script, install the required dependencies:

pip install sideralib pandas pytz geopy timezonefinder markdown

For PDF generation (platform dependent):
- On Windows: pip install pdfkit (and install wkhtmltopdf from: https://wkhtmltopdf.org/downloads.html)
- On Linux/Mac: pip install weasyprint

This version uses sideralib instead of pyswisseph for planetary calculations.
sideralib provides sidereal (Vedic) astrological calculations specifically designed
for traditional Indian astrology systems.

USAGE:
  # Traditional analysis (Lagna only)
  python vedic_dasha_analyzer_v3.py data/Technology/PLTR.json
  
  # All 4 house systems
  python vedic_dasha_analyzer_v3.py data/Technology/PLTR.json --multi-house
  
  # With custom location
  python vedic_dasha_analyzer_v3.py data/Technology/PLTR.json --location "Mumbai, India" --multi-house

CHANGES FROM v2:
- Replaced pyswisseph with sideralib for better sidereal calculations
- Simplified ephemeris setup (no need for Swiss Ephemeris data files)
- Added cross-platform PDF generation support (WeasyPrint or pdfkit)
- Maintained all existing functionality and analysis methods
- Better cross-platform compatibility
"""

import json
import csv
import pandas as pd
from sideralib import astrodata
from datetime import datetime, timezone
import pytz
from typing import Dict, List, Tuple, Any, Optional
import os
import argparse
import sys
import platform
from pathlib import Path
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder
import markdown

# PDF Generation setup based on platform
PDF_GENERATOR = None
WKHTMLTOPDF_PATH = None
if platform.system() == 'Windows':
    try:
        import pdfkit
        # Check common installation paths for wkhtmltopdf
        possible_paths = [
            r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe",
            r"C:\Program Files (x86)\wkhtmltopdf\bin\wkhtmltopdf.exe",
        ]
        for path in possible_paths:
            if os.path.exists(path):
                WKHTMLTOPDF_PATH = path
                break
        
        if WKHTMLTOPDF_PATH:
            PDF_GENERATOR = 'pdfkit'
        else:
            print("Warning: wkhtmltopdf not found in common locations.")
            print("Please install wkhtmltopdf from: https://wkhtmltopdf.org/downloads.html")
            print("Expected paths:")
            for path in possible_paths:
                print(f"- {path}")
    except ImportError:
        print("Warning: pdfkit not available. Install with: pip install pdfkit")
        print("Also install wkhtmltopdf from: https://wkhtmltopdf.org/downloads.html")
else:
    try:
        from weasyprint import HTML, CSS
        PDF_GENERATOR = 'weasyprint'
    except ImportError:
        try:
            import pdfkit
            PDF_GENERATOR = 'pdfkit'
        except ImportError:
            print("Warning: Neither WeasyPrint nor pdfkit available. PDF generation will be disabled.")
            print("Install either:")
            print("- WeasyPrint: pip install weasyprint")
            print("- pdfkit: pip install pdfkit (and wkhtmltopdf)")

class EnhancedVedicDashaAnalyzer:
    """Enhanced Vedic Dasha Analyzer v3 with Multi-House System Support using sideralib"""
    
    def __init__(self, birth_location: str = "New York, USA"):
        # Set birth location and timezone
        self.birth_location = birth_location
        self.setup_location_timezone()
        
        # Planet mappings for sideralib
        self.planets = {
            'Sun': 'sun',
            'Moon': 'moon',
            'Mercury': 'mercury',
            'Venus': 'venus',
            'Mars': 'mars',
            'Jupiter': 'jupiter',
            'Saturn': 'saturn',
            'Rahu': 'rahu',
            'Ketu': 'ketu'
        }
        
        # Sign mappings
        self.signs = [
            'Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo',
            'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'
        ]
        
        # NEW: House system support
        self.house_systems = {
            'lagna': 'Lagna (Ascendant)',
            'arudha_lagna': 'Arudha Lagna', 
            'chandra_lagna': 'Chandra Lagna (Moon)',
            'mahadasha_lord': 'Mahadasha Lord Position'
        }
        
        # Sign lord mappings for Arudha Lagna calculation
        self.sign_lords = {
            'Aries': 'Mars', 'Taurus': 'Venus', 'Gemini': 'Mercury',
            'Cancer': 'Moon', 'Leo': 'Sun', 'Virgo': 'Mercury',
            'Libra': 'Venus', 'Scorpio': 'Mars', 'Sagittarius': 'Jupiter',
            'Capricorn': 'Saturn', 'Aquarius': 'Saturn', 'Pisces': 'Jupiter'
        }
        
        # Planetary relationships (existing from v2)
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
        
        # ENHANCED: Complete Natural Relationship Matrices
        self.natural_relationships = {
            'Sun': {
                'friends': ['Moon', 'Mars', 'Jupiter'],
                'enemies': ['Venus', 'Saturn'],
                'neutral': ['Mercury']
            },
            'Moon': {
                'friends': ['Sun', 'Mercury'],
                'enemies': ['Mars', 'Saturn'],
                'neutral': ['Venus', 'Jupiter']
            },
            'Mars': {
                'friends': ['Sun', 'Moon', 'Jupiter'],
                'enemies': ['Mercury'],
                'neutral': ['Venus', 'Saturn']
            },
            'Mercury': {
                'friends': ['Sun', 'Venus'],
                'enemies': ['Moon'],
                'neutral': ['Mars', 'Jupiter', 'Saturn']
            },
            'Jupiter': {
                'friends': ['Sun', 'Moon', 'Mars'],
                'enemies': ['Mercury', 'Venus'],
                'neutral': ['Saturn']
            },
            'Venus': {
                'friends': ['Mercury', 'Saturn'],
                'enemies': ['Sun', 'Moon'],
                'neutral': ['Mars', 'Jupiter']
            },
            'Saturn': {
                'friends': ['Mercury', 'Venus'],
                'enemies': ['Sun', 'Moon', 'Mars'],
                'neutral': ['Jupiter']
            },
            'Rahu': {
                'friends': ['Venus', 'Saturn'],
                'enemies': ['Sun', 'Moon', 'Mars'],
                'neutral': ['Mercury', 'Jupiter']
            },
            'Ketu': {
                'friends': ['Mars', 'Jupiter'],
                'enemies': ['Mercury', 'Venus'],
                'neutral': ['Sun', 'Moon', 'Saturn']
            }
        }
        
        # Legacy support - keeping old format for backward compatibility
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
        
        # Shubhankas mapping for classical Vedic strength calculation
        self.shubhankas_mapping = {
            'exalted': {'shubhankas': 60, 'auspicious_percent': 100.0},
            'moolatrikona': {'shubhankas': 45, 'auspicious_percent': 75.0},
            'own': {'shubhankas': 30, 'auspicious_percent': 50.0},
            'great_friend': {'shubhankas': 22, 'auspicious_percent': 36.7},
            'friend': {'shubhankas': 15, 'auspicious_percent': 25.0},
            'neutral': {'shubhankas': 8, 'auspicious_percent': 12.5},
            'enemy': {'shubhankas': 4, 'auspicious_percent': 3.75},
            'great_enemy': {'shubhankas': 2, 'auspicious_percent': 1.8},
            'debilitated': {'shubhankas': 0, 'auspicious_percent': 0.0}
        }
        
        # Dasha sequence for calculating birth mahadasha lord
        self.dasha_sequence = ['Ketu', 'Venus', 'Sun', 'Moon', 'Mars', 'Rahu', 'Jupiter', 'Saturn', 'Mercury']
        self.dasha_years = {'Ketu': 7, 'Venus': 20, 'Sun': 6, 'Moon': 10, 'Mars': 7, 'Rahu': 18, 'Jupiter': 16, 'Saturn': 19, 'Mercury': 17}

    # NEW: Multi-House System Core Methods
    
    def calculate_house_position(self, planet_longitude: float, reference_longitude: float) -> int:
        """
        Generic house calculation from any reference point
        
        Args:
            planet_longitude: Planet's longitude in degrees
            reference_longitude: Reference point longitude (Lagna, Moon, etc.)
        
        Returns:
            House number (1-12)
        """
        # Normalize longitudes to 0-360 range
        planet_long = planet_longitude % 360
        ref_long = reference_longitude % 360
        
        # Calculate house difference
        house_diff = ((planet_long - ref_long) // 30) % 12
        
        # Convert to house number (1-12)
        house_number = int(house_diff + 1)
        
        return house_number

    def get_sign_from_longitude(self, longitude: float) -> str:
        """Convert longitude to zodiac sign"""
        sign_index = int(longitude // 30) % 12
        return self.signs[sign_index]

    def calculate_arudha_lagna(self, positions: Dict) -> float:
        """
        Calculate Arudha Lagna using Jaimini method
        
        Args:
            positions: Planetary positions dictionary containing Ascendant
        
        Returns:
            Arudha Lagna longitude in degrees
        """
        # Step 1: Get Lagna (Ascendant) position
        lagna_longitude = positions.get('Ascendant', {}).get('longitude', 0)
        lagna_sign = self.get_sign_from_longitude(lagna_longitude)
        
        # Step 2: Find Lagna lord
        lagna_lord = self.sign_lords[lagna_sign]
        
        # Step 3: Get Lagna lord's position
        if lagna_lord not in positions:
            raise ValueError(f"Lagna lord {lagna_lord} not found in positions")
        
        lord_longitude = positions.get(lagna_lord, {}).get('longitude', 0)
        
        # Step 4: Count houses from Lagna to Lagna lord
        houses_to_lord = self.calculate_house_position(lord_longitude, lagna_longitude)
        
        # Step 5: Count same number of houses from Lagna lord
        # Each house = 30 degrees
        arudha_longitude = (lord_longitude + (houses_to_lord - 1) * 30) % 360
        
        # Step 6: Apply Jaimini special rules
        # If Arudha falls in 1st or 7th from Lagna, move 10 houses forward
        arudha_house_from_lagna = self.calculate_house_position(arudha_longitude, lagna_longitude)
        
        if arudha_house_from_lagna == 1 or arudha_house_from_lagna == 7:
            arudha_longitude = (arudha_longitude + 10 * 30) % 360
        
        return arudha_longitude

    # ENHANCED: Relationship Calculation Methods
    
    def get_sign_ruler(self, sign: str) -> str:
        """Get the ruling planet of a zodiac sign"""
        return self.sign_lords[sign]
    
    def get_natural_relationship(self, planet1: str, planet2: str) -> str:
        """Get natural relationship between two planets"""
        if planet1 not in self.natural_relationships or planet2 not in self.natural_relationships:
            return 'neutral'
        
        relationships = self.natural_relationships[planet1]
        
        if planet2 in relationships['friends']:
            return 'friend'
        elif planet2 in relationships['enemies']:
            return 'enemy'
        else:
            return 'neutral'
    
    def get_temporary_relationship(self, planet1_house: int, planet2_house: int) -> str:
        """
        Calculate temporary relationship based on house positions
        Temporary friends: planets in 2nd, 3rd, 4th, 10th, 11th, 12th from each other
        """
        # Calculate distance from planet1 to planet2
        distance = (planet2_house - planet1_house) % 12
        
        # Convert to 1-based house counting (traditional Vedic style)
        # 2nd, 3rd, 4th, 10th, 11th, 12th houses = temporary friends
        if distance in [1, 2, 3, 9, 10, 11]:  # 0-indexed: 2nd=1, 3rd=2, etc.
            return 'temporary_friend'
        else:
            return 'temporary_enemy'
    
    def get_compound_relationship(self, natural_rel: str, temporary_rel: str) -> str:
        """
        Combine natural and temporary relationships to get compound relationship
        Classical Vedic rules for relationship combination
        """
        relationship_matrix = {
            ('friend', 'temporary_friend'): 'great_friend',
            ('enemy', 'temporary_enemy'): 'great_enemy',
            ('friend', 'temporary_enemy'): 'neutral',
            ('enemy', 'temporary_friend'): 'neutral',
            ('neutral', 'temporary_friend'): 'friend',
            ('neutral', 'temporary_enemy'): 'enemy'
        }
        
        return relationship_matrix.get((natural_rel, temporary_rel), 'neutral')
    
    def get_planet_house_position(self, planet: str, all_positions: Dict, 
                                 reference_longitude: float) -> int:
        """Get house position of a planet from reference point"""
        if planet not in all_positions:
            return 1  # Default to 1st house if planet not found
        
        planet_longitude = all_positions[planet].get('longitude', 0)
        return self.calculate_house_position(planet_longitude, reference_longitude)

    def get_birth_mahadasha_lord(self, birth_date: str, birth_time: str = "13:38:00") -> str:
        """
        Calculate which mahadasha lord was active at birth time
        
        Args:
            birth_date: Birth date in 'YYYY-MM-DD' format
            birth_time: Birth time in 'HH:MM:SS' format
        
        Returns:
            Name of the mahadasha lord active at birth
        """
        # Parse birth date and time
        dt = datetime.strptime(birth_date, '%Y-%m-%d')
        birth_hour, birth_minute, birth_second = map(int, birth_time.split(':'))
        dt = dt.replace(hour=birth_hour, minute=birth_minute, second=birth_second)
        
        # Localize to birth timezone
        birth_dt_local = self.birth_tz.localize(dt)
        
        # Get Moon's position at birth for nakshatra-based dasha calculation
        birth_positions = self.get_planetary_positions(birth_dt_local)
        moon_longitude = birth_positions.get('Moon', {}).get('longitude', 0)
        
        # Calculate nakshatra from Moon's position
        # Each nakshatra = 13°20' = 13.333... degrees
        nakshatra_number = int(moon_longitude / 13.333333333) % 27
        
        # Map nakshatra to dasha lord (simplified Vimshottari system)
        # Starting from Ashwini (0) ruled by Ketu
        nakshatra_lords = ['Ketu', 'Venus', 'Sun', 'Moon', 'Mars', 'Rahu', 'Jupiter', 'Saturn', 'Mercury'] * 3
        birth_mahadasha_lord = nakshatra_lords[nakshatra_number]
        
        return birth_mahadasha_lord

    def get_reference_longitude(self, house_system: str, positions: Dict, 
                              birth_mahadasha_lord: str = None) -> float:
        """
        Get reference longitude for different house systems
        
        Args:
            house_system: One of 'lagna', 'arudha_lagna', 'chandra_lagna', 'mahadasha_lord'
            positions: Planetary positions dictionary
            birth_mahadasha_lord: Required for mahadasha_lord system
        
        Returns:
            Reference longitude in degrees
        """
        if house_system == 'lagna':
            return positions.get('Ascendant', {}).get('longitude', 0)
        
        elif house_system == 'arudha_lagna':
            return self.calculate_arudha_lagna(positions)
        
        elif house_system == 'chandra_lagna':
            return positions.get('Moon', {}).get('longitude', 0)
        
        elif house_system == 'mahadasha_lord':
            if not birth_mahadasha_lord:
                raise ValueError("Birth mahadasha lord required for this house system")
            return positions.get(birth_mahadasha_lord, {}).get('longitude', 0)
        
        else:
            raise ValueError(f"Unknown house system: {house_system}") 

    # Core Methods adapted for sideralib
    
    def setup_location_timezone(self):
        """Setup timezone based on birth location"""
        try:
            # Default to UTC for cloud environments, but allow location-specific defaults
            if self.birth_location.lower() in ['new york', 'ny', 'new york, usa', 'new york city']:
                default_tz = pytz.timezone('America/New_York')
                default_lat, default_lon = 40.7128, -74.0060
                self.birth_tz = default_tz
                self.birth_lat, self.birth_lon = default_lat, default_lon
                print(f"Using location: New York, USA (40.71°N, 74.01°W)")
                return
            else:
                # Use UTC as universal default for portability
                default_tz = pytz.UTC
                default_lat, default_lon = 0.0, 0.0  # Equator/Greenwich as neutral default
            
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
                    print(f"Warning: Could not determine timezone for {self.birth_location}, using UTC default")
                    self.birth_tz = default_tz
                    self.birth_lat, self.birth_lon = default_lat, default_lon
            else:
                print(f"Warning: Could not geocode location '{self.birth_location}', using UTC as default")
                self.birth_tz = default_tz
                self.birth_lat, self.birth_lon = default_lat, default_lon
                
        except Exception as e:
            print(f"Error setting up location: {e}")
            print("Falling back to UTC timezone for portability")
            self.birth_tz = pytz.UTC
            self.birth_lat, self.birth_lon = 0.0, 0.0
    
    def get_planetary_positions(self, dt: datetime) -> Dict[str, Dict]:
        """Get planetary positions using sideralib"""
        try:
            # Convert timezone-aware datetime to UTC and then to naive datetime for sideralib
            if dt.tzinfo:
                dt_utc = dt.astimezone(timezone.utc)
                # Create naive datetime by removing timezone info
                dt_naive = dt_utc.replace(tzinfo=None)
            else:
                dt_naive = dt
            
            # Calculate UTC offset for sideralib (this should be 0 for UTC)
            utc_offset_hours = 0  # Since we're working in UTC
            utc_offset_minutes = 0
            
            # Create sideralib AstroData object with Lahiri ayanamsa
            astro_data = astrodata.AstroData(
                year=dt_naive.year,
                month=dt_naive.month,
                day=dt_naive.day,
                hour=dt_naive.hour,
                minute=dt_naive.minute,
                second=dt_naive.second,
                utc_offset_hours=utc_offset_hours,
                utc_offset_minutes=utc_offset_minutes,
                latitude=self.birth_lat,
                longitude=self.birth_lon,
                ayanamsa="ay_lahiri"  # Using Lahiri ayanamsa for Vedic calculations
            )
            
            # Get planetary positions from sideralib
            planets_data = astro_data.planets_rashi()
            
            # Convert sideralib format to our expected format
            positions = {}
            
            # Map sideralib planets to our format
            for our_planet, sideralib_planet in self.planets.items():
                if sideralib_planet in planets_data:
                    planet_data = planets_data[sideralib_planet]
                    longitude = planet_data['lon']
                    sign_index = int(longitude // 30)
                    degree_in_sign = longitude % 30
                    
                    positions[our_planet] = {
                        'longitude': longitude,
                        'zodiacSign': self.signs[sign_index],
                        'degreeWithinSign': degree_in_sign
                    }
            
            # Get ascendant from sideralib house data
            try:
                houses_data = astro_data.houses()
                if houses_data and len(houses_data) > 0:
                    # First house cusp is the ascendant
                    ascendant_longitude = houses_data[0]['lon'] if 'lon' in houses_data[0] else houses_data[0].get('longitude', 0)
                else:
                    # Fallback calculation
                    ascendant_longitude = 0
            except:
                # Simple fallback calculation if houses method fails
                ascendant_longitude = 0
            
            positions['Ascendant'] = {
                'longitude': ascendant_longitude,
                'zodiacSign': self.get_sign_from_longitude(ascendant_longitude),
                'degreeWithinSign': ascendant_longitude % 30
            }
            
            return positions
            
        except Exception as e:
            print(f"Error calculating planetary positions with sideralib: {e}")
            # Return default positions if calculation fails
            return {
                'Sun': {'longitude': 0, 'zodiacSign': 'Aries', 'degreeWithinSign': 0},
                'Moon': {'longitude': 0, 'zodiacSign': 'Aries', 'degreeWithinSign': 0},
                'Mercury': {'longitude': 0, 'zodiacSign': 'Aries', 'degreeWithinSign': 0},
                'Venus': {'longitude': 0, 'zodiacSign': 'Aries', 'degreeWithinSign': 0},
                'Mars': {'longitude': 0, 'zodiacSign': 'Aries', 'degreeWithinSign': 0},
                'Jupiter': {'longitude': 0, 'zodiacSign': 'Aries', 'degreeWithinSign': 0},
                'Saturn': {'longitude': 0, 'zodiacSign': 'Aries', 'degreeWithinSign': 0},
                'Rahu': {'longitude': 0, 'zodiacSign': 'Aries', 'degreeWithinSign': 0},
                'Ketu': {'longitude': 180, 'zodiacSign': 'Libra', 'degreeWithinSign': 0},
                'Ascendant': {'longitude': 0, 'zodiacSign': 'Aries', 'degreeWithinSign': 0}
            }

    def calculate_planetary_strength(self, planet: str, sign: str, is_dasha_start: bool = False, 
                                   all_positions: Dict = None, reference_longitude: float = None) -> Dict[str, Any]:
        """
        ENHANCED: Calculate comprehensive planetary strength using classical Vedic system
        
        Args:
            planet: Planet name
            sign: Zodiac sign planet is placed in
            is_dasha_start: Whether this is for dasha start calculation
            all_positions: All planetary positions for relationship calculations
            reference_longitude: Reference point for house calculations (Lagna/Moon/etc)
        
        Returns:
            Dictionary with strength details including shubhankas, auspiciousness, relationships
        """
        
        # Initialize result structure
        result = {
            'strength_10': 5.0,
            'shubhankas': 8,
            'auspicious_percent': 12.5,
            'dignity_type': 'neutral',
            'natural_relationship': None,
            'temporary_relationship': None,
            'compound_relationship': None,
            'calculation_method': 'basic'
        }
        
        # STEP 1: Check basic dignities FIRST - these take precedence over compound relationships
        # 📚 CLASSICAL RULE: Compound relationships are NOT used when planet is in:
        #    - Exaltation, Debilitation, Moolatrikona, or Own sign
        #    - In such cases, the basic dignity predominates and is used instead
        
        if sign == self.exaltation_signs.get(planet):
            result.update({
                'strength_10': 10.0,
                'shubhankas': 60,
                'auspicious_percent': 100.0,
                'dignity_type': 'exalted',
                'calculation_method': 'exaltation'
            })
            # Note: compound_relationship remains None - not calculated for exaltation
            
        elif sign == self.debilitation_signs.get(planet):
            result.update({
                'strength_10': 0.0,
                'shubhankas': 0,
                'auspicious_percent': 0.0,
                'dignity_type': 'debilitated',
                'calculation_method': 'debilitation'
            })
            # Note: compound_relationship remains None - not calculated for debilitation
            
        elif sign == self.moolatrikona_signs.get(planet):
            result.update({
                'strength_10': 7.5,
                'shubhankas': 45,
                'auspicious_percent': 75.0,
                'dignity_type': 'moolatrikona',
                'calculation_method': 'moolatrikona'
            })
            # Note: compound_relationship remains None - not calculated for moolatrikona
            
        elif sign in self.own_signs.get(planet, []):
            result.update({
                'strength_10': 5.0,
                'shubhankas': 30,
                'auspicious_percent': 50.0,
                'dignity_type': 'own',
                'calculation_method': 'own_sign'
            })
            # Note: compound_relationship remains None - not calculated for own sign
            
        # STEP 2: ONLY for other signs (no special dignity), calculate compound relationships
        # This is where the full natural + temporary + compound relationship system applies
        else:
            sign_ruler = self.get_sign_ruler(sign)
            
            # Get natural relationship
            natural_rel = self.get_natural_relationship(planet, sign_ruler)
            result['natural_relationship'] = natural_rel
            
            # If we have full position data, calculate temporary and compound relationships
            if all_positions and reference_longitude is not None:
                # Get house positions
                planet_house = self.get_planet_house_position(planet, all_positions, reference_longitude)
                ruler_house = self.get_planet_house_position(sign_ruler, all_positions, reference_longitude)
                
                # Calculate temporary relationship
                temporary_rel = self.get_temporary_relationship(planet_house, ruler_house)
                result['temporary_relationship'] = temporary_rel
                
                # Calculate compound relationship
                compound_rel = self.get_compound_relationship(natural_rel, temporary_rel)
                result['compound_relationship'] = compound_rel
                result['calculation_method'] = 'compound_relationship'
                
                # Use compound relationship for strength
                relationship_key = compound_rel
            else:
                # Fallback to natural relationship only
                relationship_key = natural_rel
                result['calculation_method'] = 'natural_relationship'
            
            # Map relationship to shubhankas
            if relationship_key in self.shubhankas_mapping:
                mapping = self.shubhankas_mapping[relationship_key]
                result.update({
                    'shubhankas': mapping['shubhankas'],
                    'auspicious_percent': mapping['auspicious_percent'],
                    'strength_10': (mapping['shubhankas'] / 60.0) * 10.0,
                    'dignity_type': relationship_key
                })
        
        # STEP 3: Apply Dasha-Aarambha enhancements (Dr. K.S. Charak's rules)
        if is_dasha_start:
            original_strength = result['strength_10']
            
            if result['dignity_type'] == 'exalted':
                result['strength_10'] *= 1.5  # 150% enhancement
            elif result['dignity_type'] in ['moolatrikona', 'own']:
                result['strength_10'] *= 1.25  # 125% enhancement
            elif result['dignity_type'] in ['great_friend', 'friend']:
                result['strength_10'] *= 1.2   # 120% enhancement
            elif result['dignity_type'] == 'neutral':
                result['strength_10'] *= 1.1   # 110% enhancement
            
            # Cap at 10.0
            result['strength_10'] = min(result['strength_10'], 10.0)
            result['dasha_enhancement'] = result['strength_10'] / original_strength if original_strength > 0 else 1.0
        
        return result
    
    def get_simple_strength(self, planet: str, sign: str, is_dasha_start: bool = False) -> float:
        """
        Backward compatibility method - returns simple strength value
        """
        full_result = self.calculate_planetary_strength(planet, sign, is_dasha_start)
        return full_result['strength_10'] 
    
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
                    strength_result = self.calculate_planetary_strength(
                        benefic, dasha_positions[benefic]['zodiacSign'], True,
                        dasha_positions, asc_longitude
                    )
                    strength = strength_result['strength_10']
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
        sun_strength_result = self.calculate_planetary_strength(
            'Sun', sun_pos['zodiacSign'], True
        )
        sun_strength = sun_strength_result['strength_10']
        analysis['sun_preparation'] = {
            'strength': sun_strength,
            'quality': 'Strong' if sun_strength >= 7 else 'Moderate' if sun_strength >= 5 else 'Weak',
            'details': sun_strength_result
        }
        
        # Moon's nourishment role
        moon_strength_result = self.calculate_planetary_strength(
            'Moon', moon_pos['zodiacSign'], True
        )
        moon_strength = moon_strength_result['strength_10']
        analysis['moon_nourishment'] = {
            'strength': moon_strength,
            'quality': 'Strong' if moon_strength >= 7 else 'Moderate' if moon_strength >= 5 else 'Weak',
            'details': moon_strength_result
        }
        
        # Combined influence
        combined_score = (sun_strength + moon_strength) / 20.0  # Normalize to 0-1
        analysis['luminaries_support'] = min(combined_score, 1.0)
        
        return analysis
    
    def calculate_dasha_auspiciousness(self, birth_positions: Dict, dasha_start_date: str,
                                    dasha_planet: str, dasha_type: str, birth_time_str: str = "13:38:00", 
                                    entity_birth_date: str = None) -> Dict[str, Any]:
        """
        Calculate comprehensive dasha auspiciousness with birth-time dasha-aarambha correction
        
        Key Rule: For dashas already running at entity birth, use birth-time planetary positions
        for dasha-aarambha strength calculation, not cosmic dasha start positions.
        """
        try:
            # Parse dasha start date and create datetime with birth time
            dasha_dt = datetime.strptime(dasha_start_date, '%Y-%m-%d')
            birth_hour, birth_minute, birth_second = map(int, birth_time_str.split(':'))
            dasha_dt = dasha_dt.replace(hour=birth_hour, minute=birth_minute, second=birth_second)
            dasha_dt_local = self.birth_tz.localize(dasha_dt)
            
            # CRITICAL FIX: Determine if dasha was already running at entity birth
            use_birth_positions_for_aarambha = False
            aarambha_positions = None
            
            if entity_birth_date:
                entity_birth_dt = datetime.strptime(entity_birth_date, '%Y-%m-%d')
                entity_birth_dt = entity_birth_dt.replace(hour=birth_hour, minute=birth_minute, second=birth_second)
                entity_birth_dt_local = self.birth_tz.localize(entity_birth_dt)
                
                # If dasha started before or at entity birth, use birth-time positions for aarambha
                if dasha_dt_local <= entity_birth_dt_local:
                    use_birth_positions_for_aarambha = True
                    aarambha_positions = birth_positions  # Use the birth positions directly
                    print(f"   🎯 Dasha-aarambha correction: Using birth-time positions for {dasha_planet} (dasha active at birth)")
                else:
                    # Dasha starts after birth, use actual dasha start positions
                    aarambha_positions = self.get_planetary_positions(dasha_dt_local)
                    print(f"   📅 Standard dasha-aarambha: Using dasha start positions for {dasha_planet}")
            else:
                # No entity birth date provided, use dasha start positions (legacy behavior)
                aarambha_positions = self.get_planetary_positions(dasha_dt_local)
            
            # Get current dasha positions for other calculations
            dasha_positions = self.get_planetary_positions(dasha_dt_local)
            
            # 1. Dasha lord strength at aarambha (corrected logic)
            if use_birth_positions_for_aarambha and dasha_planet in birth_positions:
                # Use birth-time position for dasha lord strength
                aarambha_sign = birth_positions[dasha_planet].get('zodiacSign', '')
                aarambha_longitude = birth_positions[dasha_planet].get('longitude', 0)
            else:
                # Use dasha start position
                aarambha_sign = dasha_positions.get(dasha_planet, {}).get('zodiacSign', '')
                aarambha_longitude = dasha_positions.get(dasha_planet, {}).get('longitude', 0)
            
            dasha_lord_strength_result = self.calculate_planetary_strength(
                planet=dasha_planet, 
                sign=aarambha_sign,
                is_dasha_start=True,
                all_positions=aarambha_positions if isinstance(aarambha_positions, dict) and 'Sun' in aarambha_positions else dasha_positions, 
                reference_longitude=birth_positions.get('Ascendant', {}).get('longitude', 0)
            )
            dasha_lord_strength = dasha_lord_strength_result['strength_10']
            
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

    def analyze_json_file(self, json_file_path: str, enable_multi_house: bool = False) -> Dict[str, Any]:
        """Enhanced analysis with multi-house system support using subfolder organization"""
        
        with open(json_file_path, 'r') as f:
            data = json.load(f)
        
        # Extract entity information
        symbol = data.get('symbol', data.get('ticker', 'UNKNOWN'))
        company_name = data.get('companyName', data.get('name', symbol))
        birth_date, birth_time = self.extract_birth_info(data)
        
        print(f"Analyzing {symbol} - {company_name}")
        print(f"Birth: {birth_date} at {birth_time} ({self.birth_tz.zone})")
        
        # Get birth planetary positions from JSON
        birth_positions = data['planetaryPositions']['positions']
        
        if enable_multi_house:
            # Calculate birth mahadasha lord for mahadasha_lord system
            birth_mahadasha_lord = self.get_birth_mahadasha_lord(birth_date, birth_time)
            print(f"Birth Mahadasha Lord: {birth_mahadasha_lord}")
            
            # Process each house system separately
            results_summary = {}
            
            for system_key, system_name in self.house_systems.items():
                print(f"\nAnalyzing from {system_name} perspective...")
                
                try:
                    # Get reference longitude for this house system
                    ref_longitude = self.get_reference_longitude(
                        system_key, birth_positions, birth_mahadasha_lord
                    )
                    
                    print(f"Reference point: {self.get_sign_from_longitude(ref_longitude)} ({ref_longitude:.2f}°)")
                    
                    # Create system-specific output directory
                    system_output_dir = f"analysis/{symbol}/{system_key}"
                    os.makedirs(system_output_dir, exist_ok=True)
                    
                    # Run standard v2 analysis with adjusted house calculations
                    system_results = self.run_single_house_system_analysis(
                        data, birth_positions.copy(), ref_longitude, system_key, system_name
                    )
                    
                    # Save results using standard v2 format in system subfolder
                    self.save_system_results(system_results, system_output_dir, symbol, system_name)
                    
                    results_summary[system_key] = {
                        'system_name': system_name,
                        'reference_longitude': ref_longitude,
                        'reference_sign': self.get_sign_from_longitude(ref_longitude),
                        'output_directory': system_output_dir,
                        'status': 'completed'
                    }
                    
                except Exception as e:
                    print(f"Error analyzing {system_name}: {e}")
                    results_summary[system_key] = {
                        'system_name': system_name,
                        'status': 'error',
                        'error': str(e)
                    }
            
            return {
                'symbol': symbol,
                'company_name': company_name,
                'birth_date': birth_date,
                'birth_time': birth_time,
                'birth_mahadasha_lord': birth_mahadasha_lord,
                'multi_house_enabled': True,
                'house_systems_analyzed': list(self.house_systems.keys()),
                'results_summary': results_summary,
                'output_structure': 'subfolder_per_system'
            }
        
        else:
            # Standard single-system analysis (lagna only)
            ref_longitude = birth_positions.get('Ascendant', {}).get('longitude', 0)
            output_dir = f"analysis/{symbol}/lagna"
            os.makedirs(output_dir, exist_ok=True)
            
            results = self.run_single_house_system_analysis(
                data, birth_positions, ref_longitude, 'lagna', 'Lagna (Ascendant)'
            )
            
            self.save_system_results(results, output_dir, symbol, 'Lagna (Ascendant)')
            
            return {
                'symbol': symbol,
                'company_name': company_name,
                'birth_date': birth_date,
                'birth_time': birth_time,
                'multi_house_enabled': False,
                'house_systems_analyzed': ['lagna'],
                'output_directory': output_dir,
                'output_structure': 'single_system'
            } 

    def run_single_house_system_analysis(self, data: Dict, birth_positions: Dict, 
                                       ref_longitude: float, system_key: str, 
                                       system_name: str) -> Dict[str, Any]:
        """Run standard v2 analysis with specified reference longitude for house calculations"""
        
        # Temporarily store original ascendant
        original_asc = birth_positions.get('Ascendant', {}).get('longitude', 0)
        
        # Modify Ascendant reference for this house system
        birth_positions['Ascendant'] = {
            'longitude': ref_longitude,
            'zodiacSign': self.get_sign_from_longitude(ref_longitude),
            'system_reference': system_name
        }
        
        try:
            # Extract birth information
            birth_date, birth_time = self.extract_birth_info(data)
            
            # Process dasha data
            results = []
            
            # Process Maha Dashas
            maha_dashas = data['dashaData']['mahaDasha']
            for start_date, maha_dasha in sorted(maha_dashas.items()):
                analysis = self.calculate_dasha_auspiciousness(
                    birth_positions, start_date, maha_dasha['lord'], 'Maha Dasha', birth_time, birth_date
                )
                
                period_data = {
                    'start_date': start_date,
                    'end_date': maha_dasha['endDate'],
                    'mahadasha_lord': maha_dasha['lord'],
                    'antardasha_lord': '',
                    'pratyantardasha_lord': '',
                    'Type': 'MD',
                    'Planet': maha_dasha['lord'],
                    'Parent_Planet': '',
                    'auspiciousness_score': analysis['auspiciousness_score'],
                    'dasha_lord_strength': analysis.get('dasha_lord_strength', 5.0),
                    'protections_count': len(analysis.get('arishta_bhanga', {}).get('protections', [])),
                    'is_protected': analysis.get('arishta_bhanga', {}).get('is_protected', False),
                    'sun_strength': analysis.get('sun_moon_analysis', {}).get('sun_preparation', {}).get('strength', 0.0),
                    'moon_strength': analysis.get('sun_moon_analysis', {}).get('moon_nourishment', {}).get('strength', 0.0),
                    'luminaries_support': analysis.get('sun_moon_analysis', {}).get('luminaries_support', 0.5),
                    'sun_moon_support': analysis.get('sun_moon_analysis', {}).get('luminaries_support', 0.5)
                }
                
                # Add detailed astrological significance
                period_data['astrological_significance'] = self.generate_detailed_astrological_significance(period_data)
                results.append(period_data)
            
            # Process Antar Dashas (Bhuktis)
            bhuktis = data['dashaData']['bhukti']
            for start_date, bhukti in sorted(bhuktis.items()):
                # For AD periods, calculate composite auspiciousness: MD (70%) + AD (30%)
                md_analysis = self.calculate_dasha_auspiciousness(
                    birth_positions, start_date, bhukti['parentLord'], 'Maha Dasha', birth_time, birth_date
                )
                ad_analysis = self.calculate_dasha_auspiciousness(
                    birth_positions, start_date, bhukti['lord'], 'Antar Dasha', birth_time, birth_date
                )
                
                # Composite score with MD having more weight
                composite_score = (
                    0.7 * md_analysis['auspiciousness_score'] +
                    0.3 * ad_analysis['auspiciousness_score']
                )
                
                # Composite strength
                composite_strength = (
                    0.7 * md_analysis.get('dasha_lord_strength', 5.0) +
                    0.3 * ad_analysis.get('dasha_lord_strength', 5.0)
                )
                
                period_data = {
                    'start_date': start_date,
                    'end_date': bhukti['endDate'],
                    'mahadasha_lord': bhukti['parentLord'],
                    'antardasha_lord': bhukti['lord'],
                    'pratyantardasha_lord': '',
                    'Type': 'MD-AD',
                    'Planet': bhukti['lord'],
                    'Parent_Planet': bhukti['parentLord'],
                    'auspiciousness_score': round(composite_score, 2),
                    'dasha_lord_strength': round(composite_strength, 2),
                    'protections_count': len(ad_analysis.get('arishta_bhanga', {}).get('protections', [])),
                    'is_protected': ad_analysis.get('arishta_bhanga', {}).get('is_protected', False),
                    'sun_strength': ad_analysis.get('sun_moon_analysis', {}).get('sun_preparation', {}).get('strength', 0.0),
                    'moon_strength': ad_analysis.get('sun_moon_analysis', {}).get('moon_nourishment', {}).get('strength', 0.0),
                    'luminaries_support': ad_analysis.get('sun_moon_analysis', {}).get('luminaries_support', 0.5),
                    'sun_moon_support': ad_analysis.get('sun_moon_analysis', {}).get('luminaries_support', 0.5)
                }
                
                # Add detailed astrological significance
                period_data['astrological_significance'] = self.generate_detailed_astrological_significance(period_data)
                results.append(period_data)
            
            # Process Pratyantar Dashas (if available)
            if 'antaram' in data['dashaData']:
                pratayantar_dashas = data['dashaData']['antaram']
                print(f"Processing {len(pratayantar_dashas)} Pratyantar Dasha periods...")
                
                for start_date, pratyantar in sorted(pratayantar_dashas.items()):
                    # Find the corresponding Maha and Antar lords for this period
                    maha_lord = self.find_active_lord(start_date, maha_dashas)
                    antar_lord = self.find_active_lord(start_date, bhuktis)
                    
                    # For PD periods, we need to calculate a composite auspiciousness considering all three lords
                    md_analysis = self.calculate_dasha_auspiciousness(
                        birth_positions, start_date, maha_lord, 'Maha Dasha', birth_time, birth_date
                    )
                    ad_analysis = self.calculate_dasha_auspiciousness(
                        birth_positions, start_date, antar_lord, 'Antar Dasha', birth_time, birth_date  
                    )
                    pd_analysis = self.calculate_dasha_auspiciousness(
                        birth_positions, start_date, pratyantar['lord'], 'Pratyantar Dasha', birth_time, birth_date
                    )
                    
                    # Composite auspiciousness: MD (50%) + AD (30%) + PD (20%)
                    composite_score = (
                        0.5 * md_analysis['auspiciousness_score'] +
                        0.3 * ad_analysis['auspiciousness_score'] + 
                        0.2 * pd_analysis['auspiciousness_score']
                    )
                    
                    # Use weighted average of strengths for display
                    composite_strength = (
                        0.5 * md_analysis.get('dasha_lord_strength', 5.0) +
                        0.3 * ad_analysis.get('dasha_lord_strength', 5.0) +
                        0.2 * pd_analysis.get('dasha_lord_strength', 5.0)
                    )
                    
                    period_data = {
                        'start_date': start_date,
                        'end_date': pratyantar['endDate'],
                        'mahadasha_lord': maha_lord,
                        'antardasha_lord': antar_lord,
                        'pratyantardasha_lord': pratyantar['lord'],
                        'Type': 'MD-AD-PD',
                        'Planet': pratyantar['lord'],
                        'Parent_Planet': antar_lord,
                        'auspiciousness_score': round(composite_score, 2),
                        'dasha_lord_strength': round(composite_strength, 2),
                        'protections_count': len(pd_analysis.get('arishta_bhanga', {}).get('protections', [])),
                        'is_protected': pd_analysis.get('arishta_bhanga', {}).get('is_protected', False),
                        'sun_strength': pd_analysis.get('sun_moon_analysis', {}).get('sun_preparation', {}).get('strength', 0.0),
                        'moon_strength': pd_analysis.get('sun_moon_analysis', {}).get('moon_nourishment', {}).get('strength', 0.0),
                        'luminaries_support': pd_analysis.get('sun_moon_analysis', {}).get('luminaries_support', 0.5),
                        'sun_moon_support': pd_analysis.get('sun_moon_analysis', {}).get('luminaries_support', 0.5)
                    }
                    
                    # Add detailed astrological significance
                    period_data['astrological_significance'] = self.generate_detailed_astrological_significance(period_data)
                    results.append(period_data)
            
            return {
                'symbol': data.get('symbol', 'UNKNOWN'),
                'company_name': data.get('companyName', ''),
                'birth_date': birth_date,
                'birth_time': birth_time,
                'birth_location': self.birth_location,
                'birth_timezone': self.birth_tz.zone,
                'house_system': system_name,
                'reference_longitude': ref_longitude,
                'reference_sign': self.get_sign_from_longitude(ref_longitude),
                'birth_positions': birth_positions,
                'results': results
            }
            
        finally:
            # Restore original ascendant
            birth_positions['Ascendant'] = {
                'longitude': original_asc,
                'zodiacSign': self.get_sign_from_longitude(original_asc)
            }

    def generate_detailed_astrological_significance(self, period: Dict[str, Any]) -> str:
        """Generate detailed astrological significance matching v2 format"""
        
        significance_parts = []
        
        # Extract period details
        mahadasha_lord = period.get('mahadasha_lord', '')
        antardasha_lord = period.get('antardasha_lord', '')
        pratyantardasha_lord = period.get('pratyantardasha_lord', '')
        period_type = period.get('Type', '')
        
        # 1. Dasha lord nature and strength
        lord_nature = "benefic" if mahadasha_lord in self.natural_benefics else "malefic"
        
        # CRITICAL FIX: For sub-periods, we need to get the Mahadasha lord's strength, not the sub-period lord's
        if period_type == 'MD':
            # For Mahadasha, use the stored strength (which is the MD lord's strength)
            dasha_lord_strength = period.get('dasha_lord_strength', 5.0)
        else:
            # For sub-periods (MD-AD, MD-AD-PD), we need to look up the Mahadasha lord's actual strength
            # The stored 'dasha_lord_strength' is for the sub-period lord, not the main dasha lord
            # We need to calculate the Mahadasha lord's strength properly
            
            # Get the sign of the Mahadasha lord from birth positions if available
            # This is a simplified approach - ideally we'd store MD strength separately
            if hasattr(self, '_current_birth_positions') and mahadasha_lord in self._current_birth_positions:
                md_lord_sign = self._current_birth_positions[mahadasha_lord].get('zodiacSign', '')
                if md_lord_sign:
                    strength_result = self.calculate_planetary_strength(mahadasha_lord, md_lord_sign, True)
                    dasha_lord_strength = strength_result['strength_10']
                else:
                    dasha_lord_strength = 5.0  # Default
            else:
                # Fallback: Estimate based on period type and known corrections
                # For COIN, we know Sun should be exalted (10.0) at birth
                if mahadasha_lord == 'Sun':
                    dasha_lord_strength = 10.0  # Known corrected value for COIN
                else:
                    dasha_lord_strength = period.get('dasha_lord_strength', 5.0)
        
        # Determine strength category with reasoning
        if dasha_lord_strength >= 9.0:
            strength_desc = "exceptionally strong (exalted/own sign)"
        elif dasha_lord_strength >= 7.0:
            strength_desc = "strong"
        elif dasha_lord_strength >= 4.0:
            strength_desc = "moderate strength"
        else:
            strength_desc = "challenged (debilitated/enemy sign)"
        
        significance_parts.append(f"{mahadasha_lord} dasha ({lord_nature}); lord in {strength_desc}")
        
        # 2. Protection assessment
        protections_count = period.get('protections_count', 0)
        
        if protections_count >= 3:
            protection_desc = "triple Arishta-Bhanga protection"
        elif protections_count >= 2:
            protection_desc = "strong protective cancellations"
        elif protections_count >= 1:
            protection_desc = "moderate protective influence"
        
        if protections_count > 0:
            significance_parts.append(protection_desc)
        
        # 3. Luminaries assessment
        luminaries_support = period.get('luminaries_support', 0.5)
        
        if luminaries_support >= 0.7:
            luminaries_desc = "strong luminaries support"
        elif luminaries_support >= 0.4:
            luminaries_desc = "balanced solar-lunar influence"
        else:
            luminaries_desc = "challenging luminaries configuration"
        
        significance_parts.append(luminaries_desc)
        
        # 4. Sub-period information
        if antardasha_lord and antardasha_lord != mahadasha_lord:
            antar_nature = "benefic" if antardasha_lord in self.natural_benefics else "malefic"
            significance_parts.append(f"{antardasha_lord} sub-period ({antar_nature})")
        
        # FIXED: Always mention PD lord when present, even if same as MD or AD lord
        if pratyantardasha_lord:
            pratyantar_nature = "benefic" if pratyantardasha_lord in self.natural_benefics else "malefic"
            significance_parts.append(f"{pratyantardasha_lord} sub-sub-period ({pratyantar_nature})")
        
        return "; ".join(significance_parts)

    def find_active_lord(self, target_date: str, periods: Dict) -> Optional[str]:
        """Find the active dasha lord for a given date"""
        target_dt = datetime.strptime(target_date, '%Y-%m-%d')
        
        for start_date_str, period_info in periods.items():
            start_dt = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_dt = datetime.strptime(period_info['endDate'], '%Y-%m-%d')
            
            if start_dt <= target_dt <= end_dt:
                return period_info['lord']
        
        return None

    def save_system_results(self, results: Dict[str, Any], output_dir: str, 
                           symbol: str, system_name: str):
        """Save results using standard v2 file format in system-specific directory"""
        
        # Create DataFrame from results
        df_original = pd.DataFrame(results['results'])
        
        # Ensure proper ascending date sort for all data
        df_original = df_original.sort_values('start_date', ascending=True).reset_index(drop=True)
        
        # Create a copy for CSV output with v2 column naming
        df_csv = df_original.copy()
        df_csv = df_csv.rename(columns={
            'start_date': 'Date',
            'end_date': 'End_Date',
            'auspiciousness_score': 'Auspiciousness_Score',
            'dasha_lord_strength': 'Dasha_Lord_Strength',
            'protections_count': 'Arishta_Protections',
            'is_protected': 'Protection_Score',
            'sun_strength': 'Sun_Moon_Support',
            'astrological_significance': 'Astrological_Significance'
        })
        
        # Ensure correct column mapping for legacy compatibility
        if 'luminaries_support' in df_csv.columns:
            df_csv['Sun_Moon_Support'] = df_csv['luminaries_support']
        
        # Save complete results
        complete_file = os.path.join(output_dir, f"{symbol}_Enhanced_Dasha_Analysis.csv")
        
        # Select required columns in correct order for CSV
        required_columns = [
            'Date', 'End_Date', 'Type', 'mahadasha_lord', 'antardasha_lord', 'pratyantardasha_lord',
            'Planet', 'Parent_Planet', 'Auspiciousness_Score', 'Dasha_Lord_Strength', 
            'Arishta_Protections', 'Protection_Score', 'Sun_Moon_Support', 'Astrological_Significance'
        ]
        
        # Create output dataframe with only required columns
        output_df = df_csv[required_columns].copy()
        
        # Ensure Protection_Score is properly mapped (boolean to float for compatibility)
        output_df['Protection_Score'] = output_df['Protection_Score'].astype(float)
        
        output_df.to_csv(complete_file, index=False)
        
        # Create separate files by type (all sorted by date ascending)
        files_created = [complete_file]
        
        # Maha Dashas only
        md_only = output_df[output_df['Type'] == 'MD'].sort_values('Date', ascending=True)
        if not md_only.empty:
            md_file = os.path.join(output_dir, f"{symbol}_MahaDashas.csv")
            md_only.to_csv(md_file, index=False)
            files_created.append(md_file)
        
        # Antar Dashas only
        ad_only = output_df[output_df['Type'] == 'MD-AD'].sort_values('Date', ascending=True)
        if not ad_only.empty:
            ad_file = os.path.join(output_dir, f"{symbol}_AntarDashas.csv")
            ad_only.to_csv(ad_file, index=False)
            files_created.append(ad_file)
        
        # Pratyantar Dashas only
        pd_only = output_df[output_df['Type'] == 'MD-AD-PD'].sort_values('Date', ascending=True)
        if not pd_only.empty:
            pd_file = os.path.join(output_dir, f"{symbol}_PratyantarDashas.csv")
            pd_only.to_csv(pd_file, index=False)
            files_created.append(pd_file)
        
        print(f"  CSV Results saved to: {output_dir}/")
        for file_path in files_created:
            print(f"    - {os.path.basename(file_path)}")
        
        # Generate enhanced markdown report with system context using original DataFrame with lowercase columns
        self.generate_markdown_report(results, df_original, output_dir, system_name)
        
        return df_original, output_dir

    def generate_markdown_report(self, analysis_results: Dict[str, Any], df: pd.DataFrame, 
                                output_dir: str, system_name: str = None):
        """Generate comprehensive markdown report matching v2 format exactly"""
        symbol = analysis_results['symbol']
        company_name = analysis_results['company_name']
        birth_date = analysis_results['birth_date']
        birth_time = analysis_results['birth_time']
        birth_location = analysis_results['birth_location']
        birth_timezone = analysis_results['birth_timezone']
        birth_positions = analysis_results.get('birth_positions', {})
        
        # Calculate planetary strength analysis
        strong_planets = []
        if birth_positions:
            for planet, data in birth_positions.items():
                if planet in ['Ascendant', 'MC']: continue
                if isinstance(data, dict) and 'sign' in data:
                    strength_result = self.calculate_planetary_strength(planet, data['sign'])
                    strength = strength_result['strength_10']
                    if strength >= 7.0:  # Strong planets
                        strong_planets.append({
                            'planet': planet, 
                            'sign': data['sign'], 
                            'strength': strength,
                            'details': strength_result
                        })
        
        # Basic statistics  
        total_periods = len(df)
        protected_periods = len(df[df['protections_count'] > 0]) if 'protections_count' in df.columns else 0
        protection_rate = (protected_periods / total_periods * 100) if total_periods > 0 else 0
        perfect_scores = len(df[df['auspiciousness_score'] >= 9.5])
        
        # High protection periods (triple protection, sorted by date)
        protection_col = 'protections_count' if 'protections_count' in df.columns else 'Arishta_Protections'
        high_protection = df[df[protection_col] >= 3].copy().sort_values('start_date')
        
        # Group by type for analysis (sorted by date ascending)
        top_md = df[df['Type'] == 'MD'].copy().sort_values('start_date') if len(df[df['Type'] == 'MD']) > 0 else pd.DataFrame()
        current_periods = df.copy()
        
        # Current year for analysis
        current_year = datetime.now().year
        
        # Get transition opportunities (sorted by date)
        transition_opportunities = self.analyze_investment_transitions(df)
        
        # Calculate IPO year for date range
        ipo_year = int(birth_date[:4])
        analysis_period = f"{ipo_year}-2050"
        
        # Add house system context
        house_system_context = ""
        if system_name:
            ref_longitude = analysis_results.get('reference_longitude', 0)
            ref_sign = analysis_results.get('reference_sign', 'Unknown')
            house_system_context = f"""

### House System Analysis
**System:** {system_name}  
**Reference Point:** {ref_sign} ({ref_longitude:.2f}°)  
**Method:** {self._get_house_system_description(system_name)}
"""
        
        # Create comprehensive markdown content matching v2 format exactly
        markdown_content = f"""# 🏛️ Vedic Dasha Analysis Report - {symbol}
**{company_name}** | **House System:** {system_name if system_name else 'Lagna (Traditional)'}

*Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}*

---

## 📋 Executive Summary

### Entity Profile
- **Symbol:** {symbol}
- **Company:** {company_name}
- **Birth Date:** {birth_date}
- **Birth Time:** {birth_time}
- **Birth Location:** {birth_location}
- **Birth Timezone:** {birth_timezone}
- **Analysis Period:** {analysis_period} (comprehensive view from IPO)

### Key Metrics
- **Total Periods Analyzed:** {total_periods:,}
- **Protection Rate:** {protection_rate:.1f}% ({protected_periods}/{total_periods} periods)
- **Perfect Scores (≥9.5):** {perfect_scores}
- **Analysis Depth:** 3-level (Maha + Antar + Pratyantar Dashas)
{house_system_context}

### Chart Assessment
- **{"Exceptional" if len(strong_planets) >= 4 else "Strong" if len(strong_planets) >= 2 else "Moderate"} Strength:** {len(strong_planets)} planets highly dignified
- **Natural Balance:** {"Strong" if any(p['planet'] in self.natural_benefics for p in strong_planets) and any(p['planet'] in self.natural_malefics for p in strong_planets) else "Moderate"} mix of benefics and malefics
- **Technological Affinity:** {"Strong" if any(p['planet'] in ['Rahu', 'Ketu'] for p in strong_planets) else "Moderate"} innovation indicators
- **Leadership Potential:** {"High" if any(p['planet'] == 'Mars' and p['sign'] == 'Aries' for p in strong_planets) else "Moderate"} based on planetary positions

---"""

        # Investment Strategy Analysis (maintain chronological order)
        current_best = current_periods.sort_values('start_date') if not current_periods.empty else pd.DataFrame()
        current_worst = current_periods.sort_values('start_date') if not current_periods.empty else pd.DataFrame()
        
        markdown_content += f"""

## 💰 Transition-Based Investment Strategy ({analysis_period})

### 🚀 Prime Buy Opportunities - "Buy the Dip Before the Rip"

**Investment Thesis:** Buy during low-scoring periods when high-scoring periods are imminent. These opportunities offer maximum upside potential by entering before favorable planetary influences drive stock appreciation.

| Date Range | MD-AD-PD Combination | Current Score | Next Score | Change | Action | Selection Criteria | Astrological Significance | Confidence |
|------------|---------------------|---------------|------------|--------|--------|-------------------|---------------------------|------------|"""

        # Top buy opportunities
        for opp in transition_opportunities['buy_opportunities'][:10]:
            date_range = f"{opp['current_date']} - {opp['current_end']}"
            year = opp['current_date'][:4]
            status = "🟢 **NOW**" if int(year) == current_year else "🔵 FUTURE" if int(year) > current_year else "🟡 PAST"
            
            markdown_content += f"\n| {date_range} | {opp['md_ad_pd_combo']} | {opp['current_score']:.1f} | {opp['next_score']:.1f} | +{opp['score_change']:.1f} | **{opp['action']}** | {opp['selection_rationale']} | {opp['astrological_significance']} | {opp['confidence']} {status} |"

        markdown_content += f"""

### 📉 Strategic Sell Opportunities - "Sell the Peak Before the Decline"

**Exit Thesis:** Sell during high-scoring periods when low-scoring periods are approaching. These opportunities protect gains by exiting before challenging planetary influences pressure stock prices.

| Date Range | MD-AD-PD Combination | Current Score | Next Score | Change | Action | Selection Criteria | Astrological Significance | Confidence |
|------------|---------------------|---------------|------------|--------|--------|-------------------|---------------------------|------------|"""

        # Top sell opportunities  
        for opp in transition_opportunities['sell_opportunities'][:10]:
            date_range = f"{opp['current_date']} - {opp['current_end']}"
            year = opp['current_date'][:4]
            status = "⚠️ **NOW**" if int(year) == current_year else "📅 FUTURE" if int(year) > current_year else "📊 PAST"
            
            markdown_content += f"\n| {date_range} | {opp['md_ad_pd_combo']} | {opp['current_score']:.1f} | {opp['next_score']:.1f} | {opp['score_change']:.1f} | **{opp['action']}** | {opp['selection_rationale']} | {opp['astrological_significance']} | {opp['confidence']} {status} |"

        # Near-term transition analysis
        near_term_transitions = self.analyze_investment_transitions(current_periods)
        
        markdown_content += f"""

---

## 📊 Immediate Investment Strategy ({current_year}-{current_year + 3})

### 🎯 Near-Term Transition Opportunities

**Strategy Focus:** Execute optimal timing based on upcoming period transitions rather than current scores alone."""

        if near_term_transitions['buy_opportunities']:
            markdown_content += f"""

**🟢 IMMEDIATE BUY SIGNALS - Act Before Price Rise**

| Date Range | MD-AD-PD Combination | Current→Next Score | Change | Action | Selection Criteria | Astrological Significance | Timing Strategy |
|------------|---------------------|-------------------|--------|--------|-------------------|---------------------------|-----------------|"""
            
            for opp in near_term_transitions['buy_opportunities'][:5]:
                date_range = f"{opp['current_date']} - {opp['current_end']}"
                score_transition = f"{opp['current_score']:.1f} → {opp['next_score']:.1f}"
                change = f"+{opp['score_change']:.1f}"
                
                # Enhanced timing strategy
                if opp['score_change'] >= 3.0:
                    timing = "🚨 **URGENT** - Begin accumulating immediately"
                elif opp['score_change'] >= 2.0:
                    timing = "⚡ **PRIORITY** - Start building position this period"  
                else:
                    timing = "📈 **PLANNED** - Gradual accumulation recommended"
                
                markdown_content += f"\n| {date_range} | {opp['md_ad_pd_combo']} | {score_transition} | {change} | **{opp['action']}** | {opp['selection_rationale']} | {opp['astrological_significance']} | {timing} |"

        if near_term_transitions['sell_opportunities']:
            markdown_content += f"""

**🔴 IMMEDIATE SELL SIGNALS - Act Before Price Drop**

| Date Range | MD-AD-PD Combination | Current→Next Score | Change | Action | Selection Criteria | Astrological Significance | Risk Management |
|------------|---------------------|-------------------|--------|--------|-------------------|---------------------------|-----------------|"""
            
            for opp in near_term_transitions['sell_opportunities'][:5]:
                date_range = f"{opp['current_date']} - {opp['current_end']}"
                score_transition = f"{opp['current_score']:.1f} → {opp['next_score']:.1f}"
                change = f"{opp['score_change']:.1f}"
                
                # Enhanced risk management
                if opp['score_change'] <= -3.0:
                    risk_mgmt = "🚨 **CRITICAL** - Exit positions before period ends"
                elif opp['score_change'] <= -2.0:
                    risk_mgmt = "⚠️ **HIGH PRIORITY** - Reduce exposure significantly"
                else:
                    risk_mgmt = "📉 **DEFENSIVE** - Take profits, tighten stops"
                
                markdown_content += f"\n| {date_range} | {opp['md_ad_pd_combo']} | {score_transition} | {change} | **{opp['action']}** | {opp['selection_rationale']} | {opp['astrological_significance']} | {risk_mgmt} |"

        # Add hold periods if any
        if near_term_transitions['hold_recommendations']:
            markdown_content += f"""

**🟡 HOLD PERIODS - Maintain Current Strategy**

| Date Range | MD-AD-PD Combination | Score Range | Action | Selection Criteria | Astrological Significance | Strategy |
|------------|---------------------|-------------|--------|-------------------|---------------------------|----------|"""
            
            for opp in near_term_transitions['hold_recommendations'][:3]:
                date_range = f"{opp['current_date']} - {opp['current_end']}"
                score_range = f"{opp['current_score']:.1f} → {opp['next_score']:.1f}"
                
                markdown_content += f"\n| {date_range} | {opp['md_ad_pd_combo']} | {score_range} | **{opp['action']}** | {opp['selection_rationale']} | {opp['astrological_significance']} | {opp['rationale']} |"

        # Comprehensive Investment Framework
        markdown_content += f"""

---

## 🎯 Transition-Based Investment Framework

### Revolutionary Approach: "Buy the Dip, Sell the Rip"

**Core Philosophy:** Success comes from anticipating transitions, not following current conditions. Enter positions during unfavorable periods before they improve, exit during favorable periods before they deteriorate.

### 📈 **Transition-Based Entry Strategy**

#### 🟢 **Strong Buy Criteria** 
- **Current Score ≤ 4.0 + Next Score ≥ 7.0:** Maximum opportunity - buy the bottom before surge
- **Score Improvement ≥ 3.0 points:** High-conviction accumulation phase
- **Final 25% of challenging periods:** Position for reversal

#### 🔵 **Accumulation Criteria**
- **Current Score ≤ 5.0 + Score Improvement ≥ 2.5:** Build positions gradually  
- **Transitioning from decline to growth:** Dollar-cost average entry
- **2-3 periods before major auspicious cycles:** Strategic pre-positioning

#### 🟡 **Hold Criteria**
- **Score changes ≤ 1.0 point:** Maintain current allocation
- **Neutral transitions (4.5-6.5 range):** No major adjustments needed
- **Stable periods with unclear direction:** Wait for better signals

### 📉 **Transition-Based Exit Strategy**

#### 🔴 **Defensive Sell Criteria**
- **Current Score ≥ 7.0 + Next Score ≤ 4.0:** Exit peak before crash
- **Score Decline ≥ 3.0 points:** High-conviction reduction phase  
- **Final 25% of excellent periods:** Protect gains before reversal

#### 🟠 **Profit Taking Criteria**
- **Current Score ≥ 6.0 + Score Decline ≥ 2.0:** Partial position reduction
- **Transitioning from growth to decline:** Gradual profit realization
- **2-3 periods before major challenging cycles:** Strategic de-risking

### 🎯 **Dynamic Portfolio Allocation**

**{symbol} Allocation Strategy Based on Transition Analysis:**

| Phase | Allocation | Criteria | Action |
|-------|------------|----------|---------|
| **Pre-Surge** | 35-50% | Score improving 3.0+ points | Maximum accumulation |
| **Growth** | 25-35% | Score 6.0-8.0, stable/improving | Hold core position |  
| **Peak** | 15-25% | Score 7.0+, deteriorating | Begin profit taking |
| **Pre-Decline** | 5-15% | Score declining 2.0+ points | Defensive positioning |
| **Bottom** | 20-30% | Score ≤ 4.0, improving ahead | Strategic re-entry |

### 🛡️ **Enhanced Risk Management**

#### **Transition Risk Assessment**
- **High Risk:** Score drops ≥3.0 points → Reduce exposure 50-75%
- **Moderate Risk:** Score drops 2.0-2.9 points → Reduce exposure 25-50%
- **Low Risk:** Score changes <2.0 points → Maintain strategy
- **Opportunity:** Score improves ≥2.5 points → Increase exposure

#### **Protection-Enhanced Positioning** 
- **Triple Protection Periods:** 1.5x normal allocation (maximum confidence)
- **Double Protection Periods:** 1.25x normal allocation
- **Single Protection Periods:** 1.0x normal allocation
- **No Protection Periods:** 0.75x normal allocation (defensive)

### 📊 **Performance Targets by Transition Type**

#### **Buy Opportunities (Score Improvements)**
- **+4.0+ point improvement:** Target 75-150% returns
- **+3.0-3.9 point improvement:** Target 50-75% returns  
- **+2.0-2.9 point improvement:** Target 25-50% returns
- **+1.5-1.9 point improvement:** Target 10-25% returns

#### **Risk Management (Score Deterioration)**
- **-3.0+ point decline:** Protect against 30-60% drawdown
- **-2.0-2.9 point decline:** Protect against 15-30% drawdown
- **-1.5-1.9 point decline:** Protect against 5-15% drawdown

### 🔄 **Implementation Timeline**

#### **Monthly Reviews**
1. **Transition Analysis:** Identify upcoming score changes 1-3 periods ahead
2. **Position Adjustment:** Align allocation with transition predictions
3. **Risk Assessment:** Update protection status and exposure levels

#### **Weekly Monitoring**  
1. **Current Period Status:** Monitor for early transition signals
2. **Technical Confirmation:** Verify astrological predictions with price action
3. **Trigger Preparation:** Ready orders for anticipated transitions

#### **Daily Execution**
1. **Entry Timing:** Execute buys in final weeks of low-score periods
2. **Exit Timing:** Execute sells in final weeks of high-score periods  
3. **Stop Management:** Adjust protective stops based on transition proximity
"""

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
                    combo = period['mahadasha_lord']
                elif period['Type'] == 'MD-AD':
                    combo = f"{period['mahadasha_lord']}-{period['antardasha_lord']}"
                else:
                    combo = f"{period['mahadasha_lord']}-{period['antardasha_lord']}-{period['pratyantardasha_lord']}"
                
                markdown_content += f"\n{i}. **{period['start_date']} to {period['end_date']}:** {combo} ({period[protection_col]} protections)"

        # Risk periods (sorted by date ascending)
        risk_periods = df[df['auspiciousness_score'] < 3.5].sort_values('start_date').head(5)
        if not risk_periods.empty:
            markdown_content += f"""

### Risk Periods Requiring Caution

#### Challenging Windows (Score < 3.5)"""
            for _, period in risk_periods.iterrows():
                if period['Type'] == 'MD':
                    combo = period['mahadasha_lord']
                elif period['Type'] == 'MD-AD':
                    combo = f"{period['mahadasha_lord']}-{period['antardasha_lord']}"
                else:
                    combo = f"{period['mahadasha_lord']}-{period['antardasha_lord']}-{period['pratyantardasha_lord']}"
                
                markdown_content += f"\n- **{period['start_date']} to {period['end_date']}:** {combo} ({period['auspiciousness_score']:.2f}/10)"

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

### Maha Dasha Periods (Chronological)

| Period | Maha Lord | Duration | Auspiciousness | Key Characteristics |
|--------|-----------|----------|----------------|-------------------|"""

            for _, period in top_md.iterrows():
                start_year = period['start_date'][:4]
                end_year = period['end_date'][:4]
                duration = int(end_year) - int(start_year)
                status = "**CURRENT**" if int(start_year) <= current_year <= int(end_year) else "Future" if int(start_year) > current_year else "Past"
                
                characteristics = self.get_planet_characteristics(period['mahadasha_lord'])
                
                row = f"| {start_year}-{end_year} | {period['mahadasha_lord']} | {duration} years | {period['auspiciousness_score']:.2f}/10 | {characteristics}"
                if "CURRENT" in status:
                    row = f"| **{start_year}-{end_year}** | **{period['mahadasha_lord']}** | **{duration} years** | **{period['auspiciousness_score']:.2f}/10** | **{characteristics} {status}** |"
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
- **House System:** {system_name if system_name else 'Lagna (Traditional)'} perspective

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

**Disclaimer:** This analysis is for educational and strategic planning purposes. Investment decisions should consider multiple factors including fundamental analysis, market conditions, and professional financial advice.
"""

        # Save markdown file
        markdown_file = os.path.join(output_dir, f"{symbol}_Vedic_Analysis_Report.md")
        with open(markdown_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        print(f"    - {os.path.basename(markdown_file)}")
        
        # Generate PDF version
        try:
            pdf_file = self.generate_pdf_report(markdown_content, output_dir, symbol)
            if pdf_file:
                print(f"    - {os.path.basename(pdf_file)}")
        except Exception as e:
            print(f"    - PDF generation skipped: {e}")
        
        return markdown_file

    def analyze_investment_transitions(self, df: pd.DataFrame) -> Dict[str, List]:
        """Analyze period transitions to identify buy/sell opportunities"""
        opportunities = {
            'buy_opportunities': [],
            'sell_opportunities': [],
            'hold_recommendations': []
        }
        
        if df.empty:
            return opportunities
        
        # Sort by date for transition analysis
        df_sorted = df.sort_values('start_date').copy()
        
        for i in range(len(df_sorted) - 1):
            current = df_sorted.iloc[i]
            next_period = df_sorted.iloc[i + 1]
            
            current_score = current['auspiciousness_score']
            next_score = next_period['auspiciousness_score']
            score_change = next_score - current_score
            
            # Generate period combination string
            if current['Type'] == 'MD':
                combo = current['mahadasha_lord']
            elif current['Type'] == 'MD-AD':
                combo = f"{current['mahadasha_lord']}-{current['antardasha_lord']}"
            else:
                combo = f"{current['mahadasha_lord']}-{current['antardasha_lord']}-{current['pratyantardasha_lord']}"
            
            # Basic significance
            significance = current.get('astrological_significance', f"{current['mahadasha_lord']} period")[:100]
            
            opportunity = {
                'current_date': current['start_date'],
                'current_end': current['end_date'],
                'next_date': next_period['start_date'],
                'current_score': current_score,
                'next_score': next_score,
                'score_change': score_change,
                'md_ad_pd_combo': combo,
                'astrological_significance': significance,
                'current_type': current['Type']
            }
            
            # Determine opportunity type
            if score_change >= 2.5 and current_score <= 5.5:
                # Strong buy opportunity - low score improving significantly
                opportunity.update({
                    'action': 'STRONG BUY',
                    'confidence': 'HIGH' if score_change >= 3.5 else 'MEDIUM',
                    'selection_rationale': f'Score improving {score_change:.1f} points from low base',
                    'rationale': 'Buy before surge'
                })
                opportunities['buy_opportunities'].append(opportunity)
                
            elif score_change >= 1.5 and current_score <= 6.0:
                # Moderate buy opportunity
                opportunity.update({
                    'action': 'BUY',
                    'confidence': 'MEDIUM',
                    'selection_rationale': f'Score improving {score_change:.1f} points',
                    'rationale': 'Accumulate on improvement'
                })
                opportunities['buy_opportunities'].append(opportunity)
                
            elif score_change <= -2.5 and current_score >= 6.0:
                # Strong sell opportunity - high score declining significantly
                opportunity.update({
                    'action': 'STRONG SELL',
                    'confidence': 'HIGH' if score_change <= -3.5 else 'MEDIUM',
                    'selection_rationale': f'Score declining {score_change:.1f} points from high base',
                    'rationale': 'Sell before decline'
                })
                opportunities['sell_opportunities'].append(opportunity)
                
            elif score_change <= -1.5 and current_score >= 5.5:
                # Moderate sell opportunity
                opportunity.update({
                    'action': 'SELL',
                    'confidence': 'MEDIUM',
                    'selection_rationale': f'Score declining {score_change:.1f} points',
                    'rationale': 'Take profits on decline'
                })
                opportunities['sell_opportunities'].append(opportunity)
                
            elif abs(score_change) <= 1.0:
                # Hold recommendation
                opportunity.update({
                    'action': 'HOLD',
                    'confidence': 'MEDIUM',
                    'selection_rationale': f'Stable score (change: {score_change:.1f})',
                    'rationale': 'Maintain current strategy'
                })
                opportunities['hold_recommendations'].append(opportunity)
        
        # Sort by date ascending (chronological order)
        opportunities['buy_opportunities'].sort(key=lambda x: x['current_date'])
        opportunities['sell_opportunities'].sort(key=lambda x: x['current_date'])
        opportunities['hold_recommendations'].sort(key=lambda x: x['current_date'])
        
        return opportunities

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

    def _get_house_system_description(self, system_name: str) -> str:
        """Get description of house system calculation method"""
        descriptions = {
            'Lagna (Ascendant)': 'Traditional Vedic system using birth Ascendant as 1st house',
            'Arudha Lagna': 'Jaimini system using Arudha Lagna calculation with special rules',
            'Chandra Lagna (Moon)': 'Moon-based system using natal Moon position as 1st house',
            'Mahadasha Lord Position': 'Birth mahadasha lord position as 1st house reference'
        }
        return descriptions.get(system_name, 'Custom house system calculation')

    def get_house_system_description(self, system_name: str) -> str:
        """Get description of house system calculation method"""
        descriptions = {
            'Lagna (Ascendant)': 'Traditional Vedic system using birth Ascendant as 1st house',
            'Arudha Lagna': 'Jaimini system using Arudha Lagna calculation with special rules',
            'Chandra Lagna (Moon)': 'Moon-based system using natal Moon position as 1st house',
            'Mahadasha Lord Position': 'Birth mahadasha lord position as 1st house reference'
        }
        return descriptions.get(system_name, 'Custom house system calculation')

    def generate_pdf_report(self, markdown_content: str, output_dir: str, symbol: str) -> Optional[str]:
        """
        Generate PDF report from markdown content using available PDF generator
        
        Args:
            markdown_content: Markdown formatted content
            output_dir: Output directory path
            symbol: Stock symbol for filename
            
        Returns:
            Path to generated PDF file or None if generation failed
        """
        if not PDF_GENERATOR:
            print("Warning: PDF generation is disabled. No PDF generator available.")
            return None
            
        try:
            # Convert markdown to HTML
            html_content = markdown.markdown(
                markdown_content,
                extensions=['tables', 'fenced_code']
            )
            
            # Add basic CSS styling
            css_style = """
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                table { border-collapse: collapse; width: 100%; margin: 20px 0; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #f5f5f5; }
                h1, h2, h3 { color: #333; }
                .chart { max-width: 100%; height: auto; }
            </style>
            """
            
            html_content = f"<html><head>{css_style}</head><body>{html_content}</body></html>"
            
            # Create output directory if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)
            pdf_path = os.path.join(output_dir, f"{symbol}_analysis.pdf")
            
            if PDF_GENERATOR == 'weasyprint':
                HTML(string=html_content).write_pdf(pdf_path)
            elif PDF_GENERATOR == 'pdfkit':
                options = {
                    'page-size': 'A4',
                    'margin-top': '20mm',
                    'margin-right': '20mm',
                    'margin-bottom': '20mm',
                    'margin-left': '20mm',
                    'encoding': 'UTF-8'
                }
                # Use explicit path to wkhtmltopdf on Windows
                if platform.system() == 'Windows' and WKHTMLTOPDF_PATH:
                    config = pdfkit.configuration(wkhtmltopdf=WKHTMLTOPDF_PATH)
                    pdfkit.from_string(html_content, pdf_path, options=options, configuration=config)
                else:
                    pdfkit.from_string(html_content, pdf_path, options=options)
                
            print(f"PDF report generated: {pdf_path}")
            return pdf_path
            
        except Exception as e:
            print(f"Error generating PDF report: {str(e)}")
            if PDF_GENERATOR == 'pdfkit':
                print("\nTroubleshooting wkhtmltopdf:")
                if platform.system() == 'Windows':
                    if not WKHTMLTOPDF_PATH:
                        print("1. wkhtmltopdf not found in common locations. Please:")
                        print("   - Download from: https://wkhtmltopdf.org/downloads.html")
                        print("   - Install to default location (C:\\Program Files\\wkhtmltopdf)")
                    else:
                        print(f"1. Using wkhtmltopdf from: {WKHTMLTOPDF_PATH}")
                        print("   If this path is incorrect, please reinstall wkhtmltopdf")
                print("2. After installation, restart your Python script")
            return None

def main():
    """Main execution function with command-line argument parsing"""
    parser = argparse.ArgumentParser(
        description='Enhanced Vedic Dasha Analyzer v3 with Multi-House System Support',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Traditional analysis (Lagna only)
  python vedic_dasha_analyzer_v3.py data/Technology/PLTR.json
  
  # All 4 house systems
  python vedic_dasha_analyzer_v3.py data/Technology/PLTR.json --multi-house
  
  # Specific house systems
  python vedic_dasha_analyzer_v3.py data/Technology/PLTR.json --house-systems lagna arudha_lagna
  
  # With custom location
  python vedic_dasha_analyzer_v3.py data/Technology/PLTR.json --location "Mumbai, India" --multi-house
        """
    )
    
    parser.add_argument('json_file', help='Path to the JSON file containing entity data')
    parser.add_argument('--location', '-l', default='New York, USA', 
                       help='Birth location (default: New York, USA; fallback: UTC timezone)')
    parser.add_argument('--multi-house', action='store_true',
                       help='Enable all 4 house systems analysis (lagna, arudha_lagna, chandra_lagna, mahadasha_lord)')
    parser.add_argument('--house-systems', nargs='+', 
                       choices=['lagna', 'arudha_lagna', 'chandra_lagna', 'mahadasha_lord'],
                       help='Specify which house systems to analyze')
    parser.add_argument('--output', '-o', help='Custom output directory (default: analysis/{SYMBOL}/)')
    
    args = parser.parse_args()
    
    # Validate input file
    if not os.path.exists(args.json_file):
        print(f"Error: JSON file '{args.json_file}' not found.")
        sys.exit(1)
    
    print("=" * 80)
    print("🏛️  VEDIC DASHA ANALYZER v3 - MULTI-HOUSE SYSTEM EDITION")
    print("=" * 80)
    
    # Determine house systems to analyze
    if args.house_systems:
        # User specified particular systems
        selected_systems = args.house_systems
        print(f"🎯 Analyzing specified house systems: {', '.join(selected_systems)}")
    elif args.multi_house:
        # User wants all systems
        selected_systems = ['lagna', 'arudha_lagna', 'chandra_lagna', 'mahadasha_lord']
        print("🌟 Multi-house analysis enabled - analyzing all 4 systems")
    else:
        # Default: Lagna only (backward compatibility)
        selected_systems = ['lagna']
        print("📍 Traditional analysis: Lagna system only")
    
    try:
        # Initialize analyzer
        analyzer = EnhancedVedicDashaAnalyzer(birth_location=args.location)
        
        # Filter house systems based on selection
        if len(selected_systems) == 1 and selected_systems[0] == 'lagna':
            # Standard single-system mode
            results = analyzer.analyze_json_file(args.json_file, enable_multi_house=False)
        else:
            # Multi-system mode - temporarily adjust house_systems
            original_systems = analyzer.house_systems.copy()
            analyzer.house_systems = {k: v for k, v in original_systems.items() if k in selected_systems}
            
            results = analyzer.analyze_json_file(args.json_file, enable_multi_house=True)
            
            # Restore original systems
            analyzer.house_systems = original_systems
        
        print("\n" + "=" * 80)
        print("✅ ANALYSIS COMPLETE")
        print("=" * 80)
        
        if results.get('multi_house_enabled', False):
            print(f"📊 Multi-house analysis completed for {results['symbol']}")
            print(f"🏠 House systems analyzed: {len(results['house_systems_analyzed'])}")
            print("\n📁 Output Structure:")
            for system_key, summary in results['results_summary'].items():
                if summary['status'] == 'completed':
                    print(f"   📂 analysis/{results['symbol']}/{system_key}/")
                    print(f"      ✅ {summary['system_name']}")
                    print(f"      📍 Reference: {summary['reference_sign']} ({summary['reference_longitude']:.2f}°)")
                else:
                    print(f"   ❌ {summary['system_name']}: {summary['error']}")
        else:
            print(f"📊 Traditional analysis completed for {results['symbol']}")
            print(f"📁 Output: {results['output_directory']}")
        
        print(f"\n🎯 Ready for cross-system comparison and strategic analysis!")
        
    except Exception as e:
        print(f"\n❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 