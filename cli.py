"""Command-line interface for rallycross driver rankings."""

import argparse
import csv
from pathlib import Path


def create_parser():
    """Create and return the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        description="Rallycross Driver Rankings - Sparse Competition Optimization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
OVERVIEW:

This ranking system is optimized for rallycross data where drivers often never
directly compete in the same class on the same event. The algorithm uses:
  • Normalized time differences per 60-second baseline
  • Weighted averages with recency factors
  • Transitive comparison chains (default depth 3)
  • Activity status tracking

EXAMPLES:

1. Generate all rankings (default):
    python -m cli
    Output: predictions_60s.csv, cross_class_rankings.csv, etc.

2. Generate a file of all pairwise comparisons:
    python -m cli
    Output: output/pairwise_comparisons_60s.csv
    
3. Generate rankings at 1000-second runtime:
    python -m cli --runtime 1000
    Output: predictions_1000s.csv, cross_class_rankings_1000s.csv

4. Generate finishing order for specific drivers:
    python -m cli --driver-file drivers.csv --runtime 500
    Output: Ranking for drivers in drivers.csv
    
    Create drivers.csv with format:
      first_name,last_name,class
      Corey,Graffunder,MA
      Casey,Hamm,MA

5. Use deeper transitive comparisons:
    python -m cli --depth 5
    (allows comparing drivers separated by up to 5 degrees)

6. Apply inactivity decay:
    python -m cli --apply-decay
    (reduces scores for inactive drivers)

ADVANCED OPTIONS:

Use --depth for transitive comparisons:
    python -m cli --depth 3
    
    This allows comparing drivers who haven't directly raced by finding paths
    through common competitors (e.g., A beat B, B beat C, so A > C transitively).
    Default depth is 3 (transitive comparisons up to 3 levels deep).

Combine multiple flags:
    python -m cli --runtime 1500 --depth 2 --driver-file lineup.csv --apply-decay
    
    This generates finishing order for drivers in lineup.csv with 1500s runtime,
    transitive depth 2, and inactivity decay applied.

OUTPUT FILES:

All output files are written to the output/ directory and include the runtime
in their filename. The output/ directory is automatically created and cleaned
before each run.

OUTPUT COLUMNS:

predictions_Xs.csv:
- rank: Position within the class (1 = fastest)
- predicted_time: Predicted race time in seconds at the specified runtime
- time_gap_per_60s: Average time gap per 60 seconds compared to class fastest
- accuracy: Confidence level (low/medium/high) based on comparison count
- activity: Activity level (active/stale/inactive) based on last event date
- wins: Number of fastest times (wins) in this class

cross_class_rankings.csv:
- ranking: Overall score from 1-100 (100 = fastest)
- accuracy: Confidence level (low/medium/high) based on comparison count
- activity: Activity level (active/stale/inactive) based on last event date
- wins: Total wins across all classes

cross_class_rankings_by_class.csv:
- class: Racing class
- ranking: Score within that class from 1-100 (100 = fastest)
- accuracy: Confidence level (low/medium/high) based on comparison count
- activity: Activity level (active/stale/inactive) based on last event date
- wins: Number of wins in this class

pairwise_comparisons_Xs.csv:
- date: Event date
- event_name: Event name
- class: Racing class
- driver1, driver2: Drivers compared
- raw_diff_sec: Time difference (seconds, positive = driver1 faster)
- normalized_diff_per_60s: Time difference normalized to 60-second baseline
- driver1_time, driver2_time: Actual race times

WHY THIS ALGORITHM:

Rallycross rankings require handling sparse head-to-head competition data.
Many drivers never directly race in the same class on the same day. This system:

✓ Leverages transitive comparisons to connect all drivers
✓ Uses actual performance metrics (time differences)
✓ Weights recent events more heavily
✓ Provides accuracy scoring based on comparison frequency
✓ Tracks driver activity status
✓ Scales to large datasets with many drivers and events
""",
    )
    parser.add_argument(
        "--runtime", type=float, default=60.0,
        help="Base runtime in seconds for predictions (default: 60.0)"
    )
    parser.add_argument(
        "--depth", type=int, default=3,
        help="Transitive comparison depth (default: 3)"
    )
    parser.add_argument(
        "--driver-file", type=str, default=None,
        help="Path to CSV file with drivers (first_name, last_name, class columns)"
    )
    parser.add_argument(
        "--apply-decay", action="store_true",
        help="Apply inactivity decay multiplier to ranking scores"
    )
    # ---------------------------------------------------------------------------------
    # Adding support for alternative ranking algorithms
    #
    # To add a new algorithm (e.g. TrueSkill, Bradley-Terry):
    #
    # 1. Create a new module (e.g. trueskill_ranking.py) that implements a ranking
    #    system class with at minimum:
    #      - __init__(self, drivers) — accepts a driver collection
    #      - load_pairwise_comparisons(self, filepath) — loads pairwise CSV data
    #      - calculate_ratings(self) — runs the algorithm
    #      - export_ratings_by_class(self, output_dir) — writes per-class CSVs
    #      - export_overall_rankings(self, output_dir) — writes overall CSV
    #
    # 2. Add a CLI argument here, e.g.:
    #      parser.add_argument("--algorithm", choices=["default", "trueskill"], ...)
    #
    # 3. In main(), dispatch to the appropriate ranking system based on the argument.
    #
    # 4. Add tests in tests/ for the new algorithm module.
    #
    # Note: The primary transitive comparison algorithm is purpose-built for sparse
    # rallycross data and should remain the default.  Alternative algorithms are
    # useful for comparison and research.
    # ---------------------------------------------------------------------------------

    return parser


def load_driver_list(filepath):
    """Load a list of drivers from a CSV file.
    
    Expected format:
        first_name,last_name,class
        Corey,Graffunder,MA
        Casey,Hamm,MA
    """
    drivers = []
    try:
        with open(filepath, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                drivers.append({
                    'first_name': row['first_name'],
                    'last_name': row['last_name'],
                    'class': row['class']
                })
    except FileNotFoundError:
        print(f"Error: Driver file not found: {filepath}")
        return []
    except KeyError:
        print(f"Error: Driver file must have columns: first_name, last_name, class")
        return []
    
    return drivers


def main():
    """Main entry point for the CLI."""
    from runner import Runner
    
    parser = create_parser()
    args = parser.parse_args()

    # Run the primary ranking system (optimized for sparse rallycross data)
    print("Running primary ranking system (optimized for sparse rallycross data)...")
    runner = Runner(runtime=args.runtime, depth=args.depth, apply_decay=args.apply_decay)
    runner.run()
    runner.run_predictions()

    if args.driver_file:
        drivers = load_driver_list(args.driver_file)
        if drivers:
            finishing_order = runner.generate_finishing_order(drivers, args.runtime)
            runner.export_finishing_order(finishing_order, args.runtime)


if __name__ == "__main__":
    main()
