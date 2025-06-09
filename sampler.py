import csv
import random
from datetime import datetime, timedelta

def random_us_number():
    # Generates a random US 10-digit phone number as a string
    area = random.randint(200, 999)
    exchange = random.randint(200, 999)
    subscriber = random.randint(1000, 9999)
    return f"{area}{exchange}{subscriber}"

def random_timestamp(start_date, end_date):
    # Returns a random datetime string between start_date and end_date
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    delta = end - start
    random_days = random.randint(0, delta.days)
    random_seconds = random.randint(0, 86399)
    dt = start + timedelta(days=random_days, seconds=random_seconds)
    return dt.strftime("%Y-%m-%d %H:%M:%S")

# Generate 8 unique phone numbers
phones = set()
while len(phones) < 8:
    phones.add(random_us_number())
phones = list(phones)

cdr_records = []

# Generate 200 random call records
for _ in range(200):
    caller, receiver = random.sample(phones, 2)  # Ensure caller != receiver
    timestamp = random_timestamp("2024-01-01", "2025-05-31")
    cdr_records.append({
        "caller": caller,
        "receiver": receiver,
        "timestamp": timestamp
    })

# Write to CSV
with open("cdr_sample.csv", "w", newline="") as csvfile:
    fieldnames = ["caller", "receiver", "timestamp"]
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for record in cdr_records:
        writer.writerow(record)

print("CDR CSV file 'cdr_sample.csv' generated successfully.")