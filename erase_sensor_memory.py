import time
import serial
import adafruit_fingerprint

# UART setup for fingerprint sensor
uart = serial.Serial("COM4", baudrate=57600, timeout=2)
time.sleep(1)  # Adding delay to ensure the sensor is ready
finger = adafruit_fingerprint.Adafruit_Fingerprint(uart)

# Function to delete all stored fingerprints
def delete_all_fingerprints():
    print("Deleting all stored fingerprints...")
    for location in range(1, 128):  # Loop through all possible storage locations
        i = finger.delete_model(location)
        if i == adafruit_fingerprint.OK:
            print(f"Fingerprint model at location {location} deleted.")
        else:
            print(f"Failed to delete fingerprint model at location {location}.")

    print("All fingerprints deleted.")

# Main program
if __name__ == "__main__":
    delete_all_fingerprints()

    # Close UART connection when done
    uart.close()

