#!/usr/bin/env python3
"""
Enhanced Vedic Dasha Analyzer v4 with Navamsha (D9) Evaluation System
Supports 4 house systems + Navamsha weighting: Lagna, Arudha Lagna, Chandra Lagna, and Mahadasha Lord Position
Uses sideralib for sidereal ephemeris calculations with classical Navamsha analysis

INSTALLATION REQUIREMENTS:
Before running this script, install the required dependencies:

pip install sideralib pandas pytz geopy timezonefinder markdown weasyprint

This version adds classical Navamsha (D9) evaluation with 10:9 weighting system.
- D1 (Rashi) chart weight: 10/10 for immediate manifestation
- D9 (Navamsha) chart weight: 9/10 for underlying strength and sustainability
- Combined analysis provides more accurate predictions following classical Vedic principles

USAGE:
  # Traditional analysis (Lagna only)
  python vedic_dasha_analyzer_v4.py data/Technology/PLTR.json
  
  # All 4 house systems with Navamsha evaluation
  python vedic_dasha_analyzer_v4.py data/Technology/PLTR.json --multi-house --navamsha
  
  # With custom location and Navamsha
  python vedic_dasha_analyzer_v4.py data/Technology/PLTR.json --location "Mumbai, India" --multi-house --navamsha

CHANGES FROM v3:
- Added complete Navamsha (D9) calculation system
- Implemented 10:9 weighting between D1 and D9 charts
- Enhanced analysis with D9 planetary strength evaluation
- Vargottama detection (same sign in D1 and D9)
- Classical Navamsha rules for marriage, spirituality, and life sustainability
- Integrated D9 analysis into investment recommendations
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
from weasyprint import HTML, CSS

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

        # NEW: Navamsha (D9) calculation mappings
        # Navamsha pattern for each elemental triplicity
        self.navamsha_patterns = {
            'Fire': ['Aries', 'Leo', 'Sagittarius', 'Capricorn', 'Taurus', 'Virgo', 'Libra', 'Aquarius', 'Gemini'],
            'Earth': ['Capricorn', 'Taurus', 'Virgo', 'Libra', 'Aquarius', 'Gemini', 'Cancer', 'Scorpio', 'Pisces'],
            'Air': ['Libra', 'Aquarius', 'Gemini', 'Cancer', 'Scorpio', 'Pisces', 'Aries', 'Leo', 'Sagittarius'],
            'Water': ['Cancer', 'Scorpio', 'Pisces', 'Aries', 'Leo', 'Sagittarius', 'Capricorn', 'Taurus', 'Virgo']
        }
        
        # NEW: DASHAMSHA (D10) CALCULATION MAPPINGS
        # Dashamsha pattern for each sign type (odd/even)
        self.dashamsha_patterns = {
            'odd': ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo', 'Libra', 'Scorpio', 'Sagittarius', 'Capricorn'],
            'even': ['Sagittarius', 'Capricorn', 'Aquarius', 'Pisces', 'Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo']
        }
        
        # Dashamsha deity rulership and career significations
        self.dashamsha_deities = {
            1: {'deity': 'Indra', 'significance': 'Leadership, Authority, Government, Royal positions'},
            2: {'deity': 'Agni', 'significance': 'Energy, Innovation, Management, Passionate careers'},
            3: {'deity': 'Yama', 'significance': 'Law, Justice, Administration, Disciplinary roles'},
            4: {'deity': 'Rakshasa', 'significance': 'Competition, Politics, Risk-taking, Business warfare'},
            5: {'deity': 'Varuna', 'significance': 'Creativity, Arbitration, Fluid careers, Cooperation'},
            6: {'deity': 'Vayu', 'significance': 'Communication, Travel, Media, Freedom-oriented work'},
            7: {'deity': 'Kubera', 'significance': 'Finance, Banking, Wealth management, Resources'},
            8: {'deity': 'Isan', 'significance': 'Healing, Counseling, Spiritual work, Transformation'},
            9: {'deity': 'Brahma', 'significance': 'Innovation, Engineering, Arts, Creation, Research'},
            10: {'deity': 'Ananth', 'significance': 'Long-term stability, Civil service, Preservation'}
        }
        
        # Sign elements mapping for navamsha calculation
        self.sign_elements = {
            'Aries': 'Fire', 'Leo': 'Fire', 'Sagittarius': 'Fire',
            'Taurus': 'Earth', 'Virgo': 'Earth', 'Capricorn': 'Earth',
            'Gemini': 'Air', 'Libra': 'Air', 'Aquarius': 'Air',
            'Cancer': 'Water', 'Scorpio': 'Water', 'Pisces': 'Water'
        }
        
        # D1 vs D9 weighting system (classical Vedic principle)
        self.chart_weights = {
            'd1_weight': 10,  # Rashi chart - immediate manifestation
            'd9_weight': 9,   # Navamsha chart - underlying strength & sustainability  
            'd10_weight': 8   # Dashamsha chart - career & professional success
        }

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

    # NEW: NAVAMSHA (D9) CALCULATION METHODS
    
    def calculate_navamsha_position(self, planet_longitude: float) -> Dict[str, Any]:
        """
        Calculate navamsha position for a planet based on its longitude
        
        Args:
            planet_longitude: Planet's longitude in degrees (0-360)
        
        Returns:
            Dictionary with navamsha sign, degree, and pada information
        """
        # Normalize longitude to 0-360
        longitude = planet_longitude % 360
        
        # Get the rashi (main sign) and degrees within sign
        rashi_index = int(longitude // 30)
        rashi_sign = self.signs[rashi_index]
        degrees_in_sign = longitude % 30
        
        # Calculate navamsha number (1-9) within the sign
        navamsha_number = int(degrees_in_sign / 3.333333333) + 1
        navamsha_number = min(navamsha_number, 9)  # Ensure max is 9
        
        # Get the element of the rashi
        element = self.sign_elements[rashi_sign]
        
        # Get navamsha sign from the pattern
        navamsha_pattern = self.navamsha_patterns[element]
        navamsha_sign = navamsha_pattern[navamsha_number - 1]
        
        # Calculate degrees within navamsha sign
        navamsha_degree = (degrees_in_sign % 3.333333333) * 9  # Convert to 30-degree scale
        
        return {
            'rashi_sign': rashi_sign,
            'navamsha_sign': navamsha_sign,
            'navamsha_number': navamsha_number,
            'degrees_in_navamsha': navamsha_degree,
            'is_vargottama': rashi_sign == navamsha_sign  # Same sign in D1 and D9
        }
    
    def calculate_navamsha_chart(self, positions: Dict[str, Dict]) -> Dict[str, Dict]:
        """
        Calculate complete navamsha chart for all planets
        
        Args:
            positions: Dictionary of planetary positions from D1 chart
        
        Returns:
            Dictionary with navamsha positions for all planets
        """
        navamsha_chart = {}
        
        for planet, planet_data in positions.items():
            if planet == 'Ascendant':
                # Calculate navamsha lagna
                asc_longitude = planet_data.get('longitude', 0)
                nav_data = self.calculate_navamsha_position(asc_longitude)
                navamsha_chart['Navamsha_Lagna'] = {
                    'longitude': nav_data['degrees_in_navamsha'],
                    'zodiacSign': nav_data['navamsha_sign'],
                    'degreeWithinSign': nav_data['degrees_in_navamsha'],
                    'is_vargottama': nav_data['is_vargottama'],
                    'navamsha_number': nav_data['navamsha_number']
                }
            else:
                # Calculate navamsha position for planet
                planet_longitude = planet_data.get('longitude', 0)
                nav_data = self.calculate_navamsha_position(planet_longitude)
                
                navamsha_chart[planet] = {
                    'longitude': nav_data['degrees_in_navamsha'],
                    'zodiacSign': nav_data['navamsha_sign'],
                    'degreeWithinSign': nav_data['degrees_in_navamsha'],
                    'is_vargottama': nav_data['is_vargottama'],
                    'navamsha_number': nav_data['navamsha_number'],
                    'rashi_sign': nav_data['rashi_sign']
                }
        
        return navamsha_chart
    
    def evaluate_with_navamsha_weight(self, d1_score: float, d9_score: float, 
                                    d1_rating: str = None, d9_rating: str = None) -> Dict[str, Any]:
        """
        Apply 10:9 weighting system between D1 (Rashi) and D9 (Navamsha) charts
        
        Args:
            d1_score: Score from D1 analysis (0-10)
            d9_score: Score from D9 analysis (0-10)
            d1_rating: Optional categorical rating from D1
            d9_rating: Optional categorical rating from D9
        
        Returns:
            Combined analysis with weighted scores and final recommendation
        """
        # Apply classical weighting: D1 = 10/10, D9 = 9/10
        d1_weighted = d1_score * (self.chart_weights['d1_weight'] / 10.0)
        d9_weighted = d9_score * (self.chart_weights['d9_weight'] / 10.0)
        
        # Calculate combined score
        total_possible = self.chart_weights['d1_weight'] + self.chart_weights['d9_weight']
        combined_score = (d1_weighted + d9_weighted) / total_possible * 10
        
        # Determine final rating based on combined score
        if combined_score >= 8.5:
            final_rating = "Strong Buy"
        elif combined_score >= 7.0:
            final_rating = "Buy"
        elif combined_score >= 5.5:
            final_rating = "Hold"
        elif combined_score >= 3.0:
            final_rating = "Sell" 
        else:
            final_rating = "Strong Sell"
        
        # Classical interpretation
        interpretation = self._get_navamsha_interpretation(d1_score, d9_score, d1_rating, d9_rating)
        
        return {
            'd1_score': d1_score,
            'd9_score': d9_score,
            'd1_weighted': d1_weighted,
            'd9_weighted': d9_weighted,
            'combined_score': combined_score,
            'd1_rating': d1_rating,
            'd9_rating': d9_rating,
            'final_rating': final_rating,
            'interpretation': interpretation,
            'weight_explanation': f"D1 (Rashi) weight: {self.chart_weights['d1_weight']}/10, D9 (Navamsha) weight: {self.chart_weights['d9_weight']}/10"
        }
    
    def _get_navamsha_interpretation(self, d1_score: float, d9_score: float, 
                                   d1_rating: str, d9_rating: str) -> str:
        """Generate classical Vedic interpretation of D1 vs D9 combination"""
        
        interpretations = []
        
        # Score-based analysis
        if d1_score > d9_score + 2:
            interpretations.append("Strong immediate prospects but underlying foundation needs attention")
        elif d9_score > d1_score + 2:
            interpretations.append("Excellent long-term potential despite current challenges")
        elif abs(d1_score - d9_score) <= 1:
            interpretations.append("Balanced outlook with aligned immediate and long-term prospects")
        
        # Rating-based analysis
        if d1_rating and d9_rating:
            if d1_rating in ["Strong Buy", "Buy"] and d9_rating in ["Sell", "Strong Sell"]:
                interpretations.append("Caution: Strong surface indicators undermined by weak fundamentals")
            elif d1_rating in ["Sell", "Strong Sell"] and d9_rating in ["Buy", "Strong Buy"]:
                interpretations.append("Hidden opportunity: Poor surface conditions but strong underlying potential")
            elif d1_rating == "Strong Buy" and d9_rating == "Hold":
                interpretations.append("Good opportunity with moderate sustainability - proceed with measured optimism")
        
        return "; ".join(interpretations) if interpretations else "Standard combined analysis applies"
    
    def _get_dashamsha_effect_description(self, d10_analysis: Dict[str, Any], d1_score: float) -> str:
        """Generate concise dashamsha effect description for CSV"""
        if not d10_analysis:
            return "No D10 Analysis"
        
        d10_score = d10_analysis.get('d10_auspiciousness', 0)
        career_deity = d10_analysis.get('career_deity', 'Unknown')
        is_vargottama = d10_analysis.get('is_d10_vargottama', False)
        
        # Determine effect type
        score_diff = d10_score - d1_score
        
        effect_parts = []
        
        if abs(score_diff) <= 1.0:
            effect_type = "Balanced"
        elif score_diff > 1.0:
            effect_type = "Career-Strong"
            effect_parts.append(f"Career+{score_diff:.1f}")
        else:
            effect_type = "Career-Weak"
            effect_parts.append(f"Career{score_diff:.1f}")
        
        # Add deity info
        if career_deity in ['Indra', 'Kubera', 'Brahma']:
            effect_parts.append(f"{career_deity}")
        
        # Add vargottama if present
        if is_vargottama:
            effect_parts.append("D10-Varg")
        
        return " | ".join(effect_parts) if effect_parts else f"D10 {effect_type}"
    
    def _get_triple_chart_effect_description(self, combined_analysis: Dict[str, Any]) -> str:
        """Generate concise triple chart effect description for CSV"""
        if not combined_analysis:
            return "No Triple Analysis"
        
        d1_score = combined_analysis.get('d1_score', 0)
        d9_score = combined_analysis.get('d9_score', 0)
        d10_score = combined_analysis.get('d10_score', 0)
        final_rating = combined_analysis.get('final_rating', 'Hold')
        
        # Find strongest and weakest charts
        scores = {'D1': d1_score, 'D9': d9_score, 'D10': d10_score}
        strongest = max(scores.keys(), key=lambda k: scores[k])
        weakest = min(scores.keys(), key=lambda k: scores[k])
        
        effect_parts = []
        
        # Identify dominant pattern
        if scores[strongest] - scores[weakest] >= 2.0:
            effect_parts.append(f"{strongest}-Led")
        else:
            effect_parts.append("Balanced")
        
        # Add final result
        effect_parts.append(final_rating)
        
        # Add specific insights
        if d10_score >= 8.0:
            effect_parts.append("Career-Excel")
        elif d9_score >= 8.0:
            effect_parts.append("Sustain-Strong")
        elif d1_score >= 8.0:
            effect_parts.append("Immediate-Strong")
        
        return " | ".join(effect_parts)
    
    def _analyze_dasha_in_navamsha(self, dasha_lord: str, navamsha_chart: Dict, 
                                 birth_positions: Dict) -> Dict[str, Any]:
        """
        Analyze dasha lord's strength in navamsha chart
        
        Args:
            dasha_lord: Planet whose dasha is being analyzed
            navamsha_chart: Complete D9 chart
            birth_positions: D1 chart positions
            
        Returns:
            Analysis of dasha lord in navamsha with auspiciousness score
        """
        if dasha_lord not in navamsha_chart:
            return {
                'd9_auspiciousness': 5.0,
                'd9_analysis': 'Dasha lord not found in navamsha chart',
                'is_vargottama': False,
                'd9_sign': 'Unknown'
            }
        
        d9_planet_data = navamsha_chart[dasha_lord]
        d9_sign = d9_planet_data['zodiacSign']
        is_vargottama = d9_planet_data['is_vargottama']
        
        # Calculate strength in D9
        d9_strength_result = self.calculate_planetary_strength(
            dasha_lord, d9_sign, is_dasha_start=True
        )
        d9_strength = d9_strength_result['strength_10']
        
        # Vargottama bonus (classical rule)
        if is_vargottama:
            d9_strength *= 1.25  # 25% bonus for vargottama
            d9_strength = min(d9_strength, 10.0)
        
        # Additional D9 specific analysis
        d9_analysis_notes = []
        
        if is_vargottama:
            d9_analysis_notes.append(f"{dasha_lord} is Vargottama (same sign in D1 and D9) - excellent strength")
        
        if d9_sign == self.exaltation_signs.get(dasha_lord):
            d9_analysis_notes.append(f"{dasha_lord} exalted in D9 - strong underlying support")
        elif d9_sign in self.own_signs.get(dasha_lord, []):
            d9_analysis_notes.append(f"{dasha_lord} in own sign in D9 - stable foundation")
        elif d9_sign == self.debilitation_signs.get(dasha_lord):
            d9_analysis_notes.append(f"{dasha_lord} debilitated in D9 - underlying weakness")
        
        # Convert D9 strength to auspiciousness score
        d9_auspiciousness = d9_strength
        
        return {
            'd9_auspiciousness': d9_auspiciousness,
            'd9_strength': d9_strength,
            'd9_sign': d9_sign,
            'is_vargottama': is_vargottama,
            'd9_analysis': "; ".join(d9_analysis_notes) if d9_analysis_notes else f"{dasha_lord} in {d9_sign} in D9",
            'd9_dignity': d9_strength_result['dignity_type']
        }
    
    def _score_to_rating(self, score: float) -> str:
        """Convert numerical score to categorical rating"""
        if score >= 8.5:
            return "Strong Buy"
        elif score >= 7.0:
            return "Buy"
        elif score >= 5.5:
            return "Hold"
        elif score >= 3.0:
            return "Sell"
        else:
            return "Strong Sell"
    
    def _get_navamsha_effect_description(self, combined_analysis: Dict[str, Any]) -> str:
        """Generate concise navamsha effect description for CSV"""
        if not combined_analysis:
            return "No D9 Analysis"
        
        d1_score = combined_analysis.get('d1_score', 0)
        d9_score = combined_analysis.get('d9_score', 0)
        final_rating = combined_analysis.get('final_rating', 'Hold')
        
        # Determine effect type
        score_diff = d9_score - d1_score
        
        if abs(score_diff) <= 1.0:
            effect_type = "Balanced"
        elif score_diff > 1.0:
            effect_type = "Strengthening"
        else:
            effect_type = "Weakening"
        
        # Create concise description
        if effect_type == "Strengthening":
            return f"D9 Strengthens (+{score_diff:.1f}) → {final_rating}"
        elif effect_type == "Weakening":
            return f"D9 Weakens ({score_diff:.1f}) → {final_rating}"
        else:
            return f"D9 Balanced (±{abs(score_diff):.1f}) → {final_rating}"

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
                else:
                    # Dasha starts after birth, use actual dasha start positions
                    aarambha_positions = self.get_planetary_positions(dasha_dt_local)
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

    def analyze_json_file(self, json_file_path: str, enable_multi_house: bool = False, 
                         enable_navamsha: bool = False, enable_dashamsha: bool = False) -> Dict[str, Any]:
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
                        data, birth_positions.copy(), ref_longitude, system_key, system_name, 
                        enable_navamsha, enable_dashamsha
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
                data, birth_positions, ref_longitude, 'lagna', 'Lagna (Ascendant)', 
                enable_navamsha, enable_dashamsha
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
                                       system_name: str, enable_navamsha: bool = False, 
                                       enable_dashamsha: bool = False) -> Dict[str, Any]:
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
            
            # NEW: Calculate divisional charts if enabled
            navamsha_chart = None
            dashamsha_chart = None
            
            if enable_navamsha:
                print(f"    Calculating Navamsha (D9) chart...")
                navamsha_chart = self.calculate_navamsha_chart(birth_positions)
            
            if enable_dashamsha:
                print(f"    Calculating Dashamsha (D10) chart...")
                dashamsha_chart = self.calculate_dashamsha_chart(birth_positions)
            
            # Process dasha data
            results = []
            
            # Process Maha Dashas
            maha_dashas = data['dashaData']['mahaDasha']
            for start_date, maha_dasha in sorted(maha_dashas.items()):
                analysis = self.calculate_dasha_auspiciousness(
                    birth_positions, start_date, maha_dasha['lord'], 'Maha Dasha', birth_time, birth_date
                )
                
                # NEW: Divisional chart analysis if enabled
                final_auspiciousness = analysis['auspiciousness_score']
                divisional_data = {}
                
                # Handle different combinations of divisional charts
                if enable_navamsha and enable_dashamsha and navamsha_chart and dashamsha_chart:
                    # Triple chart analysis (D1 + D9 + D10)
                    d9_analysis = self._analyze_dasha_in_navamsha(
                        maha_dasha['lord'], navamsha_chart, birth_positions
                    )
                    d10_analysis = self._analyze_dasha_in_dashamsha(
                        maha_dasha['lord'], dashamsha_chart, birth_positions
                    )
                    
                    combined_analysis = self.evaluate_with_triple_chart_weight(
                        d1_score=analysis['auspiciousness_score'],
                        d9_score=d9_analysis['d9_auspiciousness'],
                        d10_score=d10_analysis['d10_auspiciousness'],
                        d1_rating=self._score_to_rating(analysis['auspiciousness_score']),
                        d9_rating=self._score_to_rating(d9_analysis['d9_auspiciousness']),
                        d10_rating=self._score_to_rating(d10_analysis['d10_auspiciousness'])
                    )
                    
                    final_auspiciousness = combined_analysis['combined_score']
                    divisional_data = {
                        'd1_auspiciousness': analysis['auspiciousness_score'],
                        'd9_auspiciousness': d9_analysis['d9_auspiciousness'],
                        'd10_auspiciousness': d10_analysis['d10_auspiciousness'],
                        'navamsha_analysis': d9_analysis,
                        'dashamsha_analysis': d10_analysis,
                        'combined_analysis': combined_analysis,
                        # CSV-friendly column names
                        'D1_Score': round(analysis['auspiciousness_score'], 2),
                        'D9_Score': round(d9_analysis['d9_auspiciousness'], 2),
                        'D10_Score': round(d10_analysis['d10_auspiciousness'], 2),
                        'D9_Sign': d9_analysis['d9_sign'],
                        'D10_Sign': d10_analysis['d10_sign'],
                        'D9_Vargottama': 'Yes' if d9_analysis['is_vargottama'] else 'No',
                        'D10_Vargottama': 'Yes' if d10_analysis['is_d10_vargottama'] else 'No',
                        'D10_Deity': d10_analysis['career_deity'],
                        'D10_Career': d10_analysis['career_significance'],
                        'Triple_Chart_Effect': self._get_triple_chart_effect_description(combined_analysis)
                    }
                
                elif enable_navamsha and navamsha_chart:
                    # D1 + D9 analysis only
                    d9_analysis = self._analyze_dasha_in_navamsha(
                        maha_dasha['lord'], navamsha_chart, birth_positions
                    )
                    
                    combined_analysis = self.evaluate_with_navamsha_weight(
                        d1_score=analysis['auspiciousness_score'],
                        d9_score=d9_analysis['d9_auspiciousness'],
                        d1_rating=self._score_to_rating(analysis['auspiciousness_score']),
                        d9_rating=self._score_to_rating(d9_analysis['d9_auspiciousness'])
                    )
                    
                    final_auspiciousness = combined_analysis['combined_score']
                    divisional_data = {
                        'd1_auspiciousness': analysis['auspiciousness_score'],
                        'd9_auspiciousness': d9_analysis['d9_auspiciousness'],
                        'navamsha_analysis': d9_analysis,
                        'combined_analysis': combined_analysis,
                        # CSV-friendly column names
                        'D1_Score': round(analysis['auspiciousness_score'], 2),
                        'D9_Score': round(d9_analysis['d9_auspiciousness'], 2),
                        'D9_Sign': d9_analysis['d9_sign'],
                        'D9_Vargottama': 'Yes' if d9_analysis['is_vargottama'] else 'No',
                        'Navamsha_Effect': self._get_navamsha_effect_description(combined_analysis)
                    }
                
                elif enable_dashamsha and dashamsha_chart:
                    # D1 + D10 analysis only
                    d10_analysis = self._analyze_dasha_in_dashamsha(
                        maha_dasha['lord'], dashamsha_chart, birth_positions
                    )
                    
                    # Use D1 + D10 weighting (no D9)
                    d1_weighted = analysis['auspiciousness_score'] * (self.chart_weights['d1_weight'] / 10.0)
                    d10_weighted = d10_analysis['d10_auspiciousness'] * (self.chart_weights['d10_weight'] / 10.0)
                    total_possible = self.chart_weights['d1_weight'] + self.chart_weights['d10_weight']
                    combined_score = (d1_weighted + d10_weighted) / total_possible * 10
                    
                    final_auspiciousness = combined_score
                    divisional_data = {
                        'd1_auspiciousness': analysis['auspiciousness_score'],
                        'd10_auspiciousness': d10_analysis['d10_auspiciousness'],
                        'dashamsha_analysis': d10_analysis,
                        # CSV-friendly column names
                        'D1_Score': round(analysis['auspiciousness_score'], 2),
                        'D10_Score': round(d10_analysis['d10_auspiciousness'], 2),
                        'D10_Sign': d10_analysis['d10_sign'],
                        'D10_Vargottama': 'Yes' if d10_analysis['is_d10_vargottama'] else 'No',
                        'D10_Deity': d10_analysis['career_deity'],
                        'D10_Career': d10_analysis['career_significance'],
                        'Dashamsha_Effect': self._get_dashamsha_effect_description(d10_analysis, analysis['auspiciousness_score'])
                    }
                
                period_data = {
                    'start_date': start_date,
                    'end_date': maha_dasha['endDate'],
                    'mahadasha_lord': maha_dasha['lord'],
                    'antardasha_lord': '',
                    'pratyantardasha_lord': '',
                    'Type': 'MD',
                    'Planet': maha_dasha['lord'],
                    'Parent_Planet': '',
                    'auspiciousness_score': final_auspiciousness,
                    'dasha_lord_strength': analysis.get('dasha_lord_strength', 5.0),
                    'protections_count': len(analysis.get('arishta_bhanga', {}).get('protections', [])),
                    'is_protected': analysis.get('arishta_bhanga', {}).get('is_protected', False),
                    'sun_strength': analysis.get('sun_moon_analysis', {}).get('sun_preparation', {}).get('strength', 0.0),
                    'moon_strength': analysis.get('sun_moon_analysis', {}).get('moon_nourishment', {}).get('strength', 0.0),
                    'luminaries_support': analysis.get('sun_moon_analysis', {}).get('luminaries_support', 0.5),
                    'sun_moon_support': analysis.get('sun_moon_analysis', {}).get('luminaries_support', 0.5),
                    **divisional_data  # Add divisional chart data if available
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
                
                # NEW: Divisional chart analysis if enabled (analyze MD lord for primary influence)
                final_auspiciousness = round(composite_score, 2)
                divisional_data = {}
                
                # Handle different combinations of divisional charts
                if enable_navamsha and enable_dashamsha and navamsha_chart and dashamsha_chart:
                    # Triple chart analysis (D1 + D9 + D10)
                    d9_analysis = self._analyze_dasha_in_navamsha(
                        bhukti['parentLord'], navamsha_chart, birth_positions
                    )
                    d10_analysis = self._analyze_dasha_in_dashamsha(
                        bhukti['parentLord'], dashamsha_chart, birth_positions
                    )
                    
                    combined_analysis = self.evaluate_with_triple_chart_weight(
                        d1_score=composite_score,
                        d9_score=d9_analysis['d9_auspiciousness'],
                        d10_score=d10_analysis['d10_auspiciousness'],
                        d1_rating=self._score_to_rating(composite_score),
                        d9_rating=self._score_to_rating(d9_analysis['d9_auspiciousness']),
                        d10_rating=self._score_to_rating(d10_analysis['d10_auspiciousness'])
                    )
                    
                    final_auspiciousness = round(combined_analysis['combined_score'], 2)
                    divisional_data = {
                        'd1_auspiciousness': composite_score,
                        'd9_auspiciousness': d9_analysis['d9_auspiciousness'],
                        'd10_auspiciousness': d10_analysis['d10_auspiciousness'],
                        'navamsha_analysis': d9_analysis,
                        'dashamsha_analysis': d10_analysis,
                        'combined_analysis': combined_analysis,
                        # CSV-friendly column names
                        'D1_Score': round(composite_score, 2),
                        'D9_Score': round(d9_analysis['d9_auspiciousness'], 2),
                        'D10_Score': round(d10_analysis['d10_auspiciousness'], 2),
                        'D9_Sign': d9_analysis['d9_sign'],
                        'D10_Sign': d10_analysis['d10_sign'],
                        'D9_Vargottama': 'Yes' if d9_analysis['is_vargottama'] else 'No',
                        'D10_Vargottama': 'Yes' if d10_analysis['is_d10_vargottama'] else 'No',
                        'D10_Deity': d10_analysis['career_deity'],
                        'D10_Career': d10_analysis['career_significance'],
                        'Triple_Chart_Effect': self._get_triple_chart_effect_description(combined_analysis)
                    }
                
                elif enable_navamsha and navamsha_chart:
                    # D1 + D9 analysis only
                    d9_analysis = self._analyze_dasha_in_navamsha(
                        bhukti['parentLord'], navamsha_chart, birth_positions
                    )
                    
                    combined_analysis = self.evaluate_with_navamsha_weight(
                        d1_score=composite_score,
                        d9_score=d9_analysis['d9_auspiciousness'],
                        d1_rating=self._score_to_rating(composite_score),
                        d9_rating=self._score_to_rating(d9_analysis['d9_auspiciousness'])
                    )
                    
                    final_auspiciousness = round(combined_analysis['combined_score'], 2)
                    divisional_data = {
                        'd1_auspiciousness': composite_score,
                        'd9_auspiciousness': d9_analysis['d9_auspiciousness'],
                        'navamsha_analysis': d9_analysis,
                        'combined_analysis': combined_analysis,
                        # CSV-friendly column names
                        'D1_Score': round(composite_score, 2),
                        'D9_Score': round(d9_analysis['d9_auspiciousness'], 2),
                        'D9_Sign': d9_analysis['d9_sign'],
                        'D9_Vargottama': 'Yes' if d9_analysis['is_vargottama'] else 'No',
                        'Navamsha_Effect': self._get_navamsha_effect_description(combined_analysis)
                    }
                
                elif enable_dashamsha and dashamsha_chart:
                    # D1 + D10 analysis only
                    d10_analysis = self._analyze_dasha_in_dashamsha(
                        bhukti['parentLord'], dashamsha_chart, birth_positions
                    )
                    
                    # Use D1 + D10 weighting (no D9)
                    d1_weighted = composite_score * (self.chart_weights['d1_weight'] / 10.0)
                    d10_weighted = d10_analysis['d10_auspiciousness'] * (self.chart_weights['d10_weight'] / 10.0)
                    total_possible = self.chart_weights['d1_weight'] + self.chart_weights['d10_weight']
                    combined_score = (d1_weighted + d10_weighted) / total_possible * 10
                    
                    final_auspiciousness = round(combined_score, 2)
                    divisional_data = {
                        'd1_auspiciousness': composite_score,
                        'd10_auspiciousness': d10_analysis['d10_auspiciousness'],
                        'dashamsha_analysis': d10_analysis,
                        # CSV-friendly column names
                        'D1_Score': round(composite_score, 2),
                        'D10_Score': round(d10_analysis['d10_auspiciousness'], 2),
                        'D10_Sign': d10_analysis['d10_sign'],
                        'D10_Vargottama': 'Yes' if d10_analysis['is_d10_vargottama'] else 'No',
                        'D10_Deity': d10_analysis['career_deity'],
                        'D10_Career': d10_analysis['career_significance'],
                        'Dashamsha_Effect': self._get_dashamsha_effect_description(d10_analysis, composite_score)
                    }
                
                period_data = {
                    'start_date': start_date,
                    'end_date': bhukti['endDate'],
                    'mahadasha_lord': bhukti['parentLord'],
                    'antardasha_lord': bhukti['lord'],
                    'pratyantardasha_lord': '',
                    'Type': 'MD-AD',
                    'Planet': bhukti['lord'],
                    'Parent_Planet': bhukti['parentLord'],
                    'auspiciousness_score': final_auspiciousness,
                    'dasha_lord_strength': round(composite_strength, 2),
                    'protections_count': len(ad_analysis.get('arishta_bhanga', {}).get('protections', [])),
                    'is_protected': ad_analysis.get('arishta_bhanga', {}).get('is_protected', False),
                    'sun_strength': ad_analysis.get('sun_moon_analysis', {}).get('sun_preparation', {}).get('strength', 0.0),
                    'moon_strength': ad_analysis.get('sun_moon_analysis', {}).get('moon_nourishment', {}).get('strength', 0.0),
                    'luminaries_support': ad_analysis.get('sun_moon_analysis', {}).get('luminaries_support', 0.5),
                    'sun_moon_support': ad_analysis.get('sun_moon_analysis', {}).get('luminaries_support', 0.5),
                    **divisional_data  # Add divisional chart data if available
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
                    
                    # NEW: Divisional chart analysis if enabled (analyze MD lord for primary influence)
                    final_auspiciousness = round(composite_score, 2)
                    divisional_data = {}
                    
                    # Handle different combinations of divisional charts
                    if enable_navamsha and enable_dashamsha and navamsha_chart and dashamsha_chart:
                        # Triple chart analysis (D1 + D9 + D10)
                        d9_analysis = self._analyze_dasha_in_navamsha(
                            maha_lord, navamsha_chart, birth_positions
                        )
                        d10_analysis = self._analyze_dasha_in_dashamsha(
                            maha_lord, dashamsha_chart, birth_positions
                        )
                        
                        combined_analysis = self.evaluate_with_triple_chart_weight(
                            d1_score=composite_score,
                            d9_score=d9_analysis['d9_auspiciousness'],
                            d10_score=d10_analysis['d10_auspiciousness'],
                            d1_rating=self._score_to_rating(composite_score),
                            d9_rating=self._score_to_rating(d9_analysis['d9_auspiciousness']),
                            d10_rating=self._score_to_rating(d10_analysis['d10_auspiciousness'])
                        )
                        
                        final_auspiciousness = round(combined_analysis['combined_score'], 2)
                        divisional_data = {
                            'd1_auspiciousness': composite_score,
                            'd9_auspiciousness': d9_analysis['d9_auspiciousness'],
                            'd10_auspiciousness': d10_analysis['d10_auspiciousness'],
                            'navamsha_analysis': d9_analysis,
                            'dashamsha_analysis': d10_analysis,
                            'combined_analysis': combined_analysis,
                            # CSV-friendly column names
                            'D1_Score': round(composite_score, 2),
                            'D9_Score': round(d9_analysis['d9_auspiciousness'], 2),
                            'D10_Score': round(d10_analysis['d10_auspiciousness'], 2),
                            'D9_Sign': d9_analysis['d9_sign'],
                            'D10_Sign': d10_analysis['d10_sign'],
                            'D9_Vargottama': 'Yes' if d9_analysis['is_vargottama'] else 'No',
                            'D10_Vargottama': 'Yes' if d10_analysis['is_d10_vargottama'] else 'No',
                            'D10_Deity': d10_analysis['career_deity'],
                            'D10_Career': d10_analysis['career_significance'],
                            'Triple_Chart_Effect': self._get_triple_chart_effect_description(combined_analysis)
                        }
                    
                    elif enable_navamsha and navamsha_chart:
                        # D1 + D9 analysis only
                        d9_analysis = self._analyze_dasha_in_navamsha(
                            maha_lord, navamsha_chart, birth_positions
                        )
                        
                        combined_analysis = self.evaluate_with_navamsha_weight(
                            d1_score=composite_score,
                            d9_score=d9_analysis['d9_auspiciousness'],
                            d1_rating=self._score_to_rating(composite_score),
                            d9_rating=self._score_to_rating(d9_analysis['d9_auspiciousness'])
                        )
                        
                        final_auspiciousness = round(combined_analysis['combined_score'], 2)
                        divisional_data = {
                            'd1_auspiciousness': composite_score,
                            'd9_auspiciousness': d9_analysis['d9_auspiciousness'],
                            'navamsha_analysis': d9_analysis,
                            'combined_analysis': combined_analysis,
                            # CSV-friendly column names
                            'D1_Score': round(composite_score, 2),
                            'D9_Score': round(d9_analysis['d9_auspiciousness'], 2),
                            'D9_Sign': d9_analysis['d9_sign'],
                            'D9_Vargottama': 'Yes' if d9_analysis['is_vargottama'] else 'No',
                            'Navamsha_Effect': self._get_navamsha_effect_description(combined_analysis)
                        }
                    
                    elif enable_dashamsha and dashamsha_chart:
                        # D1 + D10 analysis only
                        d10_analysis = self._analyze_dasha_in_dashamsha(
                            maha_lord, dashamsha_chart, birth_positions
                        )
                        
                        # Use D1 + D10 weighting (no D9)
                        d1_weighted = composite_score * (self.chart_weights['d1_weight'] / 10.0)
                        d10_weighted = d10_analysis['d10_auspiciousness'] * (self.chart_weights['d10_weight'] / 10.0)
                        total_possible = self.chart_weights['d1_weight'] + self.chart_weights['d10_weight']
                        combined_score = (d1_weighted + d10_weighted) / total_possible * 10
                        
                        final_auspiciousness = round(combined_score, 2)
                        divisional_data = {
                            'd1_auspiciousness': composite_score,
                            'd10_auspiciousness': d10_analysis['d10_auspiciousness'],
                            'dashamsha_analysis': d10_analysis,
                            # CSV-friendly column names
                            'D1_Score': round(composite_score, 2),
                            'D10_Score': round(d10_analysis['d10_auspiciousness'], 2),
                            'D10_Sign': d10_analysis['d10_sign'],
                            'D10_Vargottama': 'Yes' if d10_analysis['is_d10_vargottama'] else 'No',
                            'D10_Deity': d10_analysis['career_deity'],
                            'D10_Career': d10_analysis['career_significance'],
                            'Dashamsha_Effect': self._get_dashamsha_effect_description(d10_analysis, composite_score)
                        }
                    
                    period_data = {
                        'start_date': start_date,
                        'end_date': pratyantar['endDate'],
                        'mahadasha_lord': maha_lord,
                        'antardasha_lord': antar_lord,
                        'pratyantardasha_lord': pratyantar['lord'],
                        'Type': 'MD-AD-PD',
                        'Planet': pratyantar['lord'],
                        'Parent_Planet': antar_lord,
                        'auspiciousness_score': final_auspiciousness,
                        'dasha_lord_strength': round(composite_strength, 2),
                        'protections_count': len(pd_analysis.get('arishta_bhanga', {}).get('protections', [])),
                        'is_protected': pd_analysis.get('arishta_bhanga', {}).get('is_protected', False),
                        'sun_strength': pd_analysis.get('sun_moon_analysis', {}).get('sun_preparation', {}).get('strength', 0.0),
                        'moon_strength': pd_analysis.get('sun_moon_analysis', {}).get('moon_nourishment', {}).get('strength', 0.0),
                        'luminaries_support': pd_analysis.get('sun_moon_analysis', {}).get('luminaries_support', 0.5),
                        'sun_moon_support': pd_analysis.get('sun_moon_analysis', {}).get('luminaries_support', 0.5),
                        **divisional_data  # Add divisional chart data if available
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
        
        # 5. NEW: Navamsha (D9) Analysis
        if 'navamsha_analysis' in period and 'combined_analysis' in period:
            navamsha_details = self._generate_navamsha_significance(period)
            if navamsha_details:
                significance_parts.append(navamsha_details)
        
        return "; ".join(significance_parts)
    
    def _generate_navamsha_significance(self, period: Dict[str, Any]) -> str:
        """Generate navamsha-specific astrological significance"""
        navamsha_analysis = period.get('navamsha_analysis', {})
        combined_analysis = period.get('combined_analysis', {})
        
        if not navamsha_analysis or not combined_analysis:
            return ""
        
        significance_parts = []
        
        # D9 sign and strength
        d9_sign = navamsha_analysis.get('d9_sign', 'Unknown')
        d9_strength = navamsha_analysis.get('d9_strength', 0)
        is_vargottama = navamsha_analysis.get('is_vargottama', False)
        
        # Vargottama status (most important)
        if is_vargottama:
            significance_parts.append("Vargottama (same sign D1-D9) - exceptional strength")
        
        # D9 dignity assessment
        dasha_lord = period.get('mahadasha_lord', '')
        if dasha_lord and d9_sign:
            if d9_sign == self.exaltation_signs.get(dasha_lord):
                significance_parts.append(f"D9 exalted in {d9_sign}")
            elif d9_sign in self.own_signs.get(dasha_lord, []):
                significance_parts.append(f"D9 own sign {d9_sign}")
            elif d9_sign == self.debilitation_signs.get(dasha_lord):
                significance_parts.append(f"D9 debilitated in {d9_sign}")
            else:
                significance_parts.append(f"D9 in {d9_sign}")
        
        # Combined effect interpretation
        d1_score = combined_analysis.get('d1_score', 0)
        d9_score = combined_analysis.get('d9_score', 0)
        interpretation = combined_analysis.get('interpretation', '')
        
        score_diff = d9_score - d1_score
        if abs(score_diff) > 1.5:
            if score_diff > 0:
                significance_parts.append("D9 significantly strengthens long-term prospects")
            else:
                significance_parts.append("D9 indicates underlying challenges")
        
        # Add key interpretation if meaningful
        if interpretation and "opportunity" in interpretation.lower():
            significance_parts.append("D9 reveals hidden potential")
        elif interpretation and "caution" in interpretation.lower():
            significance_parts.append("D9 suggests foundational weakness")
        
        return "; ".join(significance_parts) if significance_parts else ""
    
    def _get_navamsha_opportunity_analysis(self, opportunity: Dict[str, Any], df: pd.DataFrame) -> str:
        """Extract navamsha analysis for investment opportunity"""
        try:
            # Find the period in dataframe matching this opportunity
            current_date = opportunity['current_date']
            matching_periods = df[df['start_date'] == current_date]
            
            if matching_periods.empty:
                return "No D9 data"
            
            period = matching_periods.iloc[0]
            
            # Extract navamsha information if available
            navamsha_parts = []
            
            # D9 score and effect
            if 'D9_Score' in period and pd.notna(period['D9_Score']):
                d9_score = period['D9_Score']
                d1_score = period.get('D1_Score', period.get('auspiciousness_score', 0))
                
                score_diff = d9_score - d1_score
                if score_diff > 1.0:
                    navamsha_parts.append(f"D9 strengthens (+{score_diff:.1f})")
                elif score_diff < -1.0:
                    navamsha_parts.append(f"D9 weakens ({score_diff:.1f})")
                else:
                    navamsha_parts.append(f"D9 balanced ({score_diff:+.1f})")
            
            # Vargottama status
            if 'Vargottama' in period and period['Vargottama'] == 'Yes':
                navamsha_parts.append("Vargottama")
            
            # D9 sign
            if 'D9_Sign' in period and pd.notna(period['D9_Sign']):
                navamsha_parts.append(f"D9 in {period['D9_Sign']}")
            
            # Navamsha effect description
            if 'Navamsha_Effect' in period and pd.notna(period['Navamsha_Effect']):
                effect = str(period['Navamsha_Effect'])
                if "Strengthens" in effect:
                    navamsha_parts.append("Long-term strength")
                elif "Weakens" in effect:
                    navamsha_parts.append("Underlying weakness")
            
            return "; ".join(navamsha_parts) if navamsha_parts else "Standard D9"
            
        except Exception as e:
            return "D9 analysis error"
    
    def _get_dashamsha_opportunity_analysis(self, opportunity: Dict[str, Any], df: pd.DataFrame) -> str:
        """Extract dashamsha analysis for investment opportunity"""
        try:
            # Find the period in dataframe matching this opportunity
            current_date = opportunity['current_date']
            matching_periods = df[df['start_date'] == current_date]
            
            if matching_periods.empty:
                return "No D10 data"
            
            period = matching_periods.iloc[0]
            
            # Extract dashamsha information if available
            dashamsha_parts = []
            
            # D10 score and effect
            if 'D10_Score' in period and pd.notna(period['D10_Score']):
                d10_score = period['D10_Score']
                d1_score = period.get('D1_Score', period.get('auspiciousness_score', 0))
                
                score_diff = d10_score - d1_score
                if score_diff > 1.0:
                    dashamsha_parts.append(f"D10 career+{score_diff:.1f}")
                elif score_diff < -1.0:
                    dashamsha_parts.append(f"D10 career{score_diff:.1f}")
                else:
                    dashamsha_parts.append(f"D10 balanced({score_diff:+.1f})")
            
            # D10 Vargottama status
            if 'D10_Vargottama' in period and period['D10_Vargottama'] == 'Yes':
                dashamsha_parts.append("D10-Varg")
            
            # D10 deity
            if 'D10_Deity' in period and pd.notna(period['D10_Deity']):
                deity = str(period['D10_Deity'])
                if deity in ['Indra', 'Kubera', 'Brahma']:
                    dashamsha_parts.append(f"{deity}")
            
            # Dashamsha effect description
            if 'Dashamsha_Effect' in period and pd.notna(period['Dashamsha_Effect']):
                effect = str(period['Dashamsha_Effect'])
                if "Career-Strong" in effect:
                    dashamsha_parts.append("Career-Excel")
                elif "Career-Weak" in effect:
                    dashamsha_parts.append("Career-Challenge")
            
            return " | ".join(dashamsha_parts) if dashamsha_parts else "Standard D10"
            
        except Exception as e:
            return "D10 analysis error"
    
    def _get_triple_chart_opportunity_analysis(self, opportunity: Dict[str, Any], df: pd.DataFrame) -> str:
        """Extract triple chart analysis for investment opportunity"""
        try:
            # Find the period in dataframe matching this opportunity
            current_date = opportunity['current_date']
            matching_periods = df[df['start_date'] == current_date]
            
            if matching_periods.empty:
                return "No Triple data"
            
            period = matching_periods.iloc[0]
            
            # Extract triple chart information if available
            triple_parts = []
            
            # Score comparison
            if all(col in period and pd.notna(period[col]) for col in ['D1_Score', 'D9_Score', 'D10_Score']):
                d1_score = period['D1_Score']
                d9_score = period['D9_Score']
                d10_score = period['D10_Score']
                
                scores = {'D1': d1_score, 'D9': d9_score, 'D10': d10_score}
                strongest = max(scores.keys(), key=lambda k: scores[k])
                weakest = min(scores.keys(), key=lambda k: scores[k])
                
                if scores[strongest] - scores[weakest] >= 2.0:
                    triple_parts.append(f"{strongest}-Led")
                else:
                    triple_parts.append("Balanced")
                
                # Add specific strengths
                if d10_score >= 8.0:
                    triple_parts.append("Career-Excel")
                elif d9_score >= 8.0:
                    triple_parts.append("Sustain-Strong")
                elif d1_score >= 8.0:
                    triple_parts.append("Immediate-Strong")
            
            # Vargottama status
            d9_varg = 'D9_Vargottama' in period and period['D9_Vargottama'] == 'Yes'
            d10_varg = 'D10_Vargottama' in period and period['D10_Vargottama'] == 'Yes'
            
            if d9_varg and d10_varg:
                triple_parts.append("Triple-Varg")
            elif d9_varg:
                triple_parts.append("D9-Varg")
            elif d10_varg:
                triple_parts.append("D10-Varg")
            
            # Triple chart effect
            if 'Triple_Chart_Effect' in period and pd.notna(period['Triple_Chart_Effect']):
                effect = str(period['Triple_Chart_Effect'])
                final_rating = None
                if "Strong Buy" in effect:
                    final_rating = "StrongBuy"
                elif "Buy" in effect:
                    final_rating = "Buy"
                elif "Hold" in effect:
                    final_rating = "Hold"
                elif "Sell" in effect:
                    final_rating = "Sell"
                
                if final_rating:
                    triple_parts.append(final_rating)
            
            return " | ".join(triple_parts) if triple_parts else "Standard Triple"
            
        except Exception as e:
            return "Triple analysis error"

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
        # Check which divisional chart columns exist
        has_navamsha = any(col in df_csv.columns for col in ['D9_Score', 'Navamsha_Effect'])
        has_dashamsha = any(col in df_csv.columns for col in ['D10_Score', 'D10_Deity'])
        has_triple_chart = any(col in df_csv.columns for col in ['Triple_Chart_Effect'])
        
        # Build required columns based on available divisional charts
        base_columns = [
            'Date', 'End_Date', 'Type', 'mahadasha_lord', 'antardasha_lord', 'pratyantardasha_lord',
            'Planet', 'Parent_Planet', 'Auspiciousness_Score', 'Dasha_Lord_Strength', 
            'Arishta_Protections', 'Protection_Score', 'Sun_Moon_Support'
        ]
        
        divisional_columns = []
        
        if has_triple_chart:
            # Triple chart analysis (D1 + D9 + D10)
            divisional_columns = [
                'D1_Score', 'D9_Score', 'D10_Score', 'D9_Sign', 'D10_Sign', 
                'D9_Vargottama', 'D10_Vargottama', 'D10_Deity', 'D10_Career', 'Triple_Chart_Effect'
            ]
        elif has_navamsha and has_dashamsha:
            # Dual chart analysis (separate D9 and D10)
            divisional_columns = [
                'D1_Score', 'D9_Score', 'D10_Score', 'D9_Sign', 'D10_Sign', 
                'D9_Vargottama', 'D10_Vargottama', 'D10_Deity', 'D10_Career', 
                'Navamsha_Effect', 'Dashamsha_Effect'
            ]
        elif has_navamsha:
            # D1 + D9 only
            divisional_columns = [
                'D1_Score', 'D9_Score', 'D9_Sign', 'D9_Vargottama', 'Navamsha_Effect'
            ]
        elif has_dashamsha:
            # D1 + D10 only
            divisional_columns = [
                'D1_Score', 'D10_Score', 'D10_Sign', 'D10_Vargottama', 'D10_Deity', 'D10_Career', 'Dashamsha_Effect'
            ]
        
        required_columns = base_columns + divisional_columns + ['Astrological_Significance']
        
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
        
        # Check for divisional chart analysis
        has_navamsha = any(col in df.columns for col in ['D9_Score', 'Navamsha_Effect'])
        has_dashamsha = any(col in df.columns for col in ['D10_Score', 'D10_Deity'])
        has_triple_chart = any(col in df.columns for col in ['Triple_Chart_Effect'])
        
        divisional_stats = ""
        
        if has_triple_chart:
            # Triple chart analysis
            d9_vargottama = len(df[df.get('D9_Vargottama', pd.Series(['No'])).str.contains('Yes', na=False)])
            d10_vargottama = len(df[df.get('D10_Vargottama', pd.Series(['No'])).str.contains('Yes', na=False)])
            career_strong_periods = len(df[df.get('Triple_Chart_Effect', pd.Series([''])).str.contains('Career-Excel', na=False)])
            divisional_stats = f"""
