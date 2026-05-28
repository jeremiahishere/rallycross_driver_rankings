"""Utility functions for rallycross driver rankings."""

import math
from datetime import datetime

# Constants
ACCURACY_THRESHOLD_LOW = 20
ACCURACY_THRESHOLD_MEDIUM = 40
TRANSITIVE_WEIGHT_MULTIPLIER = 0.5
TRANSITIVE_DISTANCE_DISCOUNT_BASE = 0.5
RECENCY_HALF_LIFE_DAYS = 180.0
INACTIVITY_DECAY_HALF_LIFE_DAYS = 365.0
ACTIVITY_ACTIVE_DAYS = 365    # Active if last event within 1 year (365 days)
ACTIVITY_STALE_DAYS = 730     # Stale if 1-2 years inactive (365-730 days)
# Inactive if > 2 years (>730 days)


def get_accuracy_level(comparison_count):
    """Return accuracy level based on comparison count."""
    if comparison_count < ACCURACY_THRESHOLD_LOW:
        return "low"
    elif comparison_count < ACCURACY_THRESHOLD_MEDIUM:
        return "medium"
    else:
        return "high"


def get_inactivity_decay_multiplier(driver_records, half_life_days=INACTIVITY_DECAY_HALF_LIFE_DAYS):
    """Calculate decay multiplier based on days since last event.
    
    Uses exponential decay: multiplier = e^(-days_inactive / half_life)
    After half_life days, multiplier = 0.368 (37% of original)
    
    Args:
        driver_records: List of driver records with 'date' field
        half_life_days: Days for multiplier to reach 0.368 (default: 365)
        
    Returns:
        tuple: (multiplier, days_inactive)
    """
    if not driver_records:
        return 0.0, 0
    
    try:
        dates = [datetime.strptime(r.get('date', ''), '%Y-%m-%d') for r in driver_records]
        last_event_date = max(dates)
    except (ValueError, TypeError):
        return 0.0, 0
    
    days_inactive = (datetime.now() - last_event_date).days
    
    if days_inactive < 0:
        return 1.0, 0
    
    multiplier = math.exp(-days_inactive / float(half_life_days))
    return multiplier, days_inactive


def get_activity_level(days_inactive):
    """Return activity level based on days inactive.
    
    - "active": last event within 1 year (0-365 days)
    - "stale": last event 1-2 years ago (366-730 days)
    - "inactive": last event > 2 years ago (>730 days)
    
    Args:
        days_inactive: Number of days since last event
        
    Returns:
        str: "active", "stale", or "inactive"
    """
    if days_inactive <= ACTIVITY_ACTIVE_DAYS:
        return "active"
    elif days_inactive <= ACTIVITY_STALE_DAYS:
        return "stale"
    else:
        return "inactive"
