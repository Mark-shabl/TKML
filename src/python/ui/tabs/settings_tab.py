from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog, QMessageBox, QTabWidget, QTextEdit, QHBoxLayout, QApplication, QLineEdit, QComboBox, QStackedWidget, QSlider, QSizePolicy, QFrame
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
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(0)
        self.setStyleSheet(f'''
            QWidget {{
                background: {MC_DARK};
                color: {MC_TEXT};
                font-family: 'Rubik', Arial, sans-serif;
            }}
            QPushButton.tab-btn {{
                border-radius: 8px;
                padding: 12px 24px;
                font-weight: bold;
                background: {MC_GRAY};
                color: {MC_TEXT};
                border: 2px solid {MC_BORDER};
                margin-bottom: 8px;
                font-size: 16px;
                text-align: left;
            }}
            QPushButton.tab-btn:checked {{
                border: 2px solid {MC_BLUE};
                background: rgba(58, 125, 207, 0.2);
                color: {MC_TEXT_LIGHT};
            }}
            QPushButton.tab-btn:hover {{
                background: {MC_GREEN};
                color: {MC_TEXT_LIGHT};
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
        # Sidebar с вкладками
        sidebar = QVBoxLayout()
        sidebar.setSpacing(0)
        sidebar.setContentsMargins(0, 0, 24, 0)
        self.tab_btns = []
        self.btn_path = QPushButton("Путь к Minecraft")
        self.btn_path.setCheckable(True)
        self.btn_path.setObjectName("tab_path")
        self.btn_path.setProperty("class", "tab-btn")
        self.btn_logs = QPushButton("Логи приложения")
        self.btn_logs.setCheckable(True)
        self.btn_logs.setObjectName("tab_logs")
        self.btn_logs.setProperty("class", "tab-btn")
        sidebar.addWidget(self.btn_path)
        sidebar.addWidget(self.btn_logs)
        sidebar.addStretch()
        self.tab_btns = [self.btn_path, self.btn_logs]
        main_layout.addLayout(sidebar)
        # Контейнер для контента вкладок
        self.tabs_content = QStackedWidget()
        main_layout.addWidget(self.tabs_content)
        # Вкладка выбора пути
        self.path_tab = QWidget()
        path_layout = QVBoxLayout(self.path_tab)
        self.nick_label = QLabel("Ник:")
        path_layout.addWidget(self.nick_label)
        self.nick_edit = QLineEdit()
        current_nick = self.config_manager.get_active_profile() or ""
        self.nick_edit.setText(current_nick)
        self.nick_edit.setPlaceholderText("Введите ваш ник")
        self.nick_edit.textChanged.connect(self.on_nick_changed)
        path_layout.addWidget(self.nick_edit)
        # Разделитель между ником и папкой Minecraft
        nick_divider = QFrame()
        nick_divider.setFrameShape(QFrame.Shape.HLine)
        nick_divider.setFrameShadow(QFrame.Shadow.Sunken)
        nick_divider.setStyleSheet(f"color: {MC_BORDER}; background: {MC_BORDER}; min-height: 2px; max-height: 2px; margin: 10px 0 10px 0; border: none;")
        path_layout.addWidget(nick_divider)
        self.path_label = QLabel(f"Папка Minecraft: {self.config_manager.get('minecraft_path')}")
        path_layout.addWidget(self.path_label)
        self.choose_btn = QPushButton("Изменить папку Minecraft")
        self.choose_btn.clicked.connect(self.choose_path)
        path_layout.addWidget(self.choose_btn)
        # --- СЕКЦИЯ: Профиль и путь ---
        profile_section = QVBoxLayout()
        profile_section.setSpacing(10)
        profile_section.setContentsMargins(0, 0, 0, 0)
        profile_title = QLabel("<b>Профиль и путь к Minecraft</b>")
        profile_title.setStyleSheet("font-size: 17px; margin-bottom: 6px;")
        profile_section.addWidget(profile_title)
        profile_section.addWidget(self.nick_label)
        profile_section.addWidget(self.nick_edit)
        # Разделитель между ником и папкой Minecraft
        nick_divider = QFrame()
        nick_divider.setFrameShape(QFrame.Shape.HLine)
        nick_divider.setFrameShadow(QFrame.Shadow.Sunken)
        nick_divider.setStyleSheet(f"color: {MC_BORDER}; background: {MC_BORDER}; min-height: 2px; max-height: 2px; margin: 10px 0 10px 0; border: none;")
        profile_section.addWidget(nick_divider)
        profile_section.addWidget(self.path_label)
        profile_section.addWidget(self.choose_btn)
        # --- СЕКЦИЯ: Память ---
        mem_section = QVBoxLayout()
        mem_section.setSpacing(10)
        mem_section.setContentsMargins(0, 16, 0, 0)
        mem_title = QLabel("<b>Параметры запуска</b>")
        mem_title.setStyleSheet("font-size: 17px; margin-bottom: 6px;")
        mem_section.addWidget(mem_title)
        mem_label = QLabel("Оперативная память для Minecraft:")
        mem_section.addWidget(mem_label)
        mem_slider_layout = QHBoxLayout()
        self.memory_slider = QSlider(Qt.Orientation.Horizontal)
        self.memory_slider.setMinimum(0)
        self.memory_slider.setMaximum(7)
        self.memory_slider.setTickInterval(1)
        self.memory_slider.setSingleStep(1)
        self.memory_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.memory_slider.setStyleSheet(f"margin-left:8px; margin-right:8px;")
        self.memory_slider.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.memory_value_label = QLabel()
        self.memory_value_label.setFixedWidth(60)
        mem_gb_values = [0, 1, 2, 4, 6, 8, 12, 16]
        mem_gb_labels = ["Авто", "1 ГБ", "2 ГБ", "4 ГБ", "6 ГБ", "8 ГБ", "12 ГБ", "16 ГБ"]
        saved_mb = int(self.config_manager.get("memory_mb", 0) or 0)
        slider_idx = mem_gb_values.index(saved_mb) if saved_mb in mem_gb_values else 0
        self.memory_slider.setValue(slider_idx)
        self.memory_value_label.setText(mem_gb_labels[slider_idx])
        def on_slider_changed(idx):
            mb = [0, 1024, 2048, 4096, 6144, 8192, 12288, 16384][idx]
            self.config_manager.set("memory_mb", mb)
            self.memory_value_label.setText(mem_gb_labels[idx])
        self.memory_slider.valueChanged.connect(on_slider_changed)
        mem_slider_layout.addWidget(self.memory_slider)
        mem_slider_layout.addWidget(self.memory_value_label)
        mem_section.addLayout(mem_slider_layout)
        # --- Добавляем секции на страницу ---
        path_layout.addLayout(profile_section)
        # Разделитель между секциями (оставляем только между памятью и профилем)
        section_divider = QFrame()
        section_divider.setFrameShape(QFrame.Shape.HLine)
        section_divider.setFrameShadow(QFrame.Shadow.Sunken)
        section_divider.setStyleSheet(f"color: {MC_BORDER}; background: {MC_BORDER}; min-height: 2px; max-height: 2px; margin: 18px 0 12px 0; border: none;")
        path_layout.addWidget(section_divider)
        path_layout.addLayout(mem_section)
        path_layout.addStretch()
        self.tabs_content.addWidget(self.path_tab)
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
        self.tabs_content.addWidget(self.logs_tab)
        # Логика переключения вкладок
        self.btn_path.clicked.connect(lambda: self.set_active_tab(0))
        self.btn_logs.clicked.connect(lambda: self.set_active_tab(1))
        self.set_active_tab(0)
        self.log_file = self._get_latest_log_file()
        self._setup_auto_update()

    def set_active_tab(self, idx):
        for i, btn in enumerate(self.tab_btns):
            btn.setChecked(i == idx)
        self.tabs_content.setCurrentIndex(idx)
        # При переходе на вкладку логов — скроллим вниз
        if idx == 1:
            self.update_log_view(force_scroll_to_bottom=True)

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

    def on_nick_changed(self, new_nick):
        self.config_manager.set_active_profile(new_nick)
        mw = self.window()
        profile_widget = getattr(mw, "profile_widget", None)
        if profile_widget is not None:
            profile_widget.nick.setText(new_nick or "Гость") 