"""
Comprehensive unit and integration tests for the rallycross driver rankings system.

Tests cover:
- Driver model and operations
- DriverPair model and normalization
- DriverCollection and search operations
- Runner pipeline and calculations
- Accuracy level categorization
"""

import pytest
import csv
import os
import glob
import tempfile
from datetime import datetime, timedelta
from runner import (
    Driver, DriverPair, DriverCollection, Runner,
    get_accuracy_level, ACCURACY_THRESHOLD_LOW, ACCURACY_THRESHOLD_MEDIUM,
    RECENCY_HALF_LIFE_DAYS, TRANSITIVE_WEIGHT_MULTIPLIER,
    TRANSITIVE_DISTANCE_DISCOUNT_BASE
)


class TestAccuracyLevel:
    """Test accuracy level categorization function."""
    
    def test_low_accuracy(self):
        """Test that 0-9 comparisons returns 'low'."""
        assert get_accuracy_level(0) == "low"
        assert get_accuracy_level(5) == "low"
        assert get_accuracy_level(9) == "low"
    
    def test_medium_accuracy(self):
        """Test that 10-19 comparisons returns 'medium'."""
        assert get_accuracy_level(10) == "medium"
        assert get_accuracy_level(15) == "medium"
        assert get_accuracy_level(19) == "medium"
    
    def test_high_accuracy(self):
        """Test that 20+ comparisons returns 'high'."""
        assert get_accuracy_level(20) == "high"
        assert get_accuracy_level(50) == "high"
        assert get_accuracy_level(100) == "high"
    
    def test_boundary_conditions(self):
        """Test exact boundary values."""
        assert get_accuracy_level(ACCURACY_THRESHOLD_LOW - 1) == "low"
        assert get_accuracy_level(ACCURACY_THRESHOLD_LOW) == "medium"
        assert get_accuracy_level(ACCURACY_THRESHOLD_MEDIUM - 1) == "medium"
        assert get_accuracy_level(ACCURACY_THRESHOLD_MEDIUM) == "high"


class TestDriver:
    """Test Driver class functionality."""
    
    def test_driver_creation(self):
        """Test creating a driver instance."""
        driver = Driver("John", "Doe", "MA")
        assert driver.first_name == "John"
        assert driver.last_name == "Doe"
        assert driver.car_class == "MA"
    
    def test_driver_name(self):
        """Test driver name formatting."""
        driver = Driver("Jane", "Smith", "PR")
        assert driver.name() == "Jane Smith"
    
    def test_driver_initialization(self):
        """Test driver attributes are initialized correctly."""
        driver = Driver("Test", "Driver", "MF")
        assert driver.pairwise_total == 0
        assert driver.pairwise_wins == 0
        assert driver.pairwise_losses == 0
        assert driver.pairwise_time_total == 0.0
        assert driver.pairwise_times == {}
        assert driver.driver_records == []
    
    def test_avg_time_difference_no_data(self):
        """Test avg_time_difference with no pairwise data."""
        driver = Driver("Test", "Driver", "MA")
        assert driver.avg_time_difference() == 0.0
    
    def test_event_count(self):
        """Test event count returns length of driver records."""
        driver = Driver("Test", "Driver", "MA")
        # Initially empty
        assert driver.event_count() == 0
        
        # Add mock records
        driver.driver_records.append({'date': '2024-01-01', 'event_name': 'Test Event'})
        driver.driver_records.append({'date': '2024-01-02', 'event_name': 'Test Event 2'})
        assert driver.event_count() == 2
    
    def test_driver_equality(self):
        """Test that two drivers with same info are different instances."""
        driver1 = Driver("John", "Doe", "MA")
        driver2 = Driver("John", "Doe", "MA")
        # Same attributes but different objects
        assert driver1.name() == driver2.name()
        assert driver1 is not driver2


