
#Populate the PostgreSQL meters table from the official AUCA generator.

#The generator is the source of truth for the 4,000 meter metadata records.
#We store only the three fields required by the assignment:

    #meter_id
   # region
    # customer_type


import psycopg

import smart_meter_simulator as simulator


# ------------------------------------------------------------
# PostgreSQL connection information
# ------------------------------------------------------------

DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "smart_energy"
DB_USER = "Ildephonse"
DB_PASSWORD = "unity"


def main():
    # --------------------------------------------------------
    # 1. Get the official 4,000 meter metadata from the
    #    unchanged AUCA generator.
    # --------------------------------------------------------

    meters = simulator.meter_metadata()

    print(f"Generator returned {len(meters):,} meters.")


    # --------------------------------------------------------
    # 2. Connect Python to PostgreSQL.
    #
    #    psycopg is the Python PostgreSQL database driver.
    # --------------------------------------------------------

    with psycopg.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    ) as conn:

        # ----------------------------------------------------
        # 3. Open a database cursor.
        #
        #    A cursor allows Python to send SQL commands
        #    to PostgreSQL.
        # ----------------------------------------------------

        with conn.cursor() as cur:

            # ------------------------------------------------
            # 4. Insert each meter.
            #
            #    We deliberately store only the three fields
            #    required by the assignment.
            # ------------------------------------------------

            for meter in meters:

                cur.execute(
                    """
                    INSERT INTO meters
                        (meter_id, region, customer_type)
                    VALUES
                        (%s, %s, %s)
                    ON CONFLICT (meter_id) DO NOTHING;
                    """,
                    (
                        meter["meter_id"],
                        meter["region"],
                        meter["customer_type"],
                    ),
                )

        # ----------------------------------------------------
        # 5. The 'with' block commits the transaction when
        #    everything succeeds.
        #
        #    If an error occurs, PostgreSQL rolls back the
        #    transaction instead of leaving a partial load.
        # ----------------------------------------------------


    print("Meter population completed successfully.")


if __name__ == "__main__":
    main()