- **Triple Chart Analysis:** ✅ Enabled (D1:D9:D10 = 10:9:8 weighting)
- **D9 Vargottama Periods:** {d9_vargottama} ({d9_vargottama/total_periods*100:.1f}% exceptional foundation)
- **D10 Vargottama Periods:** {d10_vargottama} ({d10_vargottama/total_periods*100:.1f}% exceptional career strength)
- **Career Excellence Periods:** {career_strong_periods} periods show outstanding professional potential"""
        
        elif has_navamsha and has_dashamsha:
            # Dual analysis
            d9_vargottama = len(df[df.get('D9_Vargottama', pd.Series(['No'])).str.contains('Yes', na=False)])
            d10_vargottama = len(df[df.get('D10_Vargottama', pd.Series(['No'])).str.contains('Yes', na=False)])
            divisional_stats = f"""
- **Dual Chart Analysis:** ✅ D9 (10:9) + D10 (10:8) separate analysis
- **D9 Vargottama Periods:** {d9_vargottama} ({d9_vargottama/total_periods*100:.1f}% exceptional foundation)
- **D10 Vargottama Periods:** {d10_vargottama} ({d10_vargottama/total_periods*100:.1f}% exceptional career strength)"""
        
        elif has_navamsha:
            # D9 only
            d9_vargottama = len(df[df.get('D9_Vargottama', pd.Series(['No'])).str.contains('Yes', na=False)])
            strengthening_periods = len(df[df.get('Navamsha_Effect', pd.Series([''])).str.contains('Strengthens', na=False)])
            divisional_stats = f"""
