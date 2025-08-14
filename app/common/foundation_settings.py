from qfluentwidgets import *
from qfluentwidgets import FluentIcon as FIF
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

import json
import os
import sys
import platform
import winreg
from datetime import datetime
from loguru import logger

from app.common.config import get_theme_icon, load_custom_font, is_dark_theme, VERSION

is_dark = is_dark_theme(qconfig)

class foundation_settingsCard(GroupHeaderCardWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("基础设置")
        self.setBorderRadius(8)
        self.settings_file = "app/Settings/Settings.json"
        self.default_settings = {
            "check_on_startup": True,
            "self_starting_enabled": False,
            "pumping_floating_enabled": True,
            "pumping_floating_visible": True,
            "pumping_floating_side": 0,
            "pumping_reward_side": 0,
            "pumping_floating_transparency_mode": 6,
            "main_window_focus_mode": 0,
            "main_window_focus_time": 0,
            "main_window_mode": 0,
            "settings_window_mode": 0,
            "topmost_switch": False,
            "url_protocol_enabled": False,
        }

        self.self_starting_switch = SwitchButton()
        self.pumping_floating_switch = SwitchButton()
        self.pumping_floating_side_comboBox = ComboBox()
        self.pumping_reward_side_comboBox = ComboBox()
        self.pumping_floating_transparency_comboBox = ComboBox()
        self.main_window_focus_comboBox = ComboBox()
        self.main_window_focus_time_comboBox = ComboBox()
        self.main_window_comboBox = ComboBox()
        self.settings_window_comboBox = ComboBox()

        # 开机自启动按钮
        self.self_starting_switch.setOnText("开启")
        self.self_starting_switch.setOffText("关闭")
        self.self_starting_switch.setFont(QFont(load_custom_font(), 12))
        self.self_starting_switch.checkedChanged.connect(self.on_pumping_floating_switch_changed)
        self.self_starting_switch.checkedChanged.connect(self.setting_startup)

        # 浮窗显示/隐藏按钮
        self.pumping_floating_switch.setOnText("显示")
        self.pumping_floating_switch.setOffText("隐藏")
        self.pumping_floating_switch.checkedChanged.connect(self.on_pumping_floating_switch_changed)
        self.pumping_floating_switch.setFont(QFont(load_custom_font(), 12))

        # 抽人选项侧边栏位置设置
        self.pumping_floating_side_comboBox.setFixedWidth(100)
        self.pumping_floating_side_comboBox.addItems(["顶部", "底部"])
        self.pumping_floating_side_comboBox.currentIndexChanged.connect(self.save_settings)
        self.pumping_floating_side_comboBox.setFont(QFont(load_custom_font(), 12))

        # 抽奖选项侧边栏位置设置
        self.pumping_reward_side_comboBox.setFixedWidth(100)
        self.pumping_reward_side_comboBox.addItems(["顶部", "底部"])
        self.pumping_reward_side_comboBox.currentIndexChanged.connect(self.save_settings)
        self.pumping_reward_side_comboBox.setFont(QFont(load_custom_font(), 12))

        # 定时清理按钮
        self.cleanup_button = PushButton("设置定时清理")
        self.cleanup_button.clicked.connect(self.show_cleanup_dialog)
        self.cleanup_button.setFont(QFont(load_custom_font(), 12))

        # 导出诊断数据按钮
        self.export_diagnostic_button = PushButton("导出诊断数据")
        self.export_diagnostic_button.clicked.connect(self.export_diagnostic_data)
        self.export_diagnostic_button.setFont(QFont(load_custom_font(), 12))

        # 导入设置按钮
        self.import_settings_button = PushButton("导入设置")
        self.import_settings_button.clicked.connect(self.import_settings)
        self.import_settings_button.setFont(QFont(load_custom_font(), 12))

        # 导出设置按钮
        self.export_settings_button = PushButton("导出设置")
        self.export_settings_button.clicked.connect(self.export_settings)
        self.export_settings_button.setFont(QFont(load_custom_font(), 12))

        # 浮窗透明度设置下拉框
        self.pumping_floating_transparency_comboBox.setFixedWidth(200)
        self.pumping_floating_transparency_comboBox.addItems(["100%", "90%", "80%", "70%", "60%", "50%", "40%", "30%", "20%", "10%"])
        self.pumping_floating_transparency_comboBox.currentIndexChanged.connect(self.save_settings)
        self.pumping_floating_transparency_comboBox.setFont(QFont(load_custom_font(), 12))

        # 设置主窗口不是焦点时关闭延迟
        self.main_window_focus_comboBox.setFixedWidth(200)
        self.main_window_focus_comboBox.addItems(
            ["不关闭", "直接关闭", "3秒后关闭", "5秒后关闭", "10秒后关闭", "15秒后关闭", "30秒后关闭", "1分钟后关闭",
             "2分钟后关闭", "3分钟后关闭", "5分钟后关闭", "10分钟后关闭", "30分钟后关闭", "45分钟后关闭", "1小时后关闭",
             "2小时后关闭", "3小时后关闭", "6小时后关闭", "12小时后关闭"])
        self.main_window_focus_comboBox.currentIndexChanged.connect(self.on_focus_mode_changed)
        self.main_window_focus_comboBox.setFont(QFont(load_custom_font(), 12))

        # 设置检测主窗口焦点时间
        self.main_window_focus_time_comboBox.setFixedWidth(200)
        self.main_window_focus_time_comboBox.addItems(
            ["不检测", "1秒", "2秒", "3秒", "5秒", "10秒", "15秒", "30秒",
             "1分钟", "5分钟", "10分钟", "15分钟", "30分钟",
             "1小时", "2小时", "3小时", "6小时"])
        self.main_window_focus_time_comboBox.currentIndexChanged.connect(self.on_focus_time_changed)
        self.main_window_focus_time_comboBox.setFont(QFont(load_custom_font(), 12))

        # 主窗口窗口显示位置下拉框
        self.main_window_comboBox.setFixedWidth(200)
        self.main_window_comboBox.addItems(["居中", "居中向下3/5"])
        self.main_window_comboBox.currentIndexChanged.connect(self.save_settings)
        self.main_window_comboBox.setFont(QFont(load_custom_font(), 12))

        # 设置窗口显示位置下拉框
        self.settings_window_comboBox.setFixedWidth(200)
        self.settings_window_comboBox.addItems(["居中", "居中向下3/5"])
        self.settings_window_comboBox.currentIndexChanged.connect(self.save_settings)
        self.settings_window_comboBox.setFont(QFont(load_custom_font(), 12))

        # 添加组件到分组中
        self.check_on_startup = SwitchButton()
        self.check_on_startup.setOnText("开启")
        self.check_on_startup.setOffText("关闭")
        self.check_on_startup.setFont(QFont(load_custom_font(), 12))
        self.check_on_startup.checkedChanged.connect(self.save_settings)
        
        # 是否显示浮窗左侧控件
        self.left_pumping_floating_switch = SwitchButton()
        self.left_pumping_floating_switch.setOnText("经典版")
        self.left_pumping_floating_switch.setOffText("简洁版")
        self.left_pumping_floating_switch.setFont(QFont(load_custom_font(), 12))
        self.left_pumping_floating_switch.checkedChanged.connect(self.save_settings)

        # 主界面置顶功能
        self.topmost_switch = SwitchButton()
        self.topmost_switch.setOnText("置顶")
        self.topmost_switch.setOffText("取消置顶")
        self.topmost_switch.setFont(QFont(load_custom_font(), 12))
        self.topmost_switch.checkedChanged.connect(self.save_settings)
        
        # URL协议注册功能
        self.url_protocol_switch = SwitchButton()
        self.url_protocol_switch.setOnText("已注册")
        self.url_protocol_switch.setOffText("未注册")
        self.url_protocol_switch.setFont(QFont(load_custom_font(), 12))
        self.url_protocol_switch.checkedChanged.connect(self.toggle_url_protocol)


        self.addGroup(get_theme_icon("ic_fluent_arrow_sync_20_filled"), "更新设置", "启动时自动检查软件更新", self.check_on_startup)
        self.addGroup(get_theme_icon("ic_fluent_branch_compare_20_filled"), "开机自启", "系统启动时自动启动本应用(启用后将自动设置不显示主窗口)", self.self_starting_switch)
        self.addGroup(get_theme_icon("ic_fluent_branch_fork_link_20_filled"), "URL协议注册", "注册SecRandom URL协议，允许其他程序通过URL启动SecRandom并打开特定界面", self.url_protocol_switch)
        self.addGroup(get_theme_icon("ic_fluent_window_ad_20_filled"), "浮窗显隐", "设置便捷抽人的浮窗显示/隐藏", self.pumping_floating_switch)
        self.addGroup(get_theme_icon("ic_fluent_arrow_autofit_height_20_filled"), "抽人选项侧边栏位置", "设置抽人选项侧边栏位置", self.pumping_floating_side_comboBox)
        self.addGroup(get_theme_icon("ic_fluent_arrow_autofit_height_20_filled"), "抽奖选项侧边栏位置", "设置抽奖选项侧边栏位置", self.pumping_reward_side_comboBox)
        self.addGroup(get_theme_icon("ic_fluent_clock_20_filled"), "定时清理", "设置定时清理抽取记录的时间", self.cleanup_button)
        self.addGroup(get_theme_icon("ic_fluent_window_inprivate_20_filled"), "浮窗样式", "设置便捷抽人的浮窗样式", self.left_pumping_floating_switch)
        self.addGroup(get_theme_icon("ic_fluent_window_inprivate_20_filled"), "浮窗透明度", "设置便捷抽人的浮窗透明度", self.pumping_floating_transparency_comboBox)
        self.addGroup(get_theme_icon("ic_fluent_window_inprivate_20_filled"), "主窗口置顶", "设置主窗口是否置顶(需重新打开主窗口生效-不是重启软件)", self.topmost_switch)
        self.addGroup(get_theme_icon("ic_fluent_layout_row_two_focus_top_settings_20_filled"), "主窗口焦点", "设置主窗口不是焦点时关闭延迟", self.main_window_focus_comboBox)
        self.addGroup(get_theme_icon("ic_fluent_timer_20_filled"), "检测主窗口焦点时间", "设置检测主窗口焦点时间", self.main_window_focus_time_comboBox)
        self.addGroup(get_theme_icon("ic_fluent_window_location_target_20_filled"), "主窗口位置", "设置主窗口的显示位置", self.main_window_comboBox)
        self.addGroup(get_theme_icon("ic_fluent_window_location_target_20_filled"), "设置窗口位置", "设置设置窗口的显示位置", self.settings_window_comboBox)
        self.addGroup(get_theme_icon("ic_fluent_group_20_filled"), "导出诊断数据", "导出软件诊断数据用于问题排查", self.export_diagnostic_button)
        self.addGroup(get_theme_icon("ic_fluent_multiselect_ltr_20_filled"), "导入设置", "从文件导入软件设置", self.import_settings_button)
        self.addGroup(get_theme_icon("ic_fluent_multiselect_ltr_20_filled"), "导出设置", "导出软件设置到文件", self.export_settings_button)
        
        # 定时检查清理
        self.cleanup_timer = QTimer(self)
        self.cleanup_timer.timeout.connect(self.check_cleanup_time)
        self.cleanup_timer.start(1000)

        self.load_settings()
        self.save_settings()

    def on_pumping_floating_switch_changed(self, checked):
        self.save_settings()

    def on_focus_mode_changed(self):
        self.save_settings()  # 先保存设置
        index = self.main_window_focus_comboBox.currentIndex()
        main_window = None
        for widget in QApplication.topLevelWidgets():
            if hasattr(widget, 'update_focus_mode'):  # 通过特征识别主窗口
                main_window = widget
                break
        if main_window:
            main_window.update_focus_mode(index)

    def on_focus_time_changed(self):
        self.save_settings()  # 先保存设置
        index = self.main_window_focus_time_comboBox.currentIndex()
        main_window = None
        for widget in QApplication.topLevelWidgets():
            if hasattr(widget, 'update_focus_time'):  # 通过特征识别主窗口
                main_window = widget
                break
        if main_window:
            main_window.update_focus_time(index)

    def setting_startup(self):
        import sys
        import os
        import platform

        # 获取当前程序路径
        executable = sys.executable
        logger.info(f"设置开机自启动的程序路径: {executable}")

        if not executable:
            logger.error("无法获取可执行文件路径")
            return

        try:
            # 读取设置文件
            with open('app/Settings/Settings.json', 'r', encoding='utf-8') as f:
                settings = json.load(f)
                foundation_settings = settings.get('foundation', {})
                self_starting_enabled = foundation_settings.get('self_starting_enabled', False)

                # 处理启动文件夹操作
                if platform.system() != 'Windows':
                    self.self_starting_switch.setChecked(self.default_settings["self_starting_enabled"])
                    logger.error("仅支持Windows系统")
                    return

                # 获取启动文件夹路径
                startup_folder = os.path.join(
                    os.getenv('APPDATA'),
                    r'Microsoft\Windows\Start Menu\Programs\Startup'
                )
                shortcut_path = os.path.join(startup_folder, 'SecRandom.lnk')

                if self_starting_enabled:
                    try:
                        # 创建快捷方式
                        import winshell
                        from win32com.client import Dispatch

                        shell = Dispatch('WScript.Shell')
                        shortcut = shell.CreateShortCut(shortcut_path)
                        shortcut.Targetpath = executable
                        shortcut.WorkingDirectory = os.path.dirname(executable)
                        shortcut.save()
                        logger.success("开机自启动设置成功")
                    except Exception as e:
                        logger.error(f"创建快捷方式失败: {e}")
                else:
                    try:
                        if os.path.exists(shortcut_path):
                            os.remove(shortcut_path)
                            logger.success("开机自启动取消成功")
                        else:
                            logger.info("开机自启动项不存在，无需取消")
                    except Exception as e:
                        logger.error(f"删除快捷方式失败: {e}")

        except json.JSONDecodeError as e:
            logger.error(f"设置文件格式错误: {e}")
        except Exception as e:
            logger.error(f"读取设置文件时出错: {e}")

    def load_settings(self):
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    foundation_settings = settings.get("foundation", {})
                    
                    # 优先使用保存的文字选项
                    self_starting_enabled = foundation_settings.get("self_starting_enabled", self.default_settings["self_starting_enabled"])

                    pumping_floating_enabled = foundation_settings.get("pumping_floating_enabled", self.default_settings["pumping_floating_enabled"])

                    pumping_floating_side = foundation_settings.get("pumping_floating_side", self.default_settings["pumping_floating_side"])
                    if pumping_floating_side < 0 or pumping_floating_side >= self.pumping_floating_side_comboBox.count():
                        # 如果索引值无效，则使用默认值
                        pumping_floating_side = self.default_settings["pumping_floating_side"]

                    pumping_reward_side = foundation_settings.get("pumping_reward_side", self.default_settings["pumping_reward_side"])
                    if pumping_reward_side < 0 or pumping_reward_side >= self.pumping_reward_side_comboBox.count():
                        # 如果索引值无效，则使用默认值
                        pumping_reward_side = self.default_settings["pumping_reward_side"]
                        
                    main_window_mode = foundation_settings.get("main_window_mode", self.default_settings["main_window_mode"])
                    if main_window_mode < 0 or main_window_mode >= self.main_window_comboBox.count():
                        # 如果索引值无效，则使用默认值
                        main_window_mode = self.default_settings["main_window_mode"]

                    pumping_floating_transparency_mode = foundation_settings.get("pumping_floating_transparency_mode", self.default_settings["pumping_floating_transparency_mode"])
                    if pumping_floating_transparency_mode < 0 or pumping_floating_transparency_mode >= self.pumping_floating_transparency_comboBox.count():
                        # 如果索引值无效，则使用默认值
                        pumping_floating_transparency_mode = self.default_settings["pumping_floating_transparency_mode"]

                    main_window_focus_mode = foundation_settings.get("main_window_focus_mode", self.default_settings["main_window_focus_mode"])
                    if main_window_focus_mode < 0 or main_window_focus_mode >= self.main_window_focus_comboBox.count():
                        # 如果索引值无效，则使用默认值
                        main_window_focus_mode = self.default_settings["main_window_focus_mode"]

                    main_window_focus_time = foundation_settings.get("main_window_focus_time", self.default_settings["main_window_focus_time"])
                    if main_window_focus_time < 0 or main_window_focus_time >= self.main_window_focus_time_comboBox.count():
                        # 如果索引值无效，则使用默认值
                        main_window_focus_time = self.default_settings["main_window_focus_time"]

                    settings_window_mode = foundation_settings.get("settings_window_mode", self.default_settings["settings_window_mode"])
                    if settings_window_mode < 0 or settings_window_mode >= self.settings_window_comboBox.count():
                        # 如果索引值无效，则使用默认值
                        settings_window_mode = self.default_settings["settings_window_mode"]

                    check_on_startup = foundation_settings.get("check_on_startup", self.default_settings["check_on_startup"])

                    pumping_floating_visible = foundation_settings.get("pumping_floating_visible", self.default_settings["pumping_floating_visible"])

                    topmost_switch = foundation_settings.get("topmost_switch", self.default_settings["topmost_switch"])

                    url_protocol_enabled = foundation_settings.get("url_protocol_enabled", self.default_settings["url_protocol_enabled"])

                    self.self_starting_switch.setChecked(self_starting_enabled)
                    self.pumping_floating_switch.setChecked(pumping_floating_enabled)
                    self.pumping_floating_side_comboBox.setCurrentIndex(pumping_floating_side)
                    self.pumping_reward_side_comboBox.setCurrentIndex(pumping_reward_side)
                    self.pumping_floating_transparency_comboBox.setCurrentIndex(pumping_floating_transparency_mode)
                    self.main_window_focus_comboBox.setCurrentIndex(main_window_focus_mode)
                    self.main_window_focus_time_comboBox.setCurrentIndex(main_window_focus_time)
                    self.main_window_comboBox.setCurrentIndex(main_window_mode)
                    self.settings_window_comboBox.setCurrentIndex(settings_window_mode)
                    self.check_on_startup.setChecked(check_on_startup)
                    self.left_pumping_floating_switch.setChecked(pumping_floating_visible)
                    self.topmost_switch.setChecked(topmost_switch)
                    self.url_protocol_switch.setChecked(url_protocol_enabled)
            else:
                logger.warning(f"设置文件不存在: {self.settings_file}")
                self.self_starting_switch.setChecked(self.default_settings["self_starting_enabled"])
                self.pumping_floating_switch.setChecked(self.default_settings["pumping_floating_enabled"])
                self.pumping_floating_side_comboBox.setCurrentIndex(self.default_settings["pumping_floating_side"])
                self.pumping_reward_side_comboBox.setCurrentIndex(self.default_settings["pumping_reward_side"])
                self.pumping_floating_transparency_comboBox.setCurrentIndex(self.default_settings["pumping_floating_transparency_mode"])
                self.main_window_focus_comboBox.setCurrentIndex(self.default_settings["main_window_focus_mode"])
                self.main_window_focus_time_comboBox.setCurrentIndex(self.default_settings["main_window_focus_time"])
                self.main_window_comboBox.setCurrentIndex(self.default_settings["main_window_mode"])
                self.settings_window_comboBox.setCurrentIndex(self.default_settings["settings_window_mode"])
                self.check_on_startup.setChecked(self.default_settings["check_on_startup"])
                self.left_pumping_floating_switch.setChecked(self.default_settings["pumping_floating_visible"])
                self.topmost_switch.setChecked(self.default_settings["topmost_switch"])
                self.url_protocol_switch.setChecked(self.default_settings["url_protocol_enabled"])

                self.save_settings()
        except Exception as e:
            logger.error(f"加载设置时出错: {e}")
            self.self_starting_switch.setChecked(self.default_settings["self_starting_enabled"])
            self.pumping_floating_switch.setChecked(self.default_settings["pumping_floating_enabled"])
            self.pumping_floating_side_comboBox.setCurrentIndex(self.default_settings["pumping_floating_side"])
            self.pumping_reward_side_comboBox.setCurrentIndex(self.default_settings["pumping_reward_side"])
            self.pumping_floating_transparency_comboBox.setCurrentIndex(self.default_settings["pumping_floating_transparency_mode"])
            self.main_window_focus_comboBox.setCurrentIndex(self.default_settings["main_window_focus_mode"])
            self.main_window_focus_time_comboBox.setCurrentIndex(self.default_settings["main_window_focus_time"])
            self.main_window_comboBox.setCurrentIndex(self.default_settings["main_window_mode"])
            self.settings_window_comboBox.setCurrentIndex(self.default_settings["settings_window_mode"])
            self.check_on_startup.setChecked(self.default_settings["check_on_startup"])
            self.left_pumping_floating_switch.setChecked(self.default_settings["pumping_floating_visible"])
            self.topmost_switch.setChecked(self.default_settings["topmost_switch"])
            self.url_protocol_switch.setChecked(self.default_settings["url_protocol_enabled"])
            self.save_settings()
    
    def show_cleanup_dialog(self):
        dialog = CleanupTimeDialog(self)
        if dialog.exec():
            cleanup_times = dialog.getText()
            try:
                # 确保Settings目录存在
                os.makedirs(os.path.dirname('app/Settings/CleanupTimes.json'), exist_ok=True)
                
                settings = {}
                if os.path.exists('app/Settings/CleanupTimes.json'):
                    with open('app/Settings/CleanupTimes.json', 'r', encoding='utf-8') as f:
                        settings = json.load(f)
                
                # 处理多个时间输入
                time_list = [time.strip() for time in cleanup_times.split('\n') if time.strip()]
                
                # 清空现有设置
                if 'foundation' in settings:
                    settings['foundation'] = {}
                
                # 验证并收集所有有效时间
                valid_times = []
                for time_str in time_list:
                    try:
                        # 验证时间格式
                        time_str = time_str.replace('：', ':')  # 中文冒号转英文
                        
                        # 支持HH:MM或HH:MM:SS格式
                        parts = time_str.split(':')
                        if len(parts) == 2:
                            hours, minutes = parts
                            seconds = '00'
                            time_str = f"{hours}:{minutes}:{seconds}"  # 转换为完整格式
                        elif len(parts) == 3:
                            hours, minutes, seconds = parts
                        else:
                            raise ValueError(f"时间格式应为'HH:MM'或'HH:MM:SS'，当前输入: {time_str}")
                        
                        # 确保所有部分都存在
                        if not all([hours, minutes, seconds]):
                            raise ValueError(f"时间格式不完整，应为'HH:MM'或'HH:MM:SS'，当前输入: {time_str}")
                            
                        hours = int(hours.strip())
                        minutes = int(minutes.strip())
                        seconds = int(seconds.strip())
                        
                        if hours < 0 or hours > 23:
                            raise ValueError(f"小时数必须在0-23之间，当前输入: {hours}")
                        if minutes < 0 or minutes > 59:
                            raise ValueError(f"分钟数必须在0-59之间，当前输入: {minutes}")
                        if seconds < 0 or seconds > 59:
                            raise ValueError(f"秒数必须在0-59之间，当前输入: {seconds}")
                        
                        valid_times.append(time_str)
                    except Exception as e:
                        logger.error(f"时间格式验证失败: {str(e)}")
                        continue
                
                # 按时间排序
                valid_times.sort(key=lambda x: tuple(map(int, x.split(':'))))
                
                # 重新编号并保存
                for idx, time_str in enumerate(valid_times, 1):
                    settings.setdefault('foundation', {})[str(idx)] = time_str
                
                with open('app/Settings/CleanupTimes.json', 'w', encoding='utf-8') as f:
                    json.dump(settings, f, ensure_ascii=False, indent=4)
                    logger.info(f"成功保存{len(time_list)}个定时清理时间设置")
                    InfoBar.success(
                        title='设置成功',
                        content=f"成功保存{len(time_list)}个定时清理时间!",
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=3000,
                        parent=self
                    )
            except Exception as e:
                logger.error(f"保存定时清理时间失败: {str(e)}")
                InfoBar.error(
                    title='设置失败',
                    content=f"保存定时清理时间失败: {str(e)}",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
    
    def check_cleanup_time(self):
        try:
            current_time = QTime.currentTime().toString("HH:mm:ss")
            if os.path.exists('app/Settings/CleanupTimes.json'):
                with open('app/Settings/CleanupTimes.json', 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    # 检查所有设置的时间
                    foundation_times = settings.get('foundation', {})
                    for time_id, cleanup_time in foundation_times.items():
                        if cleanup_time and current_time == cleanup_time:
                            self.cleanup_temp_files()
                            InfoBar.success(
                                title='清理完成',
                                content=f"定时清理时间 {cleanup_time} 已触发，已清理抽取记录",
                                orient=Qt.Horizontal,
                                isClosable=True,
                                position=InfoBarPosition.TOP,
                                duration=3000,
                                parent=self
                            )
                            break
        except Exception as e:
            logger.error(f"检查定时清理时间时出错: {str(e)}")
    
    def cleanup_temp_files(self):
        try:
            temp_dir = "app/resource/Temp"
            if os.path.exists(temp_dir):
                for filename in os.listdir(temp_dir):
                    if filename.endswith(".json"):
                        file_path = os.path.join(temp_dir, filename)
                        os.remove(file_path)
                        logger.info(f"已清理文件: {file_path}")
        except Exception as e:
            logger.error(f"清理TEMP文件夹时出错: {str(e)}")

    def export_diagnostic_data(self):
        """导出诊断数据到压缩文件"""
        # 首先显示安全确认对话框，告知用户将要导出敏感数据
        try:
            # 创建安全确认对话框
            confirm_box = Dialog(
                title='⚠️ 敏感数据导出确认',
                content=(
                    '您即将导出诊断数据，这些数据可能包含敏感信息：\n\n'
                    '📋 包含的数据类型：\n'
                    '• 抽人名单数据、抽奖设置文件、历史记录文件\n'
                    '• 软件设置文件、插件配置文件、系统日志文件\n\n'
                    '⚠️ 注意事项：\n'
                    '• 这些数据可能包含个人信息和使用记录\n'
                    '• 请妥善保管导出的压缩包文件\n'
                    '• 不要将导出文件分享给不可信的第三方\n'
                    '• 如不再需要，请及时删除导出的文件\n\n'
                    '确认要继续导出诊断数据吗？'
                ),
                parent=self
            )
            confirm_box.yesButton.setText('确认导出')
            confirm_box.cancelButton.setText('取消')
            confirm_box.setFont(QFont(load_custom_font(), 12))
            
            # 如果用户取消导出，则直接返回
            if not confirm_box.exec():
                logger.info("用户取消了诊断数据导出")
                InfoBar.info(
                    title='导出已取消',
                    content='诊断数据导出操作已取消',
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
                return
                
        except Exception as e:
            logger.error(f"创建安全确认对话框失败: {str(e)}")
            pass

        try:
            with open('app/SecRandom/enc_set.json', 'r', encoding='utf-8') as f:
                settings = json.load(f)
                logger.debug("正在读取安全设置，准备执行导出诊断数据验证～ ")

                if settings.get('hashed_set', {}).get('start_password_enabled', False) == True:
                    from app.common.password_dialog import PasswordDialog
                    dialog = PasswordDialog(self)
                    if dialog.exec_() != QDialog.Accepted:
                        logger.warning("用户取消导出诊断数据操作，安全防御已解除～ ")
                        return
        except Exception as e:
            logger.error(f"密码验证系统出错喵～ {e}")
            return
            
        try:
            import zipfile
            from datetime import datetime
            
            # 获取桌面路径
            desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
            if not os.path.exists(desktop_path):
                desktop_path = os.path.join(os.path.expanduser("~"), "桌面")
            
            # 创建诊断文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            zip_filename = f"SecRandom_诊断数据_{timestamp}.zip"
            zip_path = os.path.join(desktop_path, zip_filename)
            
            # 需要导出的文件夹列表
            export_folders = [
                "app/resource/list", 
                "app/resource/reward",
                "app/resource/history",
                "app/resource/settings",
                "app/plugin",
                "logs"
            ]
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                exported_count = 0
                
                for folder_path in export_folders:
                    full_path = os.path.join(os.getcwd(), folder_path)
                    if os.path.exists(full_path):
                        for root, dirs, files in os.walk(full_path):
                            for file in files:
                                file_path = os.path.join(root, file)
                                arcname = os.path.relpath(file_path, os.getcwd())
                                zipf.write(file_path, arcname)
                                exported_count += 1
                    else:
                        # 如果文件夹不存在，创建一个结构化的缺失记录
                        missing_info = {
                            "folder": folder_path,
                            "status": "missing",
                            "note": "该文件夹在导出时不存在"
                        }
                        zipf.writestr(f"_missing_{folder_path.replace('/', '_')}.json", 
                                    json.dumps(missing_info, ensure_ascii=False, indent=2))
                
                # 创建结构化的系统信息报告 - 使用JSON格式便于程序解析
                system_info = {
                    # 【导出元数据】基础信息记录
                    "export_metadata": {
                        "software": "SecRandom",                                                # 软件名称
                        "export_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),            # 人类可读时间
                        "export_timestamp": datetime.now().isoformat(),                         # ISO标准时间戳
                        "version": VERSION,                                                     # 当前软件版本
                        "export_type": "diagnostic",                                            # 导出类型（诊断数据）
                    },
                    # 【系统环境信息】详细的运行环境数据
                    "system_info": {
                        "software_path": os.getcwd(),                                           # 软件安装路径
                        "operating_system": f"{platform.system()} {platform.release()}",        # 操作系统版本
                        "platform_details": {                                                   # 平台详细信息
                            "system": platform.system(),                                        # 系统类型 (Windows/Linux/Darwin)
                            "release": platform.release(),                                      # 系统发行版本
                            "version": platform.version(),                                      # 完整系统版本
                            "machine": platform.machine(),                                      # 机器架构 (AMD64/x86_64)
                            "processor": platform.processor()                                   # 处理器信息
                        },
                        "python_version": sys.version,                                          # Python完整版本信息
                        "python_executable": sys.executable                                     # Python可执行文件路径
                    },
                    # 【导出摘要】统计信息和导出详情
                    "export_summary": {
                        "total_files_exported": exported_count,                                 # 成功导出的文件总数
                        "export_folders": export_folders,                                       # 导出的文件夹列表
                        "export_location": zip_path                                             # 导出压缩包的完整路径
                    }
                }
                # 将系统信息写入JSON文件，使用中文编码确保兼容性
                diagnostic_filename = f"SecRandom_诊断报告_{VERSION}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                zipf.writestr(diagnostic_filename, json.dumps(system_info, ensure_ascii=False, indent=2))
            
            # 显示成功提示
            InfoBar.success(
                title='导出成功',
                content=f'诊断数据已导出到: {zip_path}',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=5000,
                parent=self
            )
            
            logger.success(f"诊断数据导出成功: {zip_path}")
            
            # 打开导出文件所在的文件夹 - 提供用户友好的选择提示
            try:
                # 创建消息框询问用户是否打开导出目录
                msg_box = Dialog(
                    title='诊断数据导出完成',
                    content=f'诊断数据已成功导出到桌面！\n\n文件位置: {zip_path}\n\n是否立即打开导出文件夹查看文件？',
                    parent=self
                )
                msg_box.yesButton.setText('打开文件夹')
                msg_box.cancelButton.setText('稍后再说')
                msg_box.setFont(QFont(load_custom_font(), 12))
                
                if msg_box.exec():
                    # 用户选择打开文件夹
                    os.startfile(os.path.dirname(zip_path))
                    logger.info("用户选择打开诊断数据导出文件夹")
                else:
                    # 用户选择不打开
                    logger.info("用户选择不打开诊断数据导出文件夹")
                    
            except Exception as e:
                # 如果消息框创建失败，回退到简单的提示
                logger.error(f"创建消息框失败: {str(e)}")
                try:
                    os.startfile(os.path.dirname(zip_path))
                except:
                    logger.error("无法打开诊断数据导出文件夹")
                    os.startfile(desktop_path)
            except:
                pass
                
        except Exception as e:
            logger.error(f"导出诊断数据时出错: {str(e)}")
            InfoBar.error(
                title='导出失败',
                content=f'导出诊断数据时出错: {str(e)}',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=5000,
                parent=self
            )
    
    def save_settings(self):
        # 先读取现有设置
        existing_settings = {}
        if os.path.exists(self.settings_file):
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                try:
                    existing_settings = json.load(f)
                except json.JSONDecodeError:
                    existing_settings = {}
        
        # 更新foundation部分的所有设置
        if "foundation" not in existing_settings:
            existing_settings["foundation"] = {}
            
        foundation_settings = existing_settings["foundation"]
        # 删除保存文字选项的代码
        foundation_settings["self_starting_enabled"] = self.self_starting_switch.isChecked()
        foundation_settings["pumping_floating_enabled"] = self.pumping_floating_switch.isChecked()
        foundation_settings["pumping_floating_side"] = self.pumping_floating_side_comboBox.currentIndex()
        foundation_settings["pumping_reward_side"] = self.pumping_reward_side_comboBox.currentIndex()
        foundation_settings["pumping_floating_transparency_mode"] = self.pumping_floating_transparency_comboBox.currentIndex()
        foundation_settings["main_window_focus_mode"] = self.main_window_focus_comboBox.currentIndex()
        foundation_settings["main_window_focus_time"] = self.main_window_focus_time_comboBox.currentIndex()
        foundation_settings["main_window_mode"] = self.main_window_comboBox.currentIndex()
        foundation_settings["settings_window_mode"] = self.settings_window_comboBox.currentIndex()
        foundation_settings["check_on_startup"] = self.check_on_startup.isChecked()
        foundation_settings["pumping_floating_visible"] = self.left_pumping_floating_switch.isChecked()
        foundation_settings["topmost_switch"] = self.topmost_switch.isChecked()
        foundation_settings["url_protocol_enabled"] = self.url_protocol_switch.isChecked()

        
        os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
        with open(self.settings_file, 'w', encoding='utf-8') as f:
            json.dump(existing_settings, f, indent=4)

    def import_settings(self):
        """导入设置"""
        try:
            # 打开文件选择对话框
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "选择要导入的设置文件",
                "",
                "设置文件 (*.json);;所有文件 (*.*)"
            )
            
            if not file_path:
                return
            
            # 读取导入的设置文件
            with open(file_path, 'r', encoding='utf-8') as f:
                imported_settings = json.load(f)
            
            # 显示设置选择对话框
            dialog = SettingsSelectionDialog(mode="import", parent=self)
            if dialog.exec_() == QDialog.Accepted:
                selected_settings = dialog.get_selected_settings()
                
                # 获取设置目录路径
                settings_dir = "./app/Settings"
                
                # 应用选中的设置
                for file_name, subcategories in selected_settings.items():
                    # 特殊处理：所有设置项实际上都在Settings.json文件中
                    if file_name in ["foundation", "pumping_people", "pumping_reward", "history", "channel", "position"]:
                        file_path = os.path.join(settings_dir, "Settings.json")
                    else:
                        file_path = os.path.join(settings_dir, f"{file_name}.json")
                    
                    if os.path.exists(file_path):
                        # 读取现有设置
                        with open(file_path, 'r', encoding='utf-8') as f:
                            current_settings = json.load(f)
                        
                        # 更新选中的设置项
                        for subcategory_name, settings in subcategories.items():
                            if settings:  # 如果有选中的设置项
                                if file_name in ["foundation", "pumping_people", "pumping_reward", "history", "channel", "position"]:
                                    # 这些分类都在Settings.json文件中
                                    if file_name == "channel":
                                        # channel是根级别的字符串，不是嵌套对象
                                        if "channel" in imported_settings:
                                            current_settings["channel"] = imported_settings["channel"]
                                    elif file_name == "position":
                                        # position是根级别的对象
                                        if "position" in imported_settings:
                                            current_settings["position"] = imported_settings["position"]
                                    else:
                                        # foundation、pumping_people、pumping_reward、history等分类
                                        if file_name not in current_settings:
                                            current_settings[file_name] = {}
                                        
                                        for setting_name in settings:
                                            if file_name in imported_settings and setting_name in imported_settings[file_name]:
                                                current_settings[file_name][setting_name] = imported_settings[file_name][setting_name]
                                elif file_name == "voice_engine":
                                    # voice_engine文件中的设置在voice_engine分类下
                                    if "voice_engine" not in current_settings:
                                        current_settings["voice_engine"] = {}
                                    
                                    for setting_name in settings:
                                        if "voice_engine" in imported_settings and setting_name in imported_settings["voice_engine"]:
                                            current_settings["voice_engine"][setting_name] = imported_settings["voice_engine"][setting_name]
                                elif file_name == "plugin_settings":
                                    # plugin_settings文件中的设置在plugin_settings分类下
                                    if "plugin_settings" not in current_settings:
                                        current_settings["plugin_settings"] = {}
                                    
                                    for setting_name in settings:
                                        if "plugin_settings" in imported_settings and setting_name in imported_settings["plugin_settings"]:
                                            current_settings["plugin_settings"][setting_name] = imported_settings["plugin_settings"][setting_name]
                                elif file_name == "config":
                                    # config文件中的设置项分布在不同的分类下
                                    for setting_name in settings:
                                        if setting_name == "DpiScale":
                                            target_section = "Window"
                                        elif setting_name in ["ThemeColor", "ThemeMode"]:
                                            target_section = "QFluentWidgets"
                                        else:
                                            target_section = "config"
                                        
                                        if target_section not in current_settings:
                                            current_settings[target_section] = {}
                                        
                                        if target_section in imported_settings and setting_name in imported_settings[target_section]:
                                            current_settings[target_section][setting_name] = imported_settings[target_section][setting_name]
                                
                        # 保存更新后的设置
                        with open(file_path, 'w', encoding='utf-8') as f:
                            json.dump(current_settings, f, indent=4, ensure_ascii=False)
                
                # 显示成功消息
                w = Dialog("导入成功", "设置已成功导入，现在需要重启应用才能生效。", None)
                w.yesButton.setText("确定")
                w.cancelButton.hide()
                w.buttonLayout.insertStretch(1)
                w.exec_()
        except Exception as e:
            logger.error(f"导入设置失败: {str(e)}")
            w = Dialog("导入失败", f"导入设置时发生错误: {str(e)}", None)
            w.yesButton.setText("确定")
            w.cancelButton.hide()
            w.buttonLayout.insertStretch(1)
            w.exec_()
    
    def export_settings(self):
        """导出设置"""
        try:
            # 显示设置选择对话框
            dialog = SettingsSelectionDialog(mode="export", parent=self)
            if dialog.exec_() == QDialog.Accepted:
                selected_settings = dialog.get_selected_settings()
                
                # 获取设置目录路径
                settings_dir = "./app/Settings"
                
                # 收集选中的设置
                exported_settings = {}
                
                # 遍历选中的设置项，现在category_name直接就是文件名
                for file_name, subcategories in selected_settings.items():
                    for subcategory_name, settings in subcategories.items():
                        if settings:  # 如果有选中的设置项
                                
                                # 特殊处理：所有设置项实际上都在Settings.json文件中
                                if file_name in ["foundation", "pumping_people", "pumping_reward", "history", "channel", "position"]:
                                    file_path = os.path.join(settings_dir, "Settings.json")
                                else:
                                    file_path = os.path.join(settings_dir, f"{file_name}.json")
                                
                                if os.path.exists(file_path):
                                    # 读取设置文件
                                    with open(file_path, 'r', encoding='utf-8') as f:
                                        current_settings = json.load(f)
                                    
                                    # 添加选中的设置项到导出数据
                                    if file_name not in exported_settings:
                                        exported_settings[file_name] = {}
                                    
                                    # 确定在文件中的分类名
                                    section_name = file_name  # 默认分类名与文件名相同
                                    
                                    # 特殊处理Settings.json文件中的多个分类
                                    if file_name in ["foundation", "pumping_people", "pumping_reward", "history", "channel", "position"]:
                                        # 这些分类都在Settings.json文件中
                                        if file_name == "channel":
                                            # channel是根级别的字符串，不是嵌套对象
                                            if "channel" in current_settings:
                                                exported_settings[file_name] = current_settings["channel"]
                                        elif file_name == "position":
                                            # position是根级别的对象
                                            if "position" in current_settings:
                                                exported_settings[file_name] = current_settings["position"]
                                        else:
                                            # foundation、pumping_people、pumping_reward、history等分类直接导出
                                            if file_name in current_settings:
                                                # 如果该分类还没有在导出设置中，则创建
                                                if file_name not in exported_settings:
                                                    exported_settings[file_name] = {}
                                                
                                                # 导出该分类下的所有选中的设置项
                                                for setting_name in settings:
                                                    if setting_name in current_settings[file_name]:
                                                        exported_settings[file_name][setting_name] = current_settings[file_name][setting_name]
                                    elif file_name == "channel":
                                        # channel文件中的设置直接在根级别
                                        for setting_name in settings:
                                            if setting_name in current_settings:
                                                if section_name not in exported_settings[file_name]:
                                                    exported_settings[file_name][section_name] = {}
                                                exported_settings[file_name][section_name][setting_name] = current_settings[setting_name]
                                        continue
                                    elif file_name == "voice_engine":
                                        section_name = "voice_engine"
                                        if section_name not in exported_settings[file_name]:
                                            exported_settings[file_name][section_name] = {}
                                        
                                        for setting_name in settings:
                                            if section_name in current_settings and setting_name in current_settings[section_name]:
                                                exported_settings[file_name][section_name][setting_name] = current_settings[section_name][setting_name]
                                    elif file_name == "plugin_settings":
                                        section_name = "plugin_settings"
                                        if section_name not in exported_settings[file_name]:
                                            exported_settings[file_name][section_name] = {}
                                        
                                        for setting_name in settings:
                                            if section_name in current_settings and setting_name in current_settings[section_name]:
                                                exported_settings[file_name][section_name][setting_name] = current_settings[section_name][setting_name]
                                    elif file_name in ["pumping_people", "pumping_reward"]:
                                        # 特殊处理pumping_people和pumping_reward，需要包含音效设置
                                        section_name = file_name
                                        # 由于这些分类已经在Settings.json处理分支中处理过，这里不需要重复处理
                                        # 确保分类存在
                                        if section_name not in exported_settings:
                                            exported_settings[section_name] = {}
                                        
                                        for setting_name in settings:
                                            # 从Settings.json中对应的分类中获取设置值
                                            if section_name in current_settings and setting_name in current_settings[section_name]:
                                                exported_settings[section_name][setting_name] = current_settings[section_name][setting_name]
                                        
                                        # 如果当前处理的是pumping_reward，并且有音效设置被选中，需要添加音效设置
                                        if file_name == "pumping_reward":
                                            # 检查是否有音效设置被选中
                                            sound_settings = ["animation_music_enabled", "result_music_enabled", 
                                                           "animation_music_volume", "result_music_volume",
                                                           "music_fade_in", "music_fade_out"]
                                            
                                            # 获取选中的音效设置
                                            selected_sound_settings = []
                                            for category_name, subcategories in selected_settings.items():
                                                for subcategory_name, settings_list in subcategories.items():
                                                    if subcategory_name == "音效设置":
                                                        selected_sound_settings = settings_list
                                                        break
                                            
                                            # 如果有音效设置被选中，添加到pumping_reward分类中
                                            if selected_sound_settings:
                                                for sound_setting in selected_sound_settings:
                                                    if sound_setting in sound_settings and sound_setting in current_settings.get("pumping_reward", {}):
                                                        exported_settings[section_name][sound_setting] = current_settings["pumping_reward"][sound_setting]
                                    elif file_name == "config":
                                        # config文件中的设置项分布在不同的分类下
                                        for setting_name in settings:
                                            if setting_name == "DpiScale":
                                                target_section = "Window"
                                            elif setting_name in ["ThemeColor", "ThemeMode"]:
                                                target_section = "QFluentWidgets"
                                            else:
                                                target_section = "config"
                                            
                                            if target_section not in exported_settings[file_name]:
                                                exported_settings[file_name][target_section] = {}
                                            
                                            if target_section in current_settings and setting_name in current_settings[target_section]:
                                                exported_settings[file_name][target_section][setting_name] = current_settings[target_section][setting_name]
                                        continue
                                    else:
                                        # 其他文件的处理
                                        if section_name not in exported_settings[file_name]:
                                            exported_settings[file_name][section_name] = {}
                                        
                                        for setting_name in settings:
                                            if setting_name in current_settings.get(section_name, {}):
                                                exported_settings[file_name][section_name][setting_name] = current_settings[section_name][setting_name]
                                            elif setting_name in current_settings:
                                                # 处理根级别的设置项
                                                exported_settings[file_name][section_name][setting_name] = current_settings[setting_name]
                
                # 打开保存文件对话框
                file_path, _ = QFileDialog.getSaveFileName(
                    self,
                    "保存设置文件",
                    f"settings_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    "设置文件 (*.json)"
                )
                
                if file_path:
                    # 确保文件扩展名是.json
                    if not file_path.endswith('.json'):
                        file_path += '.json'
                    
                    # 保存导出的设置
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(exported_settings, f, indent=4, ensure_ascii=False)
                    
                    # 显示成功消息
                    w = Dialog("导出成功", f"设置已成功导出到:\n{file_path}", None)
                    w.yesButton.setText("确定")
                    w.cancelButton.hide()
                    w.buttonLayout.insertStretch(1)
                    w.exec_()
        except Exception as e:
            logger.error(f"导出设置失败: {str(e)}")
            w = Dialog("导出失败", f"导出设置时发生错误: {str(e)}", None)
            w.yesButton.setText("确定")
            w.cancelButton.hide()
            w.buttonLayout.insertStretch(1)
            w.exec_()
        
    def toggle_url_protocol(self, enabled):
        """切换URL协议注册状态"""
        try:
            if enabled:
                success = self.register_url_protocol()
                if success:
                    logger.success("URL协议注册成功")
                    InfoBar.success(
                        title='注册成功',
                        content='SecRandom URL协议已成功注册，现在可以通过secrandom://链接启动程序',
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=3000,
                        parent=self
                    )
                    self.save_settings()
                else:
                    self.url_protocol_switch.setChecked(False)
                    logger.error("URL协议注册失败")
                    InfoBar.error(
                        title='注册失败',
                        content='URL协议注册失败，请检查权限设置',
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=3000,
                        parent=self
                    )
                    self.url_protocol_switch.setChecked(False)
                    self.save_settings()
            else:
                success = self.unregister_url_protocol()
                if success:
                    logger.success("URL协议注销成功")
                    InfoBar.success(
                        title='注销成功',
                        content='SecRandom URL协议已成功注销',
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=3000,
                        parent=self
                    )
                else:
                    self.url_protocol_switch.setChecked(True)
                    logger.error("URL协议注销失败")
                    InfoBar.error(
                        title='注销失败',
                        content='URL协议注销失败，请检查权限设置',
                        orient=Qt.Horizontal,
                        isClosable=True,
                        position=InfoBarPosition.TOP,
                        duration=3000,
                        parent=self
                    )
        except Exception as e:
            logger.error(f"URL协议操作失败: {str(e)}")
            InfoBar.error(
                title='操作失败',
                content=f'URL协议操作失败: {str(e)}',
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
    
    def register_url_protocol(self):
        """注册SecRandom URL协议"""
        try:
            import sys
            import os
            
            # 获取当前程序路径
            executable = sys.executable
            if not executable:
                logger.error("无法获取可执行文件路径")
                return False
            
            # 构建命令行参数，包含URL处理
            command = f'"{executable}" --url="%1"'
            
            # 注册URL协议到注册表
            protocol_key = "secrandom"
            
            # 创建协议主键
            with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, protocol_key) as key:
                winreg.SetValue(key, None, winreg.REG_SZ, "URL:SecRandom Protocol")
                winreg.SetValueEx(key, "URL Protocol", 0, winreg.REG_SZ, "")
            
            # 创建默认图标
            with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, f"{protocol_key}\\DefaultIcon") as key:
                winreg.SetValue(key, None, winreg.REG_SZ, executable)
            
            # 创建shell\open\command
            with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, f"{protocol_key}\\shell\\open\\command") as key:
                winreg.SetValue(key, None, winreg.REG_SZ, command)
            
            logger.info(f"URL协议注册成功: {protocol_key}")
            return True
            
        except Exception as e:
            logger.error(f"注册URL协议失败: {str(e)}")
            return False
    
    def unregister_url_protocol(self):
        """注销SecRandom URL协议"""
        try:
            protocol_key = "secrandom"
            
            # 删除注册表项
            try:
                winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, f"{protocol_key}\\shell\\open\\command")
                winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, f"{protocol_key}\\shell\\open")
                winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, f"{protocol_key}\\shell")
                winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, f"{protocol_key}\\DefaultIcon")
                winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, protocol_key)
            except WindowsError:
                # 如果键不存在，忽略错误
                pass
            
            logger.info(f"URL协议注销成功: {protocol_key}")
            return True
            
        except Exception as e:
            logger.error(f"注销URL协议失败: {str(e)}")
            return False
    
    def is_url_protocol_registered(self):
        """检查URL协议是否已注册"""
        try:
            protocol_key = "secrandom"
            with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, protocol_key) as key:
                return True
        except WindowsError:
            return False
    
    def handle_url_command(self, url):
        """处理URL命令，打开指定界面"""
        try:
            if not url.startswith("secrandom://"):
                logger.error(f"无效的SecRandom URL: {url}")
                return False
            
            # 解析URL
            from urllib.parse import urlparse, parse_qs
            parsed_url = urlparse(url)
            path = parsed_url.path.strip('/')
            query_params = parse_qs(parsed_url.query)
            
            # 界面映射字典
            interface_map = {
                "main": "open_main_window",
                "settings": "open_settings_window",
                "pumping": "open_pumping_window",
                "reward": "open_reward_window",
                "history": "open_history_window",
                "floating": "open_floating_window"
            }
            
            # 根据路径打开对应界面
            if path in interface_map:
                method_name = interface_map[path]
                main_window = self.get_main_window()
                if main_window and hasattr(main_window, method_name):
                    method = getattr(main_window, method_name)
                    method()
                    logger.info(f"通过URL打开界面: {path}")
                    return True
                else:
                    logger.error(f"找不到对应的方法: {method_name}")
            else:
                logger.error(f"未知的界面路径: {path}")
            
            return False
            
        except Exception as e:
            logger.error(f"处理URL命令失败: {str(e)}")
            return False
    
    def get_main_window(self):
        """获取主窗口实例"""
        try:
            for widget in QApplication.topLevelWidgets():
                if hasattr(widget, 'update_focus_mode'):  # 通过特征识别主窗口
                    return widget
            return None
        except Exception as e:
            logger.error(f"获取主窗口失败: {str(e)}")
            return None
    
    def closeEvent(self, event):
        if not self.saved:
            w = Dialog('未保存内容', '确定要关闭吗？', self)
            w.setFont(QFont(load_custom_font(), 12))
            w.yesButton.setText("确定")
            w.cancelButton.setText("取消")
            w.yesButton = PrimaryPushButton('确定')
            w.cancelButton = PushButton('取消')
            
            if w.exec():
                self.reject
                return
            else:
                event.ignore()
                return
        event.accept()
    
    def getText(self):
        return self.textEdit.toPlainText()


