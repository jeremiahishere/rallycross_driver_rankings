import argparse
import csv
import glob
import math
import os
from collections import defaultdict
from datetime import datetime

# Constants
ACCURACY_THRESHOLD_LOW = 10
ACCURACY_THRESHOLD_MEDIUM = 20
TRANSITIVE_WEIGHT_MULTIPLIER = 0.5
TRANSITIVE_DISTANCE_DISCOUNT_BASE = 0.5
RECENCY_HALF_LIFE_DAYS = 180.0


def get_accuracy_level(comparison_count):
    """Return accuracy level based on comparison count."""
    if comparison_count < ACCURACY_THRESHOLD_LOW:
        return "low"
    elif comparison_count < ACCURACY_THRESHOLD_MEDIUM:
        return "medium"
    else:
        return "high"


class DriverCollection:
    def __init__(self):
        self.drivers = {}

    def add(self, first_name, last_name, car_class):
        key = self.driver_id(first_name, last_name, car_class)
        if key not in self.drivers:
            driver = Driver(first_name, last_name, car_class)
            self.drivers[key] = driver
        return self.drivers[key]

    def get(self, first_name, last_name, car_class):
        """Get a specific driver by name and class."""
        return self.drivers[self.driver_id(first_name, last_name, car_class)]
    
    def get_by_name_and_class(self, driver_name, car_class):
        """Get a driver by their full name and class.
        
        Args:
            driver_name: Full name string (e.g., "John Doe", "Diego De")
            car_class: Racing class
            
        Returns:
            Driver object or None if not found
        """
        for driver in self.drivers.values():
            if driver.name() == driver_name and driver.car_class == car_class:
                return driver
        return None
    
    def get_by_name(self, first_name, last_name):
        """Get all drivers with given first and last name (across all classes)."""
        return [d for d in self.drivers.values() 
                if d.first_name == first_name and d.last_name == last_name]
    
    def get_by_class(self, car_class):
        """Get all drivers in a given class."""
        return [d for d in self.drivers.values() if d.car_class == car_class]
    
    def get_all_classes(self):
        """Get sorted list of all classes represented."""
        return sorted(set(d.car_class for d in self.drivers.values()))

    def driver_objs(self):
        output = []
        for key, value in self.drivers.items():
            output.append(value)
        return output

    def driver_id(self, first_name, last_name, car_class):
        return f"{first_name}|{last_name}|{car_class}"

    def __str__(self):
        high = -1000
        low = 1000
        for key, driver in self.drivers.items():
            val = driver.avg_time_difference()
            if val > high:
                high = val
            if val < low:
                low = val

        output = "first_name,last_name,car_class,event_count,avg_time_difference,ranking\n"
        for key, driver in self.drivers.items():
            output += f"{driver.to_csv_with_normalization(high, low)}\n"

        return output


