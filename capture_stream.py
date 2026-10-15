
#Smart Energy Grid Analytics
#Full Historical Data Capture

#Purpose
#-------
#read data smart_meter_simulator.py generator and store every
#emitted reading in the TimescaleDB hypertable:

    #energy_readings

#IMPORTANT
#---------
#This stage is RAW DATA CAPTURE.

#We intentionally DO NOT clean the data here.

#Therefore:

    #- duplicate readings are preserved
    #- missing readings remain missing
    #- delayed readings remain delayed

#Cleaning and quality analysis will happen later.

#Expected generator output
#-------------------------

#Architecture
#------------

    #smart_meter_simulator.py
             #|
             #| iter_readings()
            # v
       #capture_stream.py
            # |
            # | batches
            # v
       #TimescaleDB
            # |
            # v
       #energy_readings


#Why batches?
# ------------
#The complete dataset contains more than 10 million readings.

#We do NOT load all 10+ million dictionaries into RAM at once.

#Instead:

    #generator
   #     ↓
    #small batch
    #    ↓
   # INSERT
   #     ↓
    #COMMIT
   #     ↓
   # clear batch
   #     ↓
   # next batch

#This keeps memory usage much lower.


#Database table


#The table is already a TimescaleDB hypertable partitioned
#by event_time with a 1-day chunk interval.


# ---------------------------------------------------------
# IMPORT LIBRARIES
# ---------------------------------------------------------

import time

# psycopg is the PostgreSQL/TimescaleDB Python driver.
# It allows Python to connect to PostgreSQL and execute SQL.
import psycopg

# This is the UNCHANGED assignment generator.
# We only READ data from it.
import smart_meter_simulator as simulator


# ---------------------------------------------------------
# DATABASE CONNECTION SETTINGS
# ---------------------------------------------------------

# PostgreSQL/TimescaleDB is running in Docker and its
# container port 5432 is mapped to localhost:5432.
DB_HOST = "localhost"
DB_PORT = 5432

# Database created for this assignment.
DB_NAME = "smart_energy"

# PostgreSQL username.
DB_USER = "Ildephonse"

# PostgreSQL password.
DB_PASSWORD = "unity"


# ---------------------------------------------------------
# BATCH SIZE
# ---------------------------------------------------------

# We insert this many readings in one database operation.

# A batch is simply a group of rows processed together.

# 5,000 worked successfully in the performance test,
# so we keep the same batch size for the full capture.
BATCH_SIZE = 5_000


# ---------------------------------------------------------
# EXPECTED DATASET SIZE
# ---------------------------------------------------------

# This is the expected number of readings emitted by the
# assignment generator.

EXPECTED_EMITTED = 10_696_848


# ---------------------------------------------------------
# CONNECT TO TIMESCALEDB
# ---------------------------------------------------------

print("================================================")
print("SMART ENERGY GRID - FULL HISTORICAL CAPTURE")
print("================================================")
print()

print("Connecting to TimescaleDB...")

# Open a connection to PostgreSQL/TimescaleDB.
connection = psycopg.connect(
    host=DB_HOST,
    port=DB_PORT,
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD,
)

# A cursor is used to send SQL commands to the database.
cursor = connection.cursor()

print("Connected successfully.")
print()


# ---------------------------------------------------------
# CLEAR OLD TEST DATA
# ---------------------------------------------------------

print("Clearing previous test data...")

# IMPORTANT:
#
# The table currently contains the 5,000 rows from our
# performance test.
#
# We must remove them before starting the real full capture.
#
# TRUNCATE removes all rows from the table.
#
# We are NOT deleting the table itself.
# The hypertable structure remains available.
cursor.execute(
    "TRUNCATE TABLE energy_readings"
)

# Make the TRUNCATE permanent.
connection.commit()

print("energy_readings is now empty.")
print()


# ---------------------------------------------------------
# START A FRESH GENERATOR
# ---------------------------------------------------------

print("Starting a fresh generator...")