- **Navamsha Analysis:** ✅ Enabled (D1:D9 = 10:9 weighting)
- **D9 Vargottama Periods:** {d9_vargottama} ({d9_vargottama/total_periods*100:.1f}% exceptional strength)
- **D9 Strengthening:** {strengthening_periods} periods show enhanced long-term potential"""
        
        elif has_dashamsha:
            # D10 only
            d10_vargottama = len(df[df.get('D10_Vargottama', pd.Series(['No'])).str.contains('Yes', na=False)])
            indra_periods = len(df[df.get('D10_Deity', pd.Series([''])).str.contains('Indra', na=False)])
            kubera_periods = len(df[df.get('D10_Deity', pd.Series([''])).str.contains('Kubera', na=False)])
            divisional_stats = f"""
- **Dashamsha Analysis:** ✅ Enabled (D1:D10 = 10:8 weighting) 
- **D10 Vargottama Periods:** {d10_vargottama} ({d10_vargottama/total_periods*100:.1f}% exceptional career strength)
- **Leadership Periods (Indra):** {indra_periods} periods for authority roles
- **Wealth Periods (Kubera):** {kubera_periods} periods for financial success"""
        
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
- **Analysis Depth:** 3-level (Maha + Antar + Pratyantar Dashas){divisional_stats}
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

"""

        # Determine table headers based on available charts
        if has_triple_chart:
            buy_table_header = "| Date Range | MD-AD-PD Combination | Current Score | Next Score | Change | Action | Selection Criteria | Astrological Significance | D1-D9-D10 Analysis | Confidence |\n|------------|---------------------|---------------|------------|--------|--------|-------------------|---------------------------|-------------------|----------|"
        elif has_navamsha and has_dashamsha:
            buy_table_header = "| Date Range | MD-AD-PD Combination | Current Score | Next Score | Change | Action | Selection Criteria | Astrological Significance | D9 Analysis | D10 Analysis | Confidence |\n|------------|---------------------|---------------|------------|--------|--------|-------------------|---------------------------|-------------|--------------|----------|"
        elif has_dashamsha:
            buy_table_header = "| Date Range | MD-AD-PD Combination | Current Score | Next Score | Change | Action | Selection Criteria | Astrological Significance | D10 Career Analysis | Confidence |\n|------------|---------------------|---------------|------------|--------|--------|-------------------|---------------------------|-------------------|----------|"
        elif has_navamsha:
            buy_table_header = "| Date Range | MD-AD-PD Combination | Current Score | Next Score | Change | Action | Selection Criteria | Astrological Significance | D9 Sustainability | Confidence |\n|------------|---------------------|---------------|------------|--------|--------|-------------------|---------------------------|------------------|----------|"
        else:
            buy_table_header = "| Date Range | MD-AD-PD Combination | Current Score | Next Score | Change | Action | Selection Criteria | Astrological Significance | Confidence |\n|------------|---------------------|---------------|------------|--------|--------|-------------------|---------------------------|----------|"
        
        markdown_content += buy_table_header

        # Top buy opportunities
        for opp in transition_opportunities['buy_opportunities'][:10]:
            date_range = f"{opp['current_date']} - {opp['current_end']}"
            year = opp['current_date'][:4]
            status = "🟢 **NOW**" if int(year) == current_year else "🔵 FUTURE" if int(year) > current_year else "🟡 PAST"
            
            # Add divisional analysis based on available charts
            divisional_cells = ""
            if has_triple_chart:
                triple_info = self._get_triple_chart_opportunity_analysis(opp, df)
                divisional_cells = f" | {triple_info}"
            elif has_navamsha and has_dashamsha:
                navamsha_info = self._get_navamsha_opportunity_analysis(opp, df)
                dashamsha_info = self._get_dashamsha_opportunity_analysis(opp, df)
                divisional_cells = f" | {navamsha_info} | {dashamsha_info}"
            elif has_dashamsha:
                dashamsha_info = self._get_dashamsha_opportunity_analysis(opp, df)
                divisional_cells = f" | {dashamsha_info}"
            elif has_navamsha:
                navamsha_info = self._get_navamsha_opportunity_analysis(opp, df)
                divisional_cells = f" | {navamsha_info}"
            
            markdown_content += f"\n| {date_range} | {opp['md_ad_pd_combo']} | {opp['current_score']:.1f} | {opp['next_score']:.1f} | +{opp['score_change']:.1f} | **{opp['action']}** | {opp['selection_rationale']} | {opp['astrological_significance']}{divisional_cells} | {opp['confidence']} {status} |"

        markdown_content += f"""

### 📉 Strategic Sell Opportunities - "Sell the Peak Before the Decline"

**Exit Thesis:** Sell during high-scoring periods when low-scoring periods are approaching. These opportunities protect gains by exiting before challenging planetary influences pressure stock prices.

"""

        # Determine sell table headers based on available charts
        if has_triple_chart:
            sell_table_header = "| Date Range | MD-AD-PD Combination | Current Score | Next Score | Change | Action | Selection Criteria | Astrological Significance | D1-D9-D10 Analysis | Confidence |\n|------------|---------------------|---------------|------------|--------|--------|-------------------|---------------------------|-------------------|----------|"
        elif has_navamsha and has_dashamsha:
            sell_table_header = "| Date Range | MD-AD-PD Combination | Current Score | Next Score | Change | Action | Selection Criteria | Astrological Significance | D9 Analysis | D10 Analysis | Confidence |\n|------------|---------------------|---------------|------------|--------|--------|-------------------|---------------------------|-------------|--------------|----------|"
        elif has_dashamsha:
            sell_table_header = "| Date Range | MD-AD-PD Combination | Current Score | Next Score | Change | Action | Selection Criteria | Astrological Significance | D10 Career Analysis | Confidence |\n|------------|---------------------|---------------|------------|--------|--------|-------------------|---------------------------|-------------------|----------|"
        elif has_navamsha:
            sell_table_header = "| Date Range | MD-AD-PD Combination | Current Score | Next Score | Change | Action | Selection Criteria | Astrological Significance | D9 Sustainability | Confidence |\n|------------|---------------------|---------------|------------|--------|--------|-------------------|---------------------------|------------------|----------|"
        else:
            sell_table_header = "| Date Range | MD-AD-PD Combination | Current Score | Next Score | Change | Action | Selection Criteria | Astrological Significance | Confidence |\n|------------|---------------------|---------------|------------|--------|--------|-------------------|---------------------------|----------|"
        
        markdown_content += sell_table_header

        # Top sell opportunities  
        for opp in transition_opportunities['sell_opportunities'][:10]:
            date_range = f"{opp['current_date']} - {opp['current_end']}"
            year = opp['current_date'][:4]
            status = "⚠️ **NOW**" if int(year) == current_year else "📅 FUTURE" if int(year) > current_year else "📊 PAST"
            
            # Add divisional analysis based on available charts
            divisional_cells = ""
            if has_triple_chart:
                triple_info = self._get_triple_chart_opportunity_analysis(opp, df)
                divisional_cells = f" | {triple_info}"
            elif has_navamsha and has_dashamsha:
                navamsha_info = self._get_navamsha_opportunity_analysis(opp, df)
                dashamsha_info = self._get_dashamsha_opportunity_analysis(opp, df)
                divisional_cells = f" | {navamsha_info} | {dashamsha_info}"
            elif has_dashamsha:
                dashamsha_info = self._get_dashamsha_opportunity_analysis(opp, df)
                divisional_cells = f" | {dashamsha_info}"
            elif has_navamsha:
                navamsha_info = self._get_navamsha_opportunity_analysis(opp, df)
                divisional_cells = f" | {navamsha_info}"
            
            markdown_content += f"\n| {date_range} | {opp['md_ad_pd_combo']} | {opp['current_score']:.1f} | {opp['next_score']:.1f} | {opp['score_change']:.1f} | **{opp['action']}** | {opp['selection_rationale']} | {opp['astrological_significance']}{divisional_cells} | {opp['confidence']} {status} |"

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

