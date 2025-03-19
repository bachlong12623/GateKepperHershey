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

import serial
import verify as verify
import threading
from serial_port import BarcodeScanner, auto_detect_port  # Import the BarcodeScanner class and auto_detect_port function

Ui_MainWindow, QtBaseClass = uic.loadUiType("MainWindow.ui")


class PasswordDialog(QDialog):
    def __init__(self, parent=None, serial_number="", inner_code="", position=""):
        super(PasswordDialog, self).__init__(parent)
        self.setWindowTitle("Enter Password")
        self.setModal(True)
        self.setFixedSize(700, 500)  # Increase the size of the dialog
        
        layout = QVBoxLayout()
        
        self.setStyleSheet("background-color: blue;")
        
        self.info_label = QLabel(f"Serial đã bị trùng\nSerial Number: {serial_number}\nInner Code: {inner_code}\nVị trí: {position}")
        self.info_label.setStyleSheet("color: yellow; font-size: 18px;")  # Set the text color to yellow and increase font size
        layout.addWidget(self.info_label)
        
        self.label = QLabel("Please enter the password to proceed:")
        self.label.setStyleSheet("color: yellow; font-size: 20px;")  # Set the text color to yellow and increase font size
        layout.addWidget(self.label)
        
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setStyleSheet("font-size: 24px; padding: 10px;")
        layout.addWidget(self.password_input)
        
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
        
    def get_password(self):
        return self.password_input.text()
    
    def closeEvent(self, event):
        # Prevent closing the dialog without entering the correct password
        QMessageBox.critical(self, "Error", "Password input required. Application will not proceed.")
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
        
        # Read comparison value from config.ini
        config = configparser.ConfigParser()
        config.read('config.ini')
        comparison_value = int(config['Settings'].get('klippel_time', 3))  # Default to 3 if not set
        
        self.comparison_spinbox.setValue(comparison_value)
        
        self.save_button.clicked.connect(self.save_comparison_value)
        
    def fetch_data(self, cursor):
        cursor.execute("SELECT * FROM i_packing_duplicate WHERE scan_time >= %s ORDER BY id DESC", (datetime.now().strftime("%Y-%m-%d"),))
        records = cursor.fetchall()
        print(records)
        self.table.setRowCount(len(records))
        for i, record in enumerate(records):
            for j, value in enumerate(record):
                self.table.setItem(i, j, QTableWidgetItem(str(value)))
        self.table.resizeColumnsToContents()  # Adjust column width to fit content
    
    def save_comparison_value(self):
        comparison_value = self.comparison_spinbox.value()
        config = configparser.ConfigParser()
        config.read('config.ini')
        if 'Settings' not in config:
            config['Settings'] = {}
        config['Settings']['klippel_time'] = str(comparison_value)
        with open('config.ini', 'w') as configfile:
            config.write(configfile)
        self.accept()

