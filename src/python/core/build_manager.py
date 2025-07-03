"""
Менеджер сборок Minecraft
Управление созданием, загрузкой и установкой сборок
"""

import os
import json
import shutil
import requests
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from loguru import logger
import zipfile
import tempfile
import time


class BuildManager:
    """Менеджер для работы со сборками Minecraft"""
    
    def __init__(self, config_manager, minecraft_manager):
        """Инициализация менеджера сборок"""
        self.config_manager = config_manager
        self.minecraft_manager = minecraft_manager
        self.minecraft_path = Path(self.config_manager.get("minecraft_path"))
        
        # Создаем структуру папок
        self.instances_path = self.config_manager.get_instances_path()
        self.versions_path = self.config_manager.get_versions_path()
        self.libraries_path = self.config_manager.get_libraries_path()
        self.assets_path = self.config_manager.get_assets_path()
        self.logs_path = self.config_manager.get_logs_path()
        self.config_path = self.config_manager.get_config_path()
        self.temp_path = self.config_manager.get_temp_path()
        
        # Создаем необходимые директории
        self._create_directory_structure()
        
        logger.info("BuildManager инициализирован")
    
    def _create_directory_structure(self):
        """Создание структуры папок"""
        directories = [
            self.instances_path,
            self.versions_path,
            self.libraries_path,
            self.assets_path / "indexes",
            self.assets_path / "objects",
            self.assets_path / "virtual" / "legacy",
            self.logs_path / "crash_reports",
            self.config_path,
            self.temp_path / "downloads",
            self.temp_path / "installers",
            self.temp_path / "cache"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def create_build(self, build_config: Dict[str, Any], progress_callback: Optional[Callable] = None, log_callback: Optional[Callable] = None) -> bool:
        print('create_build called, log_callback:', log_callback)
        if log_callback:
            log_callback(f"[BuildManager] Начато создание сборки: {build_config}")
        logger.info(f"Вызван create_build с конфигом: {build_config}")
        logger.info(f"[BuildManager] Начато создание сборки: {build_config}")
        try:
            build_name = build_config.get("name", "Unnamed Build")
            minecraft_version = build_config.get("minecraft_version")
            loader = build_config.get("loader", "Vanilla")
            loader_version = build_config.get("loader_version")
            if log_callback:
                log_callback(f"Параметры: name={build_name}, version={minecraft_version}, loader={loader}, loader_version={loader_version}")
            logger.debug(f"[BuildManager] Параметры: name={build_name}, version={minecraft_version}, loader={loader}, loader_version={loader_version}")
            if log_callback:
                log_callback(f"Создаём директорию для сборки: {build_name}")
            if progress_callback:
                progress_callback(0, "Подготовка к созданию сборки...")
            # Создаем директорию для сборки
            instance_dir = self.instances_path / self._sanitize_name(build_name)
            instance_dir.mkdir(parents=True, exist_ok=True)
            if log_callback:
                log_callback(f"Создана папка сборки: {instance_dir}")
            if progress_callback:
                progress_callback(5, "Создание папки сборки...")
            # Создаем .minecraft папку внутри сборки
            minecraft_instance_dir = instance_dir / ".minecraft"
            minecraft_instance_dir.mkdir(exist_ok=True)
            if log_callback:
                log_callback(f"Создана папка .minecraft: {minecraft_instance_dir}")
            if progress_callback:
                progress_callback(8, "Создание папки .minecraft...")
            if log_callback:
                log_callback(f"Загрузка Minecraft версии: {minecraft_version}")
            if progress_callback:
                progress_callback(10, "Загрузка Minecraft...")
            # Загружаем базовую версию Minecraft
            if not self._download_minecraft_version(str(minecraft_version), progress_callback, log_callback):
                if log_callback:
                    log_callback(f"Ошибка загрузки Minecraft версии: {minecraft_version}")
                return False
            if log_callback:
                log_callback(f"Minecraft {minecraft_version} загружен.")
            if progress_callback:
                progress_callback(30, "Minecraft загружен. Подготовка к установке лоадера...")
            if log_callback:
                log_callback(f"Установка лоадера: {loader}")
            if progress_callback:
                progress_callback(40, f"Установка {loader}...")
            # Устанавливаем лоадер
            version_id = str(minecraft_version)
            if loader != "Vanilla":
                if not self._install_loader(str(minecraft_version), loader, str(loader_version) if loader_version else "", progress_callback, log_callback):
                    if log_callback:
                        log_callback(f"Ошибка установки лоадера {loader}")
                    return False
                version_id = f"{loader.lower()}-{loader_version}-{minecraft_version}"
                if log_callback:
                    log_callback(f"Лоадер {loader} установлен.")
                if progress_callback:
                    progress_callback(70, f"Лоадер {loader} установлен...")
            if log_callback:
                log_callback(f"Создание профиля запуска...")
            if progress_callback:
                progress_callback(80, "Создание профиля запуска...")
            # Создаем профиль запуска
            self._create_launch_profile(build_config, instance_dir, version_id)
            if log_callback:
                log_callback(f"Профиль запуска создан.")
            if progress_callback:
                progress_callback(85, "Профиль запуска создан...")
            if log_callback:
                log_callback(f"Создание конфигурации сборки...")
            # Создаем конфигурацию сборки
            self._create_instance_config(build_config, instance_dir)
            if log_callback:
                log_callback(f"Конфигурация сборки создана.")
            if progress_callback:
                progress_callback(95, "Конфигурация сборки создана...")
            if log_callback:
                log_callback(f"Сборка создана успешно!")
            if progress_callback:
                progress_callback(100, "Сборка создана успешно!")
            logger.success(f"[BuildManager] Сборка '{build_name}' успешно создана")
            return True
        except Exception as e:
            logger.exception(f"[BuildManager] Ошибка создания сборки: {e}")
            if log_callback:
                log_callback(f"Ошибка создания сборки: {e}")
            if progress_callback:
                progress_callback(-1, f"Ошибка: {str(e)}")
            return False
    
    def _sanitize_name(self, name: str) -> str:
        """Очистка названия для использования в пути"""
        import re
        # Заменяем недопустимые символы на подчеркивания
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', name)
        # Убираем лишние пробелы и подчеркивания
        sanitized = re.sub(r'\s+', '_', sanitized.strip())
        sanitized = re.sub(r'_+', '_', sanitized)
        return sanitized
    
    def _download_minecraft_version(self, version: str, progress_callback: Optional[Callable] = None, log_callback: Optional[Callable] = None) -> bool:
        if log_callback:
            log_callback(f"Начало загрузки Minecraft версии: {version}")
        logger.info(f"Попытка скачать Minecraft версию: {version}")
        logger.info(f"[BuildManager] Начало загрузки версии Minecraft: {version}")
        try:
            version_dir = self.versions_path / version
            if version_dir.exists():
                if log_callback:
                    log_callback(f"Версия {version} уже существует: {version_dir}")
                logger.info(f"Версия {version} уже существует")
                return True
            version_info = self._get_version_info(version)
            if not version_info:
                if log_callback:
                    log_callback(f"Не удалось получить информацию о версии: {version}")
                return False
            client_url = version_info.get("downloads", {}).get("client", {}).get("url")
            if not client_url:
                if log_callback:
                    log_callback(f"URL клиента не найден для версии {version}")
                logger.error(f"URL клиента не найден для версии {version}")
                return False
            client_path = version_dir / f"{version}.jar"
            if log_callback:
                log_callback(f"Скачивание Minecraft client: {client_url} → {client_path}")
            logger.info({
                "event": "download_mc_attempt",
                "filename": f"{version}.jar",
                "dst": str(client_path),
                "src": client_url,
                "msg": "Начинаю загрузку Minecraft client"
            })
            try:
                response = requests.get(client_url, stream=True, timeout=30)
                response.raise_for_status()
                with open(client_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                if log_callback:
                    log_callback(f"Minecraft client успешно загружен: {client_path}")
                logger.info({
                    "event": "download_mc",
                    "filename": f"{version}.jar",
                    "dst": str(client_path),
                    "src": client_url,
                    "msg": "Minecraft client успешно загружен"
                })
            except Exception as e:
                if log_callback:
                    log_callback(f"Ошибка загрузки Minecraft client: {e}")
                logger.error({
                    "event": "download_mc_error",
                    "filename": f"{version}.jar",
                    "dst": str(client_path),
                    "src": client_url,
                    "msg": f"Ошибка загрузки Minecraft client: {e}"
                })
                return False
            logger.success(f"[BuildManager] Версия Minecraft {version} успешно загружена")
            return True
        except Exception as e:
            logger.exception(f"[BuildManager] Ошибка загрузки версии Minecraft {version}")
            if log_callback:
                log_callback(f"Ошибка загрузки версии Minecraft {version}: {e}")
            return False
    
    def _get_version_info(self, version: str) -> Optional[Dict[str, Any]]:
        """Получение информации о версии"""
        try:
            # Сначала пробуем получить из манифеста
            manifest_url = "https://launchermeta.mojang.com/mc/game/version_manifest.json"
            response = requests.get(manifest_url, timeout=30)
            response.raise_for_status()
            
            manifest = response.json()
            version_info = None
            
            for v in manifest.get("versions", []):
                if v["id"] == version:
                    # Получаем детальную информацию о версии
                    version_response = requests.get(v["url"], timeout=30)
                    version_response.raise_for_status()
                    version_info = version_response.json()
                    break
            
            return version_info
            
        except Exception as e:
            logger.error(f"Ошибка получения информации о версии {version}: {e}")
            return None
    
    def _download_file(self, url: str, file_path: Path, progress_callback: Optional[Callable] = None, index: Optional[int] = None, total: Optional[int] = None) -> bool:
        logger.info(f"Начинаю скачивание файла: url={url}, file_path={file_path}, index={index}, total={total}")
        logger.info({
            "event": "download_file_attempt",
            **({"index": index} if index is not None else {}),
            **({"total": total} if total is not None else {}),
            "filename": file_path.name,
            "dst": str(file_path),
            "src": url,
            "msg": "Начинаю загрузку файла"
        })
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0 and progress_callback:
                            progress = int((downloaded / total_size) * 100)
                            progress_callback(progress, f"Загрузка {file_path.name}...")
            logger.info({
                "event": "download_file",
                **({"index": index} if index is not None else {}),
                **({"total": total} if total is not None else {}),
                "filename": file_path.name,
                "dst": str(file_path),
                "src": url,
                "msg": "Файл успешно загружен"
            })
            return True
        except Exception as e:
            logger.error({
                "event": "download_file_error",
                **({"index": index} if index is not None else {}),
                **({"total": total} if total is not None else {}),
                "filename": file_path.name,
                "dst": str(file_path),
                "src": url,
                "msg": f"Ошибка загрузки: {e}"
            })
            return False
    
    def _download_libraries(self, libraries: List[Dict], progress_callback: Optional[Callable] = None) -> bool:
        logger.info(f"Начинаю загрузку библиотек: {len(libraries)} шт.")
        try:
            total = len(libraries)
            for i, library in enumerate(libraries):
                if progress_callback:
                    progress = 25 + int((i / total) * 10)  # 25-35%
                    progress_callback(progress, f"Загрузка библиотеки {i+1}/{total}...")
                if "rules" in library:
                    continue
                artifact = library.get("downloads", {}).get("artifact")
                if not artifact:
                    continue
                url = artifact.get("url")
                path = artifact.get("path")
                if url and path:
                    lib_path = self.libraries_path / path
                    self._download_file(url, lib_path, progress_callback, index=i+1, total=total)
            logger.success("[BuildManager] Библиотеки успешно загружены")
            return True
        except Exception as e:
            logger.error("[BuildManager] Ошибка загрузки библиотек")
            return False
    
    def _download_assets(self, version_info: Dict[str, Any], progress_callback: Optional[Callable] = None) -> bool:
        logger.info(f"Начинаю загрузку assets для версии: {version_info.get('id')}")
        logger.info(f"[BuildManager] Начало загрузки ресурсов для версии: {version_info.get('id')}")
        try:
            assets = version_info.get("assetIndex", {})
            url = assets.get("url")
            id_ = assets.get("id")
            if not url or not id_:
                logger.error({
                    "event": "download_asset_error",
                    "filename": id_,
                    "src": url,
                    "msg": "Нет информации о ресурсе"
                })
                return False
            assets_dir = self.assets_path / "indexes"
            assets_dir.mkdir(parents=True, exist_ok=True)
            asset_path = assets_dir / f"{id_}.json"
            logger.info({
                "event": "download_asset_attempt",
                "filename": f"{id_}.json",
                "dst": str(asset_path),
                "src": url,
                "msg": "Начинаю загрузку assetIndex"
            })
            try:
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                with open(asset_path, 'wb') as f:
                    f.write(response.content)
                logger.info({
                    "event": "download_asset",
                    "filename": f"{id_}.json",
                    "dst": str(asset_path),
                    "src": url,
                    "msg": "assetIndex успешно загружен"
                })
            except Exception as e:
                logger.error({
                    "event": "download_asset_error",
                    "filename": f"{id_}.json",
                    "dst": str(asset_path),
                    "src": url,
                    "msg": f"Ошибка загрузки assetIndex: {e}"
                })
                return False
            # Можно добавить аналогичное логирование для отдельных файлов assets, если нужно
            logger.success(f"[BuildManager] Ресурсы для версии {version_info.get('id')} успешно загружены")
            return True
        except Exception as e:
            logger.exception(f"[BuildManager] Ошибка загрузки ресурсов для версии {version_info.get('id')}")
            return False
    
    def _install_loader(self, minecraft_version: str, loader: str, loader_version: str, progress_callback: Optional[Callable] = None, log_callback: Optional[Callable] = None) -> bool:
        logger.info(f"Начинаю установку лоадера: {loader} {loader_version} для {minecraft_version}")
        try:
            if loader == "Fabric":
                return self._install_fabric(minecraft_version, loader_version, progress_callback, log_callback)
            elif loader == "Forge":
                return self._install_forge(minecraft_version, loader_version, progress_callback, log_callback)
            elif loader == "Quilt":
                return self._install_quilt(minecraft_version, loader_version, progress_callback, log_callback)
            elif loader == "NeoForge":
                return self._install_neoforge(minecraft_version, loader_version, progress_callback, log_callback)
            elif loader in ["Paper", "Purpur"]:
                return self._install_server_jar(minecraft_version, loader, loader_version, progress_callback, log_callback)
            else:
                logger.warning(f"Лоадер {loader} не поддерживается")
                return True
                
        except Exception as e:
            logger.error(f"Ошибка установки лоадера {loader}: {e}")
            return False
    
    def _install_fabric(self, minecraft_version: str, loader_version: str, progress_callback: Optional[Callable] = None, log_callback: Optional[Callable] = None) -> bool:
        logger.info(f"Установка Fabric: {minecraft_version} {loader_version}")
        try:
            if log_callback:
                log_callback(f"Установка Fabric: {minecraft_version} {loader_version}")
            if progress_callback:
                progress_callback(45, "Установка Fabric...")
            
            # Получаем URL для Fabric
            url = f"https://meta.fabricmc.net/v2/versions/loader/{minecraft_version}/{loader_version}/profile/json"
            
            # Загружаем профиль Fabric
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            fabric_profile = response.json()
            
            # Сохраняем профиль
            profile_name = f"fabric-loader-{loader_version}-{minecraft_version}"
            profile_path = self.versions_path / profile_name / f"{profile_name}.json"
            profile_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(profile_path, 'w', encoding='utf-8') as f:
                json.dump(fabric_profile, f, indent=2)
            
            # Загружаем библиотеки Fabric
            libraries = fabric_profile.get("libraries", [])
            if not self._download_libraries(libraries, progress_callback):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка установки Fabric: {e}")
            return False
    
    def _install_forge(self, minecraft_version: str, forge_version: str, progress_callback: Optional[Callable] = None, log_callback: Optional[Callable] = None) -> bool:
        logger.info(f"Установка Forge: {minecraft_version} {forge_version}")
        try:
            if log_callback:
                log_callback(f"Установка Forge: {minecraft_version} {forge_version}")
            if progress_callback:
                progress_callback(45, "Установка Forge...")
            
            # Получаем URL для Forge
            url = f"https://files.minecraftforge.net/maven/net/minecraftforge/forge/{minecraft_version}-{forge_version}/forge-{minecraft_version}-{forge_version}-installer.jar"
            
            # Скачиваем установщик
            installer_path = self.temp_path / "installers" / f"forge-{minecraft_version}-{forge_version}-installer.jar"
            if not self._download_file(url, installer_path, progress_callback):
                return False
            
            # Запускаем установщик (упрощенная версия)
            # В реальной реализации здесь нужно запустить Java с установщиком
            logger.info(f"Forge установщик загружен: {installer_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка установки Forge: {e}")
            return False
    
    def _install_quilt(self, minecraft_version: str, loader_version: str, progress_callback: Optional[Callable] = None, log_callback: Optional[Callable] = None) -> bool:
        logger.info(f"Установка Quilt: {minecraft_version} {loader_version}")
        try:
            if log_callback:
                log_callback(f"Установка Quilt: {minecraft_version} {loader_version}")
            if progress_callback:
                progress_callback(45, "Установка Quilt...")
            
            # Получаем URL для Quilt
            url = f"https://meta.quiltmc.org/v3/versions/loader/{minecraft_version}/{loader_version}/profile/json"
            
            # Загружаем профиль Quilt
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            quilt_profile = response.json()
            
            # Сохраняем профиль
            profile_name = f"quilt-loader-{loader_version}-{minecraft_version}"
            profile_path = self.versions_path / profile_name / f"{profile_name}.json"
            profile_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(profile_path, 'w', encoding='utf-8') as f:
                json.dump(quilt_profile, f, indent=2)
            
            # Загружаем библиотеки Quilt
            libraries = quilt_profile.get("libraries", [])
            if not self._download_libraries(libraries, progress_callback):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка установки Quilt: {e}")
            return False
    
    def _install_neoforge(self, minecraft_version: str, neoforge_version: str, progress_callback: Optional[Callable] = None, log_callback: Optional[Callable] = None) -> bool:
        logger.info(f"Установка NeoForge: {minecraft_version} {neoforge_version}")
        try:
            if log_callback:
                log_callback(f"Установка NeoForge: {minecraft_version} {neoforge_version}")
            if progress_callback:
                progress_callback(45, "Установка NeoForge...")
            
            # Получаем URL для NeoForge
            url = f"https://maven.neoforged.net/releases/net/neoforged/neoforge/{neoforge_version}/neoforge-{neoforge_version}-installer.jar"
            
            # Скачиваем установщик
            installer_path = self.temp_path / "installers" / f"neoforge-{neoforge_version}-installer.jar"
            if not self._download_file(url, installer_path, progress_callback):
                return False
            
            # Запускаем установщик (упрощенная версия)
            logger.info(f"NeoForge установщик загружен: {installer_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка установки NeoForge: {e}")
            return False
    
    def _install_server_jar(self, minecraft_version: str, server_type: str, build_number: str, progress_callback: Optional[Callable] = None, log_callback: Optional[Callable] = None) -> bool:
        logger.info(f"Установка серверного JAR: {server_type} {build_number} для {minecraft_version}")
        try:
            if log_callback:
                log_callback(f"Установка серверного JAR: {server_type} {build_number} для {minecraft_version}")
            if progress_callback:
                progress_callback(45, f"Установка {server_type}...")
            if server_type == "Paper":
                url = f"https://api.papermc.io/v2/projects/paper/versions/{minecraft_version}/builds/{build_number}/downloads/paper-{minecraft_version}-{build_number}.jar"
            elif server_type == "Purpur":
                url = f"https://api.purpurmc.org/v2/purpur/{minecraft_version}/{build_number}/download"
            else:
                return False
            server_jar_path = self.versions_path / f"{server_type.lower()}-{minecraft_version}-{build_number}" / f"{server_type.lower()}-{minecraft_version}-{build_number}.jar"
            server_jar_path.parent.mkdir(parents=True, exist_ok=True)
            logger.info({
                "event": "download_server_attempt",
                "filename": server_jar_path.name,
                "dst": str(server_jar_path),
                "src": url,
                "msg": "Начинаю загрузку server jar"
            })
            try:
                response = requests.get(url, stream=True, timeout=30)
                response.raise_for_status()
                with open(server_jar_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                logger.info({
                    "event": "download_server",
                    "filename": server_jar_path.name,
                    "dst": str(server_jar_path),
                    "src": url,
                    "msg": "Server jar успешно загружен"
                })
            except Exception as e:
                logger.error({
                    "event": "download_server_error",
                    "filename": server_jar_path.name,
                    "dst": str(server_jar_path),
                    "src": url,
                    "msg": f"Ошибка загрузки server jar: {e}"
                })
                return False
            return True
        except Exception as e:
            logger.error(f"Ошибка установки {server_type}: {e}")
            return False
    
    def _create_launch_profile(self, build_config: Dict[str, Any], instance_dir: Path, version_id: str):
        logger.info(f"Создание профиля запуска: {build_config}, instance_dir={instance_dir}, version_id={version_id}")
        try:
            profile_data = {
                "name": build_config.get("name"),
                "type": "custom",
                "created": time.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "lastUsed": time.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "icon": "Grass",
                "lastVersionId": version_id,
                "gameDir": str(instance_dir / ".minecraft"),
                "javaDir": self.config_manager.get("java_path", "auto"),
                "javaArgs": f"-Xmx{self.config_manager.get('max_memory', 2048)}M -Xms{self.config_manager.get('min_memory', 512)}M"
            }
            
            # Сохраняем профиль
            profiles_file = self.config_path / "launcher_profiles.json"
            
            if profiles_file.exists():
                with open(profiles_file, 'r', encoding='utf-8') as f:
                    profiles = json.load(f)
            else:
                profiles = {"profiles": {}}
            
            profile_name = self._sanitize_name(build_config.get("name", "Unnamed"))
            profiles["profiles"][profile_name] = profile_data
            
            with open(profiles_file, 'w', encoding='utf-8') as f:
                json.dump(profiles, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Профиль запуска создан: {profile_name}")
            
        except Exception as e:
            logger.error(f"Ошибка создания профиля запуска: {e}")
    
    def _create_instance_config(self, build_config: Dict[str, Any], instance_dir: Path):
        logger.info(f"Создание конфигурации сборки: {build_config}, instance_dir={instance_dir}")
        try:
            config_data = {
                "name": build_config.get("name"),
                "minecraft_version": build_config.get("minecraft_version"),
                "loader": build_config.get("loader"),
                "loader_version": build_config.get("loader_version"),
                "created": time.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "last_used": time.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "notes": build_config.get("notes", ""),
                "icon": "Grass"
            }
            
            config_file = instance_dir / "instance.cfg"
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Конфигурация сборки создана: {config_file}")
            
        except Exception as e:
            logger.error(f"Ошибка создания конфигурации сборки: {e}")
    
    def get_builds(self) -> List[Dict[str, Any]]:
        """Получение списка созданных сборок"""
        try:
            builds = []
            
            if self.instances_path.exists():
                for instance_dir in self.instances_path.iterdir():
                    if instance_dir.is_dir():
                        config_file = instance_dir / "instance.cfg"
                        if config_file.exists():
                            with open(config_file, 'r', encoding='utf-8') as f:
                                config = json.load(f)
                        else:
                            config = {"name": instance_dir.name}
                        
                        build_info = {
                            "name": config.get("name", instance_dir.name),
                            "path": str(instance_dir),
                            "created": config.get("created", instance_dir.stat().st_ctime),
                            "last_used": config.get("last_used", instance_dir.stat().st_mtime),
                            "minecraft_version": config.get("minecraft_version", "Unknown"),
                            "loader": config.get("loader", "Unknown"),
                            "notes": config.get("notes", "")
                        }
                        builds.append(build_info)
            
            return builds
            
        except Exception as e:
            logger.error(f"Ошибка получения списка сборок: {e}")
            return []
    
    def delete_build(self, build_name: str) -> bool:
        """Удаление сборки"""
        try:
            instance_dir = self.instances_path / self._sanitize_name(build_name)
            
            if instance_dir.exists():
                shutil.rmtree(instance_dir)
                logger.info(f"Сборка {build_name} удалена")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Ошибка удаления сборки {build_name}: {e}")
            return False
    
    def get_build_logs(self, build_name: str) -> List[Dict[str, Any]]:
        """Получение логов сборки"""
        try:
            instance_dir = self.instances_path / self._sanitize_name(build_name)
            logs_dir = instance_dir / ".minecraft" / "logs"
            
            logs = []
            if logs_dir.exists():
                for log_file in logs_dir.glob("*.log"):
                    log_info = {
                        "name": log_file.name,
                        "path": str(log_file),
                        "size": log_file.stat().st_size,
                        "modified": log_file.stat().st_mtime
                    }
                    logs.append(log_info)
            
            return logs
            
        except Exception as e:
            logger.error(f"Ошибка получения логов сборки {build_name}: {e}")
            return [] 