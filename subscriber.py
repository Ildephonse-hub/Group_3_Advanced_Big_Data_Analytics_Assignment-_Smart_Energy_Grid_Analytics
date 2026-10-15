
# MQTT Subscriber for the Smart Energy Grid pilot.

# Purpose

# 1. Connect to the EMQX MQTT broker.
# 2. Subscribe to all smart-meter topics:
       # energy/meters/#
# 3. Receive JSON reading messages.
# 4. Convert the JSON message into Python data.
# 5. Insert every received reading into PostgreSQL table energy_live.

# Important

# We intentionally DO NOT remove duplicates here.

#Why?
#Because this pilot is supposed to capture the MQTT stream as it arrives.
#If the same reading is published twice, both messages should be inserted.
#The duplicate-cleaning stage comes later.


import json
import time

import paho.mqtt.client as mqtt
import psycopg


# ============================================================
# 1. MQTT CONNECTION SETTINGS
# ============================================================

# EMQX is running on our own computer.
MQTT_HOST = "localhost"

# Standard MQTT port without TLS.
MQTT_PORT = 1883

# We subscribe to every meter topic under energy/meters/.
MQTT_TOPIC = "energy/meters/#"

# MQTT Quality of Service 1.
#
# QoS 1 means:
# "The message should be delivered at least once."
#
# Because delivery can happen more than once, duplicates are
# possible. This is one reason we preserve every received
# message in energy_live.
MQTT_QOS = 1


# ============================================================
# 2. POSTGRESQL / TIMESCALEDB CONNECTION SETTINGS
# ============================================================

DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "smart_energy"
DB_USER = "Ildephonse"
DB_PASSWORD = "unity"


# ============================================================
# 3. PILOT TARGET
# ============================================================

# The assignment pilot asks us to process 2,000 readings.
TARGET_MESSAGES = 2_000


# ============================================================
# 4. COUNTERS
# ============================================================

# Number of MQTT messages successfully received by the
# subscriber.
received_count = 0

# Number of rows successfully inserted into energy_live.
inserted_count = 0


# ============================================================
# 5. DATABASE CONNECTION
# ============================================================

print("Connecting to PostgreSQL / TimescaleDB...")

db_connection = psycopg.connect(
    host=DB_HOST,
    port=DB_PORT,
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD,
)

db_cursor = db_connection.cursor()

print("Connected to database.")
print()


# ============================================================
# 6. MQTT CALLBACK: WHEN CONNECTION IS ESTABLISHED
# ============================================================

def on_connect(client, userdata, flags, reason_code, properties):
    """
    This function is automatically called by Paho MQTT
    after the subscriber connects to EMQX.

    'callback' means a function that Paho calls automatically
    when a particular MQTT event happens.
    """

    print("Connected to EMQX.")
    print(f"Subscribing to: {MQTT_TOPIC}")
    print(f"QoS: {MQTT_QOS}")

    # Ask EMQX to send us messages matching our topic filter.
    result, mid = client.subscribe(
        MQTT_TOPIC,
        qos=MQTT_QOS
    )

    if result == mqtt.MQTT_ERR_SUCCESS:
        print("Subscription request sent successfully.")
    else:
        print(f"Subscription failed. MQTT result code: {result}")


# ============================================================
# 7. MQTT CALLBACK: WHEN A MESSAGE ARRIVES
# ============================================================

