import csv
import glob
import math

class DriverCollection:
    def __init__(self):
        self.drivers = {}

    def add(self, first_name, last_name, car_class):
        driver = Driver(first_name, last_name, car_class)
        self.drivers[self.driver_id(first_name, last_name, car_class)] = driver

        return driver

    def get(self, first_name, last_name, car_class):
        return self.drivers[self.driver_id(first_name, last_name, car_class)]

    def driver_objs(self):
        # probably not the best way to do this
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
            return self.pairwise_time_total/self.pairwise_total

    def event_count(self):
        return len(self.driver_records)

    def pairwise_stats(self):
        output = ""
        # output = str(self)
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
        # output += "\n"
        # output += self.pairwise_stats()
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

class Runner:
    def __init__(self):
        self.records = []
        self.drivers = DriverCollection()

    def setup(self):
        files = glob.glob("./results/*.csv")
        # [
        #     "results/2025_national_championships.csv",
        #     "results/2024_national_championships.csv",
        #     "results/2023_national_championships.csv",
        #     "results/2022_national_championships.csv",
        # ]
        for file in files:
            with open(file, mode='r', newline='') as file:
                csv_reader = csv.DictReader(file)
                for row in csv_reader:
                    self.records.append(row)
                    self.drivers.add(row['first_name'], row['last_name'], row['class'])

    def run(self):
        self.setup()
        # print(self.records)
        # print(self.drivers)

        driver_pairing_count = {}
        pairwise_driver_records = {}
        driver_pairwise_total = {}

        for driver in self.drivers.driver_objs():
            driver_records = driver.find_pairwise_competitors(self.records)

        print(self.drivers)

    def drivers_name(self, row):
        return f"{row['first_name']} {row['last_name']}"

if __name__ == "__main__":
    runner = Runner()
    runner.run()
