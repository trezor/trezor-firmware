
import sys
import time
from pathlib import Path
from serial.tools import list_ports
from hardware_ctl.gdm8351 import GDM8351
from dut import Dut


output_directory = Path("single_capture_test_results")
test_description = "non_specified_test"
temp_description = "ambient"


"""
This script will connect to a signle DUT over VCP port and will run a continous
log of the power manager data (continously calls pm-report command) into the
log file. User can also select to log the temepertature readings from an
external thermocouple sensor connected to the GDM8351 multimeter.
"""

def main():

    print("**********************************************************")
    print("  DUT port selection ")
    print("**********************************************************")

    ports = list_ports.comports()

    available_ports = {}
    port_count = 0
    print("Available VCP ports:")
    for port in ports:
        if "ACM" in port.device:
            port_count += 1
            available_ports[port_count] = port.device
            print(f"    [{port_count}]: {port.device} - {port.description}")

    if port_count == 0:
        print("No device conneceted. Exiting.")
        return

    dut_port_selection = input("Select VCP port number (or Q to quit the selection): ")

    if dut_port_selection.lower() == 'q':
        print("Exiting script.")
        sys.exit(0)

    selected_port = None
    for port_id, port_name in available_ports.items():
        if int(dut_port_selection) == port_id:
            selected_port = port_name
            break

    try:
        dut = Dut(name="Trezor", usb_port=selected_port)
    except Exception as e:
        print(f"Failed to initialize DUT on port {selected_port}: {e}")
        sys.exit(1)
    # Initialize DUT


    print("**********************************************************")
    print("  GDM8351 port selection (temp measurement) ")
    print("**********************************************************")

    # Initialize the GDM8351 multimeter
    gdm8351 = GDM8351()

    # Get the device ID to confirm connection
    try:
        device_id = gdm8351.get_id()
        print(f"Connected to device: {device_id}")
    except Exception as e:
        print(f"Error getting device ID: {e}")
        return

    # Configure temperature sensing
    try:
        gdm8351.configure_temperature_sensing(sensor_type="K", junction_temp_deg=29.0)
        print("Temperature sensing configured successfully.")
    except ValueError as ve:
        print(f"Configuration error: {ve}")
    except Exception as e:
        print(f"Error configuring temperature sensing: {e}")


    # Creat test time ID
    test_time_id = f"{time.strftime('%y%m%d%H%M')}"

    # Create output data directory
    try:
        output_directory.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print("Failed to create output directory:", e)
        sys.exit(1)


    #########################################################################
    # Test setup section
    #########################################################################

    dut.set_soc_limit(100)
    dut.set_backlight(100)
    dut.enable_charging()

    #########################################################################
    # Main test loop
    #########################################################################
    try:

        while True:

            dut.log_data(output_directory=output_directory,
                         test_time_id=test_time_id,
                         test_scenario="single_capture",
                         test_phase=test_description,
                         temp=temp_description,
                         verbose=True)

            # Read temperature from GDM8351
            gdm8351.log_temperature(output_directory=output_directory,
                                    test_time_id=test_time_id,
                                    verbose=True)

            time.sleep(1)


    except KeyboardInterrupt:
        print("Test execution interrupted by user (Ctrl+C)")
    except Exception as e:
        print(f"FATAL ERROR during test execution: {e}")
    finally:

        dut.close()
        gdm8351.close()


if __name__ == "__main__":
    main()