# iter_readings() returns a generator.
#
# A generator produces readings one at a time instead of
# creating the entire 10+ million-row dataset in memory.
generator = simulator.iter_readings()

print("Generator started.")
print()

print("Beginning COMPLETE historical capture...")
print()
print(
    f"Expected emitted readings: {EXPECTED_EMITTED:,}"
)
print(
    f"Database batch size:        {BATCH_SIZE:,}"
)
print()


# ---------------------------------------------------------
# COUNTERS
# ---------------------------------------------------------

# Number of readings received from the generator.
emitted_count = 0

# Number of readings successfully inserted into PostgreSQL.
inserted_count = 0

# Current group of rows waiting to be inserted.
batch = []


# ---------------------------------------------------------
# START TIMER
# ---------------------------------------------------------

# perf_counter() provides a high-resolution timer.
#
# We use it to measure the actual database loading time.
start_time = time.perf_counter()


# ---------------------------------------------------------
# MAIN CAPTURE LOOP
# ---------------------------------------------------------

try:

    # Read one reading at a time from the generator.
    #
    # The loop continues until the generator has produced
    # its complete dataset.
    for reading in generator:

        # We successfully received one reading from the
        # generator.
        emitted_count += 1


        # -------------------------------------------------
        # CONVERT DICTIONARY TO DATABASE ROW
        # -------------------------------------------------

        # The generator returns a dictionary such as:
        #
        # {
        #     "meter_id": 1000000000,
        #     "event_time": "...",
        #     "received_time": "...",
        #     "power_kw": ...,
        #     "voltage_v": ...,
        #     "current_a": ...,
        #     "frequency_hz": ...,
        #     "energy_kwh": ...
        # }
        #
        # We extract the eight required fields and create
        # one tuple representing one database row.

        batch.append(
            (
                reading["meter_id"],
                reading["event_time"],
                reading["received_time"],
                reading["power_kw"],
                reading["voltage_v"],
                reading["current_a"],
                reading["frequency_hz"],
                reading["energy_kwh"],
            )
        )


        # -------------------------------------------------
        # INSERT WHEN BATCH IS FULL
        # -------------------------------------------------

        # Once the batch reaches 5,000 rows, send those rows
        # to PostgreSQL.
        if len(batch) >= BATCH_SIZE:

            cursor.executemany(
                """
                INSERT INTO energy_readings (
                    meter_id,
                    event_time,
                    received_time,
                    power_kw,
                    voltage_v,
                    current_a,
                    frequency_hz,
                    energy_kwh
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
                """,
                batch,
            )


            # -------------------------------------------------
            # COMMIT
            # -------------------------------------------------

            # COMMIT permanently saves this batch.

            connection.commit()


            # Since the database successfully accepted the
            # batch, increase the inserted counter.
            inserted_count += len(batch)


            # Remove the rows from the Python list.

            # This is important because we do not want the
            # batch list to grow to millions of rows.
            batch.clear()


            # -------------------------------------------------
            # PERFORMANCE INFORMATION
            # -------------------------------------------------

            elapsed = (
                time.perf_counter() - start_time
            )

            # Calculate the current insertion speed.
            rows_per_second = (
                inserted_count / elapsed
                if elapsed > 0
                else 0
            )


            # Print progress periodically.
            print(
                f"Emitted={emitted_count:,} | "
                f"Inserted={inserted_count:,} | "
                f"Elapsed={elapsed:.1f}s | "
                f"Rate={rows_per_second:,.0f} rows/s"
            )


    # ---------------------------------------------------------
    # INSERT FINAL PARTIAL BATCH
    # ---------------------------------------------------------

    # The total number of readings may not be an exact
    # multiple of 5,000.
    #
    # Therefore, after the generator finishes, there may
    # still be some rows remaining in 'batch'.
    #
    # We must insert those rows too.

    if batch:

        cursor.executemany(
            """
            INSERT INTO energy_readings (
                meter_id,
                event_time,
                received_time,
                power_kw,
                voltage_v,
                current_a,
                frequency_hz,
                energy_kwh
            )
            VALUES (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )
            """,
            batch,
        )

        # Permanently save the final batch.
        connection.commit()

        # Add the final batch size to the inserted counter.
        inserted_count += len(batch)

        # Clear the Python list.
        batch.clear()


