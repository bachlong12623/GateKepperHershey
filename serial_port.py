import serial
import threading
import serial.tools.list_ports

class DM8050E:
    def __init__(self, port, baudrate=115200, timeout=1):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.connection = None
        self.read_thread = None
        self.reading = False

    def connect(self):
        try:
            if self.connection and self.connection.is_open:
                self.connection.close()
            self.connection = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout
            )
            if self.connection.is_open:
                print(f"Connected to {self.port} at {self.baudrate} baud.")
                self.start_reading()
        except serial.SerialException as e:
            print(f"Failed to connect to {self.port}: {e}")
        except PermissionError as e:
            print(f"Permission denied when trying to connect to {self.port}: {e}")

    def disconnect(self):
        self.stop_reading()
        if self.connection and self.connection.is_open:
            self.connection.close()
            print(f"Disconnected from {self.port}.")

    def send_command(self, command):
        if self.connection and self.connection.is_open:
            self.connection.write(command.encode())
            response = self.connection.readline().decode().strip()
            return response
        else:
            print("Connection is not open.")
            return None

    def start_reading(self):
        self.reading = True
        self.read_thread = threading.Thread(target=self.read_data)
        self.read_thread.start()

    def stop_reading(self):
        self.reading = False
        if self.read_thread:
            self.read_thread.join()

    def read_data(self):
        """
        Reads data from the serial connection in a separate thread.

        This function is started as a separate thread by start_reading() and
        stopped by stop_reading(). It reads data from the serial connection and
        prints it to the console.

        If an error occurs while reading from the serial connection, the
        reading loop is stopped and the error is printed to the console.
        """
        while self.reading:
            if self.connection and self.connection.is_open:
                try:
                    data = self.connection.readline().decode().strip()
                    if data:
                        print(f"Received: {data}")
                except serial.SerialException as e:
                    print(f"Error reading from {self.port}: {e}")
                    self.reading = False
def auto_detect_port():
    ports = serial.tools.list_ports.comports()
    for port in ports:
        print(f"Found port: {port.device}")
    return ports[0].device if ports else None
if __name__ == "__main__":
    port = auto_detect_port()
    if port:
        dm8050e = DM8050E(port=port)
        dm8050e.connect()
        
        # Example command to send to the DM8050E device
        response = dm8050e.send_command('*IDN?')
        if response:
            print(f"Response: {response}")
        
        # Keep the program running to read data
        try:
            while True:
                pass
        except KeyboardInterrupt:
            print("Exiting...")
        
        dm8050e.disconnect()
    else:
        print("No serial ports found.")