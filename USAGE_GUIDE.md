#!/usr/bin/env python3
"""
Rallycross Driver Rankings - Usage Guide

This system generates driver rankings optimized for sparse head-to-head 
competition data in rallycross racing.
"""

## OVERVIEW

The ranking system uses normalized time differences, weighted averages, and
transitive comparison chains to rank drivers even when they rarely compete
directly against each other.

**Why this approach?**
- Rallycross drivers often never race the same class on the same day
- Traditional rating systems (Elo, etc.) fail on sparse data
- This system leverages transitive relationships to connect all drivers
- Real performance metrics (time differences) are more interpretable than abstract ratings

## QUICK START

```bash
# Generate all rankings (default)
python3 -m cli

# Specify runtime (seconds)
python3 -m cli --runtime 1000

# Filter to specific drivers
python3 -m cli --driver-file drivers.csv

# Apply inactivity decay
python3 -m cli --apply-decay

# Deeper transitive comparisons
python3 -m cli --depth 5
```

## COMMAND-LINE OPTIONS

```
--runtime SECONDS
    Base runtime for predictions (default: 60)
    Example: --runtime 1000
    
--depth LEVEL
    Transitive comparison depth (default: 3)
    Higher = more distant comparisons included
    Example: --depth 5

--apply-decay
    Apply inactivity decay to scores
    Reduces ranking for drivers inactive >365 days
    
--driver-file PATH
    Filter rankings to specific drivers (CSV format)
    Format:
      first_name,last_name,class
      Corey,Graffunder,MA
      Casey,Hamm,MA
```

## UNDERSTANDING THE OUTPUT

### predictions_60s.csv
Per-class predictions at specified runtime:

```
class  rank  driver_name        predicted_time  time_gap_per_60s  accuracy  activity  wins
US     1     Evan Williams      700.5           0.52              high      active    12
US     2     Gary Rhodes        702.1           0.38              medium    active    8
```

- **rank**: Position in class (1 = fastest)
- **predicted_time**: Estimated race time (seconds)
- **time_gap_per_60s**: Average advantage per 60-second race
- **accuracy**: low/medium/high (based on comparison count)
- **activity**: active/stale/inactive (days since last event)
- **wins**: Fastest times in this class

### cross_class_rankings.csv
Overall driver ranking across all classes:

```
driver_name         ranking  accuracy  activity  wins
Bob Martin          100      high      active    45
Andrew Hamilton     98       high      active    38
```

- **ranking**: 1-100 score (100 = fastest overall)
- **accuracy**: Confidence level
- **activity**: Recent competition status
- **wins**: Total fastest times across all classes

### cross_class_rankings_by_class.csv
Per-class rankings for each driver:

```
driver_name         class  ranking  accuracy  activity  wins
Bob Martin          MA     100      high      active    12
Bob Martin          MF     95       medium    active    8
```

### pairwise_comparisons_60s.csv
Raw pairwise data (for analysis):

```
date        event_name              class  driver1         driver2           raw_diff_sec
2024-05-18  2024 National Champ     US     Evan Williams   Ed Trudeau        -2.581
```

## HOW IT WORKS

### 1. Generate Pairwise Comparisons
All drivers in same event + class get compared:
- 4 drivers in same event = 6 pairwise rows (A-B, A-C, A-D, B-C, B-D, C-D)
- Times are normalized to 60-second baseline
- Each comparison includes date, event, drivers, time difference

### 2. Transitive Comparison Chains
Connect drivers who never directly raced:

```
A beat B (Event 1)
B beat C (Event 2)
=> A > C (inferred, depth 1)

A beat B, B beat C, C beat D (depth 2)
=> A > D (more distant, discounted)
```

Distance discount: Each hop beyond direct has reduced weight

### 3. Calculate Rankings
For each driver:
1. Collect all comparisons (direct + transitive)
2. Weight by recency (newer events count more)
3. Normalize by activity status
4. Average to get final ranking
5. Calculate accuracy based on comparison count