class Driver:
    def __init__(self, first_name, last_name, car_class):
        self.first_name = first_name
        self.last_name = last_name
        self.car_class = car_class

        self.pairwise_total = 0
        self.pairwise_wins = 0
        self.pairwise_losses = 0

        self.pairwise_time_total = 0.0
        self.pairwise_times = {}

        # results that match this driver (after being populated)
        self.driver_records = []

    def name(self):
        return f"{self.first_name} {self.last_name}"

    def avg_time_difference(self):
        if self.pairwise_time_total == 0.0:
            return 0.0
        else:
            return self.pairwise_time_total / self.pairwise_total

    def event_count(self):
        return len(self.driver_records)

    def pairwise_stats(self):
        output = ""
        for key, value in self.pairwise_times.items():
            output += f"{key}: {value}\n"
        return output

    def to_csv_with_normalization(self, high, low):
        ranking = math.ceil(100 - (((self.avg_time_difference() - low) / (high - low)) * 100))
        output = ",".join([
            self.first_name,
            self.last_name,
            self.car_class,
            str(self.event_count()),
            "{:.3f}".format(self.avg_time_difference()),
            str(ranking),
        ])
        return output

    def __str__(self):
        output = ",".join([
            self.first_name,
            self.last_name,
            self.car_class,
            str(self.event_count()),
            "{:.3f}".format(self.avg_time_difference()),
        ])
        return output

    def find_driver_records(self, records):
        for row in records:
            if row['first_name'] == self.first_name and row['last_name'] == self.last_name and row['class'] == self.car_class:
                self.driver_records.append(row)

    def find_pairwise_competitors(self, records):
        self.find_driver_records(records)

        # find the other drivers in the same event/class
        for driver_record in self.driver_records:
            for row in records:
                if driver_record['date'] == row['date'] and driver_record['event_name'] == row['event_name'] and driver_record['class'] == row['class'] and driver_record['car_number'] != row['car_number']:
                    pairwise_name = f"{self.name()} -> {row['first_name']} {row['last_name']}"
                    # new pairing
                    if pairwise_name not in self.pairwise_times:
                        self.pairwise_times[pairwise_name] = 0
                    time_difference = float(driver_record['total']) - float(row['total'])
                    self.pairwise_times[pairwise_name] += time_difference
                    self.pairwise_time_total += time_difference
                    self.pairwise_total += 1
                    if time_difference > 0:
                        self.pairwise_losses += 1
                    else:
                         self.pairwise_wins += 1


class DriverPair:
    """Stores information about a comparison between two drivers."""
    
    def __init__(self, driver1, driver2, date, event_name, car_class, 
                 driver1_time, driver2_time):
        """
        Args:
            driver1: Driver object (the faster driver, or first in comparison)
            driver2: Driver object (the slower driver, or second in comparison)
            date: Date of the event (YYYY-MM-DD format)
            event_name: Name of the event
            car_class: Class in which they competed
            driver1_time: driver1's total race time
            driver2_time: driver2's total race time
        """
        self.driver1 = driver1
        self.driver2 = driver2
        self.date = date
        self.event_name = event_name
        self.car_class = car_class
        self.driver1_time = driver1_time
        self.driver2_time = driver2_time
        
        # Calculate differences
        self.raw_diff = driver1_time - driver2_time
        # Normalize to per-60-second rate
        baseline = (driver1_time + driver2_time) / 2.0
        if baseline == 0:
            self.normalized_diff_per_60s = 0.0
        else:
            self.normalized_diff_per_60s = (self.raw_diff / baseline) * 60.0
    
    def get_driver1_name(self):
        """Get first driver's name."""
        return self.driver1.name()
    
    def get_driver2_name(self):
        """Get second driver's name."""
        return self.driver2.name()
    
    def to_dict(self):
        """Convert to dictionary for CSV export."""
        return {
            'date': self.date,
            'event_name': self.event_name,
            'class': self.car_class,
            'driver1': self.get_driver1_name(),
            'driver2': self.get_driver2_name(),
            'normalized_diff_per_60s': self.normalized_diff_per_60s,
            'raw_diff_sec': self.raw_diff,
            'driver1_time': self.driver1_time,
            'driver2_time': self.driver2_time,
        }


