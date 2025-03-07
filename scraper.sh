#!/bin/bash

# Define the Python script path
PYTHON_SCRIPT="scraper.py"
LOG_FILE="scraper.log"

# Check if cron is installed
if ! command -v crontab &> /dev/null
then
    echo "Cron is not installed. Please install it first."
    exit 1
fi

# Write the cron job (Runs daily at 2 AM)
CRON_JOB="0 2 * * * /usr/bin/python3 $PYTHON_SCRIPT >> $LOG_FILE 2>&1"

# Check if the cron job already exists
(crontab -l 2>/dev/null | grep -F "$PYTHON_SCRIPT") && echo "Cron job already exists." && exit 0

# Add the cron job
(crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -

echo "Cron job added successfully! The scraper will run daily at 2 AM."
