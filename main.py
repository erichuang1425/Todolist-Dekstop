import sys
import os
import sqlite3
import webbrowser
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QScrollArea, 
                             QGridLayout, QLineEdit, QTextEdit, QDialog,
                             QFileDialog, QMessageBox, QSystemTrayIcon,
                             QMenu, QComboBox, QDateTimeEdit, QListWidget, QStyleFactory,
                             QGraphicsDropShadowEffect, QFormLayout,
                             QCalendarWidget, QTabWidget, QProgressBar, QCompleter)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QDateTime, pyqtSignal
from PyQt6.QtGui import QIcon, QColor, QPalette, QFont
import winreg

import sqlite3
import os

class DatabaseManager:
    def __init__(self):
        self.conn = None
        try:
            home_dir = os.path.expanduser("~")
            app_dir = os.path.join(home_dir, ".todo_list_app")
            os.makedirs(app_dir, exist_ok=True)
            db_path = os.path.join(app_dir, "todo_list.db")
            self.conn = sqlite3.connect(db_path)
            self.create_tables()
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            raise

    def create_tables(self):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY,
                    title TEXT,
                    description TEXT,
                    icon_path TEXT,
                    link TEXT,
                    reminder_time TEXT,
                    priority INTEGER,
                    category TEXT,
                    status TEXT,
                    due_date TEXT,
                    tags TEXT
                )
            ''')
            self.conn.commit()
            
            # Check if all columns exist, if not, add them
            columns_to_check = [
                "title", "description", "icon_path", "link", "reminder_time",
                "priority", "category", "status", "due_date", "tags"
            ]
            for column in columns_to_check:
                if not self.column_exists("tasks", column):
                    cursor.execute(f'ALTER TABLE tasks ADD COLUMN {column} TEXT')
            
            self.conn.commit()
                
        except sqlite3.Error as e:
            print(f"Error creating/updating table: {e}")
            raise

    def column_exists(self, table_name, column_name):
        cursor = self.conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [column[1] for column in cursor.fetchall()]
        return column_name in columns

    def add_task(self, task):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO tasks (title, description, icon_path, link, reminder_time, priority, category, status, due_date, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (task.title, task.description, task.icon_path, task.link, task.reminder_time, task.priority, task.category, task.status, task.due_date, ','.join(task.tags)))
        self.conn.commit()
        return cursor.lastrowid

    def update_task(self, task):
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE tasks
            SET title = ?, description = ?, icon_path = ?, link = ?, reminder_time = ?, priority = ?, category = ?, status = ?, due_date = ?, tags = ?
            WHERE id = ?
        ''', (task.title, task.description, task.icon_path, task.link, task.reminder_time, task.priority, task.category, task.status, task.due_date, ','.join(task.tags), task.id))
        self.conn.commit()

    def get_all_tasks(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM tasks')
        return cursor.fetchall()

    def delete_task(self, task_id):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
        self.conn.commit()

    def get_all_categories(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT DISTINCT category FROM tasks')
        return [row[0] for row in cursor.fetchall() if row[0]]

    def get_all_tags(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT tags FROM tasks')
        all_tags = [tag for row in cursor.fetchall() for tag in row[0].split(',') if row[0]]
        return list(set(all_tags))
    
    def close_connection(self):
        if self.conn:
            self.conn.close()

class ModernButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                font-size: 14px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3e8e41;
            }
        """)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(8)
        shadow.setXOffset(0)
        shadow.setYOffset(2)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.setGraphicsEffect(shadow)

class Task(QWidget):
    delete_task = pyqtSignal(int)
    edit_task = pyqtSignal(object)
    status_changed = pyqtSignal(object)

    def __init__(self, id, title, description, icon_path, link, reminder_time, priority, category, status, due_date, tags, parent=None):
        super().__init__(parent)
        self.id = id
        self.title = title
        self.description = description
        self.icon_path = icon_path
        self.link = link
        self.reminder_time = reminder_time
        self.priority = priority
        self.category = category
        self.status = status
        self.due_date = due_date
        self.tags = tags.split(',') if isinstance(tags, str) else tags
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        self.title_label = QLabel(self.title)
        self.title_label.setWordWrap(True)

        self.status_combo = QComboBox()
        self.status_combo.addItems(["Not Started", "In Progress", "Completed"])
        self.status_combo.setCurrentText(self.status)
        self.status_combo.currentTextChanged.connect(self.on_status_changed)

        self.due_date_label = QLabel(f"Due: {self.due_date}")

        layout.addWidget(self.title_label)
        layout.addWidget(self.status_combo)
        layout.addWidget(self.due_date_label)

        self.setFixedSize(200, 120)
        self.update_display()

    def update_display(self):
        status_colors = {"Not Started": "#FF7043", "In Progress": "#FFD54F", "Completed": "#81C784"}
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {status_colors.get(self.status, "#E0E0E0")};
                border-radius: 10px;
                padding: 10px;
            }}
            QLabel {{
                font-size: 12px;
                color: #333333;
            }}
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.animate_press()
            if self.link:
                self.open_link()

    def contextMenuEvent(self, event):
        context_menu = QMenu(self)
        edit_action = context_menu.addAction("Edit")
        delete_action = context_menu.addAction("Delete")
        action = context_menu.exec(event.globalPos())
        if action == edit_action:
            self.edit_task.emit(self)
        elif action == delete_action:
            self.delete_task.emit(self.id)

    def animate_press(self):
        animation = QPropertyAnimation(self, b"geometry")
        animation.setDuration(100)
        animation.setStartValue(self.geometry())
        animation.setEndValue(self.geometry().adjusted(2, 2, -2, -2))
        animation.setEasingCurve(QEasingCurve.Type.OutQuad)
        animation.start()
        QTimer.singleShot(100, self.animate_release)

    def animate_release(self):
        animation = QPropertyAnimation(self, b"geometry")
        animation.setDuration(100)
        animation.setStartValue(self.geometry())
        animation.setEndValue(self.geometry().adjusted(-2, -2, 2, 2))
        animation.setEasingCurve(QEasingCurve.Type.OutQuad)
        animation.start()

    def open_link(self):
        if self.link.startswith(("http://", "https://")):
            webbrowser.open(self.link)
        elif os.path.exists(self.link):
            os.startfile(self.link)
        else:
            QMessageBox.warning(self, "Error", "Invalid link or file path.")

    def on_status_changed(self, new_status):
        self.status = new_status
        self.update_display()
        self.status_changed.emit(self)

class TaskDialog(QDialog):
    def __init__(self, task=None, parent=None, db_manager=None):
        super().__init__(parent)
        self.task = task
        self.db_manager = db_manager
        self.setWindowTitle("Task Settings")
        self.setMinimumSize(500, 600)
        self.icon_path = ""
        self.init_ui()

    def init_ui(self):
        layout = QFormLayout(self)
        layout.setSpacing(10)

        self.title_input = QLineEdit(self.task.title if self.task else "")
        layout.addRow(QLabel("Title:"), self.title_input)

        self.description_input = QTextEdit(self.task.description if self.task else "")
        self.description_input.setMinimumHeight(100)
        layout.addRow(QLabel("Description:"), self.description_input)

        icon_button = ModernButton("Choose Icon")
        icon_button.clicked.connect(self.choose_icon)
        layout.addRow(QLabel("Icon:"), icon_button)

        self.link_input = QLineEdit(self.task.link if self.task else "")
        layout.addRow(QLabel("Link (web or local):"), self.link_input)

        self.reminder_datetime = QDateTimeEdit(QDateTime.currentDateTime())
        if self.task and self.task.reminder_time:
            try:
                self.reminder_datetime.setDateTime(QDateTime.fromString(self.task.reminder_time, Qt.DateFormat.ISODate))
            except ValueError:
                print(f"Invalid date format: {self.task.reminder_time}")
        self.reminder_datetime.setCalendarPopup(True)
        layout.addRow(QLabel("Reminder Time:"), self.reminder_datetime)

        self.priority_combo = QComboBox()
        self.priority_combo.addItems(["Low", "Medium", "High"])
        if self.task:
            self.priority_combo.setCurrentIndex(self.task.priority)
        layout.addRow(QLabel("Priority:"), self.priority_combo)

        self.category_input = QLineEdit(self.task.category if self.task else "")
        if self.db_manager:
            category_completer = QCompleter(self.db_manager.get_all_categories())
            self.category_input.setCompleter(category_completer)
        layout.addRow(QLabel("Category:"), self.category_input)

        self.status_combo = QComboBox()
        self.status_combo.addItems(["Not Started", "In Progress", "Completed"])
        if self.task:
            self.status_combo.setCurrentText(self.task.status)
        layout.addRow(QLabel("Status:"), self.status_combo)

        self.due_date = QDateTimeEdit(QDateTime.currentDateTime())
        if self.task and self.task.due_date:
            try:
                self.due_date.setDateTime(QDateTime.fromString(self.task.due_date, Qt.DateFormat.ISODate))
            except ValueError:
                print(f"Invalid date format: {self.task.due_date}")
        self.due_date.setCalendarPopup(True)
        layout.addRow(QLabel("Due Date:"), self.due_date)

        self.tags_input = QLineEdit(','.join(self.task.tags) if self.task and self.task.tags else "")
        if self.db_manager:
            tags_completer = QCompleter(self.db_manager.get_all_tags())
            tags_completer.setFilterMode(Qt.MatchFlag.MatchContains)
            tags_completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
            self.tags_input.setCompleter(tags_completer)
        layout.addRow(QLabel("Tags (comma-separated):"), self.tags_input)

        save_button = ModernButton("Save")
        save_button.clicked.connect(self.accept)
        layout.addRow("", save_button)

    def choose_icon(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Select Icon", "", "Image Files (*.png *.jpg *.bmp)")
        if file_name:
            self.icon_path = file_name
            QMessageBox.information(self, "Icon Selected", "Icon has been selected successfully.")

class TodoApp(QMainWindow):
    def __init__(self, db_manager):
        super().__init__()
        self.setWindowTitle('Advanced Todo List')
        self.setGeometry(100, 100, 1000, 800)
        self.db_manager = db_manager
        self.init_ui()
        self.load_tasks()
        self.setup_reminders()
        self.setup_autostart()
        self.is_dark_mode = False
        self.set_light_theme()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Toolbar
        toolbar = QHBoxLayout()
        add_button = ModernButton("Add Task")
        add_button.clicked.connect(self.add_task)
        toolbar.addWidget(add_button)

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search tasks...")
        self.search_bar.textChanged.connect(self.filter_tasks)
        toolbar.addWidget(self.search_bar)

        self.dark_mode_button = ModernButton("Toggle Dark Mode")
        self.dark_mode_button.clicked.connect(self.toggle_dark_mode)
        toolbar.addWidget(self.dark_mode_button)

        main_layout.addLayout(toolbar)

        # Tab widget
        self.tab_widget = QTabWidget()
        self.all_tasks_tab = QWidget()
        self.calendar_tab = QWidget()
        self.stats_tab = QWidget()
        self.categories_tab = QWidget()

        self.tab_widget.addTab(self.all_tasks_tab, "All Tasks")
        self.tab_widget.addTab(self.calendar_tab, "Calendar")
        self.tab_widget.addTab(self.stats_tab, "Stats")
        self.tab_widget.addTab(self.categories_tab, "Categories")

        main_layout.addWidget(self.tab_widget)

        # All Tasks Tab
        all_tasks_layout = QVBoxLayout(self.all_tasks_tab)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        all_tasks_layout.addWidget(scroll_area)

        scroll_content = QWidget()
        self.tasks_layout = QGridLayout(scroll_content)
        scroll_area.setWidget(scroll_content)

        # Calendar Tab
        calendar_layout = QVBoxLayout(self.calendar_tab)
        self.calendar_widget = QCalendarWidget()
        self.calendar_widget.selectionChanged.connect(self.on_date_selected)
        calendar_layout.addWidget(self.calendar_widget)

        self.date_tasks_list = QListWidget()
        calendar_layout.addWidget(self.date_tasks_list)

        # Stats Tab
        stats_layout = QVBoxLayout(self.stats_tab)
        self.update_stats()

        # Categories Tab
        categories_layout = QVBoxLayout(self.categories_tab)
        self.categories_list = QListWidget()
        categories_layout.addWidget(self.categories_list)
        self.update_categories()

        # System tray icon
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon("app_icon.png"))
        self.tray_icon.setVisible(True)

        # Create a menu for the system tray icon
        tray_menu = QMenu()
        show_action = tray_menu.addAction("Show")
        show_action.triggered.connect(self.show)
        quit_action = tray_menu.addAction("Quit")
        quit_action.triggered.connect(QApplication.quit)
        self.tray_icon.setContextMenu(tray_menu)

    def add_task(self):
        try:
            dialog = TaskDialog(parent=self, db_manager=self.db_manager)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                task = Task(
                    id=None,
                    title=dialog.title_input.text(),
                    description=dialog.description_input.toPlainText(),
                    icon_path=dialog.icon_path,
                    link=dialog.link_input.text(),
                    reminder_time=dialog.reminder_datetime.dateTime().toString(Qt.DateFormat.ISODate),
                    priority=dialog.priority_combo.currentIndex(),
                    category=dialog.category_input.text(),
                    status=dialog.status_combo.currentText(),
                    due_date=dialog.due_date.dateTime().toString(Qt.DateFormat.ISODate),
                    tags=dialog.tags_input.text().split(',')
                )
                task.id = self.db_manager.add_task(task)
                self.add_task_to_layout(task)
                self.setup_reminder(task)
                self.update_stats()
                self.update_categories()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred while adding the task: {str(e)}")

    def setup_reminders(self):
        tasks = self.db_manager.get_all_tasks()
        for task_data in tasks:
            task = Task(*task_data)
            self.setup_reminder(task)

    def setup_reminder(self, task):
        try:
            reminder_time = QDateTime.fromString(task.reminder_time, Qt.DateFormat.ISODate)
            current_time = QDateTime.currentDateTime()
            if reminder_time > current_time:
                QTimer.singleShot(current_time.msecsTo(reminder_time), lambda: self.show_reminder(task))
        except ValueError:
            print(f"Invalid reminder time for task: {task.title}")

    def show_reminder(self, task):
        self.tray_icon.showMessage(
            "Task Reminder",
            f"Don't forget: {task.title}",
            QSystemTrayIcon.MessageIcon.Information,
            10000  # Display for 10 seconds
        )

    def setup_autostart(self):
        if sys.platform == "win32":
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
                winreg.SetValueEx(key, "TodoListApp", 0, winreg.REG_SZ, sys.executable + " " + os.path.abspath(__file__))
                winreg.CloseKey(key)
            except WindowsError:
                QMessageBox.warning(self, "Auto-start Setup", "Unable to set the registry key for auto-start.")

    def toggle_dark_mode(self):
        self.is_dark_mode = not self.is_dark_mode
        if self.is_dark_mode:
            self.set_dark_theme()
        else:
            self.set_light_theme()

    def set_dark_theme(self):
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
        dark_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
        dark_palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
        QApplication.setPalette(dark_palette)

    def set_light_theme(self):
        QApplication.setPalette(QApplication.style().standardPalette())

    def add_task_to_layout(self, task):
        row, col = divmod(self.tasks_layout.count(), 4)
        self.tasks_layout.addWidget(task, row, col)
        task.delete_task.connect(self.delete_task)
        task.edit_task.connect(self.edit_task)
        task.status_changed.connect(self.on_task_status_changed)

    def load_tasks(self):
        tasks = self.db_manager.get_all_tasks()
        for task_data in tasks:
            task = Task(*task_data)
            self.add_task_to_layout(task)

    def filter_tasks(self):
        search_text = self.search_bar.text().lower()
        for i in range(self.tasks_layout.count()):
            item = self.tasks_layout.itemAt(i)
            if item:
                widget = item.widget()
                if isinstance(widget, Task):
                    should_show = (
                        search_text in widget.title.lower() or
                        search_text in widget.description.lower() or
                        search_text in widget.category.lower() or
                        any(search_text in tag.lower() for tag in widget.tags)
                    )
                    widget.setVisible(should_show)

    def delete_task(self, task_id):
        self.db_manager.delete_task(task_id)
        for i in range(self.tasks_layout.count()):
            item = self.tasks_layout.itemAt(i)
            if item:
                widget = item.widget()
                if isinstance(widget, Task) and widget.id == task_id:
                    self.tasks_layout.removeItem(item)
                    widget.deleteLater()
                    break
        self.update_stats()
        self.update_categories()

    def edit_task(self, task):
        dialog = TaskDialog(task, self, self.db_manager)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            task.title = dialog.title_input.text()
            task.description = dialog.description_input.toPlainText()
            task.icon_path = dialog.icon_path
            task.link = dialog.link_input.text()
            task.reminder_time = dialog.reminder_datetime.dateTime().toString(Qt.DateFormat.ISODate)
            task.priority = dialog.priority_combo.currentIndex()
            task.category = dialog.category_input.text()
            task.status = dialog.status_combo.currentText()
            task.due_date = dialog.due_date.dateTime().toString(Qt.DateFormat.ISODate)
            task.tags = dialog.tags_input.text().split(',')
            task.update_display()
            self.db_manager.update_task(task)
            self.setup_reminder(task)
            self.update_stats()
            self.update_categories()

    def on_task_status_changed(self, task):
        self.db_manager.update_task(task)
        self.update_stats()

    def on_date_selected(self):
        selected_date = self.calendar_widget.selectedDate().toString(Qt.DateFormat.ISODate)
        self.date_tasks_list.clear()
        for i in range(self.tasks_layout.count()):
            item = self.tasks_layout.itemAt(i)
            if item:
                widget = item.widget()
                if isinstance(widget, Task) and widget.due_date == selected_date:
                    self.date_tasks_list.addItem(f"{widget.title} - {widget.status}")

    def update_stats(self):
        stats_layout = self.stats_tab.layout()
        if stats_layout:
            while stats_layout.count():
                child = stats_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
        else:
            stats_layout = QVBoxLayout(self.stats_tab)

        total_tasks = self.tasks_layout.count()
        completed_tasks = sum(1 for i in range(total_tasks) if self.tasks_layout.itemAt(i).widget().status == "Completed")
        in_progress_tasks = sum(1 for i in range(total_tasks) if self.tasks_layout.itemAt(i).widget().status == "In Progress")
        not_started_tasks = total_tasks - completed_tasks - in_progress_tasks

        stats_layout.addWidget(QLabel(f"Total Tasks: {total_tasks}"))
        stats_layout.addWidget(QLabel(f"Completed Tasks: {completed_tasks}"))
        stats_layout.addWidget(QLabel(f"In Progress Tasks: {in_progress_tasks}"))
        stats_layout.addWidget(QLabel(f"Not Started Tasks: {not_started_tasks}"))

        if total_tasks > 0:
            completion_rate = (completed_tasks / total_tasks) * 100
            progress_bar = QProgressBar()
            progress_bar.setValue(int(completion_rate))
            stats_layout.addWidget(QLabel("Completion Rate:"))
            stats_layout.addWidget(progress_bar)

    def update_categories(self):
        self.categories_list.clear()
        categories = self.db_manager.get_all_categories()
        for category in categories:
            self.categories_list.addItem(category)

    def closeEvent(self, event):
        reply = QMessageBox.question(self, 'Exit', 'Are you sure you want to exit?',
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            self.db_manager.close_connection()  # Close the database connection
            event.accept()
            QApplication.quit()
        else:
            event.ignore()
            self.hide()
            self.tray_icon.showMessage(
                "Todo List",
                "Application minimized to system tray",
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )
if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle(QStyleFactory.create("Fusion"))  
    
    # Set application-wide font
    font = QFont("Segoe UI", 10)  
    app.setFont(font)
    
    app.setStyleSheet("""
        QMainWindow, QDialog {
            background-color: #f0f0f0;
        }
        QLabel {
            font-size: 14px;
        }
        QLineEdit, QTextEdit, QComboBox, QDateTimeEdit {
            padding: 8px;
            border: 1px solid #ccc;
            border-radius: 4px;
            font-size: 14px;
        }
        QScrollArea, QListWidget, QCalendarWidget {
            border: none;
        }
        QTabWidget::pane {
            border: 1px solid #ccc;
            border-radius: 4px;
        }
        QTabBar::tab {
            background-color: #e0e0e0;
            padding: 8px 16px;
            margin-right: 2px;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }
        QTabBar::tab:selected {
            background-color: #f0f0f0;
        }
        QProgressBar {
            border: 1px solid #ccc;
            border-radius: 4px;
            text-align: center;
        }
        QProgressBar::chunk {
            background-color: #4CAF50;
            width: 10px;
            margin: 0.5px;
        }
    """)

    try:
        db_manager = DatabaseManager()
        todo_app = TodoApp(db_manager)
        todo_app.show()
        sys.exit(app.exec())
    except sqlite3.Error as e:
        error_message = f"Database error: {e}\n\nPlease ensure you have write permissions in your home directory."
        QMessageBox.critical(None, "Database Error", error_message)
        sys.exit(1)
    except Exception as e:
        error_message = f"An unexpected error occurred: {e}"
        QMessageBox.critical(None, "Unexpected Error", error_message)
        sys.exit(1)