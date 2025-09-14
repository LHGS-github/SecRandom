# ================================================== ✧*｡٩(ˊᗜˋ*)و✧*｡
# 魔法导入水晶球 🔮
# ================================================== ✧*｡٩(ˊᗜˋ*)و✧*｡

# ✨ 系统自带魔法道具 ✨
import json
import os
import sys
import time
import subprocess
import warnings
import random
from urllib3.exceptions import InsecureRequestWarning
from pathlib import Path

# 🧙‍♀️ 第三方魔法典籍 🧙‍♂️
import loguru
from loguru import logger
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtNetwork import *
from PyQt5.QtWidgets import QGraphicsBlurEffect, QGraphicsScene, QGraphicsPixmapItem
from qfluentwidgets import *

# 🏰 应用内部魔法卷轴 🏰
from app.common.config import YEAR, MONTH, AUTHOR, VERSION, APPLY_NAME, GITHUB_WEB, BILIBILI_WEB
from app.common.config import get_theme_icon, load_custom_font, check_for_updates, get_update_channel
from app.common.path_utils import path_manager
from app.common.path_utils import open_file, ensure_dir
from app.view.settings import settings_Window
from app.view.main_page.pumping_people import pumping_people
from app.view.main_page.pumping_reward import pumping_reward
from app.view.main_page.history_handoff_setting import history_handoff_setting
from app.view.main_page.vocabulary_learning import vocabulary_learning
from app.view.levitation import LevitationWindow
from app.view.settings_page.about_setting import about
from app.common.about import ContributorDialog, DonationDialog
from app.common.password_settings import check_and_delete_pending_usb

# ================================================== (^・ω・^ )
# 白露的初始化魔法阵 ⭐
# ================================================== (^・ω・^ )

# 🔮 忽略那些烦人的不安全请求警告
warnings.filterwarnings('ignore', category=InsecureRequestWarning)

# 星野导航：使用跨平台路径定位设置目录 ✧*｡٩(ˊᗜˋ*)ow✧*｡
settings_dir = path_manager.get_settings_path().parent
ensure_dir(settings_dir)
logger.info("白露魔法: 创建了设置目录哦~ ✧*｡٩(ˊᗜˋ*)ow✧*｡")

def show_update_notification(latest_version):
    """显示自定义更新通知窗口"""
    try:
        from app.common.update_notification import UpdateNotification
        import sys

        # 确保有应用实例
        if QApplication.instance() is None:
            app = QApplication(sys.argv)
        else:
            app = QApplication.instance()

        # 创建并显示通知窗口
        notification = UpdateNotification(latest_version)
        notification.show()
        # 防止通知窗口关闭时程序退出
        original_quit_setting = app.quitOnLastWindowClosed()
        app.setQuitOnLastWindowClosed(False)
        notification.destroyed.connect(lambda: app.setQuitOnLastWindowClosed(original_quit_setting))
        logger.info(f"自定义更新通知已显示，版本: {latest_version}")

    except ImportError as e:
        logger.error(f"导入自定义通知失败: {str(e)}")
    except Exception as e:
        logger.error(f"显示更新通知失败: {str(e)}", exc_info=True)

# ==================================================
# 配置管理类
# ==================================================
class ConfigurationManager:
    """(^・ω・^ ) 白露的配置管理魔法书
    负责保管所有设置的小管家哦~ 会把重要的配置都藏在安全的地方！
    还会自动缓存设置，减少不必要的IO操作，是不是很聪明呀？(๑•̀ㅂ•́)ow✧"""

    def __init__(self):
        """开启白露的配置魔法~ 初始化设置路径和默认值，并预加载设置"""
        self.app_dir = path_manager._app_root
        self.settings_path = path_manager.get_settings_path('Settings.json')  # 📜 普通设置文件路径
        self.enc_settings_path = path_manager.get_enc_set_path()  # 🔒 加密设置文件路径
        self.default_settings = {
            'foundation': {
                'main_window_focus_mode': 0,
                'main_window_focus_time': 0,
                'window_width': 800,
                'window_height': 600,
                'pumping_floating_enabled': True,
                'pumping_floating_side': 0,
                'pumping_reward_side': 0,
                'main_window_mode': 0,
                'check_on_startup': True,
                'topmost_switch': False
            }
        }  # 📝 默认设置模板
        # 🌟 星穹铁道白露：预加载设置缓存，减少启动时IO操作
        self._settings_cache = None
        self.load_settings()

    def load_settings(self):
        """(^・ω・^ ) 读取配置文件的魔法
        尝试打开设置文件，如果失败就用默认设置哦~ 不会让程序崩溃的！
        使用缓存避免重复IO操作，就像记忆力超群的小精灵一样~ ✧*｡٩(ˊᗜˋ*)ow✧*｡"""
        # if self._settings_cache is not None:
        #     return self._settings_cache
        try:
            ensure_dir(self.settings_path.parent)
            with open_file(self.settings_path, 'r', encoding='utf-8') as f:
                self._settings_cache = json.load(f)
                return self._settings_cache
        except Exception as e:
            logger.error(f"白露魔法出错: 加载设置文件失败了呢~ {e}")
            self._settings_cache = self.default_settings
            return self._settings_cache  # 返回默认设置作为后备方案

    def get_foundation_setting(self, key):
        """(^・ω・^ ) 获取基础设置的小魔法
        从设置中找到对应的key值，如果找不到就用默认值哦~ 
        像在魔法袋里找东西，总能找到需要的那个！✨"""
        settings = self.load_settings()
        return settings.get('foundation', {}).get(key, self.default_settings['foundation'][key])

    def save_window_size(self, width, height):
        """(^・ω・^ ) 保存窗口大小的魔法咒语
        确保窗口不会太小（至少600x400），然后把新尺寸记下来~ 
        就像整理房间一样，要保持整洁又实用呢！(๑•̀ㅂ•́)ow✧"""
        if width < 600 or height < 400:  # 太小的窗口可不行哦~ 
            logger.warning("白露提醒: 窗口尺寸太小啦，不保存哦~ ")
            return

        try:
            settings = self.load_settings()
            if 'foundation' not in settings:
                settings['foundation'] = {}  # 如果没有基础设置，就创建一个
            settings['foundation']['window_width'] = width
            settings['foundation']['window_height'] = height

            ensure_dir(self.settings_path.parent)
            with open_file(self.settings_path, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=4)
            logger.info(f"白露魔法成功: 窗口大小已保存为 {width}x{height} ✨")
        except Exception as e:
            logger.error(f"白露魔法出错: 保存窗口大小失败了呢~ {e}")


# ==================================================
# 更新检查类
# ==================================================
class UpdateChecker(QObject):
    """(ﾟДﾟ≡ﾟдﾟ) 星野的更新巡逻队！
    负责监视有没有新版本发布，发现时会发出警报信号喵！
    就像太空巡逻兵一样，保护软件安全又新鲜！🚀✨"""

    update_available = pyqtSignal(str)  # 🚨 发现新版本时发射的信号

    def __init__(self, parent=None):
        """启动星野的更新检查系统！准备好监视版本变化喵！"""
        super().__init__(parent)

    def check_for_updates(self):
        """(ﾟДﾟ≡ﾟдﾟ) 启动更新检查任务！
        派出 Worker 小分队去执行秘密任务，不会打扰主线程喵！
        就像派出侦察机一样，悄悄地收集情报～ 🕵️‍♂️✨"""
        self.worker = self.UpdateCheckWorker()
        self.worker.result_ready.connect(self.on_update_result)
        self.worker.start()
        logger.info("星野指令: 更新检查小分队已出发！")

    class UpdateCheckWorker(QThread):
        """(ﾟдﾟ≡ﾟдﾟ) 更新检查特工队！
        在后台默默工作的线程，专门负责版本侦察任务喵！
        绝对不会打扰UI主线程的工作，非常专业！💪"""
        result_ready = pyqtSignal(bool, str)  # 📡 发送侦察结果的信号
        
        def __init__(self):
            super().__init__()
            self._is_running = True
            self._force_stop = False
        
        def stop(self):
            """停止特工队行动！"""
            self._is_running = False
            self._force_stop = True
        
        def run(self):
            """特工队行动开始！连接服务器获取最新版本信息！"""
            try:
                # 设置线程为可终止
                self.setTerminationEnabled(True)
                
                channel = get_update_channel()
                if self._is_running and not self._force_stop:
                    update_available, latest_version = check_for_updates(channel)
                    if self._is_running and not self._force_stop:
                        self.result_ready.emit(update_available, latest_version)
            except Exception as e:
                logger.error(f"星野侦察失败: 更新检查过程中出错喵～ {e}")
                if self._is_running and not self._force_stop:
                    self.result_ready.emit(False, "")

    def on_update_result(self, update_available, latest_version):
        """(ﾟдﾟ≡ﾟдﾟ) 收到侦察报告！
        如果发现新版本，立刻拉响警报发射信号喵！
        绝不让用户错过任何重要更新！🚨✨"""
        if update_available and latest_version:
            logger.info(f"星野警报: 发现新版本 {latest_version}！准备通知用户！")
            self.update_available.emit(latest_version)  # 发射新版本信号
    
    def stop_checking(self):
        """(ﾟдﾟ≡ﾟдﾟ) 停止更新检查任务！
        确保worker线程安全停止，不会造成线程销毁错误喵！
        就像让特工队安全撤退一样重要！🛡️✨"""
        try:
            if hasattr(self, 'worker') and self.worker:
                # 立即设置强制停止标志
                self.worker.stop()
                
                # 断开信号连接
                try:
                    self.worker.result_ready.disconnect(self.on_update_result)
                except:
                    pass
                
                # 停止worker线程
                if self.worker.isRunning():
                    # 首先尝试优雅退出
                    self.worker.quit()
                    if not self.worker.wait(2000):  # 等待最多2秒
                        logger.warning("星野撤退: 线程优雅退出失败，准备强制终止～ ")
                        # 如果优雅退出失败，强制终止
                        self.worker.terminate()
                        self.worker.wait(1000)  # 再等待1秒
                        
                        # 如果还在运行，记录警告
                        if self.worker.isRunning():
                            logger.error("星野撤退: 线程仍然在运行，可能存在资源泄漏！")
                
                # 清理引用
                self.worker = None
                logger.info("星野撤退: 更新检查任务已安全停止～ ")
        except Exception as e:
            logger.error(f"星野撤退失败: 停止更新检查时出错喵～ {e}")
    
    def __del__(self):
        """析构函数，确保资源正确释放"""
        try:
            self.stop_checking()
        except:
            pass