class SettingsSelectionDialog(QDialog):
    """设置选择对话框，用于选择要导入导出的设置项"""
    def __init__(self, mode="export", parent=None):
        super().__init__(parent)
        self.mode = mode  # "export" 或 "import"
        self.setWindowTitle("选择设置项" if mode == "export" else "导入设置")
        self.setMinimumSize(600, 500)  # 设置最小大小而不是固定大小
        self.dragging = False
        self.drag_position = None
        
        # 设置无边框但可调整大小的窗口
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        
        # 创建自定义标题栏
        self.title_bar = QWidget()
        self.title_bar.setObjectName("CustomTitleBar")
        self.title_bar.setFixedHeight(35)
        
        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(10, 0, 10, 0)
        
        # 创建包含图标的标题布局
        title_content_layout = QHBoxLayout()
        title_content_layout.setContentsMargins(0, 0, 0, 0)
        
        # 添加设置图标
        settings_icon = BodyLabel()
        icon_path = "./app/resource/icon/SecRandom.png"
        if os.path.exists(icon_path):
            settings_icon.setPixmap(QIcon(icon_path).pixmap(20, 20))
        else:
            # 如果图标文件不存在，使用备用图标
            settings_icon.setPixmap(QIcon.fromTheme("document-properties", QIcon()).pixmap(20, 20))
        title_content_layout.addWidget(settings_icon)
        
        # 添加功能描述标题
        title_text = "导出设置 - 选择要导出的设置项" if mode == "export" else "导入设置 - 选择要导入的设置项"
        self.title_label = BodyLabel(title_text)
        self.title_label.setObjectName("TitleLabel")
        self.title_label.setFont(QFont(load_custom_font(), 12))
        title_content_layout.addWidget(self.title_label)
        title_content_layout.addStretch()
        
        self.close_btn = QPushButton("✕")
        self.close_btn.setObjectName("CloseButton")
        self.close_btn.setFixedSize(25, 25)
        self.close_btn.clicked.connect(self.reject)
        
        # 将标题内容布局添加到主标题布局中
        title_layout.addLayout(title_content_layout)
        title_layout.addWidget(self.close_btn)
        
        # 创建滚动区域
        self.scroll_area = ScrollArea()
        self.scroll_area.setWidgetResizable(True)
        
        # 创建内容容器
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setAlignment(Qt.AlignLeft)
        
        # 创建设置项选择区域
        self.settings_groups = {}
        self.create_setting_selections()
        
        self.scroll_area.setWidget(self.content_widget)
        
        # 创建按钮
        self.select_all_button = PushButton("全选")
        self.deselect_all_button = PushButton("取消全选")
        self.ok_button = PrimaryPushButton("确定")
        self.cancel_button = PushButton("取消")
        
        self.select_all_button.clicked.connect(self.select_all)
        self.deselect_all_button.clicked.connect(self.deselect_all)
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        
        # 设置字体
        for widget in [self.select_all_button, self.deselect_all_button, self.ok_button, self.cancel_button]:
            widget.setFont(QFont(load_custom_font(), 12))
        
        # 布局
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.select_all_button)
        button_layout.addWidget(self.deselect_all_button)
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.ok_button)
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.title_bar)
        main_layout.addWidget(self.scroll_area)
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
        
        # 更新主题样式
        self.update_theme_style()
        qconfig.themeChanged.connect(self.update_theme_style)
    
    def create_setting_selections(self):
        """创建设置项选择界面"""
        # 定义按文件分类的设置项结构
        self.settings_structure = {
            "foundation": {
                "主窗口设置": [
                    "main_window_mode", "main_window_focus_mode", "main_window_focus_time",
                    "topmost_switch", "window_width", "window_height"
                ],
                "设置窗口设置": [
                    "settings_window_mode", "settings_window_width", "settings_window_height"
                ],
                "浮窗设置": [
                    "pumping_floating_enabled", "pumping_floating_side", "pumping_reward_side",
                    "pumping_floating_transparency_mode", "pumping_floating_visible"
                ],
                "启动设置": [
                    "check_on_startup", "self_starting_enabled", "url_protocol_enabled"
                ]
            },
            "pumping_people": {
                "基础设置": [
                    "draw_mode", "draw_pumping", "student_id", "student_name", "people_theme"
                ],
                "显示设置": [
                    "display_format", "font_size", "animation_color", "show_student_image",
                    "show_random_member", "random_member_format"
                ],
                "动画设置": [
                    "animation_mode", "animation_interval", "animation_auto_play"
                ],
                "音效设置": [
                    "animation_music_enabled", "result_music_enabled",
                    "animation_music_volume", "result_music_volume",
                    "music_fade_in", "music_fade_out"
                ]
            },
            "pumping_reward": {
                "基础设置": [
                    "draw_mode", "draw_pumping", "reward_theme"
                ],
                "显示设置": [
                    "display_format", "font_size", "animation_color", "show_reward_image"
                ],
                "动画设置": [
                    "animation_mode", "animation_interval", "animation_auto_play"
                ],
                "音效设置": [
                    "animation_music_enabled", "result_music_enabled",
                    "animation_music_volume", "result_music_volume",
                    "music_fade_in", "music_fade_out"
                ]
            },
            "history": {
                "抽人历史": [
                    "history_enabled", "probability_weight", "history_days"
                ],
                "抽奖历史": [
                    "reward_history_enabled", "history_reward_days"
                ]
            },
            "channel": {
                "更新设置": [
                    "channel"
                ]
            },
            "position": {
                "位置设置": [
                    "x", "y"
                ]
            },
            "config": {
                "主题与显示": [
                    "ThemeColor", "ThemeMode", "DpiScale"
                ]
            },
            "voice_engine": {
                "语音引擎设置": [
                    "voice_engine", "edge_tts_voice_name", "voice_enabled", "voice_volume",
                    "voice_speed", "system_volume_enabled", "system_volume_value"
                ]
            },
            "plugin_settings": {
                "插件设置": [
                    "run_plugins_on_startup", "fetch_plugin_list_on_startup", "selected_plugin"
                ]
            }
        }
        
        # 为每个功能分类创建选择区域
        for category_name, subcategories in self.settings_structure.items():
            file_group = GroupHeaderCardWidget()
            file_group.setTitle(category_name)
            file_group.setBorderRadius(8)
            
            self.settings_groups[category_name] = {}
            
            # 遍历每个子分类和设置项，为每个设置项创建独立的分组
            for subcategory_name, settings in subcategories.items():
                self.settings_groups[category_name][subcategory_name] = {}
                
                # 为每个设置项创建独立的分组
                for setting in settings:
                    # 创建独立的设置项容器
                    setting_widget = QWidget()
                    setting_layout = QVBoxLayout(setting_widget)
                    setting_layout.setAlignment(Qt.AlignLeft)
                    setting_layout.setSpacing(4)
                    
                    # 创建复选框
                    checkbox = CheckBox(self.get_setting_display_name(setting))
                    checkbox.setFont(QFont(load_custom_font(), 10))
                    checkbox.setChecked(True)
                    self.settings_groups[category_name][subcategory_name][setting] = checkbox
                    
                    # 创建水平布局让复选框靠左
                    checkbox_layout = QHBoxLayout()
                    checkbox_layout.addWidget(checkbox)
                    checkbox_layout.setAlignment(Qt.AlignLeft)
                    checkbox_layout.addStretch()
                    
                    # 将复选框布局添加到设置布局中
                    checkbox_widget = QWidget()
                    checkbox_widget.setLayout(checkbox_layout)
                    setting_layout.addWidget(checkbox_widget)
                    
                    # 简化分类逻辑，直接使用子分类名称和设置项显示名称
                    display_name = self.get_setting_display_name(setting)
                    file_group.addGroup(None, subcategory_name, f"{display_name}设置项", setting_widget)
            
            self.content_layout.addWidget(file_group)

    def get_setting_display_name(self, setting_name):
        """获取设置项的显示名称"""
        display_names = {
            # foundation设置
            "check_on_startup": "启动时检查更新", # 有
            "self_starting_enabled": "开机自启动", # 有
            "pumping_floating_enabled": "浮窗启用", # 有
            "pumping_floating_side": "抽人侧边栏位置", # 有
            "pumping_reward_side": "抽奖侧边栏位置", # 有
            "pumping_floating_transparency_mode": "浮窗透明度", # 有
            "main_window_focus_mode": "主窗口焦点模式", # 有
            "main_window_focus_time": "焦点检测时间", # 有
            "main_window_mode": "主窗口位置", # 有
            "settings_window_mode": "设置窗口位置", # 有
            "pumping_floating_visible": "浮窗样式", # 有
            "topmost_switch": "主窗口置顶", # 有
            "window_width": "主窗口宽度", # 有
            "window_height": "主窗口高度", # 有
            "settings_window_width": "设置窗口宽度", # 有
            "settings_window_height": "设置窗口高度", # 有
            "url_protocol_enabled": "URL协议注册", # 有
            # pumping_people设置（跟pumping_reward设置有重复的不计入）
            "student_id": "显示学号", # 有
            "student_name": "显示姓名", # 有
            "people_theme": "主题", # 有
            "show_random_member": "显示随机成员", # 有
            "random_member_format": "随机成员格式", # 有
            "show_student_image": "显示学生图片", # 有
            # pumping_reward设置（跟pumping_people设置有重复的不计入）
            "reward_theme": "主题", # 有
            "show_reward_image": "显示奖品图片", # 有
            # pumping_people设置和pumping_reward设置 重复设置项
            "draw_mode": "抽取模式", # 有
            "draw_pumping": "抽取方式", # 有
            "animation_mode": "动画模式", # 有
            "animation_interval": "动画间隔", # 有
            "animation_auto_play": "自动播放", # 有
            "animation_music_enabled": "动画音乐", # 有
            "result_music_enabled": "结果音乐", # 有
            "animation_music_volume": "动画音量", # 有
            "result_music_volume": "结果音量", # 有
            "music_fade_in": "音乐淡入", # 有
            "music_fade_out": "音乐淡出", # 有
            "display_format": "显示格式", # 有
            "animation_color": "动画颜色", # 有
            "font_size": "字体大小", # 有
            # history设置
            "history_enabled": "历史记录启用", # 有
            "probability_weight": "概率权重", # 有
            "history_days": "历史记录天数", # 有
            "reward_history_enabled": "奖品历史启用", # 有
            "history_reward_days": "奖品历史天数", # 有
            # position设置
            "x": "浮窗X坐标", # 有
            "y": "浮窗Y坐标", # 有
            # channel设置
            "channel": "更新通道", # 有
            # config设置
            "DpiScale": "DPI缩放", # 有
            "ThemeColor": "主题颜色", # 有
            "ThemeMode": "主题模式", # 有
            # plugin_settings设置
            "run_plugins_on_startup": "启动时运行插件", # 有
            "fetch_plugin_list_on_startup": "启动时获取插件列表", # 有
            "selected_plugin": "选中插件", # 有
            # voice_engine设置
            "voice_engine": "语音引擎", # 有
            "edge_tts_voice_name": "Edge TTS语音", # 有
            "voice_enabled": "语音启用", # 有
            "voice_volume": "语音音量", # 有
            "voice_speed": "语音速度", # 有
            "system_volume_enabled": "系统音量控制", # 有
            "system_volume_value": "系统音量值" # 有
        }
        return display_names.get(setting_name, setting_name)
    
    def select_all(self):
        """全选所有设置项"""
        for category_name in self.settings_groups:
            for subcategory_name in self.settings_groups[category_name]:
                for setting_name in self.settings_groups[category_name][subcategory_name]:
                    self.settings_groups[category_name][subcategory_name][setting_name].setChecked(True)
    
    def deselect_all(self):
        """取消全选所有设置项"""
        for category_name in self.settings_groups:
            for subcategory_name in self.settings_groups[category_name]:
                for setting_name in self.settings_groups[category_name][subcategory_name]:
                    self.settings_groups[category_name][subcategory_name][setting_name].setChecked(False)
    
    def get_selected_settings(self):
        """获取选中的设置项"""
        selected = {}
        for file_name in self.settings_groups:
            selected[file_name] = {}
            for subcategory_name in self.settings_groups[file_name]:
                selected[file_name][subcategory_name] = []
                for setting_name in self.settings_groups[file_name][subcategory_name]:
                    if self.settings_groups[file_name][subcategory_name][setting_name].isChecked():
                        selected[file_name][subcategory_name].append(setting_name)
        return selected
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.title_bar.underMouse():
            self.dragging = True
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        if self.dragging and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_position)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        self.dragging = False
    
    def update_theme_style(self):
        colors = {'text': '#F5F5F5', 'bg': '#111116', 'title_bg': '#2D2D2D'} if is_dark else {'text': '#111116', 'bg': '#F5F5F5', 'title_bg': '#E0E0E0'}
        self.setStyleSheet(f"""
            QDialog {{ background-color: {colors['bg']}; border-radius: 5px; }}
            #CustomTitleBar {{ background-color: {colors['title_bg']}; }}
            #TitleLabel {{ color: {colors['text']}; font-weight: bold; padding: 5px; }}
            #CloseButton {{ 
                background-color: transparent; 
                color: {colors['text']}; 
                border-radius: 4px; 
                font-weight: bold; 
            }}
            #CloseButton:hover {{ background-color: #ff4d4d; color: white; }}
            QLabel, QPushButton, QCheckBox {{ color: {colors['text']}; }}
        """)
        
        # 设置标题栏颜色（仅Windows系统）
        if os.name == 'nt':
            try:
                import ctypes
                hwnd = int(self.winId())
                bg_color = colors['bg'].lstrip('#')
                rgb_color = int(f'FF{bg_color}', 16) if len(bg_color) == 6 else int(bg_color, 16)
                
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    ctypes.c_int(hwnd), 35,
                    ctypes.byref(ctypes.c_uint(rgb_color)),
                    ctypes.sizeof(ctypes.c_uint)
                )
            except Exception as e:
                logger.warning(f"设置标题栏颜色失败: {str(e)}")

class CleanupTimeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        # 🌟 星穹铁道白露：设置无边框但可调整大小的窗口样式并解决屏幕设置冲突~ 
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setWindowTitle("输入定时清理记录时间")
        self.setMinimumSize(400, 335)  # 设置最小大小而不是固定大小
        self.saved = False
        self.dragging = False
        self.drag_position = None
        
        # 确保不设置子窗口的屏幕属性
        if parent is not None:
            self.setParent(parent)
        
        # 🐦 小鸟游星野：创建自定义标题栏啦~ (≧∇≦)ﾉ
        self.title_bar = QWidget()
        self.title_bar.setObjectName("CustomTitleBar")
        self.title_bar.setFixedHeight(35)
        
        # 标题栏布局
        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(10, 0, 10, 0)
        
        # 窗口标题
        self.title_label = QLabel("输入定时清理记录时间")
        self.title_label.setObjectName("TitleLabel")
        self.title_label.setFont(QFont(load_custom_font(), 12))
        
        # 窗口控制按钮
        self.close_btn = QPushButton("✕")
        self.close_btn.setObjectName("CloseButton")
        self.close_btn.setFixedSize(25, 25)
        self.close_btn.clicked.connect(self.reject)
        
        # 添加组件到标题栏
        title_layout.addWidget(self.title_label)
        title_layout.addStretch()
        title_layout.addWidget(self.close_btn)
        
        self.text_label = BodyLabel('请输入定时清理记录时间，每行一个\n格式为：HH:mm:ss\n例如：12:00:00 或 20:00:00\n中文冒号自动转英文冒号\n自动补秒位为00')
        self.text_label.setFont(QFont(load_custom_font(), 12))

        self.update_theme_style()
        qconfig.themeChanged.connect(self.update_theme_style)
        
        self.textEdit = PlainTextEdit()
        self.textEdit.setPlaceholderText("请输入定时清理记录时间，每行一个")
        self.textEdit.setFont(QFont(load_custom_font(), 12))
        
        self.setFont(QFont(load_custom_font(), 12))

        try:
            if os.path.exists('app/Settings/CleanupTimes.json'):
                with open('app/Settings/CleanupTimes.json', 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    
                    # 获取所有清理时间并格式化为字符串
                    cleanup_times = settings.get('foundation', {})
                    if cleanup_times:
                        times_list = [str(time) for time_id, time in cleanup_times.items()]
                        self.textEdit.setPlainText('\n'.join(times_list))
                    else:
                        pass
        except Exception as e:
            logger.error(f"加载定时清理记录时间失败: {str(e)}")

        self.saveButton = PrimaryPushButton("保存")
        self.cancelButton = PushButton("取消")
        self.saveButton.clicked.connect(self.accept)
        self.cancelButton.clicked.connect(self.reject)
        self.saveButton.setFont(QFont(load_custom_font(), 12))
        self.cancelButton.setFont(QFont(load_custom_font(), 12))
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        # 添加自定义标题栏
        layout.addWidget(self.title_bar)
        # 添加内容区域
        content_layout = QVBoxLayout()
        content_layout.setSpacing(10)
        content_layout.addWidget(self.text_label)
        content_layout.addWidget(self.textEdit)
        
        buttonLayout = QHBoxLayout()
        buttonLayout.addStretch(1)
        buttonLayout.addWidget(self.cancelButton)
        buttonLayout.addWidget(self.saveButton)
        
        content_layout.addLayout(buttonLayout)
        content_layout.setContentsMargins(20, 10, 20, 20)
        layout.addLayout(content_layout)
        self.setLayout(layout)

    def mousePressEvent(self, event):
        # 🐦 小鸟游星野：窗口拖动功能~ 按住标题栏就能移动啦 (๑•̀ㅂ•́)و✧
        if event.button() == Qt.LeftButton and self.title_bar.underMouse():
            self.dragging = True
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.dragging and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.dragging = False

    def update_theme_style(self):
        # 🌟 星穹铁道白露：主题样式更新 ~ 现在包含自定义标题栏啦！
        colors = {'text': '#F5F5F5', 'bg': '#111116', 'title_bg': '#2D2D2D'} if is_dark else {'text': '#111116', 'bg': '#F5F5F5', 'title_bg': '#E0E0E0'}
        self.setStyleSheet(f"""
            QDialog {{ background-color: {colors['bg']}; border-radius: 5px; }}
            #CustomTitleBar {{ background-color: {colors['title_bg']}; }}
            #TitleLabel {{ color: {colors['text']}; font-weight: bold; padding: 5px; }}
            #CloseButton {{ 
                background-color: transparent; 
                color: {colors['text']}; 
                border-radius: 4px; 
                font-weight: bold; 
            }}
            #CloseButton:hover {{ background-color: #ff4d4d; color: white; }}
            QLabel, QPushButton, QTextEdit {{ color: {colors['text']}; }}
        """)
        
        # 设置标题栏颜色以匹配背景色（仅Windows系统）
        if os.name == 'nt':
            try:
                import ctypes
                # 🌟 星穹铁道白露：修复参数类型错误~ 现在要把窗口ID转成整数才行哦！
                hwnd = int(self.winId())  # 转换为整数句柄
                
                # 🐦 小鸟游星野：颜色格式要改成ARGB才行呢~ 添加透明度通道(๑•̀ㅂ•́)و✧
                bg_color = colors['bg'].lstrip('#')
                # 转换为ARGB格式（添加不透明通道）
                rgb_color = int(f'FF{bg_color}', 16) if len(bg_color) == 6 else int(bg_color, 16)
                
                # 设置窗口标题栏颜色
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    ctypes.c_int(hwnd),  # 窗口句柄（整数类型）
                    35,  # DWMWA_CAPTION_COLOR
                    ctypes.byref(ctypes.c_uint(rgb_color)),  # 颜色值指针
                    ctypes.sizeof(ctypes.c_uint)  # 数据大小
                )
            except Exception as e:
                logger.warning(f"设置标题栏颜色失败: {str(e)}")