class TestDriverPair:
    """Test DriverPair class functionality."""
    
    def test_driver_pair_creation(self):
        """Test creating a DriverPair instance."""
        d1 = Driver("John", "Doe", "MA")
        d2 = Driver("Jane", "Smith", "MA")
        
        pair = DriverPair(d1, d2, "2024-05-15", "Test Event", "MA", 300.0, 305.0)
        
        assert pair.driver1 is d1
        assert pair.driver2 is d2
        assert pair.date == "2024-05-15"
        assert pair.event_name == "Test Event"
        assert pair.car_class == "MA"
    
    def test_driver_pair_raw_diff(self):
        """Test raw time difference calculation."""
        d1 = Driver("John", "Doe", "MA")
        d2 = Driver("Jane", "Smith", "MA")
        
        pair = DriverPair(d1, d2, "2024-05-15", "Event", "MA", 300.0, 305.0)
        assert pair.raw_diff == -5.0  # 300 - 305
    
    def test_driver_pair_normalized_diff(self):
        """Test normalized time difference calculation."""
        d1 = Driver("John", "Doe", "MA")
        d2 = Driver("Jane", "Smith", "MA")
        
        # Test case: 300s vs 305s
        # baseline = (300 + 305) / 2 = 302.5
        # normalized = (-5 / 302.5) * 60 = -0.994...
        pair = DriverPair(d1, d2, "2024-05-15", "Event", "MA", 300.0, 305.0)
        
        # Check it's within expected range
        assert -1.0 < pair.normalized_diff_per_60s < 0.0
        assert abs(pair.normalized_diff_per_60s - (-5.0 / 302.5 * 60.0)) < 0.001
    
    def test_driver_pair_zero_baseline(self):
        """Test normalized diff when baseline is zero."""
        d1 = Driver("John", "Doe", "MA")
        d2 = Driver("Jane", "Smith", "MA")
        
        pair = DriverPair(d1, d2, "2024-05-15", "Event", "MA", 0.0, 0.0)
        assert pair.normalized_diff_per_60s == 0.0
    
    def test_driver_pair_get_names(self):
        """Test getting driver names from pair."""
        d1 = Driver("John", "Doe", "MA")
        d2 = Driver("Jane", "Smith", "MA")
        
        pair = DriverPair(d1, d2, "2024-05-15", "Event", "MA", 300.0, 305.0)
        
        assert pair.get_driver1_name() == "John Doe"
        assert pair.get_driver2_name() == "Jane Smith"
    
    def test_driver_pair_to_dict(self):
        """Test converting DriverPair to dictionary."""
        d1 = Driver("John", "Doe", "MA")
        d2 = Driver("Jane", "Smith", "MA")
        
        pair = DriverPair(d1, d2, "2024-05-15", "Test Event", "MA", 300.0, 305.0)
        pair_dict = pair.to_dict()
        
        assert pair_dict['date'] == "2024-05-15"
        assert pair_dict['event_name'] == "Test Event"
        assert pair_dict['class'] == "MA"
        assert pair_dict['driver1'] == "John Doe"
        assert pair_dict['driver2'] == "Jane Smith"
        assert 'normalized_diff_per_60s' in pair_dict
        assert 'raw_diff_sec' in pair_dict
        assert pair_dict['driver1_time'] == 300.0
        assert pair_dict['driver2_time'] == 305.0


