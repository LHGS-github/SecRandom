import sys
import argparse
import json
import os
from loguru import logger
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from qfluentwidgets import *
from app.common.config import get_theme_icon, load_custom_font, check_for_updates, VERSION, is_dark_theme, themeColor
from app.common.path_utils import path_manager
from app.common.path_utils import open_file, ensure_dir

class URLHandler:
    """URL处理器类"""
    
    def __init__(self):
        self.url_command = None
        self.fixed_url_settings = {}
        self.config_file_path = path_manager.get_settings_path('custom_settings.json')
        self.last_modified_time = 0
        self.load_fixed_url_settings()
        self.parse_command_line()
    
    def load_fixed_url_settings(self):
        """加载fixed_url设置"""
        try:
            # 获取配置文件路径
            if not self.config_file_path:
                self.config_file_path = path_manager.get_settings_path('custom_settings.json')
            
            # 检查配置文件是否存在
            if not os.path.exists(self.config_file_path):
                logger.error(f"配置文件不存在: {self.config_file_path}")
                self._load_default_settings()
                return
            
            # 读取配置文件
            with open(self.config_file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.fixed_url_settings = config.get('fixed_url', {})
                
            # 记录文件修改时间
            self.last_modified_time = os.path.getmtime(self.config_file_path)
            
            logger.info("配置文件加载完成")
        except Exception as e:
            logger.error(f"加载fixed_url设置失败: {str(e)}")
            self._load_default_settings()
    
    def _load_default_settings(self):
        """加载默认设置"""
        self.fixed_url_settings = {}
    
    def is_url_enabled(self, url_type):
        """检查特定URL是否启用"""
        return self.fixed_url_settings.get( f"enable_{url_type}", True)
    
    def get_notification_setting(self, url_type):
        """获取特定URL的弹窗提醒设置"""
        return self.fixed_url_settings.get(f"{url_type}_notification", 0)
    
    def show_url_notification(self, url, url_type, callback=None):
        """显示URL弹窗提醒"""
        try:
            self.load_fixed_url_settings()

            notification_type = self.get_notification_setting(url_type)
            
            logger.info(f"显示URL弹窗提醒: url={url}, url_type={url_type}, notification_type={notification_type}")
            
            if notification_type == 0:  # 0=disabled
                # 如果弹窗提醒已禁用，直接执行回调
                logger.info("弹窗提醒已禁用，直接执行回调")
                if callback:
                    callback()
                return True
            
            # 创建弹窗
            logger.info("创建URL通知弹窗")
            notification = URLNotification(url, url_type, notification_type, callback)
            
            # 确保窗口显示在最前面
            logger.info("显示URL通知弹窗")
            notification.show()
            notification.raise_()
            notification.activateWindow()
            
            # 强制处理所有待处理的事件
            QApplication.processEvents()
            
            logger.info("URL通知弹窗显示成功")
            return True
        except Exception as e:
            logger.error(f"显示URL弹窗提醒失败: {str(e)}")
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            # 如果弹窗显示失败，直接执行回调
            if callback:
                callback()
            return False
    
    def force_reload_settings(self):
        """强制重新加载配置文件"""
        logger.info("强制重新加载配置文件")
        # 重置修改时间，强制重新加载
        self.last_modified_time = 0
        self.load_fixed_url_settings()
    
    def update_notification_setting(self, url_type, notification_type):
        """更新特定URL的通知设置
        Args:
            url_type: URL类型
            notification_type: 通知设置 (0=disabled, 1=notify_only, 2=confirm, 3=confirm_with_security)
        """
        try:
            # 确保设置已加载
            self.load_fixed_url_settings()
            
            # 更新设置
            setting_key = f"{url_type}_notification"
            # 确保notification_type是数字值
            if isinstance(notification_type, str):
                try:
                    notification_type = int(notification_type)
                except ValueError:
                    logger.error(f"无效的通知设置值: {notification_type}, 使用默认值0")
                    notification_type = 0
            self.fixed_url_settings[setting_key] = notification_type
            
            # 读取现有配置
            config = {}
            if os.path.exists(self.config_file_path):
                with open(self.config_file_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            
            # 确保fixed_url部分存在
            if 'fixed_url' not in config:
                config['fixed_url'] = {}
            
            # 更新配置
            config['fixed_url'][setting_key] = notification_type
            
            # 保存配置
            with open(self.config_file_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
            
            # 更新修改时间
            self.last_modified_time = os.path.getmtime(self.config_file_path)
            
            logger.info(f"已更新 {url_type} 的通知设置为: {notification_type}")
            return True
        except Exception as e:
            logger.error(f"更新通知设置失败: {str(e)}")
            return False
    
    def parse_command_line(self):
        """解析命令行参数"""
        try:
            parser = argparse.ArgumentParser(description='SecRandom URL处理器')
            parser.add_argument('--url', type=str, help='通过URL协议启动的URL')
            
            # 只解析已知的参数，忽略其他参数
            args, unknown = parser.parse_known_args()
            
            if args.url:
                self.url_command = args.url
                logger.info(f"接收到URL命令: {self.url_command}")
            
        except Exception as e:
            logger.error(f"解析命令行参数失败: {str(e)}")
    
    def has_url_command(self):
        """检查是否有URL命令"""
        return self.url_command is not None
    
    def get_url_command(self):
        """获取URL命令"""
        return self.url_command
    
    def process_url_command(self, main_window=None):
        """处理URL命令"""
        if not self.has_url_command():
            return False
        
        try:
            # 在处理URL之前重新检查配置文件是否有更新
            self.load_fixed_url_settings()
            
            url = self.get_url_command()
            logger.info(f"开始处理URL命令: {url}")
            
            if not url.startswith("secrandom://"):
                logger.error(f"无效的SecRandom URL: {url}")
                return False
            
            # 解析URL
            from urllib.parse import urlparse, parse_qs
            parsed_url = urlparse(url)
            path = parsed_url.path.strip('/')
            
            # 如果路径为空，尝试从netloc中获取路径
            if not path and parsed_url.netloc:
                path = parsed_url.netloc
            
            query_params = parse_qs(parsed_url.query)
            
            logger.info(f"URL路径: {path}")
            logger.info(f"URL参数: {query_params}")
            
            # 如果没有提供主窗口，尝试获取
            if main_window is None:
                main_window = self.get_main_window()
            
            if main_window is None:
                logger.error("找不到主窗口实例")
                return False
            
            # 界面映射字典
            interface_map = {
                "main": ("show_main_window", "main_url"),
                "settings": ("show_settings_window", "settings_url"),
                "pumping": ("show_pumping_window", "pumping_url"),
                "reward": ("show_reward_window", "reward_url"),
                "history": ("show_history_window", "history_url"),
                "floating": ("show_floating_window", "floating_url"),
                'direct_extraction': ('show_direct_extraction', 'direct_extraction_url'),
                "plugin_settings": ("show_plugin_settings_window", "plugin_settings_url")
            }
            
            # 根据路径打开对应界面
            if path in interface_map:
                method_name, setting_key = interface_map[path]
                
                # 检查该URL是否启用
                if not self.is_url_enabled(f"enable_{setting_key}"):
                    logger.error(f"URL功能已禁用: {path} (设置项: enable_{setting_key})")
                    return False
                
                # 显示弹窗提醒
                def open_interface():
                    if hasattr(main_window, method_name):
                        method = getattr(main_window, method_name)
                        method()
                        logger.info(f"通过URL成功打开界面: {path}")
                        
                        # 处理额外的参数
                        self.handle_additional_params(main_window, query_params, path)
                    else:
                        logger.error(f"主窗口缺少方法: {method_name}")
                
                # 显示弹窗提醒
                self.show_url_notification(url, setting_key, open_interface)
                
                return True
            else:
                logger.error(f"未知的界面路径: {path}")
                
                # 显示可用路径
                available_paths = ", ".join(interface_map.keys())
                logger.info(f"可用的界面路径: {available_paths}")
            
            return False
            
        except Exception as e:
            logger.error(f"处理URL命令失败: {str(e)}")
            return False
    
    def handle_additional_params(self, main_window, query_params, path=None):
        """处理额外的URL参数"""
        try:
            # 处理action参数
            if 'action' in query_params:
                action = query_params['action'][0]
                logger.info(f"执行动作: {action}")
                
                # 根据路径和动作检查是否启用
                action_enabled = True
                
                # 点名相关操作
                if path == "pumping":
                    if action == 'start':
                        action_enabled = self.is_url_enabled("pumping_start_url")
                    elif action == 'stop':
                        action_enabled = self.is_url_enabled("pumping_stop_url")
                    elif action == 'reset':
                        action_enabled = self.is_url_enabled("pumping_reset_url")
                    else:
                        action_enabled = self.is_url_enabled("pumping_action_url")
                
                # 抽奖相关操作
                elif path == "reward":
                    if action == 'start':
                        action_enabled = self.is_url_enabled("reward_start_url")
                    elif action == 'stop':
                        action_enabled = self.is_url_enabled("reward_stop_url")
                    elif action == 'reset':
                        action_enabled = self.is_url_enabled("reward_reset_url")
                    else:
                        action_enabled = self.is_url_enabled("reward_action_url")
                
                # 关于界面相关操作
                elif path == "about":
                    if action == 'donation':
                        action_enabled = self.is_url_enabled("about_donation_url")
                    elif action == 'contributor':
                        action_enabled = self.is_url_enabled("about_contributor_url")
                    else:
                        action_enabled = self.is_url_enabled("about_action_url")
                
                # 插件设置相关操作
                elif path == "plugin_settings":
                    if action == 'open':
                        action_enabled = self.is_url_enabled("plugin_settings_open_url")
                    else:
                        action_enabled = self.is_url_enabled("plugin_settings_action_url")
                
                # 如果操作未启用，记录日志并返回
                if not action_enabled:
                    logger.error(f"URL操作已禁用: {path}?action={action}")
                    return
                
                # 执行相应的操作
                # 点名相关操作
                if action == 'start' and hasattr(main_window, 'start_random_selection'):
                    main_window.start_random_selection()
                elif action == 'stop' and hasattr(main_window, 'stop_random_selection'):
                    main_window.stop_random_selection()
                elif action == 'reset' and hasattr(main_window, 'reset_selection'):
                    main_window.reset_selection()
                
                # 抽奖相关操作
                elif action == 'start' and hasattr(main_window, 'start_reward_selection'):
                    main_window.start_reward_selection()
                elif action == 'stop' and hasattr(main_window, 'stop_reward_selection'):
                    main_window.stop_reward_selection()
                elif action == 'reset' and hasattr(main_window, 'reset_reward_selection'):
                    main_window.reset_reward_selection()
                
                # 关于界面相关操作
                elif action == 'donation' and hasattr(main_window, 'show_donation_dialog'):
                    main_window.show_donation_dialog()
                elif action == 'contributor' and hasattr(main_window, 'show_contributor_dialog'):
                    main_window.show_contributor_dialog()
                
                # 插件设置相关操作
                elif action == 'open' and hasattr(main_window, 'show_plugin_settings_window'):
                    main_window.show_plugin_settings_window()
                
                else:
                    logger.error(f"未知的动作或主窗口缺少对应方法: {action}")
            
        except Exception as e:
            logger.error(f"处理额外参数失败: {str(e)}")
    
    def get_main_window(self):
        """获取主窗口实例"""
        try:
            for widget in QApplication.topLevelWidgets():
                # 通过特征识别主窗口
                if hasattr(widget, 'update_focus_mode') or hasattr(widget, 'show_main_window'):
                    return widget
            return None
        except Exception as e:
            logger.error(f"获取主窗口失败: {str(e)}")
            return None
    
    def get_available_interfaces(self):
        """获取可用的界面列表"""
        return {
            "main": "主界面",
            "settings": "设置界面",
            "pumping": "点名界面",
            "reward": "抽奖界面",
            "history": "历史记录界面",
            "floating": "浮窗界面",
            'direct_extraction': '闪抽界面',
            "plugin_settings": "插件设置界面"
        }
    
    def generate_url_examples(self):
        """生成URL使用示例"""
        # 在生成URL示例之前重新检查配置文件是否有更新
        self.load_fixed_url_settings()
        
        examples = []
        interfaces = self.get_available_interfaces()
        
        # 界面URL示例
        for path, name in interfaces.items():
            # 检查该URL是否启用
            enable_key = f"enable_{path}_url"
            if self.is_url_enabled(enable_key):
                examples.append(f"secrandom://{path} - 打开{name}")
        
        # 点名相关操作示例
        if self.is_url_enabled("enable_pumping_start_url"):
            examples.append("secrandom://pumping?action=start - 开始点名")
        if self.is_url_enabled("enable_pumping_stop_url"):
            examples.append("secrandom://pumping?action=stop - 停止点名")
        if self.is_url_enabled("enable_pumping_reset_url"):
            examples.append("secrandom://pumping?action=reset - 重置点名")
        
        # 抽奖相关操作示例
        if self.is_url_enabled("enable_reward_start_url"):
            examples.append("secrandom://reward?action=start - 开始抽奖")
        if self.is_url_enabled("enable_reward_stop_url"):
            examples.append("secrandom://reward?action=stop - 停止抽奖")
        if self.is_url_enabled("enable_reward_reset_url"):
            examples.append("secrandom://reward?action=reset - 重置抽奖")
        
        # 关于界面相关操作示例
        if self.is_url_enabled("enable_about_donation_url"):
            examples.append("secrandom://about?action=donation - 打开捐赠支持对话框")
        if self.is_url_enabled("enable_about_contributor_url"):
            examples.append("secrandom://about?action=contributor - 打开贡献者对话框")
        
        # 插件设置相关操作示例
        if self.is_url_enabled("enable_plugin_settings_open_url"):
            examples.append("secrandom://plugin_settings?action=open - 打开插件页面")
        
        return examples


# 全局URL处理器实例
url_handler = URLHandler()


def get_url_handler():
    """获取全局URL处理器实例"""
    return url_handler


def process_url_if_exists(main_window=None):
    """如果存在URL命令则处理"""
    handler = get_url_handler()
    if handler.has_url_command():
        return handler.process_url_command(main_window)
    return False


class URLNotification(QDialog):
    """URL弹窗提醒窗口"""
    
    def __init__(self, url, url_type, notification_type, callback=None):
        # 添加Qt.Tool标志隐藏任务栏图标
        super().__init__(parent=None, flags=Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.url = url
        self.url_type = url_type
        self.notification_type = notification_type
        self.callback = callback
        self.security_verified = False
        self.duration = 15000  # 默认显示15秒
        
        # 根据URL类型设置标题和描述
        self.url_info = self.get_url_info()
        
        # 初始化UI、动画和定时器
        self.init_ui()
        self.init_animation()
        self.start_auto_close_timer()
    
    def showEvent(self, event):
        """显示事件 - 确保窗口在最前面"""
        self.raise_()
        self.activateWindow()
        super().showEvent(event)
    
    def get_url_info(self):
        """根据URL类型获取URL信息"""
        url_info_map = {
            "main": {"title": "SecRandom 主界面", "desc": "即将打开SecRandom主界面"},
            "settings": {"title": "SecRandom 设置界面", "desc": "即将打开SecRandom设置界面"},
            "pumping": {"title": "SecRandom 点名界面", "desc": "即将打开SecRandom点名界面"},
            "reward": {"title": "SecRandom 抽奖界面", "desc": "即将打开SecRandom抽奖界面"},
            "history": {"title": "SecRandom 历史记录界面", "desc": "即将打开SecRandom历史记录界面"},
            "floating": {"title": "SecRandom 浮窗界面", "desc": "即将打开SecRandom浮窗界面"},
            "direct_extraction": {"title": "SecRandom 闪抽界面", "desc": "即将打开SecRandom闪抽界面"},
            "plugin_settings": {"title": "SecRandom 插件设置界面", "desc": "即将打开SecRandom插件设置界面"},
            "pumping_start": {"title": "SecRandom 开始点名", "desc": "即将开始SecRandom点名操作"},
            "pumping_stop": {"title": "SecRandom 停止点名", "desc": "即将停止SecRandom点名操作"},
            "pumping_reset": {"title": "SecRandom 重置点名", "desc": "即将重置SecRandom点名结果"},
            "reward_start": {"title": "SecRandom 开始抽奖", "desc": "即将开始SecRandom抽奖操作"},
            "reward_stop": {"title": "SecRandom 停止抽奖", "desc": "即将停止SecRandom抽奖操作"},
            "reward_reset": {"title": "SecRandom 重置抽奖", "desc": "即将重置SecRandom抽奖结果"},
            "about_donation": {"title": "SecRandom 捐赠支持", "desc": "即将打开SecRandom捐赠支持对话框"},
            "about_contributor": {"title": "SecRandom 贡献者", "desc": "即将打开SecRandom贡献者对话框"},
            "plugin_settings_open": {"title": "SecRandom 插件页面", "desc": "即将打开SecRandom插件页面"},
        }
        
        return url_info_map.get(self.url_type, {"title": "SecRandom URL请求", "desc": f"即将处理URL请求: {self.url}"})
    
    def init_ui(self):
        """初始化UI界面"""
        cursor_pos = QCursor.pos()
        for screen in QGuiApplication.screens():
            if screen.geometry().contains(cursor_pos):
                target_screen = screen
                break
        else:
            target_screen = QGuiApplication.primaryScreen()
        screen_geometry = target_screen.availableGeometry()
        max_width = min(int(screen_geometry.width() * 0.3), 500)  # 最大宽度为屏幕30%或500px取较小值
        self.setMaximumWidth(max_width)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        
        # 设置窗口标志
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setStyleSheet("""
            QDialog {                
                background-color: rgrga((235, 238, 242, 0.95)0.95);
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 5px;
           }
        """)

        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(20)

        # 标题栏（包含图标和标题）
        title_layout = QHBoxLayout()
        title_layout.setSpacing(10)

        # 更新图标
        icon_label = QLabel()
        icon_path = path_manager.get_resource_path('icon', 'secrandom-icon.png')
        icon_label.setPixmap(QIcon(str(icon_path)).pixmap(55, 55))
        icon_label.setStyleSheet("background: transparent; border: none;")

        # 标题文本
        title_label = BodyLabel(f"{self.url_info['title']}")
        title_label.setFont(QFont(load_custom_font(), 14, QFont.Bold))
        title_label.setStyleSheet("color: #1a1a1a; border: none; background: transparent;")

        # URL信息
        url_label = BodyLabel(f"URL: {self.url}\n{self.url_info['desc']}")
        url_label.setFont(QFont(load_custom_font(), 12))
        url_label.setStyleSheet("color: #2d3436; border: none; background: transparent;")
        url_label.setAlignment(Qt.AlignCenter)

        # 关闭按钮
        close_btn = PushButton("")
        close_icon_path = get_theme_icon("ic_fluent_arrow_exit_20_filled")
        close_btn.setIcon(QIcon(str(close_icon_path)))
        close_btn.setStyleSheet("background: transparent; border: none;")
        close_btn.clicked.connect(self.close_with_animation)

        # 添加到标题布局
        title_layout.addWidget(icon_label)
        title_layout.addWidget(title_label)
        title_layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum))
        title_layout.addWidget(close_btn)

        # 按钮布局
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)   

        # 根据通知类型添加不同的按钮
        try:
            theme_color = themeColor()
            # 如果themeColor()返回的是QColor对象，需要转换为十六进制字符串
            if hasattr(theme_color, 'name'):
                theme_color = theme_color.name()
        except:
            theme_color = "#3AF2FF"
            
        font_color = "black"
            
        if self.notification_type == 1:  # 1=notify_only
            # 仅提醒类型，只有一个关闭按钮
            close_btn = PushButton("关闭")
            close_btn.setStyleSheet(f""
                f"QPushButton {{background-color: {theme_color}; color: {font_color}; border-radius: 8px; padding: 8px 16px; font-weight: 500; border: none;}}"
                f"QPushButton:hover {{background-color: {theme_color};}}"
            )
            close_btn.setFont(QFont(load_custom_font(), 12))
            close_btn.clicked.connect(self.close_with_animation)
            btn_layout.addWidget(close_btn)
        else:
            # 确认类型，有确认和取消按钮
            cancel_btn = PushButton("取消")
            cancel_btn.setStyleSheet(""
                f"QPushButton {{background-color: #6c757d; color: {font_color}; border-radius: 8px; padding: 8px 16px; font-weight: 500; border: none;}}"
                "QPushButton:hover {background-color: #5a6268;}"
            )
            cancel_btn.setFont(QFont(load_custom_font(), 12))
            cancel_btn.clicked.connect(self.close_with_animation)
            
            confirm_btn = PushButton("确认")
            confirm_btn.setStyleSheet(f""
                f"QPushButton {{background-color: {theme_color}; color: {font_color}; border-radius: 8px; padding: 8px 16px; font-weight: 500; border: none;}}"
                "QPushButton:hover {background-color: #218838;}"
            )
            confirm_btn.setFont(QFont(load_custom_font(), 12))
            confirm_btn.clicked.connect(self.on_confirm_clicked)

            btn_layout.addWidget(confirm_btn)

        # 添加所有组件到主布局
        main_layout.addLayout(title_layout)
        main_layout.addWidget(url_label)
        main_layout.addLayout(btn_layout)

        # 首先将窗口移动到右下角
        self.move_to_bottom_right()
        # 设置窗口初始透明度为0，以便动画效果
        self.setWindowOpacity(0.0)
    
    def init_animation(self):
        """初始化动画效果"""
        # 获取屏幕几何信息
        screen_geometry = QApplication.desktop().availableGeometry()
        
        # 首先确保窗口在右下角
        self.adjustSize()  # 确保窗口大小正确
        x = max(0, screen_geometry.width() - self.width() - 20)
        y = max(0, screen_geometry.height() - self.height() - 20)
        
        # 设置初始位置在屏幕右侧外
        start_x = screen_geometry.width()
        self.move(start_x, y)
        
        # 创建位置动画
        self.pos_animation = QPropertyAnimation(self, b"pos")
        self.pos_animation.setDuration(600)
        self.pos_animation.setEasingCurve(QEasingCurve.OutCubic)
        self.pos_animation.setStartValue(QPoint(start_x, y))
        self.pos_animation.setEndValue(QPoint(x, y))
        
        # 创建透明度动画
        self.opacity_animation = QPropertyAnimation(self, b"windowOpacity")
        self.opacity_animation.setDuration(400)
        self.opacity_animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.opacity_animation.setStartValue(0.0)
        self.opacity_animation.setEndValue(1.0)
        
        # 并行运行所有动画
        self.group_animation = QParallelAnimationGroup(self)
        self.group_animation.addAnimation(self.pos_animation)
        self.group_animation.addAnimation(self.opacity_animation)
        
        # 连接动画完成信号
        self.group_animation.finished.connect(self.on_animation_finished)
        
        # 延迟启动动画，确保窗口已完全初始化
        QTimer.singleShot(100, self.start_animation)

    def start_animation(self):
        """启动动画效果"""
        if hasattr(self, 'group_animation'):
            self.group_animation.start()
    
    def on_animation_finished(self):
        """动画完成事件处理"""
        # 确保窗口在最前面
        self.raise_()
        self.activateWindow()
    
    def start_auto_close_timer(self):
        """启动自动关闭定时器"""
        self.timer = QTimer(self)
        # 根据通知类型设置不同的行为
        if self.notification_type == 1:  # 1=notify_only，仅提醒模式
            # 仅提醒模式下，定时器到期后执行回调并关闭窗口
            self.timer.timeout.connect(self.on_notify_only_timeout)
        else:  # 其他模式，定时器到期后只关闭窗口
            self.timer.timeout.connect(self.close_with_animation)
        self.timer.start(self.duration)
    
    def on_notify_only_timeout(self):
        """仅提醒模式超时处理 - 执行回调并关闭窗口"""
        # 执行回调函数
        if self.callback:
            self.callback()
        # 关闭窗口
        self.close_with_animation()

    def move_to_bottom_right(self):
        """将窗口移动到屏幕右下角"""
        screen_geometry = QGuiApplication.primaryScreen().availableGeometry()
        # 重新获取窗口尺寸确保准确性
        self.adjustSize()
        x = max(0, screen_geometry.width() - self.width() - 20)
        y = max(0, screen_geometry.height() - self.height() - 20)
        self.move(x, y)
    
    def on_security_checkbox_changed(self, state):
        """安全验证复选框状态变化处理"""
        self.security_verified = (state == Qt.Checked)
        # 启用或禁用确认按钮
        for i in range(self.layout().count()):
            item = self.layout().itemAt(i)
            if isinstance(item, QHBoxLayout):
                for j in range(item.count()):
                    widget = item.itemAt(j).widget()
                    if isinstance(widget, PushButton) and widget.text() == "确认":
                        widget.setEnabled(self.security_verified)
                        break
    
    def on_confirm_clicked(self):
        """确认按钮点击事件"""
        # 如果是安全验证模式，需要先进行密码验证
        if self.notification_type == 3:  # 3=confirm_with_security
            try:
                from app.common.password_dialog import PasswordDialog
                # 读取安全设置文件，获取密码验证配置
                enc_settings_path = path_manager.get_enc_set_path()
                with open_file(enc_settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    logger.info("星野安检: 正在读取安全设置，准备执行URL操作验证～ ")
                    
                    # 检查是否启用了启动密码和退出验证功能
                    if settings.get('hashed_set', {}).get('start_password_enabled', False) == True:
                        # 创建并显示密码验证对话框，等待用户输入
                        dialog = PasswordDialog(self)
                        if dialog.exec_() != QDialog.Accepted:
                            logger.error("星野安检: 用户取消URL操作，安全防御已解除～ ")
                            # 验证失败或用户取消，不执行回调函数并返回
                            return
            except Exception as e:
                # 捕获验证过程中的任何异常，确保程序不会崩溃
                logger.error(f"星野安检失败: 密码验证系统出错喵～ {e}")
                # 发生异常时不执行回调函数，直接返回
                return
        
        # 执行回调函数
        if self.callback:
            self.callback()
        self.close_with_animation()
    
    def close_with_animation(self):
        """带动画效果关闭窗口"""
        # 获取屏幕几何信息
        screen_geometry = QApplication.desktop().availableGeometry()
        
        # 创建位置动画到屏幕右侧外
        self.pos_animation = QPropertyAnimation(self, b"pos")
        self.pos_animation.setEasingCurve(QEasingCurve.InCubic)
        self.pos_animation.setDuration(600)
        self.pos_animation.setStartValue(self.pos())
        self.pos_animation.setEndValue(QPoint(screen_geometry.width(), self.y()))
        
        # 创建透明度动画
        self.opacity_animation = QPropertyAnimation(self, b"windowOpacity")
        self.opacity_animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.opacity_animation.setDuration(400)
        self.opacity_animation.setStartValue(1.0)
        self.opacity_animation.setEndValue(0.0)
        
        # 并行运行所有动画
        self.group_animation = QParallelAnimationGroup(self)
        self.group_animation.addAnimation(self.pos_animation)
        self.group_animation.addAnimation(self.opacity_animation)
        self.group_animation.finished.connect(self.close)
        self.group_animation.start()

    def mousePressEvent(self, event):
        """鼠标按下事件 - 重置自动关闭定时器"""
        if event.button() == Qt.LeftButton:
            self.timer.start(self.duration)
        super().mousePressEvent(event)

    def closeEvent(self, event):
        """窗口关闭事件 - 清理资源"""
        # 清理动画资源
        if hasattr(self, 'fade_animation'):
            self.fade_animation.stop()
            self.fade_animation.deleteLater()
        
        if hasattr(self, 'fade_effect'):
            self.fade_effect.deleteLater()
            
        # 清理定时器 - 添加额外检查防止对象已被删除
        if hasattr(self, 'timer'):
            try:
                # 检查定时器是否仍然有效
                if self.timer and not self.timer.parent() is None:
                    self.timer.stop()
                    self.timer.deleteLater()
            except RuntimeError:
                # 定时器对象已被删除，忽略错误
                pass
        
        super().closeEvent(event)


if __name__ == "__main__":
    # 测试URL处理器
    handler = URLHandler()
    
    if handler.has_url_command():
        print(f"URL命令: {handler.get_url_command()}")
    else:
        print("没有URL命令")
    
    # 显示可用界面
    interfaces = handler.get_available_interfaces()
    print("\n可用界面:")
    for path, name in interfaces.items():
        print(f"  {path}: {name}")
    
    # 显示URL示例
    examples = handler.generate_url_examples()
    print("\nURL使用示例:")
    for example in examples:
        print(f"  {example}")