# ==================================================
# 托盘图标管理器类
# ==================================================
class TrayIconManager(QObject):
    """(^・ω・^ ) 白露的系统托盘精灵！
    负责管理可爱的托盘图标和菜单，右键点击会有惊喜哦～
    就像藏在任务栏里的小助手，随时待命呢！(๑•̀ㅂ•́)ow✧"""

    def __init__(self, main_window):
        """(^・ω・^ ) 唤醒托盘精灵！
        初始化系统托盘图标，设置好图标和提示文字～ 
        让它在任务栏安营扎寨，随时准备为用户服务！🏕️✨"""
        super().__init__(main_window)
        self.main_window = main_window
        self.tray_icon = QSystemTrayIcon(main_window)
        self.tray_icon.setIcon(QIcon(str(path_manager.get_resource_path('icon', 'SecRandom.png')))) 
        self.tray_icon.setToolTip('SecRandom')  # 鼠标放上去会显示的文字
        self._create_menu()  # 创建魔法菜单
        self.tray_icon.activated.connect(self._on_tray_activated)  # 连接点击事件
        
        # 初始化菜单自动关闭定时器
        self.menu_timer = QTimer(main_window)
        self.menu_timer.setSingleShot(True)
        self.menu_timer.timeout.connect(self._on_menu_timeout)
        
        # 安装事件过滤器来检测点击外部
        self.tray_menu.installEventFilter(self)
        QApplication.instance().installEventFilter(self)
        
        logger.info("白露魔法: 托盘精灵已唤醒！")

    def _create_menu(self):
        """(^・ω・^ ) 制作托盘菜单魔法！
        精心设计的右键菜单，包含各种常用功能～ 
        就像准备了一桌丰盛的点心，总有一款适合你！🍰✨"""
        self.tray_menu = RoundMenu(parent=self.main_window)
        # 关于SecRandom
        self.tray_menu.addAction(Action(get_theme_icon("ic_fluent_info_20_filled"), '关于SecRandom', triggered=self.main_window.show_about_tab))
        self.tray_menu.addSeparator()
        # 主界面控制
        self.tray_menu.addAction(Action(get_theme_icon("ic_fluent_power_20_filled"), '暂时显示/隐藏主界面', triggered=self.main_window.toggle_window))
        self.tray_menu.addAction(Action(get_theme_icon("ic_fluent_window_ad_20_filled"), '暂时显示/隐藏浮窗', triggered=self.main_window.toggle_levitation_window))
        # self.tray_menu.addAction(Action(get_theme_icon("ic_fluent_window_inprivate_20_filled"), '切换窗口置顶', triggered=self.main_window.toggle_window_topmost))
        self.tray_menu.addAction(Action(get_theme_icon("ic_fluent_settings_20_filled"), '打开设置界面', triggered=self.main_window.show_setting_interface))
        self.tray_menu.addSeparator()
        # 系统操作
        self.tray_menu.addAction(Action(get_theme_icon("ic_fluent_arrow_sync_20_filled"), '重启', triggered=self.main_window.restart_app))
        self.tray_menu.addAction(Action(get_theme_icon("ic_fluent_arrow_exit_20_filled"), '退出', triggered=self.main_window.close_window_secrandom))
        logger.info("白露魔法: 托盘菜单已准备就绪！")

    def _on_tray_activated(self, reason):
        """(^・ω・^ ) 托盘精灵响应事件！
        当用户点击托盘图标时，显示精心准备的菜单～ 
        就像有人敲门时，立刻开门迎接客人一样热情！(๑•̀ㅂ•́)ow✧"""
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.Context):
            pos = QCursor.pos()  # 获取鼠标位置
            
            # 确保菜单不会超出屏幕边界
            screen = QApplication.primaryScreen().availableGeometry()
            menu_size = self.tray_menu.sizeHint()
            
            # 计算菜单显示位置，优先在鼠标位置附近显示
            # 如果鼠标位置右侧空间不足，显示在鼠标左侧
            if pos.x() + menu_size.width() > screen.right():
                adjusted_x = pos.x() - menu_size.width()
            else:
                adjusted_x = pos.x()
            
            # 如果鼠标位置下方空间不足，显示在鼠标上方
            if pos.y() + menu_size.height() > screen.bottom():
                adjusted_y = pos.y() - menu_size.height()
            else:
                adjusted_y = pos.y()
            
            # 确保菜单完全在屏幕内
            adjusted_x = max(screen.left(), min(adjusted_x, screen.right() - menu_size.width()))
            adjusted_y = max(screen.top(), min(adjusted_y, screen.bottom() - menu_size.height()))
            
            adjusted_pos = QPoint(adjusted_x, adjusted_y - 35)
            self.tray_menu.popup(adjusted_pos)  # 在调整后的位置显示菜单
            
            # 启动5秒自动关闭定时器
            self.menu_timer.start(5000)  # 5秒后自动关闭
            logger.debug("白露魔法: 托盘菜单已显示给用户～ ")
    
    def _on_menu_timeout(self):
        """(^・ω・^ ) 菜单超时自动关闭！
        当用户5秒内没有操作菜单时，自动关闭菜单～
        就像害羞的小精灵，等待太久就会悄悄离开呢！(๑•̀ㅂ•́)ow✧"""
        if self.tray_menu.isVisible():
            self.tray_menu.close()
            logger.debug("白露魔法: 托盘菜单因超时自动关闭～ ")
    
    def eventFilter(self, obj, event):
        """(^・ω・^ ) 事件过滤器魔法！
        监听菜单相关事件，当用户点击菜单外部时自动关闭菜单～
        就像敏锐的守护者，时刻关注着用户的一举一动！(๑•̀ㅂ•́)ow✧"""
        if obj == self.tray_menu:
            # 如果是菜单被点击，停止定时器（用户正在操作）
            if event.type() == event.MouseButtonPress:
                self.menu_timer.stop()
            # 如果菜单失去焦点，关闭菜单
            elif event.type() == event.Hide:
                self.menu_timer.stop()
        
        # 检测点击外部区域关闭菜单
        if event.type() == event.MouseButtonPress and self.tray_menu.isVisible():
            # 获取点击位置
            click_pos = event.globalPos()
            menu_rect = self.tray_menu.geometry()
            
            # 如果点击位置不在菜单区域内，关闭菜单
            if not menu_rect.contains(click_pos):
                self.tray_menu.close()
                self.menu_timer.stop()
                logger.debug("白露魔法: 托盘菜单因点击外部而关闭～ ")
                return True
        
        return super().eventFilter(obj, event)


