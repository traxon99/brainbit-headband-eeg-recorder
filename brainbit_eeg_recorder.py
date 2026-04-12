from time import sleep, time
import csv
import os
from datetime import datetime
from neurosdk.scanner import Scanner
from neurosdk.cmn_types import SensorFamily, SensorCommand

OUTPUT_DIR = "./"
os.makedirs(OUTPUT_DIR, exist_ok=True)
OUTPUT_CSV = os.path.join(OUTPUT_DIR, f"brainbit_eeg_{datetime.now():%Y-%m-%d_%H-%M-%S}.csv")

RECORD_SECONDS = 60  # Adjust recording time here
SCAN_SECONDS = 10 # Adjust scan time here

def main():
    scanner = Scanner([SensorFamily.LEBrainBit2])

    print(f"Scanning for devices for {SCAN_SECONDS} seconds...")
    scanner.start()
    sleep(SCAN_SECONDS)
    scanner.stop()

    sensors = scanner.sensors()
    if not sensors:
        print("No devices found.")
        return

    print(f"Found {len(sensors)} device(s):")
    for i, s in enumerate(sensors):
        print(f"[{i}] {s}")
        
    sensor_info = sensors[0]
    print("Connecting to:", sensor_info)

    sensor = scanner.create_sensor(sensor_info)
    print("Connected")

    channel_map = {}
    print("Supported channels:")
    for ch in sensor.supported_channels:
        ch_name = getattr(ch, "Name", None)
        ch_num = getattr(ch, "Num", None)
        ch_id = getattr(ch, "Id", None)
        print(f"  Name={ch_name}, Num={ch_num}, Id={ch_id}")

        if ch_name is not None and ch_num is not None:
            channel_map[ch_name] = ch_num

    print("Channel map:", channel_map)

    start_time = time()
    rows_written = 0
    batches_received = 0
    
    with open(OUTPUT_CSV, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["t_sec", "pack_num", "marker", "ch1", "ch2", "ch3", "ch4"])
        f.flush()

        def on_signal(sensor_obj, data):
            nonlocal rows_written, batches_recieved
            
            if not data:
                return

            batches_received += 1
            batch_time = time() - start_time
            print(f"Received batch #{batches_received}: {len(data)} samples at t={batch_time:.3f}s")

            for sample in data:
                t_now = time() - start_time

                samples = getattr(sample, "Samples", None)
                if samples is None:
                    print("Sample missing Samples field:", dir(sample))
                    continue

                # Prefer known BrainBit channel names if available
                preferred = ["O1", "O2", "T3", "T4"]
                row_values = []

                for name in preferred:
                    if name in channel_map and channel_map[name] < len(samples):
                        row_values.append(samples[channel_map[name]])
                    else:
                        row_values.append("")

                # Fallback: just use the first 4 sample values
                if all(v == "" for v in row_values):
                    row_values = list(samples[:4])
                    while len(row_values) < 4:
                        row_values.append("")
                        
                writer.writerow([
                    round(t_now, 6),
                    getattr(sample, "PackNum", ""),
                    getattr(sample, "Marker", ""),
                    row_values[0],
                    row_values[1],
                    row_values[2],
                    row_values[3],
                ])
                rows_written += 1
                
            f.flush()

        sensor.signalDataReceived = on_signal
        try:
            print(f"Recording EEG for {RECORD_SECONDS} seconds...")
            sensor.exec_command(SensorCommand.StartSignal)
            print("StartSignal sent")
    
            sleep(RECORD_SECONDS)
    
            print("Finished recording")
        finally:
            print("Stopping signal and disconnecting...")
            try:
                sensor.exec_command(SensorCommand.StopSignal)
                print("StopSignal sent")
            except Exception as e:
                print("StopSignal error:", repr(e))
                
            sensor.signalDataReceived = None

    del sensor
    del scanner

    print(f"Saved {rows_written} rows to: {OUTPUT_CSV}")
    print(f"Total batches received: {batches_received}")

if __name__ == "__main__":
    main()
