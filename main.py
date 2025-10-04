# ==================================================
# 系统工具导入
# ==================================================
import os
import sys
import json
import time
import asyncio

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# ==================================================
# 第三方库导入
# ==================================================
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtNetwork import *
from qfluentwidgets import *
from loguru import logger

# ==================================================
# 内部模块导入
# ==================================================
from app.common.config import cfg, VERSION, load_custom_font
from app.view.SecRandom import Window
from app.common.url_handler import process_url_if_exists
from app.common.path_utils import path_manager, ensure_dir, open_file, file_exists
from qfluentwidgets import qconfig, Theme

def send_ipc_message(url_command=None):
    """向已运行的实例发送IPC消息"""
    socket = QLocalSocket()
    socket.connectToServer(IPC_SERVER_NAME)

    if socket.waitForConnected(1000):
        if url_command:
            # 发送URL命令
            message = f"url:{url_command}"
            socket.write(message.encode('utf-8'))
            logger.info(f"IPC URL消息发送成功: {message}")
        else:
            # 发送普通的show指令
            socket.write(b"show")
            logger.info("IPC show消息发送成功")
        socket.flush()
        socket.waitForBytesWritten(1000)
        socket.disconnectFromServer()
        return True
    logger.error("IPC连接失败，目标实例可能未响应")
    return False


def configure_logging():
    """配置日志系统"""
    log_dir = os.path.join(project_root, "logs")
    if not path_manager.file_exists(log_dir):
        os.makedirs(log_dir)
        logger.info("日志文件夹创建成功")

    logger.configure(patcher=lambda record: record)

    logger.add(
        os.path.join(log_dir, "SecRandom_{time:YYYY-MM-DD}.log"),
        rotation="1 MB",
        encoding="utf-8",
        retention="30 days",
        format="{time:YYYY-MM-DD HH:mm:ss:SSS} | {level} | {name}:{function}:{line} - {message}",
        enqueue=True,  # 启用异步日志记录
        compression="tar.gz", # 启用压缩
        backtrace=True,  # 启用回溯信息
        diagnose=True,  # 启用诊断信息
        catch=True  # 捕获未处理的异常
    )

    logger.info("=" * 50)
    logger.info("日志系统配置完成")

# ==================================================
# 显示设置
# ==================================================
if cfg.get(cfg.dpiScale) == "Auto":
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    logger.info("DPI缩放已设置为自动模式")
else:
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"
    os.environ["QT_SCALE_FACTOR"] = str(cfg.get(cfg.dpiScale))
    logger.info(f"DPI缩放已设置为{cfg.get(cfg.dpiScale)}倍")

# ==================================================
# 应用实例创建
# ==================================================
# 首先创建QApplication实例，确保在任何QWidget创建之前
app = QApplication(sys.argv)
logger.info("QApplication实例已创建")

# 初始化消息接收器
from app.common.message_receiver import init_message_receiver
init_message_receiver()
logger.info("MessageReceiver实例已初始化")