# ==================================================
# 主窗口类
# ==================================================
class Window(MSFluentWindow):
    """(ﾟДﾟ≡ﾟдﾟ) 星野的主窗口司令部！
    这里是程序的核心指挥中心喵！所有重要操作都从这里发起～
    不要随便修改这里的核心逻辑，会导致系统崩溃喵！(๑•̀ㅂ•́)ow✧"""

    # ==============================
    # 星野的魔法常量库 ✨
    # ==============================
    FOCUS_TIMEOUT_MAP = [
        0, 0, 3000, 5000, 10000, 15000, 30000, 60000, 120000, 180000, 300000, 600000, 1800000,
        2700000, 3600000, 7200000, 10800000, 21600000, 43200000
    ]
    """(ﾟДﾟ≡ﾟдﾟ) 星野的焦点超时魔法数组！
    存储不同模式下窗口自动隐藏的时间阈值（毫秒）喵～
    0=不隐藏，1=立即隐藏，其他值按索引对应不同时长！"""

    FOCUS_TIMEOUT_TIME = [
        0, 1000, 2000, 3000, 5000, 10000, 15000, 30000, 60000, 300000, 600000, 900000, 1800000,
        3600000, 7200000, 10800000, 21600000, 43200000
    ]
    """(ﾟДﾟ≡ﾟдﾟ) 星野的检查间隔魔法数组！
    存储焦点检查的时间间隔（毫秒）喵～
    不同索引对应不同的检查频率，数值越小检查越频繁！"""

    MINIMUM_WINDOW_SIZE = (600, 400)
    """(^・ω・^ ) 白露的窗口尺寸保护魔法！
    窗口最小不能小于这个尺寸哦～ 太小了会看不清内容的！(๑•̀ㅂ•́)ow✧"""

    # ==============================
    # 初始化与生命周期方法
    # ==============================
    def __init__(self):
        super().__init__()
        # 设置窗口对象名称，方便其他组件查找
        self.setObjectName("MainWindow")
        
        # 初始化管理器
        self.config_manager = ConfigurationManager()
        self.update_checker = UpdateChecker(self)
        self.update_checker.update_available.connect(show_update_notification)

        # 初始化IPC服务器
        self.server = QLocalServer(self)
        self.server.newConnection.connect(self.handle_new_connection)
        
        # 清理可能存在的旧服务器实例
        QLocalServer.removeServer("SecRandomIPC")
        
        # 尝试监听，如果失败则输出错误日志
        if not self.server.listen("SecRandomIPC"):
            logger.error(f"IPC服务器监听失败: {self.server.errorString()}")
        else:
            logger.info("IPC服务器监听成功: SecRandomIPC")

        # 初始化定时器
        self.focus_timer = QTimer(self)
        self.focus_timer.timeout.connect(self.check_focus_timeout)
        self.last_focus_time = QDateTime.currentDateTime()

        self.resize_timer = QTimer(self)
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(lambda: self.config_manager.save_window_size(self.width(), self.height()))

        # USB检测定时器
        self.usb_detection_timer = QTimer(self)
        self.usb_detection_timer.timeout.connect(check_and_delete_pending_usb)
        self.usb_detection_timer.start(5000)  # 每5秒检查一次


        # 初始化焦点模式设置
        self.focus_mode = self.config_manager.get_foundation_setting('main_window_focus_mode')
        self.focus_time = self.config_manager.get_foundation_setting('main_window_focus_time')

        # 验证焦点时间有效性
        if self.focus_time >= len(self.FOCUS_TIMEOUT_TIME):
            self.focus_time = 1

        # 启动焦点计时器
        # ✨ 小鸟游星野：修复CPU占用过高问题，设置最低计时器间隔为200ms
        if self.focus_time == 0:
            pass
        else:
            # 🌟 星穹铁道白露：确保计时器间隔不小于200ms
            interval = max(self.FOCUS_TIMEOUT_TIME[self.focus_time], 200)
            self.focus_timer.start(interval)

        # 设置窗口属性
        window_width = self.config_manager.get_foundation_setting('window_width')
        window_height = self.config_manager.get_foundation_setting('window_height')
        self.resize(window_width, window_height)
        self.setMinimumSize(self.MINIMUM_WINDOW_SIZE[0], self.MINIMUM_WINDOW_SIZE[1])
        self.setWindowTitle('SecRandom')
        self.setWindowIcon(QIcon(str(path_manager.get_resource_path('icon', 'SecRandom.png'))))

        # 应用背景图片
        self.apply_background_image()

        # 检查更新
        check_startup = self.config_manager.get_foundation_setting('check_on_startup')
        if check_startup:
            self.check_updates_async()

        self._position_window()
        self.createSubInterface()
        self.tray_manager = TrayIconManager(self)
        self.tray_manager.tray_icon.show()
        self.start_cleanup()
        self.levitation_window = LevitationWindow()
        if self.config_manager.get_foundation_setting('pumping_floating_enabled'):
            self.levitation_window.show()

        if self.config_manager.get_foundation_setting('topmost_switch'):
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint) # 置顶
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint) # 取消置顶

        self._apply_window_visibility_settings()

    def apply_background_image(self):
        """(^・ω・^ ) 白露的背景图片魔法！
        检查设置中的 enable_main_background，如果开启则应用主界面背景图片～
        让界面变得更加美观个性化，就像给房间贴上漂亮的壁纸一样！(๑•̀ㅂ•́)ow✧"""
        try:
            # 读取自定义设置
            custom_settings_path = path_manager.get_settings_path('custom_settings.json')
            with open_file(custom_settings_path, 'r', encoding='utf-8') as f:
                custom_settings = json.load(f)
                
            # 检查是否启用了主界面背景图标
            personal_settings = custom_settings.get('personal', {})
            enable_main_background = personal_settings.get('enable_main_background', True)
            
            if enable_main_background:
                # 获取主界面背景图片设置
                main_background_image = personal_settings.get('main_background_image', '')
                
                # 检查是否选择了背景图片
                if main_background_image and main_background_image != "无背景图":
                    # 获取背景图片文件夹路径
                    background_dir = path_manager.get_resource_path('images', 'background')
                    
                    # 检查文件夹是否存在
                    if background_dir.exists():
                        # 构建图片完整路径
                        image_path = background_dir / main_background_image
                        
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
                                
                                logger.info(f"白露魔法: 已成功应用主界面背景图片 {main_background_image}，模糊度: {blur_value}，亮度: {brightness_value}%～ ")
                            else:
                                logger.error(f"白露魔法出错: 主界面背景图片 {main_background_image} 加载失败～ ")
                        else:
                            logger.warning(f"白露提醒: 主界面背景图片 {main_background_image} 不存在～ ")
                    else:
                        logger.warning("白露提醒: 背景图片文件夹不存在～ ")
                else:
                    logger.debug("白露魔法: 未选择主界面背景图片～ ")
            else:
                logger.debug("白露魔法: 主界面背景图片功能未启用～ ")
                
        except FileNotFoundError:
            logger.warning("白露提醒: 自定义设置文件不存在，使用默认设置～ ")
        except Exception as e:
            logger.error(f"白露魔法出错: 应用主界面背景图片时发生异常～ {e}")
    
    def _on_resize_event(self, event):
        """(^・ω・^ ) 白露的窗口大小调整魔法！
        当窗口大小改变时，自动调整背景图片大小，确保背景始终填满整个窗口～
        就像魔法地毯一样，无论房间多大都能完美铺满！(๑•̀ㅂ•́)ow✧"""
        # 调用原始的resizeEvent，确保布局正确更新
        if hasattr(self, 'original_resizeEvent'):
            self.original_resizeEvent(event)
        else:
            super(Window, self).resizeEvent(event)
        
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
        """(^・ω・^ ) 白露的窗口最大化处理魔法！
        当窗口最大化时，确保所有控件正确适应新的窗口大小～
        就像魔法变形术一样，让界面完美适应全屏状态！(๑•̀ㅂ•́)ow✧"""
        # 确保所有子控件适应最大化窗口
        for child in self.findChildren(QWidget):
            child.updateGeometry()
        
        # 强制重新布局
        QApplication.processEvents()
        
        # 延迟再次更新布局，确保所有控件都已适应
        QTimer.singleShot(100, self._delayed_layout_update)
    
    def _delayed_layout_update(self):
        """(^・ω・^ ) 白露的延迟布局更新魔法！
        在窗口最大化后延迟执行布局更新，确保所有控件都已正确适应～
        就像魔法延时术一样，给界面一些时间来完美调整！(๑•̀ㅂ•́)ow✧"""
        # 再次强制更新布局
        self.updateGeometry()
        self.update()
        
        # 确保所有子控件再次更新
        for child in self.findChildren(QWidget):
            child.updateGeometry()
        
        # 最后一次强制重新布局
        QApplication.processEvents()

    def _position_window(self):
        """(^・ω・^ ) 白露的窗口定位魔法！
        根据屏幕尺寸和用户设置自动计算最佳位置～
        确保窗口出现在最舒服的视觉位置，不会让眼睛疲劳哦！(๑•̀ㅂ•́)ow✧"""
        import platform
        
        screen = QApplication.primaryScreen()
        desktop = screen.availableGeometry()
        w, h = desktop.width(), desktop.height()
        main_window_mode = self.config_manager.get_foundation_setting('main_window_mode')
        
        # 计算目标位置
        if main_window_mode == 0:
            # 模式0：屏幕正中央定位
            target_x = w // 2 - self.width() // 2
            target_y = h // 2 - self.height() // 2
        elif main_window_mode == 1:
            # 模式1：屏幕偏下定位（更符合视觉习惯）
            target_x = w // 2 - self.width() // 2
            target_y = h * 3 // 5 - self.height() // 2
        
        # Linux兼容性处理
        if platform.system().lower() == 'linux':
            self._position_window_linux(target_x, target_y)
        else:
            # Windows和其他系统使用标准方法
            self.move(target_x, target_y)
            
        logger.debug(f"白露魔法: 窗口已定位到({self.x()}, {self.y()})位置～ ")
    
    def _position_window_linux(self, target_x, target_y):
        """(^・ω・^ ) 白露的Linux窗口定位魔法！
        专门为Linux系统优化的窗口定位方法，处理各种窗口管理器兼容性问题～
        确保在GNOME、KDE、XFCE等桌面环境下都能正常工作哦！(๑•̀ㅂ•́)ow✧"""
        try:
            # 确保窗口已经显示
            if not self.isVisible():
                self.show()
            
            # 先移动到目标位置
            self.move(target_x, target_y)
            
            # 如果move没有生效，尝试使用setGeometry
            current_x, current_y = self.x(), self.y()
            if abs(current_x - target_x) > 10 or abs(current_y - target_y) > 10:
                # move方法可能没有生效，使用setGeometry
                window_width = self.width()
                window_height = self.height()
                self.setGeometry(target_x, target_y, window_width, window_height)
            
            # 再次检查位置，如果仍然不正确，尝试延迟重定位
            current_x, current_y = self.x(), self.y()
            if abs(current_x - target_x) > 10 or abs(current_y - target_y) > 10:
                # 使用QTimer延迟重定位，给窗口管理器一些时间
                QTimer.singleShot(100, lambda: self._delayed_position_linux(target_x, target_y))
                
        except Exception as e:
            logger.error(f"白露魔法出错: Linux窗口定位失败了呢～ {e}")
            # 最后的备用方案：强制设置几何形状
            try:
                window_width = self.width() if self.width() > 0 else 800
                window_height = self.height() if self.height() > 0 else 600
                self.setGeometry(target_x, target_y, window_width, window_height)
            except Exception as e2:
                logger.error(f"白露魔法出错: Linux窗口定位备用方案也失败了呢～ {e2}")
    
    def _delayed_position_linux(self, target_x, target_y):
        """(^・ω・^ ) 白露的Linux延迟定位魔法！
        给窗口管理器一些时间处理后，再次尝试定位窗口～
        这是Linux环境下的最后保障哦！(๑•̀ㅂ•́)ow✧"""
        try:
            # 再次尝试move
            self.move(target_x, target_y)
            
            # 检查是否成功
            current_x, current_y = self.x(), self.y()
            if abs(current_x - target_x) > 10 or abs(current_y - target_y) > 10:
                # 仍然失败，使用setGeometry
                window_width = self.width() if self.width() > 0 else 800
                window_height = self.height() if self.height() > 0 else 600
                self.setGeometry(target_x, target_y, window_width, window_height)
                
            logger.debug(f"白露魔法: Linux延迟定位完成，当前位置({self.x()}, {self.y()})～ ")
            
        except Exception as e:
            logger.error(f"白露魔法出错: Linux延迟定位失败了呢～ {e}")
    
    def _apply_window_visibility_settings(self):
        """(^・ω・^ ) 白露的窗口显示魔法！
        根据用户保存的设置决定窗口是否自动显示～
        如果上次设置为显示，启动时就会自动出现哦！(๑•̀ㅂ•́)ow✧"""
        try:
            settings = self.config_manager.load_settings()
            if settings.get('toggle_window') == 'show':
                self.show()
                logger.info("白露魔法: 根据设置自动显示主窗口～ ")
        except Exception as e:
            logger.error(f"白露魔法出错: 加载窗口显示设置失败了呢～ {e}")

    def check_updates_async(self):
        """(ﾟДﾟ≡ﾟдﾟ) 星野的太空巡逻队出发！
        正在异步执行版本侦察任务喵～ 不会阻塞主线程哦！
        发现新版本时会立刻拉响警报通知用户喵！🚀✨"""
        self.update_checker.check_for_updates()
        logger.info("星野指令: 更新检查任务已安排，开始扫描宇宙寻找新版本～ ")

    def createSubInterface(self):
        """(^・ω・^ ) 白露的魔法建筑师开工啦！
        正在搭建子界面导航系统，就像建造一座功能齐全的魔法城堡～
        每个功能模块都是城堡的房间，马上就能入住使用啦！🏰✨"""
        # 创建设置界面
        self.settingInterface = settings_Window(self)
        self.settingInterface.setObjectName("settingInterface")
        logger.debug("白露建筑: 设置界面房间已建成～ ")

        # 创建关于界面
        self.about_settingInterface = about(self)
        self.about_settingInterface.setObjectName("about_settingInterface")
        logger.debug("白露建筑: 关于界面房间已建成～ ")
        
        # 根据设置决定是否创建"历史交接设置"界面
        try:
            settings_path = path_manager.get_settings_path('custom_settings.json')
            with open_file(settings_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                sidebar_settings = settings.get('sidebar', {})
                history_side = sidebar_settings.get('main_window_history_switch', 1)
                
                if history_side != 2:  # 不为"不显示"时才创建界面
                    # 创建历史交接设置界面
                    self.history_handoff_settingInterface = history_handoff_setting(self)
                    self.history_handoff_settingInterface.setObjectName("history_handoff_settingInterface")
                    logger.debug("白露建筑: 历史交接设置界面房间已建成～ ")
                else:
                    logger.debug("白露建筑: '历史交接设置'界面已设置为不创建～ ")
                    self.history_handoff_settingInterface = None
        except Exception as e:
            logger.error(f"白露建筑出错: 读取历史交接设置界面设置失败了呢～ {e}, 默认创建界面")
            # 创建历史交接设置界面
            self.history_handoff_settingInterface = history_handoff_setting(self)
            self.history_handoff_settingInterface.setObjectName("history_handoff_settingInterface")
            logger.debug("白露建筑: 历史交接设置界面房间已建成～ ")
        
        # 根据设置决定是否创建"背单词"界面
        try:
            settings_path = path_manager.get_settings_path('custom_settings.json')
            with open_file(settings_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                sidebar_settings = settings.get('sidebar', {})
                vocabulary_side = sidebar_settings.get('main_window_side_switch', 2)
                
                if vocabulary_side != 2:  # 不为"不显示"时才创建界面
                    # 创建背单词界面
                    self.vocabulary_learningInterface = vocabulary_learning(self)
                    self.vocabulary_learningInterface.setObjectName("vocabulary_learningInterface")
                    logger.debug("白露建筑: 背单词界面房间已建成～ ")
                else:
                    logger.debug("白露建筑: '背单词'界面已设置为不创建～ ")
                    self.vocabulary_learningInterface = None
        except Exception as e:
            logger.error(f"白露建筑出错: 读取背单词界面设置失败了呢～ {e}, 默认不创建界面")
            # 创建背单词界面
            self.vocabulary_learningInterface = None

        # 根据设置决定是否创建"抽人"界面
        try:
            settings_path = path_manager.get_settings_path('custom_settings.json')
            with open_file(settings_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                sidebar_settings = settings.get('sidebar', {})
                pumping_floating_side = sidebar_settings.get('pumping_floating_side', 0)
                
                if pumping_floating_side != 2:  # 不为"不显示"时才创建界面
                    # 创建抽人界面（主界面）
                    self.pumping_peopleInterface = pumping_people(self)
                    self.pumping_peopleInterface.setObjectName("pumping_peopleInterface")
                    logger.debug("白露建筑: 抽人界面房间已建成～ ")
                else:
                    logger.debug("白露建筑: '抽人'界面已设置为不创建～ ")
                    self.pumping_peopleInterface = None
        except Exception as e:
            logger.error(f"白露建筑出错: 读取抽人界面设置失败了呢～ {e}, 默认创建界面")
            # 创建抽人界面（主界面）
            self.pumping_peopleInterface = pumping_people(self)
            self.pumping_peopleInterface.setObjectName("pumping_peopleInterface")
            logger.debug("白露建筑: 抽人界面房间已建成～ ")

        # 根据设置决定是否创建"抽奖"界面
        try:
            settings_path = path_manager.get_settings_path('custom_settings.json')
            with open_file(settings_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                sidebar_settings = settings.get('sidebar', {})
                pumping_reward_side = sidebar_settings.get('pumping_reward_side', 0)
                
                if pumping_reward_side != 2:  # 不为"不显示"时才创建界面
                    # 创建抽奖界面
                    self.pumping_rewardInterface = pumping_reward(self)
                    self.pumping_rewardInterface.setObjectName("pumping_rewardInterface")
                    logger.debug("白露建筑: 抽奖界面房间已建成～ ")
                else:
                    logger.debug("白露建筑: '抽奖'界面已设置为不创建～ ")
                    self.pumping_rewardInterface = None
        except Exception as e:
            logger.error(f"白露建筑出错: 读取抽奖界面设置失败了呢～ {e}, 默认创建界面")
            # 创建抽奖界面
            self.pumping_rewardInterface = pumping_reward(self)
            self.pumping_rewardInterface.setObjectName("pumping_rewardInterface")
            logger.debug("白露建筑: 抽奖界面房间已建成～ ")

        # 初始化导航系统
        self.initNavigation()
        logger.info("白露建筑: 所有子界面和导航系统已完工！城堡可以正式对外开放啦～ ")

    def initNavigation(self):
        """(^・ω・^ ) 白露的魔法导航系统启动！
        根据用户设置构建个性化菜单导航～ 就像魔法地图一样清晰！
        确保每个功能模块都有明确路标，不会让用户迷路哦！🧭✨"""
        try:
            settings_path = path_manager.get_settings_path('custom_settings.json')
            with open_file(settings_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                sidebar_settings = settings.get('sidebar', {})
                logger.debug("白露导航: 已读取导航配置，准备构建个性化菜单～ ")

                # 根据设置决定"抽人"界面位置
                pumping_floating_side = sidebar_settings.get('pumping_floating_side', 0)
                if pumping_floating_side == 1:
                    if self.pumping_peopleInterface is not None:
                        self.addSubInterface(self.pumping_peopleInterface, get_theme_icon("ic_fluent_people_community_20_filled"), '抽人', position=NavigationItemPosition.BOTTOM)
                        logger.debug("白露导航: '抽人'界面已放置在底部导航栏～ ")
                    else:
                        logger.debug("白露导航: '抽人'界面未创建，无法添加到导航栏～ ")
                elif pumping_floating_side == 2:
                    logger.debug("白露导航: '抽人'界面已设置为不显示～ ")
                else:
                    if self.pumping_peopleInterface is not None:
                        self.addSubInterface(self.pumping_peopleInterface, get_theme_icon("ic_fluent_people_community_20_filled"), '抽人', position=NavigationItemPosition.TOP)
                        logger.debug("白露导航: '抽人'界面已放置在顶部导航栏～ ")
                    else:
                        logger.debug("白露导航: '抽人'界面未创建，无法添加到导航栏～ ")

                # 根据设置决定"抽奖"界面位置
                pumping_reward_side = sidebar_settings.get('pumping_reward_side', 0)
                if pumping_reward_side == 1:
                    if self.pumping_rewardInterface is not None:
                        self.addSubInterface(self.pumping_rewardInterface, get_theme_icon("ic_fluent_reward_20_filled"), '抽奖', position=NavigationItemPosition.BOTTOM)
                        logger.debug("白露导航: '抽奖'界面已放置在底部导航栏～ ")
                    else:
                        logger.debug("白露导航: '抽奖'界面未创建，无法添加到导航栏～ ")
                elif pumping_reward_side == 2:
                    logger.debug("白露导航: '抽奖'界面已设置为不显示～ ")
                else:
                    if self.pumping_rewardInterface is not None:
                        self.addSubInterface(self.pumping_rewardInterface, get_theme_icon("ic_fluent_reward_20_filled"), '抽奖', position=NavigationItemPosition.TOP)
                        logger.debug("白露导航: '抽奖'界面已放置在顶部导航栏～ ")
                    else:
                        logger.debug("白露导航: '抽奖'界面未创建，无法添加到导航栏～ ")

        except FileNotFoundError as e:
            logger.error(f"白露导航出错: 配置文件找不到啦～ {e}, 使用默认顶部导航布局")
            if self.pumping_peopleInterface is not None:
                self.addSubInterface(self.pumping_peopleInterface, get_theme_icon("ic_fluent_people_community_20_filled"), '抽人', position=NavigationItemPosition.TOP)
            if self.pumping_rewardInterface is not None:
                self.addSubInterface(self.pumping_rewardInterface, get_theme_icon("ic_fluent_reward_20_filled"), '抽奖', position=NavigationItemPosition.TOP)

        try:
            # 添加单词PK界面导航项
            vocabulary_side = sidebar_settings.get('main_window_side_switch', 2)
            if vocabulary_side == 1:
                if self.vocabulary_learningInterface is not None:
                    self.addSubInterface(self.vocabulary_learningInterface, get_theme_icon("ic_fluent_text_whole_word_20_filled"), '单词PK', position=NavigationItemPosition.BOTTOM)
                    logger.debug("白露导航: '单词PK'界面已放置在底部导航栏～ ")
                else:
                    logger.debug("白露导航: '单词PK'界面未创建，无法添加到导航栏～ ")
            elif vocabulary_side == 2:
                logger.debug("白露导航: '单词PK'界面已设置为不显示～ ")
            else:
                if self.vocabulary_learningInterface is not None:
                    self.addSubInterface(self.vocabulary_learningInterface, get_theme_icon("ic_fluent_text_whole_word_20_filled"), '单词PK', position=NavigationItemPosition.TOP)
                    logger.debug("白露导航: '单词PK'界面已放置在顶部导航栏～ ")
                else:
                    logger.debug("白露导航: '单词PK'界面未创建，无法添加到导航栏～ ")
        except Exception as e:
            if self.vocabulary_learningInterface is not None:
                self.addSubInterface(self.vocabulary_learningInterface, get_theme_icon("ic_fluent_text_whole_word_20_filled"), '单词PK', position=NavigationItemPosition.BOTTOM)
            logger.error(f"白露导航出错: 加载单词PK界面导航项失败了呢～ {e}")

        # 添加历史记录导航项
        try:
            history_side = sidebar_settings.get('main_window_history_switch', 1)
            if history_side == 1:
                if self.history_handoff_settingInterface is not None:
                    # 为历史记录导航项添加点击事件处理器
                    history_item = self.addSubInterface(self.history_handoff_settingInterface, get_theme_icon("ic_fluent_chat_history_20_filled"), '历史记录', position=NavigationItemPosition.BOTTOM)
                    # 点击历史记录导航项时切换到历史记录界面
                    history_item.clicked.connect(lambda: self.switchTo(self.history_handoff_settingInterface))
                    logger.debug("白露导航: '历史记录'导航项已放置在底部导航栏～ ")
                else:
                    logger.debug("白露导航: '历史记录'界面未创建，无法添加到导航栏～ ")
            elif history_side == 2:
                logger.debug("白露导航: '历史记录'导航项已设置为不显示～ ")
            else:
                if self.history_handoff_settingInterface is not None:
                    # 为历史记录导航项添加点击事件处理器
                    history_item = self.addSubInterface(self.history_handoff_settingInterface, get_theme_icon("ic_fluent_chat_history_20_filled"), '历史记录', position=NavigationItemPosition.TOP)
                    # 点击历史记录导航项时切换到历史记录界面
                    history_item.clicked.connect(lambda: self.switchTo(self.history_handoff_settingInterface))
                    logger.debug("白露导航: '历史记录'导航项已放置在顶部导航栏～ ")
                else:
                    logger.debug("白露导航: '历史记录'界面未创建，无法添加到导航栏～ ")
        except Exception as e:
            logger.error(f"白露导航出错: 加载历史记录导航项失败了呢～ {e}")
            # 默认添加到底部导航栏
            if self.history_handoff_settingInterface is not None:
                history_item = self.addSubInterface(self.history_handoff_settingInterface, get_theme_icon("ic_fluent_chat_history_20_filled"), '历史记录', position=NavigationItemPosition.BOTTOM)
                # 点击历史记录导航项时切换到历史记录界面
                history_item.clicked.connect(lambda: self.switchTo(self.history_handoff_settingInterface))

        self.addSubInterface(self.about_settingInterface, get_theme_icon("ic_fluent_info_20_filled"), '关于', position=NavigationItemPosition.BOTTOM)

        try:
            settings_side = sidebar_settings.get('show_settings_icon', 1)
            if settings_side == 1:
                # 创建一个空的设置界面占位符，用于导航栏
                self.settings_placeholder = QWidget()
                self.settings_placeholder.setObjectName("settings_placeholder")
                settings_item = self.addSubInterface(self.settings_placeholder, get_theme_icon("ic_fluent_settings_20_filled"), '设置', position=NavigationItemPosition.BOTTOM)
                # 为导航项添加点击事件处理器，调用show_setting_interface方法
                settings_item.clicked.connect(self.show_setting_interface)
                settings_item.clicked.connect(lambda: self.switchTo(self.pumping_peopleInterface))
                logger.debug("白露导航: '设置'图标已放置在底部导航栏～ ")
            elif settings_side == 2:
                logger.debug("白露导航: '设置'图标已设置为不显示～ ")
            else:
                # 创建一个空的设置界面占位符，用于导航栏
                self.settings_placeholder = QWidget()
                self.settings_placeholder.setObjectName("settings_placeholder")
                settings_item = self.addSubInterface(self.settings_placeholder, get_theme_icon("ic_fluent_settings_20_filled"), '设置', position=NavigationItemPosition.TOP)
                # 为导航项添加点击事件处理器，调用show_setting_interface方法
                settings_item.clicked.connect(self.show_setting_interface)
                settings_item.clicked.connect(lambda: self.switchTo(self.pumping_peopleInterface))
                logger.debug("白露导航: '设置'图标已放置在顶部导航栏～ ")
        except Exception as e:
            logger.error(f"白露导航出错: 加载设置图标失败了呢～ {e}")
            if sidebar_settings.get('show_settings_icon', True):
                # 创建一个空的设置界面占位符，用于导航栏
                self.settings_placeholder = QWidget()
                self.settings_placeholder.setObjectName("settings_placeholder")
                settings_item = self.addSubInterface(self.settings_placeholder, get_theme_icon("ic_fluent_settings_20_filled"), '设置', position=NavigationItemPosition.BOTTOM)
                # 为导航项添加点击事件处理器，调用show_setting_interface方法
                settings_item.clicked.connect(self.show_setting_interface)
                settings_item.clicked.connect(lambda: self.switchTo(self.pumping_peopleInterface))
        
        logger.info("白露导航: 所有导航项已布置完成，导航系统可以正常使用啦～ ")

    def closeEvent(self, event):
        """(ﾟДﾟ≡ﾟдﾟ) 星野的安全防御系统启动！
        检测到窗口关闭事件！已成功拦截喵～ 
        程序将撤退到系统托盘继续潜伏运行喵！(=｀ω´=)"""
        self.hide()
        event.ignore()
        self.save_window_size()
        logger.info("星野防御: 窗口关闭事件已拦截，程序已转入后台运行～ ")

    def resizeEvent(self, event):
        """(ﾟДﾟ≡ﾟдﾟ) 星野的尺寸感应系统触发！
        检测到窗口大小变化喵～ 正在启动尺寸记录倒计时！
        500毫秒内如果不再变化就会自动保存新尺寸喵～(=｀ω´=)"""
        self.resize_timer.start(500)
        super().resizeEvent(event)

    def save_window_size(self):
        """(^・ω・^ ) 白露的尺寸保管员上线！
        正在用魔法记录当前窗口尺寸～ 就像用相机拍照存档一样！
        下次启动时会自动恢复到这个大小，不用重新调整啦～ ✨"""
        if not self.isMaximized():
            self.config_manager.save_window_size(self.width(), self.height())
            logger.info(f"白露存档: 已保存窗口尺寸为{self.width()}x{self.height()}像素～ ")

    def update_focus_mode(self, mode):
        """(^・ω・^ ) 白露的焦点模式调节器！
        已成功切换到{mode}档魔法模式～ 就像调节台灯亮度一样简单！
        不同档位会触发不同的自动隐藏魔法，数值越大隐藏速度越快哦～ ✨"""
        self.focus_mode = mode
        self.last_focus_time = QDateTime.currentDateTime()
        # logger.debug(f"白露调节: 焦点模式已切换到{mode}档～ ")

        if mode < len(self.FOCUS_TIMEOUT_MAP):
            self.focus_timeout = self.FOCUS_TIMEOUT_MAP[mode]
            # logger.debug(f"白露调节: 自动隐藏阈值已设置为{self.focus_timeout}毫秒～ ")

    def update_focus_time(self, time):
        """(^・ω・^ ) 白露的时间魔法更新！
        焦点检查时间间隔已调整为{time}档～ 就像给闹钟设置新的提醒周期！
        现在每{self.FOCUS_TIMEOUT_TIME[time] if time < len(self.FOCUS_TIMEOUT_TIME) else 0}毫秒检查一次窗口焦点哦～ ⏰"""
        self.focus_time = time
        self.last_focus_time = QDateTime.currentDateTime()
        # logger.debug(f"白露计时: 焦点检查时间已更新到{time}档～ ")

        if time < len(self.FOCUS_TIMEOUT_TIME):
            self.focus_timeout = self.FOCUS_TIMEOUT_TIME[time]
            self.focus_timer.start(self.focus_timeout)
            # logger.debug(f"白露计时: 检查间隔已设置为{self.focus_timeout}毫秒～ ")
        else:
            self.focus_timer.start(0)
            # logger.debug(f"白露计时: 检查间隔已设置为连续模式～ ")

    def check_focus_timeout(self):
        """(ﾟДﾟ≡ﾟдﾟ) 星野的焦点监视器启动！
        正在扫描窗口焦点状态喵～ {self.focus_timeout}毫秒无操作将触发自动隐藏魔法！
        不要走开太久哦，否则我会躲起来喵～(=｀ω´=)"""
        if self.focus_mode == 0:  # 不关闭模式
            return

        if not self.isActiveWindow() and not self.isMinimized():
            elapsed = self.last_focus_time.msecsTo(QDateTime.currentDateTime())
            timeout = self.FOCUS_TIMEOUT_MAP[self.focus_mode]
            # logger.debug(f"星野监视: 窗口已闲置{elapsed}毫秒，阈值为{timeout}毫秒～ ")

            if self.focus_mode == 1:  # 直接关闭模式
                self.hide()
                # logger.info("星野行动: 焦点模式1触发，窗口已自动隐藏～ ")
            elif elapsed >= timeout:
                self.hide()
                # logger.info(f"星野行动: 窗口闲置超过{timeout}毫秒，已自动隐藏～ ")
        else:
            self.last_focus_time = QDateTime.currentDateTime()
            # logger.debug("星野监视: 检测到用户活动，重置闲置计时器～ ")

    def stop_focus_timer(self):
        """星野守卫：
        焦点检测计时器已停止！
        窗口不会自动隐藏啦喵～(=｀ω´=)"""
        self.focus_timer.stop()

    def showEvent(self, event):
        """白露唤醒：
        窗口显示时重置焦点时间
        开始监控用户活动哦～(>^ω^<)"""
        super().showEvent(event)
        self.last_focus_time = QDateTime.currentDateTime()

    def focusInEvent(self, event):
        """星野注意：
        窗口获得焦点！
        重置闲置计时器喵～(ฅ´ω`ฅ)"""
        super().focusInEvent(event)
        self.last_focus_time = QDateTime.currentDateTime()

    def show_about_tab(self):
        """白露向导：
        正在导航到关于页面
        这里可以查看软件版本和作者信息哦～(>^ω^<)"""
        if self.isMinimized():
            self.showNormal()
        else:
            self.show()
            self.activateWindow()
            self.raise_()
        self.switchTo(self.about_settingInterface)

    def start_cleanup(self):
        """(^・ω・^ ) 白露的启动清理魔法！
        软件启动时清理上次遗留的临时抽取记录文件喵～
        根据抽选模式决定是否需要清理，保持系统整洁！"""
        try:
            settings_path = path_manager.get_settings_path('Settings.json')
            with open_file(settings_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                pumping_people_draw_mode = settings['pumping_people']['draw_mode']
                logger.debug(f"星野侦察: 抽选模式为{pumping_people_draw_mode}，准备执行对应清理方案～ ")

        except Exception as e:
            pumping_people_draw_mode = 1
            logger.error(f"星野魔法出错: 加载抽选模式设置失败了喵～ {e}, 使用默认:不重复抽取(直到软件重启)模式")

        import glob
        temp_dir = path_manager.get_temp_path('')
        ensure_dir(temp_dir)

        if pumping_people_draw_mode == 1:  # 不重复抽取(直到软件重启)
            if path_manager.file_exists(temp_dir):
                for file in glob.glob(f"{temp_dir}/until_the_reboot_*.json"):
                    try:
                        os.remove(file)
                        logger.info(f"星野清理: 已删除临时抽取记录文件: {file}")
                    except Exception as e:
                        logger.error(f"星野清理失败: 删除临时文件出错喵～ {e}")



    def toggle_window(self):
        """(^・ω・^ ) 白露的窗口切换魔法！
        显示→隐藏→显示，像捉迷藏一样好玩喵～
        切换时会自动激活抽人界面，方便用户继续操作！"""  
        if self.config_manager.get_foundation_setting('topmost_switch'):
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)

        if self.isVisible():
            self.hide()
            logger.info("星野魔法: 主窗口已隐藏～ ")
            if self.isMinimized():
                self.showNormal()
                self.activateWindow()
                self.raise_()
        else:
            if self.isMinimized():
                self.showNormal()
                self.activateWindow()
                self.raise_()
            else:
                self.show()
                self.activateWindow()
                self.raise_()
            logger.info("星野魔法: 主窗口已显示～ ")
        self.switchTo(self.pumping_peopleInterface)

    def calculate_menu_position(self, menu):
        """白露定位系统：
        正在计算托盘菜单最佳显示位置
        确保菜单不会超出屏幕边界哦～(๑•̀ㅂ•́)ow✧"""
        screen = QApplication.primaryScreen().availableGeometry()
        menu_size = menu.sizeHint()

        cursor_pos = QCursor.pos()

        x = cursor_pos.x() + 20
        y = cursor_pos.y() - menu_size.height()

        if x + menu_size.width() > screen.right():
            x = screen.right() - menu_size.width()
        if y < screen.top():
            y = screen.top()

        return QPoint(x, y)

    def close_window_secrandom(self):
        """(^・ω・^ ) 白露的终极安全检查！
        检测到退出请求！需要通过密码验证才能离开基地喵！
        这是最高级别的安全防御，不能让坏人随便入侵喵！🔒✨"""
        try:
            enc_settings_path = path_manager.get_enc_set_path()
            with open_file(enc_settings_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                logger.debug("星野安检: 正在读取安全设置，准备执行退出验证～ ")

                if settings.get('hashed_set', {}).get('start_password_enabled', False) == True:
                    if settings.get('hashed_set', {}).get('exit_verification_enabled', False) == True:
                        from app.common.password_dialog import PasswordDialog
                        dialog = PasswordDialog(self)
                        if dialog.exec_() != QDialog.Accepted:
                            logger.warning("星野安检: 用户取消退出程序操作，安全防御已解除～ ")
                            return
        except Exception as e:
            logger.error(f"星野安检失败: 密码验证系统出错喵～ {e}")
            return

        logger.info("星野撤退: 安全验证通过，开始执行完全退出程序流程～ ")
        self.hide()
        if hasattr(self, 'levitation_window'):
            self.levitation_window.hide()
            logger.debug("星野撤退: 悬浮窗已隐藏～ ")
            
        if hasattr(self, 'focus_timer'):
            self.stop_focus_timer()
            logger.debug("星野撤退: 焦点计时器已停止～ ")

        if hasattr(self, 'usb_detection_timer'):
            self.usb_detection_timer.stop()
            logger.debug("星野撤退: USB绑定已关闭～ ")

        # 停止resize_timer以优化CPU占用
        if hasattr(self, 'resize_timer') and self.resize_timer.isActive():
            self.resize_timer.stop()
            logger.debug("星野撤退: resize_timer已停止～ ")

        # 停止托盘菜单定时器
        if hasattr(self, 'tray_manager') and hasattr(self.tray_manager, 'menu_timer'):
            if self.tray_manager.menu_timer.isActive():
                self.tray_manager.menu_timer.stop()
                logger.debug("星野撤退: 托盘菜单定时器已停止～ ")

        # 停止USB监控线程
        if hasattr(self, 'settingInterface') and self.settingInterface:
            if hasattr(self.settingInterface, 'usb_monitor_thread') and self.settingInterface.usb_monitor_thread:
                # 先断开信号连接，避免在线程停止过程中触发信号
                self.settingInterface.usb_monitor_thread.usb_removed.disconnect()
                # 停止线程并等待完全停止
                self.settingInterface.usb_monitor_thread.stop()
                # 等待一小段时间确保线程完全停止
                if self.settingInterface.usb_monitor_thread.isRunning():
                    self.settingInterface.usb_monitor_thread.wait(500)  # 等待最多500ms
                self.settingInterface.usb_monitor_thread = None
                logger.debug("星野撤退: USB监控线程已停止～ ")

        if hasattr(self, 'server'):
            self.server.close()
            logger.debug("星野撤退: IPC服务器已关闭～ ")

        # 停止更新检查
        if hasattr(self, 'update_checker') and self.update_checker:
            self.update_checker.stop_checking()
            logger.debug("星野撤退: 更新检查已停止～ ")
            
        # 关闭共享内存
        if hasattr(self, 'shared_memory'):
            try:
                self.shared_memory.detach()
                if self.shared_memory.isAttached():
                    self.shared_memory.detach()
                logger.debug("星野撤退: 共享内存已完全释放～ ")
            except Exception as e:
                logger.error(f"星野撤退: 共享内存释放出错喵～ {e}")

        logger.debug("星野撤退: 所有资源已成功释放，程序即将退出～ ")
        
        # 正确关闭日志系统
        try:
            # 移除所有日志处理器
            loguru.logger.remove()
            logger.info("星野撤退: 日志系统已安全关闭～ ")
        except Exception as e:
            logger.error(f"星野撤退: 日志系统关闭出错喵～ {e}")

        # 确保完全退出应用程序
        QApplication.quit()
        sys.exit(0)

    def restart_app(self):
        try:
            enc_settings_path = path_manager.get_enc_set_path()
            with open_file(enc_settings_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                if settings.get('hashed_set', {}).get('start_password_enabled', False) == True:
                    if settings.get('hashed_set', {}).get('restart_verification_enabled', False) == True:
                        from app.common.password_dialog import PasswordDialog
                        dialog = PasswordDialog(self)
                        if dialog.exec_() != QDialog.Accepted:
                            logger.warning("用户取消重启操作")
                            return
        except Exception as e:
            logger.error(f"密码验证过程出错: {e}")
            return

        logger.info("星野重启: 安全验证通过，开始执行完全重启程序流程～ ")
        
        # 隐藏所有窗口
        self.hide()
        if hasattr(self, 'levitation_window'):
            self.levitation_window.hide()
            logger.debug("星野重启: 悬浮窗已隐藏～ ")
        
        # 彻底清理设置界面，防止重启后嵌套问题
        if hasattr(self, 'settingInterface') and self.settingInterface:
            try:
                # 先断开所有信号连接
                if hasattr(self.settingInterface, 'usb_monitor_thread') and self.settingInterface.usb_monitor_thread:
                    self.settingInterface.usb_monitor_thread.usb_removed.disconnect()
                
                # 关闭设置界面
                self.settingInterface.close()
                self.settingInterface = None
                logger.debug("星野重启: 设置界面已完全清理～ ")
            except Exception as e:
                logger.error(f"星野重启: 清理设置界面时出错喵～ {e}")
        
        # 停止所有计时器
        if hasattr(self, 'focus_timer'):
            self.stop_focus_timer()
            logger.debug("星野重启: 焦点计时器已停止～ ")
    
        # 停止USB检测计时器
        if hasattr(self, 'usb_detection_timer'):
            self.usb_detection_timer.stop()
            logger.debug("星野重启: USB绑定已关闭～ ")

        # 停止resize_timer以优化CPU占用
        if hasattr(self, 'resize_timer') and self.resize_timer.isActive():
            self.resize_timer.stop()
            logger.debug("星野重启: resize_timer已停止～ ")

        # 停止托盘菜单定时器
        if hasattr(self, 'tray_manager') and hasattr(self.tray_manager, 'menu_timer'):
            if self.tray_manager.menu_timer.isActive():
                self.tray_manager.menu_timer.stop()
                logger.debug("星野重启: 托盘菜单定时器已停止～ ")
                
        # 停止USB监控线程
        if hasattr(self, 'settingInterface') and self.settingInterface:
            if hasattr(self.settingInterface, 'usb_monitor_thread') and self.settingInterface.usb_monitor_thread:
                # 先断开信号连接，避免在线程停止过程中触发信号
                self.settingInterface.usb_monitor_thread.usb_removed.disconnect()
                # 停止线程并等待完全停止
                self.settingInterface.usb_monitor_thread.stop()
                # 等待一小段时间确保线程完全停止
                if self.settingInterface.usb_monitor_thread.isRunning():
                    self.settingInterface.usb_monitor_thread.wait(500)  # 等待最多500ms
                self.settingInterface.usb_monitor_thread = None
                logger.debug("星野重启: USB监控线程已停止～ ")
        
        # 关闭IPC服务器
        if hasattr(self, 'server'):
            self.server.close()
            logger.debug("星野重启: IPC服务器已关闭～ ")
        
        # 停止更新检查
        if hasattr(self, 'update_checker') and self.update_checker:
            self.update_checker.stop_checking()
            logger.debug("星野重启: 更新检查已停止～ ")

        # 关闭共享内存
        if hasattr(self, 'shared_memory'):
            try:
                self.shared_memory.detach()
                if self.shared_memory.isAttached():
                    self.shared_memory.detach()
                logger.info("星野重启: 共享内存已完全释放～ ")
            except Exception as e:
                logger.error(f"星野重启: 共享内存释放出错喵～ {e}")
        
        # 重置密码验证状态，防止重启后打不开设置
        try:
            enc_settings_path = path_manager.get_enc_set_path()
            with open_file(enc_settings_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
            if 'hashed_set' in settings and 'verification_start' in settings['hashed_set']:
                settings['hashed_set']['verification_start'] = False
                with open_file(enc_settings_path, 'w', encoding='utf-8') as f:
                    json.dump(settings, f, ensure_ascii=False, indent=4)
                logger.debug("星野重启: 密码验证状态已重置～ ")
        except Exception as e:
            logger.error(f"星野重启: 重置密码验证状态时出错喵～ {e}")
        
        # 给系统更多时间清理资源
        time.sleep(1.0)
        
        # 启动新进程，过滤掉可能导致问题的参数
        try:
            # 获取当前工作目录
            working_dir = os.getcwd()
            
            # 过滤命令行参数，移除可能导致问题的参数
            filtered_args = [arg for arg in sys.argv if not arg.startswith('--')]
            
            # 使用更安全的启动方式
            startup_info = subprocess.STARTUPINFO()
            startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            # 启动新进程
            subprocess.Popen(
                [sys.executable] + filtered_args,
                cwd=working_dir,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
                startupinfo=startup_info
            )
            logger.info("星野重启: 新进程已成功启动～ ")
        except Exception as e:
            logger.error(f"星野重启: 启动新进程失败喵～ {e}")
            return

        # 正确关闭日志系统
        try:
            # 移除所有日志处理器
            loguru.logger.remove()
            logger.info("星野重启: 日志系统已安全关闭～ ")
        except Exception as e:
            logger.error(f"星野重启: 日志系统关闭出错喵～ {e}")
        
        # 完全退出当前应用程序
        QApplication.quit()
        sys.exit(0)

    def show_setting_interface(self):
        """白露设置向导：
        正在打开设置界面
        小心不要乱动高级选项哦～(^・ω・^ )"""
        try:
            enc_settings_path = path_manager.get_enc_set_path()
            with open_file(enc_settings_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                if settings.get('hashed_set', {}).get('start_password_enabled', False):
                    from app.common.password_dialog import PasswordDialog
                    dialog = PasswordDialog(self)
                    if dialog.exec_() != QDialog.Accepted:
                        logger.warning("用户取消打开设置界面操作")
                        return
        except Exception as e:
            logger.error(f"密码验证失败: {e}")

        try:
            enc_settings_path = path_manager.get_enc_set_path()
            with open_file(enc_settings_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
            settings['hashed_set']['verification_start'] = True
            with open_file(enc_settings_path, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.error(f"写入verification_start失败: {e}")

        if not hasattr(self, 'settingInterface') or not self.settingInterface:
            self.settingInterface = settings_Window(self)

        if self.settingInterface.isVisible() and not self.settingInterface.isMinimized():
            self.settingInterface.showNormal() 
            self.settingInterface.activateWindow()
            self.settingInterface.raise_()
        else:
            if self.settingInterface.isMinimized():
                self.settingInterface.showNormal()
                self.settingInterface.activateWindow()
                self.settingInterface.raise_()
            else:
                self.settingInterface.show()
                self.settingInterface.activateWindow()
                self.settingInterface.raise_()

    def toggle_levitation_window(self):
        """星野悬浮控制：
        浮窗显示状态切换中！
        注意不要让它挡住重要内容喵～(ฅ´ω`ฅ)"""
        try:
            enc_settings_path = path_manager.get_enc_set_path()
            with open_file(enc_settings_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                if settings.get('hashed_set', {}).get('start_password_enabled', False) == True:
                    if settings.get('hashed_set', {}).get('show_hide_verification_enabled', False) == True:
                        from app.common.password_dialog import PasswordDialog
                        dialog = PasswordDialog(self)
                        if dialog.exec_() != QDialog.Accepted:
                            logger.warning("用户取消暂时切换浮窗显示/隐藏状态操作")
                            return
        except Exception as e:
            logger.error(f"密码验证失败: {e}")
            return

        if not hasattr(self, 'levitation_window') or not self.levitation_window:
            self.levitation_window.show()
        elif self.levitation_window.isVisible():
            self.levitation_window.hide()
        else:
            self.levitation_window.show()
            self.levitation_window.activateWindow()
            self.levitation_window.raise_()

    @pyqtSlot()
    def _show_direct_extraction_window_from_shortcut(self):
        """星野闪抽快捷键处理：
        通过全局快捷键触发闪抽界面！
        确保在主线程中执行UI操作喵～(ฅ´ω`ฅ)"""
        try:
            # 检查levitation_window是否存在，不存在则创建
            if not hasattr(self, 'levitation_window') or not self.levitation_window:
                self.levitation_window = LevitationWindow()
            
            # 调用LevitationWindow的_show_direct_extraction_window方法
            self.levitation_window._show_direct_extraction_window()
            logger.info("星野闪抽: 通过快捷键成功触发闪抽界面～ ")
        except Exception as e:
            logger.error(f"星野闪抽: 快捷键触发闪抽界面失败喵～ {e}")

    @pyqtSlot()
    def _show_pumping_interface_from_shortcut(self):
        """抽人界面快捷键处理：
        通过全局快捷键打开抽人界面！
        确保在主线程中执行UI操作喵～(ฅ´ω`ฅ)"""
        try:
            # 确保主窗口可见
            if not self.isVisible():
                self.show()
                self.activateWindow()
                self.raise_()
            
            # 切换到抽人界面
            self.switchTo(self.pumping_peopleInterface)
            logger.info("抽人界面: 通过快捷键成功打开抽人界面～ ")
        except Exception as e:
            logger.error(f"抽人界面: 快捷键打开抽人界面失败喵～ {e}")

    @pyqtSlot()
    def _show_reward_interface_from_shortcut(self):
        """抽奖界面快捷键处理：
        通过全局快捷键打开抽奖界面！
        确保在主线程中执行UI操作喵～(ฅ´ω`ฅ)"""
        try:
            # 确保主窗口可见
            if not self.isVisible():
                self.show()
                self.activateWindow()
                self.raise_()
            
            # 切换到抽奖界面
            self.switchTo(self.pumping_rewardInterface)
            logger.info("抽奖界面: 通过快捷键成功打开抽奖界面～ ")
        except Exception as e:
            logger.error(f"抽奖界面: 快捷键打开抽奖界面失败喵～ {e}")

    @pyqtSlot()
    def _trigger_pumping_from_shortcut(self):
        """抽人快捷键处理：
        通过全局快捷键触发抽人操作！
        确保在主线程中执行UI操作喵～(ฅ´ω`ฅ)"""
        try:
            # 确保主窗口可见
            if not self.isVisible():
                self.show()
                self.activateWindow()
                self.raise_()
            
            # 切换到抽人界面
            self.switchTo(self.pumping_peopleInterface)
            
            # 触发抽人操作
            self.pumping_peopleInterface.start_draw()
            logger.info("抽人: 通过快捷键成功触发抽人操作～ ")
        except Exception as e:
            logger.error(f"抽人: 快捷键触发抽人操作失败喵～ {e}")

    @pyqtSlot()
    def _trigger_reward_from_shortcut(self):
        """抽奖快捷键处理：
        通过全局快捷键触发抽奖操作！
        确保在主线程中执行UI操作喵～(ฅ´ω`ฅ)"""
        try:
            # 确保主窗口可见
            if not self.isVisible():
                self.show()
                self.activateWindow()
                self.raise_()
            
            # 切换到抽奖界面
            self.switchTo(self.pumping_rewardInterface)
            
            # 触发抽奖操作
            self.pumping_rewardInterface.start_draw()
            logger.info("抽奖: 通过快捷键成功触发抽奖操作～ ")
        except Exception as e:
            logger.error(f"抽奖: 快捷键触发抽奖操作失败喵～ {e}")

    def handle_new_connection(self):
        client_connection = self.server.nextPendingConnection()
        if not client_connection:
            return

        client_connection.readyRead.connect(lambda: self.read_client_data(client_connection))
        client_connection.disconnected.connect(lambda: self.cleanup_connection(client_connection))
        
    def cleanup_connection(self, client_connection):
        """清理IPC连接资源"""
        client_connection.disconnectFromServer()
        client_connection.deleteLater()

    def read_client_data(self, client_connection):
        try:
            # 检查连接状态和是否可读
            if not client_connection or not client_connection.isOpen() or not client_connection.isReadable():
                logger.warning("IPC连接未打开或不可读，跳过处理")
                return
                
            data = client_connection.readAll().data().decode().strip()
            if not data:
                logger.warning("接收到空的IPC消息，跳过处理")
                return
                
            logger.info(f"接收到IPC消息: {data}")
            
            if data == 'show':
                self.toggle_window()
            elif data.startswith('url:'):
                # 处理URL命令
                url_command = data[4:].strip()  # 移除'url:'前缀
                logger.info(f"处理URL命令: {url_command}")
                
                # 解析URL命令并调用相应方法
                if '://' in url_command:
                    # 移除协议部分，如 'secrandom://settings' -> 'settings'
                    path_part = url_command.split('://', 1)[1]
                else:
                    path_part = url_command
                    
                if '?' in path_part:
                    # 有参数的情况，如 'settings?action=start'
                    path, params_str = path_part.split('?', 1)
                    params = {}
                    for param in params_str.split('&'):
                        if '=' in param:
                            key, value = param.split('=', 1)
                            params[key] = value
                else:
                    # 无参数的情况
                    path = path_part
                    params = {}
                
                # 根据路径调用对应的方法
                method_map = {
                    'main': 'show_main_window',
                    'settings': 'show_settings_window',
                    'pumping': 'show_pumping_window',
                    'reward': 'show_reward_window',
                    'history': 'show_history_window',
                    'floating': 'show_floating_window',
                    'about': 'show_about_window',
                    'direct_extraction': 'show_direct_extraction',
                    'plugin_settings': 'show_plugin_settings_window'
                }
                
                # 去除路径末尾的斜杠，确保匹配正确
                path = path.rstrip('/')
                
                if path in method_map:
                    method_name = method_map[path]
                    if hasattr(self, method_name):
                        method = getattr(self, method_name)
                        
                        # 处理额外的action参数
                        if 'action' in params:
                            action = params['action']
                            if action == 'start' and path == 'pumping':
                                self.start_pumping_selection()
                            elif action == 'stop' and path == 'pumping':
                                self.stop_pumping_selection()
                            elif action == 'reset' and path == 'pumping':
                                self.reset_pumping_selection()
                            elif action == 'start' and path == 'reward':
                                self.start_reward_selection()
                            elif action == 'stop' and path == 'reward':
                                self.stop_reward_selection()
                            elif action == 'reset' and path == 'reward':
                                self.reset_reward_selection()
                            elif action == 'donation' and path == 'about':
                                self.show_donation_dialog()
                            elif action == 'contributor' and path == 'about':
                                self.show_contributor_dialog()
                            elif action == 'open' and path == 'plugin_settings':
                                self.show_plugin_settings_window()
                        else:
                            # 没有action参数时直接调用对应方法
                            method()
                    else:
                        logger.warning(f"找不到方法: {method_name}")
                else:
                    logger.warning(f"未知的URL路径: {path}")
            else:
                logger.warning(f"未知的IPC消息: {data}")
        except Exception as e:
            logger.error(f"处理IPC消息时发生错误: {e}")
        finally:
            # 安全地清理连接
            try:
                # 使用更安全的方式检查对象是否有效
                if client_connection and hasattr(client_connection, 'disconnectFromServer'):
                    try:
                        client_connection.disconnectFromServer()
                    except RuntimeError:
                        # 对象已被删除，忽略错误
                        pass
                    try:
                        client_connection.deleteLater()
                    except RuntimeError:
                        # 对象已被删除，忽略错误
                        pass
            except Exception as e:
                logger.error(f"清理IPC连接时发生错误: {e}")

    def show_window_from_ipc(self, socket):
        """从IPC接收显示窗口请求并激活窗口"""
        try:
            # 检查连接状态和是否可读
            if not socket or not socket.isOpen() or not socket.isReadable():
                logger.warning("IPC连接未打开或不可读，跳过处理")
                return
                
            data = socket.readAll().data().decode().strip()
            if not data:
                logger.warning("接收到空的IPC窗口显示请求，跳过处理")
                return
                
            logger.info(f"接收到IPC窗口显示请求: {data}")
            
            # 确保主窗口资源正确加载并显示
            self.show()
            self.activateWindow()
            self.raise_()
            
            # 处理悬浮窗口
            self._handle_levitation_window()
        except Exception as e:
            logger.error(f"处理IPC窗口显示请求时发生错误: {e}")
        finally:
            # 安全地清理连接
            try:
                # 使用更安全的方式检查对象是否有效
                if socket and hasattr(socket, 'disconnectFromServer'):
                    try:
                        socket.disconnectFromServer()
                    except RuntimeError:
                        # 对象已被删除，忽略错误
                        pass
            except Exception as e:
                logger.error(f"清理IPC连接时发生错误: {e}")

    def _handle_levitation_window(self):
        """处理悬浮窗口激活"""
        if hasattr(self, 'levitation_window') and self.levitation_window:
            self.levitation_window.raise_()
            self.levitation_window.activateWindow()
    
    # ==================================================
    # URL协议支持方法
    # ==================================================
    def show_main_window(self):
        """(^・ω・^ ) 白露的主界面召唤魔法！
        通过URL协议打开主界面，让用户开始他们的随机选择冒险～
        会自动显示并激活窗口，确保用户能立即看到界面！✨"""
        logger.info("白露URL: 正在打开主界面～")
        self.toggle_window()
        logger.info("白露URL: 主界面已成功打开～")
    
    def show_settings_window(self):
        """(^・ω・^ ) 白露的设置界面召唤魔法！
        通过URL协议打开设置界面，让用户可以调整各种设置～
        会检查是否跳过安全验证，如果开启则直接打开设置界面！🔒✨"""
        logger.info("白露URL: 正在打开设置界面～")
        
        # 检查是否跳过安全验证
        skip_security = False
        try:
            settings_path = path_manager.get_settings_path('fixed_url_settings.json')
            if path_manager.file_exists(settings_path):
                with open_file(settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    fixed_url_settings = settings.get('fixed_url', {})
                    skip_security = fixed_url_settings.get('settings_url_skip_security', False)
        except Exception as e:
            logger.error(f"读取跳过安全验证设置失败: {e}")
        
        # 如果没有设置跳过安全验证，则进行密码验证
        if not skip_security:
            self.show_setting_interface()
        else:
            # 跳过安全验证，直接创建并显示设置界面
            if not hasattr(self, 'settingInterface') or not self.settingInterface:
                from app.view.settings import settings_Window
                self.settingInterface = settings_Window(self)

            if self.settingInterface.isVisible() and not self.settingInterface.isMinimized():
                self.settingInterface.showNormal() 
                self.settingInterface.activateWindow()
                self.settingInterface.raise_()
            else:
                if self.settingInterface.isMinimized():
                    self.settingInterface.showNormal()
                    self.settingInterface.activateWindow()
                    self.settingInterface.raise_()
                else:
                    self.settingInterface.show()
                    self.settingInterface.activateWindow()
                    self.settingInterface.raise_()
        
        logger.info("白露URL: 设置界面已成功打开～")
    
    def show_pumping_window(self):
        """(^・ω・^ ) 白露的抽人界面召唤魔法！
        通过URL协议打开抽人界面，让用户可以开始随机选择～
        会自动切换到抽人界面，方便用户立即开始使用！🎲✨"""
        logger.info("白露URL: 正在打开抽人界面～")
        if not self.isVisible():
            self.show()
            self.activateWindow()
            self.raise_()
        self.switchTo(self.pumping_peopleInterface)
        logger.info("白露URL: 抽人界面已成功打开～")
    
    def show_reward_window(self):
        """(^・ω・^ ) 白露的抽奖界面召唤魔法！
        通过URL协议打开抽奖界面，让用户可以开始抽奖活动～
        会自动切换到抽奖界面，让用户立即开始抽奖！🎁✨"""
        logger.info("白露URL: 正在打开抽奖界面～")
        if not self.isVisible():
            self.show()
            self.activateWindow()
            self.raise_()
        self.switchTo(self.pumping_rewardInterface)
        logger.info("白露URL: 抽奖界面已成功打开～")
    
    def show_history_window(self):
        """(^・ω・^ ) 白露的历史记录界面召唤魔法！
        通过URL协议打开历史记录界面，让用户查看过往记录～
        会自动切换到历史记录界面，方便用户查看历史数据！📊✨"""
        logger.info("白露URL: 正在打开历史记录界面～")
        if not self.isVisible():
            self.show()
            self.activateWindow()
            self.raise_()
        self.switchTo(self.history_handoff_settingInterface)
        # 触发历史记录数据加载
        self.history_handoff_settingInterface.pumping_people_card.load_data()
        logger.info("白露URL: 历史记录界面已成功打开～")
    
    def show_floating_window(self):
        """(^・ω・^ ) 白露的浮窗界面召唤魔法！
        通过URL协议打开浮窗界面，让用户使用便捷的悬浮功能～
        会检查是否跳过安全验证，如果开启则直接切换浮窗状态！🪟✨"""
        logger.info("白露URL: 正在打开浮窗界面～")
        
        # 检查是否跳过安全验证
        skip_security = False
        try:
            settings_path = path_manager.get_settings_path('fixed_url_settings.json')
            if path_manager.file_exists(settings_path):
                with open_file(settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    fixed_url_settings = settings.get('fixed_url', {})
                    skip_security = fixed_url_settings.get('floating_url_skip_security', False)
        except Exception as e:
            logger.error(f"读取跳过安全验证设置失败: {e}")
        
        # 如果没有设置跳过安全验证，则进行密码验证
        if not skip_security:
            self.toggle_levitation_window()
        else:
            # 跳过安全验证，直接切换浮窗状态
            if not hasattr(self, 'levitation_window') or not self.levitation_window:
                self.levitation_window.show()
            elif self.levitation_window.isVisible():
                self.levitation_window.hide()
            else:
                self.levitation_window.show()
                self.levitation_window.activateWindow()
                self.levitation_window.raise_()
        
        logger.info("白露URL: 浮窗界面已成功打开～")
    
    def show_plugin_settings_window(self):
        """(^・ω・^ ) 白露的插件设置界面召唤魔法！
        通过URL协议打开插件设置界面，让用户可以管理插件相关设置～
        会检查是否跳过安全验证，如果开启则直接打开插件设置界面！⚙️✨
        """
        logger.info(f"白露URL: 正在打开插件设置界面～")
        
        # 检查是否跳过安全验证
        skip_security = False
        try:
            settings_path = path_manager.get_settings_path('fixed_url_settings.json')
            if path_manager.file_exists(settings_path):
                with open_file(settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    fixed_url_settings = settings.get('fixed_url', {})
                    skip_security = fixed_url_settings.get('plugin_settings_open_url_skip_security', False)
        except Exception as e:
            logger.error(f"读取跳过安全验证设置失败: {e}")
        
        # 如果没有设置跳过安全验证，则进行密码验证
        if not skip_security:
            # 确保设置窗口存在
            if not hasattr(self, 'settingInterface') or not self.settingInterface:
                from app.view.settings import settings_Window
                self.settingInterface = settings_Window(self)
            
            # 调用设置窗口的插件设置界面方法
            self.settingInterface.show_plugin_settings_interface()
        else:
            # 跳过安全验证，直接创建并显示设置窗口，然后切换到插件设置界面
            if not hasattr(self, 'settingInterface') or not self.settingInterface:
                from app.view.settings import settings_Window
                self.settingInterface = settings_Window(self)
            
            # 确保设置窗口可见
            if not self.settingInterface.isVisible():
                self.settingInterface.show()
                self.settingInterface.activateWindow()
                self.settingInterface.raise_()
            
            # 如果窗口最小化，则恢复
            if self.settingInterface.isMinimized():
                self.settingInterface.showNormal()
            
            # 检查插件设置界面是否存在
            if self.settingInterface.plugin_settingsInterface is not None:
                # 切换到插件设置界面
                self.settingInterface.stackedWidget.setCurrentWidget(self.settingInterface.plugin_settingsInterface)
                logger.info(f"白露URL: 插件设置界面已成功打开～")
            else:
                logger.error(f"白露URL: 插件设置界面不存在，无法打开～")
                # 尝试重新创建插件设置界面
                try:
                    from app.view.plugins.plugin_settings import PluginSettingsWindow
                    self.settingInterface.plugin_settingsInterface = PluginSettingsWindow(self.settingInterface)
                    self.settingInterface.plugin_settingsInterface.setObjectName("plugin_settingsInterface")
                    logger.debug("设置界面: 插件设置界面重新创建成功")
                    # 重新初始化导航
                    self.settingInterface.initNavigation()
                    # 切换到插件设置界面
                    self.settingInterface.stackedWidget.setCurrentWidget(self.settingInterface.plugin_settingsInterface)
                    logger.info(f"白露URL: 插件设置界面重新创建并成功打开～")
                except Exception as e:
                    logger.error(f"白露URL: 重新创建插件设置界面失败: {e}")
        
        logger.info(f"白露URL: 插件设置界面已成功打开～")
    
    def start_pumping_selection(self):
        """(^・ω・^ ) 白露的抽选启动魔法！
        通过URL参数启动抽选功能，让程序自动开始抽人～
        会检查当前界面并调用相应的开始方法！🎯✨"""
        logger.info("白露URL: 正在启动抽选功能～")
        try:
            # 确保主窗口可见
            if not self.isVisible():
                self.show()
                self.activateWindow()
                self.raise_()
            
            # 切换到抽人界面
            self.switchTo(self.pumping_peopleInterface)
            
            # 尝试调用抽人界面的开始方法
            if hasattr(self.pumping_peopleInterface, 'start_draw'):
                self.pumping_peopleInterface.start_draw()
                logger.info("白露URL: 抽选功能已成功启动～")
            else:
                logger.warning("白露URL: 抽人界面缺少start_draw方法～")
        except Exception as e:
            logger.error(f"白露URL: 启动抽选功能失败: {e}")
    
    def stop_pumping_selection(self):
        """(^・ω・^ ) 白露的抽选停止魔法！
        通过URL参数停止抽选功能，让程序停止当前的抽人操作～
        会检查当前界面并调用相应的停止方法！🛑✨"""
        logger.info("白露URL: 正在停止抽选功能～")
        try:
            # 确保主窗口可见
            if not self.isVisible():
                self.show()
                self.activateWindow()
                self.raise_()
            
            # 切换到抽人界面
            self.switchTo(self.pumping_peopleInterface)
            
            # 尝试调用抽人界面的停止方法
            if hasattr(self.pumping_peopleInterface, '_stop_animation') and self.pumping_peopleInterface.is_animating:
                self.pumping_peopleInterface._stop_animation()
                logger.info("白露URL: 抽选功能已成功停止～")
            else:
                logger.warning("白露URL: 抽人界面未在动画中或缺少_stop_animation方法～")
        except Exception as e:
            logger.error(f"白露URL: 停止抽选功能失败: {e}")
    
    def reset_pumping_selection(self):
        """(^・ω・^ ) 白露的抽选重置魔法！
        通过URL参数重置抽选状态，让程序清空当前的抽选结果～
        会检查当前界面并调用相应的重置方法！🔄✨"""
        logger.info("白露URL: 正在重置抽选状态～")
        try:
            # # 确保主窗口可见
            # if not self.isVisible():
            #     self.show()
            #     self.activateWindow()
            #     self.raise_()
            
            # # 切换到抽人界面
            # self.switchTo(self.pumping_peopleInterface)
            
            # 尝试调用抽人界面的重置方法
            if hasattr(self.pumping_peopleInterface, '_reset_to_initial_state'):
                self.pumping_peopleInterface._reset_to_initial_state()
                logger.info("白露URL: 抽选状态已成功重置～")
            else:
                logger.warning("白露URL: 抽人界面缺少_reset_to_initial_state方法～")
        except Exception as e:
            logger.error(f"白露URL: 重置抽选状态失败: {e}")
    
    def start_reward_selection(self):
        """(^・ω・^ ) 白露的抽奖启动魔法！
        通过URL参数启动抽奖功能，让程序自动开始抽奖～
        会检查当前界面并调用相应的开始方法！🎁✨"""
        logger.info("白露URL: 正在启动抽奖功能～")
        try:
            # 确保主窗口可见
            if not self.isVisible():
                self.show()
                self.activateWindow()
                self.raise_()
            
            # 切换到抽奖界面
            self.switchTo(self.pumping_rewardInterface)
            
            # 尝试调用抽奖界面的开始方法
            if hasattr(self.pumping_rewardInterface, 'start_draw'):
                self.pumping_rewardInterface.start_draw()
                logger.info("白露URL: 抽奖功能已成功启动～")
            else:
                logger.warning("白露URL: 抽奖界面缺少start_draw方法～")
        except Exception as e:
            logger.error(f"白露URL: 启动抽奖功能失败: {e}")
    
    def stop_reward_selection(self):
        """(^・ω・^ ) 白露的抽奖停止魔法！
        通过URL参数停止抽奖功能，让程序停止当前的抽奖操作～
        会检查当前界面并调用相应的停止方法！🛑✨"""
        logger.info("白露URL: 正在停止抽奖功能～")
        try:
            # 确保主窗口可见
            if not self.isVisible():
                self.show()
                self.activateWindow()
                self.raise_()
            
            # 切换到抽奖界面
            self.switchTo(self.pumping_rewardInterface)
            
            # 尝试调用抽奖界面的停止方法
            if hasattr(self.pumping_rewardInterface, '_stop_animation') and self.pumping_rewardInterface.is_animating:
                self.pumping_rewardInterface._stop_animation()
                logger.info("白露URL: 抽奖功能已成功停止～")
            else:
                logger.warning("白露URL: 抽奖界面未在动画中或缺少_stop_animation方法～")
        except Exception as e:
            logger.error(f"白露URL: 停止抽奖功能失败: {e}")
    
    def reset_reward_selection(self):
        """(^・ω・^ ) 白露的抽奖重置魔法！
        通过URL参数重置抽奖状态，让程序清空当前的抽奖结果～
        会检查当前界面并调用相应的重置方法！🔄✨"""
        logger.info("白露URL: 正在重置抽奖状态～")
        try:
            # # 确保主窗口可见
            # if not self.isVisible():
            #     self.show()
            #     self.activateWindow()
            #     self.raise_()
            
            # # 切换到抽奖界面
            # self.switchTo(self.pumping_rewardInterface)
            
            # 尝试调用抽奖界面的重置方法
            if hasattr(self.pumping_rewardInterface, '_reset_to_initial_state'):
                self.pumping_rewardInterface._reset_to_initial_state()
                logger.info("白露URL: 抽奖状态已成功重置～")
            else:
                logger.warning("白露URL: 抽奖界面缺少_reset_to_initial_state方法～")
        except Exception as e:
            logger.error(f"白露URL: 重置抽奖状态失败: {e}")

    def show_direct_extraction(self):
        """(^・ω・^ ) 白露的闪抽召唤魔法！
        通过URL参数直接打开抽人界面，让用户快速开始抽人操作～
        会自动切换到抽人界面，方便用户开始抽人！✨"""
        logger.info("白露URL: 正在打开闪抽界面～")
        self.levitation_window._show_direct_extraction_window()
        logger.info("白露URL: 闪抽界面已成功打开～")
    
    def show_about_window(self):
        """(^・ω・^ ) 白露的关于界面召唤魔法！
        通过URL协议打开关于界面，让用户查看软件信息～
        会自动切换到关于界面，方便用户查看版本和作者信息！ℹ️✨"""
        logger.info("白露URL: 正在打开关于界面～")
        if not self.isVisible():
            self.show()
            self.activateWindow()
            self.raise_()
        self.switchTo(self.about_settingInterface)
        logger.info("白露URL: 关于界面已成功打开～")
    
    def show_donation_dialog(self):
        """(^・ω・^ ) 白露的捐赠支持召唤魔法！
        通过URL参数打开捐赠支持对话框，让用户可以支持项目发展～
        会显示捐赠支持对话框，方便用户查看捐赠方式！💝✨"""
        logger.info("白露URL: 正在打开捐赠支持对话框～")
        try:
            # 确保主窗口可见
            if not self.isVisible():
                self.show()
                self.activateWindow()
                self.raise_()
            
            # 切换到关于界面
            self.switchTo(self.about_settingInterface)
            
            # 打开捐赠支持对话框
            donation_dialog = DonationDialog(self)
            donation_dialog.exec_()
            logger.info("白露URL: 捐赠支持对话框已成功打开～")
        except Exception as e:
            logger.error(f"白露URL: 打开捐赠支持对话框失败: {e}")
    
    def show_contributor_dialog(self):
        """(^・ω・^ ) 白露的贡献者召唤魔法！
        通过URL参数打开贡献者对话框，让用户查看项目贡献者信息～
        会显示贡献者对话框，方便用户了解项目贡献者！👥✨"""
        logger.info("白露URL: 正在打开贡献者对话框～")
        try:
            # 确保主窗口可见
            if not self.isVisible():
                self.show()
                self.activateWindow()
                self.raise_()
            
            # 切换到关于界面
            self.switchTo(self.about_settingInterface)
            
            # 打开贡献者对话框
            contributor_dialog = ContributorDialog(self)
            contributor_dialog.exec_()
            logger.info("白露URL: 贡献者对话框已成功打开～")
        except Exception as e:
            logger.error(f"白露URL: 打开贡献者对话框失败: {e}")
