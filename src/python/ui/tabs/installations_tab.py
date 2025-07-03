from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox, 
    QListWidget, QListWidgetItem, QSizePolicy, QDialog, QDialogButtonBox, 
    QMessageBox, QMenu, QTabWidget, QCheckBox, QScrollArea, QFrame, QGridLayout, 
    QGraphicsDropShadowEffect, QProgressBar, QButtonGroup, QStackedWidget, QFileDialog, QTextEdit
)
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, QTimer, QObject, QRectF, Slot, QThread
from PySide6.QtGui import QIcon, QPainter, QBrush, QColor, QPen, QFont, QPixmap
import os
import json
import urllib.request
import threading
from src.python.core.build_manager import BuildManager
from pathlib import Path
import shutil
import requests
import subprocess
import platform
import glob
import uuid

# Цвета из CSS
MC_DARK_GREEN = "#2d6135"
MC_GREEN = "#3a7d44"
MC_LIGHT_GREEN = "#4caf50"
MC_ACCENT = "#ffaa00"
MC_BLUE = "#3a7dcf"
MC_DARK_BLUE = "#2d5ca6"
MC_PURPLE = "#6a3dcf"
MC_RED = "#dc3545"
MC_YELLOW = "#ffc107"
MC_DARK = "#121212"
MC_DARKER = "#0a0a0a"
MC_GRAY = "#1e1e1e"
MC_LIGHT_GRAY = "#2d2d2d"
MC_TEXT = "#e0e0e0"
MC_TEXT_LIGHT = "#ffffff"
MC_TEXT_MUTED = "#b0b0b0"
MC_BORDER = "#333"
MC_PIXEL = "rgba(0, 0, 0, 0.15)"

# Заглушки для тестовых данных
VERSION_TYPES = ["release", "snapshot", "beta", "alpha"]
TYPE_LABELS = {"release": "Release", "snapshot": "Snapshot", "beta": "Beta", "alpha": "Alpha"}

ICON_PATHS = {
    "release": "src/python/ui/icons/release.svg",
    "snapshot": "src/python/ui/icons/snapshot.svg",
    "beta": "src/python/ui/icons/beta.svg",
    "alpha": "src/python/ui/icons/alpha.svg"
}

MOJANG_MANIFEST_URL = "https://launchermeta.mojang.com/mc/game/version_manifest.json"

def get_icon(version_type):
    path = ICON_PATHS.get(version_type)
    if path and os.path.exists(path):
        return QIcon(path)
    return QIcon()  # Пустая иконка-заглушка

class VersionCard(QFrame):
    installed_signal = Signal(dict)
    
    def __init__(self, version, installed=False, parent=None):
        super().__init__(parent)
        self.version = version
        self.setObjectName("VersionCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        
        # Стиль карточки версии
        self.setStyleSheet(f"""
            QFrame#VersionCard {{
                background: {MC_GRAY};
                border: 2px solid {MC_BORDER};
                border-radius: 12px;
                margin: 6px;
            }}
            QFrame#VersionCard:hover {{
                border: 2px solid {MC_GREEN};
                background: rgba(58, 125, 68, 0.1);
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
            }}
            QLabel {{
                color: {MC_TEXT};
            }}
            QPushButton {{
                background: {MC_GREEN};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background: {MC_DARK_GREEN};
            }}
            QPushButton:disabled {{
                background: #444;
                color: #aaa;
            }}
            QProgressBar {{
                height: 6px;
                border-radius: 3px;
                background: rgba(0, 0, 0, 0.3);
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {MC_GREEN}, stop:1 {MC_LIGHT_GREEN});
                border-radius: 3px;
            }}
        """)
        
        # Drop shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(16)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 100))
        self.setGraphicsEffect(shadow)
        
        # Анимация увеличения
        self.anim = QPropertyAnimation(self, b"geometry")
        self.anim.setDuration(120)
        self.anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        self._orig_geom = None
        self.enterEvent = self._on_enter
        self.leaveEvent = self._on_leave
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(15)
        
        # Иконка версии
        icon = QLabel()
        icon.setPixmap(get_icon(version["type"]).pixmap(48, 48))
        layout.addWidget(icon)
        
        # Информация о версии
        info = QVBoxLayout()
        info.setSpacing(4)
        
        name = QLabel(f"<b>{version['name']}</b>")
        name.setStyleSheet(f"font-size: 16px; color: {MC_TEXT_LIGHT};")
        
        vtype = QLabel(TYPE_LABELS.get(version["type"], version["type"]))
        vtype.setStyleSheet(f"font-size: 14px; color: {MC_TEXT_MUTED};")
        
        date = QLabel(version.get("date", ""))
        date.setStyleSheet(f"font-size: 12px; color: {MC_TEXT_MUTED};")
        
        info.addWidget(name)
        info.addWidget(vtype)
        info.addWidget(date)
        layout.addLayout(info)
        
        layout.addStretch()
        
        # Кнопка установки
        self.install_btn = QPushButton("Установить" if not installed else "Установлено")
        self.install_btn.setEnabled(not installed)
        self.install_btn.clicked.connect(self.start_install)
        layout.addWidget(self.install_btn)
        
        # Статус
        self.status_label = QLabel("Установлено" if installed else "Не установлено")
        self.status_label.setStyleSheet(f"font-size: 14px; color: {MC_GREEN if installed else MC_TEXT_MUTED};")
        layout.addWidget(self.status_label)
        
        # Прогресс-бар
        self.progress = QProgressBar()
        self.progress.setMinimum(0)
        self.progress.setMaximum(100)
        self.progress.setValue(0)
        self.progress.setVisible(False)
        self.progress.setFixedWidth(100)
        layout.addWidget(self.progress)
        
        self.timer = None

    def _on_enter(self, event):
        if not self._orig_geom:
            self._orig_geom = self.geometry()
        rect = self.geometry().adjusted(-6, -6, 6, 6)
        self.anim.stop()
        self.anim.setStartValue(self.geometry())
        self.anim.setEndValue(rect)
        self.anim.start()

    def _on_leave(self, event):
        if self._orig_geom:
            self.anim.stop()
            self.anim.setStartValue(self.geometry())
            self.anim.setEndValue(self._orig_geom)
            self.anim.start()

    def start_install(self):
        self.install_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.status_label.setText("Установка...")
        self.status_label.setStyleSheet(f"color: {MC_BLUE};")
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._on_progress)
        self.timer.start(30)

    def _on_progress(self):
        val = self.progress.value() + 2
        if val >= 100:
            self.progress.setValue(100)
            self.progress.setVisible(False)
            self.status_label.setText("Установлено")
            self.status_label.setStyleSheet(f"color: {MC_GREEN};")
            self.install_btn.setText("Установлено")
            self.install_btn.setEnabled(False)
            if self.timer:
                self.timer.stop()
            self.installed_signal.emit(self.version)
        else:
            self.progress.setValue(val)

