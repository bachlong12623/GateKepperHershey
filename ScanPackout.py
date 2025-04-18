import configparser
from time import sleep
import time
from PyQt5 import uic
from PyQt5.QtWidgets import QApplication, QTableWidget, QTableWidgetItem, QMessageBox, QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QSpinBox
from PyQt5.QtCore import Qt, QDate, QTimer, pyqtSignal, QObject, QThread
from PyQt5 import QtGui
import sys
import psycopg2
from datetime import datetime

import pdb
import serial
import verify as verify
import threading
from serial_port import BarcodeScanner, auto_detect_port

Ui_MainWindow, QtBaseClass = uic.loadUiType("MainWindow.ui")


class PasswordDialog(QDialog):
    def __init__(self, parent=None, serial_number="", inner_code="", position="", scanner=None):
        super(PasswordDialog, self).__init__(parent)
        self.setWindowTitle("Enter Password")
        self.setModal(True)
        self.setFixedSize(700, 500)  # Increase the size of the dialog
        self.scanner = scanner  # Pass the scanner object to the dialog

        layout = QVBoxLayout()

        self.setStyleSheet("background-color: blue;")

        self.info_label = QLabel(f"Serial đã bị trùng\nSerial Number: {serial_number}\nInner Code: {inner_code}\nVị trí: {position}")
        self.info_label.setStyleSheet("color: yellow; font-size: 18px;")  # Set the text color to yellow and increase font size
        layout.addWidget(self.info_label)

        self.label = QLabel("Quét mật khẩu để tiếp tục:")
        self.label.setStyleSheet("color: yellow; font-size: 20px;")  # Set the text color to yellow and increase font size
        layout.addWidget(self.label)

        self.password_display = QLineEdit()  # Display scanned password
        self.password_display.setEchoMode(QLineEdit.Password)  # Hide password input
        self.password_display.setStyleSheet("font-size: 24px; padding: 10px; color: white;")
        self.password_display.setReadOnly(True)  # Make it read-only
        layout.addWidget(self.password_display)

        self.submit_button = QPushButton("Submit")
        self.submit_button.setStyleSheet("font-size: 24px; padding: 10px; background-color: yellow; color: blue;")
        self.submit_button.clicked.connect(self.accept)
        layout.addWidget(self.submit_button)
        self.setLayout(layout)

        # Timer for blinking background
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.blink_background)
        self.timer.start(500)  # Blink every 500 milliseconds

        self.blink_state = False

        # Connect scanner signal
        if self.scanner:
            self.scanner.data_received.connect(self.handle_scanner_input)

        self.scanned_password = ""

        # Add flag to check if this is bypass mode
        self.is_bypass_mode = serial_number == "" and inner_code == "" and position == ""

        # Only show error info if not in bypass mode
        if not self.is_bypass_mode:
            self.info_label.setText(f"Serial đã bị trùng\nSerial Number: {serial_number}\nInner Code: {inner_code}\nVị trí: {position}")

    def handle_scanner_input(self, data):
        """Handle input from the scanner."""
        self.scanned_password = data.strip()
        self.password_display.setText(self.scanned_password)

    def get_password(self):
        return self.scanned_password

    def closeEvent(self, event):
        # Allow closing if in bypass mode
        if self.is_bypass_mode:
            event.accept()
        else:
            QMessageBox.critical(self, "Error", "Vui lòng nhập mật khẩu.")
            event.ignore()

    def blink_background(self):
        if self.blink_state:
            self.setStyleSheet("background-color: red;")
        else:
            self.setStyleSheet("background-color: blue;")
        self.blink_state = not self.blink_state

