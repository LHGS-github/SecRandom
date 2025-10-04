from qfluentwidgets import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtNetwork import *
from PyQt5.QtSvg import *

import os
import sys
import importlib.util
import json
import random
import re
from loguru import logger
from pathlib import Path

from app.common.config import load_custom_font, is_dark_theme, get_theme_icon
from app.common.path_utils import path_manager
from app.common.path_utils import open_file, ensure_dir

dark_mode = is_dark_theme(qconfig)

class LevitationWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.app_dir = path_manager._app_root
        self._load_settings()  # 加载配置
        self._init_ui_components()  # 初始化UI组件
        self._setup_event_handlers()  # 设置事件处理器
        self._init_drag_system()  # 初始化拖动系统
        self._init_keep_top_timer()  # 初始化保持置顶定时器
        self.max_count = 0 # 初始化最大抽取人数
        self.is_drawing = False # 标记是否正在抽取
        self.update_total_count() # 更新最大抽取人数
        self.load_position()

    def _load_settings(self):
        # 小鸟游星野：加载基础设置和透明度配置
        settings_path = path_manager.get_settings_path("custom_settings.json")
        try:
            ensure_dir(settings_path.parent)
            with open_file(settings_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                self.transparency_mode = settings['floating_window']['pumping_floating_transparency_mode']
                self.floating_visible = settings['floating_window']['pumping_floating_visible']
                self.button_arrangement_mode = settings['floating_window']['button_arrangement_mode']
                self.floating_icon_mode = settings['floating_window']['floating_icon_mode']
                self.flash_window_side_switch = settings['floating_window']['flash_window_side_switch']
                self.custom_retract_time = settings['floating_window']['custom_retract_time']
                self.custom_display_mode = settings['floating_window']['custom_display_mode']
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.transparency_mode = 0.8
            self.floating_visible = 3
            self.button_arrangement_mode = 0
            self.floating_icon_mode = 0
            self.flash_window_side_switch = False
            self.custom_retract_time = 5
            self.custom_display_mode = 1
            logger.error(f"加载基础设置失败: {e}")

        self.transparency_mode = max(0, min(self.transparency_mode / 100, 1))
        self.button_arrangement_mode = max(0, min(self.button_arrangement_mode, 2))
        self.floating_icon_mode = max(0, min(self.floating_icon_mode, 2))

    def _is_non_class_time(self):
        """检测当前时间是否在非上课时间段
        当'课间禁用'开关启用时，用于判断是否需要安全验证"""
        try:
            # 读取程序功能设置
            settings_path = path_manager.get_settings_path('custom_settings.json')
            if not path_manager.file_exists(settings_path):
                return False
                
            with open_file(settings_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                
            # 检查课间禁用开关是否启用
            program_functionality = settings.get("program_functionality", {})
            instant_draw_disable = program_functionality.get("instant_draw_disable", False)
            
            if not instant_draw_disable:
                return False
                
            # 读取上课时间段设置
            time_settings_path = path_manager.get_settings_path('time_settings.json')
            if not path_manager.file_exists(time_settings_path):
                return False
                
            with open_file(time_settings_path, 'r', encoding='utf-8') as f:
                time_settings = json.load(f)
                
            # 获取非上课时间段
            non_class_times = time_settings.get('non_class_times', {})
            if not non_class_times:
                return False
                
            # 获取当前时间
            current_time = QDateTime.currentDateTime()
            current_hour = current_time.time().hour()
            current_minute = current_time.time().minute()
            current_second = current_time.time().second()
            
            # 将当前时间转换为总秒数
            current_total_seconds = current_hour * 3600 + current_minute * 60 + current_second
            
            # 检查当前时间是否在任何非上课时间段内
            for time_range in non_class_times.values():
                try:
                    start_end = time_range.split('-')
                    if len(start_end) != 2:
                        continue
                        
                    start_time_str, end_time_str = start_end
                    
                    # 解析开始时间
                    start_parts = list(map(int, start_time_str.split(':')))
                    start_total_seconds = start_parts[0] * 3600 + start_parts[1] * 60 + (start_parts[2] if len(start_parts) > 2 else 0)
                    
                    # 解析结束时间
                    end_parts = list(map(int, end_time_str.split(':')))
                    end_total_seconds = end_parts[0] * 3600 + end_parts[1] * 60 + (end_parts[2] if len(end_parts) > 2 else 0)
                    
                    # 检查当前时间是否在该非上课时间段内
                    if start_total_seconds <= current_total_seconds < end_total_seconds:
                        return True
                        
                except Exception as e:
                    logger.error(f"解析非上课时间段失败: {e}")
                    continue
                    
            return False
            
        except Exception as e:
            logger.error(f"检测非上课时间失败: {e}")
            return False

    def _init_ui_components(self):
        # 白露：初始化所有UI组件 - 根据floating_visible值进行功能组合显示
        self._setup_main_layout()
        
        # 根据floating_visible值（0-14）初始化对应的组件组合
        # 映射关系：
        # 0: 显示 拖动
        # 1: 显示 主界面
        # 2: 显示 闪抽
        # 3: 显示 拖动+主界面
        # 4: 显示 拖动+闪抽
        # 5: 显示 主界面+闪抽
        # 6: 显示 拖动+主界面+闪抽
        # 7: 显示 即抽

        if self.floating_visible == 0:  # 显示 拖动
            self._init_menu_label()
        elif self.floating_visible == 1:  # 显示 主界面
            self._init_people_label()
        elif self.floating_visible == 2:  # 显示 闪抽
            self._init_flash_button()
        elif self.floating_visible == 3:  # 显示 拖动+主界面
            self._init_menu_label()
            self._init_people_label()
        elif self.floating_visible == 4:  # 显示 拖动+闪抽
            self._init_menu_label()
            self._init_flash_button()
        elif self.floating_visible == 5:  # 显示 主界面+闪抽
            self._init_people_label()
            self._init_flash_button()
        elif self.floating_visible == 6:  # 显示 拖动+主界面+闪抽
            # 3个按钮：拖动、主界面在上面，闪抽在下面
            self._init_menu_label()
            self._init_people_label()
            self._init_flash_button()
        elif self.floating_visible == 7:  # 测试 即抽(带调节人数功能)
            self._init_instant_draw_button()
        
        self._apply_window_styles()

    def _setup_main_layout(self):
        # 小鸟游星野：设置主布局容器 - 支持多种排列方式
        self.container_button = QWidget()
        # 根据透明度模式设置按钮透明度
        opacity_value = self.transparency_mode
        # 使用QGraphicsOpacityEffect设置按钮透明度
        opacity_effect = QGraphicsOpacityEffect()
        opacity_effect.setOpacity(opacity_value)
        self.container_button.setGraphicsEffect(opacity_effect)
        
        # 根据显示的按钮数量和排列方式决定布局
        button_count = self._get_button_count()
        
        if self.button_arrangement_mode == 0:  # 矩形排列
            if button_count >= 3:
                # 3个或4个按钮时使用垂直布局，文字按钮放在下面
                main_layout = QVBoxLayout(self.container_button)
                main_layout.setContentsMargins(0, 0, 0, 0)
                main_layout.setSpacing(0)
                
                # 创建上下两个容器
                self.top_container = QWidget()
                self.bottom_container = QWidget()
                
                # 上层使用水平布局
                top_layout = QHBoxLayout(self.top_container)
                top_layout.setContentsMargins(0, 0, 0, 0)
                top_layout.setSpacing(0)
                
                # 下层使用水平布局，如果是3个按钮则让按钮填满容器宽度
                bottom_layout = QHBoxLayout(self.bottom_container)
                bottom_layout.setContentsMargins(0, 0, 0, 0)
                bottom_layout.setSpacing(0)
                
                # 添加到主布局
                main_layout.addWidget(self.top_container)
                main_layout.addWidget(self.bottom_container)
                
                # 设置下层高度
                if self.floating_icon_mode != 0:
                    self.bottom_container.setFixedHeight(50)
                else:
                    self.bottom_container.setFixedHeight(70)

                if self.floating_visible == 7:
                    self.bottom_container.setFixedHeight(165)
                
            else:
                # 1个或2个按钮时使用水平布局
                button_layout = QHBoxLayout(self.container_button)
                button_layout.setContentsMargins(0, 0, 0, 0)
                button_layout.setSpacing(0)
                
                # 创建单个容器
                self.top_container = self.container_button
                self.bottom_container = None
                
        elif self.button_arrangement_mode == 1:  # 竖着排列
            # 所有按钮都垂直排列
            main_layout = QVBoxLayout(self.container_button)
            main_layout.setContentsMargins(0, 0, 0, 0)
            main_layout.setSpacing(0)
            
            # 创建专用的垂直容器，避免布局冲突
            self.top_container = QWidget()
            self.bottom_container = None
            
            # 为垂直容器设置垂直布局
            vertical_layout = QVBoxLayout(self.top_container)
            vertical_layout.setContentsMargins(0, 0, 0, 0)
            vertical_layout.setSpacing(0)
            
            # 将垂直容器添加到主布局
            main_layout.addWidget(self.top_container)
            
        elif self.button_arrangement_mode == 2:  # 横着排列
            # 所有按钮都水平排列
            main_layout = QHBoxLayout(self.container_button)
            main_layout.setContentsMargins(0, 0, 0, 0)
            main_layout.setSpacing(0)
            
            # 创建专用的水平容器，与竖着排列区分
            self.horizontal_container = QWidget()
            horizontal_layout = QHBoxLayout(self.horizontal_container)
            horizontal_layout.setContentsMargins(0, 0, 0, 0)
            horizontal_layout.setSpacing(0)
            
            # 将水平容器添加到主布局
            main_layout.addWidget(self.horizontal_container)
            
            # 设置其他容器为None，确保独立性
            self.top_container = None
            self.bottom_container = None

        # 设置窗口主布局
        window_layout = QHBoxLayout(self)
        window_layout.addWidget(self.container_button)
        self.setLayout(window_layout)
        
    def _get_button_count(self):
        # 小鸟游星野：根据floating_visible值计算要显示的按钮数量
        # 映射关系：
        # 0: 显示 拖动 (1个)
        # 1: 显示 主界面 (1个)
        # 2: 显示 闪抽 (1个)
        # 3: 显示 拖动+主界面 (2个)
        # 4: 显示 拖动+闪抽 (2个)
        # 5: 显示 主界面+闪抽 (2个)
        # 6: 显示 拖动+主界面+闪抽 (3个)
        # 7: 显示 即抽

        if self.floating_visible in [0, 1, 2]:
            return 1
        elif self.floating_visible in [3, 4, 5]:
            return 2
        elif self.floating_visible == 6:
            return 3
        elif self.floating_visible == 7:
            return 4
        else:
            return 1  # 默认值

    def _init_menu_label(self):
        # 根据floating_icon_mode值决定显示模式
        if self.floating_icon_mode == 1:  # 仅图标模式
            self.menu_label = BodyLabel(self.container_button)
            try:
                # 根据主题设置不同的颜色
                if dark_mode:
                    # 深色模式
                    icon_path = path_manager.get_resource_path("icon", f"SecRandom_menu_light.png")
                else:
                    # 浅色模式
                    icon_path = path_manager.get_resource_path("icon", f"SecRandom_menu_black.png")

                pixmap = QPixmap(str(icon_path))
                self.menu_label.setPixmap(pixmap.scaled(30, 30, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            except FileNotFoundError as e:
                pixmap = QPixmap(str(icon_path))
                self.menu_label.setPixmap(pixmap.scaled(30, 30, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                logger.error(f"加载菜单图标失败: {e}")
         
            self.menu_label.setStyleSheet('opacity: 0; background: transparent;')
            self.menu_label.setFixedSize(50, 50)
            self.menu_label.setAlignment(Qt.AlignCenter)
            # 确保图标在标签中居中显示
            self.menu_label.setProperty('class', 'centered-icon')
            # 根据透明度模式设置按钮透明度
            opacity_value = self.transparency_mode
            # 使用QGraphicsOpacityEffect设置按钮透明度
            opacity_effect = QGraphicsOpacityEffect()
            opacity_effect.setOpacity(opacity_value)
            self.menu_label.setGraphicsEffect(opacity_effect)
            
        elif self.floating_icon_mode == 2:  # 仅文字模式
            self.menu_label = PushButton("拖动")
            # 设置按钮固定大小和样式
            self.menu_label.setFixedSize(50, 50)
            # 根据透明度模式设置按钮透明度
            opacity_value = self.transparency_mode
            if dark_mode:
                self.menu_label.setStyleSheet('border: none; background: transparent; font-weight: bold; text-align: center; color: #ffffff;')
            else:
                self.menu_label.setStyleSheet('border: none; background: transparent; font-weight: bold; text-align: center; color: #000000;')
            # 使用QGraphicsOpacityEffect设置按钮透明度
            opacity_effect = QGraphicsOpacityEffect()
            opacity_effect.setOpacity(opacity_value)
            self.menu_label.setGraphicsEffect(opacity_effect)
            self.menu_label.setFont(QFont(load_custom_font(), 12))
            
        else:  # 图标+文字模式（默认）
            # 创建一个垂直布局的容器，图标在上，文字在下
            self.menu_label = PushButton()
            menu_layout = QVBoxLayout(self.menu_label)
            menu_layout.setContentsMargins(0, 5, 0, 5)
            menu_layout.setSpacing(2)
            
            # 添加图标
            icon_label = BodyLabel()
            icon_label.setAlignment(Qt.AlignCenter)  # 确保图标在标签中居中显示
            try:
                # 根据主题设置不同的颜色
                if dark_mode:
                    # 深色模式
                    icon_path = path_manager.get_resource_path("icon", f"SecRandom_menu_light.png")
                else:
                    # 浅色模式
                    icon_path = path_manager.get_resource_path("icon", f"SecRandom_menu_black.png")

                pixmap = QPixmap(str(icon_path))
                icon_label.setPixmap(pixmap.scaled(30, 30, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            except FileNotFoundError as e:
                pixmap = QPixmap(str(icon_path))
                icon_label.setPixmap(pixmap.scaled(30, 30, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                logger.error(f"加载菜单图标失败: {e}")
            
            # 添加文字
            text_label = BodyLabel("拖动")
            text_label.setFont(QFont(load_custom_font(), 10))
            text_label.setAlignment(Qt.AlignCenter)
            
            # 将图标和文字添加到布局（图标在上，文字在下）
            menu_layout.addWidget(icon_label)
            menu_layout.addWidget(text_label)
            menu_layout.setAlignment(Qt.AlignCenter)
            
            # 设置按钮样式
            if dark_mode:
                self.menu_label.setStyleSheet('opacity: 0; border: none; background: transparent; font-weight: bold; color: #ffffff;')
            else:
                self.menu_label.setStyleSheet('opacity: 0; border: none; background: transparent; font-weight: bold; color: #000000;')
            
            self.menu_label.setFixedSize(50, 70)  # 调整大小以适应垂直布局
            # 根据透明度模式设置按钮透明度
            opacity_value = self.transparency_mode
            self.menu_label.setProperty('class', 'centered-icon')
            # 使用QGraphicsOpacityEffect设置按钮透明度
            opacity_effect = QGraphicsOpacityEffect()
            opacity_effect.setOpacity(opacity_value)
            self.menu_label.setGraphicsEffect(opacity_effect)
        
        # 根据排列方式决定按钮大小和添加位置
        button_count = self._get_button_count()
        
        if self.button_arrangement_mode == 0:  # 矩形排列
            if button_count >= 3:
                # 3个或4个按钮时，拖动按钮放在上面
                if hasattr(self, 'top_container') and self.top_container:
                    self.top_container.layout().addWidget(self.menu_label)
                else:
                    self.container_button.layout().addWidget(self.menu_label)
            else:
                # 1个或2个按钮时使用水平布局
                if hasattr(self, 'top_container') and self.top_container:
                    self.top_container.layout().addWidget(self.menu_label)
                else:
                    self.container_button.layout().addWidget(self.menu_label)
                    
        elif self.button_arrangement_mode == 1:  # 竖着排列
            # 所有按钮都垂直排列
            if hasattr(self, 'top_container') and self.top_container:
                self.top_container.layout().addWidget(self.menu_label)
            else:
                self.container_button.layout().addWidget(self.menu_label)
                
        elif self.button_arrangement_mode == 2:  # 横着排列
            # 所有按钮都水平排列
            if hasattr(self, 'horizontal_container') and self.horizontal_container:
                self.horizontal_container.layout().addWidget(self.menu_label)
            elif hasattr(self, 'top_container') and self.top_container:
                self.top_container.layout().addWidget(self.menu_label)
            else:
                self.container_button.layout().addWidget(self.menu_label)

    def _init_people_label(self):
        # 根据floating_icon_mode值决定显示模式
        if self.floating_icon_mode == 1:  # 仅图标模式
            self.people_label = BodyLabel(self.container_button)
            try:
                # 根据主题设置不同的颜色
                if dark_mode:
                    # 深色模式
                    icon_path = path_manager.get_resource_path("icon", f"SecRandom_floating_light.png")
                else:
                    # 浅色模式
                    icon_path = path_manager.get_resource_path("icon", f"SecRandom_floating_black.png")

                pixmap = QPixmap(str(icon_path))
                self.people_label.setPixmap(pixmap.scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            except FileNotFoundError as e:
                pixmap = QPixmap(str(icon_path))
                self.people_label.setPixmap(pixmap.scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                logger.error(f"加载人物图标失败: {e}")
         
            self.people_label.setStyleSheet('opacity: 0; background: transparent;')
            self.people_label.setFixedSize(50, 50)
            self.people_label.setAlignment(Qt.AlignCenter)
            # 确保图标在标签中居中显示
            self.people_label.setProperty('class', 'centered-icon')
            # 根据透明度模式设置按钮透明度
            opacity_value = self.transparency_mode
            # 使用QGraphicsOpacityEffect设置按钮透明度
            opacity_effect = QGraphicsOpacityEffect()
            opacity_effect.setOpacity(opacity_value)
            self.people_label.setGraphicsEffect(opacity_effect)
            
        elif self.floating_icon_mode == 2:  # 仅文字模式
            self.people_label = PushButton("点名")
            # 设置按钮固定大小和样式
            self.people_label.setFixedSize(50, 50)
            # 根据透明度模式设置按钮透明度
            opacity_value = self.transparency_mode
            if dark_mode:
                self.people_label.setStyleSheet('border: none; background: transparent; font-weight: bold; text-align: center; color: #ffffff;')
            else:
                self.people_label.setStyleSheet('border: none; background: transparent; font-weight: bold; text-align: center; color: #000000;')
            # 使用QGraphicsOpacityEffect设置按钮透明度
            opacity_effect = QGraphicsOpacityEffect()
            opacity_effect.setOpacity(opacity_value)
            self.people_label.setGraphicsEffect(opacity_effect)
            self.people_label.setFont(QFont(load_custom_font(), 12))

            
        else:  # 图标+文字模式（默认）
            # 创建一个垂直布局的容器，图标在上，文字在下
            self.people_label = PushButton()
            people_layout = QVBoxLayout(self.people_label)
            people_layout.setContentsMargins(0, 5, 0, 5)
            people_layout.setSpacing(0)
            
            # 添加图标
            icon_label = BodyLabel()
            icon_label.setAlignment(Qt.AlignCenter)  # 确保图标在标签中居中显示
            try:
                # 根据主题设置不同的颜色
                if dark_mode:
                    # 深色模式
                    icon_path = path_manager.get_resource_path("icon", f"SecRandom_floating_light.png")
                else:
                    # 浅色模式
                    icon_path = path_manager.get_resource_path("icon", f"SecRandom_floating_black.png")

                pixmap = QPixmap(str(icon_path))
                icon_label.setPixmap(pixmap.scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            except FileNotFoundError as e:
                pixmap = QPixmap(str(icon_path))
                icon_label.setPixmap(pixmap.scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                logger.error(f"加载人物图标失败: {e}")
            
            # 添加文字
            text_label = BodyLabel("点名")
            text_label.setFont(QFont(load_custom_font(), 10))
            text_label.setAlignment(Qt.AlignCenter)
            
            # 将图标和文字添加到布局（图标在上，文字在下）
            people_layout.addWidget(icon_label)
            people_layout.addWidget(text_label)
            people_layout.addSpacing(5)
            people_layout.setAlignment(Qt.AlignCenter)
            
            # 设置按钮样式
            if dark_mode:
                self.people_label.setStyleSheet('opacity: 0; border: none; background: transparent; font-weight: bold; color: #ffffff;')
            else:
                self.people_label.setStyleSheet('opacity: 0; border: none; background: transparent; font-weight: bold; color: #000000;')
            
            self.people_label.setFixedSize(50, 70)  # 调整大小以适应垂直布局
            # 根据透明度模式设置按钮透明度
            opacity_value = self.transparency_mode
            self.people_label.setProperty('class', 'centered-icon')
            # 使用QGraphicsOpacityEffect设置按钮透明度
            opacity_effect = QGraphicsOpacityEffect()
            opacity_effect.setOpacity(opacity_value)
            self.people_label.setGraphicsEffect(opacity_effect)
        
        # 根据排列方式决定按钮大小和添加位置
        button_count = self._get_button_count()
        
        if self.button_arrangement_mode == 0:  # 矩形排列
            if button_count >= 3:
                # 3个或4个按钮时，人物按钮放在上面
                if hasattr(self, 'top_container') and self.top_container:
                    self.top_container.layout().addWidget(self.people_label)
                else:
                    self.container_button.layout().addWidget(self.people_label)
            else:
                # 1个或2个按钮时使用水平布局
                if hasattr(self, 'top_container') and self.top_container:
                    self.top_container.layout().addWidget(self.people_label)
                else:
                    self.container_button.layout().addWidget(self.people_label)
                    
        elif self.button_arrangement_mode == 1:  # 竖着排列
            # 所有按钮都垂直排列
            if hasattr(self, 'top_container') and self.top_container:
                self.top_container.layout().addWidget(self.people_label)
            else:
                self.container_button.layout().addWidget(self.people_label)
                
        elif self.button_arrangement_mode == 2:  # 横着排列
            # 所有按钮都水平排列
            if hasattr(self, 'horizontal_container') and self.horizontal_container:
                self.horizontal_container.layout().addWidget(self.people_label)
            elif hasattr(self, 'top_container') and self.top_container:
                self.top_container.layout().addWidget(self.people_label)
            else:
                self.container_button.layout().addWidget(self.people_label)

    def _init_flash_button(self):
        # 根据floating_icon_mode值决定显示模式
        if self.floating_icon_mode == 1:  # 仅图标模式
            self.flash_button = PushButton()
            try:
                # 根据主题设置不同的颜色
                is_dark = is_dark_theme(qconfig) # True: 深色, False: 浅色
                
                prefix = "light" if is_dark else "dark"
                suffix = "_light" if is_dark else "_dark"
                
                icon_path = path_manager.get_resource_path('assets', f'{prefix}/ic_fluent_flash_20_filled{suffix}.svg')

                # 使用QSvgRenderer处理SVG，保持矢量图形的清晰度和固定纵横比
                svg_renderer = QSvgRenderer(str(icon_path))
                # 创建一个适当大小的pixmap来渲染SVG
                svg_pixmap = QPixmap(25, 25)
                svg_pixmap.fill(Qt.transparent)
                painter = QPainter(svg_pixmap)
                # 获取SVG的原始尺寸
                svg_size = svg_renderer.defaultSize()
                # 计算保持纵横比的缩放比例
                if svg_size.width() > 0 and svg_size.height() > 0:
                    scale = min(25.0 / svg_size.width(), 25.0 / svg_size.height())
                    # 计算渲染区域，保持纵横比
                    render_width = int(svg_size.width() * scale)
                    render_height = int(svg_size.height() * scale)
                    # 居中渲染
                    render_x = (25 - render_width) // 2
                    render_y = (25 - render_height) // 2
                    # 在指定区域内渲染SVG，保持纵横比
                    svg_renderer.render(painter, QRectF(render_x, render_y, render_width, render_height))
                else:
                    # 如果无法获取原始尺寸，则使用默认渲染方式
                    svg_renderer.render(painter)
                painter.end()
                self.flash_button.setIcon(QIcon(svg_pixmap))
                self.flash_button.setIconSize(QSize(25, 25))
            except FileNotFoundError as e:
                # 创建一个空的透明pixmap
                empty_pixmap = QPixmap(25, 25)
                empty_pixmap.fill(Qt.transparent)
                self.flash_button.setIcon(QIcon(empty_pixmap))
                self.flash_button.setIconSize(QSize(25, 25))
                logger.error(f"加载闪抽图标失败: {e}")
            
            # 设置按钮固定大小和样式
            self.flash_button.setFixedSize(50, 50)
            # 根据透明度模式设置按钮透明度
            opacity_value = self.transparency_mode
            self.flash_button.setStyleSheet('border: none; background: transparent; text-align: center;')
            self.flash_button.setProperty('class', 'centered-icon')
            # 使用QGraphicsOpacityEffect设置按钮透明度
            opacity_effect = QGraphicsOpacityEffect()
            opacity_effect.setOpacity(opacity_value)
            self.flash_button.setGraphicsEffect(opacity_effect)
            
        elif self.floating_icon_mode == 2:  # 仅文字模式
            self.flash_button = PushButton("闪抽")
            # 设置按钮固定大小和样式
            self.flash_button.setFixedSize(50, 50)
            # 根据透明度模式设置按钮透明度
            opacity_value = self.transparency_mode
            if dark_mode:
                self.flash_button.setStyleSheet('border: none; background: transparent; font-weight: bold; text-align: center; color: #ffffff;')
            else:
                self.flash_button.setStyleSheet('border: none; background: transparent; font-weight: bold; text-align: center; color: #000000;')
            # 使用QGraphicsOpacityEffect设置按钮透明度
            opacity_effect = QGraphicsOpacityEffect()
            opacity_effect.setOpacity(opacity_value)
            self.flash_button.setGraphicsEffect(opacity_effect)
            self.flash_button.setFont(QFont(load_custom_font(), 12))
            
        else:  # 图标+文字模式（默认）
            # 创建一个垂直布局的容器，图标在上，文字在下
            self.flash_button = PushButton()
            flash_layout = QVBoxLayout(self.flash_button)
            flash_layout.setContentsMargins(0, 5, 0, 5)
            flash_layout.setSpacing(7)
            
            # 添加图标
            icon_label = BodyLabel()
            icon_label.setAlignment(Qt.AlignCenter)  # 确保图标在标签中居中显示
            icon_label.setProperty('class', 'centered-icon')  # 添加居中类属性确保图标正确居中
            try:
                # 根据主题设置不同的颜色
                is_dark = is_dark_theme(qconfig) # True: 深色, False: 浅色
                
                prefix = "light" if is_dark else "dark"
                suffix = "_light" if is_dark else "_dark"
                
                icon_path = path_manager.get_resource_path('assets', f'{prefix}/ic_fluent_flash_20_filled{suffix}.svg')

                # 使用QSvgRenderer处理SVG，保持矢量图形的清晰度和固定纵横比
                svg_renderer = QSvgRenderer(str(icon_path))
                # 创建一个适当大小的pixmap来渲染SVG
                svg_pixmap = QPixmap(25, 25)
                svg_pixmap.fill(Qt.transparent)
                painter = QPainter(svg_pixmap)
                # 获取SVG的原始尺寸
                svg_size = svg_renderer.defaultSize()
                # 计算保持纵横比的缩放比例
                if svg_size.width() > 0 and svg_size.height() > 0:
                    scale = min(25.0 / svg_size.width(), 25.0 / svg_size.height())
                    # 计算渲染区域，保持纵横比
                    render_width = int(svg_size.width() * scale)
                    render_height = int(svg_size.height() * scale)
                    # 居中渲染，向左偏移3个像素
                    render_x = (25 - render_width) // 2
                    render_y = (25 - render_height) // 2
                    # 在指定区域内渲染SVG，保持纵横比
                    svg_renderer.render(painter, QRectF(render_x, render_y, render_width, render_height))
                else:
                    # 如果无法获取原始尺寸，则使用默认渲染方式
                    svg_renderer.render(painter)
                painter.end()
                icon_label.setPixmap(svg_pixmap)
            except FileNotFoundError as e:
                # 创建一个空的透明pixmap
                empty_pixmap = QPixmap(25, 25)
                empty_pixmap.fill(Qt.transparent)
                icon_label.setPixmap(empty_pixmap)
                logger.error(f"加载闪抽图标失败: {e}")
            
            # 添加文字
            text_label = BodyLabel("闪抽")
            text_label.setFont(QFont(load_custom_font(), 10))
            text_label.setAlignment(Qt.AlignCenter)
            
            # 将图标和文字添加到布局（图标在上，文字在下）
            flash_layout.addWidget(icon_label)
            flash_layout.addWidget(text_label)
            flash_layout.setAlignment(Qt.AlignCenter)
            
            # 设置按钮固定大小和样式
            self.flash_button.setFixedSize(50, 70)  # 调整大小以适应垂直布局
            # 根据透明度模式设置按钮透明度
            opacity_value = self.transparency_mode
            if dark_mode:
                self.flash_button.setStyleSheet('border: none; background: transparent; font-weight: bold; text-align: center; color: #ffffff;')
            else:
                self.flash_button.setStyleSheet('border: none; background: transparent; font-weight: bold; text-align: center; color: #000000;')
            # 使用QGraphicsOpacityEffect设置按钮透明度
            opacity_effect = QGraphicsOpacityEffect()
            opacity_effect.setOpacity(opacity_value)
            self.flash_button.setGraphicsEffect(opacity_effect)
        
        # 根据排列方式决定按钮添加位置（保留根据显示模式设置的大小）
        button_count = self._get_button_count()
        
        if self.button_arrangement_mode == 0:  # 矩形排列
            if button_count >= 3:
                # 3个或4个按钮时，闪抽按钮放在下面
                if hasattr(self, 'bottom_container') and self.bottom_container:
                    self.bottom_container.layout().addWidget(self.flash_button)
                else:
                    self.container_button.layout().addWidget(self.flash_button)
            else:
                # 1个或2个按钮时使用水平布局
                if hasattr(self, 'top_container') and self.top_container:
                    self.top_container.layout().addWidget(self.flash_button)
                else:
                    self.container_button.layout().addWidget(self.flash_button)
                    
        elif self.button_arrangement_mode == 1:  # 竖着排列
            # 所有按钮都垂直排列
            if hasattr(self, 'top_container') and self.top_container:
                self.top_container.layout().addWidget(self.flash_button)
            else:
                self.container_button.layout().addWidget(self.flash_button)
                
        elif self.button_arrangement_mode == 2:  # 横着排列
            # 所有按钮都水平排列
            if hasattr(self, 'horizontal_container') and self.horizontal_container:
                self.horizontal_container.layout().addWidget(self.flash_button)
            elif hasattr(self, 'top_container') and self.top_container:
                self.top_container.layout().addWidget(self.flash_button)
            else:
                self.container_button.layout().addWidget(self.flash_button)

        self.flash_button.setFont(QFont(load_custom_font(), 12))
        self.flash_button.clicked.connect(self._show_direct_extraction_window)

    def _init_instant_draw_button(self):
        # 小鸟游星野：初始化即抽按钮和人数调节功能
        # 创建主容器 - 优化的两层布局
        self.instant_draw_container = QWidget()
        main_layout = QVBoxLayout(self.instant_draw_container)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(6)
        
        # 第一层：标题和人数调节布局
        first_layer_container = QWidget()
        first_layer_layout = QHBoxLayout(first_layer_container)
        first_layer_layout.setContentsMargins(0, 0, 0, 0)
        first_layer_layout.setSpacing(4)
        
        # 添加"即抽"标题
        self.instant_draw_title = BodyLabel(" 即抽")
        self.instant_draw_title.setAlignment(Qt.AlignCenter)
        self.instant_draw_title.setFixedSize(34, 30)
        if dark_mode:
            self.instant_draw_title.setStyleSheet('color: #ffffff; font-weight: bold;')
        else:
            self.instant_draw_title.setStyleSheet('color: #333333; font-weight: bold;')
        
        # 创建融合式人数调节控件
        self.count_widget = QWidget()
        self.count_widget.setFixedSize(90, 30)  # 整体宽度减小
        count_widget_layout = QHBoxLayout(self.count_widget)
        count_widget_layout.setContentsMargins(0, 0, 0, 0)
        count_widget_layout.setSpacing(0)
        
        # 左侧：减人数按钮
        self.decrease_button = PushButton("-")
        self.decrease_button.setFixedSize(28, 30)  # 宽度减小
        if dark_mode:
            self.decrease_button.setStyleSheet('border-top-left-radius: 4px; border-bottom-left-radius: 4px; border-top-right-radius: 0; border-bottom-right-radius: 0; background: #2a2a2a; color: #ffffff;')
        else:
            self.decrease_button.setStyleSheet('border-top-left-radius: 4px; border-bottom-left-radius: 4px; border-top-right-radius: 0; border-bottom-right-radius: 0; background: #f5f5f5; color: #000000;')
        
        # 中间：当前抽取人数显示
        self.count_label = BodyLabel("1")
        self.count_label.setAlignment(Qt.AlignCenter)
        self.count_label.setFixedSize(34, 30)  # 宽度减小
        if dark_mode:
            self.count_label.setStyleSheet('border-left: none; border-right: none; background: #2a2a2a; color: #ffffff;')
        else:
            self.count_label.setStyleSheet('border-left: none; border-right: none; background: #f5f5f5; color: #000000;')
        
        # 右侧：加人数按钮
        self.increase_button = PushButton("+")
        self.increase_button.setFixedSize(28, 30)  # 宽度减小
        if dark_mode:
            self.increase_button.setStyleSheet('border-top-left-radius: 0; border-bottom-left-radius: 0; border-top-right-radius: 4px; border-bottom-right-radius: 4px; background: #2a2a2a; color: #ffffff;')
        else:
            self.increase_button.setStyleSheet('border-top-left-radius: 0; border-bottom-left-radius: 0; border-top-right-radius: 4px; border-bottom-right-radius: 4px; background: #f5f5f5; color: #000000;')
        
        # 添加控件到融合式布局
        count_widget_layout.addWidget(self.decrease_button)
        count_widget_layout.addWidget(self.count_label)
        count_widget_layout.addWidget(self.increase_button)
        
        # 将标题和人数调节控件添加到第一层布局
        first_layer_layout.addWidget(self.instant_draw_title)
        first_layer_layout.addWidget(self.count_widget)
        
        # 第二层：功能按钮布局 - 融合三个按钮为一个紧凑控件
        button_control_container = QWidget()
        button_control_layout = QHBoxLayout(button_control_container)
        button_control_layout.setContentsMargins(0, 0, 0, 0)
        button_control_layout.setSpacing(0)
        
        # 创建融合式功能按钮控件
        self.function_widget = QWidget()
        self.function_widget.setFixedSize(135, 30)  # 整体宽度
        function_widget_layout = QHBoxLayout(self.function_widget)
        function_widget_layout.setContentsMargins(0, 0, 0, 0)
        function_widget_layout.setSpacing(0)
        
        # 最左侧：重置按钮
        self.reset_button = PushButton("重置")
        self.reset_button.setFixedSize(45, 30)
        if dark_mode:
            self.reset_button.setStyleSheet('border-top-left-radius: 4px; border-bottom-left-radius: 4px; border-top-right-radius: 0; border-bottom-right-radius: 0; background: #2a2a2a; color: #ffffff;')
        else:
            self.reset_button.setStyleSheet('border-top-left-radius: 4px; border-bottom-left-radius: 4px; border-top-right-radius: 0; border-bottom-right-radius: 0; background: #f5f5f5; color: #000000;')
        
        # 中间：点名按钮
        self.instant_draw_button = PushButton("点名")
        self.instant_draw_button.setFixedSize(45, 30)
        if dark_mode:
            self.instant_draw_button.setStyleSheet('border-left: none; border-right: none; background: #2a2a2a; color: #ffffff;')
        else:
            self.instant_draw_button.setStyleSheet('border-left: none; border-right: none; background: #f5f5f5; color: #000000;')
        
        # 右侧：设置按钮（打开小浮窗界面）
        self.settings_button = PushButton("设置")
        self.settings_button.setFixedSize(45, 30)
        if dark_mode:
            self.settings_button.setStyleSheet('border-top-left-radius: 0; border-bottom-left-radius: 0; border-top-right-radius: 4px; border-bottom-right-radius: 4px; background: #2a2a2a; color: #ffffff;')
        else:
            self.settings_button.setStyleSheet('border-top-left-radius: 0; border-bottom-left-radius: 0; border-top-right-radius: 4px; border-bottom-right-radius: 4px; background: #f5f5f5; color: #000000;')
        
        # 添加控件到融合式布局
        function_widget_layout.addWidget(self.reset_button)
        function_widget_layout.addWidget(self.instant_draw_button)
        function_widget_layout.addWidget(self.settings_button)
        
        # 将融合式控件添加到第二层布局
        button_control_layout.addWidget(self.function_widget)
        
        # 将两层布局添加到主布局
        main_layout.addWidget(first_layer_container)
        main_layout.addWidget(button_control_container)
        
        # 设置字体
        self.reset_button.setFont(QFont(load_custom_font(), 10))
        self.instant_draw_button.setFont(QFont(load_custom_font(), 10))
        self.increase_button.setFont(QFont(load_custom_font(), 10))
        self.decrease_button.setFont(QFont(load_custom_font(), 10))
        self.settings_button.setFont(QFont(load_custom_font(), 10))
        self.count_label.setFont(QFont(load_custom_font(), 10))
        self.instant_draw_title.setFont(QFont(load_custom_font(), 12))
        
        # 连接信号
        if hasattr(self.reset_button, 'clicked'):
            self.reset_button.clicked.connect(self._reset_instant_draw)
        if hasattr(self.instant_draw_button, 'clicked'):
            self.instant_draw_button.clicked.connect(self._show_instant_draw_window)
        if hasattr(self.increase_button, 'clicked'):
            self.increase_button.clicked.connect(self._increase_count)
        if hasattr(self.decrease_button, 'clicked'):
            self.decrease_button.clicked.connect(self._decrease_count)
        if hasattr(self.settings_button, 'clicked'):
            self.settings_button.clicked.connect(self._show_settings_window)
            
        # 初始化当前抽取人数
        self.current_count = 1
        
        # 为整个即抽容器添加拖动功能（仅空白区域）
        self.instant_draw_container.mousePressEvent = self.on_instant_draw_container_press
        self.instant_draw_container.mouseReleaseEvent = self.on_instant_draw_container_release

        # 根据排列方式决定添加位置
        target_container = None
        
        # 确定目标容器 - 支持3种独立排列样式
        if self.button_arrangement_mode == 0:  # 矩形排列
            target_container = self.bottom_container if hasattr(self, 'bottom_container') and self.bottom_container else None
        elif self.button_arrangement_mode == 1:  # 竖着排列
            target_container = self.top_container if hasattr(self, 'top_container') and self.top_container else None
        elif self.button_arrangement_mode == 2:  # 横着排列
            # 横着排列使用专用的水平容器，确保与竖着排列区分
            if hasattr(self, 'horizontal_container') and self.horizontal_container:
                target_container = self.horizontal_container
            elif hasattr(self, 'top_container') and self.top_container:
                # 如果没有专门的horizontal_container，则使用top_container
                target_container = self.top_container
        
        # 添加即抽容器到目标位置
        if target_container:
            target_container.layout().addWidget(self.instant_draw_container)
        else:
            self.container_button.layout().addWidget(self.instant_draw_container)

    def _apply_window_styles(self):
        # 白露：应用窗口样式和标志
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.NoFocus | Qt.Popup)
        # 移除完全透明背景设置，使用样式表设置背景透明度
        self.setAttribute(Qt.WA_TranslucentBackground)
        try:
            opacity = self.transparency_mode
            # 根据主题设置不同的背景颜色
            if dark_mode:
                # 深色模式背景颜色
                bg_color = f'rgba(65, 66, 66, {opacity})'
            else:
                # 浅色模式背景颜色
                bg_color = f'rgba(240, 240, 240, {opacity})'
            self.setStyleSheet(f'border-radius: 5px; background-color: {bg_color};')
        except Exception as e:
            self.setStyleSheet('border-radius: 5px; background-color: rgba(65, 66, 66, 0.3);')
            logger.error(f"应用窗口样式失败: {e}")

    def _setup_event_handlers(self):
        # 小鸟游星野：设置所有事件处理器 - 无论控件是否显示都要绑定 ✧(๑•̀ㅂ•́)ow✧
        if hasattr(self, 'menu_label') and self.menu_label is not None:
            self.menu_label.mousePressEvent = lambda event: self.start_drag(event)
            self.menu_label.mouseReleaseEvent = self.stop_drag

        # 白露：人物标签始终存在，必须绑定事件处理器
        if hasattr(self, 'people_label') and self.people_label is not None:
            self.people_label.mousePressEvent = self.on_people_press
            self.people_label.mouseReleaseEvent = self.on_people_release

        # 小鸟游星野：闪抽按钮事件处理器 - 与点名按钮相同的拖动功能 ✧(๑•̀ㅂ•́)๑
        if hasattr(self, 'flash_button') and self.flash_button is not None:
            self.flash_button.mousePressEvent = self.on_flash_press
            self.flash_button.mouseReleaseEvent = self.on_flash_release
            
        # 即抽按钮和重置按钮的拖动事件处理器 - 支持长按拖动
        if hasattr(self, 'instant_draw_button') and self.instant_draw_button is not None:
            self.instant_draw_button.mousePressEvent = self.on_instant_draw_button_press
            self.instant_draw_button.mouseReleaseEvent = self.on_instant_draw_button_release
            
        if hasattr(self, 'reset_button') and self.reset_button is not None:
            self.reset_button.mousePressEvent = self.on_reset_button_press
            self.reset_button.mouseReleaseEvent = self.on_reset_button_release
            
        # 加减按钮的拖动事件处理器 - 支持长按拖动
        if hasattr(self, 'increase_button') and self.increase_button is not None:
            self.increase_button.mousePressEvent = self.on_increase_button_press
            self.increase_button.mouseReleaseEvent = self.on_increase_button_release
            
        if hasattr(self, 'decrease_button') and self.decrease_button is not None:
            self.decrease_button.mousePressEvent = self.on_decrease_button_press
            self.decrease_button.mouseReleaseEvent = self.on_decrease_button_release

    def _init_drag_system(self):
        # 白露：初始化拖动系统
        self.drag_position = QPoint()
        self.drag_start_position = QPoint()
        self.is_dragging = False
        self.click_timer = QTimer(self)
        self.click_timer.setSingleShot(True)
        self.click_timer.timeout.connect(lambda: self.start_drag(None))

        self.move_timer = QTimer(self)
        self.move_timer.setSingleShot(True)
        self.move_timer.timeout.connect(self.save_position)

    def on_people_press(self, event):
        # 小鸟游星野：记录拖动起始位置 ✧(๑•̀ㅂ•́)ow✧
        self.drag_start_position = event.pos()
        # 启动长按计时器（100毫秒 - 进一步优化响应速度）
        self.click_timer.start(100)

    def on_people_release(self, event):
        if self.click_timer.isActive():
            # 短按：停止计时器并触发点击事件
            self.click_timer.stop()
            self.on_people_clicked()
            # 长按：计时器已触发拖动，不执行点击
            
    def on_reset_button_press(self, event):
        """重置按钮按下事件 - 支持长按拖动"""
        if event.button() == Qt.LeftButton:
            self._press_start_time = QDateTime.currentMSecsSinceEpoch()
            self._drag_start_pos = event.globalPos()
            self._original_window_pos = self.pos()
            self._long_press_triggered = False
            self._was_dragging = False  # 重置拖动标志
            
            # 启动长按检测计时器
            if hasattr(self, '_long_press_timer') and self._long_press_timer:
                self._long_press_timer.start(self._long_press_duration)
    
    def on_reset_button_release(self, event):
        """重置按钮释放事件 - 区分点击和拖动"""
        if event.button() == Qt.LeftButton:
            # 先保存拖动状态，然后再重置
            was_dragging = self._was_dragging
            
            # 重置拖动状态
            self._was_dragging = False
            self._long_press_triggered = False
            
            # 停止长按计时器
            if hasattr(self, '_long_press_timer') and self._long_press_timer:
                self._long_press_timer.stop()
            
            # 如果没有拖动，则视为点击事件
            if not was_dragging:
                # 调用重置功能
                self._reset_instant_draw()

    def on_instant_draw_button_press(self, event):
        # 即抽按钮按下事件 - 支持长按拖动
        self.drag_start_position = event.pos()
        # 启动长按计时器（100毫秒）
        self.click_timer.start(100)
        
    def on_instant_draw_button_release(self, event):
        if self._is_non_class_time():
            try:
                enc_settings_path = path_manager.get_enc_set_path()
                with open_file(enc_settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    if settings.get('hashed_set', {}).get('start_password_enabled', False) == True:
                        from app.common.password_dialog import PasswordDialog
                        dialog = PasswordDialog(self)
                        if dialog.exec_() != QDialog.Accepted:
                            logger.error("用户取消在课间使用抽取功能")
                            return
            except Exception as e:
                logger.error(f"密码验证失败: {e}")
                return
                
        if self.click_timer.isActive():
            # 短按：停止计时器并触发点击事件
            self.click_timer.stop()
            self._show_instant_draw_window()
            # 长按：计时器已触发拖动，不执行点击
            
    def on_reset_button_press(self, event):
        # 重置按钮按下事件 - 支持长按拖动
        self.drag_start_position = event.pos()
        # 启动长按计时器（100毫秒）
        self.click_timer.start(100)
        
    def on_reset_button_release(self, event):
        if self._is_non_class_time():
            try:
                enc_settings_path = path_manager.get_enc_set_path()
                with open_file(enc_settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    if settings.get('hashed_set', {}).get('start_password_enabled', False) == True:
                        from app.common.password_dialog import PasswordDialog
                        dialog = PasswordDialog(self)
                        if dialog.exec_() != QDialog.Accepted:
                            logger.error("用户取消在课间使用抽取功能")
                            return
            except Exception as e:
                logger.error(f"密码验证失败: {e}")
                return

        if self.click_timer.isActive():
            # 短按：停止计时器并触发点击事件
            self.click_timer.stop()
            self._reset_count()
            # 长按：计时器已触发拖动，不执行点击
            
    def on_increase_button_press(self, event):
        # 增加按钮按下事件 - 支持长按拖动
        self.drag_start_position = event.pos()
        # 启动长按计时器（100毫秒）
        self.click_timer.start(100)
        
    def on_increase_button_release(self, event):
        if self._is_non_class_time():
            try:
                enc_settings_path = path_manager.get_enc_set_path()
                with open_file(enc_settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    if settings.get('hashed_set', {}).get('start_password_enabled', False) == True:
                        from app.common.password_dialog import PasswordDialog
                        dialog = PasswordDialog(self)
                        if dialog.exec_() != QDialog.Accepted:
                            logger.error("用户取消在课间使用抽取功能")
                            return
            except Exception as e:
                logger.error(f"密码验证失败: {e}")
                return

        if self.click_timer.isActive():
            # 短按：停止计时器并触发点击事件
            self.click_timer.stop()
            self._increase_count()
            # 长按：计时器已触发拖动，不执行点击
            
    def on_decrease_button_press(self, event):
        # 减少按钮按下事件 - 支持长按拖动
        self.drag_start_position = event.pos()
        # 启动长按计时器（100毫秒）
        self.click_timer.start(100)
        
    def on_decrease_button_release(self, event):
        if self._is_non_class_time():
            try:
                enc_settings_path = path_manager.get_enc_set_path()
                with open_file(enc_settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    if settings.get('hashed_set', {}).get('start_password_enabled', False) == True:
                        from app.common.password_dialog import PasswordDialog
                        dialog = PasswordDialog(self)
                        if dialog.exec_() != QDialog.Accepted:
                            logger.error("用户取消在课间使用抽取功能")
                            return
            except Exception as e:
                logger.error(f"密码验证失败: {e}")
                return
                
        if self.click_timer.isActive():
            # 短按：停止计时器并触发点击事件
            self.click_timer.stop()
            self._decrease_count()
            # 长按：计时器已触发拖动，不执行点击

    # 白露：处理人物标签点击事件（忽略事件参数）
    def on_people_clicked(self, event=None): 
        # 如果没有选中插件或选中的是主窗口插件，查找主窗口
        main_window = None
        for widget in QApplication.topLevelWidgets():
            if hasattr(widget, 'toggle_window'):  # 通过特征识别主窗口
                main_window = widget
                break

        if main_window:
            main_window.toggle_window()
        else:
            logger.error("未找到主窗口实例")
            self.show_connection_error_dialog()

    def start_drag(self, event=None):
        # 白露：开始拖动逻辑 - 使用鼠标按下的全局位置作为起始位置
        if event:
            # 使用事件的全局位置减去窗口当前位置，得到相对于窗口的偏移量
            self.drag_position = event.globalPos() - self.pos()
        else:
            # 如果没有事件参数，使用之前记录的起始位置
            self.drag_position = self.drag_start_position
        self.is_dragging = True

    def mouseMoveEvent(self, event):
        # 检测长按计时期间的鼠标移动，超过阈值立即触发拖动
        if self.click_timer.isActive() and event.buttons() == Qt.LeftButton:
            delta = event.pos() - self.drag_start_position
            if abs(delta.x()) > 8 or abs(delta.y()) > 8:
                self.click_timer.stop()
                self.start_drag(event)

        if hasattr(self, 'is_dragging') and self.is_dragging and event.buttons() == Qt.LeftButton:
            # 计算鼠标移动偏移量并保持相对位置
            # drag_position现在存储的是鼠标相对于窗口的偏移量
            if hasattr(self, 'drag_position') and self.drag_position is not None:
                new_pos = event.globalPos() - self.drag_position

                # 获取屏幕尺寸
                screen = QApplication.desktop().screenGeometry()

                # 限制窗口不超出屏幕
                new_pos.setX(max(0, min(new_pos.x(), screen.width() - self.width())))
                new_pos.setY(max(0, min(new_pos.y(), screen.height() - self.height())))

                self.move(new_pos)
                
                # 拖动过程中不立即检查边缘，而是在拖动结束后再检查
            else:
                # 如果drag_position未正确设置，重新初始化拖动
                self.start_drag(event)
        super().mouseMoveEvent(event)

    def on_people_release(self, event):
        # 星穹铁道白露：人物标签释放事件处理 - 区分点击和拖动 (≧∇≦)ﾉ
        was_dragging = getattr(self, 'is_dragging', False)
        self.is_dragging = False
        
        if self.click_timer.isActive():
            # 小鸟游星野：短按点击，触发主页面打开 ✧(๑•̀ㅂ•́)๑
            self.click_timer.stop()
            self.on_people_clicked()
        elif was_dragging:
            # 白露：拖动结束，保存新位置 (≧∇≦)ﾉ
            self.save_position()
            
            # 如果启用了边缘贴边隐藏功能，在拖动结束后检查是否需要贴边
            if hasattr(self, 'flash_window_side_switch') and self.flash_window_side_switch:
                # 使用定时器延迟执行边缘检测，确保位置已经保存
                QTimer.singleShot(100, self._check_edge_proximity)
        
        # 如果是BodyLabel（仅图标模式），需要手动调用accept()来处理事件
        if hasattr(self, 'people_label') and isinstance(self.people_label, BodyLabel):
            event.accept()

    def on_flash_press(self, event):
        # 小鸟游星野：闪抽按钮按下事件 - 记录拖动起始位置 ✧(๑•̀ㅂ•́)ow✧
        self.drag_start_position = event.pos()
        # 启动长按计时器（100毫秒 - 进一步优化响应速度）
        self.click_timer.start(100)

    def on_flash_release(self, event):
        # 星穹铁道白露：闪抽按钮释放事件处理 - 区分点击和拖动 (≧∇≦)ﾉ
        was_dragging = getattr(self, 'is_dragging', False)
        self.is_dragging = False
        
        if self.click_timer.isActive():
            # 小鸟游星野：短按点击，触发闪抽窗口 ✧(๑•̀ㅂ•́)๑
            self.click_timer.stop()
            self.on_flash_clicked()
        elif was_dragging:
            # 白露：拖动结束，保存新位置 (≧∇≦)ﾉ
            self.save_position()
        
        # 如果是BodyLabel（仅图标模式），需要手动调用accept()来处理事件
        if hasattr(self, 'flash_button') and isinstance(self.flash_button, BodyLabel):
            event.accept()

    def on_flash_clicked(self, event=None):
        # 小鸟游星野：闪抽按钮点击事件 - 显示直接抽取窗口 ✧(๑•̀ㅂ•́)๑
        self._show_direct_extraction_window()
    
    def on_instant_draw_container_press(self, event):
        """处理即抽容器鼠标按下事件，支持拖动（仅空白区域）"""
        if event.button() == Qt.LeftButton:
            # 获取点击位置的子控件
            child = self.instant_draw_container.childAt(event.pos())
            # 如果点击的是容器空白区域（没有子控件或子控件不是按钮），则触发拖动
            if child is None or not isinstance(child, QPushButton):
                self.drag_start_position = event.pos()
                # 启动长按计时器
                if hasattr(self, 'click_timer'):
                    self.click_timer.start(100)  # 100ms后开始拖动
                event.accept()
            else:
                # 如果点击的是按钮，不处理拖动，让按钮保持原有功能
                event.ignore()
        else:
            event.ignore()
    
    def on_instant_draw_container_release(self, event):
        """处理即抽容器鼠标释放事件（仅空白区域）"""
        was_dragging = getattr(self, 'is_dragging', False)
        self.is_dragging = False
        
        if hasattr(self, 'click_timer') and self.click_timer.isActive():
            # 短按点击容器空白区域，不执行任何操作
            self.click_timer.stop()
            # 注释掉下面这行，使点击空白区域不触发即抽窗口
            # self._show_instant_draw_window()
        elif was_dragging:
            # 拖动结束，保存新位置
            self.save_position()
            
            # 如果启用了边缘贴边隐藏功能，在拖动结束后检查是否需要贴边
            if hasattr(self, 'flash_window_side_switch') and self.flash_window_side_switch:
                # 使用定时器延迟执行边缘检测，确保位置已经保存
                QTimer.singleShot(100, self._check_edge_proximity)
        
        event.accept()

    def show_connection_error_dialog(self):
        # 小鸟游星野：显示连接错误对话框
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("连接错误")
        msg_box.setText("无法连接到主窗口")
        msg_box.setInformativeText("请检查应用程序是否正常运行")
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec_()

    def mousePressEvent(self, event):
        # 星穹铁道白露：右键点击也会触发事件哦~ 现在整个窗口都可以拖动啦 (๑•̀ㅂ•́)๑
        if event.button() == Qt.LeftButton:
            # 记录拖动起始位置
            self.drag_start_position = event.pos()
            # 启动长按计时器（100毫秒 - 优化响应速度）
            self.click_timer.start(100)
        else:
            event.ignore()

    def _animate_button_press(self, button):
        """按钮按下动画效果"""
        # 使用样式表实现简单的按下效果
        original_style = button.styleSheet()
        pressed_style = original_style + "transform: scale(0.95);"
        button.setStyleSheet(pressed_style)
        # 保存原始样式以便恢复
        if not hasattr(button, '_original_style'):
            button._original_style = original_style
    
    def _animate_button_release(self, button):
        """按钮释放动画效果"""
        # 恢复原始样式
        if hasattr(button, '_original_style'):
            button.setStyleSheet(button._original_style)
    
    def _animate_count_change(self, new_count):
        """人数变化动画效果"""
        # 检查count_label是否存在，只有在即抽模式下才存在
        if not hasattr(self, 'count_label') or self.count_label is None:
            return
            
        # 使用定时器实现简单的淡入淡出效果
        original_style = self.count_label.styleSheet()
        
        # 淡出效果
        fade_out_style = original_style + "opacity: 0.3;"
        self.count_label.setStyleSheet(fade_out_style)
        
        def update_text():
            self.count_label.setText(str(new_count))
            # 淡入效果
            self.count_label.setStyleSheet(original_style)
        
        QTimer.singleShot(150, update_text)
    
    def stop_drag(self, event=None):
        # 小鸟游星野：停止拖动时的处理逻辑 - 菜单标签专用 ✧(๑•̀ㅂ•́)๑
        self.setCursor(Qt.ArrowCursor)
        self.move_timer.stop()
        
        # 白露：菜单标签拖动结束，保存新位置
        self.save_position()
        
        # 如果启用了边缘贴边隐藏功能，在拖动结束后检查是否需要贴边
        if hasattr(self, 'flash_window_side_switch') and self.flash_window_side_switch:
            # 使用定时器延迟执行边缘检测，确保位置已经保存
            QTimer.singleShot(100, self._check_edge_proximity)
        
        # 小鸟游星野：延迟保存，避免频繁写入
        self.move_timer.start(300)
        
        # 如果是BodyLabel（仅图标模式），需要手动调用accept()来处理事件
        if event and hasattr(self, 'menu_label') and isinstance(self.menu_label, BodyLabel):
            event.accept()

    def save_position(self):
        pos = self.pos()
        settings_path = path_manager.get_settings_path("Settings.json")
        try:
            with open_file(settings_path, "r") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            data = {}
        
        data["position"] = {
            "x": pos.x(), 
            "y": pos.y()
        }
        with open_file(settings_path, "w") as f:
            json.dump(data, f, indent=4)
        
    def load_position(self):
        settings_path = path_manager.get_settings_path("Settings.json")
        try:
            with open_file(settings_path, "r") as f:
                data = json.load(f)
                pos = data.get("position", {"x": 100, "y": 100})
                self.move(QPoint(pos["x"], pos["y"]))
                
                # 如果启用了边缘贴边隐藏功能，检查窗口是否需要贴边
                if hasattr(self, 'flash_window_side_switch') and self.flash_window_side_switch:
                    # 获取屏幕尺寸和窗口位置
                    screen = QApplication.desktop().screenGeometry()
                    window_pos = self.pos()
                    window_width = self.width()
                    window_height = self.height()
                    
                    # 定义边缘阈值（像素）
                    edge_threshold = 30
                    
                    # 检查窗口是否靠近边缘，只有靠近边缘时才执行贴边隐藏
                    is_near_edge = (
                        window_pos.x() <= edge_threshold or
                        window_pos.x() + window_width >= screen.width() - edge_threshold or
                        window_pos.y() <= edge_threshold or
                        window_pos.y() + window_height >= screen.height() - edge_threshold
                    )
                    
                    if is_near_edge:
                        # 使用定时器延迟执行边缘检测，确保窗口已经完全加载
                        QTimer.singleShot(100, self._check_edge_proximity)
                    else:
                        # 检查窗口是否已经处于隐藏状态
                        # 左边缘隐藏
                        if window_pos.x() + window_width <= 0:
                            # 创建向右箭头按钮
                            QTimer.singleShot(100, lambda: self._create_arrow_button('right', 0, window_pos.y() + window_height // 2 - 15))
                        # 右边缘隐藏
                        elif window_pos.x() >= screen.width():
                            # 创建向左箭头按钮
                            QTimer.singleShot(100, lambda: self._create_arrow_button('left', screen.width() - 30, window_pos.y() + window_height // 2 - 15))
        except (FileNotFoundError, json.JSONDecodeError):
            screen = QApplication.desktop().screenGeometry()
            x = (screen.width() - self.width()) // 2
            y = (screen.height() - self.height()) // 2
            self.move(QPoint(x, y))

    def _show_direct_extraction_window(self, draw_count=1, class_name=None, group_name='抽取全班学生', gender_name='抽取所有性别'):
        # 小鸟游星野：显示直接抽取窗口 - 包含pumping_people功能 ✧(๑•̀ㅂ•́)๑
        if self._is_non_class_time():
            try:
                from app.common.path_utils import path_manager, open_file
                enc_settings_path = path_manager.get_enc_set_path()
                with open_file(enc_settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    if settings.get('hashed_set', {}).get('start_password_enabled', False) == True:
                        from app.common.password_dialog import PasswordDialog
                        dialog = PasswordDialog(self)
                        if dialog.exec_() != QDialog.Accepted:
                            logger.error("用户取消在课间使用抽取功能")
                            return
            except Exception as e:
                logger.error(f"密码验证失败: {e}")
                return
                
        try:
            # 导入pumping_people模块
            from app.view.main_page.flash_pumping_people import instant_draw
            
            # 初始化当前抽取人数
            self.current_count = draw_count

            # 获取班级列表
            self._load_classes()
            
            try:
                from app.common.path_utils import path_manager, open_file
                with open_file(path_manager.get_settings_path(), 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    fixed_default_list = settings.get('instant_draw', {}).get('fixed_default_list', '')
                    self.use_cwci_display = settings.get('instant_draw', {}).get('use_cwci_display', False)
                    # 如果设置了固定默认名单且名单文件存在，则使用该名单
                    if fixed_default_list and fixed_default_list != "":
                        list_file = path_manager.get_resource_path('list', f'{fixed_default_list}.json')
                        if path_manager.file_exists(list_file):
                            class_name = fixed_default_list
            except Exception as e:
                logger.error(f"加载固定默认名单设置时出错: {e}")
                class_name = self.class_combo.currentText()
            group_name = group_name
            gender_name = gender_name
            
            # 创建自定义标题栏的对话框
            self.pumping_widget = QDialog()
            self.pumping_widget.setWindowFlags(Qt.FramelessWindowHint | Qt.Window | Qt.Tool | Qt.WindowStaysOnTopHint)
            self.pumping_widget.setWindowTitle("SecRandom - 抽取")
            # self.pumping_widget.setSizeGripEnabled(True)
            
            # 🐦 小鸟游星野：创建自定义标题栏啦~ (≧∇≦)ﾉ
            self.title_bar = QWidget()
            self.title_bar.setObjectName("CustomTitleBar")
            self.title_bar.setFixedHeight(35)
            
            # 标题栏布局
            title_layout = QHBoxLayout(self.title_bar)
            title_layout.setContentsMargins(10, 0, 10, 0)
            
            # 窗口标题
            title_text = "SecRandom - 抽取"
            self.title_label = BodyLabel(title_text)
            self.title_label.setObjectName("TitleLabel")
            self.title_label.setFont(QFont(load_custom_font(), 12))
            
            # 窗口控制按钮
            self.close_btn = QPushButton("✕")
            self.close_btn.setObjectName("CloseButton")
            self.close_btn.setFixedSize(25, 25)
            self.close_btn.clicked.connect(self.pumping_widget.reject)

            # 添加组件到标题栏
            title_layout.addWidget(self.title_label)
            title_layout.addStretch()
            title_layout.addWidget(self.close_btn)
            
            # 创建pumping_people内容，并传递班级、小组和性别信息
            self.pumping_content = instant_draw(draw_count=self.current_count, 
                                                 class_name=class_name, 
                                                 group_name=group_name, 
                                                 gender_name=gender_name)
            
            # 获取字体大小设置以动态调整窗口大小
            try:
                from app.common.path_utils import path_manager, open_file
                settings_file = path_manager.get_settings_path()
                with open_file(settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    font_size = settings['pumping_people']['font_size']
                    show_student_image = settings['pumping_people']['show_student_image']
            except Exception as e:
                font_size = 50  # 默认字体大小
                show_student_image = False
                logger.error(f"加载字体设置时出错: {e}, 使用默认设置")
            
            # 根据字体大小计算窗口尺寸
            # 基础尺寸 + 字体大小相关缩放，确保内容完整显示
            base_width = 310
            base_height = 350
            
            # 字体大小对应的缩放因子，确保小字号有足够空间，适配到200字号
            if font_size <= 30:
                scale_factor = 0.7
            elif font_size <= 40:
                scale_factor = 0.9
            elif font_size <= 50:
                scale_factor = 1.1
            elif font_size <= 60:
                scale_factor = 1.3
            elif font_size <= 80:
                scale_factor = 1.5
            elif font_size <= 100:
                scale_factor = 1.8
            elif font_size <= 120:
                scale_factor = 2.1
            elif font_size <= 150:
                scale_factor = 2.5
            elif font_size <= 180:
                scale_factor = 3.0
            else:
                scale_factor = 3.5

            try:
                # 尝试获取学生数据以计算最大字数
                from app.common.path_utils import path_manager, open_file
                student_file = path_manager.get_resource_path('list', f'{class_name}.json')
                if path_manager.file_exists(student_file):
                    with open_file(student_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        # 计算所有学生名称的最大字数
                        max_chars = 0
                        for student_name in data.keys():
                            # 去除【】符号后计算字数
                            clean_name = student_name.replace('【', '').replace('】', '')
                            max_chars = max(max_chars, len(clean_name))
                        
                        if max_chars > 3:
                            # 根据最大字数和字体大小计算额外宽度，减去3个字的基准宽度
                            char_width_bonus = int((max_chars - 3) * font_size * 0.6)
                            # 确保额外宽度在合理范围内
                            char_width_bonus = max(50, min(400, char_width_bonus))
                        else:
                            char_width_bonus = 50  # 3个字或更少时使用最小额外宽度
                else:
                    char_width_bonus = 100  # 默认值
            except Exception as e:
                logger.error(f"计算学生名称字数时出错: {e}, 使用默认值")
                char_width_bonus = 100  # 默认值
            
            # 计算动态窗口大小，确保最小和最大尺寸限制，适配200字号
            image_width_bonus = 0

            # 如果显示学生图片，需要增加窗口宽度
            if show_student_image and self.current_count == 1:
                # 显示图片时根据字体大小动态计算图片额外宽度
                if font_size <= 30:
                    image_width_bonus = 170   # 小字体时的图片额外宽度
                elif font_size <= 50:
                    image_width_bonus = 170  # 中等字体时的图片额外宽度
                elif font_size <= 80:
                    image_width_bonus = 240  # 较大字体时的图片额外宽度
                elif font_size <= 120:
                    image_width_bonus = 320  # 大字体时的图片额外宽度
                elif font_size <= 150:
                    image_width_bonus = 450  # 很大字体时的图片额外宽度
                elif font_size <= 180:
                    image_width_bonus = 600  # 很大字体时的图片额外宽度
                else:
                    image_width_bonus = 800  # 超大字体时的图片额外宽度
            elif show_student_image and self.current_count > 1:
                # 显示图片时根据字体大小动态计算图片额外宽度
                if font_size <= 30:
                    image_width_bonus = 130   # 小字体时的图片额外宽度
                elif font_size <= 50:
                    image_width_bonus = 130  # 中等字体时的图片额外宽度
                elif font_size <= 80:
                    image_width_bonus = 200  # 较大字体时的图片额外宽度
                elif font_size <= 120:
                    image_width_bonus = 280  # 大字体时的图片额外宽度
                elif font_size <= 150:
                    image_width_bonus = 410  # 很大字体时的图片额外宽度
                elif font_size <= 180:
                    image_width_bonus = 560  # 很大字体时的图片额外宽度
                else:
                    image_width_bonus = 760  # 超大字体时的图片额外宽度

            dynamic_width = max(150, min(1920, int((base_width + image_width_bonus + char_width_bonus) * scale_factor)))
            dynamic_height = max(170, min(1080, int(base_height * scale_factor)))
            
            self.pumping_widget.setFixedSize(dynamic_width, dynamic_height)
            
            # 创建倒计时标签
            self.countdown_label = BodyLabel("")
            self.countdown_label.setObjectName("CountdownLabel")
            self.countdown_label.setFont(QFont(load_custom_font(), 12))
            self.countdown_label.setAlignment(Qt.AlignCenter | Qt.AlignVCenter)

            # 创建底部布局
            bottom_layout = QHBoxLayout()
            bottom_layout.setContentsMargins(10, 5, 10, 5)
            bottom_layout.addWidget(self.countdown_label)

            # 主布局
            main_layout = QVBoxLayout(self.pumping_widget)
            main_layout.setContentsMargins(0, 0, 0, 0)
            main_layout.setSpacing(0)
            # 添加自定义标题栏
            main_layout.addWidget(self.title_bar)
            # 添加内容区域
            main_layout.addWidget(self.pumping_content)
            # 添加底部布局
            main_layout.addLayout(bottom_layout)
            
            # 添加窗口拖动功能 - 整个窗口都可以拖动
            self.dragging = False
            self.drag_position = None
            self.pumping_widget.mousePressEvent = self._on_window_press
            self.pumping_widget.mouseMoveEvent = self._on_window_move
            self.pumping_widget.mouseReleaseEvent = self._on_window_release
            
            # 连接窗口关闭事件以清理定时器
            self.pumping_widget.finished.connect(self._on_pumping_widget_closed)
            
            # 标题栏也保持拖动功能
            self.title_bar.mousePressEvent = self._on_title_bar_press
            self.title_bar.mouseMoveEvent = self._on_title_bar_move
            self.title_bar.mouseReleaseEvent = self._on_title_bar_release
            self.update_theme_style()
            
            # 窗口居中显示 - 相对于屏幕居中
            screen = QApplication.desktop().screenGeometry()
            x = (screen.width() - self.pumping_widget.width()) // 2
            y = (screen.height() - self.pumping_widget.height()) // 2
            self.pumping_widget.move(QPoint(x, y))
            
            if not self.use_cwci_display:
                # 直接显示窗口
                self.pumping_widget.show()
                logger.info("直接抽取窗口已打开")
            
            # 禁用闪抽按钮，防止重复点击
            if hasattr(self, 'flash_button') and self.flash_button is not None:
                self.flash_button.setEnabled(False)
                logger.info("闪抽按钮已禁用")
            
            # 禁用即抽按钮，防止重复点击
            if hasattr(self, 'instant_draw_button') and self.instant_draw_button is not None:
                self.instant_draw_button.setEnabled(False)
                logger.info("即抽按钮已禁用")
            
            # 标记抽取正在进行
            self.is_drawing = True
            logger.info("抽取状态已设置为进行中")
            
            self.pumping_content.start_draw()
            
            # 连接抽取完成信号，在抽取完成后才开始倒计时
            self.pumping_content.draw_finished.connect(self._start_countdown_after_draw)
            
            # 初始显示提示信息
            self.countdown_label.setText("抽取进行中，完成后将开始倒计时")
            self.countdown_label.setFont(QFont(load_custom_font(), 12))
            
        except ImportError as e:
            logger.error(f"导入pumping_people模块失败: {e}")
            error_dialog = Dialog("加载失败", "无法加载抽取功能模块，请检查文件是否存在", self)
            error_dialog.yesButton.setText("确定")
            error_dialog.cancelButton.hide()
            error_dialog.buttonLayout.insertStretch(1)
            error_dialog.exec()
            
        except Exception as e:
            logger.error(f"创建直接抽取窗口失败: {e}")
            error_dialog = Dialog("创建失败", f"创建抽取窗口时发生错误: {str(e)}", self)
            error_dialog.yesButton.setText("确定")
            error_dialog.cancelButton.hide()
            error_dialog.buttonLayout.insertStretch(1)
            error_dialog.exec()
    
    def _sort_key(self, group):
        """将小组名称转换为排序键"""
        # 尝试匹配 '第X小组' 或 '第X组' 格式
        match = re.match(r'第\s*(\d+|一|二|三|四|五|六|七|八|九|十)\s*(小组|组)', group)
        if match:
            num = match.group(1)
            num_map = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10}
            if num in num_map:
                return (1, num_map[num])  # 类型1: 中文数字组
            else:
                return (1, int(num))       # 类型1: 阿拉伯数字组
        
        # 尝试匹配仅数字格式
        try:
            return (2, int(group))         # 类型2: 纯数字组
        except ValueError:
            pass
        
        # 其他名称组，保持排序功能不变
        return (3, group) # 类型3: 其他名称组

    def _on_title_bar_press(self, event):
        # 🐦 小鸟游星野：窗口拖动功能~ 按住标题栏就能移动啦 (๑•̀ㅂ•́)๑
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPos() - self.pumping_widget.frameGeometry().topLeft()
            event.accept()

    def _on_title_bar_move(self, event):
        if self.dragging and event.buttons() == Qt.LeftButton:
            self.pumping_widget.move(event.globalPos() - self.drag_position)
            event.accept()

    def _on_title_bar_release(self, event):
        self.dragging = False

    def _start_countdown_after_draw(self):
        """抽取完成后开始倒计时"""
        # 从设置中获取闪抽窗口自动关闭设置
        try:
            # 获取设置
            settings_file = path_manager.get_settings_path()
            with open_file(settings_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                
            # 检查是否启用自动关闭
            auto_close_enabled = settings['foundation']['flash_window_auto_close']
            close_time_setting = settings['foundation']['flash_window_close_time']
            
            # 根据设置值映射到实际的关闭时间
            # 0：1，1：2，2：3，3：5，4：10，5：15，6：30
            close_time_mapping = {
                0: 1,
                1: 2,
                2: 3,
                3: 5,
                4: 10,
                5: 15,
                6: 30
            }
            
            # 如果close_time_setting是字符串类型，尝试转换为整数
            if isinstance(close_time_setting, str):
                try:
                    close_time_setting = int(close_time_setting)
                except ValueError:
                    close_time_setting = 2
            
            close_time = close_time_mapping.get(close_time_setting, 3)  # 默认值为3秒
            
            if self.use_cwci_display:
                self.pumping_widget.reject()
                return

            if auto_close_enabled:
                # 初始化倒计时
                self.remaining_time = close_time
                self.countdown_label.setText(f"将在{self.remaining_time}秒自动关闭该窗口")
                self.countdown_label.setFont(QFont(load_custom_font(), 12))

                # 创建倒计时定时器
                self.countdown_timer = QTimer(self.pumping_widget)
                self.countdown_timer.timeout.connect(self._update_countdown)
                self.countdown_timer.start(1000)  # 每秒更新一次

                # 创建自动关闭定时器
                self.auto_close_timer = QTimer(self.pumping_widget)
                self.auto_close_timer.setSingleShot(True)
                self.auto_close_timer.timeout.connect(self.pumping_widget.reject)
                self.auto_close_timer.start(close_time * 1000)  # 转换为毫秒
                logger.info(f"闪抽窗口将在{close_time}秒后自动关闭")
            else:
                logger.info("闪抽窗口自动关闭功能已禁用")
        except Exception as e:
            logger.error(f"加载闪抽窗口设置时出错: {e}, 使用默认设置")
            # 默认启用3秒自动关闭
            close_time = 3
            self.remaining_time = close_time
            self.countdown_label.setText(f"将在{self.remaining_time}秒自动关闭该窗口")
            self.countdown_label.setFont(QFont(load_custom_font(), 12))

            # 创建倒计时定时器
            self.countdown_timer = QTimer(self.pumping_widget)
            self.countdown_timer.timeout.connect(self._update_countdown)
            self.countdown_timer.start(1000)  # 每秒更新一次

            self.auto_close_timer = QTimer(self.pumping_widget)
            self.auto_close_timer.setSingleShot(True)
            self.auto_close_timer.timeout.connect(self.pumping_widget.reject)
            self.auto_close_timer.start(close_time * 1000)  # 3秒后自动关闭
    
    def _update_countdown(self):
        # 更新倒计时
        self.remaining_time -= 1
        self.countdown_label.setText(f"将在{self.remaining_time}秒自动关闭该窗口")
        self.countdown_label.setFont(QFont(load_custom_font(), 12))

        # 当倒计时结束时停止定时器
        if self.remaining_time <= 0:
            if hasattr(self, 'countdown_timer'):
                self.countdown_timer.stop()

    def update_theme_style(self):
        """根据当前主题更新样式"""
        if qconfig.theme == Theme.AUTO:
            lightness = QApplication.palette().color(QPalette.Window).lightness()
            is_dark = lightness <= 127
        else:
            is_dark = qconfig.theme == Theme.DARK
        
        colors = {'text': '#F5F5F5', 'bg': '#111116', 'title_bg': '#2D2D2D'} if is_dark else {'text': '#111116', 'bg': '#F5F5F5', 'title_bg': '#E0E0E0'}
        self.pumping_widget.setStyleSheet(f"""
            QDialog {{ background-color: {colors['bg']}; border-radius: 5px; }}
            #CustomTitleBar {{ background-color: {colors['title_bg']}; }}
            #TitleLabel {{ color: {colors['text']}; font-weight: bold; padding: 5px; }}
            #CloseButton {{ 
                background-color: transparent; 
                color: {colors['text']}; 
                border-radius: 4px; 
                font-weight: bold; 
                border: none;
            }}
            #CloseButton:hover {{ 
                background-color: #ff4d4d; 
                color: white; 
                border: none;
            }}
            BodyLabel, QPushButton, QTextEdit {{ color: {colors['text']}; }}
            QLineEdit {{ 
                background-color: {colors['bg']}; 
                color: {colors['text']}; 
                border: 1px solid #555555; 
                border-radius: 4px; 
                padding: 5px; 
            }}
            QPushButton {{ 
                background-color: {colors['bg']}; 
                color: {colors['text']}; 
                border: 1px solid #555555; 
                border-radius: 4px; 
                padding: 5px; 
            }}
            QPushButton:hover {{ background-color: #606060; }}
            QComboBox {{ 
                background-color: {colors['bg']}; 
                color: {colors['text']}; 
                border: 1px solid #555555; 
                border-radius: 4px; 
                padding: 5px; 
            }}
        """)
        
        # 设置标题栏颜色以匹配背景色（仅Windows系统）
        if os.name == 'nt':
            try:
                import ctypes
                hwnd = int(self.pumping_widget.winId())
                
                bg_color = colors['bg'].lstrip('#')
                rgb_color = int(f'FF{bg_color}', 16) if len(bg_color) == 6 else int(bg_color, 16)
                
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    ctypes.c_int(hwnd),
                    35,
                    ctypes.byref(ctypes.c_uint(rgb_color)),
                    ctypes.sizeof(ctypes.c_uint)
                )
            except Exception as e:
                logger.error(f"设置标题栏颜色失败: {str(e)}")

    def _on_window_press(self, event):
        """窗口鼠标按下事件 - 整个窗口都可以拖动"""
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPos() - self.pumping_widget.frameGeometry().topLeft()
            event.accept()
    
    def _on_window_move(self, event):
        """窗口鼠标移动事件"""
        if self.dragging and event.buttons() == Qt.LeftButton:
            self.pumping_widget.move(event.globalPos() - self.drag_position)
            event.accept()
    
    def _on_window_release(self, event):
        """窗口鼠标释放事件"""
        if event.button() == Qt.LeftButton:
            self.dragging = False
            event.accept()
            
    def _on_pumping_widget_closed(self):
        """直接抽取窗口关闭事件 - 清理定时器资源并重新启用闪抽按钮"""
        # 停止自动关闭定时器
        if hasattr(self, 'auto_close_timer') and self.auto_close_timer.isActive():
            self.auto_close_timer.stop()
            logger.info("直接抽取窗口已关闭，自动关闭定时器已停止")

        # 停止倒计时定时器
        if hasattr(self, 'countdown_timer') and self.countdown_timer.isActive():
            self.countdown_timer.stop()
            logger.info("直接抽取窗口已关闭，倒计时定时器已停止")
        
        # 重新启用闪抽按钮
        if hasattr(self, 'flash_button') and self.flash_button is not None:
            self.flash_button.setEnabled(True)
            logger.info("闪抽按钮已重新启用")
        
        # 重新启用即抽按钮
        if hasattr(self, 'instant_draw_button') and self.instant_draw_button is not None:
            self.instant_draw_button.setEnabled(True)
            logger.info("即抽按钮已重新启用")
        
        # 标记抽取已结束
        self.is_drawing = False
        logger.info("抽取状态已设置为结束")
    
    def closeEvent(self, event):
        """窗口关闭事件 - 清理所有定时器资源"""
        # 停止保持置顶定时器
        if hasattr(self, 'keep_top_timer') and self.keep_top_timer.isActive():
            self.keep_top_timer.stop()
            logger.info("浮窗置顶定时器已停止")
        
        # 停止点击定时器
        if hasattr(self, 'click_timer') and self.click_timer.isActive():
            self.click_timer.stop()
            logger.info("点击定时器已停止")
        
        # 停止移动定时器
        if hasattr(self, 'move_timer') and self.move_timer.isActive():
            self.move_timer.stop()
            logger.info("移动定时器已停止")
        
        # 停止自动关闭定时器
        if hasattr(self, 'auto_close_timer') and self.auto_close_timer.isActive():
            self.auto_close_timer.stop()
            logger.info("自动关闭定时器已停止")
        
        # 停止倒计时定时器
        if hasattr(self, 'countdown_timer') and self.countdown_timer.isActive():
            self.countdown_timer.stop()
            logger.info("倒计时定时器已停止")
        
        # 调用父类的closeEvent
        super().closeEvent(event)

    def _init_keep_top_timer(self):
        """初始化保持置顶定时器 - 每5秒钟让浮窗置顶一下"""
        self.keep_top_timer = QTimer(self)
        self.keep_top_timer.timeout.connect(self._keep_window_on_top)
        self.keep_top_timer.start(200)
        logger.info("浮窗置顶定时器已启动")

    def _keep_window_on_top(self):
        """保持窗口置顶"""
        try:
            self.raise_()  # 将窗口提升到最前面
            if hasattr(self, 'arrow_widget') and self.arrow_widget:
                self.arrow_widget.raise_()
            # self.activateWindow()  # 激活窗口
        except Exception as e:
            logger.error(f"保持窗口置顶失败: {e}")

    # 对用户的选择进行返回学生数量或小组数量
    def _get_cleaned_data(self, student_file, group_name, genders):
        with open_file(student_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # 初始化不同情况的列表
            group_data = []
            student_data = []
            for student_name, student_info in data.items():
                if isinstance(student_info, dict) and 'id' in student_info:
                    id = student_info.get('id', '')
                    name = student_name.replace('【', '').replace('】', '')
                    gender = student_info.get('gender', '')
                    group = student_info.get('group', '')
                    exist = student_info.get('exist', True)
                    if group_name == '抽取小组组号':
                        group_data.append((id, group, exist))
                    elif group_name == group:
                        if (not genders) or (genders and gender in genders) or (genders == '抽取所有性别'):
                            student_data.append((id, name, exist))
                    elif group_name == '抽取全班学生':
                        if (not genders) or (genders and gender in genders) or (genders == '抽取所有性别'):
                            student_data.append((id, name, exist))
                        
            if group_name == '抽取小组组号':
                valid_groups = set()
                group_exist_map = {}
                for _, group, exist in group_data:
                    if group not in group_exist_map:
                        group_exist_map[group] = exist
                    else:
                        group_exist_map[group] = group_exist_map[group] or exist
                for group, has_exist in group_exist_map.items():
                    if has_exist:
                        valid_groups.add(group)
                unique_groups = sorted(valid_groups, key=self.sort_key)
                cleaned_data = [(group_id, group, True) for group_id, group in enumerate(sorted(unique_groups, key=self.sort_key), start=1)]
            else:
                cleaned_data = [data for data in student_data if data[2]]
            return cleaned_data

    # 增加抽取人数
    def _increase_count(self):
        """增加抽取人数"""
        if self.current_count < self.max_count:
            self.current_count += 1
            self._animate_count_change(self.current_count)
            self._update_count_display()

    # 减少抽取人数        
    def _decrease_count(self):
        """减少抽取人数"""
        if self.current_count > 1:
            self.current_count -= 1
            self._animate_count_change(self.current_count)
            self._update_count_display()

    # 更新人数显示        
    def _update_count_display(self):
        """更新人数显示"""
        # 检查count_label是否存在，只有在即抽模式下才存在
        if hasattr(self, 'count_label') and self.count_label is not None:
            self.count_label.setText(str(self.current_count))
        
        # 检查按钮是否存在，只有在即抽模式下才存在
        if hasattr(self, 'increase_button') and self.increase_button is not None and hasattr(self, 'decrease_button') and self.decrease_button is not None:
            # 根据当前人数启用/禁用按钮
            self.increase_button.setEnabled(self.current_count < self.max_count)
            self.decrease_button.setEnabled(self.current_count > 1)
            
            # 只有在不在抽取过程中时才根据人数条件启用/禁用即抽按钮
            if not self.is_drawing and hasattr(self, 'instant_draw_button') and self.instant_draw_button is not None:
                self.instant_draw_button.setEnabled(self.current_count <= self.max_count and self.current_count > 0)
            # 如果正在抽取，保持按钮禁用状态
            
            # 如果当前人数超过最大人数，自动调整到最大人数
            if self.current_count > self.max_count:
                self.current_count = self.max_count
                if hasattr(self, 'count_label') and self.count_label is not None:
                    self.count_label.setText(str(self.current_count))
                self._animate_count_change(self.current_count)
                # 重新更新按钮状态
                self.increase_button.setEnabled(self.current_count < self.max_count)
                self.decrease_button.setEnabled(self.current_count > 1)
                # 只有在不在抽取过程中时才根据人数条件启用/禁用即抽按钮
                if not self.is_drawing and hasattr(self, 'instant_draw_button') and self.instant_draw_button is not None:
                    self.instant_draw_button.setEnabled(self.current_count <= self.max_count and self.current_count > 0)
    
    def _reset_count(self):
        # 小鸟游星野：重置抽取人数和已抽取名单 ✧(๑•̀ㅂ•́)๑
        self.current_count = 1
        self._animate_count_change(self.current_count)
        self._update_count_display()
        self._clean_temp_files()

    # 清理临时文件
    def _reset_instant_draw(self):
        """重置即抽功能状态"""
        # 重置抽取人数为1
        self.current_count = 1
        self._animate_count_change(self.current_count)
        self._update_count_display()
        
        # 清理临时抽取记录文件
        self._clean_temp_files()
        
        # 重置抽取状态
        self.is_drawing = False
        
        # 重新启用按钮
        if hasattr(self, 'instant_draw_button') and self.instant_draw_button is not None:
            self.instant_draw_button.setEnabled(True)
        
        if hasattr(self, 'flash_button') and self.flash_button is not None:
            self.flash_button.setEnabled(True)
            
        logger.info("即抽功能已重置")

    def _clean_temp_files(self):
        import glob
        temp_dir = path_manager.get_temp_path()
        if path_manager.file_exists(temp_dir):
            for file in glob.glob(f"{temp_dir}/until_*.json"):
                try:
                    path_manager.remove_file(file)
                    logger.info(f"已清理临时抽取记录文件: {file}")
                except Exception as e:
                    logger.error(f"清理临时抽取记录文件失败: {e}")

    def _load_classes(self):
        # 初始化班级下拉框
        self.class_combo = ComboBox()
        self.class_combo.setFixedSize(130, 24)
        self.class_combo.setFont(QFont(load_custom_font(), 10))
        self.class_combo.currentIndexChanged.connect(self.update_total_count)
        # 加载班级列表
        try:
            list_folder = path_manager.get_resource_path("list")
            if path_manager.file_exists(list_folder) and os.path.isdir(list_folder):
                files = os.listdir(list_folder)
                classes = []
                for file in files:
                    if file.endswith('.json'):
                        class_name = os.path.splitext(file)[0]
                        classes.append(class_name)
                
                self.class_combo.clear()
                if classes:
                    self.class_combo.addItems(classes)
                else:
                    logger.error("你暂未添加班级")
                    self.class_combo.addItem("你暂未添加班级")
            else:
                logger.error("你暂未添加班级")
                self.class_combo.addItem("你暂未添加班级")
        except Exception as e:
            logger.error(f"加载班级列表失败: {str(e)}")
            self.class_combo.addItem("加载班级列表失败")

    def _load_groups(self):
        # 小组下拉框
        self.group_combo = ComboBox()
        self.group_combo.setFixedSize(130, 24)
        self.group_combo.setFont(QFont(load_custom_font(), 10))
        self.group_combo.addItem('抽取全班学生')
        self.group_combo.currentIndexChanged.connect(self.update_total_count)

        class_name = self.class_combo.currentText()
        
        # 检查是否选择了有效的班级
        if class_name == "你暂未添加班级" or class_name == "加载班级列表失败":
            self.group_combo.addItem("你暂未添加小组")
            return
            
        pumping_people_file = path_manager.get_resource_path("list", f"{class_name}.json")
        if class_name not in ["你暂未添加班级", "加载班级列表失败", "你暂未添加小组", "加载小组列表失败"]:
            pumping_people_file = path_manager.get_resource_path("list", f"{class_name}.json")
            try:
                if path_manager.file_exists(pumping_people_file):
                    with open_file(pumping_people_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        groups = set()
                        for student_name, student_info in data.items():
                            if isinstance(student_info, dict) and 'id' in student_info:
                                id = student_info.get('id', '')
                                name = student_name.replace('【', '').replace('】', '')
                                gender = student_info.get('gender', '')
                                group = student_info.get('group', '')
                                if group:  # 只添加非空小组
                                    groups.add(group)
                        cleaned_data = sorted(list(groups), key=lambda x: self.sort_key(str(x)))
                        self.group_combo.clear()
                        self.group_combo.addItem('抽取全班学生')
                        if groups:
                            self.group_combo.addItem('抽取小组组号')
                            self.group_combo.addItems(cleaned_data)
                        else:
                            logger.error("你暂未添加小组")
                            self.group_combo.addItem("你暂未添加小组")
                else:
                    logger.error("你暂未添加小组")
                    self.group_combo.addItem("你暂未添加小组")
            except Exception as e:
                logger.error(f"加载小组列表失败: {str(e)}")
                self.group_combo.addItem("加载小组列表失败")
        else:
            logger.error("请先选择有效的班级")
        
    def _load_genders(self):
        # 性别下拉框
        self.gender_combo = ComboBox()
        self.gender_combo.setFixedSize(130, 24)
        self.gender_combo.setFont(QFont(load_custom_font(), 10))
        self.gender_combo.addItem('抽取所有性别')
        self.gender_combo.currentIndexChanged.connect(self.update_total_count)

        class_name = self.class_combo.currentText()
        
        # 检查是否选择了有效的班级
        if class_name == "你暂未添加班级" or class_name == "加载班级列表失败":
            self.gender_combo.addItem("你暂未添加性别")
            return
            
        pumping_people_file = path_manager.get_resource_path("list", f"{class_name}.json")
        try:
            if path_manager.file_exists(pumping_people_file):
                with open_file(pumping_people_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    genders = set()
                    for student_name, student_info in data.items():
                        if isinstance(student_info, dict) and 'id' in student_info:
                            id = student_info.get('id', '')
                            name = student_name.replace('【', '').replace('】', '')
                            gender = student_info.get('gender', '')
                            group = student_info.get('group', '')
                            if gender:  # 只添加非空小组
                                genders.add(gender)
                    cleaned_data = sorted(list(genders), key=lambda x: self.sort_key(str(x)))
                    if genders:
                        self.gender_combo.addItems(cleaned_data)
                    else:
                        logger.error("你暂未添加性别")
                        self.gender_combo.addItem("你暂未添加性别")
            else:
                logger.error("你暂未添加性别")
                self.gender_combo.addItem("你暂未添加性别")
        except Exception as e:
            logger.error(f"加载性别列表失败: {str(e)}")
            self.gender_combo.addItem("加载性别列表失败")

    # 将小组名称转换为排序键
    def sort_key(self, group):
        # 尝试匹配 '第X小组' 或 '第X组' 格式
        match = re.match(r'第\s*(\d+|一|二|三|四|五|六|七|八|九|十)\s*(小组|组)', group)
        if match:
            num = match.group(1)
            num_map = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10}
            if num in num_map:
                return (1, num_map[num])  # 类型1: 中文数字组
            else:
                return (1, int(num))       # 类型1: 阿拉伯数字组
        
        # 尝试匹配仅数字格式
        try:
            return (2, int(group))         # 类型2: 纯数字组
        except ValueError:
            pass
        
        # 🌟 星穹铁道白露：自定义组名直接使用中文排序啦~
        return (3, group) # ✨ 小鸟游星野：类型3: 其他名称组，保持排序功能不变

    def update_total_count(self):
        """更新总人数"""
        # 只在下拉框不存在时才创建它们
        if not hasattr(self, 'class_combo') or self.class_combo is None:
            self._load_classes()
        if not hasattr(self, 'group_combo') or self.group_combo is None:
            self._load_groups()
        if not hasattr(self, 'gender_combo') or self.gender_combo is None:
            self._load_genders()
            
        class_name = self.class_combo.currentText()
        group_name = self.group_combo.currentText()
        gender_name = self.gender_combo.currentText()

        # 检查是否选择了有效的班级
        if class_name == "你暂未添加班级" or class_name == "加载班级列表失败":
            self.max_count = 0
            self._update_count_display()  # 更新按钮状态
            return
            
        student_file = path_manager.get_resource_path("list", f"{class_name}.json")

        # 检查文件是否存在
        if not path_manager.file_exists(student_file):
            self.max_count = 0
            self._update_count_display()  # 更新按钮状态
            return

        cleaned_data = self._get_cleaned_data(student_file, group_name, gender_name)

        self.max_count = len(cleaned_data)
        self._update_count_display()  # 更新按钮状态
    
    def _show_instant_draw_window(self):
        # 小鸟游星野：显示即抽窗口 - 使用_show_direct_extraction_window传递抽取人数、班级、小组和性别 ✧(๑•̀ㅂ•́)๑
        try:
            # 确保当前抽取人数已设置
            if not hasattr(self, 'current_count'):
                self.current_count = 1

            self.update_total_count()
            
            # 获取当前选择的班级、小组和性别
            class_name = self.class_combo.currentText()
            group_name = self.group_combo.currentText()
            gender_name = self.gender_combo.currentText()
            
            # 调用直接抽取窗口方法，传递抽取人数、班级、小组和性别
            self._show_direct_extraction_window(self.current_count, class_name, group_name, gender_name)
            
        except Exception as e:
            logger.error(f"执行抽取功能失败: {e}")
            error_dialog = Dialog("抽取失败", f"执行抽取功能时发生错误: {str(e)}", self)
            error_dialog.yesButton.setText("确定")
            error_dialog.cancelButton.hide()
            error_dialog.buttonLayout.insertStretch(1)
            error_dialog.exec()
    
    def _check_edge_proximity(self):
        """检测窗口是否靠近屏幕边缘，并实现贴边隐藏功能（带动画效果）"""
        # 如果设置窗口存在，先关闭它
        if hasattr(self, 'settings_window') and self.settings_window:
            self._close_settings_window()
            
        # 如果有正在进行的动画，先停止它
        if hasattr(self, 'animation') and self.animation.state() == QPropertyAnimation.Running:
            self.animation.stop()
        
        # 获取屏幕尺寸
        screen = QApplication.desktop().screenGeometry()
        
        # 获取窗口当前位置和尺寸
        window_pos = self.pos()
        window_width = self.width()
        window_height = self.height()
        
        # 定义边缘阈值（像素）
        edge_threshold = 5
        hidden_width = 10  # 隐藏后露出的宽度
        
        # 检测左边缘
        if window_pos.x() <= edge_threshold:
            # 创建动画效果
            self.animation = QPropertyAnimation(self, b"geometry")
            # 设置动画持续时间
            self.animation.setDuration(300)
            # 设置缓动曲线
            self.animation.setEasingCurve(QEasingCurve.Type.OutQuad)
            
            # 设置动画起始值（当前位置）
            self.animation.setStartValue(self.geometry())
            
            # 设置动画结束值（隐藏位置）
            end_rect = QRect(-window_width + hidden_width, window_pos.y(), window_width, window_height)
            self.animation.setEndValue(end_rect)
            
            # 启动动画
            self.animation.start()
            
            # 动画结束后创建箭头按钮
            self.animation.finished.connect(lambda: self._create_arrow_button('right', 0, window_pos.y() + window_height // 2 - 15))
            return
            
        # 检测右边缘
        elif window_pos.x() + window_width >= screen.width() - edge_threshold:
            # 创建动画效果
            self.animation = QPropertyAnimation(self, b"geometry")
            # 设置动画持续时间
            self.animation.setDuration(300)
            # 设置缓动曲线
            self.animation.setEasingCurve(QEasingCurve.Type.OutQuad)
            
            # 设置动画起始值（当前位置）
            self.animation.setStartValue(self.geometry())
            
            # 设置动画结束值（隐藏位置）
            end_rect = QRect(screen.width() - hidden_width, window_pos.y(), window_width, window_height)
            self.animation.setEndValue(end_rect)
            
            # 启动动画
            self.animation.start()
            
            # 动画结束后创建箭头按钮
            self.animation.finished.connect(lambda: self._create_arrow_button('left', screen.width() - 30, window_pos.y() + window_height // 2 - 15))
            return
        
        # 保存新位置
        self.save_position()
        
    def _create_arrow_button(self, direction, x, y):
        """创建箭头按钮用于显示隐藏的窗口"""
        # 如果已存在箭头按钮，先删除
        if hasattr(self, 'arrow_button') and self.arrow_button:
            self.arrow_button.deleteLater()
            
        # 创建透明的可拖动QWidget作为容器
        self.arrow_widget = DraggableWidget()
        self.arrow_widget.setFixedSize(30, 30)
        self.arrow_widget.move(x, y)
        self.arrow_widget.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.NoFocus | Qt.Popup)
        self.arrow_widget.setFixedX(x)  # 设置固定的x坐标
        
        # 设置容器透明
        self.arrow_widget.setAttribute(Qt.WA_TranslucentBackground)
        
        # 创建布局
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 创建箭头按钮
        self.arrow_button = PushButton()
        self.arrow_button.setFixedSize(30, 30)
        self.arrow_button.setFont(QFont(load_custom_font(), 12))
        
        try:
            opacity = self.transparency_mode
            # 根据主题设置不同的背景颜色
            if dark_mode:
                # 深色模式背景颜色
                bg_color = f'rgba(65, 66, 66, {opacity})'
                color = '#ffffff'
            else:
                # 浅色模式背景颜色
                bg_color = f'rgba(240, 240, 240, {opacity})'
                color = '#000000'
            self.arrow_button.setStyleSheet(f'border: none; border-radius: 5px; background-color: {bg_color}; text-align: center; color: {color};')
        except Exception as e:
            self.arrow_button.setStyleSheet('border: none; border-radius: 5px; background-color: rgba(65, 66, 66, 0.8); text-align: center;')
            logger.error(f"应用窗口样式失败: {e}")
        
        # 根据自定义显示方式设置按钮内容
        display_mode = getattr(self, 'custom_display_mode', 0)
        
        if display_mode == 0:  # 箭头模式
            # 调整按钮尺寸以保持一致性
            self.arrow_button.setFixedSize(30, 30)
            # 设置箭头图标
            if direction == 'right':
                self.arrow_button.setText(">")
            else:  # left
                self.arrow_button.setText("<")
        elif display_mode == 1:  # 文字模式
            # 调整按钮尺寸以适应文字显示
            self.arrow_button.setFixedSize(30, 30)
            self.arrow_button.setText("抽")
        elif display_mode == 2:  # 图标模式
            self.arrow_button.setFixedSize(30, 30)
            try:
                # 根据主题设置不同的颜色
                if dark_mode:
                    # 深色模式
                    icon_path = path_manager.get_resource_path("icon", f"SecRandom_floating_light.png")
                else:
                    # 浅色模式
                    icon_path = path_manager.get_resource_path("icon", f"SecRandom_floating_black.png")
                pixmap = QPixmap(str(icon_path))
                self.arrow_button.setIcon(QIcon(pixmap.scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation)))
                self.arrow_button.setIconSize(QSize(20, 20))
            except FileNotFoundError as e:
                pixmap = QPixmap(str(icon_path))
                self.arrow_button.setIcon(QIcon(pixmap.scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation)))
                self.arrow_button.setIconSize(QSize(20, 20))
                logger.error(f"加载人物图标失败: {e}")
            
        # 设置按钮点击事件
        self.arrow_button.clicked.connect(lambda: self._show_hidden_window(direction))
        
        # 为箭头按钮容器添加点击事件处理，确保在拖动操作不会干扰点击事件
        def handle_click():
            # 检查是否发生了拖动操作
            if hasattr(self.arrow_widget, '_was_dragging') and self.arrow_widget._was_dragging:
                return  # 如果发生了拖动，不执行点击操作
            if not self.arrow_widget._dragging:
                self._show_hidden_window(direction)
        
        # 修改容器的mouseReleaseEvent，处理点击事件
        original_release = self.arrow_widget.mouseReleaseEvent
        def new_mouse_release(event):
            original_release(event)
            # 检查是否发生了拖动操作
            was_dragging = hasattr(self.arrow_widget, '_was_dragging') and self.arrow_widget._was_dragging
            if event.button() == Qt.LeftButton and not self.arrow_widget._dragging and not was_dragging:
                handle_click()
        
        self.arrow_widget.mouseReleaseEvent = new_mouse_release
        
        # 设置按钮自定义透明度
        opacity_effect = QGraphicsOpacityEffect()
        opacity_value = self.transparency_mode
        opacity_effect.setOpacity(opacity_value)
        self.arrow_button.setGraphicsEffect(opacity_effect)
        
        # 将按钮添加到布局中
        layout.addWidget(self.arrow_button, alignment=Qt.AlignCenter)
        
        # 设置容器的布局
        self.arrow_widget.setLayout(layout)
        
        # 确保容器显示在最前面
        self.arrow_widget.raise_()
        self.arrow_widget.show()
        
        # 强制容器获取焦点
        self.arrow_widget.setFocus()
        
    def _show_hidden_window(self, direction):
        """显示隐藏的窗口（带动画效果）"""
        # 如果有正在进行的动画，先停止它
        if hasattr(self, 'animation') and self.animation.state() == QPropertyAnimation.Running:
            self.animation.stop()
        
        # 获取屏幕尺寸
        screen = QApplication.desktop().screenGeometry()
        
        # 获取窗口当前位置和尺寸
        window_width = self.width()
        window_height = self.height()
        
        # 获取箭头按钮容器的当前位置
        if hasattr(self, 'arrow_widget') and self.arrow_widget:
            arrow_x = self.arrow_widget.x()
            arrow_y = self.arrow_widget.y()
            arrow_height = self.arrow_widget.height()
        else:
            # 如果箭头按钮容器不存在，使用窗口的原始位置
            arrow_x = self.x()
            arrow_y = self.y()
            arrow_height = 30  # 默认箭头按钮高度
        
        # 计算窗口应该显示的位置，使窗口中心与箭头按钮中心对齐
        window_y = arrow_y + (arrow_height // 2) - (window_height // 2)
        
        # 确保窗口不会超出屏幕顶部和底部
        if window_y < 0:
            window_y = 0
        elif window_y + window_height > screen.height():
            window_y = screen.height() - window_height
        
        # 创建动画效果
        self.animation = QPropertyAnimation(self, b"geometry")
        # 设置动画持续时间
        self.animation.setDuration(300)
        # 设置缓动曲线
        self.animation.setEasingCurve(QEasingCurve.Type.OutQuad)
        
        # 设置动画起始值（当前位置）
        self.animation.setStartValue(self.geometry())
        
        # 设置动画结束值（显示位置）
        if direction == 'right':
            # 从左侧显示窗口
            end_rect = QRect(0, window_y, window_width, window_height)
        else:  # left
            # 从右侧显示窗口
            end_rect = QRect(screen.width() - window_width, window_y, window_width, window_height)
        
        self.animation.setEndValue(end_rect)
        
        # 启动动画
        self.animation.start()

        self._delete_arrow_button()
            
        # 保存新位置
        self.save_position()
        
        # 激活主窗口，确保窗口显示在最前面
        self.raise_()
        self.activateWindow()
        
        # 根据自定义收回秒数设置延迟后自动隐藏窗口
        retract_time = getattr(self, 'custom_retract_time', 5) * 1000  # 转换为毫秒
        QTimer.singleShot(retract_time, self._auto_hide_window)
    
    def _delete_arrow_button(self):
        """实际删除箭头按钮的辅助方法"""
        # 删除箭头按钮容器
        if hasattr(self, 'arrow_widget') and self.arrow_widget:
            self.arrow_widget.deleteLater()
            self.arrow_widget = None
            
        # 删除箭头按钮
        if hasattr(self, 'arrow_button') and self.arrow_button:
            self.arrow_button.deleteLater()
            self.arrow_button = None
        
    def _auto_hide_window(self):
        """自动隐藏窗口"""
        # 如果设置窗口存在，先关闭它
        if hasattr(self, 'settings_window') and self.settings_window:
            self._close_settings_window()
            
        # 检查是否启用了边缘贴边隐藏功能
        if hasattr(self, 'flash_window_side_switch') and self.flash_window_side_switch:
            # 调用边缘检测方法隐藏窗口
            self._check_edge_proximity()
    
    def _show_settings_window(self):
        """显示简洁美观的设置小浮窗，支持上下左右智能定位"""
        try:
            # 如果设置窗口已经存在，先关闭它
            if hasattr(self, 'settings_window') and self.settings_window:
                self._close_settings_window()
                return  # 直接返回，不再创建新窗口
            
            # 创建设置窗口
            self.settings_window = QWidget()
            self.settings_window.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.NoFocus | Qt.Popup)
            self.settings_window.setAttribute(Qt.WA_TranslucentBackground)
            
            # 设置简洁小巧的窗口大小
            self.settings_window.setFixedSize(160, 90)
            
            # 智能位置计算 - 支持上下左右四个方向
            main_window_pos = self.pos()
            main_window_size = self.size()
            
            # 获取屏幕尺寸
            screen_geometry = QApplication.desktop().screenGeometry()
            screen_width = screen_geometry.width()
            screen_height = screen_geometry.height()
            
            # 计算四个方向的位置选项
            positions = {
                'right': {  # 右侧
                    'x': main_window_pos.x() + main_window_size.width() + 8,
                    'y': main_window_pos.y() + (main_window_size.height() - 90) // 2
                },
                'left': {  # 左侧
                    'x': main_window_pos.x() - 160 - 8,
                    'y': main_window_pos.y() + (main_window_size.height() - 90) // 2
                },
                'top': {  # 上方
                    'x': main_window_pos.x() + (main_window_size.width() - 160) // 2,
                    'y': main_window_pos.y() - 90 - 8
                },
                'bottom': {  # 下方
                    'x': main_window_pos.x() + (main_window_size.width() - 160) // 2,
                    'y': main_window_pos.y() + main_window_size.height() + 8
                }
            }
            
            # 按优先级选择最佳位置（下→上→左→右）
            best_position = None
            for direction in ['bottom', 'top', 'left', 'right']:
                pos = positions[direction]
                # 检查是否超出屏幕边界
                if (pos['x'] >= 0 and pos['y'] >= 0 and 
                    pos['x'] + 160 <= screen_width and 
                    pos['y'] + 90 <= screen_height):
                    best_position = pos
                    break
            
            # 如果所有预设位置都不可用，使用备用位置
            if best_position is None:
                # 优先尝试下方，如果不行就上方
                if positions['bottom']['y'] + 90 <= screen_height:
                    best_position = positions['bottom']
                elif positions['top']['y'] >= 0:
                    best_position = positions['top']
                else:
                    best_position = {
                        'x': max(5, screen_width - 160 - 5),
                        'y': max(5, min(positions['bottom']['y'], screen_height - 90 - 5))
                    }
            
            self.settings_window.move(best_position['x'], best_position['y'])
            
            # 设置美观的渐变背景样式
            if dark_mode:
                bg_gradient_start = 'rgba(60, 60, 60, 0.98)'
                bg_gradient_end = 'rgba(40, 40, 40, 0.95)'
                border_color = '#555555'
                text_color = '#ffffff'
            else:
                bg_gradient_start = 'rgba(255, 255, 255, 0.99)'
                bg_gradient_end = 'rgba(245, 245, 245, 0.98)'
                border_color = '#d0d0d0'
                text_color = '#2c2c2c'
            
            self.settings_window.setStyleSheet(f'''
                QWidget {{
                    color: {text_color};
                }}
            ''')
            
            # 创建背景标签，用于显示背景样式
            background_label = BodyLabel(self.settings_window)
            background_label.setObjectName("backgroundLabel")
            background_label.setStyleSheet(f'''
                BodyLabel#backgroundLabel {{
                    border: 1px solid {border_color};
                    border-radius: 12px;
                    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                               stop: 0 {bg_gradient_start}, stop: 0.5 {bg_gradient_start}, stop: 1 {bg_gradient_end});
                }}
            ''')
            
            # 创建紧凑主布局
            main_layout = QVBoxLayout(background_label)
            main_layout.setContentsMargins(8, 6, 8, 6)
            main_layout.setSpacing(4)
            
            # 创建窗口主布局，用于放置背景标签
            window_layout = QVBoxLayout(self.settings_window)
            window_layout.setContentsMargins(0, 0, 0, 0)
            window_layout.addWidget(background_label)
            
            # 创建设置项布局（紧凑设计）
            # 名单设置
            class_layout = QHBoxLayout()
            class_layout.setSpacing(6)
            
            # 小组设置
            group_layout = QHBoxLayout()
            group_layout.setSpacing(6)
            
            # 性别设置
            gender_layout = QHBoxLayout()
            gender_layout.setSpacing(6)
            
            # 添加设置项到主布局
            main_layout.addLayout(class_layout)
            main_layout.addLayout(group_layout)
            main_layout.addLayout(gender_layout)
            
            # 添加小箭头指示器（可选，根据位置方向显示）
            self._add_direction_indicator(best_position, main_window_pos, main_window_size) if hasattr(self, '_add_direction_indicator') else None
            
            # 初始化下拉框数据
            self._load_classes()
            self._load_groups()
            self._load_genders()
            
            # 恢复之前保存的选择
            if hasattr(self, 'saved_class') and self.saved_class:
                index = self.class_combo.findText(self.saved_class)
                if index >= 0:
                    self.class_combo.setCurrentIndex(index)
            
            if hasattr(self, 'saved_group') and self.saved_group:
                index = self.group_combo.findText(self.saved_group)
                if index >= 0:
                    self.group_combo.setCurrentIndex(index)
            
            if hasattr(self, 'saved_gender') and self.saved_gender:
                index = self.gender_combo.findText(self.saved_gender)
                if index >= 0:
                    self.gender_combo.setCurrentIndex(index)
            
            # 将下拉框添加到布局中
            class_layout.addWidget(self.class_combo)
            group_layout.addWidget(self.group_combo)
            gender_layout.addWidget(self.gender_combo)
            
            # 连接下拉框信号
            if hasattr(self, 'class_combo') and self.class_combo:
                self.class_combo.currentIndexChanged.connect(self.update_total_count)
            if hasattr(self, 'group_combo') and self.group_combo:
                self.group_combo.currentIndexChanged.connect(self.update_total_count)
            if hasattr(self, 'gender_combo') and self.gender_combo:
                self.gender_combo.currentIndexChanged.connect(self.update_total_count)
            
            # 显示窗口
            self.settings_window.show()
            
            # 为设置窗口添加点击外部关闭功能
            self.settings_window.installEventFilter(self)
            
            # 安装全局事件过滤器，以便捕获应用程序全局的鼠标点击事件
            QApplication.instance().installEventFilter(self)
            
            # 添加10秒无操作自动关闭功能
            self.settings_close_timer = QTimer(self)
            self.settings_close_timer.setSingleShot(True)
            self.settings_close_timer.timeout.connect(self._close_settings_window)
            self.settings_close_timer.start(10000)  # 10秒后自动关闭
            
        except Exception as e:
            logger.error(f"创建设置窗口失败: {e}")
    
    def _close_settings_window(self):
        """关闭设置窗口"""
        if hasattr(self, 'settings_window') and self.settings_window:
            # 保存当前选择
            if hasattr(self, 'class_combo') and self.class_combo:
                self.saved_class = self.class_combo.currentText()
            if hasattr(self, 'group_combo') and self.group_combo:
                self.saved_group = self.group_combo.currentText()
            if hasattr(self, 'gender_combo') and self.gender_combo:
                self.saved_gender = self.gender_combo.currentText()
            
            # 移除全局事件过滤器
            QApplication.instance().removeEventFilter(self)
            
            # 断开所有信号连接
            if hasattr(self, 'class_combo') and self.class_combo:
                try:
                    self.class_combo.currentIndexChanged.disconnect(self.update_total_count)
                except:
                    pass  # 忽略断开连接时的错误
            
            if hasattr(self, 'group_combo') and self.group_combo:
                try:
                    self.group_combo.currentIndexChanged.disconnect(self.update_total_count)
                except:
                    pass  # 忽略断开连接时的错误
            
            if hasattr(self, 'gender_combo') and self.gender_combo:
                try:
                    self.gender_combo.currentIndexChanged.disconnect(self.update_total_count)
                except:
                    pass  # 忽略断开连接时的错误
            
            # 关闭窗口
            self.settings_window.close()
            self.settings_window = None
            
        if hasattr(self, 'settings_close_timer') and self.settings_close_timer:
            self.settings_close_timer.stop()
    
    def _add_direction_indicator(self, settings_pos, main_pos, main_size):
        """添加方向指示器，显示设置窗口相对于主窗口的方向"""
        try:
            # 计算相对位置
            settings_x = settings_pos['x']
            settings_y = settings_pos['y']
            
            # 确定方向
            if settings_x > main_pos.x() + main_size.width():
                direction = 'right'  # 右侧
            elif settings_x + 160 < main_pos.x():
                direction = 'left'   # 左侧
            elif settings_y > main_pos.y() + main_size.height():
                direction = 'bottom' # 下方
            else:
                direction = 'top'    # 上方
            
            # 创建指示器标签
            indicator = QLabel(self.settings_window)
            
            # 设置指示器样式 - 使用三角形箭头设计
            if dark_mode:
                indicator_color = '#4a9eff'  # 亮蓝色
            else:
                indicator_color = '#2196f3'  # 蓝色
            
            # 根据方向定位指示器并设置箭头形状
            if direction == 'right':
                indicator.setFixedSize(16, 16)  # 左箭头
                indicator.move(-8, 37)  # 向左偏移
                # 使用CSS创建左箭头
                indicator.setStyleSheet(f'''
                    QLabel {{
                        background-color: {indicator_color};
                        border: none;
                        border-radius: 2px;
                    }}
                ''')
            elif direction == 'left':
                indicator.setFixedSize(16, 16)  # 右箭头
                indicator.move(152, 37)  # 向右偏移
                # 使用CSS创建右箭头
                indicator.setStyleSheet(f'''
                    QLabel {{
                        background-color: {indicator_color};
                        border: none;
                        border-radius: 2px;
                    }}
                ''')
            elif direction == 'bottom':
                indicator.setFixedSize(16, 16)  # 上箭头
                indicator.move(72, -8)  # 向上偏移
                # 使用CSS创建上箭头
                indicator.setStyleSheet(f'''
                    QLabel {{
                        background-color: {indicator_color};
                        border: none;
                        border-radius: 2px;
                    }}
                ''')
            else:  # top
                indicator.setFixedSize(16, 16)  # 下箭头
                indicator.move(72, 88)  # 向下偏移
                # 使用CSS创建下箭头
                indicator.setStyleSheet(f'''
                    QLabel {{
                        background-color: {indicator_color};
                        border: none;
                        border-radius: 2px;
                    }}
                ''')
                
            indicator.show()
            
        except Exception as e:
            logger.info(f"添加方向指示器失败: {e}")


    def eventFilter(self, obj, event):
        """事件过滤器，用于点击设置窗口外部时关闭窗口"""
        # 处理设置窗口的点击事件
        if obj == self.settings_window:
            # 如果是鼠标按下事件
            if event.type() == QEvent.MouseButtonPress:
                # 如果是窗口内部点击，重置计时器
                if hasattr(self, 'settings_close_timer') and self.settings_close_timer:
                    self.settings_close_timer.stop()
                    self.settings_close_timer.start(10000)  # 重置为10秒
            # 如果是键盘事件，也重置计时器
            elif event.type() == QEvent.KeyPress and hasattr(self, 'settings_close_timer') and self.settings_close_timer:
                self.settings_close_timer.stop()
                self.settings_close_timer.start(10000)  # 重置为10秒
        return False
        
class DraggableWidget(QWidget):
    """可垂直拖动的窗口部件"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self._dragging = False
        self._drag_start_y = 0
        self._original_y = 0
        self._fixed_x = 0  # 固定的x坐标
        self._press_start_time = 0  # 记录按下时间
        self._long_press_duration = 100  # 长按时间阈值（毫秒）
        self._long_press_timer = QTimer(self)  # 长按检测计时器
        self._long_press_timer.setSingleShot(True)
        self._long_press_timer.timeout.connect(self._on_long_press)
        self._long_press_triggered = False  # 标记是否触发长按
        
    def setFixedX(self, x):
        """设置固定的x坐标"""
        self._fixed_x = x
        
    def _on_long_press(self):
        """长按触发事件"""
        self._long_press_triggered = True
        self.setCursor(Qt.ClosedHandCursor)
        
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.LeftButton:
            self._press_start_time = QDateTime.currentMSecsSinceEpoch()
            self._drag_start_y = event.globalY()
            self._original_y = self.y()
            self._long_press_triggered = False
            # 重置拖动标志
            self._was_dragging = False
            # 启动长按检测计时器
            self._long_press_timer.start(self._long_press_duration)
        
    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        if event.buttons() & Qt.LeftButton:  # 确保左键按下
            current_time = QDateTime.currentMSecsSinceEpoch()
            # 检查是否已经长按或者移动距离足够大
            if self._long_press_triggered or (current_time - self._press_start_time > 100 and 
                                            abs(event.globalY() - self._drag_start_y) > 5):
                if not self._dragging:
                    self._dragging = True
                    # 设置拖动标志，表示发生了拖动操作
                    self._was_dragging = True
                    self.setCursor(Qt.ClosedHandCursor)
                    # 如果还没触发长按，停止计时器
                    if not self._long_press_triggered:
                        self._long_press_timer.stop()
                
                # 计算新的y坐标
                new_y = self._original_y + (event.globalY() - self._drag_start_y)
                # 保持x坐标不变
                self.move(self._fixed_x, new_y)
                
                # 同时更新主窗口的位置
                if hasattr(self, 'parent') and self.parent() and hasattr(self.parent(), 'move'):
                    # 获取主窗口的当前位置
                    parent_x = self.parent().x()
                    parent_y = self.parent().y()
                    # 更新主窗口的y坐标，保持x坐标不变
                    self.parent().move(parent_x, new_y)
        
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if event.button() == Qt.LeftButton:
            # 先保存拖动状态，然后再重置
            was_dragging = self._dragging
            self._dragging = False
            self._long_press_timer.stop()  # 停止长按计时器
            self.setCursor(Qt.ArrowCursor)
            
            # 如果没有触发长按且移动距离很小，则视为点击
            if not self._long_press_triggered and abs(event.globalY() - self._drag_start_y) < 5 and not was_dragging:
                pass
    
    def enterEvent(self, event):
        """鼠标进入窗口区域时的事件处理，不再自动展开贴边隐藏的窗口"""
        # 调用父类的enterEvent
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """鼠标离开窗口区域时的事件处理，不再自动贴边隐藏窗口"""
        # 调用父类的leaveEvent
        super().leaveEvent(event)
