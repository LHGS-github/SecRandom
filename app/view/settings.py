from qfluentwidgets import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import QGraphicsBlurEffect, QGraphicsScene, QGraphicsPixmapItem
import os
import json
from loguru import logger

from app.common.config import get_theme_icon, load_custom_font
from app.common.path_utils import path_manager
from app.common.path_utils import open_file, ensure_dir
import random

# 导入子页面
from app.view.settings_page.more_setting import more_setting
from app.view.settings_page.password_setting import password_set
from app.view.settings_page.about_setting import about
from app.view.settings_page.custom_setting import custom_setting
from app.view.settings_page.pumping_handoff_setting import pumping_handoff_setting

class settings_Window(MSFluentWindow):
    # 定义个性化设置变化信号
    personal_settings_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__()
        self.app_dir = path_manager._app_root
        self.resize_timer = QTimer(self)
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(self.save_settings_window_size)

        settings_path = path_manager.get_settings_path()
        try:
            with open_file(settings_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                foundation_settings = settings.get('foundation', {})
                # 读取保存的窗口大小，默认为800x600
                window_width = foundation_settings.get('settings_window_width', 800)
                window_height = foundation_settings.get('settings_window_height', 600)
                self.resize(window_width, window_height)
        except FileNotFoundError as e:
            logger.error(f"加载设置时出错: {e}, 使用默认大小:800x600")
            self.resize(800, 600)
        except Exception as e:
            logger.error(f"加载窗口大小设置失败: {e}, 使用默认大小:800x600")
            self.resize(800, 600)

        self.setMinimumSize(600, 400)
        self.setWindowTitle('SecRandom - 设置')
        self.setWindowIcon(QIcon(str(path_manager.get_resource_path('icon', 'secrandom-icon.png'))))

        # 获取主屏幕
        screen = QApplication.primaryScreen()
        # 获取屏幕的可用几何信息
        desktop = screen.availableGeometry()
        w, h = desktop.width(), desktop.height()
        try:
            with open_file(settings_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                foundation_settings = settings.get('foundation', {})
                settings_window_mode = foundation_settings.get('settings_window_mode', 0)
                if settings_window_mode == 0:
                    self.move(w // 2 - self.width() // 2, h // 2 - self.height() // 2)
                elif settings_window_mode == 1:
                    self.move(w // 2 - self.width() // 2, h * 3 // 5 - self.height() // 2)
        except FileNotFoundError as e:
            logger.error(f"加载设置时出错: {e}, 使用默认窗口居中显示设置界面")
            self.move(w // 2 - self.width() // 2, h // 2 - self.height() // 2)

        self.createSubInterface()

    def createSubInterface(self):
        try:
            self.more_settingInterface = more_setting(self)
            self.more_settingInterface.setObjectName("more_settingInterface")
            logger.info("更多设置界面创建成功")
        except Exception as e:
            logger.error(f"创建更多设置界面失败: {e}")
            self.more_settingInterface = None

        try:
            self.custom_settingInterface = custom_setting(self)
            self.custom_settingInterface.setObjectName("custom_settingInterface")
            logger.info("自定义设置界面创建成功")
        except Exception as e:
            logger.error(f"创建自定义设置界面失败: {e}")
            self.custom_settingInterface = None

        try:
            self.pumping_handoff_settingInterface = pumping_handoff_setting(self)
            self.pumping_handoff_settingInterface.setObjectName("pumping_handoff_settingInterface")
            logger.info("抽取设置界面创建成功")
        except Exception as e:
            logger.error(f"创建抽取设置界面失败: {e}")
            self.pumping_handoff_settingInterface = None

        try:
            self.about_settingInterface = about(self)
            self.about_settingInterface.setObjectName("about_settingInterface")
            logger.info("关于界面创建成功")
        except Exception as e:
            logger.error(f"创建关于界面失败: {e}")
            self.about_settingInterface = None

        # 根据设置决定是否创建"安全设置"界面
        try:
            settings_path = path_manager.get_settings_path('custom_settings.json')
            with open_file(settings_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                sidebar_settings = settings.get('sidebar', {})
                security_settings_switch = sidebar_settings.get('show_security_settings_switch', 1)
                
                if security_settings_switch != 2:  # 不为"不显示"时才创建界面
                    self.password_setInterface = password_set(self)
                    self.password_setInterface.setObjectName("password_setInterface")
                    logger.info("安全设置界面创建成功")
                else:
                    logger.info("安全设置界面已设置为不创建")
                    self.password_setInterface = None
        except Exception as e:
            logger.error(f"读取安全设置界面设置失败: {e}, 默认创建界面")
            self.password_setInterface = password_set(self)
            self.password_setInterface.setObjectName("password_setInterface")
            logger.info("安全设置界面创建成功")

        self.initNavigation()

    def initNavigation(self):
        # 使用 MSFluentWindow 的 addSubInterface 方法
        if self.pumping_handoff_settingInterface is not None:
            self.addSubInterface(self.pumping_handoff_settingInterface, get_theme_icon("ic_fluent_people_community_20_filled"), '抽取设置', position=NavigationItemPosition.TOP)
        else:
            logger.error("抽取设置界面不存在，无法添加到导航栏")

        if self.custom_settingInterface is not None:
            self.addSubInterface(self.custom_settingInterface, get_theme_icon("ic_fluent_person_20_filled"), '个性设置', position=NavigationItemPosition.TOP)
        else:
            logger.error("自定义设置界面不存在，无法添加到导航栏")

        # 添加安全设置导航项
        try:
            settings_path = path_manager.get_settings_path('custom_settings.json')
            with open_file(settings_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                sidebar_settings = settings.get('sidebar', {})
                security_settings_switch = sidebar_settings.get('show_security_settings_switch', 1)
                
                if security_settings_switch == 1:
                    if self.password_setInterface is not None:
                        self.addSubInterface(self.password_setInterface, get_theme_icon("ic_fluent_shield_keyhole_20_filled"), '安全设置', position=NavigationItemPosition.BOTTOM)
                        # logger.info("安全设置导航项已放置在底部导航栏")
                    else:
                        logger.error("安全设置界面未创建，无法添加到导航栏")
                elif security_settings_switch == 2:
                    logger.info("安全设置导航项已设置为不显示")
                else:
                    if self.password_setInterface is not None:
                        self.addSubInterface(self.password_setInterface, get_theme_icon("ic_fluent_shield_keyhole_20_filled"), '安全设置', position=NavigationItemPosition.TOP)
                        # logger.info("安全设置导航项已放置在顶部导航栏")
                    else:
                        logger.error("安全设置界面未创建，无法添加到导航栏")
        except Exception as e:
            logger.error(f"加载安全设置导航项失败: {e}")
            if self.password_setInterface is not None:
                self.addSubInterface(self.password_setInterface, get_theme_icon("ic_fluent_shield_keyhole_20_filled"), '安全设置', position=NavigationItemPosition.BOTTOM)

        if self.about_settingInterface is not None:
            self.addSubInterface(self.about_settingInterface, get_theme_icon("ic_fluent_info_20_filled"), '关于', position=NavigationItemPosition.BOTTOM)
        else:
            logger.error("关于界面不存在，无法添加到导航栏")

        if self.more_settingInterface is not None:
            self.addSubInterface(self.more_settingInterface, get_theme_icon("ic_fluent_more_horizontal_20_filled"), '更多设置', position=NavigationItemPosition.BOTTOM)
        else:
            logger.error("更多设置界面不存在，无法添加到导航栏")

    def closeEvent(self, event):
        """窗口关闭时隐藏主界面"""
        # 停止resize_timer以优化CPU占用
        if hasattr(self, 'resize_timer') and self.resize_timer.isActive():
            self.resize_timer.stop()
            logger.info("设置窗口resize_timer已停止")
        
        self.hide()
        event.ignore()
        self.save_settings_window_size()

    def resizeEvent(self, event):
        # 调整大小时重启计时器，仅在停止调整后保存
        self.resize_timer.start(500)  # 500毫秒延迟
        
        # 调用原始的resizeEvent，确保布局正确更新
        super().resizeEvent(event)
        
        # 强制更新布局
        self.updateGeometry()
        self.update()
        
        # 处理窗口最大化状态
        if self.isMaximized():
            # 确保所有子控件适应最大化窗口
            for child in self.findChildren(QWidget):
                child.updateGeometry()
            # 强制重新布局
            QApplication.processEvents()

    def save_settings_window_size(self):
        if not self.isMaximized():
            try:
                settings_path = path_manager.get_settings_path()
                # 读取现有设置
                try:
                    with open_file(settings_path, 'r', encoding='utf-8') as f:
                        settings = json.load(f)
                except FileNotFoundError:
                    settings = {}
                
                # 确保foundation键存在
                if 'foundation' not in settings:
                    settings['foundation'] = {}
                
                # 更新窗口大小设置
                settings['foundation']['settings_window_width'] = self.width()
                settings['foundation']['settings_window_height'] = self.height()
                
                # 保存设置
                ensure_dir(settings_path.parent)
                with open_file(settings_path, 'w', encoding='utf-8') as f:
                    json.dump(settings, f, ensure_ascii=False, indent=4)
            except Exception as e:
                logger.error(f"保存窗口大小设置失败: {e}")
    

    def _on_resize_event(self, event):
        """当窗口大小改变时，自动调整背景图片大小，确保背景始终填满整个窗口"""
        # 调用原始的resizeEvent，确保布局正确更新
        if hasattr(self, 'original_resizeEvent'):
            self.original_resizeEvent(event)
        else:
            super(settings_Window, self).resizeEvent(event)
        
        # 强制更新布局
        self.updateGeometry()
        self.update()
        
        # 处理窗口最大化状态
        if self.isMaximized():
            self._handle_maximized_state()
    
    def _handle_maximized_state(self):
        """当窗口最大化时，确保所有控件正确适应新的窗口大小"""
        # 确保所有子控件适应最大化窗口
        for child in self.findChildren(QWidget):
            child.updateGeometry()
        
        # 强制重新布局
        QApplication.processEvents()
        
        # 延迟再次更新布局，确保所有控件都已适应
        QTimer.singleShot(100, self._delayed_layout_update)
    
    def _delayed_layout_update(self):
        """在窗口最大化后延迟执行布局更新，确保所有控件都已正确适应"""
        # 再次强制更新布局
        self.updateGeometry()
        self.update()
        
        # 确保所有子控件再次更新
        for child in self.findChildren(QWidget):
            child.updateGeometry()
        
        # 最后一次强制重新布局
        QApplication.processEvents()