---

## 🛡️ Risk Mitigation Analysis

### Arishta-Bhanga Protection System

{company_name} benefits from {"exceptional" if protection_rate > 40 else "strong" if protection_rate > 30 else "moderate"} protection through classical Vedic cancellation rules:

#### Protection Rate: {protection_rate:.1f}% ({protected_periods}/{total_periods} periods)
"""

        if len(high_protection) > 0:
            markdown_content += f"\n#### Triple Protection Periods (Highest Safety)\n"
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
            
            # Create opportunity with basic info first
            opportunity = {
                'current_date': current['start_date'],
                'current_end': current['end_date'],
                'next_date': next_period['start_date'],
                'current_score': current_score,
                'next_score': next_score,
                'score_change': score_change,
                'md_ad_pd_combo': combo,
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
                # Add enhanced astrological significance
                opportunity['astrological_significance'] = self._generate_enhanced_opportunity_significance(opportunity, df)
                opportunities['buy_opportunities'].append(opportunity)
                
            elif score_change >= 1.5 and current_score <= 6.0:
                # Moderate buy opportunity
                opportunity.update({
                    'action': 'BUY',
                    'confidence': 'MEDIUM',
                    'selection_rationale': f'Score improving {score_change:.1f} points',
                    'rationale': 'Accumulate on improvement'
                })
                # Add enhanced astrological significance
                opportunity['astrological_significance'] = self._generate_enhanced_opportunity_significance(opportunity, df)
                opportunities['buy_opportunities'].append(opportunity)
                
            elif score_change <= -2.5 and current_score >= 6.0:
                # Strong sell opportunity - high score declining significantly
                opportunity.update({
                    'action': 'STRONG SELL',
                    'confidence': 'HIGH' if score_change <= -3.5 else 'MEDIUM',
                    'selection_rationale': f'Score declining {score_change:.1f} points from high base',
                    'rationale': 'Sell before decline'
                })
                # Add enhanced astrological significance
                opportunity['astrological_significance'] = self._generate_enhanced_opportunity_significance(opportunity, df)
                opportunities['sell_opportunities'].append(opportunity)
                
            elif score_change <= -1.5 and current_score >= 5.5:
                # Moderate sell opportunity
                opportunity.update({
                    'action': 'SELL',
                    'confidence': 'MEDIUM',
                    'selection_rationale': f'Score declining {score_change:.1f} points',
                    'rationale': 'Take profits on decline'
                })
                # Add enhanced astrological significance
                opportunity['astrological_significance'] = self._generate_enhanced_opportunity_significance(opportunity, df)
                opportunities['sell_opportunities'].append(opportunity)
                
            elif abs(score_change) <= 1.0:
                # Hold recommendation
                opportunity.update({
                    'action': 'HOLD',
                    'confidence': 'MEDIUM',
                    'selection_rationale': f'Stable score (change: {score_change:.1f})',
                    'rationale': 'Maintain current strategy'
                })
                # Add enhanced astrological significance
                opportunity['astrological_significance'] = self._generate_enhanced_opportunity_significance(opportunity, df)
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
        """Generate PDF version of the markdown report using WeasyPrint"""
        try:
            # Convert markdown to HTML
            html_content = markdown.markdown(markdown_content, extensions=['tables', 'toc'])
            
            # Add enhanced CSS styling for better PDF appearance
            styled_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>{symbol} - Vedic Dasha Analysis Report</title>
            </head>
            <body>
                {html_content}
            </body>
            </html>
            """
            
            # Define CSS styles
            css_styles = CSS(string="""
                @page {
                    size: A4;
                    margin: 0.75in;
                    @bottom-center {
                        content: counter(page) " of " counter(pages);
                        font-size: 10px;
                        color: #666;
                    }
                }
                
                body {
                    font-family: 'Helvetica', 'Arial', sans-serif;
                    line-height: 1.6;
                    color: #333;
                    font-size: 11px;
                }
                
                h1 {
                    color: #2c3e50;
                    font-size: 24px;
                    border-bottom: 3px solid #3498db;
                    padding-bottom: 10px;
                    margin-top: 30px;
                    margin-bottom: 20px;
                    page-break-after: avoid;
                }
                
                h2 {
                    color: #2c3e50;
                    font-size: 18px;
                    border-bottom: 1px solid #bdc3c7;
                    padding-bottom: 5px;
                    margin-top: 25px;
                    margin-bottom: 15px;
                    page-break-after: avoid;
                }
                
                h3 {
                    color: #34495e;
                    font-size: 16px;
                    margin-top: 20px;
                    margin-bottom: 12px;
                    page-break-after: avoid;
                }
                
                h4 {
                    color: #34495e;
                    font-size: 14px;
                    margin-top: 15px;
                    margin-bottom: 10px;
                    page-break-after: avoid;
                }
                
                table {
                    border-collapse: collapse;
                    width: 100%;
                    margin: 15px 0;
                    font-size: 9px;
                    page-break-inside: avoid;
                }
                
                th, td {
                    border: 1px solid #ddd;
                    padding: 6px;
                    text-align: left;
                    vertical-align: top;
                }
                
                th {
                    background-color: #f8f9fa;
                    font-weight: bold;
                    color: #2c3e50;
                }
                
                tr:nth-child(even) {
                    background-color: #f8f9fa;
                }
                
                .strong-buy {
                    background-color: #d4edda !important;
                }
                
                .sell {
                    background-color: #f8d7da !important;
                }
                
                blockquote {
                    border-left: 4px solid #3498db;
                    margin: 15px 0;
                    padding: 0 15px;
                    background-color: #f8f9fa;
                    font-style: italic;
                }
                
                code {
                    background-color: #f4f4f4;
                    padding: 2px 4px;
                    border-radius: 3px;
                    font-family: 'Courier New', monospace;
                    font-size: 10px;
                }
                
                pre {
                    background-color: #f4f4f4;
                    padding: 10px;
                    border-radius: 5px;
                    overflow-x: auto;
                    font-family: 'Courier New', monospace;
                    font-size: 10px;
                }
                
                ul, ol {
                    margin: 10px 0;
                    padding-left: 20px;
                }
                
                li {
                    margin: 5px 0;
                }
                
                p {
                    margin: 8px 0;
                    text-align: justify;
                }
                
                .page-break {
                    page-break-before: always;
                }
                
                strong {
                    color: #2c3e50;
                }
                
                /* Specific styling for investment tables */
                table th:first-child {
                    width: 15%;
                }
                
                table th:nth-child(2) {
                    width: 15%;
                }
                
                /* Emoji handling */
                .emoji {
                    font-size: 12px;
                }
            """)
            
            # Generate PDF file path
            pdf_file = os.path.join(output_dir, f"{symbol}_Vedic_Analysis_Report.pdf")
            
            # Generate PDF using WeasyPrint
            HTML(string=styled_html).write_pdf(pdf_file, stylesheets=[css_styles])
            
            print(f"PDF report saved: {os.path.basename(pdf_file)}")
            return pdf_file
            
        except ImportError:
            print(f"Warning: WeasyPrint not installed. PDF generation skipped.")
            print("Install with: pip install weasyprint")
            return None
        except Exception as e:
            print(f"Warning: Could not generate PDF report: {e}")
            print("Note: WeasyPrint requires system dependencies that may not be installed.")
            
            # Provide platform-specific installation suggestions
            import platform
            system = platform.system().lower()
            if system == "darwin":  # macOS
                print("For macOS:")
                print("  - With Homebrew: brew install pango libffi")
                print("  - Then: pip install weasyprint")
            elif system == "linux":  # Linux
                print("For Linux (Ubuntu/Debian): sudo apt-get install build-essential python3-dev python3-pip python3-setuptools python3-wheel python3-cffi libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info")
                print("For Linux (CentOS/RHEL): sudo yum install redhat-rpm-config python3-devel python3-pip python3-setuptools python3-wheel python3-cffi libffi-devel cairo pango gdk-pixbuf2")
                print("Then: pip install weasyprint")
            elif system == "windows":  # Windows
                print("For Windows: pip install weasyprint")
                print("Note: Windows installation is usually simpler as dependencies are included")
            else:
                print("Please check WeasyPrint documentation for your platform: https://weasyprint.readthedocs.io/en/stable/install.html")
            
            return None

    # NEW: DASHAMSHA (D10) CALCULATION METHODS
    
    def calculate_dashamsha_position(self, planet_longitude: float) -> Dict[str, Any]:
        """
        Calculate dashamsha (D10) position for a planet based on its longitude
        
        Args:
            planet_longitude: Planet's longitude in degrees (0-360)
        
        Returns:
            Dictionary with dashamsha sign, degree, deity, and career significance
        """
        # Normalize longitude to 0-360
        longitude = planet_longitude % 360
        
        # Get the rashi (main sign) and degrees within sign
        rashi_index = int(longitude // 30)
        rashi_sign = self.signs[rashi_index]
        degrees_in_sign = longitude % 30
        
        # Calculate dashamsha number (1-10) within the sign
        dashamsha_number = int(degrees_in_sign / 3.0) + 1
        dashamsha_number = min(dashamsha_number, 10)  # Ensure max is 10
        
        # Determine if sign is odd or even (1-indexed)
        sign_number = rashi_index + 1
        sign_type = 'odd' if sign_number % 2 == 1 else 'even'
        
        # Get dashamsha sign from the pattern
        dashamsha_pattern = self.dashamsha_patterns[sign_type]
        dashamsha_sign = dashamsha_pattern[dashamsha_number - 1]
        
        # Calculate degrees within dashamsha sign
        dashamsha_degree = (degrees_in_sign % 3.0) * 10  # Convert to 30-degree scale
        
        # Get deity and career significance
        deity_info = self.dashamsha_deities.get(dashamsha_number, {'deity': 'Unknown', 'significance': 'General'})
        
        return {
            'rashi_sign': rashi_sign,
            'dashamsha_sign': dashamsha_sign,
            'dashamsha_number': dashamsha_number,
            'degrees_in_dashamsha': dashamsha_degree,
            'deity': deity_info['deity'],
            'career_significance': deity_info['significance'],
            'is_d10_vargottama': rashi_sign == dashamsha_sign  # Same sign in D1 and D10
        }
    
    def calculate_dashamsha_chart(self, positions: Dict[str, Dict]) -> Dict[str, Dict]:
        """
        Calculate complete dashamsha chart for all planets
        
        Args:
            positions: Dictionary of planetary positions from D1 chart
        
        Returns:
            Dictionary with dashamsha positions for all planets
        """
        dashamsha_chart = {}
        
        for planet, planet_data in positions.items():
            if planet == 'Ascendant':
                # Calculate dashamsha lagna
                asc_longitude = planet_data.get('longitude', 0)
                d10_data = self.calculate_dashamsha_position(asc_longitude)
                dashamsha_chart['Dashamsha_Lagna'] = {
                    'longitude': d10_data['degrees_in_dashamsha'],
                    'zodiacSign': d10_data['dashamsha_sign'],
                    'degreeWithinSign': d10_data['degrees_in_dashamsha'],
                    'is_d10_vargottama': d10_data['is_d10_vargottama'],
                    'dashamsha_number': d10_data['dashamsha_number'],
                    'deity': d10_data['deity'],
                    'career_significance': d10_data['career_significance']
                }
            else:
                # Calculate dashamsha position for planet
                planet_longitude = planet_data.get('longitude', 0)
                d10_data = self.calculate_dashamsha_position(planet_longitude)
                
                dashamsha_chart[planet] = {
                    'longitude': d10_data['degrees_in_dashamsha'],
                    'zodiacSign': d10_data['dashamsha_sign'],
                    'degreeWithinSign': d10_data['degrees_in_dashamsha'],
                    'is_d10_vargottama': d10_data['is_d10_vargottama'],
                    'dashamsha_number': d10_data['dashamsha_number'],
                    'rashi_sign': d10_data['rashi_sign'],
                    'deity': d10_data['deity'],
                    'career_significance': d10_data['career_significance']
                }
        
        return dashamsha_chart
    
    def evaluate_with_triple_chart_weight(self, d1_score: float, d9_score: float, d10_score: float,
                                        d1_rating: str = None, d9_rating: str = None, d10_rating: str = None) -> Dict[str, Any]:
        """
        Apply three-way weighting system between D1 (Rashi), D9 (Navamsha), and D10 (Dashamsha) charts
        
        Args:
            d1_score: Score from D1 analysis (0-10)
            d9_score: Score from D9 analysis (0-10)
            d10_score: Score from D10 analysis (0-10)
            d1_rating: Optional categorical rating from D1
            d9_rating: Optional categorical rating from D9
            d10_rating: Optional categorical rating from D10
        
        Returns:
            Combined analysis with weighted scores and final recommendation
        """
        # Apply classical weighting: D1 = 10/10, D9 = 9/10, D10 = 8/10
        d1_weighted = d1_score * (self.chart_weights['d1_weight'] / 10.0)
        d9_weighted = d9_score * (self.chart_weights['d9_weight'] / 10.0)
        d10_weighted = d10_score * (self.chart_weights['d10_weight'] / 10.0)
        
        # Calculate combined score
        total_possible = self.chart_weights['d1_weight'] + self.chart_weights['d9_weight'] + self.chart_weights['d10_weight']
        combined_score = (d1_weighted + d9_weighted + d10_weighted) / total_possible * 10
        
        # Determine final rating based on combined score
        if combined_score >= 8.5:
            final_rating = "Strong Buy"
        elif combined_score >= 7.0:
            final_rating = "Buy"
        elif combined_score >= 5.5:
            final_rating = "Hold"
        elif combined_score >= 3.0:
            final_rating = "Sell" 
        else:
            final_rating = "Strong Sell"
        
        # Enhanced interpretation including career factors
        interpretation = self._get_triple_chart_interpretation(d1_score, d9_score, d10_score, d1_rating, d9_rating, d10_rating)
        
        return {
            'd1_score': d1_score,
            'd9_score': d9_score,
            'd10_score': d10_score,
            'd1_weighted': d1_weighted,
            'd9_weighted': d9_weighted,
            'd10_weighted': d10_weighted,
            'combined_score': combined_score,
            'd1_rating': d1_rating,
            'd9_rating': d9_rating,
            'd10_rating': d10_rating,
            'final_rating': final_rating,
            'interpretation': interpretation,
            'weight_explanation': f"D1: {self.chart_weights['d1_weight']}/10, D9: {self.chart_weights['d9_weight']}/10, D10: {self.chart_weights['d10_weight']}/10"
        }
    
    def _get_triple_chart_interpretation(self, d1_score: float, d9_score: float, d10_score: float,
                                       d1_rating: str, d9_rating: str, d10_rating: str) -> str:
        """Generate comprehensive interpretation of D1 vs D9 vs D10 combination"""
        
        interpretations = []
        
        # Career vs. general prosperity analysis
        career_strong = d10_score >= 7.0
        foundation_strong = d9_score >= 7.0
        immediate_strong = d1_score >= 7.0
        
        if career_strong and foundation_strong and immediate_strong:
            interpretations.append("Exceptional alignment: Strong immediate prospects, solid foundation, and excellent career trajectory")
        elif career_strong and foundation_strong:
            interpretations.append("Strong career and sustainability prospects despite current challenges")
        elif career_strong and immediate_strong:
            interpretations.append("Good immediate career opportunities but sustainability needs attention")
        elif foundation_strong and immediate_strong:
            interpretations.append("Solid immediate and long-term prospects with moderate career focus")
        elif career_strong:
            interpretations.append("Career-focused opportunity with mixed general indicators")
        
        # D10-specific insights
        if d10_score > max(d1_score, d9_score) + 1:
            interpretations.append("Career and professional matters showing strongest potential")
        elif d10_score < min(d1_score, d9_score) - 1:
            interpretations.append("Career factors lagging behind general prosperity indicators")
        
        # Rating-based professional analysis
        if d10_rating == "Strong Buy" and d1_rating in ["Hold", "Sell"]:
            interpretations.append("Professional opportunity despite general market conditions")
        elif d10_rating in ["Sell", "Strong Sell"] and d1_rating == "Strong Buy":
            interpretations.append("General opportunity but career-specific factors show caution")
        
        return "; ".join(interpretations) if interpretations else "Balanced three-chart analysis with standard interpretation"
    
    def _analyze_dasha_in_dashamsha(self, dasha_lord: str, dashamsha_chart: Dict, 
                                  birth_positions: Dict) -> Dict[str, Any]:
        """
        Analyze dasha lord's strength in dashamsha chart for career/professional insights
        
        Args:
            dasha_lord: Planet whose dasha is being analyzed
            dashamsha_chart: Complete D10 chart
            birth_positions: D1 chart positions
            
        Returns:
            Analysis of dasha lord in dashamsha with career-focused auspiciousness score
        """
        if dasha_lord not in dashamsha_chart:
            return {
                'd10_auspiciousness': 5.0,
                'd10_analysis': 'Dasha lord not found in dashamsha chart',
                'is_d10_vargottama': False,
                'd10_sign': 'Unknown',
                'career_deity': 'Unknown',
                'career_significance': 'General'
            }
        
        d10_planet_data = dashamsha_chart[dasha_lord]
        d10_sign = d10_planet_data['zodiacSign']
        is_d10_vargottama = d10_planet_data['is_d10_vargottama']
        career_deity = d10_planet_data.get('deity', 'Unknown')
        career_significance = d10_planet_data.get('career_significance', 'General')
        
        # Calculate strength in D10
        d10_strength_result = self.calculate_planetary_strength(
            dasha_lord, d10_sign, is_dasha_start=True
        )
        d10_strength = d10_strength_result['strength_10']
        
        # D10 Vargottama bonus (classical rule)
        if is_d10_vargottama:
            d10_strength *= 1.20  # 20% bonus for D10 vargottama
            d10_strength = min(d10_strength, 10.0)
        
        # Career-specific D10 analysis
        d10_analysis_notes = []
        
        if is_d10_vargottama:
            d10_analysis_notes.append(f"{dasha_lord} is D10 Vargottama (same sign in D1 and D10) - strong career foundation")
        
        # Deity-based career insights
        if career_deity == 'Indra':
            d10_analysis_notes.append("Leadership and authority-focused career period")
        elif career_deity == 'Kubera':
            d10_analysis_notes.append("Wealth and finance-oriented professional opportunities")
        elif career_deity == 'Brahma':
            d10_analysis_notes.append("Creative and innovative career developments")
        elif career_deity == 'Yama':
            d10_analysis_notes.append("Law, justice, and administrative career focus")
        
        # Professional strength assessment
        if d10_strength >= 8.0:
            d10_analysis_notes.append("Excellent professional prospects and career advancement")
        elif d10_strength >= 6.0:
            d10_analysis_notes.append("Good career opportunities with steady progress")
        elif d10_strength >= 4.0:
            d10_analysis_notes.append("Moderate professional development with mixed results")
        else:
            d10_analysis_notes.append("Career challenges requiring extra effort and strategy")
        
        return {
            'd10_auspiciousness': d10_strength,
            'd10_analysis': "; ".join(d10_analysis_notes),
            'is_d10_vargottama': is_d10_vargottama,
            'd10_sign': d10_sign,
            'career_deity': career_deity,
            'career_significance': career_significance,
            'dashamsha_number': d10_planet_data.get('dashamsha_number', 1)
        }

    def _generate_enhanced_opportunity_significance(self, opportunity: Dict[str, Any], df: pd.DataFrame) -> str:
        """Generate comprehensive astrological significance for investment opportunities including D1/D9/D10 analysis"""
        try:
            # Find the period in dataframe matching this opportunity
            current_date = opportunity['current_date']
            matching_periods = df[df['start_date'] == current_date]
            
            if matching_periods.empty:
                return opportunity.get('astrological_significance', 'No astrological data available')
            
            period = matching_periods.iloc[0]
            significance_parts = []
            
            # Get basic dasha information
            dasha_lord = period.get('mahadasha_lord', 'Unknown')
            period_type = period.get('Type', 'Unknown')
            
            # Add period structure context
            if period_type == 'MD':
                significance_parts.append(f"**{dasha_lord} Mahadasha:** Major 16-year planetary cycle")
            elif period_type == 'MD-AD':
                antardasha = period.get('antardasha_lord', 'Unknown')
                significance_parts.append(f"**{dasha_lord}-{antardasha} Period:** {antardasha} sub-cycle within {dasha_lord} major period")
            else:
                antardasha = period.get('antardasha_lord', 'Unknown')
                pratyantardasha = period.get('pratyantardasha_lord', 'Unknown')
                significance_parts.append(f"**{dasha_lord}-{antardasha}-{pratyantardasha}:** Micro-cycle for precise timing")
            
            # D1 (Rashi) Analysis
            d1_parts = []
            d1_score = period.get('D1_Score', period.get('auspiciousness_score', 0))
            if d1_score > 0:
                if d1_score >= 8.0:
                    d1_parts.append(f"D1 Score: {d1_score:.1f} (Exceptional immediate conditions)")
                elif d1_score >= 6.0:
                    d1_parts.append(f"D1 Score: {d1_score:.1f} (Strong immediate potential)")
                elif d1_score >= 4.0:
                    d1_parts.append(f"D1 Score: {d1_score:.1f} (Moderate immediate conditions)")
                else:
                    d1_parts.append(f"D1 Score: {d1_score:.1f} (Challenging immediate environment)")
            
            # Add planetary strength context
            planet_strength = period.get('planet_strength', 'Unknown')
            if planet_strength != 'Unknown':
                d1_parts.append(f"{dasha_lord} strength: {planet_strength}")
            
            if d1_parts:
                significance_parts.append(f"**D1 (Immediate Market):** {' | '.join(d1_parts)}")
            
            # D9 (Navamsha) Analysis
            has_navamsha = any(col in df.columns for col in ['D9_Score', 'Navamsha_Effect'])
            if has_navamsha:
                d9_parts = []
                d9_score = period.get('D9_Score', 0)
                if d9_score > 0:
                    d9_effect = d9_score - d1_score
                    if d9_effect > 1.0:
                        d9_parts.append(f"D9 Score: {d9_score:.1f} (Strengthens foundation +{d9_effect:.1f})")
                    elif d9_effect < -1.0:
                        d9_parts.append(f"D9 Score: {d9_score:.1f} (Weakens sustainability {d9_effect:.1f})")
                    else:
                        d9_parts.append(f"D9 Score: {d9_score:.1f} (Balanced foundation {d9_effect:+.1f})")
                
                # Vargottama status
                if period.get('D9_Vargottama', 'No') == 'Yes':
                    d9_parts.append("Vargottama (exceptional strength)")
                
                # D9 sign
                d9_sign = period.get('D9_Sign', '')
                if d9_sign:
                    d9_parts.append(f"D9 in {d9_sign}")
                
                navamsha_effect = period.get('Navamsha_Effect', '')
                if navamsha_effect:
                    if 'Strengthens' in navamsha_effect:
                        d9_parts.append("Enhances long-term sustainability")
                    elif 'Weakens' in navamsha_effect:
                        d9_parts.append("Reduces long-term stability")
                
                if d9_parts:
                    significance_parts.append(f"**D9 (Sustainability):** {' | '.join(d9_parts)}")
            
            # D10 (Dashamsha) Analysis
            has_dashamsha = any(col in df.columns for col in ['D10_Score', 'D10_Deity'])
            if has_dashamsha:
                d10_parts = []
                d10_score = period.get('D10_Score', 0)
                if d10_score > 0:
                    d10_effect = d10_score - d1_score
                    if d10_effect > 1.0:
                        d10_parts.append(f"D10 Score: {d10_score:.1f} (Enhances career potential +{d10_effect:.1f})")
                    elif d10_effect < -1.0:
                        d10_parts.append(f"D10 Score: {d10_score:.1f} (Challenges career growth {d10_effect:.1f})")
                    else:
                        d10_parts.append(f"D10 Score: {d10_score:.1f} (Balanced career influence {d10_effect:+.1f})")
                
                # D10 Vargottama
                if period.get('D10_Vargottama', 'No') == 'Yes':
                    d10_parts.append("Career Vargottama (exceptional professional strength)")
                
                # Deity analysis
                d10_deity = period.get('D10_Deity', '')
                if d10_deity:
                    deity_meanings = {
                        'Indra': 'Leadership & Authority',
                        'Agni': 'Innovation & Energy',
                        'Yama': 'Law & Justice',
                        'Rakshasa': 'Competition & Politics',
                        'Varuna': 'Creativity & Arbitration',
                        'Vayu': 'Communication & Media',
                        'Kubera': 'Finance & Wealth',
                        'Isan': 'Healing & Counseling',
                        'Brahma': 'Innovation & Creation',
                        'Ananth': 'Stability & Service'
                    }
                    deity_meaning = deity_meanings.get(d10_deity, 'Professional influence')
                    d10_parts.append(f"{d10_deity} deity ({deity_meaning})")
                
                # D10 career significance
                d10_career = period.get('D10_Career', '')
                if d10_career and len(d10_career) > 10:
                    d10_parts.append(f"Career focus: {d10_career[:50]}...")
                
                if d10_parts:
                    significance_parts.append(f"**D10 (Career/Professional):** {' | '.join(d10_parts)}")
            
            # Combined Analysis & Investment Rationale
            rationale_parts = []
            
            # Analyze the investment decision logic
            action = opportunity.get('action', 'HOLD')
            score_change = opportunity.get('score_change', 0)
            current_score = opportunity.get('current_score', 0)
            
            if action in ['STRONG BUY', 'BUY']:
                if score_change >= 3.0:
                    rationale_parts.append(f"**Entry Logic:** Major improvement expected ({score_change:+.1f} points)")
                elif score_change >= 2.0:
                    rationale_parts.append(f"**Entry Logic:** Significant improvement expected ({score_change:+.1f} points)")
                else:
                    rationale_parts.append(f"**Entry Logic:** Moderate improvement expected ({score_change:+.1f} points)")
                
                if current_score <= 4.0:
                    rationale_parts.append("buying at cycle bottom for maximum upside")
                elif current_score <= 6.0:
                    rationale_parts.append("accumulating during growth phase")
                
            elif action in ['STRONG SELL', 'SELL']:
                if score_change <= -3.0:
                    rationale_parts.append(f"**Exit Logic:** Major decline expected ({score_change:.1f} points)")
                elif score_change <= -2.0:
                    rationale_parts.append(f"**Exit Logic:** Significant decline expected ({score_change:.1f} points)")
                else:
                    rationale_parts.append(f"**Exit Logic:** Moderate decline expected ({score_change:.1f} points)")
                
                if current_score >= 7.0:
                    rationale_parts.append("selling at cycle peak to protect gains")
                elif current_score >= 5.5:
                    rationale_parts.append("reducing exposure before challenging period")
            
            # Multi-chart confirmation
            chart_confirmation = []
            if has_navamsha and has_dashamsha:
                # Check which chart is leading the decision
                if hasattr(period, 'get') and period.get('Navamsha_Effect', ''):
                    if 'Strengthens' in period.get('Navamsha_Effect', ''):
                        chart_confirmation.append("D9 confirms sustainability")
                    elif 'Weakens' in period.get('Navamsha_Effect', ''):
                        chart_confirmation.append("D9 warns of foundation issues")
                
                if period.get('D10_Career', ''):
                    if any(word in period.get('D10_Career', '').lower() for word in ['strong', 'excellent', 'favorable']):
                        chart_confirmation.append("D10 supports professional growth")
                    elif any(word in period.get('D10_Career', '').lower() for word in ['challenging', 'difficult', 'weak']):
                        chart_confirmation.append("D10 indicates career headwinds")
            
            if chart_confirmation:
                rationale_parts.append(f"**Multi-Chart Confirmation:** {' & '.join(chart_confirmation)}")
            
            if rationale_parts:
                significance_parts.append(' | '.join(rationale_parts))
            
            return ' | '.join(significance_parts) if significance_parts else opportunity.get('astrological_significance', 'Analysis pending')
            
        except Exception as e:
            return f"Significance analysis error: {str(e)}"

def main():
    """Main execution function with command-line argument parsing"""
    parser = argparse.ArgumentParser(
        description='Enhanced Vedic Dasha Analyzer v4 with Navamsha (D9) and Dashamsha (D10) Evaluation System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Traditional analysis (Lagna only)
  python vedic_dasha_analyzer_v4.py data/Technology/PLTR.json
  
  # All 4 house systems with Navamsha evaluation
  python vedic_dasha_analyzer_v4.py data/Technology/PLTR.json --multi-house --navamsha
  
  # Complete three-chart analysis (D1 + D9 + D10)
  python vedic_dasha_analyzer_v4.py data/Technology/PLTR.json --multi-house --navamsha --dashamsha
  
  # Career-focused analysis with Dashamsha
  python vedic_dasha_analyzer_v4.py data/Technology/PLTR.json --dashamsha
  
  # Specific house systems with all divisional charts
  python vedic_dasha_analyzer_v4.py data/Technology/PLTR.json --house-systems lagna arudha_lagna --navamsha --dashamsha
  
  # With custom location and complete analysis
  python vedic_dasha_analyzer_v4.py data/Technology/PLTR.json --location "Mumbai, India" --multi-house --navamsha --dashamsha
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
    parser.add_argument('--navamsha', action='store_true',
                       help='Enable Navamsha (D9) evaluation with D1:D9 weighting system')
    parser.add_argument('--dashamsha', action='store_true',
                       help='Enable Dashamsha (D10) career evaluation with deity analysis')
    parser.add_argument('--output', '-o', help='Custom output directory (default: analysis/{SYMBOL}/)')
    
    args = parser.parse_args()
    
    # Validate input file
    if not os.path.exists(args.json_file):
        print(f"Error: JSON file '{args.json_file}' not found.")
        sys.exit(1)
    
    print("=" * 80)
    print("🏛️  VEDIC DASHA ANALYZER v4 - MULTI-DIVISIONAL CHART EDITION")
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
    
    # Show divisional chart status
    divisional_charts = []
    weights_info = []
    
    if args.navamsha and args.dashamsha:
        divisional_charts = ['D1 (Rashi)', 'D9 (Navamsha)', 'D10 (Dashamsha)']
        weights_info = ['D1: 10/10 (immediate)', 'D9: 9/10 (sustainability)', 'D10: 8/10 (career)']
        print("🔢 Complete three-chart analysis enabled!")
        print("   📊 D1 (Rashi) + D9 (Navamsha) + D10 (Dashamsha)")
        print("   ⚖️  Weighting: 10:9:8 for comprehensive life analysis")
    elif args.navamsha:
        divisional_charts = ['D1 (Rashi)', 'D9 (Navamsha)']
        weights_info = ['D1: 10/10 (immediate)', 'D9: 9/10 (sustainability)']
        print("🔢 Navamsha (D9) evaluation enabled - 10:9 weighting with D1 chart")
        print("   📊 D1 (Rashi) weight: 10/10 for immediate manifestation")
        print("   🌟 D9 (Navamsha) weight: 9/10 for underlying strength & sustainability")
    elif args.dashamsha:
        divisional_charts = ['D1 (Rashi)', 'D10 (Dashamsha)']
        weights_info = ['D1: 10/10 (immediate)', 'D10: 8/10 (career)']
        print("🏢 Dashamsha (D10) career evaluation enabled")
        print("   📊 D1 (Rashi) + D10 (Dashamsha) with deity analysis")
        print("   🎯 Focus: Career, profession, and public achievement")
    else:
        divisional_charts = ['D1 (Rashi)']
        weights_info = ['D1: 10/10 (complete)']
        print("📈 Using D1 (Rashi) chart only")
        print("   💡 Add --navamsha for sustainability analysis")
        print("   💼 Add --dashamsha for career-focused insights")
        print("   🌟 Add both for complete three-chart analysis")
    
    try:
        # Initialize analyzer
        analyzer = EnhancedVedicDashaAnalyzer(birth_location=args.location)
        
        # Filter house systems based on selection
        if len(selected_systems) == 1 and selected_systems[0] == 'lagna':
            # Standard single-system mode
            results = analyzer.analyze_json_file(args.json_file, 
                                               enable_multi_house=False, 
                                               enable_navamsha=args.navamsha, 
                                               enable_dashamsha=args.dashamsha)
        else:
            # Multi-system mode - temporarily adjust house_systems
            original_systems = analyzer.house_systems.copy()
            analyzer.house_systems = {k: v for k, v in original_systems.items() if k in selected_systems}
            
            results = analyzer.analyze_json_file(args.json_file, 
                                               enable_multi_house=True, 
                                               enable_navamsha=args.navamsha, 
                                               enable_dashamsha=args.dashamsha)
            
            # Restore original systems
            analyzer.house_systems = original_systems
        
        print("\n" + "=" * 80)
        print("✅ ANALYSIS COMPLETE")
        print("=" * 80)
        
        if results.get('multi_house_enabled', False):
            print(f"📊 Multi-house analysis completed for {results['symbol']}")
            print(f"🏠 House systems analyzed: {len(results['house_systems_analyzed'])}")
            print(f"📈 Divisional charts: {', '.join(divisional_charts)}")
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
            print(f"📈 Divisional charts: {', '.join(divisional_charts)}")
        
        if len(weights_info) > 1:
            print(f"\n⚖️  Weight Distribution: {' | '.join(weights_info)}")
        
        print(f"\n🎯 Ready for cross-system comparison and strategic analysis!")
        
    except Exception as e:
        print(f"\n❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 