class SerialReader(QObject):
    data_received = pyqtSignal(str)

    def __init__(self, barcode_scanner):
        super().__init__()
        self.barcode_scanner = barcode_scanner

    def read_serial_data(self):
        buffer = ""
        while True:
            sleep(0.1)
            if self.barcode_scanner.connection and self.barcode_scanner.connection.is_open:
                try:
                    data = self.barcode_scanner.connection.read(self.barcode_scanner.connection.in_waiting).decode(errors="ignore")
                    if data:
                        buffer += data
                        while '\r' in buffer or '\n' in buffer:
                            line, buffer = buffer.split("\n", 1) if "\n" in buffer else buffer.split("\r", 1)
                            self.data_received.emit(line.strip())
                except serial.SerialException as e:
                    print(f"Error reading from serial port: {e}")
                    break

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


        # Enable line when date is chosen
        self.dateScan.dateChanged.connect(lambda: self.line.setEnabled(True))

        # Enable modelScan when line is chosen
        self.line.currentIndexChanged.connect(lambda: self.modelScan.setEnabled(True) if self.line.currentIndex() != -1 else self.modelScan.setEnabled(False))

        # Enable shift_scan when modelScan is chosen
        self.modelScan.currentIndexChanged.connect(lambda: self.shift_scan.setEnabled(True) if self.modelScan.currentIndex() != -1 else self.shift_scan.setEnabled(False))
        
        self.shift_scan.currentIndexChanged.connect(self.verify_combobox)
        self.done_button.clicked.connect(self.clear_data)
        
        # Set table column width
        self.judgement_na()
        
        self.inspect_button.clicked.connect(self.show_inspection_dialog)

        QTableWidget.setColumnWidth(self.result_table, 0, 5)
        QTableWidget.setColumnWidth(self.result_table, 1, 200)
        QTableWidget.setColumnWidth(self.result_table, 2, 100)
        QTableWidget.setColumnWidth(self.result_table, 3, 100)
        QTableWidget.setColumnWidth(self.result_table, 4, 150)
        QTableWidget.setColumnWidth(self.result_table, 5, 600)

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
    def verify_combobox(self):
        pass
    
    def clear_data(self):
        self.inner_code.setText("")
        self.second_inner_code.setText("")
        self.serial_number.setText("")
        self.result_table.setRowCount(0)
        self.judgement_na()
    def verify_string(self, string):
        print(string)
        if  self.work_order.text() =="":
            self.verify_work_order(string)
        elif self.inner_code.text() == "":
            self.verify_inner_code(string)
        elif self.second_inner_code.text() == "":
            self.verify_2ndinner_code(string)
        else:
            self.verify_serial_number(string)
    def show_inspection_dialog(self):        
        inspection_dialog = InspectionDialog(self)
        inspection_dialog.fetch_data(self.cursor_spk)
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
    
    def verify_serial_number(self, serial_number):
        if serial_number[:5] != self.en_wo:
            self.judgement_ng()
            QMessageBox.critical(self, "Error", "Serial number verification failed. Serial number not match with work order.")
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
            self.cursor_spk.execute("SELECT COUNT(*) FROM i_packing WHERE inner_code = %s", (self.inner_code.text(),))
            inner_quantity = self.cursor_spk.fetchone()[0]

            if inner_quantity >= int(self.qty_inner.text()):
                QMessageBox.critical(self, "Error", "Carton is already full. Cannot insert more.")
                self.done_button.setEnabled(True)
                return

            if inner_quantity == int(self.qty_inner.text()) - 1:
                QMessageBox.information(self, "Notification", "Full carton.")
                self.done_button.setEnabled(True)

            if record and record[2]:
                self.insert_packing_record(serial_number, klippel_record, inner_quantity)
                self.judgement_ok()
                self.show_data()
                self.serial_number.setStyleSheet("background-color: rgb(0, 200, 0); color: rgb(255, 255, 255);")
                self.serial_number.setText(serial_number)
            else:
                self.judgement_ng()
                QMessageBox.critical(self, "Error", "Serial number verification failed. Serial number not found.")
        except Exception as e:
            print(e)
            self.judgement_ng()
            QMessageBox.critical(self, "Error", "Serial number verification failed. Serial number not found.")

    def handle_duplicate_serial(self, serial_number, record):
        password_dialog = PasswordDialog(self, serial_number=serial_number, inner_code=self.inner_code.text(), position=str(record[0]))
        while True:
            if password_dialog.exec_() == QDialog.Accepted:
                entered_password = password_dialog.get_password()
                if entered_password in [datetime.now().strftime("%y%m%d"), '27894869']:
                    QMessageBox.critical(self, "Error", "Serial number already scanned.")
                    self.insert_duplicate_record(serial_number, record)
                    self.show_data()
                    break
                else:
                    QMessageBox.critical(self, "Error", "Incorrect password. Application will not proceed.")
            else:
                QMessageBox.critical(self, "Error", "Password input required. Application will not proceed.")

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
                    QMessageBox.critical(self, "Error", "Work order verification failed. Model not match.")
                    return
                self.judgement_ok()
                self.work_order.setText(work_order)
            else:
                self.work_order.setText("")
                self.judgement_ng()
                QMessageBox.critical(self, "Error", "Work order verification failed. Work order not found.")
        except Exception as e:
            self.judgement_ng()
            QMessageBox.critical(self, "Error", "Work order verification failed. Work order not found.")
    
    def verify_inner_code(self, code):
        code_parts = code.split('$')
        if len(code_parts) < 7:
            self.judgement_ng()
            QMessageBox.critical(self, "Error", "Code verification failed. Not enough parts.")
            return False
        else:
            QR = verify.QRCode(code, self.sys_wo)
            if not QR.is_valid_code():
                self.judgement_ng()
                QMessageBox.critical(self, "Error", "Code verification failed. Invalid inner code.")            
                return
            else:
                self.qty_inner.setText(QR.quantity)
                self.inner_code.setText(code)
    
    def verify_2ndinner_code(self, code):
        if code != self.inner_code.text():
            QMessageBox.critical(self, "Error", "Code verification failed. Inner code not match.")
            return
        else:
            self.dateScan.setEnabled(False)
            self.line.setEnabled(False)
            self.modelScan.setEnabled(False)
            self.shift_scan.setEnabled(False)
            self.done_button.setEnabled(False)
            self.second_inner_code.setText(code)
            self.show_data()
    
    def show_data(self):
        self.cursor_spk.execute("SELECT * FROM i_packing WHERE inner_code = %s ORDER BY id DESC", (self.inner_code.text(),))
        records = self.cursor_spk.fetchall()
        self.result_table.setRowCount(len(records))
        
        today_str = datetime.now().strftime("%Y-%m-%d")
        self.cursor_spk.execute("SELECT * FROM i_packing WHERE scan_time >= %s ORDER BY id DESC", (today_str,))
        records_today = self.cursor_spk.fetchall()
        
        self.cursor_spk.execute("SELECT * FROM i_packing_duplicate WHERE scan_time >= %s ORDER BY id DESC", (today_str,))
        duplicate_records_today = self.cursor_spk.fetchall()
        
        total_ng_today = sum(1 for record in records_today if not record[8]) + len(duplicate_records_today)
        
        self.total_today.setText(str(len(records_today) + total_ng_today))
        self.ok_today.setText(str(sum(1 for record in records_today if record[8])))
        self.ng_today.setText(str(total_ng_today))
        
        # Read comparison value from config.ini
        config = configparser.ConfigParser()
        config.read('config.ini')
        comparison_value = config['Settings'].getint('klippel_time', 4)  # Default to 4 if not set
        
        
      
        
        for i, record in enumerate(records):
            self.result_table.setItem(i, 0, QTableWidgetItem(str(record[0])))
            self.result_table.setItem(i, 1, QTableWidgetItem(str(record[6])))
            self.result_table.setItem(i, 2, self.ok_item() if record[8] else self.ng_item())
            self.result_table.setItem(i, 3, self.ok_item() if record[7] <= comparison_value else self.ng_item())
            self.result_table.setItem(i, 4, QTableWidgetItem(record[9].strftime("%Y-%m-%d %H:%M:%S")))
            self.result_table.setItem(i, 5, QTableWidgetItem(record[5]))
        
        
        self.cursor_spk.execute("SELECT COUNT(*) FROM i_packing WHERE inner_code = %s", (self.inner_code.text(),))
        inner_quantity = self.cursor_spk.fetchone()[0]
        if inner_quantity >= int(self.qty_inner.text()):
            QMessageBox.critical(self, "Error", "Carton is already full. Cannot insert more.")
            self.done_button.setEnabled(True)
            return
        if inner_quantity == int(self.qty_inner.text()) - 1:
            QMessageBox.information(self, "Notification", "Full carton.")
            self.done_button.setEnabled(True)
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