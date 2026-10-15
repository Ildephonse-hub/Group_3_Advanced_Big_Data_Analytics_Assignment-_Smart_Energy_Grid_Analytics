
#MQTT Publisher for the Smart Energy Grid pilot.

#Purpose

#. Import the UNCHANGED smart_meter_simulator.py.
#2. Generate the first 2,000 readings.
#3. Convert each reading dictionary to JSON.
#4. Publish each reading to EMQX.
#5. Use MQTT QoS 1.
#6. Do not retain messages.
#7. Count successful publish acknowledgements.

#Flow

#smart_meter_simulator.py
       # ↓
    #publisher.py
       # ↓
      #EMQX
       # ↓
  #subscriber.py
       # ↓
   #energy_live


import json
import time

import paho.mqtt.client as mqtt

import smart_meter_simulator as simulator


# ============================================================
# 1. MQTT SETTINGS
# ============================================================

# EMQX is running on this same computer.
MQTT_HOST = "localhost"

# Standard MQTT port.
MQTT_PORT = 1883

# We will publish each meter's reading under its own topic.
#
# Example:
# energy/meters/1000000000
#
# The subscriber uses:
# energy/meters/#
#
# Therefore the subscriber receives all meter messages.
TOPIC_PREFIX = "energy/meters"


# ============================================================
# 2. PILOT SETTINGS
# ============================================================

# The assignment pilot requires exactly 2,000 readings.
PILOT_COUNT = 2_000

# QoS 1 = "At least once" delivery.
#
# With QoS 1, the publisher expects a PUBACK acknowledgement
# from the MQTT broker.
#
# Because MQTT QoS 1 can deliver a message more than once,
# duplicates are possible.
MQTT_QOS = 1

# IMPORTANT:
# The assignment says not to retain these pilot messages.
RETAIN = False


# ============================================================
# 3. CREATE MQTT CLIENT
# ============================================================

client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id="smart_energy_pilot_publisher",
)


# ============================================================
# 4. CONNECT TO EMQX
# ============================================================

print("Connecting to EMQX...")
print(f"Broker: {MQTT_HOST}:{MQTT_PORT}")

client.connect(
    MQTT_HOST,
    MQTT_PORT,
    keepalive=60,
)

print("Connected to EMQX.")
print()


# ============================================================
# 5. START MQTT NETWORK LOOP
# ============================================================

# loop_start() starts Paho's background network thread.
#
# This allows Paho to communicate with EMQX while our main
# program continues publishing messages.
client.loop_start()


# ============================================================
# 6. GET A FRESH GENERATOR
# ============================================================

# IMPORTANT:
# We create a NEW iterator for this pilot.
#
# This means we start from the beginning of the generator.
readings = simulator.iter_readings()


# ============================================================
# 7. PUBLISH THE FIRST 2,000 READINGS
# ============================================================

published_count = 0
ack_count = 0

print(f"Publishing first {PILOT_COUNT:,} readings...")
print()


try:

    for reading in readings:

        # ----------------------------------------------------
        # Stop after exactly 2,000 generated readings.
        # ----------------------------------------------------

        if published_count >= PILOT_COUNT:
            break

        # ----------------------------------------------------
        # Convert the Python dictionary into JSON text.
        #
        # Example Python dictionary:
        #
        # {
        #     "meter_id": 1000000000,
        #     "event_time": "...",
        #     ...
        # }
        #
        # becomes JSON text that can travel through MQTT.
        # ----------------------------------------------------

        payload = json.dumps(reading)

        # ----------------------------------------------------
        # Build the MQTT topic for this meter.
        #
        # Example:
        #
        # energy/meters/1000000000
        # ----------------------------------------------------

        topic = f"{TOPIC_PREFIX}/{reading['meter_id']}"

        # ----------------------------------------------------
        # Publish the JSON message.
        #
        # qos=1:
        # Ask EMQX for QoS 1 delivery.
        #
        # retain=False:
        # Do not ask EMQX to retain this message for future
        # subscribers.
        # ----------------------------------------------------

        message_info = client.publish(
            topic=topic,
            payload=payload,
            qos=MQTT_QOS,
            retain=RETAIN,
        )

        # ----------------------------------------------------
        # Check whether Paho accepted the message for sending.
        #
        # IMPORTANT:
        #
        # "accepted by Paho" is not the same thing as
        # "acknowledged by EMQX".
        #
        # wait_for_publish() waits until the MQTT publish
        # operation has completed.
        # ----------------------------------------------------

        message_info.wait_for_publish()

        # ----------------------------------------------------
        # Confirm that the publish completed.
        # ----------------------------------------------------

        if message_info.is_published():
            ack_count += 1

        published_count += 1

        # ----------------------------------------------------
        # Display the first 10 messages and then every 100.
        # ----------------------------------------------------

        if published_count <= 10 or published_count % 100 == 0:

            print(
                f"Published={published_count:,} | "
                f"Acknowledged={ack_count:,} | "
                f"Meter={reading['meter_id']}"
            )


except KeyboardInterrupt:

    print()
    print("Publisher interrupted by user.")


finally:

    # Stop the background MQTT network thread.
    client.loop_stop()

    # Disconnect cleanly from EMQX.
    client.disconnect()


# ============================================================
# 8. FINAL REPORT
# ============================================================

print()
print("==============================================")
print("PILOT PUBLISHER FINISHED")
print("==============================================")

print(f"Generated readings used:       {published_count:,}")
print(f"Publish acknowledgements:      {ack_count:,}")
print(f"Expected pilot count:          {PILOT_COUNT:,}")

print()
print("The subscriber should now have received these messages.")
print("Check CMD 1 for the subscriber results.")