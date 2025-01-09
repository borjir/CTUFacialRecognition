from PyQt5.QtWidgets import QProgressDialog, QFileDialog, QApplication, QWidget, QLabel, QFrame, QHBoxLayout, QPushButton, QHBoxLayout, QComboBox, QDialog, QStackedWidget, QMessageBox, QDesktopWidget, QTableWidgetItem
from PyQt5 import QtCore
from PyQt5.uic import loadUi
from PyQt5.QtGui import QIcon, QColor, QPixmap, QImage
from PyQt5.QtCore import QTimer, QTime, Qt, QSize, pyqtSignal
from datetime import datetime, timedelta
import calendar
import re
import sys
import os
import platform
import numpy as np
from global_state import GlobalState
import account_function
import cv2
import face_recognition
import time
import sqlite3
import shutil

class PopupDialog(QDialog):
    login_success_signal = pyqtSignal(tuple)  # Signal to pass user data back to MainWindow
    def __init__(self, mode='register', parent=None):
        super().__init__(parent)
        loadUi("files/dialog.ui", self)
        self.mode = mode  # 'register' or 'login'

        if mode == 'register':
            self.stackedWidget.setCurrentIndex(0)  # Scanning for registration
            self.setFixedSize(650, 650)
        elif mode == 'login':
            self.stackedWidget.setCurrentIndex(0)  # Scanning for login
            self.setFixedSize(650, 650)

        if GlobalState.num == 0:
            self.stackedWidget.setCurrentIndex(0)
            self.setFixedSize(650,650)
        elif GlobalState.num == 1:
            self.stackedWidget.setCurrentIndex(1)    
        self.start_time = None  # Track the start time
        self.recognition_delay = 3  # Minimum delay for face recognition in seconds
        self.timeout_seconds = 5  # Maximum timeout duration in seconds
        self.back_to_mainPage_btn.clicked.connect(self.back_to_mainPage)

    def back_to_mainPage(self):
        self.close()
    def start_camera(self):
        self.capture = cv2.VideoCapture(1)
        if not self.capture.isOpened():
            QMessageBox.critical(self, "Error", "Camera not accessible.")
            return False

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.start_time = time.time()  # Record the start time
        self.timer.start(30)  # Update every 30ms
        return True


    def update_frame(self):
        ret, frame = self.capture.read()
        if ret:
            # Convert the frame to RGB for face recognition
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Detect faces
            face_locations = face_recognition.face_locations(rgb_frame)

            # Draw rectangles around detected faces
            for (top, right, bottom, left) in face_locations:
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)

            # Convert to QImage for display
            h, w, ch = frame.shape
            bytes_per_line = ch * w
            qimg = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qimg)

            # Update QLabel with the current frame
            self.camera_label.setPixmap(pixmap)

            # Check if at least 3 seconds have passed
            elapsed_time = time.time() - self.start_time
            if elapsed_time > self.recognition_delay and face_locations:
                # Process the first detected face after 3 seconds
                encoding = face_recognition.face_encodings(rgb_frame, face_locations)[0]
                self.timer.stop()
                self.process_face(encoding)
                return

        # Check if the 5-second timeout has been exceeded
        if time.time() - self.start_time > self.timeout_seconds:
            self.timer.stop()
            QMessageBox.warning(self, "Timeout", "No face detected or camera image is unclear. Please try again.")
            self.capture.release()
            self.reject()

    def process_face(self, encoding):
        if self.mode == 'register':
            self.handle_registration(encoding)
        elif self.mode == 'login':
            self.handle_login(encoding)

    def handle_registration(self, encoding):
        # Registration logic (same as before)
        stored_encodings = account_function.get_all_face_encodings()
        for stored_encoding_bytes in stored_encodings:
            stored_encoding = np.frombuffer(stored_encoding_bytes, dtype=np.float64)
            if face_recognition.compare_faces([stored_encoding], encoding, tolerance=0.6)[0]:
                QMessageBox.warning(self, "Error", "Face already registered.")
                self.capture.release()
                self.reject()
                return

        self.face_encoding = encoding
        QMessageBox.information(self, "Success", "Face recognized successfully!")
        self.capture.release()
        self.accept()

    def handle_registration(self, encoding):
        # Fetch all stored face encodings
        stored_encodings = account_function.get_all_face_encodings()

        for stored_encoding_bytes in stored_encodings:
            stored_encoding = np.frombuffer(stored_encoding_bytes, dtype=np.float64)
            
            # Calculate the distance between encodings
            distance = face_recognition.face_distance([stored_encoding], encoding)[0]

            # Use a strict threshold to determine if the face is already registered
            if distance < 0.4:  # Adjust threshold as needed
                QMessageBox.warning(self, "Error", "Face already registered.")
                self.capture.release()
                self.reject()
                return

        # If no matches are found, proceed with registration
        self.face_encoding = encoding
        QMessageBox.information(self, "Success", "Face recognized successfully!")
        self.capture.release()
        self.accept()


    # def handle_login(self, encoding):
    #     stored_encodings = account_function.get_all_face_encodings()
    #     for stored_encoding_bytes in stored_encodings:
    #         stored_encoding = np.frombuffer(stored_encoding_bytes, dtype=np.float64)
    #         if face_recognition.compare_faces([stored_encoding], encoding, tolerance=0.6)[0]:
    #             # Fetch user data from account_function
    #             user_data = account_function.get_user_data_by_encoding(stored_encoding_bytes)
    #             if user_data:
    #                 QMessageBox.information(self, "Login Success", "Face recognized. Welcome!")
    #                 self.capture.release()
    #                 self.accept()
    #                 self.login_success_signal.emit(user_data)  # Emit user data
    #                 return

    #     QMessageBox.warning(self, "Login Failed", "Face not recognized in the database.")
    #     self.capture.release()
    #     self.reject()

    def handle_login(self, encoding):
        stored_encodings = account_function.get_all_face_encodings()
        matching_user_data = None  # Placeholder for matched user data

        # Iterate through stored encodings to find a match
        for stored_encoding_bytes in stored_encodings:
            stored_encoding = np.frombuffer(stored_encoding_bytes, dtype=np.float64)
            if face_recognition.compare_faces([stored_encoding], encoding, tolerance=0.6)[0]:
                # Fetch user data for the matched encoding
                matching_user_data = account_function.get_user_data_by_encoding(stored_encoding_bytes)
                break  # Stop checking after finding the first match

        if matching_user_data:
            QMessageBox.information(self, "Login Success", "Face recognized. Welcome!")
            self.capture.release()
            self.accept()
            self.login_success_signal.emit(matching_user_data)  # Emit the correct user data
        else:
            QMessageBox.warning(self, "Login Failed", "Face not recognized in the database.")
            self.capture.release()
            self.reject()

    def closeEvent(self, event):
        if hasattr(self, 'capture') and self.capture.isOpened():
            self.capture.release()
        event.accept()

