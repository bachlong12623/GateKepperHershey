import serial
import threading
import serial.tools.list_ports
import time

class BarcodeScanner:
    def __init__(self, port, baudrate=115200, timeout=1):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.connection = None
        self.read_thread = None
        self.reading = False

    def connect(self):
        """Kết nối tới máy quét mã vạch qua cổng serial."""
        try:
            if self.connection and self.connection.is_open:
                self.connection.close()
            self.connection = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout
            )
            if self.connection.is_open:
                print(f"✅ Đã kết nối {self.port} với baudrate {self.baudrate}")
                time.sleep(0.5)
                self.connection.reset_input_buffer()  # Xóa buffer trước khi bắt đầu đọc
                #self.start_reading()
        except serial.SerialException as e:
            print(f"❌ Không thể kết nối {self.port}: {e}")
        except PermissionError as e:
            print(f"⛔ Quyền bị từ chối khi kết nối {self.port}: {e}")

    def disconnect(self):
        """Ngắt kết nối an toàn."""
        self.stop_reading()
        if self.connection and self.connection.is_open:
            self.connection.close()
            print(f"🔌 Đã ngắt kết nối {self.port}.")

    def send_command(self, command):
        """Gửi lệnh và nhận phản hồi từ máy quét."""
        if self.connection and self.connection.is_open:
            try:
                self.connection.write(command.encode())
                response = self.connection.readline().decode().strip()
                return response
            except serial.SerialException as e:
                print(f"⚠️ Lỗi gửi lệnh: {e}")
                return None
        else:
            print("⚠️ Kết nối chưa mở.")
            return None

    def start_reading(self):
        """Bắt đầu luồng đọc dữ liệu."""
        self.reading = True
        self.read_thread = threading.Thread(target=self.read_data, daemon=True)
        self.read_thread.start()

        # Chờ 100ms để đảm bảo dữ liệu được gửi đầy đủ
        time.sleep(0.1)

        # Đọc bỏ dòng đầu tiên nếu có
        if self.connection and self.connection.is_open:
            try:
                if self.connection.in_waiting:  # Kiểm tra nếu có dữ liệu sẵn trong buffer
                    garbage_line = self.connection.readline().decode(errors="ignore").strip()
                    print(f"⚠️ Bỏ qua dòng rác đầu tiên: {garbage_line}")
            except serial.SerialException:
                pass

    def stop_reading(self):
        """Dừng luồng đọc dữ liệu."""
        self.reading = False
        if self.read_thread:
            self.read_thread.join()

    def read_data(self):
        """Đọc dữ liệu từ serial, đảm bảo không mất ký tự đầu tiên."""
        buffer = ""
        while self.reading:
            if self.connection and self.connection.is_open:
                try:
                    # Chờ dữ liệu nếu chưa có
                    while self.connection.in_waiting == 0:
                        time.sleep(0.01)

                    data = self.connection.read(self.connection.in_waiting).decode(errors="ignore")
                    if data:
                        buffer += data
                        while "\n" in buffer or "\r" in buffer:
                            line, buffer = buffer.split("\n", 1) if "\n" in buffer else buffer.split("\r", 1)
                            print(f"📦 Nhận được: {line.strip()}")
                except serial.SerialException as e:
                    print(f"⚠️ Lỗi khi đọc từ {self.port}: {e}")
                    self.reading = False

def auto_detect_port():
    """Tự động tìm cổng serial khả dụng."""
    ports = serial.tools.list_ports.comports()
    if not ports:
        print("🚫 Không tìm thấy cổng serial.")
        return None
    for port in ports:
        print(f"🔍 Tìm thấy cổng: {port.device}")
    return ports[0].device  # Chọn cổng đầu tiên

if __name__ == "__main__":
    port = auto_detect_port()
    if port:
        scanner = BarcodeScanner(port=port)
        scanner.connect()

        # Gửi lệnh test đến máy quét
        response = scanner.send_command('*IDN?')
        if response:
            print(f"📢 Phản hồi: {response}")

        # Chạy chương trình cho đến khi người dùng dừng
        try:
            while True:
                time.sleep(0.1)  # Giảm tải CPU
        except KeyboardInterrupt:
            print("\n🛑 Đang thoát...")

        scanner.disconnect()
    else:
        print("❌ Không có cổng nào để kết nối.")