class TestDriverCollection:
    """Test DriverCollection class functionality."""
    
    def test_collection_creation(self):
        """Test creating a DriverCollection instance."""
        collection = DriverCollection()
        assert collection.drivers == {}
        assert len(collection.driver_objs()) == 0
    
    def test_add_driver(self):
        """Test adding drivers to collection."""
        collection = DriverCollection()
        d1 = collection.add("John", "Doe", "MA")
        
        assert d1.first_name == "John"
        assert d1.last_name == "Doe"
        assert d1.car_class == "MA"
        assert len(collection.drivers) == 1
    
    def test_add_duplicate_driver(self):
        """Test adding duplicate driver returns same instance."""
        collection = DriverCollection()
        d1 = collection.add("John", "Doe", "MA")
        d2 = collection.add("John", "Doe", "MA")
        
        # Should be same instance (deduplication)
        assert d1 is d2
        assert len(collection.drivers) == 1
    
    def test_add_same_name_different_class(self):
        """Test adding same name but different class creates new driver."""
        collection = DriverCollection()
        d1 = collection.add("John", "Doe", "MA")
        d2 = collection.add("John", "Doe", "PR")
        
        # Different instances
        assert d1 is not d2
        assert len(collection.drivers) == 2
    
    def test_get_driver(self):
        """Test retrieving a specific driver."""
        collection = DriverCollection()
        collection.add("John", "Doe", "MA")
        
        retrieved = collection.get("John", "Doe", "MA")
        assert retrieved.name() == "John Doe"
        assert retrieved.car_class == "MA"
    
    def test_get_by_name(self):
        """Test getting all drivers with a specific name."""
        collection = DriverCollection()
        collection.add("John", "Doe", "MA")
        collection.add("John", "Doe", "PR")
        collection.add("Jane", "Smith", "MA")
        
        johns = collection.get_by_name("John", "Doe")
        assert len(johns) == 2
        assert all(d.first_name == "John" and d.last_name == "Doe" for d in johns)
    
    def test_get_by_class(self):
        """Test getting all drivers in a class."""
        collection = DriverCollection()
        collection.add("John", "Doe", "MA")
        collection.add("Jane", "Smith", "MA")
        collection.add("Bob", "Jones", "PR")
        
        ma_drivers = collection.get_by_class("MA")
        assert len(ma_drivers) == 2
        assert all(d.car_class == "MA" for d in ma_drivers)
    
    def test_get_all_classes(self):
        """Test getting sorted list of all classes."""
        collection = DriverCollection()
        collection.add("John", "Doe", "PR")
        collection.add("Jane", "Smith", "MA")
        collection.add("Bob", "Jones", "MF")
        
        classes = collection.get_all_classes()
        assert classes == ["MA", "MF", "PR"]  # Sorted
    
    def test_driver_objs(self):
        """Test getting all driver objects."""
        collection = DriverCollection()
        d1 = collection.add("John", "Doe", "MA")
        d2 = collection.add("Jane", "Smith", "PR")
        
        objs = collection.driver_objs()
        assert len(objs) == 2
        assert d1 in objs
        assert d2 in objs
    
    def test_driver_id(self):
        """Test driver ID generation."""
        collection = DriverCollection()
        
        id1 = collection.driver_id("John", "Doe", "MA")
        id2 = collection.driver_id("John", "Doe", "MA")
        id3 = collection.driver_id("John", "Doe", "PR")
        
        # Same parameters should give same ID
        assert id1 == id2
        # Different class should give different ID
        assert id1 != id3


class TestRunner:
    """Test Runner class functionality."""
    
    @pytest.fixture
    def runner(self):
        """Create a basic runner instance."""
        return Runner(runtime=60.0, depth=1)
    
    def test_runner_creation(self, runner):
        """Test creating a Runner instance."""
        assert runner.runtime == 60.0
        assert runner.depth == 1
        assert len(runner.records) == 0
        assert len(runner.drivers.drivers) == 0
        assert len(runner.pairwise_comparisons) == 0
    
    def test_runner_with_custom_params(self):
        """Test creating runner with custom parameters."""
        runner = Runner(runtime=90.0, depth=3)
        assert runner.runtime == 90.0
        assert runner.depth == 3
    
    def test_recency_weight_calculation(self, runner):
        """Test recency weight calculation."""
        # Today's date
        today = datetime.now().strftime("%Y-%m-%d")
        weight_today = runner._recency_weight(today)
        
        # Weight should be close to 1.0 for today
        assert 0.95 < weight_today <= 1.0
        
        # 180 days ago: e^(-180/180) = e^(-1) ≈ 0.368
        old_date = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d")
        weight_old = runner._recency_weight(old_date)
        assert 0.35 < weight_old < 0.40
    
    def test_weighted_avg_diff_no_comparisons(self, runner):
        """Test weighted average diff with no comparisons."""
        edges = {}
        avg, weight, count = runner._weighted_avg_diff(edges, "Driver1", "Driver2")
        
        assert avg is None
        assert weight == 0
        assert count == 0
    
    def test_weighted_avg_diff_with_comparisons(self, runner):
        """Test weighted average diff with comparisons."""
        edges = {
            ("Driver1", "Driver2"): [(1.0, 0.8), (1.5, 0.7)]
        }
        
        avg, weight, count = runner._weighted_avg_diff(edges, "Driver1", "Driver2")
        
        assert avg is not None
        assert count == 2
        # weighted average: (1.0 * 0.8 + 1.5 * 0.7) / (0.8 + 0.7)
        expected_avg = (1.0 * 0.8 + 1.5 * 0.7) / (0.8 + 0.7)
        assert abs(avg - expected_avg) < 0.001