# ==================================================
# 启动窗口
# ==================================================
class StartupWindow(QDialog):
    """启动窗口，展示软件启动进度"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SecRandom 启动中...")
        self.setFixedSize(260, 135)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.NoFocus | Qt.Popup)
        
        # 移除透明背景属性，使窗口不透明
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 移除透明化效果
        # self.opacity_effect = QGraphicsOpacityEffect()
        # self.opacity_effect.setOpacity(0.8)
        # self.setGraphicsEffect(self.opacity_effect)

        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建背景容器
        self.background_widget = QWidget()
        self.background_widget.setObjectName("backgroundWidget")
        
        # 根据主题设置背景颜色
        self.update_background_theme()
        
        # 创建内容布局
        content_layout = QVBoxLayout(self.background_widget)
        content_layout.setSpacing(15)
        content_layout.setContentsMargins(20, 20, 20, 20)
        
        # 创建顶部水平布局，用于放置图标和标题
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 10)
        top_layout.setSpacing(10)  # 设置图标和标题之间的间距为10像素
        
        # 添加软件图标到左上角
        try:
            icon_path = str(path_manager.get_resource_path('icon', 'secrandom-icon.png'))
            if os.path.exists(icon_path):
                icon_label = QLabel()
                pixmap = QPixmap(icon_path)
                # 缩放图标到合适大小
                scaled_pixmap = pixmap.scaled(52, 52, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                icon_label.setPixmap(scaled_pixmap)
                icon_label.setFixedSize(52, 52)
                top_layout.addWidget(icon_label)
            else:
                logger.error(f"软件图标文件不存在: {icon_path}")
        except Exception as e:
            logger.error(f"加载软件图标失败: {e}")
        
        # 创建垂直布局容器，用于放置标题和版本号
        title_version_layout = QVBoxLayout()
        title_version_layout.setSpacing(2)  # 设置标题和版本号之间的间距
        title_version_layout.setContentsMargins(0, 0, 0, 0)
        
        # 添加标题标签
        self.title_label = BodyLabel("SecRandom")
        self.title_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.title_label.setFont(QFont(load_custom_font(), 16))
        title_version_layout.addWidget(self.title_label)
        
        # 添加版本号标签到标题下方
        self.version_label = BodyLabel(f"{VERSION}")
        self.version_label.setAlignment(Qt.AlignLeft)
        self.version_label.setFont(QFont(load_custom_font(), 10))
        title_version_layout.addWidget(self.version_label)
        
        # 将标题和版本号布局添加到水平布局
        top_layout.addLayout(title_version_layout)
        
        # 添加弹性空间，使图标和标题靠左对齐
        top_layout.addStretch(1)
        
        # 添加顶部布局到内容布局
        content_layout.addLayout(top_layout)

        # 创建详细信息标签
        self.detail_label = BodyLabel("准备启动...")
        self.detail_label.setAlignment(Qt.AlignCenter)
        self.detail_label.setFont(QFont(load_custom_font(), 9))
        content_layout.addWidget(self.detail_label)
        
        # 添加弹性空间，使进度条能够贴底显示
        content_layout.addStretch(1)
        
        # 创建进度条
        self.progress_bar = ProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                background-color: #F0F0F0;
                border-radius: 5px;
                text-align: center;
                color: #333333;
            }
            QProgressBar::chunk {
                background-color: #0078D7;
                border-radius: 5px;
            }
        """)
        content_layout.addWidget(self.progress_bar)
        
        # 将背景容器添加到主布局
        main_layout.addWidget(self.background_widget)
        
        # 启动步骤和进度
        self.startup_steps = [
            ("初始化应用程序环境", 10),
            ("配置日志系统", 20),
            ("检查单实例", 30),
            ("加载配置文件", 40),
            ("清理历史记录", 50),
            ("检查插件设置", 60),
            ("注册URL协议", 70),
            ("创建主窗口", 80),
            ("初始化界面组件", 90),
            ("处理URL命令", 95),
            ("启动完成", 100)
        ]
        
        self.current_step = 0
        
    def update_progress(self, step_name=None, progress=None, detail=None):
        """更新启动进度"""
        if progress is not None:
            self.progress_bar.setValue(progress)
        
        if detail:
            self.detail_label.setText(detail)
            
        # 确保界面更新
        QApplication.processEvents()
        
    def next_step(self, detail=None):
        """进入下一个启动步骤"""
        if self.current_step < len(self.startup_steps):
            step_name, progress = self.startup_steps[self.current_step]
            self.update_progress(step_name, progress, detail)
            self.current_step += 1
            return True
        return False
    
    def set_step(self, step_index, detail=None):
        """设置到指定步骤"""
        if 0 <= step_index < len(self.startup_steps):
            step_name, progress = self.startup_steps[step_index]
            self.update_progress(step_name, progress, detail)
            self.current_step = step_index + 1
            return True
        return False
    
    def update_background_theme(self):
        """根据当前主题更新背景颜色"""
        # 检测当前主题
        if qconfig.theme == Theme.AUTO:
            lightness = QApplication.palette().color(QPalette.Window).lightness()
            is_dark = lightness <= 127
        else:
            is_dark = qconfig.theme == Theme.DARK
        
        # 根据主题设置颜色
        if is_dark:
            # 深色主题
            bg_color = "#111116"
            border_color = "#3E3E42"
            text_color = "#F5F5F5"
            progress_bg = "#2D2D30"
            progress_text = "#F5F5F5"
        else:
            # 浅色主题
            bg_color = "#F5F5F5"
            border_color = "#CCCCCC"
            text_color = "#111116"
            progress_bg = "#F0F0F0"
            progress_text = "#333333"
        
        # 设置背景容器样式
        self.background_widget.setStyleSheet(f"""
            #backgroundWidget {{
                background-color: {bg_color};
                border-radius: 15px;
                border: 1px solid {border_color};
            }}
        """)
        
    def close_startup(self):
        """关闭启动窗口"""
        self.close()

