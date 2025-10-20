from typing import Dict
import json
import os

class ImpactService:
    def __init__(self):
        self.impact_factors = self._load_impact_factors()
        self.impact_thresholds = {
            'very_high': 10.0,  # Nature, Science, etc.
            'high': 5.0,        # Top field journals
            'medium': 2.0,      # Good specialized journals
            'low': 0.0          # Other peer-reviewed
        }

    def _load_impact_factors(self) -> Dict[str, float]:
        """Load journal impact factors from database/file"""
        try:
            with open('src/data/journal_impacts.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def get_impact_factor(self, journal: str) -> float:
        """Get impact factor for a journal"""
        # Normalize journal name
        journal = journal.lower().strip()
        return self.impact_factors.get(journal, 0.0)

    def get_impact_category(self, impact_factor: float) -> str:
        """Categorize impact factor"""
        if impact_factor >= self.impact_thresholds['very_high']:
            return 'very_high'
        elif impact_factor >= self.impact_thresholds['high']:
            return 'high'
        elif impact_factor >= self.impact_thresholds['medium']:
            return 'medium'
        else:
            return 'low' 