class MainWindow(QDialog):
    def __init__(self):
        super().__init__()
        loadUi("files/main_window.ui", self)
        self.stackedWidget.setCurrentIndex(0)

        # Buttons
        self.login_btn.clicked.connect(self.login)
        self.register_btn.clicked.connect(self.register)
        self.register_confirm_btn.clicked.connect(self.register_confirm)
        self.register_cancel_btn.clicked.connect(self.register_cancel)
        self.add_photo_btn.clicked.connect(self.add_photo)
        self.delete_db_btn.clicked.connect(self.delete_database)
        self.delete_db_btn.setVisible(False)
        self.back_to_mainPage_btn.clicked.connect(self.back_to_mainPage)
        # Initialize fields
        self.image_path = None
        self.load_combo_boxes()
        self.debug_print_database()

    def debug_print_database(self):
        try:
            conn = sqlite3.connect("user_data.db")
            cursor = conn.cursor()

            # Query to fetch all data from the users table
            cursor.execute("SELECT * FROM users")
            rows = cursor.fetchall()

            print("\nDatabase Contents (users table):")
            for row in rows:
                print(row)  # Print each row

            conn.close()
        except sqlite3.OperationalError as e:
            print(f"Error accessing the database: {e}")


    def delete_database(self):
        confirm = QMessageBox.question(
            self,
            "Confirm Deletion",
            "Are you sure you want to delete all data in the database?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm == QMessageBox.Yes:
            try:
                conn = sqlite3.connect("user_data.db")
                cursor = conn.cursor()
                cursor.execute("DELETE FROM users")
                conn.commit()
                conn.close()
                QMessageBox.information(self, "Success", "All data in the database has been deleted.")
            except sqlite3.OperationalError as e:
                QMessageBox.critical(self, "Error", f"Database error: {e}")

    def login(self):
        # Show PopupDialog for face scanning in login mode
        dialog = PopupDialog(mode='login', parent=self)

        # Connect the signal to populate_user_details
        dialog.login_success_signal.connect(self.populate_user_details)

        if dialog.start_camera():
            if dialog.exec_() == QDialog.Accepted:
                # Successful login; UI updates are handled via the signal
                self.stackedWidget.setCurrentIndex(2)  # Direct to main dashboard
            else:
                # Failed login or timeout
                QMessageBox.warning(self, "Login Error", "Login failed. Please try again.")
                self.stackedWidget.setCurrentIndex(0)  # Stay on the login screen

    def populate_user_details(self, user_data):
        # Unpack user data
        ref_num, full_name, address, email, phone_num, gender, civil_status, guardian, dob, work_status, image_path = user_data

        # Format date of birth
        dob_datetime = datetime.strptime(dob, "%Y-%m-%d")
        formatted_dob = dob_datetime.strftime("%B %d, %Y")

        # Update QLabel elements
        self.login_ref_num_label.setText(ref_num)
        self.login_full_name_label.setText(full_name)
        self.login_home_address_label.setText(address)
        self.login_email_label.setText(email)
        self.login_phone_num_label.setText(phone_num)
        self.login_gender_label.setText(gender)
        self.login_civil_status_label.setText(civil_status)
        self.login_guardian_label.setText(guardian)
        self.login_birthdate_label.setText(formatted_dob.upper())
        self.login_work_status_label.setText(work_status)

        # Load the image
        if os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            self.login_image_label.setScaledContents(True)  # Ensure QLabel scales contents
            self.login_image_label.setPixmap(pixmap)
        else:
            QMessageBox.warning(self, "Error", "User image not found.")

    def back_to_mainPage(self):
        self.stackedWidget.setCurrentIndex(0)

    def register(self):
        self.stackedWidget.setCurrentIndex(1)

    def register_cancel(self):
        self.reset_fields()
        self.stackedWidget.setCurrentIndex(0)

    def add_photo(self):
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(self, "Select Photo", "", "Images (*.png *.jpg *.jpeg)")
        if file_path:
            self.image_path = file_path
            pixmap = QPixmap(file_path)
            self.image_label.setScaledContents(True)  # Ensure QLabel scales contents
            self.image_label.setPixmap(pixmap)

    def load_combo_boxes(self):
        # Populate gender combo box
        self.gender_comboBox.addItem("CHOOSE GENDER")
        self.gender_comboBox.addItems(["MALE", "FEMALE", "RATHER NOT SAY"])
        self.gender_comboBox.model().item(0).setEnabled(False)

        self.civil_status_comboBox.addItem("CHOOSE STATUS")
        self.civil_status_comboBox.addItems([
            "SINGLE", "MARRIED", "DIVORCED", "WIDOWED",
            "SEPARATED", "IN A DOMESTIC PARTNERSHIP", "ANNULLED"
        ])
        self.civil_status_comboBox.model().item(0).setEnabled(False)

        # Populate month combo box
        months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
                  "November", "December"]
        self.month_comboBox.addItems(months)

        # Populate year combo box
        current_year = datetime.now().year
        self.year_comboBox.addItems([str(year) for year in range(1900, current_year + 1)])

        # Set current date
        today = datetime.now()
        self.year_comboBox.setCurrentText(str(today.year))
        self.month_comboBox.setCurrentIndex(today.month - 1)
        self.day_comboBox.addItem(str(today.day))  # To avoid empty before update

        # Connect signals for dynamic day loading
        self.month_comboBox.currentIndexChanged.connect(self.update_days)
        self.year_comboBox.currentIndexChanged.connect(self.update_days)
        self.update_days()

    def update_days(self):
        # Save current day
        current_day = int(self.day_comboBox.currentText()) if self.day_comboBox.currentText() else 1

        # Update days based on selected month and year
        self.day_comboBox.clear()
        month = self.month_comboBox.currentIndex() + 1
        year = int(self.year_comboBox.currentText()) if self.year_comboBox.currentText() else 1900
        days_in_month = calendar.monthrange(year, month)[1]

        # Populate days
        self.day_comboBox.addItems([str(day) for day in range(1, days_in_month + 1)])

        # Restore or adjust day
        if current_day <= days_in_month:
            self.day_comboBox.setCurrentText(str(current_day))
        else:
            self.day_comboBox.setCurrentText(str(days_in_month))

    def validate_fields(self):
        # Validate ref_num
        ref_num = self.ref_num_lineEdit.text().strip()
        if not ref_num.isdigit() or not account_function.check_unique_field("ref_num", ref_num):
            return "Reference number must be unique and numerical."

        # Validate names
        first_name = self.first_name_lineEdit.text().strip()
        last_name = self.last_name_lineEdit.text().strip()
        if not first_name or not last_name:
            return "First and last names must not be blank."

        # Validate email
        email = self.email_lineEdit.text().strip()
        if not re.match(r"[^@\s]+@[^@\s]+\.[^@\s]+", email) or not account_function.check_unique_field("email", email):
            return "Invalid or duplicate email address."

        # Validate phone number
        phone_num = self.phone_num_lineEdit.text().strip()
        if not phone_num.isdigit() or len(phone_num) != 11 or not account_function.check_unique_field("phone_num", phone_num):
            return "Phone number must be unique, numerical, and 11 digits."

        # Validate gender
        if self.gender_comboBox.currentIndex() == 0:
            return "Please select a valid gender."

        if self.civil_status_comboBox.currentIndex() == 0:
            return "Please select a valid civil status."

        # Validate date of birth
        if not self.month_comboBox.currentText() or not self.day_comboBox.currentText() or not self.year_comboBox.currentText():
            return "Please select a valid date of birth."

        selected_date = datetime(
            int(self.year_comboBox.currentText()),
            self.month_comboBox.currentIndex() + 1,
            int(self.day_comboBox.currentText())
        )
        today = datetime.now()
        if selected_date > today:
            return "Date of birth cannot be in the future."

        # Validate photo
        if not self.image_path or not os.path.exists(self.image_path):
            return "Please add a valid photo."

        return None

    def register_confirm(self):
        # Validate all fields
        error = self.validate_fields()
        if error:
            QMessageBox.warning(self, "Validation Error", error)
            return

        # Prepare data for registration
        ref_num = self.ref_num_lineEdit.text().strip().upper()
        full_name = f"{self.first_name_lineEdit.text().strip().upper()} {self.last_name_lineEdit.text().strip().upper()}"
        address = self.home_address_lineEdit.text().strip().upper()
        email = self.email_lineEdit.text().strip().lower()
        phone_num = self.phone_num_lineEdit.text().strip()
        gender = self.gender_comboBox.currentText().strip().upper()
        civil_status = self.civil_status_comboBox.currentText().strip().upper()
        guardian = self.guardian_lineEdit.text().upper()
        dob = f"{self.year_comboBox.currentText()}-{self.month_comboBox.currentIndex() + 1}-{self.day_comboBox.currentText()}"
        work_status = self.work_status_lineEdit.text().upper()

        # Show PopupDialog for face recognition
        self.setEnabled(False)
        GlobalState.num == 0
        dialog = PopupDialog(mode='register', parent=self)

        if dialog.start_camera():
            if dialog.exec_() == QDialog.Accepted:
                # Define target directory for images
                target_directory = "files/images/account_images"
                os.makedirs(target_directory, exist_ok=True)  # Ensure directory exists

                # Generate target file path using reference number
                target_image_path = os.path.join(target_directory, f"{ref_num}.jpg")

                # Copy the image to the target directory
                try:
                    shutil.copy(self.image_path, target_image_path)
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to save image: {str(e)}")
                    return

                face_encoding = dialog.face_encoding
                # Call the insert_user function with the updated image path
                account_function.insert_user(
                    ref_num,
                    full_name,
                    address,
                    email,
                    phone_num,
                    gender,
                    civil_status,
                    guardian,
                    dob,
                    work_status,
                    target_image_path,  # Use the updated image path
                    face_encoding.tobytes()
                )
                QMessageBox.information(self, "Success", "Registration complete!")
                self.reset_fields()

                # Reopen PopupDialog to display registered details
                self.setEnabled(False)
                dialog = PopupDialog(mode='register', parent=self)
                dialog.setFixedSize(1300,800)
                # Populate the PopupDialog with registration details
                dialog.stackedWidget.setCurrentIndex(1)  # Set to the success page
                dialog.regSuc_ref_num_label.setText(ref_num)
                dialog.regSuc_full_name_label.setText(full_name)
                dialog.regSuc_home_address_label.setText(address)
                dialog.regSuc_email_label.setText(email)
                dialog.regSuc_phone_num_label.setText(phone_num)
                dialog.regSuc_gender_label.setText(gender)
                dialog.regSuc_civil_status_label.setText(civil_status)
                dob_datetime = datetime.strptime(dob, "%Y-%m-%d")
                formatted_dob = dob_datetime.strftime("%B %d, %Y")  # Format as "Month Day, Year"
                # Set the formatted date
                dialog.regSuc_birthdate_label.setText(formatted_dob.upper())
                dialog.regSuc_guardian_label.setText(guardian)
                dialog.regSuc_work_status_label.setText(work_status)

                # Load the image into the QLabel
                pixmap = QPixmap(target_image_path)
                dialog.register_success_image_label.setScaledContents(True)  # Ensure QLabel scales contents
                dialog.register_success_image_label.setPixmap(pixmap)

                dialog.exec_()  # Show the new PopupDialog
                self.setEnabled(True)
                self.stackedWidget.setCurrentIndex(0)
        self.setEnabled(True)
        

    def reset_fields(self):
        """Reset all fields to their default states."""
        # Clear text fields
        self.ref_num_lineEdit.clear()
        self.first_name_lineEdit.clear()
        self.last_name_lineEdit.clear()
        self.email_lineEdit.clear()
        self.phone_num_lineEdit.clear()
        self.home_address_lineEdit.clear()
        self.guardian_lineEdit.clear()
        self.work_status_lineEdit.clear()
        # Reset combo boxes
        self.gender_comboBox.setCurrentIndex(0)
        self.civil_status_comboBox.setCurrentIndex(0)  # Reset to "CHOOSE STATUS"
        self.year_comboBox.setCurrentIndex(self.year_comboBox.findText(str(datetime.now().year)))
        self.month_comboBox.setCurrentIndex(datetime.now().month - 1)
        self.update_days()  # Ensures days are reset appropriately

        # Reset day to today's date
        self.day_comboBox.setCurrentText(str(datetime.now().day))

        # Clear image selection
        self.image_path = None
        self.image_label.clear()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main = MainWindow()
    widget = QStackedWidget()
    widget.addWidget(main)
    widget.setMinimumSize(800, 600)
    widget.setWindowTitle("CTU's Facial Recognition System")
    widget.setWindowIcon(QIcon('files/images/CTU_LOGO.png'))

    # Show maximized on start
    def show_maximized():
        widget.showMaximized()

    QtCore.QTimer.singleShot(0, show_maximized)

    widget.show()
    sys.exit(app.exec_())