from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog, QMessageBox, QTabWidget, QTextEdit, QHBoxLayout, QApplication, QLineEdit, QComboBox
from PySide6.QtCore import Qt, QTimer
from pathlib import Path
import shutil
import os
import subprocess
import json
import glob
from PySide6.QtGui import QTextCursor
import re

# Цвета из InstallationsTab
MC_DARK = "#121212"
MC_GRAY = "#1e1e1e"
MC_TEXT = "#e0e0e0"
MC_TEXT_LIGHT = "#ffffff"
MC_TEXT_MUTED = "#b0b0b0"
MC_BORDER = "#333"
MC_BLUE = "#3a7dcf"
MC_GREEN = "#3a7d44"
MC_LIGHT_GREEN = "#4caf50"
MC_RED = "#dc3545"
MC_YELLOW = "#ffc107"
MC_ACCENT = "#ffaa00"
MC_PURPLE = "#6a3dcf"

class SettingsTab(QWidget):
    def __init__(self, config_manager, build_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.build_manager = build_manager
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(20)
        self.setStyleSheet(f'''
            QWidget {{
                background: {MC_DARK};
                color: {MC_TEXT};
                font-family: 'Rubik', Arial, sans-serif;
            }}
            QPushButton {{
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: 500;
                background: {MC_GREEN};
                color: {MC_TEXT_LIGHT};
                border: none;
            }}
            QPushButton:hover {{
                background: {MC_LIGHT_GREEN};
            }}
            QPushButton:disabled {{
                background: #444;
                color: #aaa;
            }}
            QLineEdit, QComboBox {{
                background: {MC_GRAY};
                border: 2px solid {MC_BORDER};
                border-radius: 8px;
                padding: 8px 12px;
                color: {MC_TEXT_LIGHT};
                font-size: 15px;
            }}
            QLineEdit:focus, QComboBox:focus {{
                border: 2px solid {MC_BLUE};
            }}
            QLabel {{
                color: {MC_TEXT};
            }}
            QTextEdit {{
                background: {MC_GRAY};
                border: 2px solid {MC_BORDER};
                border-radius: 8px;
                color: {MC_TEXT_LIGHT};
                font-size: 15px;
                padding: 10px;
            }}
        ''')
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        # Вкладка выбора пути
        self.path_tab = QWidget()
        path_layout = QVBoxLayout(self.path_tab)
        self.path_label = QLabel(f"Папка Minecraft: {self.config_manager.get('minecraft_path')}")
        path_layout.addWidget(self.path_label)
        self.choose_btn = QPushButton("Изменить папку Minecraft")
        self.choose_btn.clicked.connect(self.choose_path)
        path_layout.addWidget(self.choose_btn)
        path_layout.addStretch()
        self.tabs.addTab(self.path_tab, "Путь к Minecraft")
        # Вкладка логов
        self.logs_tab = QWidget()
        logs_layout = QVBoxLayout(self.logs_tab)
        filter_layout = QHBoxLayout()
        self.level_combo = QComboBox()
        self.level_combo.addItems(["ALL", "INFO", "WARNING", "ERROR"])
        self.level_combo.currentTextChanged.connect(self.update_log_view)
        filter_layout.addWidget(QLabel("Уровень:"))
        filter_layout.addWidget(self.level_combo)
        self.event_combo = QComboBox()
        self.event_combo.addItems(["ALL", "download_file", "download_file_attempt", "download_file_error"])
        self.event_combo.currentTextChanged.connect(self.update_log_view)
        filter_layout.addWidget(QLabel("Событие:"))
        filter_layout.addWidget(self.event_combo)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Поиск по логам...")
        self.search_edit.textChanged.connect(self.update_log_view)
        filter_layout.addWidget(self.search_edit)
        logs_layout.addLayout(filter_layout)
        self.log_content = QTextEdit()
        self.log_content.setReadOnly(True)
        logs_layout.addWidget(self.log_content)
        btns_layout = QHBoxLayout()
        self.copy_btn = QPushButton("Копировать лог")
        self.copy_btn.setStyleSheet("padding: 6px 16px; margin-right: 8px;")
        self.copy_btn.clicked.connect(self.copy_log)
        btns_layout.addWidget(self.copy_btn)
        self.open_folder_btn = QPushButton("Открыть папку")
        self.open_folder_btn.setStyleSheet("padding: 6px 16px; margin-right: 8px;")
        self.open_folder_btn.clicked.connect(self.open_log_folder)
        btns_layout.addWidget(self.open_folder_btn)
        self.clear_btn = QPushButton("Очистить логи")
        self.clear_btn.setStyleSheet("padding: 6px 16px;")
        self.clear_btn.clicked.connect(self.clear_log)
        btns_layout.addWidget(self.clear_btn)
        btns_layout.addStretch()
        logs_layout.addLayout(btns_layout)
        self.tabs.addTab(self.logs_tab, "Логи приложения")
        self.tabs.currentChanged.connect(self._on_tab_changed)
        self.log_file = self._get_latest_log_file()
        self._setup_auto_update()

    def choose_path(self):
        current_path = str(self.config_manager.get('minecraft_path'))
        new_path = QFileDialog.getExistingDirectory(self, "Выберите папку Minecraft", current_path)
        if not new_path:
            return
        new_path = Path(new_path)
        has_mc_structure = any((new_path / d).exists() for d in ["versions", "saves"]) or (new_path / "launcher_profiles.json").exists()
        if has_mc_structure:
            reply = QMessageBox.warning(self, "Внимание", "В выбранной папке уже есть структура Minecraft. Продолжить использовать её?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply != QMessageBox.StandardButton.Yes:
                return
        old_path = Path(current_path)
        if old_path.exists() and old_path != new_path:
            try:
                for item in old_path.iterdir():
                    dest = new_path / item.name
                    if item.is_dir():
                        shutil.copytree(item, dest, dirs_exist_ok=True)
                    else:
                        shutil.copy2(item, dest)
            except Exception as e:
                QMessageBox.critical(self, "Ошибка миграции", f"Ошибка при переносе данных: {e}")
                return
        self.config_manager.set("minecraft_path", str(new_path))
        self.path_label.setText(f"Папка Minecraft: {new_path}")
        QMessageBox.information(self, "Готово", "Путь к папке Minecraft изменён. Перезапустите приложение для применения изменений.")

    def _on_tab_changed(self, idx):
        if self.tabs.tabText(idx) == "Логи приложения":
            self.update_log_view(force_scroll_to_bottom=True)

    def _get_latest_log_file(self):
        # Получаем путь к папке логов из config_manager или используем стандартный путь
        log_dir = Path(self.config_manager.get('minecraft_path')) / "logs"
        log_file = log_dir / "tmkl.log"
        return str(log_file) if log_file.exists() else None

    def _setup_auto_update(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_log_view)
        self.timer.start(1500)

    def update_log_view(self, force_scroll_to_bottom=False):
        if not self.log_file or not Path(self.log_file).exists():
            self.log_content.setPlainText("Лог-файл не найден.")
            return
        level = self.level_combo.currentText()
        query = self.search_edit.text().lower()
        html_lines = []
        log_re = re.compile(r'^(?P<time>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \| (?P<level>\w+) \| (?P<module>[^|]+) \| (?P<msg>.*)$')
        session_start_re = re.compile(r'core\\.logger:setup_logger:30 \\| Система логирования инициализирована')
        first_line = True
        scroll_bar = self.log_content.verticalScrollBar()
        prev_value = scroll_bar.value()
        prev_max = scroll_bar.maximum()
        at_bottom = prev_value == prev_max
        with open(self.log_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.rstrip("\n")
                m = log_re.match(line)
                is_session_start = bool(session_start_re.search(line))
                if is_session_start and not first_line:
                    html_lines.append('<hr style="border:1px solid #888;margin:8px 0;">'
                                     '<div style="color:#888;text-align:center;font-size:11px;margin-bottom:4px;">— Новая сессия —</div>')
                first_line = False
                if m:
                    lvl = m.group("level").upper()
                    msg = m.group("msg")
                    if (level == "ALL" or lvl == level) and (query in line.lower()):
                        color = "#ffffff"
                        if lvl == "INFO":
                            color = "#4caf50"
                        elif lvl == "WARNING":
                            color = "#ff9800"
                        elif lvl == "ERROR":
                            color = "#f44336"
                        elif lvl == "DEBUG":
                            color = "#2196f3"
                        html_lines.append(f'<span style="color:{color}">[{m.group("time")}] [{lvl}] [{m.group("module").strip()}] {msg}</span>')
                else:
                    if query in line.lower():
                        html_lines.append(f'<span style="color:#b0b0b0">{line}</span>')
        self.log_content.setHtml("<br>".join(html_lines))
        # Восстанавливаем позицию скролла
        if force_scroll_to_bottom or at_bottom:
            self.log_content.verticalScrollBar().setValue(self.log_content.verticalScrollBar().maximum())
        else:
            # Корректируем позицию с учётом возможного изменения максимума
            new_max = self.log_content.verticalScrollBar().maximum()
            if prev_max > 0:
                ratio = prev_value / prev_max
                new_value = int(ratio * new_max)
                self.log_content.verticalScrollBar().setValue(new_value)
            else:
                self.log_content.verticalScrollBar().setValue(prev_value)

    def copy_log(self):
        text = self.log_content.toPlainText()
        if text:
            QApplication.clipboard().setText(text)

    def open_log_folder(self):
        if not self.log_file:
            return
        folder = str(Path(self.log_file).parent)
        if os.name == 'nt':
            os.startfile(folder)
        elif os.name == 'posix':
            subprocess.Popen(['xdg-open', folder])
        else:
            QMessageBox.information(self, "Открыть папку", f"Путь: {folder}")

    def clear_log(self):
        if self.log_file and Path(self.log_file).exists():
            with open(self.log_file, "w", encoding="utf-8") as f:
                f.truncate(0)
            self.update_log_view() 