class InspectionDialog(QDialog):
    def __init__(self, parent=None):
        super(InspectionDialog, self).__init__(parent)
        uic.loadUi("InspectionDialog.ui", self)
        
    def fetch_data(self, cursor):
        self.label.setText("Danh sách sản phẩm NG trùng Serial")
        cursor.execute("SELECT * FROM i_packing_duplicate WHERE scan_time >= %s ORDER BY id DESC", (datetime.now().strftime("%Y-%m-%d"),))
        records = cursor.fetchall()
        self.table.setRowCount(len(records))
        for i, record in enumerate(records):
            self.table.setItem(i, 0, QTableWidgetItem(str(record[0])))
            self.table.setItem(i, 1, QTableWidgetItem(str(record[3])))
            self.table.setItem(i, 2, QTableWidgetItem(str(record[4])))
            self.table.setItem(i, 3, QTableWidgetItem(str(record[5])))
            self.table.setItem(i, 4, QTableWidgetItem(str(record[6])))
            self.table.setItem(i, 5, QTableWidgetItem(str(record[7])))
            self.table.setItem(i, 6, QTableWidgetItem(str(record[8])))
            self.table.setItem(i, 7, QTableWidgetItem(str(record[9])))
        self.table.resizeColumnsToContents()  # Adjust column width to fit content
    
    def show_ng(self, cursor):
        self.label.setText("Danh sách sản phẩm NG")
        """Fetch and display NG records."""
        cursor.execute("SELECT * FROM i_packing WHERE result = FALSE ORDER BY id DESC")
        records = cursor.fetchall()
        self.table.setRowCount(len(records))
        for i, record in enumerate(records):
            self.table.setItem(i, 0, QTableWidgetItem(str(record[0])))
            self.table.setItem(i, 1, QTableWidgetItem(str(record[3])))
            self.table.setItem(i, 2, QTableWidgetItem(str(record[4])))
            self.table.setItem(i, 3, QTableWidgetItem(str(record[5])))
            self.table.setItem(i, 4, QTableWidgetItem(str(record[6])))
            self.table.setItem(i, 5, QTableWidgetItem(str(record[7])))
            self.table.setItem(i, 6, QTableWidgetItem(str(record[8])))
            self.table.setItem(i, 7, QTableWidgetItem(str(record[9])))
        self.table.resizeColumnsToContents()  # Adjust column width to fit content

class SerialReader(QObject):
    data_received = pyqtSignal(str)

    def __init__(self, barcode_scanner):
        super().__init__()
        self.barcode_scanner = barcode_scanner
    def read_serial_data(self):
        buffer = ""
        try:
            while True:
                sleep(0.1)
                if self.barcode_scanner.connection and self.barcode_scanner.connection.is_open:
                    try:
                        while self.barcode_scanner.connection.in_waiting > 0:
                            data = self.barcode_scanner.connection.read(self.barcode_scanner.connection.in_waiting).decode(errors="ignore")
                            if data:
                                print(data)
                                buffer += data
                                while '\r' in buffer or '\n' in buffer:
                                    line, buffer = buffer.split("\n", 1) if "\n" in buffer else buffer.split("\r", 1)
                                    self.data_received.emit(line.strip())
                    except serial.SerialException as e:
                        print(f"Error reading from serial port: {e}")
                        break
        except Exception as e:
            print(e)