### 4. Per-Class and Overall Rankings
- **Per-class**: Rank within specific racing class
- **Overall**: Average ranking across all classes driver competes in

## EXAMPLES

### Example 1: Basic ranking
```bash
python3 -m cli
```
Generates rankings at 60-second baseline.

### Example 2: Custom runtime
```bash
python3 -m cli --runtime 1500
```
Calculates finishing positions at 1500-second event length.

### Example 3: Specific drivers
```bash
python3 -m cli --driver-file my_drivers.csv --runtime 500
```
Rankings for drivers in CSV at 500-second runtime.

### Example 4: Deep transitive
```bash
python3 -m cli --depth 5
```
Includes comparisons up to 5 degrees of separation.

### Example 5: With decay
```bash
python3 -m cli --apply-decay
```
Reduces scores for drivers inactive >1 year.

## INTERPRETING RANKINGS

### What does "time_gap_per_60s" mean?

If a driver has `time_gap_per_60s = 0.52`:
- In a 60-second race, they'd be ~0.52 seconds faster than the class average
- In a 300-second race (5 laps), they'd be ~2.6 seconds faster
- In a 1000-second race, they'd be ~8.7 seconds faster

This lets you predict their advantage at any race length.

### What does accuracy level mean?

- **High** (50+ comparisons): Well-established ranking, trust it
- **Medium** (20-49 comparisons): Reasonable ranking, some variance
- **Low** (<20 comparisons): Tentative ranking, may change with new events

### What does activity mean?

- **Active**: Last event ≤365 days ago
- **Stale**: Last event 366-730 days ago
- **Inactive**: Last event >730 days ago

Inactive drivers' rankings are historical—they may have improved or declined.

## CONFIGURATION

All constants are in `utils.py`:

```python
ACCURACY_THRESHOLD_LOW = 20          # Threshold for "low" accuracy
ACCURACY_THRESHOLD_MEDIUM = 40       # Threshold for "medium" accuracy
TRANSITIVE_WEIGHT_MULTIPLIER = 0.5   # Weight of transitive comparisons
TRANSITIVE_DISTANCE_DISCOUNT_BASE = 0.5  # Discount per hop
RECENCY_HALF_LIFE_DAYS = 180.0       # Half-life of events (days)
INACTIVITY_DECAY_HALF_LIFE_DAYS = 365.0  # Decay for inactive drivers
ACTIVITY_ACTIVE_DAYS = 365           # Days threshold for "active"
ACTIVITY_STALE_DAYS = 730            # Days threshold for "stale"
```

To customize: Edit `utils.py` and re-run ranking generation.

## WHY THIS SYSTEM?

See `WHY_THIS_ALGORITHM.md` for a detailed explanation of why this approach
works well for rallycross.

TL;DR:
- ✓ Designed for sparse head-to-head data
- ✓ Leverages transitive comparisons
- ✓ Uses real performance metrics
- ✓ Provides confidence/accuracy scoring
- ✓ Tracks driver activity status
- ✓ Scales efficiently

## TROUBLESHOOTING

**Q: Why are some drivers missing from top rankings?**
A: They may have low comparison counts ("low" accuracy). Try running with
   `--depth 5` to include more transitive comparisons.

**Q: Why does the ranking change between runs?**
A: Time-based weighting changes daily. Re-run ranking regularly for updates.

**Q: Can I see the pairwise comparisons?**
A: Yes, check `output/pairwise_comparisons_60s.csv` for raw comparison data.

**Q: How do I update rankings with new events?**
A: Add event data to `results/` directory and re-run `python3 -m cli`.

## NEXT STEPS

1. Generate rankings: `python3 -m cli`
2. Check output files in `output/` directory
3. Review rankings and accuracy levels
4. Customize config (if needed) in `utils.py`
5. Re-run with different options as needed

See `WHY_THIS_ALGORITHM.md` for algorithmic details.
