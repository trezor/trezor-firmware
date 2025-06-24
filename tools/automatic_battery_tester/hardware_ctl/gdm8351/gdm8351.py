
import pyvisa
import time

class GDM8351:

    def __init__(self):

        self.rm = pyvisa.ResourceManager()

        # List available resources, let the user to pick one from the list
        available_devices = {}
        device_count = 0

        print("Available devices:")
        for r_name in self.rm.list_resources():
            if("/dev/ttyACM" in r_name):
                device_count += 1
                available_devices[device_count] = r_name
                print(f"    [{device_count}]: {r_name}")


        self.device_connected = False
        while not self.device_connected:
            input_device_id = input("Digital multimeter GDM8351: Select VCP port number (or Q to quit the selection): ")

            if(input_device_id.lower() == 'q'):
                print("Exiting device selection.")
                return

            for device_id, device_name in available_devices.items():
                if int(input_device_id) == device_id:
                    print(f"Connecting to {device_name}...")

                    try:
                        self.device = self.rm.open_resource(device_name)
                        self.device_id = self.device.query("*IDN?")
                        if("GDM8351" in self.device_id):
                            print("Device connected successfully.")
                        else:
                            self.device.close()
                            print("Connected device is not a GDM8351. Please check the device ID.")
                            continue

                        self.device_connected = True
                    except Exception as e:
                        print(f"Failed to connect to {device_name}: {e}")

                    break

    def get_id(self):
        if self.device is None or not self.device_connected:
            raise Exception("Device not connected.")

        return self.device.query("*IDN?")

    def configure_temperature_sensing(self, sensor_type="K", junction_temp_deg=29.0):

        if sensor_type not in ["K", "J", "T"]:
            raise ValueError("Invalid sensor type. Use 'K', 'J', or 'T'.")

        if junction_temp_deg < 0 or junction_temp_deg > 50:
            raise ValueError("Junction temperature must be between 0 and 50 degrees Celsius.")

        try:
            junction_temp_deg = float(junction_temp_deg)
        except ValueError:
            raise ValueError("Junction temperature must be a number.")

        try:
            self.device.write(f"CONF:TEMP:TCO {sensor_type}")
            self.device.write(f"SENS:TEMP:RJUN:SIM {junction_temp_deg:.1f}")
        except Exception as e:
            raise Exception(f"Failed to configure temperature sensing: {e}")

        return

    def read_temperature(self):

        if self.device is None or not self.device_connected:
            raise Exception("Device not connected.")

        try:
            return float(self.device.query("MEAS:TEMP:TCO?"))
        except Exception as e:
            raise Exception(f"Failed to read temperature: {e}")

    def log_temperature(self, output_directory, test_time_id, verbose=False):

        # Log file name format:
        # > external_temp.<time_identifier>.csv
        # Example: external_temp.2506091307.csv

        file_path = output_directory / f"external_temp.{test_time_id}.csv"

        try:
            temp = self.read_temperature()
        except Exception as e:
            print(f"Failed to read temperature: {e}")
            return

        if not file_path.exists():
            # creat a file header
            with open(file_path, 'w') as f:
                f.write("time,temperature\n")

        with open(file_path, 'a') as f:
            f.write(str(time.time()) + "," + str(temp) + "\n")

        if verbose:
            print(f"GDM8351 temperature: {temp}°C")


    def close(self):
        if self.device is not None and self.device_connected:
            try:
                self.device.close()
                print("GDM8351 connection closed.")
            except Exception as e:
                print(f"GDM8351 Failed to close connection: {e}")