class MainWindow(QtBaseClass, Ui_MainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setupUi(self)

        # Connect to database PostgreSQL
        self.read_settings()
        try:
            self.database_glovia_conn = psycopg2.connect(host=self.database_ip, port=self.database_port, database=self.database_glovia, user=self.database_user, password=self.database_password)
            self.cursor_glovia = self.database_glovia_conn.cursor()
            
            self.database_spk_conn = psycopg2.connect(host=self.database_ip, port=self.database_port, database=self.database_spk, user=self.database_user, password=self.database_password)
            self.cursor_spk = self.database_spk_conn.cursor()
            
            self.lb_server.setText("OK")
            self.lb_server.setStyleSheet("background-color: rgb(0, 200, 0); color: rgb(255, 255, 255);")
        except Exception as e:
            self.lb_server.setText("NG")
            self.lb_server.setStyleSheet("background-color: rgb(200, 0, 0); color: rgb(255, 255, 255);")
            print(e)
        
        # Set dateBox to the first day of the current month and year
        today = QDate.currentDate()
        first_day_of_month = QDate(today.year(), today.month(), 1)
        self.dateScan.setDate(first_day_of_month)
        self.line.setCurrentIndex(-1)
        self.modelScan.setCurrentIndex(-1)
        self.shift_scan.setCurrentIndex(-1)
        
        self.bypass_vendorcode = False


        # Enable line when date is chosen
        self.dateScan.dateChanged.connect(lambda: self.line.setEnabled(True))

        # Enable modelScan when line is chosen
        self.line.currentIndexChanged.connect(lambda: self.modelScan.setEnabled(True) if self.line.currentIndex() != -1 else self.modelScan.setEnabled(False))

        # Enable shift_scan when modelScan is chosen
        self.modelScan.currentIndexChanged.connect(self.on_model_change)

        
        
        self.shift_scan.currentIndexChanged.connect(self.verify_combobox)
        self.done_button.clicked.connect(self.clear_shift)
        
        # Set table column width
        self.judgement_na()
        
        self.inspect_button.clicked.connect(self.show_duplicate)
        self.show_ng_button.clicked.connect(self.show_ng_dialog)
        
        self.labelno1.mousePressEvent = self.on_labelno1_click

       

        QTableWidget.setColumnWidth(self.result_table, 0, 50)
        QTableWidget.setColumnWidth(self.result_table, 1, 200)
        QTableWidget.setColumnWidth(self.result_table, 2, 100)
        QTableWidget.setColumnWidth(self.result_table, 3, 100)
        QTableWidget.setColumnWidth(self.result_table, 4, 150)
        QTableWidget.setColumnWidth(self.result_table, 5, 600)
        try:
            # Auto-detect and initialize BarcodeScanner
            port = auto_detect_port()
            if port:
                self.barcode_scanner = BarcodeScanner(port=port)
                self.barcode_scanner.connect()

                # Initialize SerialReader
                self.serial_reader = SerialReader(self.barcode_scanner)
                self.serial_reader.data_received.connect(self.verify_string)

                # Initialize QThread
                self.thread = QThread()
                self.serial_reader.moveToThread(self.thread)
                self.thread.started.connect(self.serial_reader.read_serial_data)
                self.thread.start()
            else:
                print("No serial ports found.")
        except Exception as e:
            print(e)
    def verify_combobox(self):
        pass
    
    def on_labelno1_click(self, event):
        password_dialog = PasswordDialog(
            self, 
            scanner=self.serial_reader,
            # Set empty strings for other params since this is bypass mode
            serial_number="",
            inner_code="",
            position=""
        )
        
        # Update dialog appearance for bypass mode
        password_dialog.setFixedSize(400, 300)  # Smaller size for bypass mode
        password_dialog.info_label.setText("Mở chế độ bypass")
        password_dialog.info_label.setStyleSheet("color: yellow; font-size: 24px;")
        password_dialog.closeEvent = lambda x: x.accept()  # Allow closing

        # Read password from config.ini
        config = configparser.ConfigParser()
        config.read('config.ini')
        stored_password = config['Settings'].get('password')

        if password_dialog.exec_() == QDialog.Accepted:
            entered_password = password_dialog.get_password()
            if entered_password in [datetime.now().strftime("%y%m%d"), stored_password]:
                self.bypass_vendorcode = True
                QMessageBox.information(self, "Success", "Bypass enabled.")
            else:
                QMessageBox.critical(self, "Error", "Incorrect password. Please try again.")
    
    def clear_shift(self):
        self.work_order.setText("")
        self.inner_code.setText("")
        self.second_inner_code.setText("")
        self.serial_number.setText("")
        self.result_table.setRowCount(0)
        self.judgement_na()
        self.line.setCurrentIndex(-1)
        self.modelScan.setCurrentIndex(-1)
        self.shift_scan.setCurrentIndex(-1)
        self.dateScan.setDate(QDate.currentDate())
        self.dateScan.setEnabled(True)
        self.line.setEnabled(False)
        self.modelScan.setEnabled(False)
        self.shift_scan.setEnabled(False)
        self.qty_inner.setText("-")
        self.qty_tray.setText("-")
    def on_model_change(self):
        if self.modelScan.currentIndex() != -1:
            self.shift_scan.setEnabled(True)
            # Read settings from config.ini when model changes
            config = configparser.ConfigParser()
            config.read('config.ini')
            self.tray_quantity = config[str(self.modelScan.currentText())]['tray_quantity']
            self.qty_tray.setText(self.tray_quantity)
        else:
            self.shift_scan.setEnabled(False)
    def clear_data(self):
        self.inner_code.setText("")
        self.second_inner_code.setText("")
        self.serial_number.setText("")
        self.result_table.setRowCount(0)
        self.judgement_na()
        self.bypass_vendorcode = False
    def verify_string(self, string):
        # Check if PasswordDialog is open
        if any(isinstance(widget, PasswordDialog) for widget in QApplication.instance().topLevelWidgets()):
            return  # Do not verify string if PasswordDialog is open

        if self.work_order.text() == "":
            self.verify_work_order(string)
        elif self.inner_code.text() == "":
            self.verify_inner_code(string)
        elif self.second_inner_code.text() == "":
            self.verify_2ndinner_code(string)
        else:
            self.verify_serial_number(string)
    def show_duplicate(self):        
        inspection_dialog = InspectionDialog(self)
        inspection_dialog.fetch_data(self.cursor_spk)
        inspection_dialog.exec_()
    def  show_ng_dialog(self):
        inspection_dialog = InspectionDialog(self)
        inspection_dialog.show_ng(self.cursor_spk)
        inspection_dialog.exec_()

    def read_settings(self):
        # Read settings from file
        self.config = configparser.ConfigParser()
        self.config.read('config.ini')
        self.database_ip = self.config.get('Database', 'database_ip')
        self.database_port = self.config.get('Database', 'database_port')
        self.database_glovia = self.config.get('Database', 'database_glovia')
        self.database_spk = self.config.get('Database', 'database_spk')
        self.database_user = self.config.get('Database', 'database_user')
        self.database_password = self.config.get('Database', 'database_password')
        # self.line = self.config.get('Database', 'line')
        # self.model = self.config.get('Database', 'model')
    
    def verify_serial_number(self, serial_number):
        """
        Verifies the provided serial number against the current work order and database records.
        Args:
            serial_number (str): The serial number to be verified.
        Behavior:
            - Checks if the serial number belongs to the current work order (`self.en_wo`).
            - Queries the database to determine if the serial number already exists in the `i_packing` table.
                - If a duplicate is found, handles the duplicate serial number.
            - Queries the `i_output` and `i_klippel` tables for additional validation.
            - Checks the count of items in the `i_packing` table with the same inner code.
            - If the serial number is valid and matches the criteria:
                - Inserts a new packing record.
                - Updates the UI to indicate success.
                - Clears data if the inner quantity reaches the specified limit.
            - If the serial number is invalid or does not match:
                - Displays an error message and updates the UI to indicate failure.
        Exceptions:
            - Catches and logs any exceptions that occur during the process.
            - Displays an error message if the verification fails due to missing data or other issues.
        Raises:
            None
        """
      
        if serial_number[:5] != self.en_wo:
            self.judgement_ng()
            QMessageBox.critical(self, "Error", "Xác minh số Serial không thành công. Hàng không thuộc work order này.")
            return

        try:
            self.cursor_spk.execute("SELECT * FROM i_packing WHERE serial = %s", (serial_number,))
            record = self.cursor_spk.fetchone()
            if record:
                self.handle_duplicate_serial(serial_number, record)
                return

            self.cursor_spk.execute("SELECT * FROM i_output WHERE id = %s", (serial_number,))
            record = self.cursor_spk.fetchone()
            self.cursor_spk.execute("SELECT * FROM i_klippel WHERE id = %s", (serial_number,))
            klippel_record = self.cursor_spk.fetchone()
            self.cursor_spk.execute("SELECT * FROM p_output WHERE id = %s", (serial_number,))
            p_output_record = self.cursor_spk.fetchone()
            if p_output_record:
                date_code = p_output_record[2]
                self.cursor_spk.execute("SELECT COUNT(*) FROM i_packing WHERE inner_code = %s", (self.inner_code.text(),))
                inner_quantity = self.cursor_spk.fetchone()[0]

                if not (date_code[0] == self.inner_date_code[3] and 
                        date_code[1] == 'V' and 
                        {'1': '01', '2': '02', '3': '03', '4': '04', '5': '05', 
                         '6': '06', '7': '07', '8': '08', '9': '09', 'O': '10', 
                         'N': '11', 'D': '12'}.get(date_code[2], '') == self.inner_date_code[4:6] and 
                        date_code[3:5] == self.inner_date_code[6:8]):
                    self.judgement_ng()
                    QMessageBox.critical(self, "Error", "Xác minh Serial number không thành công. Date code không khớp.")
                    return

            if record and record[2]:
                if inner_quantity >= int(self.innner_quantity):
                    self.clear_data()
                    return
                self.insert_packing_record(serial_number, klippel_record, inner_quantity)
                self.judgement_na()
                sleep(0.1)
                self.judgement_ok()
                self.show_data()
                self.serial_number.setStyleSheet("background-color: rgb(0, 200, 0); color: rgb(255, 255, 255);")
                self.serial_number.setText(serial_number)
                if inner_quantity >= int(self.innner_quantity)-1:
                    self.clear_data()
            else:
                self.judgement_ng()
                QMessageBox.critical(self, "Error", "Xác minh Serial number không thành công. Serial number không khớp.")
        except Exception as e:
            print(e)
            self.judgement_ng()
            QMessageBox.critical(self, "Error", "Xác minh số Serial không thành công. Không tìm thấy dữ liệu")

    def handle_duplicate_serial(self, serial_number, record):
        password_dialog = PasswordDialog(
            self,
            serial_number=serial_number,
            inner_code=self.inner_code.text(),
            position=str(record[0]),
            scanner=self.serial_reader  # Pass the scanner object
        )

        # Read password from config.ini
        config = configparser.ConfigParser()
        config.read('config.ini')
        stored_password = config['Settings'].get('password')  

        while True:
            if password_dialog.exec_() == QDialog.Accepted:
                entered_password = password_dialog.get_password()
                if entered_password in [datetime.now().strftime("%y%m%d"), stored_password]:
                    QMessageBox.critical(self, "Error", "Trùng số Serial.")
                    self.insert_duplicate_record(serial_number, record)
                    self.show_data()
                    break
                else:
                    QMessageBox.critical(self, "Error", "Sai mật khẩu. Vui lòng nhập lại.")
            else:
                QMessageBox.critical(self, "Error", "Yêu cầu nhập mật khẩu.")

    def insert_packing_record(self, serial_number, klippel_record, inner_quantity):
        self.cursor_spk.execute(
            """
            INSERT INTO i_packing (
                id, date, line, model, shift, inner_code, serial, klippel, result, scan_time
            ) VALUES (%s,%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                inner_quantity + 1, self.dateScan.date().toString("yyyy-MM-dd"), self.line.currentText(), self.modelScan.currentText(), self.shift_scan.currentText(), self.inner_code.text(),
                serial_number, klippel_record[8], True, datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        )
        self.database_spk_conn.commit()

    def insert_duplicate_record(self, serial_number, record):
        self.cursor_spk.execute(
            """
            INSERT INTO i_packing_duplicate (
                id, date, line, model, shift, inner_code, serial, klippel, result, scan_time
            ) VALUES (%s,%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                record[0], record[1], record[2], record[3], record[4], record[5], serial_number, record[7], False, datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        )
        self.database_spk_conn.commit()
    def verify_work_order(self, work_order):
        try:
            wo = work_order[:-5]
            line = work_order[-4:]
            self.cursor_glovia.execute("SELECT * FROM glovia_info WHERE wo = %s and line_wo = %s ", (wo, line))
            record = self.cursor_glovia.fetchone()
            if record is not None:
                self.en_wo = record[1]
                self.sys_wo = record[6]
                self.model = record[9]
                if str(self.model) != str(self.modelScan.currentText()):
                    self.judgement_ng()
                    QMessageBox.critical(self, "Error", "Xác minh Work Order không thành không. Model không khớp.")
                    return
                self.judgement_ok()
                self.work_order.setText(work_order)
                #select newest record from i_packing
                self.cursor_spk.execute("SELECT * FROM i_packing WHERE LEFT(serial, 5) = %s ORDER BY scan_time DESC LIMIT 1", (self.en_wo,))
                record = self.cursor_spk.fetchone()
                if record:
                    inner_code = record[5]
                    print(inner_code)
                    print(record[6])
                    inner_quantity = inner_code.split('$')[-1]
                    self.cursor_spk.execute("SELECT COUNT(*) FROM i_packing WHERE inner_code = %s", (inner_code,))
                    count = self.cursor_spk.fetchone()[0]
                    if count < int(inner_quantity):
                        if(self.verify_inner_code(inner_code)):
                            self.verify_2ndinner_code(inner_code)
                self.load_innerID()

            else:
                self.work_order.setText("")
                self.judgement_ng()
                QMessageBox.critical(self, "Error", "Xác minh Work order không thành cômg. Không tìm thấy work order.")
        except Exception as e:
            print(e)
            self.judgement_ng()
            QMessageBox.critical(self, "Error", "Xác minh Work order không thành cômg. Không tìm thấy work order.")
    def load_innerID(self):
        self.cursor_spk.execute("""
                                        SELECT *
                                        FROM i_packing
                                        WHERE SUBSTRING(inner_code FROM 8 FOR 10) ~ '^[0-9]+$'
                                        ORDER BY CAST(SUBSTRING(inner_code FROM 8 FOR 10) AS BIGINT) DESC
                                        LIMIT 1;
                                        """)
        record = self.cursor_spk.fetchone()
        id = record[5][7:17]
        self.inner_id.setText(f'Inner ID: {id}')
    def verify_inner_code(self, code):
        code_parts = code.split('$')
        if len(code_parts) < 7:
            self.judgement_ng()
            QMessageBox.critical(self, "Error", "Xác minh code thất bại. Sai Format Inner.")
            return False

        QR = verify.QRCode(code, self.sys_wo)
        if not QR.is_valid_code():
            self.judgement_ng()
            QMessageBox.critical(self, "Error", "Xác minh code thất bại. Inner code không đúng.")
            return False

        if self.verify_vendercode(code_parts[0]):
            # self.innner_quantity = QR.quantity
            self.inner_quantity = 160
            self.inner_date_code = QR.date_code
            self.qty_inner.setText(QR.quantity)
            self.inner_code.setText(code)
            return True

        self.judgement_ng()
        self.cursor_spk.execute(
            "SELECT * FROM i_packing WHERE RIGHT(LEFT(inner_code, 17), 10) = %s", 
            (code_parts[0][7:],)
        )
        record = self.cursor_spk.fetchall()
        if record:
            QMessageBox.critical(
                self, "Error", f"Xác minh Inner code thất bại. Trùng mã Serial Innercode: {record[0][5]}"
            )
        return False
    def verify_vendercode(self, code):
        if self.bypass_vendorcode:
            return True
        
        code_suffix = code[7:]
        
        # Check if the current code exists in the database
        self.cursor_spk.execute(
            "SELECT * FROM i_packing WHERE RIGHT(LEFT(inner_code, 17), 10) = %s", (code_suffix,)
        )
        current_records = self.cursor_spk.fetchall()
        
        if current_records:
            product_quantity = len(current_records)
            inner_quantity = current_records[0][5].split('$')[-1]
            if product_quantity >= int(inner_quantity):
                return False
        
        # Check if the previous code exists in the database
        self.cursor_spk.execute(
            "SELECT * FROM i_packing WHERE RIGHT(LEFT(inner_code, 17), 10) = %s", (str(int(code_suffix) - 1),)
        )
        previous_records = self.cursor_spk.fetchall()
        
        if previous_records:
            return True
        else:
            QMessageBox.critical(
                self, "Error", "Xác minh code thất bại. Số thùng liền trước không tồn tại. Quét sai label"
            )
            return False
    
    def verify_2ndinner_code(self, code):
        if code != self.inner_code.text():
            QMessageBox.critical(self, "Error", "Xác minh code thất bại. Inner code không trùng nhau")
            return
        else:
            self.dateScan.setEnabled(False)
            self.line.setEnabled(False)
            self.modelScan.setEnabled(False)
            self.shift_scan.setEnabled(False)
            self.second_inner_code.setText(code)
            self.show_data()
    
    def show_data(self):
        try:
            self.cursor_spk.execute("SELECT * FROM i_packing WHERE inner_code = %s ORDER BY id DESC", (self.inner_code.text(),))
            records = self.cursor_spk.fetchall()
            self.result_table.setRowCount(len(records))
            
            today_str = datetime.now().strftime("%Y-%m-%d")
            self.cursor_spk.execute("SELECT * FROM i_packing WHERE scan_time >= %s ORDER BY id DESC", (today_str,))
            records_today = self.cursor_spk.fetchall()
            
            self.qty_inner.setText(str(int(self.innner_quantity) - len(records)))
            self.qty_tray.setText(str(int(self.tray_quantity)-len(records)%int(self.tray_quantity)))
            if(int(self.qty_tray.text()) > int(self.qty_inner.text())):
                self.qty_tray.setText(self.qty_inner.text())
            total_ng_today = sum(1 for record in records_today if not record[8])
            
            self.total_today.setText(str(len(records_today) + total_ng_today))
            self.ok_today.setText(str(sum(1 for record in records_today if record[8])))
            self.ng_today.setText(str(total_ng_today))
            
            # Read comparison value from config.ini
            config = configparser.ConfigParser()
            config.read('config.ini')
            comparison_value = config['Settings'].getint('klippel_time', 4)  # Default to 4 if not set
        except Exception as e:
            print(e)
        
        for i, record in enumerate(records):
            self.result_table.setItem(i, 0, QTableWidgetItem(str(record[0])))
            self.result_table.setItem(i, 1, QTableWidgetItem(str(record[6])))
            self.result_table.setItem(i, 2, self.ok_item() if record[7] <= comparison_value else self.ng_item())
            self.result_table.setItem(i, 3, self.ok_item() if record[8] else self.ng_item())
            self.result_table.setItem(i, 4, QTableWidgetItem(record[9].strftime("%Y-%m-%d %H:%M:%S")))
            self.result_table.setItem(i, 5, QTableWidgetItem(record[5]))
        self.load_innerID()
        
        
    def ok_item(self):
        ok_item = QTableWidgetItem("OK")
        ok_item.setData(Qt.BackgroundRole, QtGui.QColor(0, 200, 0))
        ok_item.setData(Qt.ForegroundRole, QtGui.QColor(255, 255, 255))
        ok_item.setTextAlignment(Qt.AlignCenter)
        return ok_item

    def ng_item(self):
        ng_item = QTableWidgetItem("NG")
        ng_item.setData(Qt.BackgroundRole, QtGui.QColor(200, 0, 0))
        ng_item.setData(Qt.ForegroundRole, QtGui.QColor(255, 255, 255))
        ng_item.setTextAlignment(Qt.AlignCenter)
        return ng_item
    
    def judgement_ng(self):
        self.judgment_label.setText("NG")
        self.judgment_label.setStyleSheet("background-color: rgb(200, 0, 0); color: rgb(255, 255, 255);")
    
    def judgement_ok(self):
        self.judgment_label.setText("OK")
        self.judgment_label.setStyleSheet("background-color: rgb(0, 200, 0); color: rgb(255, 255, 255);")
    
    def judgement_na(self):
        self.judgment_label.setText("-")
        self.judgment_label.setStyleSheet("background-color: rgb(200, 200, 200); color: rgb(255, 255, 255);")
    
    def closeEvent(self, event):
        reply = QMessageBox.question(self, 'Message', "Are you sure you want to quit?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()

if __name__ == "__main__":
    app = None
    if app is None:
        app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec_()
