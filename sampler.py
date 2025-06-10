import csv
import random
from datetime import datetime, timedelta

# CDR format based on linkchart.py's "new format":
# 'Target Number', 'Call Direction', 'From or To Number', 'Date', 'Start', 'End'

def random_phone(existing=None):
    # Generate a US-style phone number
    return f"+1{random.randint(200, 999)}{random.randint(200, 999)}{random.randint(1000, 9999)}"

def random_direction():
    return random.choice(['Outbound', 'Inbound'])

def random_time_pair():
    # Random start time between 8:00 and 20:00
    start_hour = random.randint(8, 20)
    start_minute = random.randint(0, 59)
    start = datetime(2024, random.randint(1, 12), random.randint(1, 28), start_hour, start_minute)
    # Duration between 1 and 30 minutes
    duration = timedelta(seconds=random.randint(30, 1800))
    end = start + duration
    return start, end

def generate_phonebook(min_phones=6, max_phones=20):
    count = random.randint(min_phones, max_phones)
    phones = set()
    while len(phones) < count:
        phones.add(random_phone())
    return list(phones)

def generate_cdr_rows(n, phonebook):
    rows = []
    for _ in range(n):
        # Pick two different phones
        target, other = random.sample(phonebook, 2)
        direction = random_direction()
        # Assign direction
        if direction == 'Outbound':
            from_to = other
        else:
            from_to = other
        start_dt, end_dt = random_time_pair()
        row = {
            'Target Number': target,
            'Call Direction': direction,
            'From or To Number': from_to,
            'Date': start_dt.strftime('%Y-%m-%d'),
            'Start': start_dt.strftime('%H:%M:%S'),
            'End': end_dt.strftime('%H:%M:%S')
        }
        rows.append(row)
    return rows

def write_cdr_csv(filename, rows):
    fieldnames = ['Target Number', 'Call Direction', 'From or To Number', 'Date', 'Start', 'End']
    with open(filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

if __name__ == "__main__":
    phonebook = generate_phonebook(100, 1400)
    cdr_rows = generate_cdr_rows(18000, phonebook)
    write_cdr_csv('cdr_sample.csv', cdr_rows)
    print(f"Generated cdr_sample.csv with {len(cdr_rows)} rows and {len(phonebook)} unique phone numbers.")