class StartupWindowThread(QThread):
    """启动窗口线程类，用于在单独的线程中运行启动窗口"""
    
    def __init__(self, startup_window=None):
        super().__init__()
        self.startup_window = startup_window
        self.running = False
    
    def run(self):
        """线程运行函数"""
        self.running = True
        # 启动事件循环，保持线程响应
        self.exec_()
    
    def update_progress(self, step_name=None, progress=None, detail=None):
        """更新启动进度"""
        if self.startup_window and self.running:
            self.startup_window.update_progress(step_name, progress, detail)
    
    def next_step(self, detail=None):
        """进入下一个启动步骤"""
        if self.startup_window and self.running:
            self.startup_window.next_step(detail)
    
    def set_step(self, step_index, detail=None):
        """设置到指定步骤"""
        if self.startup_window and self.running:
            self.startup_window.set_step(step_index, detail)
    
    def close_window(self):
        """关闭启动窗口"""
        if self.startup_window and self.running:
            self.running = False
            self.startup_window.close()
            self.quit()  # 退出事件循环


# ==================================================
# 验证状态初始化
# ==================================================
try:
    enc_set_path = path_manager.get_enc_set_path()
    ensure_dir(enc_set_path.parent)
    with open_file(enc_set_path, 'r') as f:
        settings = json.load(f)
    settings['hashed_set']['verification_start'] = False
    with open_file(enc_set_path, 'w') as f:
        json.dump(settings, f, ensure_ascii=False, indent=4)
    logger.info("verification_start状态已成功重置为False")
except Exception as e:
    logger.error(f"写入verification_start失败: {e}")

# ==================================================
# 常量定义
# ==================================================
IPC_SERVER_NAME = 'SecRandomIPC'  # IPC通讯服务器名称
SHARED_MEMORY_KEY = 'SecRandom'   # 共享内存密钥