class InstalledVersionWidget(QWidget):
    remove_requested = Signal(dict)
    
    def __init__(self, version, parent=None):
        super().__init__(parent)
        self.version = version
        
        # Основной стиль виджета
        self.setStyleSheet(f"""
            QWidget {{
                background: {MC_GRAY};
                border-radius: 12px;
                border: 1px solid {MC_BORDER};
                padding: 8px;
            }}
            QLabel {{
                color: {MC_TEXT};
            }}
            QPushButton {{
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 14px;
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)
        
        # Иконка версии
        icon = QLabel()
        icon.setPixmap(get_icon(version["type"]).pixmap(32, 32))
        layout.addWidget(icon)
        
        # Название и тип версии
        name = QLabel(f"<b>{version['name']}</b> [{TYPE_LABELS.get(version['type'], version['type'])}]")
        name.setStyleSheet(f"font-size: 14px; color: {MC_TEXT_LIGHT};")
        layout.addWidget(name)
        
        layout.addStretch()
        
        # Статус
        self.status = QLabel(version.get("status", "Установлено"))
        self.status.setStyleSheet(f"font-size: 13px; color: {MC_GREEN};")
        layout.addWidget(self.status)
        
        # Кнопка запуска
        self.launch_btn = QPushButton("Запустить")
        self.launch_btn.setStyleSheet(f"""
            QPushButton {{
                background: {MC_GREEN};
                color: white;
            }}
            QPushButton:hover {{
                background: {MC_DARK_GREEN};
            }}
        """)
        self.launch_btn.clicked.connect(self.launch)
        layout.addWidget(self.launch_btn)
        
        # Кнопка удаления
        self.delete_btn = QPushButton("Удалить")
        self.delete_btn.setStyleSheet(f"""
            QPushButton {{
                background: {MC_RED};
                color: white;
            }}
            QPushButton:hover {{
                background: #c82333;
            }}
        """)
        self.delete_btn.clicked.connect(self.delete)
        layout.addWidget(self.delete_btn)
    
    def launch(self):
        QMessageBox.information(self, "Запуск", f"Запуск версии {self.version['name']}")
    
    def delete(self):
        reply = QMessageBox.question(
            self, 
            "Удалить версию", 
            f"Удалить версию {self.version['name']}?", 
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.remove_requested.emit(self.version)

class LoaderUpdater(QObject):
    update = Signal(list)

class RoundedPanel(QWidget):
    def __init__(self, parent=None, radius=18, bg_color=MC_GRAY, border_color=MC_BORDER, border_width=2):
        super().__init__(parent)
        self.radius = radius
        self.bg_color = QColor(bg_color)
        self.border_color = QColor(border_color)
        self.border_width = border_width
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAutoFillBackground(False)
        
        # Добавляем эффект размытия фона
        self.setGraphicsEffect(QGraphicsDropShadowEffect(
            blurRadius=15, 
            xOffset=0, 
            yOffset=4, 
            color=QColor(0, 0, 0, 100)
        ))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect())
        rect.adjust(self.border_width/2, self.border_width/2, -self.border_width/2, -self.border_width/2)
        
        # Рисуем фон с прозрачностью
        painter.setBrush(QBrush(QColor(self.bg_color.red(), self.bg_color.green(), self.bg_color.blue(), 200)))
        painter.setPen(QPen(self.border_color, self.border_width))
        painter.drawRoundedRect(rect, self.radius, self.radius)

class BuildWorker(QObject):
    progress = Signal(int, str)
    finished = Signal()
    error = Signal(str)
    log_msg = Signal(str)

    def __init__(self, build_manager, build_config):
        super().__init__()
        self.build_manager = build_manager
        self.build_config = build_config

    def run(self):
        print('BuildWorker.run called')
        def progress_callback(value, text):
            print(f"PROGRESS: {value} {text}")
            self.progress.emit(value, text)
        def log_callback(msg):
            print(f"LOG: {msg}")
            self.log_msg.emit(msg)
        try:
            self.build_manager.create_build(self.build_config, progress_callback, log_callback)
            self.finished.emit()
        except Exception as e:
            print(f"EXCEPTION in BuildWorker.run: {e}")
            self.error.emit(str(e))

class InstallationsTab(QWidget):
    progress_update = Signal(int, str)
    
    def __init__(self, build_manager, minecraft_manager, get_nick_func=None, parent=None):
        super().__init__(parent)
        self.build_manager = build_manager
        self.minecraft_manager = minecraft_manager
        self.get_nick_func = get_nick_func or (lambda: "Player")
        self.threads = []  # Для хранения активных QThread
        self.setup_ui()
        self.update_my_builds()
        
        # Основной стиль вкладки
        self.setStyleSheet(f"""
            QWidget {{
                background: {MC_DARK};
                color: {MC_TEXT};
                font-family: 'Rubik', Arial, sans-serif;
            }}
            QPushButton.sidebar-tab {{
                border-radius: 8px;
                padding: 14px 18px;
                font-size: 16px;
                color: {MC_TEXT_MUTED};
                background: {MC_GRAY};
                border: 2px solid {MC_BORDER};
                margin-bottom: 8px;
                text-align: left;
                font-weight: 500;
                transition: background 0.2s, color 0.2s;
            }}
            QPushButton.sidebar-tab:checked {{
                background: {MC_BLUE};
                color: {MC_TEXT_LIGHT};
                border: 2px solid {MC_BLUE};
                font-weight: bold;
                box-shadow: 0 0 8px 2px rgba(58,125,207,0.25);
            }}
            QPushButton.sidebar-tab:hover {{
                background: {MC_GREEN};
                color: {MC_TEXT_LIGHT};
            }}
        """)

    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(0)
        
        # Sidebar с вкладками
        sidebar = QVBoxLayout()
        sidebar.setSpacing(0)
        sidebar.setContentsMargins(0, 0, 24, 0)
        self.btn_my = QPushButton("Мои сборки")
        self.btn_my.setCheckable(True)
        self.btn_my.setProperty("class", "sidebar-tab")
        self.btn_create = QPushButton("Создать сборку")
        self.btn_create.setCheckable(True)
        self.btn_create.setProperty("class", "sidebar-tab")
        self.btn_ready = QPushButton("Готовые сборки")
        self.btn_ready.setCheckable(True)
        self.btn_ready.setProperty("class", "sidebar-tab")
        sidebar.addWidget(self.btn_my)
        sidebar.addWidget(self.btn_create)
        sidebar.addWidget(self.btn_ready)
        sidebar.addStretch()
        self.sidebar_btns = [self.btn_my, self.btn_create, self.btn_ready]
        main_layout.addLayout(sidebar)
        
        # Контейнер для контента вкладок
        self.tabs_content = QStackedWidget()
        main_layout.addWidget(self.tabs_content)
        
        # Вкладка 'Мои сборки'
        self.my_builds_tab = RoundedPanel()
        my_builds_layout = QVBoxLayout(self.my_builds_tab)
        my_builds_layout.addWidget(QLabel("Здесь будут отображаться ваши сборки", alignment=Qt.AlignmentFlag.AlignCenter))
        self.tabs_content.addWidget(self.my_builds_tab)
        
        # Вкладка 'Создать сборку'
        self.create_tab = QWidget()
        self.setup_create_tab()
        self.tabs_content.addWidget(self.create_tab)
        
        # Вкладка 'Готовые сборки'
        self.ready_tab = RoundedPanel()
        ready_layout = QVBoxLayout(self.ready_tab)
        ready_layout.addWidget(QLabel("Готовые сборки (скоро)", alignment=Qt.AlignmentFlag.AlignCenter))
        self.tabs_content.addWidget(self.ready_tab)
        
        # Логика переключения вкладок
        self.btn_my.clicked.connect(lambda: self.set_active_tab(0))
        self.btn_create.clicked.connect(lambda: self.set_active_tab(1))
        self.btn_ready.clicked.connect(lambda: self.set_active_tab(2))
        self.set_active_tab(0)
        
        # Обработка смены лоадера
        loader_updater = LoaderUpdater()
        
        def update_loader_versions(versions):
            self.loader_ver_combo.clear()
            if versions:
                self.loader_ver_combo.addItems(versions)
            else:
                self.loader_ver_combo.addItem('Версии не найдены')
            update_build_name()
        
        loader_updater.update.connect(update_loader_versions)
        
        def on_loader_changed(text):
            if text == "Vanilla":
                self.loader_ver_combo.clear()
                self.loader_ver_combo.setVisible(False)
                update_build_name()
            elif text == "Fabric":
                self.loader_ver_combo.clear()
                self.loader_ver_combo.setVisible(True)
                mc_version = self.version_combo.currentText()
                def fetch_fabric_versions():
                    versions = self.minecraft_manager.get_fabric_loader_versions(mc_version)
                    loader_updater.update.emit(versions)
                    update_build_name()
                threading.Thread(target=fetch_fabric_versions).start() if mc_version else None
            elif text == "Forge":
                self.loader_ver_combo.clear()
                self.loader_ver_combo.setVisible(True)
                mc_version = self.version_combo.currentText()
                def fetch_forge_versions():
                    versions = self.minecraft_manager.get_forge_loader_versions(mc_version)
                    loader_updater.update.emit(versions)
                    update_build_name()
                threading.Thread(target=fetch_forge_versions).start() if mc_version else None
            elif text == "Quilt":
                self.loader_ver_combo.clear()
                self.loader_ver_combo.setVisible(True)
                mc_version = self.version_combo.currentText()
                def fetch_quilt_versions():
                    versions = self.minecraft_manager.get_quilt_loader_versions(mc_version)
                    loader_updater.update.emit(versions)
                    update_build_name()
                threading.Thread(target=fetch_quilt_versions).start() if mc_version else None
            elif text == "NeoForge":
                self.loader_ver_combo.clear()
                self.loader_ver_combo.setVisible(True)
                mc_version = self.version_combo.currentText()
                def fetch_neoforge_versions():
                    versions = self.minecraft_manager.get_neoforge_loader_versions(mc_version)
                    loader_updater.update.emit(versions)
                    update_build_name()
                threading.Thread(target=fetch_neoforge_versions).start() if mc_version else None
            elif text == "Paper":
                self.loader_ver_combo.clear()
                self.loader_ver_combo.setVisible(True)
                mc_version = self.version_combo.currentText()
                def fetch_paper_versions():
                    versions = self.minecraft_manager.get_paper_versions(mc_version)
                    loader_updater.update.emit(versions)
                    update_build_name()
                threading.Thread(target=fetch_paper_versions).start() if mc_version else None
                self.loader_combo.setToolTip("Paper — только для серверов. Нельзя запускать моды, только плагины!")
            elif text == "Purpur":
                self.loader_ver_combo.clear()
                self.loader_ver_combo.setVisible(True)
                mc_version = self.version_combo.currentText()
                def fetch_purpur_versions():
                    versions = self.minecraft_manager.get_purpur_versions(mc_version)
                    loader_updater.update.emit(versions)
                    update_build_name()
                threading.Thread(target=fetch_purpur_versions).start() if mc_version else None
                self.loader_combo.setToolTip("Purpur — только для серверов. Нельзя запускать моды, только плагины!")
            else:
                self.loader_ver_combo.clear()
                self.loader_ver_combo.addItems(["0.14.21", "0.14.20", "0.14.19"])
                self.loader_ver_combo.setVisible(True)
                update_build_name()
        
        self.loader_combo.currentTextChanged.connect(on_loader_changed)
        
        # При смене версии Minecraft, если выбран Fabric, обновлять список версий лоадера
        def on_mc_version_changed():
            on_loader_changed(self.loader_combo.currentText())
        self.version_combo.currentTextChanged.connect(lambda _: on_mc_version_changed())
        
        # Всплывающая подсказка при наведении на Paper/Purpur
        def show_loader_tooltip(index):
            text = self.loader_combo.itemText(index)
            if text == "Paper":
                self.loader_combo.setToolTip("Paper — только для серверов. Нельзя запускать моды, только плагины!")
            elif text == "Purpur":
                self.loader_combo.setToolTip("Purpur — только для серверов. Нельзя запускать моды, только плагины!")
            else:
                self.loader_combo.setToolTip("")
        
        self.loader_combo.highlighted.connect(show_loader_tooltip)
        
        # Автоматическое формирование названия сборки
        def update_build_name():
            mc_version = self.version_combo.currentText()
            loader = self.loader_combo.currentText()
            
            if not mc_version:
                return
            
            if loader == "Vanilla":
                build_name = f"Minecraft {mc_version}"
            else:
                build_name = f"Minecraft {mc_version} with {loader}"
            
            self.name_edit.setText(build_name)
        
        # Подключаем обновление названия к изменениям в комбобоксах
        self.version_combo.currentTextChanged.connect(lambda _: update_build_name())
        self.loader_combo.currentTextChanged.connect(lambda _: update_build_name())
        self.loader_ver_combo.currentTextChanged.connect(lambda _: update_build_name())
        
        # Скрыть loader_ver_combo при инициализации, если выбран Vanilla
        if self.loader_combo.currentText() == "Vanilla":
            self.loader_ver_combo.setVisible(False)
        
        # Инициализируем название при загрузке
        if self.version_combo.count() > 0:
            update_build_name()

    def setup_create_tab(self):
        from PySide6.QtWidgets import QFileDialog
        from PySide6.QtGui import QPixmap
        form_outer = QVBoxLayout(self.create_tab)
        form_outer.setContentsMargins(24, 24, 24, 24)
        form_outer.setSpacing(18)
        top_layout = QHBoxLayout()
        top_layout.setSpacing(20)
        # Превью и кнопка выбора картинки
        img_layout = QVBoxLayout()
        self.image_preview = QLabel()
        self.image_preview.setFixedSize(120, 120)
        self.image_preview.setStyleSheet(f"""
            background: {MC_GRAY};
            border: 2.5px solid {MC_BORDER};
            border-radius: 8px;
            font-size: 16px;
            color: {MC_TEXT_MUTED};
            qproperty-alignment: AlignCenter;
        """)
        self.image_preview.setText("Нет картинки")
        img_layout.addWidget(self.image_preview)
        self.select_img_btn = QPushButton("Выбрать картинку")
        self.select_img_btn.setStyleSheet(f"padding: 6px 16px; margin-top: 8px;")
        img_layout.addWidget(self.select_img_btn)
        self.selected_image_path = None
        def choose_image():
            file, _ = QFileDialog.getOpenFileName(self.create_tab, "Выберите картинку", "", "Images (*.png *.jpg *.jpeg *.bmp)")
            if file:
                self.selected_image_path = file
                pixmap = QPixmap(file)
                if not pixmap.isNull():
                    self.image_preview.setPixmap(pixmap.scaled(120, 120, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                else:
                    self.image_preview.setText("Ошибка картинки")
        self.select_img_btn.clicked.connect(choose_image)
        top_layout.addLayout(img_layout)
        
        # Поля формы
        fields_layout = QVBoxLayout()
        fields_layout.setSpacing(14)
        
        # Поле названия сборки
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Название сборки")
        self.name_edit.setStyleSheet(f"""
            font-size: 16px;
            padding: 10px;
            border-radius: 8px;
            border: 2px solid {MC_BORDER};
            background: {MC_GRAY};
            color: {MC_TEXT_LIGHT};
        """)
        fields_layout.addWidget(self.name_edit)
        
        # Комбобокс версии Minecraft
        self.version_combo = QComboBox()
        all_versions = self.minecraft_manager.get_available_versions()
        release_versions = [v["id"] for v in all_versions if v["type"] == "release"]
        self.version_combo.addItems(release_versions)
        self.version_combo.setStyleSheet(f"""
            QComboBox {{
                background: {MC_GRAY};
                border: 2px solid {MC_BORDER};
                border-radius: 8px;
                color: {MC_TEXT_LIGHT};
                font-size: 16px;
                padding: 10px;
            }}
            QComboBox::drop-down {{
                border: none;
                background: transparent;
            }}
            QComboBox QAbstractItemView {{
                background: {MC_GRAY};
                color: {MC_TEXT_LIGHT};
                border: 2px solid {MC_BORDER};
                selection-background-color: rgba(58, 125, 207, 0.3);
                selection-color: {MC_TEXT_LIGHT};
                outline: 0;
            }}
        """)
        
        # Комбобокс лоадера
        self.loader_combo = QComboBox()
        self.loader_combo.addItems(["Vanilla", "Fabric", "Forge", "NeoForge", "Quilt"])
        self.loader_combo.setStyleSheet(self.version_combo.styleSheet())
        
        # Комбобокс версии лоадера
        self.loader_ver_combo = QComboBox()
        self.loader_ver_combo.addItems(["0.14.21", "0.14.20", "0.14.19"])
        self.loader_ver_combo.setStyleSheet(self.version_combo.styleSheet())
        
        fields_layout.addWidget(self.version_combo)
        fields_layout.addWidget(self.loader_combo)
        fields_layout.addWidget(self.loader_ver_combo)
        top_layout.addLayout(fields_layout)
        form_outer.addLayout(top_layout)
        
        # Логи процесса
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFixedHeight(120)
        self.log_text.setStyleSheet(f"""
            background: {MC_GRAY};
            border: 2px solid {MC_BORDER};
            border-radius: 8px;
            color: {MC_TEXT_LIGHT};
            font-size: 14px;
            padding: 8px;
        """)
        form_outer.addWidget(self.log_text)
        form_outer.addStretch()
        
        # Кнопка создания и прогресс-бар
        create_btn = QPushButton("Создать сборку")
        create_btn.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {MC_BLUE}, stop:1 {MC_PURPLE});
            color: white;
            border-radius: 8px;
            font-weight: bold;
            font-size: 18px;
            padding: 12px 24px;
            border: none;
        """)
        create_btn.setMinimumHeight(48)
        create_btn.clicked.connect(self.create_build)
        form_outer.addWidget(create_btn)
        
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setStyleSheet(f"""
            height: 8px;
            border-radius: 4px;
            background: {MC_GRAY};
            border: 1px solid {MC_BORDER};
        """)
        self.progress.setTextVisible(False)
        self.progress.setVisible(False)
        form_outer.addWidget(self.progress)

    @Slot(int, str)
    def _on_progress_update(self, value, text):
        if value < 0:
            self.progress.setValue(0)
            self.progress.setVisible(False)
        else:
            self.progress.setValue(value)
            self.progress.setVisible(True)

    def update_my_builds(self):
        from pathlib import Path
        import os
        from PySide6.QtGui import QPixmap
        from PySide6.QtWidgets import QScrollArea, QWidget, QVBoxLayout, QHBoxLayout
        # Удаляем старый scroll_area, если есть
        if hasattr(self, 'scroll_area') and self.scroll_area:
            layout = self.my_builds_tab.layout() or QVBoxLayout(self.my_builds_tab)
            layout.removeWidget(self.scroll_area)
            self.scroll_area.deleteLater()
            self.scroll_area = None
        # Создаём scroll area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet(f"background: transparent; border: none;")
        content_widget = QWidget()
        vbox = QVBoxLayout(content_widget)
        vbox.setContentsMargins(12, 12, 12, 12)
        vbox.setSpacing(16)
        # Получить список сборок из папки versions
        versions_path = self.build_manager.config_manager.get_versions_path()
        builds = []
        for folder in os.listdir(versions_path):
            build_dir = Path(versions_path) / folder
            if build_dir.is_dir():
                builds.append(folder)
        if not builds:
            vbox.addWidget(QLabel("У вас пока нет сборок", alignment=Qt.AlignmentFlag.AlignCenter))
        else:
            for build in builds:
                build_dir = Path(versions_path) / build
                # Картинка
                img_path = None
                for ext in ('.png', '.jpg', '.jpeg', '.bmp'):
                    candidate = build_dir / f"{build}{ext}"
                    if candidate.exists():
                        img_path = candidate
                        break
                # Проверка целостности сборки
                errors = []
                json_path = build_dir / f"{build}.json"
                jar_path = build_dir / f"{build}.jar"
                if not json_path.exists():
                    errors.append("Нет JSON-файла версии")
                if not jar_path.exists():
                    errors.append("Нет jar-файла версии")
                missing_libs = []
                if json_path.exists():
                    import json
                    with open(json_path, encoding="utf-8") as f:
                        version_json = json.load(f)
                    libs_dir = Path(self.build_manager.config_manager.get('minecraft_path')) / "libraries"
                    for lib in version_json.get('libraries', []):
                        artifact = lib.get('downloads', {}).get('artifact')
                        if artifact:
                            lib_path = libs_dir / artifact['path']
                            if not lib_path.exists():
                                missing_libs.append(str(lib_path))
                    if missing_libs:
                        errors.append(f"Нет библиотек: {len(missing_libs)} шт.")
                # Карточка
                card = QFrame()
                card.setStyleSheet(f"""
                    QFrame {{
                        background: {MC_GRAY};
                        border: 2px solid {MC_BORDER};
                        border-radius: 12px;
                        margin: 0px;
                        padding: 10px 18px;
                    }}
                """)
                card_layout = QHBoxLayout(card)
                card_layout.setContentsMargins(10, 8, 10, 8)
                card_layout.setSpacing(18)
                # Картинка превью
                img_label = QLabel()
                img_label.setFixedSize(64, 64)
                if img_path:
                    pixmap = QPixmap(str(img_path))
                    img_label.setPixmap(pixmap.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                else:
                    img_label.setText("Нет\nкартинки")
                    img_label.setStyleSheet(f"color: {MC_TEXT_MUTED}; font-size: 12px;")
                card_layout.addWidget(img_label)
                # Если есть ошибки — выводим предупреждение
                if errors:
                    err_label = QLabel("<br>".join(errors))
                    err_label.setStyleSheet("color: #e74c3c; font-size: 13px; font-weight: bold;")
                    card_layout.addWidget(err_label)
                # Вертикальный layout для названия и кнопок
                info_vbox = QVBoxLayout()
                info_vbox.setSpacing(8)
                # Название
                name_label = QLabel(f"<b>{build}</b>")
                name_label.setStyleSheet(f"font-size: 18px; color: {MC_TEXT_LIGHT};")
                info_vbox.addWidget(name_label)
                # Горизонтальный layout для кнопок
                btns_hbox = QHBoxLayout()
                btns_hbox.setSpacing(12)
                # Кнопка Играть
                play_btn = QPushButton("Играть")
                play_btn.setObjectName("playBtn")
                play_btn.setStyleSheet(
                    "QPushButton#playBtn {"
                    "padding: 8px 18px;"
                    "border-radius: 8px;"
                    "background: #3a7d44;"
                    "color: white;"
                    "font-weight: bold;"
                    "border: none;"
                    "transition: background 0.2s, box-shadow 0.2s;"
                    "}"
                    "QPushButton#playBtn:hover {"
                    "background: #2d6135;"
                    "box-shadow: 0 0 12px 2px rgba(58,125,68,0.25);"
                    "}"
                )
                def launch_selected_build():
                    import shutil
                    build_dir = Path(versions_path) / build
                    json_path = build_dir / f"{build}.json"
                    jar_path = build_dir / f"{build}.jar"
                    # Проверка наличия java
                    java_path_setting = self.build_manager.config_manager.get('java_path', 'auto')
                    java_path = None
                    if java_path_setting and java_path_setting != 'auto':
                        java_path = shutil.which(java_path_setting)
                    if not java_path:
                        # Пробуем найти java в PATH
                        java_path = shutil.which('java')
                    if not java_path and platform.system() == 'Windows':
                        # Пробуем найти javaw.exe/java.exe в Program Files на всех дисках
                        candidates = []
                        drives = [f'{chr(d)}:' for d in range(67, 91) if os.path.exists(f'{chr(d)}:')]  # C: ... Z:
                        for drive in drives:
                            for pf_base in ['Program Files', 'Program Files (x86)']:
                                pf = os.path.join(drive + '\\', pf_base)
                                if os.path.exists(pf):
                                    candidates += glob.glob(os.path.join(pf, 'Java', '*', 'bin', 'java.exe'))
                                    candidates += glob.glob(os.path.join(pf, 'Java', '*', 'bin', 'javaw.exe'))
                        if candidates:
                            java_path = candidates[0]
                    if java_path:
                        # Сохраняем найденный путь для будущих запусков
                        self.build_manager.config_manager.set('java_path', java_path)
                    if not java_path:
                        self.append_log('Java не найдена! Установите Java 17+ и добавьте в PATH или настройте путь в настройках.')
                        return
                    # Проверка jar-файла
                    if not json_path.exists() or not jar_path.exists():
                        self.append_log(f'Не найден json или jar-файл: {json_path}, {jar_path}')
                        return
                    try:
                        with open(json_path, encoding="utf-8") as f:
                            version_json = json.load(f)
                        # 1. Собираем classpath
                        libraries = []
                        libs_dir = Path(self.build_manager.config_manager.get('minecraft_path')) / "libraries"
                        for lib in version_json.get("libraries", []):
                            artifact = lib.get("downloads", {}).get("artifact")
                            if artifact:
                                lib_path = libs_dir / artifact["path"]
                                if not lib_path.exists():
                                    self.append_log(f'Библиотека не найдена: {lib_path}')
                                libraries.append(str(lib_path))
                        classpath = os.pathsep.join(libraries + [str(jar_path)])
                        # 2. Получаем mainClass
                        main_class = version_json.get("mainClass")
                        if not main_class:
                            self.append_log('mainClass не найден в json')
                            return
                        # 3. Формируем переменные для подстановки (ОФФЛАЙН-РЕЖИМ)
                        nick = self.get_nick_func() if callable(self.get_nick_func) else "Player"
                        # Оффлайн UUID (uuid3 по нику)
                        offline_uuid = str(uuid.uuid3(uuid.NAMESPACE_DNS, str(nick)))
                        args = {
                            "auth_player_name": nick,
                            "version_name": build,
                            "game_directory": str(build_dir),
                            "assets_root": str(Path(self.build_manager.config_manager.get('minecraft_path')) / "assets"),
                            "assets_index_name": version_json.get("assetIndex", {}).get("id", ""),
                            "auth_uuid": offline_uuid,
                            "auth_access_token": "0",  # Оффлайн-режим
                            "clientid": "",
                            "auth_xuid": "",
                            "user_type": "legacy",  # Оффлайн-режим
                            "user_properties": "{}",
                            "version_type": version_json.get("type", "release"),
                            "resolution_width": 854,
                            "resolution_height": 480,
                            "natives_directory": str(build_dir / "natives"),
                            "launcher_name": "TKML",
                            "launcher_version": "1.0",
                            "classpath": classpath,
                        }
                        # Добавляем все ключи из version_json для безопасной подстановки (например, quickPlayPath)
                        for k, v in version_json.items():
                            if k not in args:
                                args[k] = v
                        # 4. Собираем JVM arguments
                        memory_mb = self.build_manager.config_manager.get('memory_mb', 0)
                        jvm_args = []
                        if memory_mb and str(memory_mb).isdigit() and int(memory_mb) > 0:
                            jvm_args.append(f'-Xmx{int(memory_mb)}M')
                        for item in version_json.get("arguments", {}).get("jvm", []):
                            if isinstance(item, str):
                                jvm_args.append(item)
                            elif isinstance(item, dict):
                                rules = item.get("rules")
                                allowed = True
                                if rules:
                                    allowed = False
                                    for rule in rules:
                                        if rule.get("action") == "allow":
                                            os_rule = rule.get("os", {})
                                            if not os_rule or os_rule.get("name") == "windows":
                                                allowed = True
                                        if rule.get("action") == "disallow":
                                            os_rule = rule.get("os", {})
                                            if os_rule.get("name") == "windows":
                                                allowed = False
                                if allowed:
                                    value = item.get("value")
                                    if isinstance(value, list):
                                        jvm_args.extend(value)
                                    else:
                                        jvm_args.append(value)
                        # Безопасная подстановка: если переменной нет — пустая строка
                        def safe_format(s):
                            try:
                                return s.replace('${', '{').format_map(DefaultDictEmpty(args))
                            except Exception as e:
                                self.append_log(f'Ошибка подстановки аргумента: {e}')
                                return s
                        class DefaultDictEmpty(dict):
                            def __missing__(self, key):
                                return ''
                        jvm_args = [safe_format(v) if isinstance(v, str) else v for v in jvm_args]
                        # 5. Собираем game arguments
                        game_args = []
                        for item in version_json.get("arguments", {}).get("game", []):
                            if isinstance(item, str):
                                game_args.append(item)
                            elif isinstance(item, dict):
                                rules = item.get("rules")
                                allowed = True
                                if rules:
                                    allowed = False
                                    for rule in rules:
                                        if rule.get("action") == "allow":
                                            allowed = True
                                        if rule.get("action") == "disallow":
                                            allowed = False
                                if allowed:
                                    value = item.get("value")
                                    if isinstance(value, list):
                                        game_args.extend(value)
                                    else:
                                        game_args.append(value)
                        # Удаляем --demo и связанные параметры, если они есть
                        game_args = [arg for arg in game_args if not (isinstance(arg, str) and arg.strip().startswith("--demo"))]
                        game_args = [safe_format(v) if isinstance(v, str) else v for v in game_args]
                        # 6. Запуск процесса с выводом stdout/stderr
                        cmd = [java_path] + jvm_args + [main_class] + game_args
                        self.append_log(f'Запуск: {' '.join(cmd)}')
                        proc = subprocess.Popen(cmd, cwd=str(build_dir), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                        out, err = proc.communicate()
                        if out:
                            self.append_log(out)
                        if err:
                            self.append_log(err)
                        if proc.returncode == 0:
                            self.append_log('Minecraft успешно запущен (или завершён без ошибок).')
                        else:
                            self.append_log(f'Процесс завершился с ошибкой (код {proc.returncode})')
                    except Exception as e:
                        self.append_log(f'Ошибка запуска: {e}')
                play_btn.clicked.connect(launch_selected_build)
                btns_hbox.addWidget(play_btn)
                # Кнопка Настройки
                settings_btn = QPushButton("Настройки")
                settings_btn.setObjectName("settingsBtn")
                settings_btn.setStyleSheet(
                    "QPushButton#settingsBtn {"
                    "padding: 8px 18px;"
                    "border-radius: 8px;"
                    "background: #3a7dcf;"
                    "color: white;"
                    "font-weight: bold;"
                    "border: none;"
                    "transition: background 0.2s, box-shadow 0.2s;"
                    "}"
                    "QPushButton#settingsBtn:hover {"
                    "background: #2d5ca6;"
                    "box-shadow: 0 0 12px 2px rgba(58,125,207,0.18);"
                    "}"
                )
                settings_btn.clicked.connect(lambda _, b=build: print(f'Настройки: {b}'))
                btns_hbox.addWidget(settings_btn)
                btns_hbox.addStretch()
                info_vbox.addLayout(btns_hbox)
                info_vbox.addStretch()
                card_layout.addLayout(info_vbox)
                vbox.addWidget(card)
        vbox.addStretch()
        self.scroll_area.setWidget(content_widget)
        # Очищаем и добавляем scroll_area в my_builds_tab
        layout = self.my_builds_tab.layout() or QVBoxLayout(self.my_builds_tab)
        for i in reversed(range(layout.count())):
            item = layout.itemAt(i)
            widget = item.widget() if item else None
            if widget is not None:
                widget.setParent(None)
        layout.addWidget(self.scroll_area)

    def append_log(self, text):
        self.log_text.append(text)
        # Пишем в logs/tmkl.log относительно настроек пользователя
        log_dir = self.build_manager.config_manager.get_logs_path()
        log_file = log_dir / 'tmkl.log'
        log_dir.mkdir(parents=True, exist_ok=True)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(text + "\n")

    def create_build(self):
        from pathlib import Path
        import shutil
        import os
        import requests
        import json
        print('create_build (InstallationsTab) called')
        name = self.name_edit.text().strip()
        mc_version = self.version_combo.currentText()
        print(f'mc_version: {mc_version}')
        if not name:
            self.append_log('Укажите название сборки!')
            return
        if not mc_version:
            self.append_log('Выберите версию Minecraft!')
            return
        # Получаем путь к папке версий
        versions_path = self.build_manager.config_manager.get_versions_path()
        build_dir = Path(versions_path) / name.replace(' ', '_')
        try:
            build_dir.mkdir(parents=True, exist_ok=True)
            self.append_log(f'Папка сборки создана: {build_dir}')
            # Копируем картинку, если выбрана
            if self.selected_image_path:
                ext = os.path.splitext(self.selected_image_path)[1]
                img_dst = build_dir / f"{name.replace(' ', '_')}{ext}"
                shutil.copy2(self.selected_image_path, img_dst)
                self.append_log(f'Картинка скопирована: {img_dst}')
            # Скачиваем JSON-файл версии
            all_versions = self.build_manager.minecraft_manager.get_available_versions()
            version_info = next((v for v in all_versions if v.get('id') == mc_version), None)
            print(f'version_info: {version_info}')
            if not version_info or 'url' not in version_info:
                self.append_log(f'Не удалось получить ссылку на JSON-файл версии: {mc_version}')
                print('all_versions:', all_versions)
                return
            json_url = version_info['url']
            json_dst = build_dir / f"{name.replace(' ', '_')}.json"
            self.append_log(f'Скачивание JSON-файла версии: {json_url} → {json_dst}')
            resp = requests.get(json_url, timeout=30)
            resp.raise_for_status()
            with open(json_dst, 'w', encoding='utf-8') as f:
                f.write(resp.text)
            self.append_log(f'JSON-файл успешно загружен: {json_dst}')
            # Парсим JSON и ищем ссылку на jar
            version_json = json.loads(resp.text)
            jar_url = version_json.get('downloads', {}).get('client', {}).get('url')
            if not jar_url:
                self.append_log(f'Не найден URL jar-файла в JSON для версии: {mc_version}')
                return
            jar_dst = build_dir / f"{name.replace(' ', '_')}.jar"
            self.append_log(f'Скачивание jar-файла: {jar_url} → {jar_dst}')
            resp_jar = requests.get(jar_url, stream=True, timeout=30)
            resp_jar.raise_for_status()
            with open(jar_dst, 'wb') as f:
                for chunk in resp_jar.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            self.append_log(f'jar-файл успешно загружен: {jar_dst}')
            # Скачиваем библиотеки
            libs_dir = Path(self.build_manager.config_manager.get('minecraft_path')) / "libraries"
            for lib in version_json.get('libraries', []):
                artifact = lib.get('downloads', {}).get('artifact')
                if artifact:
                    url = artifact.get('url')
                    path = libs_dir / artifact['path']
                    if not path.exists():
                        path.parent.mkdir(parents=True, exist_ok=True)
                        try:
                            r = requests.get(url, timeout=30)
                            r.raise_for_status()
                            with open(path, 'wb') as f:
                                f.write(r.content)
                            self.append_log(f'Скачана библиотека: {path}')
                        except Exception as e:
                            self.append_log(f'Ошибка скачивания {url}: {e}')
                    else:
                        self.append_log(f'Библиотека уже есть: {path}')
        except Exception as e:
            self.append_log(f'Ошибка: {e}')
        self.progress.setValue(100)
        self.progress.setVisible(True)

    def set_active_tab(self, idx):
        for i, btn in enumerate(self.sidebar_btns):
            btn.setChecked(i == idx)
        self.tabs_content.setCurrentIndex(idx)