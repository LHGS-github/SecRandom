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
from app.view.settings_page.Changeable_history_handoff_setting import changeable_history_handoff_setting
from app.view.settings_page.password_setting import password_set
from app.view.settings_page.about_setting import about
from app.view.settings_page.custom_setting import custom_setting
from app.view.settings_page.pumping_handoff_setting import pumping_handoff_setting
from app.view.settings_page.voice_engine_setting import voice_engine_settings


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

        # 应用背景图片
        self.apply_background_image()

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

        # 根据设置决定是否创建"历史记录设置"界面
        try:
            settings_path = path_manager.get_settings_path('custom_settings.json')
            with open_file(settings_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                sidebar_settings = settings.get('sidebar', {})
                history_settings_switch = sidebar_settings.get('show_history_settings_switch', 1)
                
                if history_settings_switch != 2:  # 不为"不显示"时才创建界面
                    self.changeable_history_handoff_settingInterface = changeable_history_handoff_setting(self)
                    self.changeable_history_handoff_settingInterface.setObjectName("changeable_history_handoff_settingInterface")
                    logger.info("历史记录设置界面创建成功")
                else:
                    logger.info("历史记录设置界面已设置为不创建")
                    self.changeable_history_handoff_settingInterface = None
        except Exception as e:
            logger.error(f"读取历史记录设置界面设置失败: {e}, 默认创建界面")
            self.changeable_history_handoff_settingInterface = changeable_history_handoff_setting(self)
            self.changeable_history_handoff_settingInterface.setObjectName("changeable_history_handoff_settingInterface")
            logger.info("历史记录设置界面创建成功")

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

        # 根据设置决定是否创建"语音设置"界面
        try:
            settings_path = path_manager.get_settings_path('custom_settings.json')
            with open_file(settings_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                sidebar_settings = settings.get('sidebar', {})
                voice_settings_switch = sidebar_settings.get('show_voice_settings_switch', 1)
                
                if voice_settings_switch != 2:  # 不为"不显示"时才创建界面
                    self.voice_engine_settingsInterface = voice_engine_settings(self)
                    self.voice_engine_settingsInterface.setObjectName("voice_engine_settingsInterface")
                    logger.info("语音设置界面创建成功")
                else:
                    logger.info("语音设置界面已设置为不创建")
                    self.voice_engine_settingsInterface = None
        except Exception as e:
            logger.error(f"读取语音设置界面设置失败: {e}, 默认创建界面")
            self.voice_engine_settingsInterface = voice_engine_settings(self)
            self.voice_engine_settingsInterface.setObjectName("voice_engine_settingsInterface")
            logger.info("语音设置界面创建成功")

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

        # 添加语音设置导航项
        try:
            settings_path = path_manager.get_settings_path('custom_settings.json')
            with open_file(settings_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                sidebar_settings = settings.get('sidebar', {})
                voice_settings_switch = sidebar_settings.get('show_voice_settings_switch', 1)
                
                if voice_settings_switch == 1:
                    if self.voice_engine_settingsInterface is not None:
                        self.addSubInterface(self.voice_engine_settingsInterface, get_theme_icon("ic_fluent_person_voice_20_filled"), '语音设置', position=NavigationItemPosition.BOTTOM)
                        # logger.info("语音设置导航项已放置在底部导航栏")
                    else:
                        logger.error("语音设置界面未创建，无法添加到导航栏")
                elif voice_settings_switch == 2:
                    logger.info("语音设置导航项已设置为不显示")
                else:
                    if self.voice_engine_settingsInterface is not None:
                        self.addSubInterface(self.voice_engine_settingsInterface, get_theme_icon("ic_fluent_person_voice_20_filled"), '语音设置', position=NavigationItemPosition.TOP)
                        # logger.info("语音设置导航项已放置在顶部导航栏")
                    else:
                        logger.error("语音设置界面未创建，无法添加到导航栏")
        except Exception as e:
            logger.error(f"加载语音设置导航项失败: {e}")
            if self.voice_engine_settingsInterface is not None:
                self.addSubInterface(self.voice_engine_settingsInterface, get_theme_icon("ic_fluent_person_voice_20_filled"), '语音设置', position=NavigationItemPosition.BOTTOM)

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

        # 添加历史记录设置导航项
        try:
            settings_path = path_manager.get_settings_path('custom_settings.json')
            with open_file(settings_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                sidebar_settings = settings.get('sidebar', {})
                history_settings_switch = sidebar_settings.get('show_history_settings_switch', 1)
                
                if history_settings_switch == 1:
                    if self.changeable_history_handoff_settingInterface is not None:
                        history_item = self.addSubInterface(self.changeable_history_handoff_settingInterface, get_theme_icon("ic_fluent_chat_history_20_filled"), '历史记录', position=NavigationItemPosition.BOTTOM)
                        history_item.clicked.connect(lambda: self.changeable_history_handoff_settingInterface.pumping_people_card.load_data())
                        # logger.info("历史记录设置导航项已放置在底部导航栏")
                    else:
                        logger.error("历史记录设置界面未创建，无法添加到导航栏")
                elif history_settings_switch == 2:
                    logger.info("历史记录设置导航项已设置为不显示")
                else:
                    if self.changeable_history_handoff_settingInterface is not None:
                        history_item = self.addSubInterface(self.changeable_history_handoff_settingInterface, get_theme_icon("ic_fluent_chat_history_20_filled"), '历史记录', position=NavigationItemPosition.TOP)
                        history_item.clicked.connect(lambda: self.changeable_history_handoff_settingInterface.pumping_people_card.load_data())
                        # logger.info("历史记录设置导航项已放置在顶部导航栏")
                    else:
                        logger.error("历史记录设置界面未创建，无法添加到导航栏")
        except Exception as e:
            logger.error(f"加载历史记录设置导航项失败: {e}")
            if self.changeable_history_handoff_settingInterface is not None:
                history_item = self.addSubInterface(self.changeable_history_handoff_settingInterface, get_theme_icon("ic_fluent_chat_history_20_filled"), '历史记录', position=NavigationItemPosition.BOTTOM)
                history_item.clicked.connect(lambda: self.changeable_history_handoff_settingInterface.pumping_people_card.load_data())

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
    
    def apply_background_image(self):
        """检查设置中的 enable_settings_background 和 enable_settings_background_color，
        如果开启则应用设置界面背景图片或背景颜色"""
        try:
            # 读取自定义设置
            custom_settings_path = path_manager.get_settings_path('custom_settings.json')
            with open_file(custom_settings_path, 'r', encoding='utf-8') as f:
                custom_settings = json.load(f)
                
            # 检查是否启用了设置界面背景图标
            personal_settings = custom_settings.get('personal', {})
            enable_settings_background = personal_settings.get('enable_settings_background', True)
            enable_settings_background_color = personal_settings.get('enable_settings_background_color', False)
            
            # 优先应用背景颜色（如果启用）
            if enable_settings_background_color:
                settings_background_color = personal_settings.get('settings_background_color', '#FFFFFF')
                
                # 创建背景颜色标签并设置样式（使用标签方式，与图片保持一致）
                self.background_label = QLabel(self)
                self.background_label.setGeometry(0, 0, self.width(), self.height())
                self.background_label.setStyleSheet(f"background-color: {settings_background_color};")
                self.background_label.lower()  # 将背景标签置于底层
                
                # 设置窗口属性，确保背景可见
                self.setAttribute(Qt.WA_TranslucentBackground)
                self.setStyleSheet("background: transparent;")
                
                # 保存原始的resizeEvent方法
                self.original_resizeEvent = self.resizeEvent
                
                # 重写resizeEvent方法，调整背景大小
                self.resizeEvent = self._on_resize_event
                
                logger.info(f"已成功应用设置界面背景颜色 {settings_background_color}")
                
            # 如果背景颜色未启用，但背景图片启用了，则应用背景图片
            elif enable_settings_background:
                # 获取设置界面背景图片设置
                settings_background_image = personal_settings.get('settings_background_image', '')
                
                # 检查是否选择了背景图片
                if settings_background_image and settings_background_image != "无背景图":
                    # 获取背景图片文件夹路径
                    background_dir = path_manager.get_resource_path('images', 'background')
                    
                    # 检查文件夹是否存在
                    if background_dir.exists():
                        # 构建图片完整路径
                        image_path = background_dir / settings_background_image
                        
                        # 检查图片文件是否存在
                        if image_path.exists():
                            # 创建背景图片对象
                            background_pixmap = QPixmap(str(image_path))
                            
                            # 如果图片加载成功，应用背景
                            if not background_pixmap.isNull():
                                # 获取模糊度和亮度设置
                                blur_value = personal_settings.get('background_blur', 10)
                                brightness_value = personal_settings.get('background_brightness', 30)
                                
                                # 应用模糊效果
                                if blur_value > 0:
                                    # 创建模糊效果
                                    blur_effect = QGraphicsBlurEffect()
                                    blur_effect.setBlurRadius(blur_value)
                                    
                                    # 创建临时场景和图形项来应用模糊效果
                                    scene = QGraphicsScene()
                                    item = QGraphicsPixmapItem(background_pixmap)
                                    item.setGraphicsEffect(blur_effect)
                                    scene.addItem(item)
                                    
                                    # 创建渲染图像
                                    result_image = QImage(background_pixmap.size(), QImage.Format_ARGB32)
                                    result_image.fill(Qt.transparent)
                                    painter = QPainter(result_image)
                                    scene.render(painter)
                                    painter.end()
                                    
                                    # 更新背景图片
                                    background_pixmap = QPixmap.fromImage(result_image)
                                
                                # 应用亮度效果
                                if brightness_value != 100:
                                    # 创建图像副本
                                    brightness_image = QImage(background_pixmap.size(), QImage.Format_ARGB32)
                                    brightness_image.fill(Qt.transparent)
                                    painter = QPainter(brightness_image)
                                    
                                    # 计算亮度调整因子
                                    brightness_factor = brightness_value / 100.0
                                    
                                    # 应用亮度调整
                                    painter.setOpacity(brightness_factor)
                                    painter.drawPixmap(0, 0, background_pixmap)
                                    painter.end()
                                    
                                    # 更新背景图片
                                    background_pixmap = QPixmap.fromImage(brightness_image)
                                
                                # 创建背景标签并设置样式
                                self.background_label = QLabel(self)
                                self.background_label.setGeometry(0, 0, self.width(), self.height())
                                self.background_label.setPixmap(background_pixmap.scaled(
                                    self.width(), self.height(), 
                                    Qt.IgnoreAspectRatio, 
                                    Qt.SmoothTransformation
                                ))
                                self.background_label.lower()  # 将背景标签置于底层
                                
                                # 保存原始图片，用于窗口大小调整时重新缩放
                                self.original_background_pixmap = background_pixmap
                                
                                # 确保背景标签随窗口大小变化
                                self.background_label.setAttribute(Qt.WA_StyledBackground, True)
                                
                                # 设置窗口属性，确保背景可见
                                self.setAttribute(Qt.WA_TranslucentBackground)
                                self.setStyleSheet("background: transparent;")
                                
                                # 保存原始的resizeEvent方法
                                self.original_resizeEvent = self.resizeEvent
                                
                                # 重写resizeEvent方法，调整背景大小
                                self.resizeEvent = self._on_resize_event
                                
                                logger.info(f"已成功应用设置界面背景图片 {settings_background_image}，模糊度: {blur_value}，亮度: {brightness_value}%")
                            else:
                                logger.error(f"设置界面背景图片 {settings_background_image} 加载失败")
                        else:
                            logger.error(f"设置界面背景图片 {settings_background_image} 不存在")
                    else:
                        logger.error("背景图片文件夹不存在")
                else:
                    logger.info("未选择设置界面背景图片")
            else:
                # 如果两者都未启用，则使用默认背景
                self.setStyleSheet("background: transparent;")
                
                # 清除可能存在的背景图片标签
                if hasattr(self, 'background_label') and self.background_label:
                    self.background_label.deleteLater()
                    delattr(self, 'background_label')
                
                # 恢复原始的resizeEvent方法
                if hasattr(self, 'original_resizeEvent'):
                    self.resizeEvent = self.original_resizeEvent
                    delattr(self, 'original_resizeEvent')
                
                # logger.debug("设置界面背景图片和颜色功能均未启用，使用默认背景")
                
        except FileNotFoundError:
            logger.error("自定义设置文件不存在，使用默认设置")
        except Exception as e:
            logger.error(f"应用设置界面背景图片或颜色时发生异常: {e}")
    
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
        
        # 如果存在背景标签，调整其大小
        if hasattr(self, 'background_label') and self.background_label:
            self.background_label.setGeometry(0, 0, self.width(), self.height())
            # 使用保存的原始图片进行缩放，避免重复缩放导致的像素化
            if hasattr(self, 'original_background_pixmap') and self.original_background_pixmap:
                self.background_label.setPixmap(self.original_background_pixmap.scaled(
                    self.width(), self.height(), 
                    Qt.IgnoreAspectRatio, 
                    Qt.SmoothTransformation
                ))
        
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
