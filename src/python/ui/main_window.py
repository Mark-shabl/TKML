"""
Главное окно лаунчера
Основной интерфейс приложения
"""

from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QPushButton, QLabel, QMessageBox, QSizePolicy, QFrame, QStackedWidget, QGridLayout, QDialog
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from loguru import logger
from ui.tabs.profiles_tab import ProfilesTab, get_avatar_pixmap
from ui.tabs.installations_tab import InstallationsTab
from ui.tabs.settings_tab import SettingsTab
from core.minecraft_manager import MinecraftManager
from core.build_manager import BuildManager

# Цветовые константы для единого стиля
MC_DARK = "#121212"
MC_GRAY = "#1e1e1e"
MC_TEXT = "#e0e0e0"
MC_TEXT_LIGHT = "#ffffff"
MC_TEXT_MUTED = "#b0b0b0"
MC_BORDER = "#333"
MC_BLUE = "#3a7dcf"
MC_GREEN = "#3a7d44"


class ProfileWidget(QFrame):
    def __init__(self, config_manager, on_click=None, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.on_click = on_click
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("background: #232323; border-radius: 10px; padding: 8px;")
        layout = QHBoxLayout(self)
        active = self.config_manager.get_active_profile()
        pixmap = get_avatar_pixmap(active, 40)
        self.avatar = QLabel()
        self.avatar.setPixmap(pixmap)
        layout.addWidget(self.avatar)
        self.nick = QLabel(active or "Гость")
        self.nick.setStyleSheet("color: white; font-weight: bold; font-size: 16px;")
        layout.addWidget(self.nick)
        layout.addStretch()
        self.setCursor(Qt.CursorShape.PointingHandCursor)
    def mousePressEvent(self, event):
        if self.on_click:
            self.on_click()


class MainWidget(QWidget):
    def __init__(self, config_manager, theme_manager, minecraft_manager, profiles_tab, installations_tab, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.theme_manager = theme_manager
        self.minecraft_manager = minecraft_manager
        self.profiles_tab = profiles_tab
        self.installations_tab = installations_tab
        layout = QVBoxLayout(self)
        # Верхние крупные кнопки
        top_btns = QHBoxLayout()
        self.btn_home = QPushButton("Главная")
        self.btn_home.setStyleSheet("font-size: 16px; padding: 10px 24px; border-radius: 8px;")
        self.btn_install = QPushButton("Установки")
        self.btn_install.setStyleSheet("font-size: 16px; padding: 10px 24px; border-radius: 8px;")
        self.btn_mybuilds = QPushButton("Мои сборки")
        self.btn_mybuilds.setStyleSheet("font-size: 16px; padding: 10px 24px; border-radius: 8px;")
        top_btns.addWidget(self.btn_home)
        top_btns.addWidget(self.btn_install)
        top_btns.addWidget(self.btn_mybuilds)
        top_btns.addStretch()
        layout.addLayout(top_btns)
        # Стек для разделов
        self.stack = QStackedWidget()
        self.page_home = QWidget()  # Пустая главная
        self.page_install = installations_tab
        self.page_mybuilds = QWidget()  # Заглушка
        self.stack.addWidget(self.page_home)
        self.stack.addWidget(self.page_install)
        self.stack.addWidget(self.page_mybuilds)
        layout.addWidget(self.stack)
        # Сигналы
        self.btn_home.clicked.connect(lambda: self.stack.setCurrentWidget(self.page_home))
        self.btn_install.clicked.connect(lambda: self.stack.setCurrentWidget(self.page_install))
        self.btn_mybuilds.clicked.connect(lambda: self.stack.setCurrentWidget(self.page_mybuilds))


class HomePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        # Кнопки "Мои сборки", "Создать сборку", "Готовые сборки"
        tabs_layout = QHBoxLayout()
        self.btn_my = QPushButton("Мои сборки")
        self.btn_create = QPushButton("Создать сборку")
        self.btn_ready = QPushButton("Готовые сборки")
        for btn in [self.btn_my, self.btn_create, self.btn_ready]:
            btn.setStyleSheet("font-size: 15px; padding: 8px 18px; border-radius: 8px;")
            tabs_layout.addWidget(btn)
        tabs_layout.addStretch()
        layout.addLayout(tabs_layout)
        # Сетка карточек (заглушки)
        grid = QGridLayout()
        for i in range(2):
            for j in range(3):
                card = QFrame()
                card.setStyleSheet("border: 1px solid #aaa; border-radius: 8px; min-width: 160px; min-height: 120px;")
                vbox = QVBoxLayout(card)
                vbox.addWidget(QLabel(f"1.21.{i*3+j+1}"))
                vbox.addWidget(QLabel("Описание"))
                play_btn = QPushButton("Играть")
                vbox.addWidget(play_btn)
                grid.addWidget(card, i, j)
        layout.addLayout(grid)


class MainWindow(QMainWindow):
    """Главное окно лаунчера"""
    
    def __init__(self, config_manager, theme_manager):
        """Инициализация главного окна"""
        super().__init__()
        
        self.config_manager = config_manager
        self.theme_manager = theme_manager
        
        # Настройка окна
        self.setWindowTitle("TMKL - The Minecraft Launcher")
        self.setMinimumSize(1000, 700)
        
        # Восстанавливаем размер окна
        width = self.config_manager.get("window_width", 1200)
        height = self.config_manager.get("window_height", 800)
        self.resize(width, height)
        
        # Создание интерфейса
        self.setup_ui()
        
        logger.info("Главное окно инициализировано")
    
    def setup_ui(self):
        """Настройка пользовательского интерфейса"""
        # Центральный виджет
        central_widget = QWidget()
        central_widget.setStyleSheet("background: #23272e; border-radius: 24px; border: none;")
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        # Боковое меню
        sidebar = QVBoxLayout()
        sidebar.setAlignment(Qt.AlignmentFlag.AlignTop)
        sidebar_widget = QWidget()
        sidebar_widget.setStyleSheet(f"""
            background: #232323;
            min-width: 180px;
            max-width: 220px;
        """)
        sidebar_widget.setLayout(sidebar)
        # Профиль
        self.profile_widget = ProfileWidget(self.config_manager, on_click=self.goto_profiles)
        sidebar.addWidget(self.profile_widget)
        sidebar.addSpacing(16)
        # Стили для кнопок боковой панели
        sidebar_btn_style = f'''
            QPushButton[sidebar="true"] {{
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
            QPushButton[sidebar="true"]:checked {{
                background: {MC_BLUE};
                color: {MC_TEXT_LIGHT};
                border: 2px solid {MC_BLUE};
                font-weight: bold;
                box-shadow: 0 0 8px 2px rgba(58,125,207,0.25);
            }}
            QPushButton[sidebar="true"]:hover {{
                background: {MC_GREEN};
                color: {MC_TEXT_LIGHT};
            }}
        '''
        self.setStyleSheet(self.styleSheet() + sidebar_btn_style)
        # Кнопки боковой панели
        self.home_btn = QPushButton("Главная")
        self.home_btn.setCheckable(True)
        self.home_btn.setProperty("sidebar", True)
        sidebar.addWidget(self.home_btn)
        self.install_btn = QPushButton("Установки")
        self.install_btn.setCheckable(True)
        self.install_btn.setProperty("sidebar", True)
        sidebar.addWidget(self.install_btn)
        sidebar.addStretch()
        self.news_btn = QPushButton("Что нового")
        self.news_btn.setCheckable(True)
        self.news_btn.setProperty("sidebar", True)
        self.settings_btn = QPushButton("Настройки")
        self.settings_btn.setCheckable(True)
        self.settings_btn.setProperty("sidebar", True)
        sidebar.addWidget(self.news_btn)
        sidebar.addWidget(self.settings_btn)
        # Группа для эксклюзивного выбора
        self.sidebar_btns = [self.home_btn, self.install_btn, self.news_btn, self.settings_btn]
        def set_active_sidebar(idx):
            for i, btn in enumerate(self.sidebar_btns):
                btn.setChecked(i == idx)
        # Основная часть
        content_layout = QVBoxLayout()
        header_layout = QHBoxLayout()
        title_label = QLabel("TMKL - The Minecraft Launcher")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; margin: 20px;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        content_layout.addLayout(header_layout)
        # QStackedWidget для главной и установок
        self.stack = QStackedWidget()
        self.page_home = QWidget()  # Пустая главная
        # Создание InstallationsTab с передачей функции получения ника
        def get_active_nick():
            return self.profile_widget.nick.text() if self.profile_widget.nick.text() != "Гость" else "Player"
        minecraft_manager = MinecraftManager(self.config_manager)
        build_manager = BuildManager(self.config_manager, minecraft_manager)
        self.installations_tab = InstallationsTab(build_manager, minecraft_manager, get_nick_func=get_active_nick)
        self.settings_tab = SettingsTab(self.config_manager, build_manager)
        self.stack.addWidget(self.page_home)
        self.stack.addWidget(self.installations_tab)
        self.stack.addWidget(self.settings_tab)
        content_layout.addWidget(self.stack)
        main_layout.addWidget(sidebar_widget)
        main_layout.addLayout(content_layout)
        # Сигналы для переключения страниц и выделения активной кнопки
        self.home_btn.clicked.connect(lambda: [self.stack.setCurrentWidget(self.page_home), set_active_sidebar(0)])
        self.install_btn.clicked.connect(lambda: [self.stack.setCurrentWidget(self.installations_tab), set_active_sidebar(1)])
        self.news_btn.clicked.connect(lambda: set_active_sidebar(2))
        self.settings_btn.clicked.connect(lambda: [self.stack.setCurrentWidget(self.settings_tab), set_active_sidebar(3)])
        set_active_sidebar(0)

    def update_play_button(self):
        """Включает или выключает кнопку 'ИГРАТЬ' в зависимости от наличия профиля"""
        profiles = self.config_manager.profiles.get("profiles", {})
        active = self.config_manager.get_active_profile()
        enabled = bool(profiles) and active in profiles
        # self.play_button.setEnabled(enabled)

    def on_play_clicked(self):
        profiles = self.config_manager.profiles.get("profiles", {})
        active = self.config_manager.get_active_profile()
        if not profiles or not active or active not in profiles:
            # Переключаемся на вкладку профилей
            self.stack.setCurrentWidget(self.page_home)
            QMessageBox.information(self, "Нет профиля", "Создайте профиль для начала игры.")
            return
        
        # Получаем выбранную версию из активной вкладки
        current_tab = self.stack.currentWidget()
        # Здесь будет запуск игры
        QMessageBox.information(self, "Запуск", f"Запуск игры за {active}")

    def toggle_theme(self):
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        self.theme_manager.toggle_theme(app)

    def goto_profiles(self):
        self.stack.setCurrentWidget(self.page_home)