async def initialize_font_settings():
    """初始化字体设置，加载并应用保存的字体"""
    try:
        # 读取个人设置文件
        settings_file = path_manager.get_settings_path('custom_settings.json')
        ensure_dir(settings_file.parent)
        
        if file_exists(settings_file):
            with open_file(settings_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                personal_settings = settings.get('personal', {})
                font_family = personal_settings.get('font_family')
                
                if font_family:
                    # 应用字体设置
                    logger.info(f"初始化字体设置: {font_family}")
                    await apply_font_to_application(font_family)
                else:
                    logger.info("初始化字体设置: 未指定字体家族，使用默认字体")
                    await apply_font_to_application('HarmonyOS Sans SC')  
        else:
            # 如果设置文件不存在，使用默认字体
            logger.info("初始化字体设置: 设置文件不存在，使用默认字体")
            await apply_font_to_application('HarmonyOS Sans SC')
    except Exception as e:
        logger.error(f"初始化字体设置失败: {e}")
        # 发生错误时使用默认字体
        logger.info("初始化字体设置: 发生错误，使用默认字体")
        await apply_font_to_application('HarmonyOS Sans SC')

async def apply_font_to_application(font_family):
    """应用字体设置到整个应用程序
    
    Args:
        font_family (str): 字体家族名称
    """
    try:
        # 获取当前应用程序默认字体
        current_font = QApplication.font()
        
        # 创建字体对象，只修改字体家族，保持原有字体大小
        app_font = QFont(font_family)
        app_font.setPointSize(current_font.pointSize())
        
        # 如果是HarmonyOS Sans SC字体，使用特定的字体文件路径
        if font_family == "HarmonyOS Sans SC":
            font_path = path_manager.get_font_path('HarmonyOS_Sans_SC_Bold.ttf')
            if font_path and path_manager.file_exists(font_path):
                font_id = QFontDatabase.addApplicationFont(str(font_path))
                if font_id >= 0:
                    font_families = QFontDatabase.applicationFontFamilies(font_id)
                    if font_families:
                        app_font = QFont(font_families[0])
                        app_font.setPointSize(current_font.pointSize())
                        # logger.debug(f"已加载HarmonyOS Sans SC字体文件: {font_path}")
                    else:
                        logger.error(f"无法从字体文件获取字体家族: {font_path}")
                else:
                    logger.error(f"无法加载字体文件: {font_path}")
            else:
                logger.error(f"HarmonyOS Sans SC字体文件不存在: {font_path}")
        
        # 获取所有顶级窗口并更新它们的字体
        widgets_updated = 0
        for widget in QApplication.topLevelWidgets():
            if isinstance(widget, QWidget):
                update_widget_fonts(widget, app_font)
                widgets_updated += 1
            
        # logger.debug(f"已应用字体: {font_family}, 更新了{widgets_updated}个控件字体")
    except Exception as e:
        logger.error(f"应用字体失败: {e}")

def update_widget_fonts(widget, font):
    """递归更新控件及其子控件的字体
    
    Args:
        widget: 要更新字体的控件
        font: 要应用的字体
    """
    if widget is None:
        return
        
    try:
        # 获取控件当前字体
        current_widget_font = widget.font()
        
        # 创建新字体，只修改字体家族，保持原有字体大小和其他属性
        new_font = QFont(font.family(), current_widget_font.pointSize())
        # 保持原有字体的粗体和斜体属性
        new_font.setBold(current_widget_font.bold())
        new_font.setItalic(current_widget_font.italic())
        
        # 更新当前控件的字体
        widget.setFont(new_font)
        
        # 特殊处理某些控件类型
        widget_type = type(widget).__name__
        
        # 对于按钮、标签等控件，确保字体更新
        if widget_type:
            widget.setFont(new_font)
            widget.update()
        
        # 强制控件更新
        widget.update()
        widget.repaint()
        
        # 如果控件有子控件，递归更新子控件的字体
        if isinstance(widget, QWidget):
            children = widget.children()
            for child in children:
                if isinstance(child, QWidget):
                    update_widget_fonts(child, font)
    except Exception as e:
        logger.error(f"更新控件字体失败: {e}")

async def check_single_instance():
    """检查单实例，防止多个程序副本同时运行"""
    # 检查是否有启动窗口线程
    has_startup_thread = 'startup_thread' in globals() and startup_thread is not None and startup_thread.isRunning()
    
    if has_startup_thread:
        startup_thread.next_step(detail="正在检查单实例...")
    
    shared_memory = QSharedMemory(SHARED_MEMORY_KEY)
    if not shared_memory.create(1):
        logger.info('检测到已有 SecRandom 实例正在运行')

        # 获取URL命令（如果存在）
        url_command = None
        try:
            from app.common.url_handler import get_url_handler
            url_handler = get_url_handler()
            if url_handler.has_url_command():
                url_command = url_handler.get_url_command()
                logger.info(f'检测到URL命令，将传递给已有实例: {url_command}')
                if has_startup_thread:
                    startup_thread.next_step(detail="检测到URL命令，将传递给已有实例")
        except Exception as e:
            logger.error(f'获取URL命令失败: {e}')
            if has_startup_thread:
                startup_thread.next_step(detail=f"获取URL命令失败: {e}")

        # 尝试直接发送IPC消息唤醒已有实例
        if send_ipc_message(url_command):
            logger.info('成功唤醒已有实例，当前实例将退出')
            if has_startup_thread:
                startup_thread.update_progress(detail="成功唤醒已有实例，当前实例将退出")
            sys.exit()
        else:
            # IPC连接失败，短暂延迟后重试一次
            await asyncio.sleep(0.3)
            if not send_ipc_message(url_command):
                logger.error("无法连接到已有实例，程序将退出")
                if has_startup_thread:
                    startup_thread.update_progress(detail="无法连接到已有实例，程序将退出")
                sys.exit()
    
    logger.info('单实例检查通过，可以安全启动程序')
    if has_startup_thread:
        startup_thread.update_progress(detail="单实例检查通过，可以安全启动程序")
    
    return shared_memory

def log_software_info():
    """记录软件启动成功信息和相关元信息"""
    # 打印分隔线，增强日志可读性
    logger.info("=" * 50)
    # 记录软件启动成功信息
    logger.info("软件启动成功")
    # 记录软件相关元信息
    software_info = {
        "作者": "lzy98276",
        "Github地址": "https://github.com/SECTL/SecRandom",
        "版本": VERSION
    }
    for key, value in software_info.items():
        logger.info(f"软件{key}: {value}")

def clean_expired_data():
    """清理过期历史记录"""
    from app.common.history_cleaner import clean_expired_history, clean_expired_reward_history
    clean_expired_history()
    clean_expired_reward_history()
    logger.info("已清理过期历史记录")

async def create_main_window_async():
    """异步创建主窗口实例并根据设置决定是否显示窗口"""
    # 检查是否有启动窗口线程
    has_startup_thread = 'startup_thread' in globals() and startup_thread is not None and startup_thread.isRunning()
    
    # 创建主窗口实例
    if has_startup_thread:
        startup_thread.set_step(6, "正在创建主窗口...")
    
    # 延迟50ms后异步创建主窗口
    await asyncio.sleep(0.1)
    
    sec = Window()
    
    # 等待所有子界面加载完成
    if has_startup_thread:
        startup_thread.update_progress(detail="正在等待所有子界面加载完成...")
    
    # 等待子界面和UI组件加载完成
    await asyncio.sleep(0.5)  # 给予足够的时间让异步任务完成
    
    try:
        settings_file = path_manager.get_settings_path()
        ensure_dir(settings_file.parent)
        with open_file(settings_file, 'r') as f:
            settings = json.load(f)
            foundation_settings = settings.get('foundation', {})
            self_starting_enabled = foundation_settings.get('self_starting_enabled', False)
            
            # 显示窗口
            sec.show()
            logger.info("主窗口已显示")
            
            # 如果是开机自启动，则在短暂延迟后隐藏窗口
            if self_starting_enabled:
                sec.hide()
                logger.info("开机自启动模式，窗口已隐藏")
    except FileNotFoundError:
        logger.error("加载设置时出错 - 文件不存在, 使用默认显示主窗口")
        sec.show()
    except KeyError:
        logger.error("设置文件中缺少foundation键, 使用默认显示主窗口")
        sec.show()
    except Exception as e:
        logger.error(f"加载设置时出错: {e}, 使用默认显示主窗口")
        sec.show()
    
    # 将创建的主窗口保存到全局变量
    global main_window
    main_window = sec


# 异步初始化应用程序函数
async def async_initialize_app():
    """异步初始化应用程序，使用asyncio避免阻塞主线程"""
    # 首先配置日志系统
    if 'startup_thread' in globals() and startup_thread is not None and startup_thread.isRunning():
        startup_thread.next_step("正在配置日志系统...")
    configure_logging()
    
    # 设置工作目录为程序所在目录，解决URL协议唤醒时工作目录错误的问题
    if getattr(sys, 'frozen', False):
        # 打包后的可执行文件
        program_dir = os.path.dirname(sys.executable)
    else:
        # 开发环境
        program_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 更改当前工作目录
    if os.getcwd() != program_dir:
        os.chdir(program_dir)
        logger.info(f"工作目录已设置为: {program_dir}")
    
    # 异步执行检查单实例
    await async_check_single_instance()

async def async_check_single_instance():
    """异步检查单实例"""
    if 'startup_thread' in globals() and startup_thread is not None and startup_thread.isRunning():
        startup_thread.next_step("正在检查单实例...")
    global shared_memory
    shared_memory = await check_single_instance()
    
    # 异步执行初始化应用程序
    await async_init_application()

async def async_init_application():
    """异步初始化应用程序"""
    if 'startup_thread' in globals() and startup_thread is not None and startup_thread.isRunning():
        startup_thread.next_step("正在加载配置文件...")
    log_software_info()

    if 'startup_thread' in globals() and startup_thread is not None and startup_thread.isRunning():
        startup_thread.set_step(4, "正在清理历史记录...")
    clean_expired_data()

    # 异步执行注册URL协议
    await async_register_url_protocol()

async def async_register_url_protocol():
    """异步注册URL协议"""
    if 'startup_thread' in globals() and startup_thread is not None and startup_thread.isRunning():
        startup_thread.set_step(6, "正在注册URL协议...")
    try:
        from app.common.foundation_settings import register_url_protocol_on_startup
        register_url_protocol_on_startup()
        logger.info("URL协议自动注册完成")
        if 'startup_thread' in globals() and startup_thread is not None and startup_thread.isRunning():
            startup_thread.set_step(7, "正在创建主窗口...")
    except Exception as e:
        logger.error(f"URL协议注册失败: {e}")
        if 'startup_thread' in globals() and startup_thread is not None and startup_thread.isRunning():
            startup_thread.set_step(7, "正在创建主窗口...")
    
    # 异步执行创建主窗口
    await create_main_window_async()
    
    # 异步执行延迟URL处理
    await async_delayed_url_processing()

async def async_delayed_url_processing():
    """异步延迟URL处理"""
    # 异步处理URL命令
    if 'startup_thread' in globals() and startup_thread is not None and startup_thread.isRunning():
        startup_thread.set_step(9, "正在处理URL命令...")
    
    # 处理URL命令
    process_url_if_exists()
    
    # 完成启动
    if 'startup_thread' in globals() and startup_thread is not None and startup_thread.isRunning():
        startup_thread.set_step(10, "启动完成")
        startup_thread.update_progress(100)
        
        # 延迟关闭启动窗口
        await asyncio.sleep(0.5)
        startup_thread.close_window()

# 异步创建启动窗口函数
async def async_create_startup_window():
    """异步创建启动窗口"""
    # 创建启动窗口
    global startup_window, startup_thread
    startup_window = StartupWindow()
    startup_window.show()
    
    # 强制处理事件，确保启动窗口立即显示
    QApplication.processEvents()
    
    # 创建启动窗口线程并启动
    startup_thread = StartupWindowThread(startup_window)
    startup_thread.start()
    
    # 更新启动窗口进度
    startup_thread.next_step("正在初始化应用程序环境...")
    
    # 给启动窗口一些时间显示和更新
    await asyncio.sleep(0.1)
    
    # 异步初始化应用程序
    await async_initialize_app()

# ==================================================
# 主程序入口
# ==================================================
async def main_async():
    """异步主函数，使用asyncio实现异步初始化"""
    # 全局变量已经在程序入口点初始化
    
    # 检查是否需要初始化应用程序
    if startup_window is None:
        # 不显示启动窗口，直接初始化应用程序
        await async_initialize_app()
    else:
        # 启动窗口已经创建，继续初始化应用程序
        await async_initialize_app()
    
    # 初始化字体设置
    # logger.info("初始化字体设置...")
    if 'startup_thread' in globals() and startup_thread is not None and startup_thread.isRunning():
        startup_thread.next_step(detail="初始化字体设置...")
    await initialize_font_settings()

if __name__ == "__main__":
    # 创建新的事件循环
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # 全局变量，用于存储主窗口实例
    global main_window, startup_window, startup_thread, shared_memory
    
    main_window = None
    startup_window = None
    startup_thread = None
    shared_memory = None
    
    # 检查是否显示启动窗口
    show_startup_window = True  # 默认显示启动窗口
    try:
        settings_file = path_manager.get_settings_path()
        ensure_dir(settings_file.parent)
        if file_exists(settings_file):
            with open_file(settings_file, 'r') as f:
                settings = json.load(f)
                foundation_settings = settings.get('foundation', {})
                show_startup_window = foundation_settings.get('show_startup_window_switch', False)
    except Exception as e:
        logger.error(f"读取启动窗口设置失败，使用默认显示启动窗口: {e}")
    
    # 根据设置决定是否创建启动窗口
    if show_startup_window:
        # 立即创建启动窗口，不使用异步函数
        startup_window = StartupWindow()
        startup_window.show()
        
        # 强制处理事件，确保启动窗口立即显示
        QApplication.processEvents()
        
        # 创建启动窗口线程并启动
        startup_thread = StartupWindowThread(startup_window)
        startup_thread.start()
        
        # 更新启动窗口进度
        startup_thread.next_step("正在初始化应用程序环境...")
        
        # 给启动窗口一些时间显示和更新
        QApplication.processEvents()
    
    try:
        # 启动异步主函数
        loop.run_until_complete(main_async())
        # 启动Qt事件循环
        logger.info("应用程序事件循环启动")
        app.exec_()
    except Exception as e:
        logger.error(f"程序启动失败: {e}")
    finally:
        # 确保共享内存已释放
        if 'shared_memory' in globals() and shared_memory is not None:
            shared_memory.detach()
            logger.info("共享内存已释放，程序完全退出")
        
        # 确保启动窗口线程已退出
        if 'startup_thread' in globals() and startup_thread is not None and startup_thread.isRunning():
            startup_thread.close_window()
            startup_thread.wait(1000)  # 等待最多1秒
        
        # 关闭事件循环
        loop.close()
        sys.exit()