class Runner:
    def __init__(self, runtime=60.0, depth=1):
        self.records = []
        self.drivers = DriverCollection()
        self.pairwise_comparisons = []
        self.runtime = runtime
        self.depth = depth
        self.comparison_count = 0  # Track comparisons for progress reporting

    def setup(self):
        # Create output directory and clean it
        output_dir = "./output"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Remove all CSV files from output directory
        for csv_file in glob.glob(os.path.join(output_dir, "*.csv")):
            os.remove(csv_file)
        
        files = glob.glob("./results/*.csv")
        for file in files:
            with open(file, mode='r', newline='') as file:
                csv_reader = csv.DictReader(file)
                for row in csv_reader:
                    self.records.append(row)
                    self.drivers.add(row['first_name'], row['last_name'], row['class'])

    def run(self):
        self.setup()

        for driver in self.drivers.driver_objs():
            driver.find_pairwise_competitors(self.records)

        self.build_pairwise_comparisons()
        self.export_pairwise_comparisons()

        rankings_by_class = self.build_cross_class_rankings_by_class()
        self.export_cross_class_rankings_by_class(rankings_by_class)
        self.print_cross_class_rankings_by_class(rankings_by_class)

        rankings = self.build_cross_class_rankings()
        self.export_cross_class_rankings(rankings)
        self.print_cross_class_rankings(rankings)

    def drivers_name(self, row):
        return f"{row['first_name']} {row['last_name']}"

    def build_pairwise_comparisons(self):
        """Build normalized pairwise comparison records from raw results."""
        self.pairwise_comparisons = []
        seen = set()

        for driver in self.drivers.driver_objs():
            for driver_record in driver.driver_records:
                for row in self.records:
                    if (driver_record['date'] == row['date']
                            and driver_record['event_name'] == row['event_name']
                            and driver_record['class'] == row['class']
                            and driver_record['car_number'] != row['car_number']):
                        driver1_name = driver.name()
                        driver2_name = f"{row['first_name']} {row['last_name']}"
                        pair_key = (driver_record['date'], driver_record['event_name'],
                                    driver_record['class'], driver1_name, driver2_name)
                        if pair_key in seen:
                            continue
                        seen.add(pair_key)

                        # Get or create the second driver object
                        driver2 = self.drivers.add(row['first_name'], row['last_name'], row['class'])
                        
                        # Create DriverPair object
                        pair = DriverPair(
                            driver1=driver,
                            driver2=driver2,
                            date=driver_record['date'],
                            event_name=driver_record['event_name'],
                            car_class=driver_record['class'],
                            driver1_time=float(driver_record['total']),
                            driver2_time=float(row['total'])
                        )
                        
                        self.pairwise_comparisons.append(pair)

    def export_pairwise_comparisons(self):
        """Export pairwise comparisons to CSV."""
        filename = f"output/pairwise_comparisons_{int(self.runtime)}s.csv"
        with open(filename, "w", newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'date', 'event_name', 'class', 'driver1', 'driver2',
                'normalized_diff_per_60s', 'raw_diff_sec',
                'driver1_time', 'driver2_time'
            ])
            for pair in self.pairwise_comparisons:
                comp = pair.to_dict()
                writer.writerow([
                    comp['date'],
                    comp['event_name'],
                    comp['class'],
                    comp['driver1'],
                    comp['driver2'],
                    "{:.3f}".format(comp['normalized_diff_per_60s']),
                    "{:.3f}".format(comp['raw_diff_sec']),
                    "{:.3f}".format(comp['driver1_time']),
                    "{:.3f}".format(comp['driver2_time']),
                ])
        print(f"Wrote {filename}")

    def _recency_weight(self, date_str):
        """Calculate recency weight with exponential decay."""
        event_date = datetime.strptime(date_str, "%Y-%m-%d")
        days_ago = (datetime.now() - event_date).days
        return math.exp(-days_ago / RECENCY_HALF_LIFE_DAYS)

    def _build_class_graph(self, car_class):
        """Build a weighted directed graph for a single class.

        Returns:
            drivers_in_class: list of driver names
            edges: dict mapping (driver1, driver2) to list of
                   (normalized_diff, weight) tuples
        """
        drivers_in_class = set()
        edges = defaultdict(list)

        for pair in self.pairwise_comparisons:
            if pair.car_class != car_class:
                continue
            d1 = pair.get_driver1_name()
            d2 = pair.get_driver2_name()
            drivers_in_class.add(d1)
            drivers_in_class.add(d2)
            weight = self._recency_weight(pair.date)
            edges[(d1, d2)].append((pair.normalized_diff_per_60s, weight))

        return list(drivers_in_class), edges

    def _weighted_avg_diff(self, edges, d1, d2):
        """Return (weighted_avg_diff, total_weight, count) for d1 vs d2."""
        comparisons = edges.get((d1, d2), [])
        if not comparisons:
            return None, 0, 0
        total_w = sum(w for _, w in comparisons)
        if total_w == 0:
            return None, 0, 0
        avg = sum(diff * w for diff, w in comparisons) / total_w
        return avg, total_w, len(comparisons)

    def _transitive_diff(self, edges, drivers, d1, d2, depth):
        """Find transitive time difference through intermediate drivers."""
        if depth <= 0:
            return None, 0, 0

        results = []
        for mid in drivers:
            if mid == d1 or mid == d2:
                continue
            diff1, w1, c1 = self._weighted_avg_diff(edges, d1, mid)
            if diff1 is None:
                continue
            diff2, w2, c2 = self._weighted_avg_diff(edges, mid, d2)
            if diff2 is None:
                # try deeper transitive
                if depth > 1:
                    diff2, w2, c2 = self._transitive_diff(
                        edges, drivers, mid, d2, depth - 1
                    )
                if diff2 is None:
                    continue
            combined_diff = diff1 + diff2
            combined_weight = min(w1, w2) * TRANSITIVE_WEIGHT_MULTIPLIER
            combined_count = c1 + c2
            results.append((combined_diff, combined_weight, combined_count))

        if not results:
            return None, 0, 0

        total_w = sum(w for _, w, _ in results)
        if total_w == 0:
            return None, 0, 0
        avg = sum(d * w for d, w, _ in results) / total_w
        total_count = sum(c for _, _, c in results)
        return avg, total_w, total_count

    def _rank_class(self, car_class):
        """Rank all drivers within a class.

        Returns list of dicts with keys:
            driver_name, class, time_gap_per_60s, comparison_count, weight
        sorted by time_gap ascending (fastest first).
        """
        drivers, edges = self._build_class_graph(car_class)
        if not drivers:
            return []

        # Build full diff matrix using direct + transitive comparisons
        driver_gaps = {}
        for d in drivers:
            gaps = []
            total_comparisons = 0
            for other in drivers:
                if other == d:
                    continue
                diff, w, c = self._weighted_avg_diff(edges, d, other)
                if diff is None and self.depth > 0:
                    diff, w, c = self._transitive_diff(
                        edges, drivers, d, other, self.depth
                    )
                    if diff is not None:
                        w *= TRANSITIVE_DISTANCE_DISCOUNT_BASE
                if diff is not None:
                    gaps.append((diff, w))
                    total_comparisons += c
                
                # Track progress: print every 1000 comparisons
                self.comparison_count += 1
                if self.comparison_count % 1000 == 0:
                    print(f"Progress: {self.comparison_count} comparisons completed", flush=True)

            if gaps:
                total_w = sum(w for _, w in gaps)
                if total_w > 0:
                    avg_gap = sum(d * w for d, w in gaps) / total_w
                else:
                    avg_gap = sum(d for d, _ in gaps) / len(gaps)
                driver_gaps[d] = (avg_gap, total_comparisons, total_w)
            else:
                driver_gaps[d] = (0.0, 0, 0.0)

        ranked = sorted(driver_gaps.items(), key=lambda x: x[1][0])

        # Normalize so fastest driver has gap = 0
        if ranked:
            best_gap = ranked[0][1][0]
        else:
            best_gap = 0.0

        results = []
        for driver_name, (gap, count, weight) in ranked:
            results.append({
                'driver_name': driver_name,
                'class': car_class,
                'time_gap_per_60s': gap - best_gap,
                'comparison_count': count,
                'weight': weight,
            })

        return results

    def build_cross_class_rankings_by_class(self):
        """Build rankings within each class."""
        classes = self.drivers.get_all_classes()
        all_rankings = []
        for car_class in classes:
            ranked = self._rank_class(car_class)
            if not ranked:
                continue
            high = max(r['time_gap_per_60s'] for r in ranked) if len(ranked) > 1 else 1.0
            if high == 0:
                high = 1.0
            for r in ranked:
                score = math.ceil(100 - ((r['time_gap_per_60s'] / high) * 100))
                score = max(1, min(100, score))
                # Get driver object to access event count
                driver_obj = self.drivers.get_by_name_and_class(r['driver_name'], r['class'])
                events = driver_obj.event_count() if driver_obj else 0
                all_rankings.append({
                    'driver_name': r['driver_name'],
                    'class': r['class'],
                    'ranking': score,
                    'accuracy': r['comparison_count'],
                    'events': events,
                })
        return all_rankings

    def build_cross_class_rankings(self):
        """Build overall cross-class rankings."""
        by_class = self.build_cross_class_rankings_by_class()
        # Aggregate: average ranking per driver across classes
        driver_scores = defaultdict(list)
        driver_accuracy = defaultdict(int)
        driver_events = defaultdict(int)
        for r in by_class:
            driver_scores[r['driver_name']].append(r['ranking'])
            driver_accuracy[r['driver_name']] = max(
                driver_accuracy[r['driver_name']], r['accuracy']
            )
            driver_events[r['driver_name']] = max(
                driver_events[r['driver_name']], r['events']
            )

        rankings = []
        for name, scores in driver_scores.items():
            avg_score = sum(scores) / len(scores)
            rankings.append({
                'driver_name': name,
                'ranking': round(avg_score),
                'accuracy': driver_accuracy[name],
                'events': driver_events[name],
            })

        rankings.sort(key=lambda x: x['ranking'], reverse=True)
        return rankings

    def export_cross_class_rankings(self, rankings):
        """Export cross-class rankings to CSV without group column."""
        filename = f"output/cross_class_rankings_{int(self.runtime)}s.csv"
        with open(filename, "w", newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['driver_name', 'ranking', 'accuracy', 'events'])
            for r in rankings:
                writer.writerow([
                    r['driver_name'],
                    r['ranking'],
                    get_accuracy_level(r['accuracy']),
                    r['events'],
                ])
        print(f"Wrote {filename}")

    def export_cross_class_rankings_by_class(self, rankings):
        """Export cross-class rankings by class to CSV without group column."""
        filename = f"output/cross_class_rankings_by_class_{int(self.runtime)}s.csv"
        with open(filename, "w", newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['driver_name', 'class', 'ranking', 'accuracy', 'events'])
            for r in rankings:
                writer.writerow([
                    r['driver_name'],
                    r['class'],
                    r['ranking'],
                    get_accuracy_level(r['accuracy']),
                    r['events'],
                ])
        print(f"Wrote {filename}")

    def print_cross_class_rankings(self, rankings):
        """Print cross-class rankings with accuracy as text levels."""
        print("\n=== Cross-Class Rankings ===")
        print(f"{'Rank':<6}{'Driver':<30}{'Score':<8}{'Accuracy':<10}{'Events':<8}")
        print("-" * 62)
        for i, r in enumerate(rankings, 1):
            level = get_accuracy_level(r['accuracy'])
            print(f"{i:<6}{r['driver_name']:<30}{r['ranking']:<8}{level:<10}{r['events']:<8}")

    def print_cross_class_rankings_by_class(self, rankings):
        """Print cross-class rankings by class sorted by ranking."""
        # Sort by ranking descending (highest ranking first)
        sorted_rankings = sorted(rankings, key=lambda x: x['ranking'], reverse=True)
        print("\n=== Cross-Class Rankings by Class ===")
        print(f"{'Driver':<30}{'Class':<8}{'Ranking':<10}{'Accuracy':<10}{'Events':<8}")
        print("-" * 66)
        for r in sorted_rankings:
            level = get_accuracy_level(r['accuracy'])
            print(f"{r['driver_name']:<30}{r['class']:<8}{r['ranking']:<10}{level:<10}{r['events']:<8}")

    def generate_finishing_order(self, drivers, runtime):
        """Generate expected finishing order for a list of drivers at a given runtime.

        Args:
            drivers: list of dicts with 'first_name', 'last_name', 'class' keys
            runtime: base runtime in seconds for the fastest driver

        Returns:
            list of dicts with driver info and predicted times, sorted fastest first
        """
        finishing_order = []

        for driver_info in drivers:
            car_class = driver_info['class']
            driver_name = f"{driver_info['first_name']} {driver_info['last_name']}"

            ranked = self._rank_class(car_class)
            gap = 0.0
            comparison_count = 0
            events = 0
            found = False
            for r in ranked:
                if r['driver_name'] == driver_name:
                    gap = r['time_gap_per_60s']
                    comparison_count = r['comparison_count']
                    found = True
                    # Get driver object to access event count
                    driver_obj = self.drivers.get_by_name_and_class(driver_name, car_class)
                    events = driver_obj.event_count() if driver_obj else 0
                    break

            predicted_time = runtime + (gap * runtime / 60.0)
            finishing_order.append({
                'class': car_class,
                'driver_name': driver_name,
                'predicted_time': predicted_time,
                'time_gap_per_60s': gap,
                'comparison_count': comparison_count,
                'events': events,
            })

        finishing_order.sort(key=lambda x: x['predicted_time'])

        for i, entry in enumerate(finishing_order, 1):
            entry['rank'] = i

        return finishing_order

    def export_finishing_order(self, finishing_order, runtime):
        """Export finishing order to CSV."""
        filename = f"output/predictions_{int(runtime)}s.csv"
        with open(filename, "w", newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'class', 'rank', 'driver_name', 'predicted_time',
                'time_gap_per_60s', 'accuracy', 'events'
            ])
            for entry in finishing_order:
                writer.writerow([
                    entry['class'],
                    entry['rank'],
                    entry['driver_name'],
                    "{:.3f}".format(entry['predicted_time']),
                    "{:.3f}".format(entry['time_gap_per_60s']),
                    get_accuracy_level(entry['comparison_count']),
                    entry['events'],
                ])
        print(f"Wrote {filename}")

    def print_finishing_order(self, finishing_order, runtime):
        """Print formatted finishing order."""
        print(f"\n=== Predicted Finishing Order (runtime={int(runtime)}s) ===")
        print(f"{'Rank':<6}{'Class':<8}{'Driver':<30}{'Time':<12}{'Gap/60s':<10}{'Accuracy':<10}{'Events':<8}")
        print("-" * 84)
        for entry in finishing_order:
            level = get_accuracy_level(entry['comparison_count'])
            print(
                f"{entry['rank']:<6}"
                f"{entry['class']:<8}"
                f"{entry['driver_name']:<30}"
                f"{entry['predicted_time']:<12.3f}"
                f"{entry['time_gap_per_60s']:<10.3f}"
                f"{level:<10}"
                f"{entry['events']:<8}"
            )

    def run_predictions(self):
        """Generate predictions for all classes at the configured runtime."""
        classes = self.drivers.get_all_classes()
        all_predictions = []
        for car_class in classes:
            ranked = self._rank_class(car_class)
            if not ranked:
                continue
            for i, r in enumerate(ranked, 1):
                predicted_time = self.runtime + (r['time_gap_per_60s'] * self.runtime / 60.0)
                # Get driver object to access event count
                driver_obj = self.drivers.get_by_name_and_class(r['driver_name'], car_class)
                events = driver_obj.event_count() if driver_obj else 0
                all_predictions.append({
                    'class': car_class,
                    'rank': i,
                    'driver_name': r['driver_name'],
                    'predicted_time': predicted_time,
                    'time_gap_per_60s': r['time_gap_per_60s'],
                    'comparison_count': r['comparison_count'],
                    'events': events,
                })

        filename = f"output/predictions_{int(self.runtime)}s.csv"
        with open(filename, "w", newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'class', 'rank', 'driver_name', 'predicted_time',
                'time_gap_per_60s', 'accuracy', 'events'
            ])
            for p in all_predictions:
                writer.writerow([
                    p['class'],
                    p['rank'],
                    p['driver_name'],
                    "{:.3f}".format(p['predicted_time']),
                    "{:.3f}".format(p['time_gap_per_60s']),
                    get_accuracy_level(p['comparison_count']),
                    p['events'],
                ])
        print(f"Wrote {filename}")

        return all_predictions


