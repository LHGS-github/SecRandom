from re import S
from qfluentwidgets import *
from qfluentwidgets import FluentIcon as FIF
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

import json
import os
import subprocess
from pathlib import Path
from loguru import logger

from app.common.config import get_theme_icon, load_custom_font
from app.common.path_utils import path_manager, ensure_dir, open_file

class pumping_reward_SettinsCard(GroupHeaderCardWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("抽奖设置")
        self.setBorderRadius(8)
        self.settings_file = path_manager.get_settings_path()
        self.default_settings = {
            "font_size": 50,
            "draw_mode": 0,
            "draw_pumping": 0,
            "animation_mode": 0,
            "animation_interval": 100,
            "animation_auto_play": 5,
            "animation_music_enabled": False,
            "result_music_enabled": False,
            "animation_music_volume": 5,
            "result_music_volume": 5,
            "music_fade_in": 300,
            "music_fade_out": 300,
            "display_format": 0,
            "animation_color": 0,
            "show_reward_image": False
        }

        self.pumping_reward_Draw_comboBox = ComboBox()
        self.pumping_reward_mode_Draw_comboBox = ComboBox()
        self.pumping_reward_Animation_comboBox = ComboBox()
        self.pumping_reward_font_size_SpinBox = DoubleSpinBox()
        self.pumping_reward_animation_interval_SpinBox = SpinBox()
        self.pumping_reward_animation_auto_play_SpinBox = SpinBox()
        
        # 抽取模式下拉框
        self.pumping_reward_Draw_comboBox.addItems(["重复抽取", "不重复抽取(直到软件重启)", "不重复抽取(直到抽完全部奖项)"])
        self.pumping_reward_Draw_comboBox.currentIndexChanged.connect(self.save_settings)
        self.pumping_reward_Draw_comboBox.setFont(QFont(load_custom_font(), 12))

        # 抽取方式下拉框
        self.pumping_reward_mode_Draw_comboBox.addItems(["可预测抽取", "不可预测抽取"])
        self.pumping_reward_mode_Draw_comboBox.currentIndexChanged.connect(self.save_settings)
        self.pumping_reward_mode_Draw_comboBox.setFont(QFont(load_custom_font(), 12))

        # 字体大小
        self.pumping_reward_font_size_SpinBox.setRange(30, 200)
        self.pumping_reward_font_size_SpinBox.setValue(50)
        self.pumping_reward_font_size_SpinBox.setSingleStep(5)
        self.pumping_reward_font_size_SpinBox.setDecimals(0)
        self.pumping_reward_font_size_SpinBox.valueChanged.connect(self.save_settings)
        self.pumping_reward_font_size_SpinBox.setFont(QFont(load_custom_font(), 12))

        # 动画模式下拉框
        self.pumping_reward_Animation_comboBox.addItems(["手动停止动画", "自动播放完整动画", "直接显示结果"])
        self.pumping_reward_Animation_comboBox.currentIndexChanged.connect(lambda: self.save_settings())
        self.pumping_reward_Animation_comboBox.setFont(QFont(load_custom_font(), 12))

        # 动画间隔
        self.pumping_reward_animation_interval_SpinBox.setRange(0, 2000)
        self.pumping_reward_animation_interval_SpinBox.setValue(100)
        self.pumping_reward_animation_interval_SpinBox.setSingleStep(10)
        self.pumping_reward_animation_interval_SpinBox.setSuffix("ms")
        self.pumping_reward_animation_interval_SpinBox.valueChanged.connect(self.save_settings)
        self.pumping_reward_animation_interval_SpinBox.setFont(QFont(load_custom_font(), 12))

        # 显示格式
        self.pumping_reward_display_format_comboBox = ComboBox()
        self.pumping_reward_display_format_comboBox.addItems([
            "学号+奖品",
            "奖品",
            "学号"
        ])
        self.pumping_reward_display_format_comboBox.setCurrentIndex(0)
        self.pumping_reward_display_format_comboBox.currentIndexChanged.connect(self.save_settings)
        self.pumping_reward_display_format_comboBox.setFont(QFont(load_custom_font(), 12))

        # 添加组件到分组中
        # ===== 抽取模式设置 =====
        self.addGroup(get_theme_icon("ic_fluent_arrow_sync_20_filled"), "抽取模式", "配置抽取奖品的基本模式", self.pumping_reward_Draw_comboBox)
        self.addGroup(get_theme_icon("ic_fluent_arrow_sync_20_filled"), "抽取方式", "选择抽取奖品的具体方式", self.pumping_reward_mode_Draw_comboBox)
        
        # ===== 显示格式设置 =====
        self.addGroup(get_theme_icon("ic_fluent_text_font_size_20_filled"), "字体大小", "调整抽取结果显示的字体大小", self.pumping_reward_font_size_SpinBox)
        self.addGroup(get_theme_icon("ic_fluent_people_eye_20_filled"), "显示格式", "配置抽取结果的展示格式", self.pumping_reward_display_format_comboBox)

        # ===== 动画设置 =====
        self.addGroup(get_theme_icon("ic_fluent_calendar_video_20_filled"), "动画模式", "选择抽取时的动画播放模式", self.pumping_reward_Animation_comboBox)
        self.addGroup(get_theme_icon("ic_fluent_calendar_video_20_filled"), "动画间隔", "调整动画播放的时间间隔(50-2000ms，适用于1、2号动画)", self.pumping_reward_animation_interval_SpinBox)
        self.addGroup(get_theme_icon("ic_fluent_calendar_video_20_filled"), "自动播放次数", "设置动画自动播放的次数(1-200次，仅适用于2号动画)", self.pumping_reward_animation_auto_play_SpinBox)
        self.load_settings()  # 加载设置
        self.save_settings()  # 保存设置

    def on_pumping_reward_Voice_switch_changed(self, checked):
        self.save_settings()

    def on_color_animation_dialog(self):
        color_type = "animation"
        self.load_color_settings()
        pumping_reward_animation_color_fixed_dialog = ColorDialog(QColor(self.pumping_reward_animation_color_fixed), "动画颜色", self, enableAlpha=False)
        pumping_reward_animation_color_fixed_dialog.setModal(False)
        pumping_reward_animation_color_fixed_dialog.colorChanged.connect(lambda color: self.save_color_settings(color.name(), color_type))
        pumping_reward_animation_color_fixed_dialog.setFont(QFont(load_custom_font(), 12))
        pumping_reward_animation_color_fixed_dialog.show()

    def on_color_result_dialog(self):
        color_type = "result"
        self.load_color_settings()
        pumping_reward_result_color_fixed_dialog = ColorDialog(QColor(self.pumping_reward_result_color_fixed), "结果颜色", self, enableAlpha=False)
        pumping_reward_result_color_fixed_dialog.setModal(False)
        pumping_reward_result_color_fixed_dialog.colorChanged.connect(lambda color: self.save_color_settings(color.name(), color_type))
        pumping_reward_result_color_fixed_dialog.setFont(QFont(load_custom_font(), 12))
        pumping_reward_result_color_fixed_dialog.show()

    def open_music_path(self, button):
        bgm_animation_path = path_manager.get_resource_path('music/pumping_reward', 'Animation_music')
        bgm_result_path = path_manager.get_resource_path('music/pumping_reward', 'result_music')
        ensure_dir(bgm_animation_path)
        ensure_dir(bgm_result_path)
        if button == 'Animation_music':
            self.open_folder(str(bgm_animation_path))
        elif button == 'result_music':
            self.open_folder(str(bgm_result_path))

    def open_image_path(self):
        image_path = path_manager.get_resource_path('images/pumping_reward', 'rewards')
        ensure_dir(image_path)
        self.open_folder(str(image_path))
    
    def open_folder(self, folder_path):
        """跨平台打开文件夹的方法"""
        try:
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder_path))
        except Exception as e:
            logger.error(f"打开文件夹失败: {e}")

    def apply_font_size(self):
        try:
            font_size_str = self.pumping_reward_font_size_SpinBox.value()
            font_size = int(font_size_str)
            if 30 <= font_size <= 200:
                # 格式化保留一位小数
                self.pumping_reward_font_size_SpinBox.setValue(font_size)
                self.save_settings()
                InfoBar.success(
                    title='设置成功',
                    content=f"设置字体大小为: {font_size}",
                    orient=Qt.Horizontal, parent=self, isClosable=True, duration=3000, position=InfoBarPosition.TOP
                )
            else:
                logger.error(f"字体大小超出范围: {font_size}")
                InfoBar.warning(
                    title='字体大小超出范围',
                    content=f"字体大小超出范围，请输入30-200之间的数字，最多一位小数: {font_size}",
                    orient=Qt.Horizontal, parent=self, isClosable=True, duration=3000, position=InfoBarPosition.TOP
                )
        except ValueError as e:
            logger.error(f"无效的字体大小输入: {self.pumping_reward_font_size_SpinBox.value()}")
            InfoBar.warning(
                title='无效的字体大小输入',
                content=f"无效的字体大小输入: {e}",
                orient=Qt.Horizontal, parent=self, isClosable=True, duration=3000, position=InfoBarPosition.TOP
            )

    def reset_font_size(self):
        try:
            self.pumping_reward_font_size_SpinBox.setValue("50")
        except FileNotFoundError as e:
            logger.error(f"加载设置时出错: {e}, 使用默认大小:50")
            self.pumping_reward_font_size_SpinBox.setValue("50")
        except KeyError:
            logger.error(f"设置文件中缺少'foundation'键, 使用默认大小:50")
            self.pumping_reward_font_size_SpinBox.setValue("50")
        self.save_settings()
        self.load_settings()
        
    def load_settings(self):
        try:
            if path_manager.file_exists(self.settings_file):
                with open_file(self.settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    pumping_reward_settings = settings.get("pumping_reward", {})

                    font_size = pumping_reward_settings.get("font_size", self.default_settings["font_size"])
                    
                    # 直接使用索引值
                    draw_mode = pumping_reward_settings.get("draw_mode", self.default_settings["draw_mode"])
                    if draw_mode < 0 or draw_mode >= self.pumping_reward_Draw_comboBox.count():
                        logger.error(f"无效的抽取模式索引: {draw_mode}")
                        draw_mode = self.default_settings["draw_mode"]

                    draw_pumping = pumping_reward_settings.get("draw_pumping", self.default_settings["draw_pumping"])
                    if draw_pumping < 0 or draw_pumping >= self.pumping_reward_mode_Draw_comboBox.count():
                        logger.error(f"无效的抽取方式索引: {draw_pumping}")
                        draw_pumping = self.default_settings["draw_pumping"]
                        
                    animation_mode = pumping_reward_settings.get("animation_mode", self.default_settings["animation_mode"])
                    if animation_mode < 0 or animation_mode >= self.pumping_reward_Animation_comboBox.count():
                        logger.error(f"无效的动画模式索引: {animation_mode}")
                        animation_mode = self.default_settings["animation_mode"]

                    animation_interval = pumping_reward_settings.get("animation_interval", self.default_settings["animation_interval"])
                    animation_auto_play = pumping_reward_settings.get("animation_auto_play", self.default_settings["animation_auto_play"])

                    # 加载动画音乐设置
                    animation_music_enabled = pumping_reward_settings.get("animation_music_enabled", self.default_settings["animation_music_enabled"])
                    result_music_enabled = pumping_reward_settings.get("result_music_enabled", self.default_settings["result_music_enabled"])
                    animation_music_volume = pumping_reward_settings.get("animation_music_volume", self.default_settings["animation_music_volume"])
                    result_music_volume = pumping_reward_settings.get("result_music_volume", self.default_settings["result_music_volume"])
                    music_fade_in = pumping_reward_settings.get("music_fade_in", self.default_settings["music_fade_in"])
                    music_fade_out = pumping_reward_settings.get("music_fade_out", self.default_settings["music_fade_out"])

                    # 显示格式
                    display_format = pumping_reward_settings.get("display_format", self.default_settings["display_format"])
                    if display_format < 0 or display_format >= self.pumping_reward_display_format_comboBox.count():
                        logger.error(f"无效的显示格式索引: {display_format}")
                        display_format = self.default_settings["display_format"]

                    # 动画/结果颜色
                    animation_color = pumping_reward_settings.get("animation_color", self.default_settings["animation_color"])
                    if animation_color < 0 or animation_color >= self.pumping_reward_student_name_color_comboBox.count():
                        logger.error(f"无效的动画/结果颜色索引: {animation_color}")
                        animation_color = self.default_settings["animation_color"]

                    # 奖品图片显示
                    show_reward_image = pumping_reward_settings.get("show_reward_image", self.default_settings["show_reward_image"])
                    
                    self.pumping_reward_Draw_comboBox.setCurrentIndex(draw_mode)
                    self.pumping_reward_mode_Draw_comboBox.setCurrentIndex(draw_pumping)
                    self.pumping_reward_font_size_SpinBox.setValue(font_size)
                    self.pumping_reward_Animation_comboBox.setCurrentIndex(animation_mode)
                    self.pumping_reward_animation_interval_SpinBox.setValue(animation_interval)
                    self.pumping_reward_animation_auto_play_SpinBox.setValue(animation_auto_play)
                    self.pumping_reward_display_format_comboBox.setCurrentIndex(display_format)
            else:
                self.pumping_reward_Draw_comboBox.setCurrentIndex(self.default_settings["draw_mode"])
                self.pumping_reward_mode_Draw_comboBox.setCurrentIndex(self.default_settings["draw_pumping"])
                self.pumping_reward_font_size_SpinBox.setValue(self.default_settings["font_size"])
                self.pumping_reward_Animation_comboBox.setCurrentIndex(self.default_settings["animation_mode"])
                self.pumping_reward_animation_interval_SpinBox.setValue(self.default_settings["animation_interval"])
                self.pumping_reward_animation_auto_play_SpinBox.setValue(self.default_settings["animation_auto_play"])
                self.pumping_reward_Animation_comboBox.setCurrentIndex(self.default_settings["animation_mode"])
                self.pumping_reward_display_format_comboBox.setCurrentIndex(self.default_settings["display_format"])
                self.save_settings()
        except Exception as e:
            logger.error(f"加载设置时出错: {e}")
            self.pumping_reward_Draw_comboBox.setCurrentIndex(self.default_settings["draw_mode"])
            self.pumping_reward_mode_Draw_comboBox.setCurrentIndex(self.default_settings["draw_pumping"])
            self.pumping_reward_font_size_SpinBox.setValue(self.default_settings["font_size"])
            self.pumping_reward_Animation_comboBox.setCurrentIndex(self.default_settings["animation_mode"])
            self.pumping_reward_animation_interval_SpinBox.setValue(self.default_settings["animation_interval"])
            self.pumping_reward_animation_auto_play_SpinBox.setValue(self.default_settings["animation_auto_play"])
            self.pumping_reward_display_format_comboBox.setCurrentIndex(self.default_settings["display_format"])

            self.save_settings()
    
    def save_settings(self):
        # 先读取现有设置
        existing_settings = {}
        if path_manager.file_exists(self.settings_file):
            with open_file(self.settings_file, 'r', encoding='utf-8') as f:
                try:
                    existing_settings = json.load(f)
                except json.JSONDecodeError:
                    existing_settings = {}
        
        # 更新pumping_reward部分的所有设置
        if "pumping_reward" not in existing_settings:
            existing_settings["pumping_reward"] = {}
            
        pumping_reward_settings = existing_settings["pumping_reward"]
        # 只保存索引值
        pumping_reward_settings["draw_mode"] = self.pumping_reward_Draw_comboBox.currentIndex()
        pumping_reward_settings["draw_pumping"] = self.pumping_reward_mode_Draw_comboBox.currentIndex()
        pumping_reward_settings["animation_mode"] = self.pumping_reward_Animation_comboBox.currentIndex()
        pumping_reward_settings["animation_interval"] = self.pumping_reward_animation_interval_SpinBox.value()
        pumping_reward_settings["animation_auto_play"] = self.pumping_reward_animation_auto_play_SpinBox.value()
        pumping_reward_settings["display_format"] = self.pumping_reward_display_format_comboBox.currentIndex()

        # 保存字体大小
        try:
            font_size = int(self.pumping_reward_font_size_SpinBox.value())
            if 30 <= font_size <= 200:
                pumping_reward_settings["font_size"] = font_size
            # else:
            #     logger.error(f"字体大小超出范围: {font_size}")
        except ValueError:
            # logger.warning(f"无效的字体大小输入: {self.pumping_reward_font_size_edit.text()}")
            pass
        
        ensure_dir(Path(self.settings_file).parent)
        with open_file(self.settings_file, 'w', encoding='utf-8') as f:
            json.dump(existing_settings, f, indent=4)

    # 读取颜色设置
    def load_color_settings(self):
        existing_settings = {}
        if path_manager.file_exists(self.settings_file):
            with open_file(self.settings_file, 'r', encoding='utf-8') as f:
                try:
                    existing_settings = json.load(f)
                except json.JSONDecodeError:
                    existing_settings = {}
        pumping_reward_settings = existing_settings.get("pumping_reward", {})
        self.pumping_reward_animation_color_fixed = (pumping_reward_settings.get("_animation_color", "#ffffff"))
        self.pumping_reward_result_color_fixed = (pumping_reward_settings.get("_result_color", "#ffffff"))

    def save_color_settings(self, color_name, color_type):
        # 先读取现有设置
        existing_settings = {}
        if path_manager.file_exists(self.settings_file):
            with open_file(self.settings_file, 'r', encoding='utf-8') as f:
                try:
                    existing_settings = json.load(f)
                except json.JSONDecodeError:
                    existing_settings = {}
        
        # 更新pumping_reward部分的所有设置
        if "pumping_reward" not in existing_settings:
            existing_settings["pumping_reward"] = {}

        pumping_reward_settings = existing_settings["pumping_reward"]
        if color_type == "animation":
            pumping_reward_settings["_animation_color"] = color_name
        elif color_type == "result":
            pumping_reward_settings["_result_color"] = color_name
        
        ensure_dir(Path(self.settings_file).parent)
        with open_file(self.settings_file, 'w', encoding='utf-8') as f:
            json.dump(existing_settings, f, indent=4)