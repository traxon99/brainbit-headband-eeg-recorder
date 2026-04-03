from time import sleep, time
import csv
import os
from datetime import datetime
from neurosdk.scanner import Scanner
from neurosdk.cmn_types import SensorFamily, SensorCommand

OUTPUT_DIR = "./"
os.makedirs(OUTPUT_DIR, exist_ok=True)
OUTPUT_CSV = os.path.join(OUTPUT_DIR, f"brainbit_eeg_{datetime.now():%Y-%m-%d_%H-%M-%S}.csv")

RECORD_SECONDS = 30  # Adjust recording time here


def main():
    scanner = Scanner([SensorFamily.SensorLEBrainBit2])

    print("Scanning for devices for 10 seconds...")
    scanner.start()
    sleep(10)
    scanner.stop()

    sensors = scanner.sensors()
    if not sensors:
        print("No devices found.")
        return

    sensor_info = sensors[0]
    print("Connecting to:", sensor_info)

    sensor = scanner.create_sensor(sensor_info)
    print("Connected")

    start_time = time()
    rows_written = 0

    with open(OUTPUT_CSV, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["t_sec", "pack_num", "marker", "ch1", "ch2", "ch3", "ch4"])

        def on_signal(sensor_obj, data):
            nonlocal rows_written
            if not data:
                return

            t_now = time() - start_time

            for sample in data:
                writer.writerow([
                    round(t_now, 6),
                    sample.PackNum,
                    sample.Marker,
                    sample.Ch1,
                    sample.Ch2,
                    sample.Ch3,
                    sample.Ch4,
                ])
                rows_written += 1

        sensor.signalDataReceived = on_signal

        print(f"Recording EEG for {RECORD_SECONDS} seconds...")
        sensor.exec_command(SensorCommand.StartSignal)

        sleep(RECORD_SECONDS)

        print("Finished recording. Disconnecting...")

        sensor.signalDataReceived = None

    del sensor
    del scanner

    print(f"Saved {rows_written} rows to: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