def on_message(client, userdata, msg):
    """
    This function is automatically called every time an MQTT
    message arrives from EMQX.

    'msg' contains information such as:
        msg.topic   -> MQTT topic
        msg.payload -> actual message bytes
    """

    global received_count
    global inserted_count

    # --------------------------------------------------------
    # Count the received MQTT message.
    # --------------------------------------------------------

    received_count += 1

    # --------------------------------------------------------
    # Convert the MQTT payload from bytes to text.
    #
    # MQTT payload arrives as bytes.
    #
    # Example:
    # b'{"meter_id": 1000000000, ...}'
    #
    # decode("utf-8") converts those bytes into normal text.
    # --------------------------------------------------------

    payload_text = msg.payload.decode("utf-8")

    # --------------------------------------------------------
    # Convert JSON text into a Python dictionary.
    #
    # JSON = a standard text format used to exchange data.
    #
    # After json.loads(), we can access:
    # reading["meter_id"]
    # reading["event_time"]
    # etc.
    # --------------------------------------------------------

    reading = json.loads(payload_text)

    # --------------------------------------------------------
    # Extract the eight required fields.
    # --------------------------------------------------------

    meter_id = reading["meter_id"]
    event_time = reading["event_time"]
    received_time = reading["received_time"]
    power_kw = reading["power_kw"]
    voltage_v = reading["voltage_v"]
    current_a = reading["current_a"]
    frequency_hz = reading["frequency_hz"]
    energy_kwh = reading["energy_kwh"]

    # --------------------------------------------------------
    # Insert the complete reading into energy_live.
    #
    # Notice:
    # We do NOT check whether this reading already exists.
    #
    # Therefore duplicate messages are preserved.
    # --------------------------------------------------------

    db_cursor.execute(
        """
        INSERT INTO energy_live (
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
            %s, %s, %s, %s,
            %s, %s, %s, %s
        )
        """,
        (
            meter_id,
            event_time,
            received_time,
            power_kw,
            voltage_v,
            current_a,
            frequency_hz,
            energy_kwh,
        ),
    )

    inserted_count += 1

    # --------------------------------------------------------
    # Commit periodically instead of committing every single
    # message.
    #
    # A commit makes database changes permanent.
    #
    # Committing every 100 rows reduces transaction overhead
    # while still saving data progressively.
    # --------------------------------------------------------

    if inserted_count % 100 == 0:
        db_connection.commit()

    # --------------------------------------------------------
    # Display progress.
    # --------------------------------------------------------

    if received_count <= 10 or received_count % 100 == 0:
        print(
            f"Received={received_count:,} | "
            f"Inserted={inserted_count:,} | "
            f"Meter={meter_id}"
        )


# ============================================================
# 8. CREATE THE MQTT CLIENT
# ============================================================

# Paho MQTT is the Python library we use to communicate
# using the MQTT protocol.
client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id="smart_energy_pilot_subscriber",
)


# Tell Paho which functions should run for particular events.

# Run on_connect() after connecting to EMQX.
client.on_connect = on_connect

# Run on_message() whenever a subscribed message arrives.
client.on_message = on_message


# ============================================================
# 9. CONNECT TO EMQX
# ============================================================

print("Connecting to EMQX broker...")

client.connect(
    MQTT_HOST,
    MQTT_PORT,
    keepalive=60,
)

print("Starting MQTT network loop...")
print()
print("Subscriber is now waiting for messages.")
print("START THE PUBLISHER IN ANOTHER CMD WINDOW.")
print()


# ============================================================
# 10. START THE MQTT NETWORK LOOP
# ============================================================

# loop_forever() keeps the subscriber running.
#
# It continuously:
#   - receives MQTT packets
#   - sends MQTT acknowledgements
#   - calls on_message() when data arrives
#   - maintains the MQTT connection
#
# Without this network loop, the subscriber would not
# continuously process incoming messages.

try:
    client.loop_forever()

except KeyboardInterrupt:
    print()
    print("Stopping subscriber...")


# ============================================================
# 11. FINAL DATABASE COMMIT
# ============================================================

# There may be fewer than 100 rows in the final transaction.
# This commit ensures those rows are saved too.

db_connection.commit()


# ============================================================
# 12. CLOSE RESOURCES
# ============================================================

client.disconnect()

db_cursor.close()
db_connection.close()

print()
print("Subscriber stopped.")
print(f"Total MQTT messages received: {received_count:,}")
print(f"Total database rows inserted: {inserted_count:,}")