# ---------------------------------------------------------
# ERROR HANDLING
# ---------------------------------------------------------

except Exception:

    # If something goes wrong, undo the current uncommitted
    # database transaction.
    connection.rollback()

    print()
    print("================================================")
    print("ERROR: HISTORICAL CAPTURE FAILED")
    print("================================================")
    print(
        f"Readings emitted before failure: "
        f"{emitted_count:,}"
    )
    print(
        f"Rows inserted before failure: "
        f"{inserted_count:,}"
    )
    print()

    # Re-raise the original error so that Python displays
    # the exact technical problem.
    raise


# ---------------------------------------------------------
# CLOSE DATABASE RESOURCES
# ---------------------------------------------------------

finally:

    # Close the cursor because we no longer need it.
    cursor.close()

    # Close the database connection.
    connection.close()


# ---------------------------------------------------------
# FINAL PERFORMANCE CALCULATION
# ---------------------------------------------------------

elapsed = (
    time.perf_counter() - start_time
)

if elapsed > 0:
    rows_per_second = (
        inserted_count / elapsed
    )
else:
    rows_per_second = 0


# ---------------------------------------------------------
# COMPARE WITH EXPECTED GENERATOR COUNT
# ---------------------------------------------------------

count_difference = (
    emitted_count - EXPECTED_EMITTED
)


# ---------------------------------------------------------
# FINAL REPORT
# ---------------------------------------------------------

print()
print("================================================")
print("FULL HISTORICAL CAPTURE FINISHED")
print("================================================")
print()

print(
    f"Expected emitted readings:   "
    f"{EXPECTED_EMITTED:,}"
)

print(
    f"Actual emitted readings:     "
    f"{emitted_count:,}"
)

print(
    f"Database rows inserted:      "
    f"{inserted_count:,}"
)

print(
    f"Difference from expected:    "
    f"{count_difference:,}"
)

print(
    f"Elapsed time:                "
    f"{elapsed:.2f} seconds"
)

print(
    f"Loading rate:                "
    f"{rows_per_second:,.0f} rows/second"
)

print()


# ---------------------------------------------------------
# CHECK WHETHER GENERATOR COUNT MATCHED EXPECTATION
# ---------------------------------------------------------

if emitted_count == EXPECTED_EMITTED:

    print(
        "Generator count verification: PASS"
    )

else:

    print(
        "Generator count verification: CHECK REQUIRED"
    )

    print(
        "The actual emitted count does not match "
        "the assignment expectation."
    )

print()


# ---------------------------------------------------------
# CHECK WHETHER INSERT COUNT MATCHED EMITTED COUNT
# ---------------------------------------------------------

if inserted_count == emitted_count:

    print(
        "Capture count verification: PASS"
    )

    print(
        "Every emitted reading was inserted."
    )

else:

    print(
        "Capture count verification: CHECK REQUIRED"
    )

    print(
        "The emitted and inserted counts are different."
    )

print()


# ---------------------------------------------------------
# DATA QUALITY REMINDER
# ---------------------------------------------------------

print("IMPORTANT DATA-STAGE REMINDER:")
print()
print("This is RAW historical data.")
print()
print("- Duplicate readings are preserved.")
print("- Missing readings remain missing.")
print("- Delayed readings remain delayed.")
print("- No deduplication has been performed.")
print("- No missing intervals have been filled.")
print("- No readings have been deleted.")
print()


# ---------------------------------------------------------
# NEXT STAGE
# ---------------------------------------------------------

print(
    "Next stage:"
)

print(
    "Verify the complete captured dataset in "
    "TimescaleDB before beginning data-quality cleaning."
)

print()
print("================================================")
print("END")
print("================================================")