class TestIntegration:
    """Integration tests using the full runner pipeline."""
    
    @pytest.fixture
    def temp_results_dir(self):
        """Create a temporary directory for test results."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.fixture(autouse=True)
    def setup_output_dir(self):
        """Create and clean output directory before and after each test."""
        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)
        
        # Clean CSV files before test
        for csv_file in glob.glob(os.path.join(output_dir, "*.csv")):
            os.remove(csv_file)
        
        yield
        
        # Clean CSV files after test
        for csv_file in glob.glob(os.path.join(output_dir, "*.csv")):
            os.remove(csv_file)
    
    @pytest.fixture
    def sample_records(self):
        """Create sample race records for testing."""
        return [
            {
                'date': '2024-01-01',
                'event_name': 'Test Event 1',
                'class': 'MA',
                'first_name': 'John',
                'last_name': 'Doe',
                'car_number': '1',
                'total': '300.5',
            },
            {
                'date': '2024-01-01',
                'event_name': 'Test Event 1',
                'class': 'MA',
                'first_name': 'Jane',
                'last_name': 'Smith',
                'car_number': '2',
                'total': '305.2',
            },
            {
                'date': '2024-01-01',
                'event_name': 'Test Event 1',
                'class': 'MA',
                'first_name': 'Bob',
                'last_name': 'Jones',
                'car_number': '3',
                'total': '310.1',
            },
            {
                'date': '2024-01-02',
                'event_name': 'Test Event 2',
                'class': 'PR',
                'first_name': 'Alice',
                'last_name': 'Johnson',
                'car_number': '4',
                'total': '250.0',
            },
            {
                'date': '2024-01-02',
                'event_name': 'Test Event 2',
                'class': 'PR',
                'first_name': 'Charlie',
                'last_name': 'Brown',
                'car_number': '5',
                'total': '255.5',
            },
        ]
    
    def test_full_pipeline(self, sample_records):
        """Test the complete runner pipeline with sample data."""
        runner = Runner(runtime=60.0, depth=1)
        runner.records = sample_records
        
        # Add drivers
        for record in sample_records:
            runner.drivers.add(record['first_name'], record['last_name'], record['class'])
        
        # Build pairwise comparisons
        for driver in runner.drivers.driver_objs():
            driver.find_pairwise_competitors(runner.records)
        
        runner.build_pairwise_comparisons()
        
        # Should have created pairwise comparisons
        assert len(runner.pairwise_comparisons) > 0
        
        # Check that DriverPair objects were created
        for pair in runner.pairwise_comparisons:
            assert isinstance(pair, DriverPair)
            assert pair.get_driver1_name() is not None
            assert pair.get_driver2_name() is not None
    
    def test_build_class_graph(self, sample_records):
        """Test building a class graph from pairwise comparisons."""
        runner = Runner(runtime=60.0, depth=1)
        runner.records = sample_records
        
        # Set up data
        for record in sample_records:
            runner.drivers.add(record['first_name'], record['last_name'], record['class'])
        
        for driver in runner.drivers.driver_objs():
            driver.find_pairwise_competitors(runner.records)
        
        runner.build_pairwise_comparisons()
        
        # Build graph for MA class
        drivers, edges = runner._build_class_graph("MA")
        
        assert len(drivers) == 3  # John, Jane, Bob
        assert len(edges) > 0  # Should have comparison edges
    
    def test_cross_class_rankings_by_class(self, sample_records):
        """Test building cross-class rankings by class."""
        runner = Runner(runtime=60.0, depth=1)
        runner.records = sample_records
        
        # Set up data
        for record in sample_records:
            runner.drivers.add(record['first_name'], record['last_name'], record['class'])
        
        for driver in runner.drivers.driver_objs():
            driver.find_pairwise_competitors(runner.records)
        
        runner.build_pairwise_comparisons()
        
        # Build rankings
        rankings = runner.build_cross_class_rankings_by_class()
        
        # Should have rankings for both MA and PR classes
        assert len(rankings) > 0
        
        # Check structure
        for ranking in rankings:
            assert 'driver_name' in ranking
            assert 'class' in ranking
            assert 'ranking' in ranking
            assert 'accuracy' in ranking
            # Ranking should be 1-100
            assert 1 <= ranking['ranking'] <= 100
    
    def test_cross_class_rankings(self, sample_records):
        """Test building overall cross-class rankings."""
        runner = Runner(runtime=60.0, depth=1)
        runner.records = sample_records
        
        # Set up data
        for record in sample_records:
            runner.drivers.add(record['first_name'], record['last_name'], record['class'])
        
        for driver in runner.drivers.driver_objs():
            driver.find_pairwise_competitors(runner.records)
        
        runner.build_pairwise_comparisons()
        
        # Build rankings
        rankings = runner.build_cross_class_rankings()
        
        # Should have rankings for all drivers
        assert len(rankings) > 0
        
        # Rankings should be sorted by score descending
        scores = [r['ranking'] for r in rankings]
        assert scores == sorted(scores, reverse=True)
    
    def test_export_pairwise_comparisons(self, sample_records):
        """Test exporting pairwise comparisons to CSV."""
        runner = Runner(runtime=60.0, depth=1)
        runner.records = sample_records
        
        # Set up data
        for record in sample_records:
            runner.drivers.add(record['first_name'], record['last_name'], record['class'])
        
        for driver in runner.drivers.driver_objs():
            driver.find_pairwise_competitors(runner.records)
        
        runner.build_pairwise_comparisons()
        
        # Ensure output directory exists
        os.makedirs("output", exist_ok=True)
        
        # Export to file
        runner.export_pairwise_comparisons()
        
        # Verify file exists and has correct structure
        assert os.path.exists("output/pairwise_comparisons_60s.csv")
        
        with open("output/pairwise_comparisons_60s.csv", 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
            assert len(rows) > 0
            # Check header
            assert 'date' in reader.fieldnames
            assert 'driver1' in reader.fieldnames
            assert 'driver2' in reader.fieldnames
            assert 'normalized_diff_per_60s' in reader.fieldnames


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_driver_with_spaces_in_name(self):
        """Test driver names with spaces and punctuation."""
        driver = Driver("Mary", "O'Brien", "MA")
        assert driver.name() == "Mary O'Brien"
    
    def test_multi_word_last_name_lookup(self):
        """Test looking up drivers with multi-word last names like 'Diego De'."""
        collection = DriverCollection()
        collection.add("Diego", "De", "MA")
        
        # Test get_by_name_and_class lookup
        driver = collection.get_by_name_and_class("Diego De", "MA")
        assert driver is not None
        assert driver.first_name == "Diego"
        assert driver.last_name == "De"
        assert driver.car_class == "MA"
    
    def test_driver_pair_identical_times(self):
        """Test driver pair with identical times."""
        d1 = Driver("John", "Doe", "MA")
        d2 = Driver("Jane", "Smith", "MA")
        
        pair = DriverPair(d1, d2, "2024-05-15", "Event", "MA", 300.0, 300.0)
        assert pair.raw_diff == 0.0
        assert pair.normalized_diff_per_60s == 0.0
    
    def test_collection_get_nonexistent_class(self):
        """Test getting drivers from nonexistent class."""
        collection = DriverCollection()
        collection.add("John", "Doe", "MA")
        
        result = collection.get_by_class("NONEXISTENT")
        assert result == []
    
    def test_accuracy_level_negative(self):
        """Test accuracy level with negative value (shouldn't happen but test anyway)."""
        # Negative values should be treated as "low"
        result = get_accuracy_level(-5)
        assert result == "low"
    
    def test_runner_empty_edges(self):
        """Test runner methods with empty edge data."""
        runner = Runner(runtime=60.0, depth=1)
        
        # Test with no edges
        avg, weight, count = runner._weighted_avg_diff({}, "D1", "D2")
        assert avg is None
        assert weight == 0
        assert count == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