def load_driver_list(csv_file):
    """Load drivers from CSV with first_name, last_name, class columns."""
    drivers = []
    with open(csv_file, mode='r', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            drivers.append({
                'first_name': row['first_name'],
                'last_name': row['last_name'],
                'class': row['class'],
            })
    return drivers


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Rallycross Driver Rankings",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EXAMPLES:

1. Generate a file of all pairwise comparisons:
    python runner.py
    Output: output/pairwise_comparisons_60s.csv
    
    This generates normalized pairwise comparisons between all drivers in the same
    event/class. Each row shows driver1 vs driver2 with the time difference normalized
    to a 60-second baseline. Always generated on every run.

2. Generate a file of class-based rankings for all drivers (--runtime 1000 seconds):
    python runner.py --runtime 1000
    Output: output/predictions_1000s.csv
    
    This generates per-class rankings where each driver is ranked within their class,
    with predicted race times calculated at the specified runtime (1000s in this case).

3. Generate a file of class-based rankings for specific drivers (--driver-file, --runtime 500):
    python runner.py --driver-file drivers.csv --runtime 500
    Output: output/predictions_500s.csv
    
    First create drivers.csv with format:
      first_name,last_name,class
      Corey,Graffunder,MA
      Casey,Hamm,MA
    
    This will rank only the specified drivers and calculate their expected finishing
    order at 500 second runtime.

4. Generate an overall driver ranking file:
    python runner.py
    Output: output/cross_class_rankings.csv
    
    This generates overall rankings across all classes. Each driver gets an average
    ranking based on their performance across all classes they participate in.
    Ranks are 1-100 with 100 being fastest.

5. Generate class-based driver ranking file:
    python runner.py
    Output: output/cross_class_rankings_by_class.csv
    
    This generates per-class rankings for each driver. Each driver-class combination
    gets its own rank (1-100) within that class.

ADVANCED OPTIONS:

Use --depth for transitive comparisons:
    python runner.py --depth 3
    
    This allows comparing drivers who haven't directly raced by finding paths through
    common competitors (e.g., A beat B, B beat C, so A > C transitively).
    Default depth is 3 (transitive comparisons up to 3 levels deep).

Combine multiple flags:
    python runner.py --runtime 1500 --depth 2 --driver-file lineup.csv
    
    This generates finishing order for drivers in lineup.csv with 1500s runtime and
    transitive comparisons up to depth 2.

OUTPUT FILES:

All output files are written to the output/ directory and include the runtime in
their filename. The output/ directory is automatically created and cleaned before
each run to remove old CSV files.

OUTPUT COLUMNS:

predictions_Xs.csv:
- rank: Position within the class (1 = fastest)
- predicted_time: Predicted race time in seconds at the specified runtime
- time_gap_per_60s: Average time gap per 60 seconds compared to class fastest
- accuracy: Confidence level (low/medium/high) based on comparison count
- events: Number of events the driver has attended

cross_class_rankings.csv:
- ranking: Overall score from 1-100 (100 = fastest)
- accuracy: Confidence level (low/medium/high) based on comparison count
- events: Number of events the driver has attended

cross_class_rankings_by_class.csv:
- class: Racing class
- ranking: Score within that class from 1-100 (100 = fastest)
- accuracy: Confidence level (low/medium/high) based on comparison count
- events: Number of events the driver has attended
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

    args = parser.parse_args()

    runner = Runner(runtime=args.runtime, depth=args.depth)
    runner.run()
    runner.run_predictions()

    if args.driver_file:
        drivers = load_driver_list(args.driver_file)
        finishing_order = runner.generate_finishing_order(drivers, args.runtime)
        runner.export_finishing_order(finishing_order, args.runtime)
        runner.print_finishing_order(finishing_order, args.runtime)
