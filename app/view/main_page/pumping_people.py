from qfluentwidgets import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtMultimedia import *

import os
import glob
import json
import random
import re
import datetime
import math
from loguru import logger
from random import SystemRandom
system_random = SystemRandom()

from app.common.config import get_theme_icon, load_custom_font, restore_volume, is_dark_theme
from app.common.path_utils import path_manager, open_file, remove_file, ensure_dir


is_dark = is_dark_theme(qconfig)

class pumping_people(QWidget):
    refresh_signal = pyqtSignal()
    def __init__(self, parent=None):
        super().__init__(parent)
        # 设置对象名称，用于快捷键功能识别
        self.setObjectName("PumpingInterface")
        # 定义变量
        self.is_animating = False
        self.max_draw_times_per_person = 1
        self.animation_timer = None
        self.clear_timer = None  # 添加计时器变量，用于自动清除临时抽取记录
        # 音乐播放器初始化 ✧(◍˃̶ᗜ˂̶◍)✩ 感谢白露提供的播放器
        self.music_player = QMediaPlayer()
        self.initUI()
        
        # 连接清理信号
        self._connect_cleanup_signal()
    
    def start_draw(self):
        """开始抽选学生"""
        # 获取抽选模式和动画模式设置
        try:
            with open_file(path_manager.get_settings_path(), 'r', encoding='utf-8') as f:
                settings = json.load(f)
                pumping_people_animation_mode = settings['pumping_people']['animation_mode']
                self.interval = settings['pumping_people']['animation_interval']
                self.auto_play = settings['pumping_people']['animation_auto_play']
                self.animation_music_enabled = settings['pumping_people']['animation_music_enabled']
                self.result_music_enabled = settings['pumping_people']['result_music_enabled']
                self.animation_music_volume = settings['pumping_people']['animation_music_volume']
                self.result_music_volume = settings['pumping_people']['result_music_volume']
                self.music_fade_in = settings['pumping_people']['music_fade_in']
                self.music_fade_out = settings['pumping_people']['music_fade_out']
                self.max_draw_times_per_person = settings['pumping_people'].get('Draw_pumping', 1)
                
        except Exception as e:
            pumping_people_animation_mode = 0
            self.interval = 100
            self.auto_play = 5
            self.animation_music_enabled = False
            self.result_music_enabled = False
            self.animation_music_volume = 5
            self.result_music_volume = 5
            self.music_fade_in = 300
            self.music_fade_out = 300
            self.max_draw_times_per_person = 1
            logger.error(f"加载设置失败: {e}, 使用默认设置")
            
        # 根据动画模式执行不同逻辑
        if pumping_people_animation_mode == 0:  # 手动停止动画
            self.start_button.setText("停止")
            if self.animation_music_enabled:
                self._play_animation_music()
            self.is_animating = True
            self.animation_timer = QTimer()
            self.animation_timer.timeout.connect(self._show_random_student)
            self.animation_timer.start(self.interval)
            self.start_button.clicked.disconnect()
            self.start_button.clicked.connect(self._stop_animation)
            
        elif pumping_people_animation_mode == 1:  # 自动播放完整动画
            self._play_full_animation()
            
        elif pumping_people_animation_mode == 2:  # 直接显示结果
            self._show_result_directly()
        
    def _start_clear_timer(self):
        """启动计时器，在设置的时间后自动清除临时抽取记录"""
        # 如果已有计时器在运行，先停止它
        if self.clear_timer is not None:
            self.clear_timer.stop()
            self.clear_timer = None
            
        try:
            # 读取设置中的定时清理时间
            with open_file(path_manager.get_settings_path(), 'r', encoding='utf-8') as f:
                settings = json.load(f)
                clear_time = settings['pumping_people']['max_draw_count']
                
            # 只有在"定时清临时记录"模式下才启动计时器
            if clear_time > 0:  # 3是"定时清临时记录"选项的索引
                self.clear_timer = QTimer()
                self.clear_timer.setSingleShot(True)  # 单次触发
                self.clear_timer.timeout.connect(lambda: self._clean_temp_files())
                self.clear_timer.timeout.connect(lambda: self.clear_layout(self.result_grid))
                self.clear_timer.timeout.connect(lambda: self.update_total_count())
                self.clear_timer.start(clear_time * 1000)  # 转换为毫秒
                logger.info(f"已启动计时器，将在{clear_time}秒后自动清除临时抽取记录")
        except Exception as e:
            logger.error(f"启动计时器时出错: {e}")
    
    def _stop_clear_timer(self):
        """停止计时器"""
        if self.clear_timer is not None:
            self.clear_timer.stop()
            self.clear_timer = None
            logger.info("已停止计时器")
    
    def _show_random_student(self):
        """显示随机学生（用于动画效果）"""
        class_name = self.class_combo.currentText()
        group_name = self.group_combo.currentText()
        genders = self.gender_combo.currentText()

        if class_name and class_name not in ["你暂未添加班级", "加载班级列表失败", "你暂未添加小组", "加载小组列表失败"] and group_name and group_name not in ["你暂未添加小组", "加载小组列表失败"]:
            student_file = path_manager.get_resource_path("list", f"{class_name}.json")

            if group_name == '抽取全班学生':
                draw_record_file = path_manager.get_temp_path(f"{class_name}_{group_name}_{genders}.json")
            elif group_name == '抽取小组组号':
                draw_record_file = path_manager.get_temp_path(f"{class_name}_{group_name}.json")
            else:
                draw_record_file = path_manager.get_temp_path(f"{class_name}_{group_name}_{genders}.json")
            
            # 创建Temp目录如果不存在
            os.makedirs(os.path.dirname(draw_record_file), exist_ok=True)
            
            # 初始化抽取记录文件
            if not path_manager.file_exists(draw_record_file):
                with open_file(draw_record_file, 'w', encoding='utf-8') as f:
                    json.dump([], f, ensure_ascii=False, indent=4)
            
            # 读取已抽取记录
            record_data = []
            with open_file(draw_record_file, 'r', encoding='utf-8') as f:
                try:
                    record_data = json.load(f)
                except json.JSONDecodeError:
                    record_data = []

            if path_manager.file_exists(student_file):
                with open_file(student_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    cleaned_data = []
                    # 获取学生列表
                    if group_name == '抽取全班学生':
                        if genders == '抽取所有性别':
                            for student_name, student_info in data.items():
                                if isinstance(student_info, dict) and 'id' in student_info:
                                    id = student_info.get('id', '')
                                    name = student_name.replace('【', '').replace('】', '')
                                    gender = student_info.get('gender', '')
                                    group = student_info.get('group', '')
                                    exist = student_info.get('exist', True)
                                    cleaned_data.append((id, name, exist))
                        else:
                            for student_name, student_info in data.items():
                                if isinstance(student_info, dict) and 'id' in student_info:
                                    id = student_info.get('id', '')
                                    name = student_name.replace('【', '').replace('】', '')
                                    gender = student_info.get('gender', '')
                                    group = student_info.get('group', '')
                                    exist = student_info.get('exist', True)
                                    if gender == genders:
                                        cleaned_data.append((id, name, exist))
                    elif group_name == '抽取小组组号':
                        groups = set()
                        for student_name, student_info in data.items():
                            if isinstance(student_info, dict) and 'id' in student_info:
                                id = student_info.get('id', '')
                                name = student_name.replace('【', '').replace('】', '')
                                gender = student_info.get('gender', '')
                                group = student_info.get('group', '')
                                exist = student_info.get('exist', True)
                                if group:  # 只添加非空小组
                                    groups.add((id, group, exist))
                        filtered_groups = [g for g in groups if g[1] not in record_data]
                        cleaned_data = sorted(list(filtered_groups), key=lambda x: self.sort_key(str(x)))
                    else:
                        if genders == '抽取所有性别':
                            for student_name, student_info in data.items():
                                if isinstance(student_info, dict) and 'id' in student_info:
                                    id = student_info.get('id', '')
                                    name = student_name.replace('【', '').replace('】', '')
                                    gender = student_info.get('gender', '')
                                    group = student_info.get('group', '')
                                    exist = student_info.get('exist', True)
                                    if group == group_name:
                                        cleaned_data.append((id, name, exist))
                        else:
                            for student_name, student_info in data.items():
                                if isinstance(student_info, dict) and 'id' in student_info:
                                    id = student_info.get('id', '')
                                    name = student_name.replace('【', '').replace('】', '')
                                    gender = student_info.get('gender', '')
                                    group = student_info.get('group', '')
                                    exist = student_info.get('exist', True)
                                    if gender == genders and group == group_name:
                                        cleaned_data.append((id, name, exist))

                    # 过滤学生信息的exist为False的学生
                    cleaned_data = list(filter(lambda x: x[2], cleaned_data))

                    # 如果设置了最大抽取次数，过滤掉已达到最大抽取次数的学生
                    if self.max_draw_times_per_person > 0:
                        # 创建一个集合，包含已达到最大抽取次数的学生
                        maxed_out_students = set()
                        for record in record_data:
                            # 如果记录中包含次数信息（格式：姓名_次数）
                            if '_' in record:
                                record_name, record_count = record.rsplit('_', 1)
                                try:
                                    count = int(record_count)
                                    # logger.debug(f"检查记录 {record}，姓名 {record_name}，次数 {count}，最大抽取次数 {self.max_draw_times_per_person}")
                                    if count >= self.max_draw_times_per_person:
                                        maxed_out_students.add(record_name)
                                except ValueError:
                                    # 如果次数解析失败，忽略这条记录
                                    pass
                        
                        # 过滤掉已达到最大抽取次数的学生
                        students = [s for s in cleaned_data if s[1].replace(' ', '') not in maxed_out_students and s[1].replace(' ', '') not in [x.replace(' ', '') for x in record_data if '_' not in x or x.rsplit('_', 1)[0] != s[1].replace(' ', '')]] or cleaned_data
                    else:
                        # 如果max_draw_times_per_person等于0，则允许重复抽取，不进行过滤
                        students = cleaned_data

                    if students:
                        # 从self.current_count获取抽取人数
                        draw_count = self.current_count
                        
                        # 抽取多个学生
                        selected_students = random.sample(students, min(draw_count, len(students)))
                        
                        # 清除旧布局和标签
                        if hasattr(self, 'container') and isinstance(self.container, list):
                            for label in self.container:
                                label.deleteLater()
                            self.container = []
                        elif hasattr(self, 'container') and isinstance(self.container, QWidget):
                            try:
                                if self.container:
                                    self.container.deleteLater()
                            except RuntimeError:
                                pass
                            del self.container

                        if hasattr(self, 'student_labels'):
                            for label in self.student_labels:
                                try:
                                    if label:
                                        label.deleteLater()
                                except RuntimeError:
                                    pass
                            self.student_labels = []
                            
                        # 删除布局中的所有内容
                        while self.result_grid.count(): 
                            item = self.result_grid.takeAt(0)
                            widget = item.widget()
                            if widget:
                                try:
                                    widget.deleteLater()
                                except RuntimeError:
                                    pass
                        
                        # 根据设置格式化学号显示
                        try:
                            with open_file(path_manager.get_settings_path(), 'r', encoding='utf-8') as f:
                                settings = json.load(f)
                                pumping_people_student_id = settings['pumping_people']['student_id']
                                pumping_people_student_name = settings['pumping_people']['student_name']
                                display_format = settings['pumping_people']['display_format']
                                font_size = settings['pumping_people']['font_size']
                                animation_color = settings['pumping_people']['animation_color']
                                _animation_color = settings['pumping_people'].get('_animation_color', '#ffffff')
                                show_student_image = settings['pumping_people']['show_student_image']
                        except Exception as e:
                            pumping_people_student_id = 0
                            pumping_people_student_name = 0
                            display_format = 0
                            font_size = 50
                            animation_color = 0
                            _animation_color = '#ffffff'
                            show_student_image = False

                        # 创建新布局
                        vbox_layout = QGridLayout()
                        # 创建新标签列表
                        self.student_labels = []
                        for num, selected, exist in selected_students:
                            student_id_format = pumping_people_student_id
                            student_name_format = pumping_people_student_name
                            # 为每个奖励单独查找对应的图片文件
                            current_image_path = None
                            if show_student_image:
                                # 支持多种图片格式：png、jpg、jpeg、svg
                                image_extensions = ['.png', '.jpg', '.jpeg', '.svg']
                                
                                # 遍历所有支持的图片格式，查找存在的图片文件
                                for ext in image_extensions:
                                    temp_path = path_manager.get_resource_path("images", f"students/{selected}{ext}")
                                    if path_manager.file_exists(temp_path):
                                        current_image_path = str(temp_path)
                                        break
                                    else:
                                        current_image_path = None
                                        continue
                            
                            # 为每个标签创建独立的容器和布局
                            h_layout = QHBoxLayout()
                            h_layout.setSpacing(8)
                            h_layout.setContentsMargins(0, 0, 0, 0)
                            # 创建容器widget来包含水平布局
                            __container = QWidget()
                            __container.setLayout(h_layout)
                            if student_id_format == 0:
                                student_id_str = f"{num:02}"
                            elif student_id_format == 1:
                                student_id_str = f"{num:^5}"
                            else:
                                student_id_str = f"{num:02}"
                            
                            if (student_name_format == 0 and len(selected) == 2) and not group_name == '抽取小组组号':
                                name = f"{selected[0]}    {selected[1]}"
                            else:
                                name = selected

                            if group_name == '抽取小组组号':
                                # 定义格式常量
                                FORMAT_GROUP_RANDOM_MEMBER = 0
                                FORMAT_GROUP_RANDOM = 1
                                FORMAT_GROUP_SIMPLE = 2
                                FORMAT_GROUP_ARROW = 3
                                FORMAT_GROUP_ARROW_BRACKET = 4

                                # 格式映射字典
                                FORMAT_MAPPINGS = {
                                    FORMAT_GROUP_RANDOM_MEMBER: f"{{selected}}-随机组员:{{random_member}}",
                                    FORMAT_GROUP_RANDOM: f"{{selected}}-随机:{{random_member}}",
                                    FORMAT_GROUP_SIMPLE: f"{{selected}}-{{random_member}}",
                                    FORMAT_GROUP_ARROW: f"{{selected}}>{{random_member}}",
                                    FORMAT_GROUP_ARROW_BRACKET: f"{{selected}}>{{random_member}}<"
                                }

                                # 构建学生数据文件路径
                                student_file = path_manager.get_resource_path("list", f"{self.class_combo.currentText()}.json")
                                members = []

                                # 加载学生数据和筛选组成员
                                if path_manager.file_exists(student_file):
                                    try:
                                        with open_file(student_file, 'r', encoding='utf-8') as f:
                                            data = json.load(f)
                                            members = [
                                                name.replace('【', '').replace('】', '') 
                                                for name, info in data.items()
                                                if isinstance(info, dict) and info.get('group') == selected and info.get('exist', True)
                                            ]
                                    except (json.JSONDecodeError, IOError) as e:
                                        # 记录具体错误但不中断程序
                                        print(f"加载学生数据失败: {str(e)}")

                                # 随机选择成员
                                random_member = random.choice(members) if members else ''
                                display_text = selected  # 默认显示组号

                                # 加载显示设置
                                try:
                                    with open_file(path_manager.get_settings_path(), 'r', encoding='utf-8') as f:
                                        settings = json.load(f)
                                        show_random = settings['pumping_people'].get('show_random_member', False)
                                        format_str = settings['pumping_people'].get('random_member_format', FORMAT_GROUP_SIMPLE)
                                except (json.JSONDecodeError, IOError, KeyError) as e:
                                    show_random = False
                                    format_str = FORMAT_GROUP_SIMPLE
                                    print(f"加载设置失败: {str(e)}")

                                # 应用格式设置
                                if show_random and random_member and format_str in FORMAT_MAPPINGS:
                                    display_text = FORMAT_MAPPINGS[format_str].format(
                                        selected=selected, 
                                        random_member=random_member
                                    )

                                label = BodyLabel(display_text)
                            else:
                                if display_format == 1:
                                    self.result_grid.setAlignment(Qt.AlignCenter)
                                    if draw_count == 1:
                                        if show_student_image:
                                            if current_image_path != None:
                                                avatar = AvatarWidget(current_image_path)
                                            else:
                                                avatar = AvatarWidget()
                                                avatar.setText(name)
                                            avatar.setRadius(font_size*2)
                                            text_label = BodyLabel(f"{name}")
                                            h_layout.addWidget(avatar)
                                            h_layout.addWidget(text_label)
                                            
                                            # 使用容器作为标签
                                            label = __container
                                        else:
                                            label = BodyLabel(f"{name}")
                                    else:
                                        self.result_grid.setAlignment(Qt.AlignTop | Qt.AlignCenter)
                                        if show_student_image:
                                            if current_image_path != None:
                                                avatar = AvatarWidget(current_image_path)
                                            else:
                                                avatar = AvatarWidget()
                                                avatar.setText(name)
                                            avatar.setRadius(font_size//2)
                                            if current_image_path == None:
                                                avatar.setText(name)
                                            text_label = BodyLabel(f"{name}")
                                            h_layout.addWidget(avatar)
                                            h_layout.addWidget(text_label)
                                            
                                            # 使用容器作为标签
                                            label = __container
                                        else:
                                            label = BodyLabel(f"{name}")
                                elif display_format == 2:
                                    self.result_grid.setAlignment(Qt.AlignCenter)
                                    if draw_count == 1:
                                        if show_student_image:
                                            if current_image_path != None:
                                                avatar = AvatarWidget(current_image_path)
                                            else:
                                                avatar = AvatarWidget()
                                                avatar.setText(name)
                                            avatar.setRadius(font_size*2)
                                            text_label = BodyLabel(f"{student_id_str}")
                                            h_layout.addWidget(avatar)
                                            h_layout.addWidget(text_label)
                                            
                                            # 使用容器作为标签
                                            label = __container
                                        else:
                                            label = BodyLabel(f"{student_id_str}")
                                    else:
                                        self.result_grid.setAlignment(Qt.AlignTop | Qt.AlignCenter)
                                        if show_student_image:
                                            if current_image_path != None:
                                                avatar = AvatarWidget(current_image_path)
                                            else:
                                                avatar = AvatarWidget()
                                                avatar.setText(name)
                                            avatar.setRadius(font_size//2)
                                            if current_image_path == None:
                                                avatar.setText(name)
                                            text_label = BodyLabel(f"{student_id_str}")
                                            h_layout.addWidget(avatar)
                                            h_layout.addWidget(text_label)
                                            
                                            # 使用容器作为标签
                                            label = __container
                                        else:
                                            label = BodyLabel(f"{student_id_str}")
                                else:
                                    self.result_grid.setAlignment(Qt.AlignCenter)
                                    if draw_count == 1:
                                        if show_student_image:
                                            if current_image_path != None:
                                                avatar = AvatarWidget(current_image_path)
                                            else:
                                                avatar = AvatarWidget()
                                                avatar.setText(name)
                                            avatar.setRadius(font_size*2)
                                            text_label = BodyLabel(f"{student_id_str}\n{name}")
                                            h_layout.addWidget(avatar)
                                            h_layout.addWidget(text_label)
                                            
                                            # 使用容器作为标签
                                            label = __container
                                        else:
                                            label = BodyLabel(f"{student_id_str}\n{name}")
                                    else:
                                        self.result_grid.setAlignment(Qt.AlignTop | Qt.AlignCenter)
                                        if show_student_image:
                                            if current_image_path != None:
                                                avatar = AvatarWidget(current_image_path)
                                            else:
                                                avatar = AvatarWidget()
                                                avatar.setText(name)
                                            avatar.setRadius(font_size//2)
                                            if current_image_path == None:
                                                avatar.setText(name)
                                            text_label = BodyLabel(f"{student_id_str} {name}")
                                            h_layout.addWidget(avatar)
                                            h_layout.addWidget(text_label)
                                            
                                            # 使用容器作为标签
                                            label = __container
                                        else:
                                            label = BodyLabel(f"{student_id_str} {name}")

                            widget = None  # 初始化widget变量
                            # 根据label类型应用不同的样式设置
                            if isinstance(label, QWidget) and hasattr(label, 'layout') and label.layout() is not None:
                                # 如果是容器类型，对容器内的文本标签应用样式
                                layout = label.layout()
                                if layout:
                                    for i in range(layout.count()):
                                        item = layout.itemAt(i)
                                        widget = item.widget()
                                        if isinstance(widget, BodyLabel):
                                            widget.setAlignment(Qt.AlignCenter)
                                            if animation_color == 1:
                                                widget.setStyleSheet(f"color: {self._generate_vibrant_color()};")
                                            elif animation_color == 2:
                                                widget.setStyleSheet(f"color: {_animation_color};")
                            else:
                                # 如果是普通的BodyLabel，直接应用样式
                                label.setAlignment(Qt.AlignCenter)
                                if animation_color == 1:
                                    label.setStyleSheet(f"color: {self._generate_vibrant_color()};")
                                elif animation_color == 2:
                                    label.setStyleSheet(f"color: {_animation_color};")
                            
                            # 为widget设置字体（如果widget存在）
                            if widget is not None:
                                widget.setFont(QFont(load_custom_font(), font_size))
                            # 为label设置字体
                            label.setFont(QFont(load_custom_font(), font_size))
                            vbox_layout.addWidget(label)
                            self.student_labels.append(label)

                        # 计算所有标签的宽度之和，并考虑间距和边距
                        if self.student_labels:
                            total_width = sum(label.sizeHint().width() for label in self.student_labels) + \
                                          len(self.student_labels) * 180
                            available_width = self.width() - 20
                            
                            # 如果总宽度超过可用宽度，则计算每行最多能放几个标签
                            if total_width > available_width:
                                avg_label_width = total_width / len(self.student_labels)
                                max_columns = max(1, int(available_width // avg_label_width))
                            else:
                                max_columns = len(self.student_labels)  # 一行显示所有标签
                        else:
                            max_columns = 1
                        
                        # 复用 container 和 vbox_layout
                        if not hasattr(self, 'container'):
                            self.container = QWidget()
                            self.vbox_layout = QGridLayout()
                            # 设置标签之间的水平和垂直间距
                            self.vbox_layout.setSpacing(15)  # 设置统一的间距
                            self.vbox_layout.setHorizontalSpacing(20)  # 设置水平间距
                            self.vbox_layout.setVerticalSpacing(10)   # 设置垂直间距
                            self.container.setLayout(self.vbox_layout)
                        else:
                            # 清空旧标签
                            for i in reversed(range(self.vbox_layout.count())):
                                item = self.vbox_layout.itemAt(i)
                                if item.widget():
                                    item.widget().setParent(None)

                        for i, label in enumerate(self.student_labels):
                            row = i // max_columns
                            col = i % max_columns
                            self.vbox_layout.addWidget(label, row, col)
                        
                        self.result_grid.addWidget(self.container)
                        
                        return
                    else:
                        return

        
        else:
            self.clear_layout(self.result_grid)
            if hasattr(self, 'container'):
                self.container.deleteLater()
                del self.container
            if hasattr(self, 'student_labels'):
                for label in self.student_labels:
                    label.deleteLater()
            
            # 创建错误标签
            error_label = BodyLabel("-- 抽选失败")
            error_label.setAlignment(Qt.AlignCenter)
            
            try:
                with open_file(path_manager.get_settings_path(), 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    font_size = settings['pumping_people']['font_size']
            except Exception as e:
                font_size = 50
                logger.error(f"加载字体设置失败: {e}, 使用默认设置")
            error_label.setFont(QFont(load_custom_font(), font_size))
            self.result_grid.addWidget(error_label)
    
    # 停止动画并显示最终结果
    def _stop_animation(self):
        """停止动画并显示最终结果"""
        self.animation_timer.stop()
        if self.animation_music_enabled:
            # 创建音量渐出动画 ～(￣▽￣)～* 白露负责温柔收尾
            self.fade_out_animation = QPropertyAnimation(self.music_player, b"volume")
            self.fade_out_animation.setDuration(self.music_fade_out)
            self.fade_out_animation.setStartValue(self.music_player.volume())
            self.fade_out_animation.setEndValue(0)
            self.fade_out_animation.setEasingCurve(QEasingCurve.InOutQuad)
        
            # 动画结束后停止播放
            def stop_after_fade():
                self.music_player.stop()
                self.music_player.setVolume(100)  # 重置音量为最大，准备下次播放
            
            self.fade_out_animation.finished.connect(stop_after_fade)
            self.fade_out_animation.start()
        if self.result_music_enabled:
            self._play_result_music()
        self.is_animating = False
        self.start_button.setText("开始")
        self.start_button.clicked.disconnect()
        self.start_button.clicked.connect(self.start_draw)
        
        # 显示最终结果
        self.random()
        self.voice_play()
    
    def _play_full_animation(self):
        """播放完整动画（快速显示n个随机学生后显示最终结果）
        星野：动画开始啦~ 让我们看看谁是幸运儿！🎡
        白露：背景音乐和动画会同步播放哦~ 🎵"""
        self.is_animating = True
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self._show_random_student)
        self.animation_timer.start(self.interval)
        if self.animation_music_enabled:
            self._play_animation_music()
        self.start_button.setEnabled(False)  # 禁用按钮（星野：抽奖中不能重复点击哦~）
        
        # n次随机后停止
        QTimer.singleShot(self.auto_play * self.interval, lambda: [
            self.animation_timer.stop(),
            self._stop_animation(),
            self.start_button.setEnabled(True)  # 白露：按钮恢复啦~ 可以再次抽奖哦！😊
          ])
    
    # 直接显示结果（无动画效果）
    def _show_result_directly(self):
        """直接显示结果（无动画效果）"""
        if self.result_music_enabled:
            self._play_result_music()
        self.random()
        self.voice_play()

    def _play_result_music(self):
        """播放结果音乐
        星野：恭喜你抽中啦！🎉 来听听胜利的音乐吧~
        白露：结果音乐和动画音乐是分开的呢~ 真有趣！"""
        try:
            BGM_RESULT_PATH = path_manager.get_resource_path("music", "pumping_people/result_music")
            # 检查音乐目录是否存在
            if not path_manager.file_exists(BGM_RESULT_PATH):
                logger.error(f"结果音乐目录不存在: {BGM_RESULT_PATH}")
                return

            # 获取所有支持的音乐文件 (｡･ω･｡)ﾉ♡
            music_extensions = ['*.mp3', '*.wav', '*.ogg', '*.flac']
            music_files = []
            for ext in music_extensions:
                music_files.extend(glob.glob(os.path.join(BGM_RESULT_PATH, ext)))

            if not music_files:
                logger.error(f"结果音乐目录中没有找到音乐文件: {BGM_RESULT_PATH}")
                return

            # 随机选择一首音乐 ♪(^∇^*)
            selected_music = random.choice(music_files)
            logger.info(f"正在播放结果音乐: {selected_music}")

            # 设置并播放音乐，准备渐入效果 ✧*｡٩(ˊᗜˋ*)و✧*｡
            self.music_player.setMedia(QMediaContent(QUrl.fromLocalFile(selected_music)))
            if self.music_player.mediaStatus() == QMediaPlayer.InvalidMedia:
                logger.error(f"无效的媒体文件: {selected_music}")
                return
            self.music_player.setVolume(0)  # 初始音量设为0
            self.music_player.play()
            # 连接错误信号
            self.music_player.error.connect(self.handle_media_error)
            
            # 创建音量渐入动画 ～(￣▽￣)～* 星野的魔法音量调节
            self.fade_in_animation = QPropertyAnimation(self.music_player, b"volume")
            self.fade_in_animation.setDuration(self.music_fade_in)
            self.fade_in_animation.setStartValue(0)
            self.fade_in_animation.setEndValue(self.result_music_volume)
            self.fade_in_animation.setEasingCurve(QEasingCurve.InOutQuad)
            self.fade_in_animation.start()

            # 延迟一段时间后再开始音量渐出动画，确保音乐能正常播放
            QTimer.singleShot(self.music_fade_in + 1000, self._start_fade_out_animation)

        except Exception as e:
            logger.error(f"播放结果音乐时出错: {e}")

    def _start_fade_out_animation(self):
        """开始音量渐出动画"""
        if self.music_player.state() == QMediaPlayer.PlayingState:
            # 创建音量渐出动画
            fade_out_animation = QPropertyAnimation(self.music_player, b"volume")
            fade_out_animation.setDuration(self.music_fade_out)
            fade_out_animation.setStartValue(self.music_player.volume())
            fade_out_animation.setEndValue(0)
            fade_out_animation.setEasingCurve(QEasingCurve.InOutQuad)

            # 动画结束后停止播放并重置音量
            def final_stop():
                self.music_player.stop()
                self.music_player.setVolume(self.result_music_volume)

            fade_out_animation.finished.connect(final_stop)
            fade_out_animation.start()
    
    # 根据抽取模式抽选学生
    def random(self):
        """根据抽取模式抽选学生"""
        class_name = self.class_combo.currentText()
        group_name = self.group_combo.currentText()
        genders = self.gender_combo.currentText()
        
        if class_name and class_name not in ["你暂未添加班级", "加载班级列表失败", "你暂未添加小组", "加载小组列表失败"] and group_name and group_name not in ["你暂未添加小组", "加载小组列表失败"]:
            student_file = path_manager.get_resource_path("list", f"{class_name}.json")

            if group_name == '抽取全班学生':
                draw_record_file = path_manager.get_resource_path("Temp", f"{class_name}_{group_name}_{genders}.json")
            elif group_name == '抽取小组组号':
                draw_record_file = path_manager.get_resource_path("Temp", f"{class_name}_{group_name}.json")
            else:
                draw_record_file = path_manager.get_resource_path("Temp", f"{class_name}_{group_name}_{genders}.json")
            
            # 创建Temp目录如果不存在
            path_manager.ensure_directory_exists(draw_record_file.parent)
            
            # 初始化抽取记录文件
            if not path_manager.file_exists(draw_record_file):
                with open_file(draw_record_file, 'w', encoding='utf-8') as f:
                    json.dump([], f, ensure_ascii=False, indent=4)
            
            # 读取已抽取记录
            record_data = []
            with open_file(draw_record_file, 'r', encoding='utf-8') as f:
                try:
                    record_data = json.load(f)
                except json.JSONDecodeError:
                    record_data = []
            
            if path_manager.file_exists(student_file):
                with open_file(student_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    cleaned_data = []
                    __cleaned_data = []
                    
                    # 获取学生列表
                    if group_name == '抽取全班学生':
                        if genders == '抽取所有性别':
                            for student_name, student_info in data.items():
                                if isinstance(student_info, dict) and 'id' in student_info:
                                    id = student_info.get('id', '')
                                    name = student_name.replace('【', '').replace('】', '')
                                    gender = student_info.get('gender', '')
                                    group = student_info.get('group', '')
                                    exist = student_info.get('exist', True)
                                    cleaned_data.append((id, name, exist))
                                    __cleaned_data.append((id, name, gender, group, exist))
                        else:
                            for student_name, student_info in data.items():
                                if isinstance(student_info, dict) and 'id' in student_info:
                                    id = student_info.get('id', '')
                                    name = student_name.replace('【', '').replace('】', '')
                                    gender = student_info.get('gender', '')
                                    group = student_info.get('group', '')
                                    exist = student_info.get('exist', True)
                                    if gender == genders:
                                        cleaned_data.append((id, name, exist))
                                        __cleaned_data.append((id, name, gender, group, exist))
                    elif group_name == '抽取小组组号':
                        groups = set()
                        for student_name, student_info in data.items():
                            if isinstance(student_info, dict) and 'id' in student_info:
                                id = student_info.get('id', '')
                                name = student_name.replace('【', '').replace('】', '')
                                gender = student_info.get('gender', '')
                                group = student_info.get('group', '')
                                exist = student_info.get('exist', True)
                                if group:  # 只添加非空小组
                                    groups.add((id, group, exist))
                                    __cleaned_data.append((id, name, gender, group, exist))
                        cleaned_data = sorted(list(groups), key=lambda x: self.sort_key(str(x)))
                    else:
                        if genders == '抽取所有性别':
                            for student_name, student_info in data.items():
                                if isinstance(student_info, dict) and 'id' in student_info:
                                    id = student_info.get('id', '')
                                    name = student_name.replace('【', '').replace('】', '')
                                    gender = student_info.get('gender', '')
                                    group = student_info.get('group', '')
                                    exist = student_info.get('exist', True)
                                    if group == group_name:
                                        cleaned_data.append((id, name, exist))
                                        __cleaned_data.append((id, name, gender, group, exist))
                        else:
                            for student_name, student_info in data.items():
                                if isinstance(student_info, dict) and 'id' in student_info:
                                    id = student_info.get('id', '')
                                    name = student_name.replace('【', '').replace('】', '')
                                    gender = student_info.get('gender', '')
                                    group = student_info.get('group', '')
                                    exist = student_info.get('exist', True)
                                    if gender == genders and group == group_name:
                                        cleaned_data.append((id, name, exist))
                                        __cleaned_data.append((id, name, gender, group, exist))

                    # 过滤学生信息的exist为False的学生
                    cleaned_data = list(filter(lambda x: x[2], cleaned_data))
                    __cleaned_data = list(filter(lambda x: x[4], __cleaned_data))

                    if self.max_draw_times_per_person == 0:
                        available_students = cleaned_data
                    elif self.max_draw_times_per_person != 0:
                        # 解析记录数据，获取已达到最大抽取次数的学生
                        maxed_out_students = set()
                        for record in record_data:
                            if '_' in record:
                                name, times_str = record.rsplit('_', 1)
                                try:
                                    times = int(times_str)
                                    if times >= self.max_draw_times_per_person:
                                        maxed_out_students.add(name)
                                except ValueError:
                                    # 如果解析失败，默认为1次
                                    pass
                        
                        # 过滤掉已达到最大抽取次数的学生
                        available_students = [s for s in cleaned_data if s[1].replace(' ', '') not in [x.replace(' ', '') for x in record_data] and s[1] not in maxed_out_students]

                    if available_students:
                        # 从self.current_count获取抽取人数
                        draw_count = self.current_count
                        
                        # 根据设置选项选择随机方法
                        use_system_random = self.get_random_method_setting()
                        
                        if use_system_random == 1:  # 使用SystemRandom的方式-不可预测抽取
                            if len(available_students) <= draw_count:
                                selected_students = available_students
                            else:
                                selected_students = system_random.sample(available_students, draw_count)

                        elif use_system_random == 2 or use_system_random == 3:  # 动态权重调整抽取系统
                            # 加载历史记录
                            history_file = path_manager.get_resource_path("history", f"{class_name}.json")
                            history_data = {}
                            if path_manager.file_exists(history_file):
                                with open_file(history_file, 'r', encoding='utf-8') as f:
                                    try:
                                        history_data = json.load(f)
                                    except json.JSONDecodeError:
                                        history_data = {}
                            
                            # 初始化权重数据
                            weights = {}
                            
                            for student_id, student_name, exist in available_students:
                                # 获取学生历史记录
                                student_history = history_data.get("pumping_people", {}).get(student_name, {
                                    "total_number_of_times": 0,
                                    "last_drawn_time": None,
                                    "rounds_missed": 0,
                                    "time": []
                                })
                                
                                # 基础参数配置
                                COLD_START_ROUNDS = 10       # 冷启动轮次
                                BASE_WEIGHT = 1.0            # 基础权重

                                # 计算各权重因子
                                # 因子1: 抽取频率惩罚（被抽中次数越多权重越低）
                                frequency_factor = 1.0 / math.sqrt(student_history["total_number_of_times"] * 2 + 1)

                                # 因子2: 小组平衡（仅当有足够数据时生效）
                                group_factor = 1.0
                                # 获取有效小组统计数量（值>0的条目）
                                valid_groups = [v for v in history_data.get("group_stats", {}).values() if v > 0]
                                if len(valid_groups) > 3:  # 有效小组数量达标
                                    for student in __cleaned_data:
                                        if student[1] == student_name:
                                            current_student_group = student[3]
                                            break
                                    else:
                                        current_student_group = ''
                                    group_history = max(history_data["group_stats"].get(current_student_group, 0), 0)
                                    group_factor = 1.0 / (group_history * 0.2 + 1)

                                # 因子3: 性别平衡（仅当两种性别都有数据时生效）
                                gender_factor = 1.0
                                # 获取有效性别统计数量（值>0的条目）
                                valid_gender = [v for v in history_data.get("gender_stats", {}).values() if v > 0]
                                if len(valid_gender) > 3:  # 有效性别数量达标
                                    for student in __cleaned_data:
                                        if student[1] == student_name:
                                            current_student_gender = student[2]
                                            break
                                    else:
                                        current_student_gender = ''
                                    gender_history = max(history_data["gender_stats"].get(current_student_gender, 0), 0)
                                    gender_factor = 1.0 / (gender_history * 0.2 + 1)

                                # 冷启动特殊处理
                                current_round = history_data.get("total_rounds", 0)
                                if current_round < COLD_START_ROUNDS:
                                    frequency_factor = min(0.8, frequency_factor)  # 防止新学生权重过低

                                # 综合权重计算
                                student_weights = {
                                    'base': BASE_WEIGHT * 0.2,                    # 基础权重
                                    'frequency': frequency_factor * 3.0,          # 频率惩罚
                                    'group': group_factor * 0.8,                  # 小组平衡
                                    'gender': gender_factor * 0.8                 # 性别平衡
                                }

                                if self.max_draw_times_per_person != 0 and student_name in record_data:
                                    # 如果是不重复抽取模式，且该学生已被抽中，则权重为0
                                    comprehensive_weight = 0
                                else:
                                    comprehensive_weight = sum(student_weights.values())

                                # 5. 最终调整与限制
                                # 确保权重在合理范围内 (0.5~5.0)
                                final_weight = max(0.5, min(comprehensive_weight, 5.0))
                                weights[(student_id, student_name, exist)] = final_weight
                            
                            # 根据权重抽取学生
                            selected_students = []
                            remaining_students = available_students.copy()

                            use_system_random = self.get_random_method_setting()
                            if use_system_random == 3:
                                random_module = system_random
                            elif use_system_random == 2:
                                random_module = random
                            else:
                                random_module = random
                            
                            for _ in range(min(draw_count, len(available_students))):
                                total_weight = sum(weights[s] for s in remaining_students)
                                r = random_module.uniform(0, total_weight)
                                accumulator = 0
                                
                                for student in remaining_students:
                                    accumulator += weights[student]
                                    if accumulator >= r:
                                        selected_students.append(student)
                                        remaining_students.remove(student)
                                        break

                        else:  # 默认使用random的方式-可预测抽取
                            if len(available_students) <= draw_count:
                                selected_students = available_students
                            else:
                                selected_students = random.sample(available_students, draw_count)

                        # 更新历史记录
                        self._update_history(class_name, group_name, genders, selected_students)
                        
                        # 显示结果
                        if hasattr(self, 'container'):
                            self.container.deleteLater()
                            del self.container
                        if hasattr(self, 'student_labels'):
                            for label in self.student_labels:
                                label.deleteLater()

                        while self.result_grid.count(): 
                            item = self.result_grid.takeAt(0)
                            widget = item.widget()
                            if widget:
                                widget.deleteLater()
                        
                        try:
                            with open_file(path_manager.get_settings_path(), 'r', encoding='utf-8') as f:
                                settings = json.load(f)
                                pumping_people_student_id = settings['pumping_people']['student_id']
                                pumping_people_student_name = settings['pumping_people']['student_name']
                                display_format = settings['pumping_people']['display_format']
                                font_size = settings['pumping_people']['font_size']
                                animation_color = settings['pumping_people']['animation_color']
                                _result_color = settings['pumping_people'].get('_result_color', '#ffffff')
                                show_student_image = settings['pumping_people']['show_student_image']
                        except Exception as e:
                            pumping_people_student_id = 0
                            pumping_people_student_name = 0
                            display_format = 0
                            font_size = 50
                            animation_color = 0
                            _result_color = "#ffffff"
                            show_student_image = False

                        self.student_labels = []
                        for num, selected, exist in selected_students:
                            student_id_format = pumping_people_student_id
                            student_name_format = pumping_people_student_name
                            # 为每个奖励单独查找对应的图片文件
                            current_image_path = None
                            if show_student_image:
                                # 支持多种图片格式：png、jpg、jpeg、svg
                                image_extensions = ['.png', '.jpg', '.jpeg', '.svg']
                                
                                # 遍历所有支持的图片格式，查找存在的图片文件
                                for ext in image_extensions:
                                    temp_path = path_manager.get_resource_path("images", f"students/{selected}{ext}")
                                    if path_manager.file_exists(temp_path):
                                        current_image_path = str(temp_path)
                                        break
                                    else:
                                        current_image_path = None
                                        continue
                            
                            # 为每个标签创建独立的容器和布局
                            h_layout = QHBoxLayout()
                            h_layout.setSpacing(8)
                            h_layout.setContentsMargins(0, 0, 0, 0)
                            # 创建容器widget来包含水平布局
                            __container = QWidget()
                            __container.setLayout(h_layout)
                            if student_id_format == 0:
                                student_id_str = f"{num:02}"
                            elif student_id_format == 1:
                                student_id_str = f"{num:^5}"
                            else:
                                student_id_str = f"{num:02}"
                            
                            if (student_name_format == 0 and len(selected) == 2) and not group_name == '抽取小组组号':
                                name = f"{selected[0]}    {selected[1]}"
                            else:
                                name = selected

                            if group_name == '抽取小组组号':
                                # 定义格式常量
                                FORMAT_GROUP_RANDOM_MEMBER = 0
                                FORMAT_GROUP_RANDOM = 1
                                FORMAT_GROUP_SIMPLE = 2
                                FORMAT_GROUP_ARROW = 3
                                FORMAT_GROUP_ARROW_BRACKET = 4

                                # 格式映射字典
                                FORMAT_MAPPINGS = {
                                    FORMAT_GROUP_RANDOM_MEMBER: f"{{selected}}-随机组员:{{random_member}}",
                                    FORMAT_GROUP_RANDOM: f"{{selected}}-随机:{{random_member}}",
                                    FORMAT_GROUP_SIMPLE: f"{{selected}}-{{random_member}}",
                                    FORMAT_GROUP_ARROW: f"{{selected}}>{{random_member}}",
                                    FORMAT_GROUP_ARROW_BRACKET: f"{{selected}}>{{random_member}}<"
                                }

                                # 构建学生数据文件路径
                                student_file = path_manager.get_resource_path("list", f"{self.class_combo.currentText()}.json")
                                members = []

                                # 加载学生数据和筛选组成员
                                if path_manager.file_exists(student_file):
                                    try:
                                        with open_file(student_file, 'r', encoding='utf-8') as f:
                                            data = json.load(f)
                                            members = [
                                                name.replace('【', '').replace('】', '') 
                                                for name, info in data.items()
                                                if isinstance(info, dict) and info.get('group') == selected and info.get('exist', True)
                                            ]
                                    except (json.JSONDecodeError, IOError) as e:
                                        # 记录具体错误但不中断程序
                                        print(f"加载学生数据失败: {str(e)}")

                                # 随机选择成员
                                random_member = random.choice(members) if members else ''
                                display_text = selected  # 默认显示组号

                                # 加载显示设置
                                try:
                                    with open_file(path_manager.get_settings_path(), 'r', encoding='utf-8') as f:
                                        settings = json.load(f)
                                        show_random = settings['pumping_people'].get('show_random_member', False)
                                        format_str = settings['pumping_people'].get('random_member_format', FORMAT_GROUP_SIMPLE)
                                except (json.JSONDecodeError, IOError, KeyError) as e:
                                    show_random = False
                                    format_str = FORMAT_GROUP_SIMPLE
                                    print(f"加载设置失败: {str(e)}")

                                # 应用格式设置
                                if show_random and random_member and format_str in FORMAT_MAPPINGS:
                                    display_text = FORMAT_MAPPINGS[format_str].format(
                                        selected=selected, 
                                        random_member=random_member
                                    )

                                label = BodyLabel(display_text)
                            else:
                                if display_format == 1:
                                    self.result_grid.setAlignment(Qt.AlignCenter)
                                    if draw_count == 1:
                                        if show_student_image:
                                            if current_image_path != None:
                                                avatar = AvatarWidget(current_image_path)
                                            else:
                                                avatar = AvatarWidget()
                                                avatar.setText(name)
                                            avatar.setRadius(font_size*2)
                                            if current_image_path == None:
                                                avatar.setText(name)
                                            text_label = BodyLabel(f"{name}")
                                            h_layout.addWidget(avatar)
                                            h_layout.addWidget(text_label)
                                            
                                            # 使用容器作为标签
                                            label = __container
                                        else:
                                            label = BodyLabel(f"{name}")
                                    else:
                                        self.result_grid.setAlignment(Qt.AlignTop | Qt.AlignCenter)
                                        if show_student_image:
                                            if current_image_path != None:
                                                avatar = AvatarWidget(current_image_path)
                                            else:
                                                avatar = AvatarWidget()
                                                avatar.setText(name)
                                            avatar.setRadius(font_size//2)
                                            if current_image_path == None:
                                                avatar.setText(name)
                                            text_label = BodyLabel(f"{name}")
                                            h_layout.addWidget(avatar)
                                            h_layout.addWidget(text_label)
                                            
                                            # 使用容器作为标签
                                            label = __container
                                        else:
                                            label = BodyLabel(f"{name}")
                                elif display_format == 2:
                                    self.result_grid.setAlignment(Qt.AlignCenter)
                                    if draw_count == 1:
                                        if show_student_image:
                                            if current_image_path != None:
                                                avatar = AvatarWidget(current_image_path)
                                            else:
                                                avatar = AvatarWidget()
                                                avatar.setText(name)
                                            avatar.setRadius(font_size*2)
                                            text_label = BodyLabel(f"{student_id_str}")
                                            h_layout.addWidget(avatar)
                                            h_layout.addWidget(text_label)
                                            
                                            # 使用容器作为标签
                                            label = __container
                                        else:
                                            label = BodyLabel(f"{student_id_str}")
                                    else:
                                        self.result_grid.setAlignment(Qt.AlignTop | Qt.AlignCenter)
                                        if show_student_image:
                                            if current_image_path != None:
                                                avatar = AvatarWidget(current_image_path)
                                            else:
                                                avatar = AvatarWidget()
                                                avatar.setText(name)
                                            avatar.setRadius(font_size//2)
                                            if current_image_path == None:
                                                avatar.setText(name)
                                            text_label = BodyLabel(f"{student_id_str}")
                                            h_layout.addWidget(avatar)
                                            h_layout.addWidget(text_label)
                                            
                                            # 使用容器作为标签
                                            label = __container
                                        else:
                                            label = BodyLabel(f"{student_id_str}")
                                else:
                                    self.result_grid.setAlignment(Qt.AlignCenter)
                                    if draw_count == 1:
                                        if show_student_image:
                                            if current_image_path != None:
                                                avatar = AvatarWidget(current_image_path)
                                            else:
                                                avatar = AvatarWidget()
                                                avatar.setText(name)
                                            avatar.setRadius(font_size*2)
                                            text_label = BodyLabel(f"{student_id_str}\n{name}")
                                            h_layout.addWidget(avatar)
                                            h_layout.addWidget(text_label)
                                            
                                            # 使用容器作为标签
                                            label = __container
                                        else:
                                            label = BodyLabel(f"{student_id_str}\n{name}")
                                    else:
                                        self.result_grid.setAlignment(Qt.AlignTop | Qt.AlignCenter)
                                        if show_student_image:
                                            if current_image_path != None:
                                                avatar = AvatarWidget(current_image_path)
                                            else:
                                                avatar = AvatarWidget()
                                                avatar.setText(name)
                                            avatar.setRadius(font_size//2)
                                            if current_image_path == None:
                                                avatar.setText(name)
                                            text_label = BodyLabel(f"{student_id_str} {name}")
                                            h_layout.addWidget(avatar)
                                            h_layout.addWidget(text_label)
                                            
                                            # 使用容器作为标签
                                            label = __container
                                        else:
                                            label = BodyLabel(f"{student_id_str} {name}")

                            widget = None  # 初始化widget变量
                            # 根据label类型应用不同的样式设置
                            if isinstance(label, QWidget) and hasattr(label, 'layout') and label.layout() is not None:
                                # 如果是容器类型，对容器内的文本标签应用样式
                                layout = label.layout()
                                if layout:
                                    for i in range(layout.count()):
                                        item = layout.itemAt(i)
                                        widget = item.widget()
                                        if isinstance(widget, BodyLabel):
                                            widget.setAlignment(Qt.AlignCenter)
                                            if animation_color == 1:
                                                widget.setStyleSheet(f"color: {self._generate_vibrant_color()};")
                                            elif animation_color == 2:
                                                widget.setStyleSheet(f"color: {_result_color};")
                            else:
                                # 如果是普通的BodyLabel，直接应用样式
                                label.setAlignment(Qt.AlignCenter)
                                if animation_color == 1:
                                    label.setStyleSheet(f"color: {self._generate_vibrant_color()};")
                                elif animation_color == 2:
                                    label.setStyleSheet(f"color: {_result_color};")

                            # 为widget设置字体（如果widget存在）
                            if widget is not None:
                                widget.setFont(QFont(load_custom_font(), font_size))
                            # 为label设置字体
                            label.setFont(QFont(load_custom_font(), font_size))
                            self.student_labels.append(label)

                        # 计算所有标签的宽度之和，并考虑间距和边距
                        if self.student_labels:
                            total_width = sum(label.sizeHint().width() for label in self.student_labels) + \
                                          len(self.student_labels) * 180
                            available_width = self.width() - 20
                            
                            # 如果总宽度超过可用宽度，则计算每行最多能放几个标签
                            if total_width > available_width:
                                avg_label_width = total_width / len(self.student_labels)
                                max_columns = max(1, int(available_width // avg_label_width))
                            else:
                                max_columns = len(self.student_labels)  # 一行显示所有标签
                        else:
                            max_columns = 1
                        
                        # 复用 container 和 vbox_layout
                        if not hasattr(self, 'container'):
                            self.container = QWidget()
                            self.vbox_layout = QGridLayout()
                            # 设置标签之间的水平和垂直间距
                            self.vbox_layout.setSpacing(15)  # 设置统一的间距
                            self.vbox_layout.setHorizontalSpacing(20)  # 设置水平间距
                            self.vbox_layout.setVerticalSpacing(10)   # 设置垂直间距
                            self.container.setLayout(self.vbox_layout)
                        else:
                            # 清空旧标签
                            for i in reversed(range(self.vbox_layout.count())):
                                item = self.vbox_layout.itemAt(i)
                                if item.widget():
                                    item.widget().setParent(None)

                        for i, label in enumerate(self.student_labels):
                            row = i // max_columns
                            col = i % max_columns
                            self.vbox_layout.addWidget(label, row, col)
                        
                        self.result_grid.addWidget(self.container)
                        
                        if self.max_draw_times_per_person != 0:
                            # 更新抽取记录，在学生名字后面添加抽取次数
                            for student in selected_students:
                                student_name = student[1].replace(' ', '')
                                # 检查学生是否已在记录中
                                found = False
                                for i, record in enumerate(record_data):
                                    # 如果记录中包含次数信息（格式：姓名_次数）
                                    if '_' in record:
                                        record_name, record_count = record.rsplit('_', 1)
                                        if record_name == student_name:
                                            # 增加抽取次数
                                            try:
                                                count = int(record_count) + 1
                                                # 如果达到最大抽取次数，则不再添加到记录中
                                                if self.max_draw_times_per_person > 0 and count > self.max_draw_times_per_person:
                                                    continue
                                                record_data[i] = f"{student_name}_{count}"
                                                found = True
                                                break
                                            except ValueError:
                                                # 如果次数解析失败，使用默认值1
                                                record_data[i] = f"{student_name}_1"
                                                found = True
                                                break
                                    # 如果记录中没有次数信息（旧格式）
                                    elif record == student_name:
                                        # 添加次数信息
                                        record_data[i] = f"{student_name}_1"
                                        found = True
                                        break
                                
                                # 如果学生不在记录中，则添加新记录
                                if not found:
                                    record_data.append(f"{student_name}_1")
                            
                            with open_file(draw_record_file, 'w', encoding='utf-8') as f:
                                json.dump(record_data, f, ensure_ascii=False, indent=4)

                        self.update_total_count()
                        # 抽取完成后启动计时器
                        self._start_clear_timer()
                        return
                    else:
                        if self.max_draw_times_per_person != 0:
                            # 删除临时文件
                            if path_manager.file_exists(draw_record_file):
                                os.remove(draw_record_file)

                        self.random()
                        return

        else:
            self.clear_layout(self.result_grid)
            if hasattr(self, 'container'):
                self.container.deleteLater()
                del self.container
            if hasattr(self, 'student_labels'):
                for label in self.student_labels:
                    label.deleteLater()
            
            # 创建错误标签
            error_label = BodyLabel("-- 抽选失败")
            error_label.setAlignment(Qt.AlignCenter)
            
            try:
                with open_file(path_manager.get_settings_path(), 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    font_size = settings['pumping_people']['font_size']
            except Exception as e:
                font_size = 50
                logger.error(f"加载字体设置失败: {e}, 使用默认设置")
            error_label.setFont(QFont(load_custom_font(), font_size))
            self.result_grid.addWidget(error_label)

    def _generate_vibrant_color(self):
        """生成鲜艳直观的颜色
        
        通过HSV色彩空间生成鲜艳颜色，确保：
        1. 饱和度高(S > 70%)，使颜色鲜艳
        2. 亮度适中(V > 70%)，使颜色明亮但不刺眼
        3. 随机色调(H)，提供多样化的颜色选择
        
        Returns:
            str: RGB格式的颜色字符串，如"rgb(255,100,50)"
        """
        import colorsys
        # 随机生成色调(0-1)
        h = random.random()
        # 设置高饱和度(0.7-1.0)，确保颜色鲜艳
        s = random.uniform(0.7, 1.0)
        # 设置较高亮度(0.7-1.0)，确保颜色明亮
        v = random.uniform(0.7, 1.0)
        
        # 将HSV转换为RGB
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        # 转换为0-255范围
        r, g, b = int(r * 255), int(g * 255), int(b * 255)
        
        return f"rgb({r},{g},{b})"

    # 清除旧布局和标签
    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
    
    def _connect_cleanup_signal(self):
        """连接清理信号"""
        try:
            # 首先尝试通过父组件查找主窗口
            parent = self.parent()
            while parent is not None:
                if hasattr(parent, 'cleanup_signal'):
                    parent.cleanup_signal.connect(self._on_cleanup_signal)
                    # logger.debug("抽人界面已连接到主窗口清理信号")
                    return
                parent = parent.parent()
            
            # 如果通过父组件未找到，尝试通过应用程序查找主窗口
            for widget in QApplication.topLevelWidgets():
                if hasattr(widget, 'cleanup_signal'):
                    widget.cleanup_signal.connect(self._on_cleanup_signal)
                    # logger.debug("抽人界面已连接到主窗口清理信号")
                    return
            
            logger.error("未找到主窗口实例，清理信号连接失败")
        except Exception as e:
            logger.error(f"连接清理信号时出错: {e}")
    
    def _on_cleanup_signal(self):
        """处理清理信号，清除标签"""
        try:
            # 清除结果区域的标签
            self.clear_layout(self.result_grid)
            # 更新总人数显示
            self.update_total_count()
            logger.info("抽人界面已清除所有标签")
        except Exception as e:
            logger.error(f"清除抽人界面标签时出错: {e}")

    # 获取随机抽取方法的设置
    def get_random_method_setting(self):
        """获取随机抽取方法的设置"""
        try:
            with open_file(path_manager.get_settings_path(), 'r', encoding='utf-8') as f:
                settings = json.load(f)
                random_method = settings['pumping_people']['draw_pumping']
                return random_method
        except Exception as e:
            logger.error(f"加载随机抽取方法设置失败: {e}, 使用默认设置")
            return 0

    # 更新历史记录
    def _update_history(self, class_name, group_name, genders, selected_students):
        """更新历史记录"""
        try:
            with open_file(path_manager.get_settings_path(), 'r', encoding='utf-8') as f:
                settings = json.load(f)
                history_enabled = settings['history']['history_enabled']
        except Exception as e:
            history_enabled = False
            logger.error(f"加载历史记录设置失败: {e}, 使用默认设置")
        
        if not history_enabled:
            logger.info("历史记录功能已被禁用。")
            return
        
        history_file = path_manager.get_resource_path("history", f"{class_name}.json")
        os.makedirs(os.path.dirname(history_file), exist_ok=True)
        
        history_data = {}
        if path_manager.file_exists(history_file):
            with open_file(history_file, 'r', encoding='utf-8') as f:
                try:
                    history_data = json.load(f)
                except json.JSONDecodeError:
                    history_data = {}
        
        # 初始化数据结构
        if "pumping_people" not in history_data:
            history_data["pumping_people"] = {}
        if "pumping_group" not in history_data:
            history_data["pumping_group"] = {}
        if "group_stats" not in history_data:
            history_data["group_stats"] = {}
        if "gender_stats" not in history_data:
            history_data["gender_stats"] = {}
        # 初始化统计数据字段
        for field in ["total_rounds", "total_stats"]:
            if field not in history_data:
                history_data[field] = 0

        # 加载学生数据以获取小组和性别信息
        student_info_map = {}
        student_file = path_manager.get_resource_path("list", f"{class_name}.json")
        if path_manager.file_exists(student_file):
            with open_file(student_file, 'r', encoding='utf-8') as f:
                student_data = json.load(f)
                for name, info in student_data.items():
                    if isinstance(info, dict) and 'id' in info:
                        student_name = name.replace('【', '').replace('】', '')
                        student_info_map[student_name] = {
                            'group': info.get('group', ''),
                            'gender': info.get('gender', '')
                        }
        
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 更新被选中学生的记录
        for student_id, student_name, exist in selected_students:
            # 获取学生信息
            student_info = student_info_map.get(student_name, {'group': '', 'gender': ''})
            student_group = student_info['group']
            student_gender = student_info['gender']

            if student_group not in history_data["group_stats"]:
                history_data["group_stats"][student_group] = 0
            if student_gender not in history_data["gender_stats"]:
                history_data["gender_stats"][student_gender] = 0

            history_data["total_rounds"] += 1

            if (not genders or '抽取所有性别' in genders) and group_name == '抽取全班学生':
                if "total_stats" not in history_data:
                    history_data["total_stats"] = 0
                history_data["total_stats"] += 1
                history_data["gender_stats"][student_gender] += 1
                history_data["group_stats"][student_group] += 1
                
            if group_name == '抽取小组组号':
                if student_name not in history_data["pumping_group"]:
                    history_data["pumping_group"][student_name] = {
                        "total_number_of_times": 1,
                        "last_drawn_time": current_time,
                        "rounds_missed": 0,
                        "time": [{
                            "draw_max": self.max_draw_times_per_person,
                            "draw_time": current_time,
                            "draw_people_numbers": self.current_count
                        }]
                    }
                else:
                    history_data["pumping_group"][student_name]["total_number_of_times"] += 1
                    history_data["pumping_group"][student_name]["last_drawn_time"] = current_time
                    history_data["pumping_group"][student_name]["rounds_missed"] = 0
                    history_data["pumping_group"][student_name]["time"].append({
                        "draw_max": self.max_draw_times_per_person,
                        "draw_time": current_time,
                        "draw_people_numbers": self.current_count
                    })
            else:
                if student_name not in history_data["pumping_people"]:
                    if not genders or '抽取所有性别' in genders:
                        history_data["pumping_people"][student_name] = {
                            "total_number_of_times": 1,
                            "total_number_auxiliary": 0,
                            "last_drawn_time": current_time,
                            "rounds_missed": 0,
                            "time": [{
                                "draw_max": self.max_draw_times_per_person,
                                "draw_time": current_time,
                                "draw_people_numbers": self.current_count,
                                "draw_group": group_name,
                                "draw_gender": genders
                            }]
                        }
                    else:
                        history_data["pumping_people"][student_name] = {
                            "total_number_of_times": 0,
                            "total_number_auxiliary": 1,
                            "last_drawn_time": current_time,
                            "rounds_missed": 0,
                            "time": [{
                                "draw_max": self.max_draw_times_per_person,
                                "draw_time": current_time,
                                "draw_people_numbers": self.current_count,
                                "draw_group": group_name,
                                "draw_gender": genders
                            }]
                        }
                else:
                    if not genders or '抽取所有性别' in genders: 
                        history_data["pumping_people"][student_name]["total_number_of_times"] += 1
                    else:
                        history_data["pumping_people"][student_name]["total_number_auxiliary"] += 1
                    history_data["pumping_people"][student_name]["last_drawn_time"] = current_time
                    history_data["pumping_people"][student_name]["rounds_missed"] = 0
                    history_data["pumping_people"][student_name]["time"].append({
                        "draw_max": self.max_draw_times_per_person,
                        "draw_time": current_time,
                        "draw_people_numbers": self.current_count,
                        "draw_group": group_name,
                        "draw_gender": genders
                    })
        
        # 更新未被选中学生的rounds_missed
        all_students = set()
        student_file = path_manager.get_resource_path("list", f"{class_name}.json")
        if path_manager.file_exists(student_file):
            with open_file(student_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for student_name, student_info in data.items():
                    if isinstance(student_info, dict) and 'id' in student_info:
                        name = student_name.replace('【', '').replace('】', '')
                        all_students.add(name)
        
        selected_names = {s[1] for s in selected_students}
        for student_name in all_students:
            if student_name in history_data["pumping_people"] and student_name not in selected_names:
                history_data["pumping_people"][student_name]["rounds_missed"] += 1
        
        # 保存历史记录
        with open_file(history_file, 'w', encoding='utf-8') as f:
            json.dump(history_data, f, ensure_ascii=False, indent=4)

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

    # 更新总人数显示   
    def update_total_count(self):
        """根据选择的班级更新总人数显示"""
        group_name = self.group_combo.currentText()
        class_name = self.class_combo.currentText()
        genders = self.gender_combo.currentText()

        try:
            with open_file(path_manager.get_settings_path("custom_settings.json"), 'r', encoding='utf-8') as f:
                settings = json.load(f)
                pumping_people_student_quantity = settings['roll_call']['people_theme']
        except Exception:
            pumping_people_student_quantity = 0

        if class_name and class_name not in ["你暂未添加班级", "加载班级列表失败"] and pumping_people_student_quantity != 3:
            student_file = path_manager.get_resource_path("list", f"{class_name}.json")
            if path_manager.file_exists(student_file):
                cleaned_data = self._get_cleaned_data(student_file, group_name, genders)
                drawn_count = self._get_drawn_count(class_name, group_name, genders)
                if group_name == '抽取全班学生':
                    _count = len(cleaned_data) - drawn_count
                elif group_name == '抽取小组组号':
                    _count = len(set(group for _, group, _ in cleaned_data)) - drawn_count
                else:
                    _count = len(cleaned_data) - drawn_count
                count = len(cleaned_data)
                if _count <= 0:
                    _count = count
                    InfoBar.success(
                        title='抽取完成',
                        content="抽取完了所有学生了！记录已清除!",
                        orient=Qt.Horizontal,
                        parent=self,
                        isClosable=True,
                        duration=3000,
                        position=InfoBarPosition.TOP
                    )
                entity_type = '组数' if group_name == '抽取小组组号' else '人数'
                if pumping_people_student_quantity == 1:
                    self.total_label.setText(f'总{entity_type}: {count}')
                elif pumping_people_student_quantity == 2:
                    self.total_label.setText(f'剩余{entity_type}: {_count}')
                else:
                    self.total_label.setText(f'总{entity_type}: {count} | 剩余{entity_type}: {_count}')
                self.max_count = count
                self._update_count_display()
            else:
                self._set_default_count(pumping_people_student_quantity)
        else:
            self._set_default_count(pumping_people_student_quantity)

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

    # 获取已抽取人数
    def _get_drawn_count(self, class_name, group_name, genders):
        # 如果max_draw_times_per_person等于0，则是重复抽取模式，返回0
        if self.max_draw_times_per_person == 0:
            return 0
        
        if group_name == '抽取全班学生':
            draw_record_file = f"app/resource/Temp/{class_name}_{group_name}_{genders}.json"
        elif group_name == '抽取小组组号':
            draw_record_file = f"app/resource/Temp/{class_name}_{group_name}.json"
        else:
            draw_record_file = f"app/resource/Temp/{class_name}_{group_name}_{genders}.json"
        if path_manager.file_exists(draw_record_file):
            try:
                with open_file(draw_record_file, 'r', encoding='utf-8') as f:
                    record_data = json.load(f)
                    # 计算未被抽取的学生人数，考虑最大抽取次数限制
                    drawn_count = 0
                    
                    # 首先遍历记录，找出已达到最大抽取次数的学生
                    for record in record_data:
                        if '_' in record:
                            # 新格式：姓名_次数
                            record_name, record_count = record.rsplit('_', 1)
                            try:
                                count = int(record_count)
                                # 如果设置了最大抽取次数且已达到，则加入maxed_out_students集合
                                if self.max_draw_times_per_person > 0 and count >= self.max_draw_times_per_person:
                                    drawn_count += 1
                                else:
                                    drawn_count += 0
                            except ValueError:
                                # 如果次数解析失败，默认为1
                                drawn_count += 1
                        else:
                            # 旧格式：只有姓名
                            drawn_count += 1
                    
                    return drawn_count
            except Exception as e:
                # 处理加载文件出错的情况，返回 0
                logger.error(f"加载抽取记录文件失败: {draw_record_file}, 错误: {e}")
                return 0
        else:
            return 0

    # 设置默认总人数显示
    def _set_default_count(self, pumping_people_student_quantity):
        if pumping_people_student_quantity != 3:
            if pumping_people_student_quantity == 1:
                self.total_label.setText('总人数: 0')
            elif pumping_people_student_quantity == 2:
                self.total_label.setText('剩余人数: 0')
            else:
                self.total_label.setText('总人数: 0 | 剩余人数: 0')
            self.max_count = 0
            self._update_count_display()
    
    # 增加抽取人数
    def _increase_count(self):
        """增加抽取人数"""
        if self.current_count < self.max_count:
            self.current_count += 1
            self._update_count_display()

    # 减少抽取人数        
    def _decrease_count(self):
        """减少抽取人数"""
        if self.current_count > 1:
            self.current_count -= 1
            self._update_count_display()

    # 更新人数显示        
    def _update_count_display(self):
        """更新人数显示"""
        self.count_label.setText(str(self.current_count))
        
        # 根据当前人数启用/禁用按钮
        self.plus_button.setEnabled(self.current_count < self.max_count)
        self.minus_button.setEnabled(self.current_count > 1)
        
        if not self.is_animating and hasattr(self, 'start_button'):
            self.start_button.setEnabled(self.current_count <= self.max_count and self.current_count > 0)
    
    # 刷新班级列表         
    def refresh_class_list(self):
        """刷新班级下拉框选项"""
        self.class_combo.clear()
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
                    logger.error("班级文件夹为空")
                    self.class_combo.addItem("你暂未添加班级")
            else:
                logger.error(f"班级列表文件夹不存在: {list_folder}")
                self.class_combo.addItem("加载班级列表失败")
        except Exception as e:
            logger.error(f"加载班级名称失败: {str(e)}")

        self.update_total_count()

        InfoBar.success(
            title='班级列表',
            content="班级列表更新成功！",
            orient=Qt.Horizontal,
            parent=self,
            isClosable=True,
            duration=3000,
            position=InfoBarPosition.TOP
        )

    # 刷新小组列表
    def refresh_group_list(self):
        """刷新小组下拉框选项"""
        class_name = self.class_combo.currentText()

        self.current_count = 1
        self._update_count_display()

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

    # 刷新性别列表
    def refresh_gender_list(self):
        """刷新性别下拉框选项"""
        class_name = self.class_combo.currentText()

        self.current_count = 1
        self._update_count_display()

        if class_name not in ["你暂未添加班级", "加载班级列表失败", "你暂未添加性别", "加载性别列表失败"]:
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
                        self.gender_combo.clear()
                        if genders:
                            self.gender_combo.addItem('抽取所有性别')
                            self.gender_combo.addItems(cleaned_data)
                        else:
                            logger.error("你暂未添加性别")
                            self.gender_combo.addItem('抽取所有性别')
                            self.gender_combo.addItem("你暂未添加性别")
                else:
                    logger.error("你暂未添加性别")
                    self.gender_combo.addItem("你暂未添加性别")
            except Exception as e:
                logger.error(f"加载性别列表失败: {str(e)}")
                self.gender_combo.addItem("加载性别列表失败")
        else:
            logger.error("请先选择有效的班级")
    
    # 恢复初始状态
    def _reset_to_initial_state(self):
        """恢复初始状态"""
        # 停止计时器
        self._stop_clear_timer()
        self._clean_temp_files()
        self.current_count = 1
        self.update_total_count()
        self.clear_layout(self.result_grid)

    # 清理临时文件
    def _clean_temp_files(self):
        try:
            settings_path = path_manager.get_settings_path('Settings.json')
            with open_file(settings_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                instant_clear_mode = settings['instant_draw']['clear_mode']
                instant_clear = settings['instant_draw']['instant_clear']
                logger.info("准备执行对应清理方案")

        except Exception as e:
            instant_clear_mode = 1
            instant_clear = False
            logger.error(f"加载抽选模式设置失败: {e}")

        import glob
        temp_dir = path_manager.get_temp_path('')
        ensure_dir(temp_dir)

        if instant_clear_mode != 1 and not instant_clear:
            if path_manager.file_exists(temp_dir):
                for file in glob.glob(f"{temp_dir}/*.json"):
                    try:
                        os.remove(file)
                        logger.info(f"已删除临时抽取记录文件: {file}")
                        InfoBar.success(
                            title='清理完成',
                            content="已清理临时抽取记录文件!",
                            orient=Qt.Horizontal,
                            parent=self,
                            isClosable=True,
                            duration=3000,
                            position=InfoBarPosition.TOP
                        )
                    except Exception as e:
                        logger.error(f"删除临时文件出错: {e}")
                        InfoBar.error(
                            title='清理失败',
                            content=f"清理临时抽取记录文件失败: {e}",
                            orient=Qt.Horizontal,
                            parent=self,
                            isClosable=True,
                            duration=3000,
                            position=InfoBarPosition.TOP
                        )
        elif instant_clear_mode != 1 and instant_clear:
            if path_manager.file_exists(temp_dir):
                for file in glob.glob(f"{temp_dir}/*_instant.json"):
                    try:
                        os.remove(file)
                        logger.info(f"已删除临时抽取记录文件: {file}")
                        InfoBar.success(
                            title='清理完成',
                            content="已清理临时抽取记录文件!",
                            orient=Qt.Horizontal,
                            parent=self,
                            isClosable=True,
                            duration=3000,
                            position=InfoBarPosition.TOP
                        )
                    except Exception as e:
                        logger.error(f"删除临时文件出错: {e}")
                        InfoBar.error(
                            title='清理失败',
                            content=f"清理临时抽取记录文件失败: {e}",
                            orient=Qt.Horizontal,
                            parent=self,
                            isClosable=True,
                            duration=3000,
                            position=InfoBarPosition.TOP
                        )

    # 初始化UI
    def __del__(self):
        """析构函数，清理计时器资源"""
        if hasattr(self, 'clear_timer') and self.clear_timer is not None:
            self.clear_timer.stop()
            self.clear_timer = None
    
    def initUI(self):
        # 加载设置
        try:
            with open_file(path_manager.get_settings_path("custom_settings.json"), 'r', encoding='utf-8') as f:
                settings = json.load(f)
                main_window_control_Switch = settings['roll_call']['pumping_people_control_Switch']
                modify_button_switch = settings['roll_call']['modify_button_switch']
                show_reset_button = settings['roll_call']['show_reset_button']
                show_refresh_button = settings['roll_call']['show_refresh_button']
                show_quantity_control = settings['roll_call']['show_quantity_control']
                show_start_button = settings['roll_call']['show_start_button']
                show_list_toggle = settings['roll_call']['show_list_toggle']
                selection_range = settings['roll_call']['selection_range']
                selection_gender = settings['roll_call']['selection_gender']
                pumping_people_student_quantity = settings['roll_call']['people_theme']
        except Exception as e:
            logger.error(f"加载设置失败: {e}, 使用默认设置")
            main_window_control_Switch = True
            modify_button_switch = False
            show_reset_button = True
            show_refresh_button = True
            show_quantity_control = True
            show_start_button = True
            show_list_toggle = True
            selection_range = True
            selection_gender = True
            pumping_people_student_quantity = 0
            
        # 主布局
        scroll_area = SingleDirectionScrollArea()
        scroll_area.setWidgetResizable(True)
        # 设置滚动条样式
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollArea QWidget {
                border: none;
                background-color: transparent;
            }
        """)
        # 启用触屏滚动
        QScroller.grabGesture(scroll_area.viewport(), QScroller.LeftMouseButtonGesture)
        
        # 创建主容器和布局
        container = QWidget(scroll_area)
        scroll_area_container = QVBoxLayout(container)
        
        # 控制面板
        control_panel = QVBoxLayout()
        control_panel.setContentsMargins(10, 10, 10, 10) # 左、上、右、下   

        # 修改班级名单按钮
        if modify_button_switch:
            self.modify_button = PushButton('修改班级名单')
            self.modify_button.setFixedSize(180, 50)
            self.modify_button.setFont(QFont(load_custom_font(), 13))
            self.modify_button.clicked.connect(self.modify_name_settings)
            control_panel.addWidget(self.modify_button, 0, Qt.AlignVCenter)

        # 刷新按钮
        if show_reset_button:
            self.refresh_button = PushButton('重置已抽取名单')
            self.refresh_button.setFixedSize(180, 50)
            self.refresh_button.setFont(QFont(load_custom_font(), 13))
            self.refresh_button.clicked.connect(lambda: self._reset_to_initial_state())
            control_panel.addWidget(self.refresh_button, 0, Qt.AlignVCenter)

        # 刷新按钮
        if show_refresh_button:
            self.refresh_button = PushButton('刷新学生列表')
            self.refresh_button.setFixedSize(180, 50)
            self.refresh_button.setFont(QFont(load_custom_font(), 13))
            self.refresh_button.clicked.connect(self.refresh_class_list)
            control_panel.addWidget(self.refresh_button, 0, Qt.AlignVCenter)

        # 创建一个水平布局
        horizontal_layout = QHBoxLayout()

        # 减号按钮
        self.minus_button = PushButton('-')
        self.minus_button.setFixedSize(50, 50)
        self.minus_button.setFont(QFont(load_custom_font(), 25))
        self.minus_button.clicked.connect(self._decrease_count)
        horizontal_layout.addWidget(self.minus_button, 0, Qt.AlignLeft)

        # 人数显示
        self.count_label = BodyLabel('1')
        self.count_label.setAlignment(Qt.AlignCenter)
        self.count_label.setFont(QFont(load_custom_font(), 25))
        self.count_label.setFixedWidth(65)
        horizontal_layout.addWidget(self.count_label, 0, Qt.AlignLeft)

        # 加号按钮
        self.plus_button = PushButton('+')
        self.plus_button.setFixedSize(50, 50)
        self.plus_button.setFont(QFont(load_custom_font(), 25))
        self.plus_button.clicked.connect(self._increase_count)
        horizontal_layout.addWidget(self.plus_button, 0, Qt.AlignLeft)

        if show_quantity_control:
            # 将水平布局添加到控制面板
            control_panel.addLayout(horizontal_layout)

        # 开始按钮
        if show_start_button:
            self.start_button = PrimaryPushButton('开始')
            self.start_button.setObjectName("pumpingButton")
            self.start_button.setFixedSize(180, 50)
            self.start_button.setFont(QFont(load_custom_font(), 15))
            self.start_button.clicked.connect(self.start_draw)
            control_panel.addWidget(self.start_button, 0, Qt.AlignVCenter)
        
        # 班级下拉框
        self.class_combo = ComboBox()
        self.class_combo.setFixedSize(180, 50)
        self.class_combo.setFont(QFont(load_custom_font(), 13))
        
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
        
        if show_list_toggle:
            control_panel.addWidget(self.class_combo)

        # 小组下拉框
        self.group_combo = ComboBox()
        self.group_combo.setFixedSize(180, 50)
        self.group_combo.setFont(QFont(load_custom_font(), 13))
        self.group_combo.addItem('抽取全班学生')
        self.group_combo.currentIndexChanged.connect(self.update_total_count)
        self.class_combo.currentIndexChanged.connect(self.refresh_group_list)

        class_name = self.class_combo.currentText()
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
        
        if selection_range:
            control_panel.addWidget(self.group_combo)

        # 性别下拉框
        self.gender_combo = ComboBox()
        self.gender_combo.setFixedSize(180, 50)
        self.gender_combo.setFont(QFont(load_custom_font(), 13))
        self.gender_combo.addItem('抽取所有性别')
        self.gender_combo.currentIndexChanged.connect(self.update_total_count)
        self.class_combo.currentIndexChanged.connect(self.refresh_gender_list)
        self.group_combo.currentIndexChanged.connect(self.refresh_gender_list)

        class_name = self.class_combo.currentText()
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
        
        if selection_gender:
            control_panel.addWidget(self.gender_combo)
        
        # 总人数和剩余人数显示
        if pumping_people_student_quantity != 3:
            if pumping_people_student_quantity == 1:
                self.total_label = BodyLabel('总人数: 0')
            elif pumping_people_student_quantity == 2:
                self.total_label = BodyLabel('剩余人数: 0')
            else:
                self.total_label = BodyLabel('总人数: 0 | 剩余人数: 0')
            self.total_label.setFont(QFont(load_custom_font(), 11))
            self.total_label.setAlignment(Qt.AlignCenter)
            self.total_label.setFixedWidth(180)
            control_panel.addWidget(self.total_label, 0, Qt.AlignLeft)
        
        control_panel.addStretch(1)
        
        # 初始化抽取人数
        self.current_count = 1
        self.max_count = 0

        # 结果区域布局
        self.result_grid = QGridLayout()
        self.result_grid.setSpacing(1)
        self.result_grid.setAlignment(Qt.AlignTop | Qt.AlignCenter)

        scroll_area_container.addLayout(self.result_grid)
        
        # 班级选择变化时更新总人数
        self.class_combo.currentTextChanged.connect(self.update_total_count)
        
        # 初始化总人数显示
        self.update_total_count()
        
        # 设置容器并应用布局
        main_layout = QHBoxLayout(self)

        control_button_layout = QVBoxLayout()

        control_button_layout.addStretch(1)
        
        # 将control_panel布局包裹在QWidget中
        control_panel_widget = QWidget()
        control_panel_widget.setLayout(control_panel)
        control_button_layout.addWidget(control_panel_widget, 0, Qt.AlignBottom)

        # 将scroll_area添加到主布局中
        scroll_area.setWidget(container)
        # 创建一个QWidget来包含control_button_layout
        control_button_widget = QWidget()
        control_button_widget.setLayout(control_button_layout)
        # 将control_button_widget添加到主布局中
        if main_window_control_Switch:
            main_layout.addWidget(scroll_area)
            main_layout.addWidget(control_button_widget)
        else:
            main_layout.addWidget(control_button_widget)
            main_layout.addWidget(scroll_area)

        # 显示主布局
        self.setLayout(main_layout)

    def modify_name_settings(self):
        """修改班级名单"""
        class_name = self.class_combo.currentText()
        
        # 检查是否选择了有效的班级
        if not class_name or class_name in ["你暂未添加班级", "加载班级列表失败"]:
            InfoBar.warning(
                title='提示',
                content="请先选择一个有效的班级！",
                orient=Qt.Horizontal,
                parent=self,
                isClosable=True,
                duration=3000,
                position=InfoBarPosition.TOP
            )
            return
        
        # 获取班级文件路径
        class_file = path_manager.get_resource_path("list", f"{class_name}.json")
        
        # 检查班级文件是否存在
        if not path_manager.file_exists(class_file):
            InfoBar.warning(
                title='提示',
                content=f"班级文件不存在：{class_name}.json",
                orient=Qt.Horizontal,
                parent=self,
                isClosable=True,
                duration=3000,
                position=InfoBarPosition.TOP
            )
            return
        
        dialog = StudentInputDialog(self)
        if dialog.exec():
            student_text = dialog.getText()
            selected_class = self.class_combo.currentText()
            if selected_class:
                try:
                    students = [line.strip() for line in student_text.split('\n') if line.strip()]
                    
                    list_folder = path_manager.get_resource_path('list', '')
                    ensure_dir(list_folder)
                    
                    student_file = path_manager.get_resource_path('list', f'{selected_class}.json')
                    student_data = {}
                    
                    if path_manager.file_exists(student_file):
                        with open_file(student_file, 'r', encoding='utf-8') as f:
                            student_data = json.load(f)
                    
                    # 先删除不在新名单中的学生
                    # ✨ 小鸟游星野：保留原始键名处理特殊字符
                    existing_students = {name for name in student_data.keys()}
                    new_students_cleaned = {student.strip().replace('【', '').replace('】', '') for student in students if student.strip()}
                    
                    # 找出需要删除的学生（原始键名）
                    students_to_remove = []
                    for name in existing_students:
                        cleaned_name = name.replace('【', '').replace('】', '')
                        if cleaned_name not in new_students_cleaned:
                            students_to_remove.append(name)
                    
                    for student_to_remove in students_to_remove:
                        del student_data[student_to_remove]
                    
                    # 更新或添加新学生
                    # 重新生成学生顺序，确保按输入顺序存储
                    new_student_data = {}
                    for idx, student in enumerate(students, start=1):
                        student_name = student.strip()
                        exist_status = False if '【' in student_name and '】' in student_name else True
                        # 确保保留原有的性别和小组信息
                        cleaned_name = student_name.replace('【', '').replace('】', '')
                        if cleaned_name in {k.replace('【', '').replace('】', '') for k in student_data.keys()}: 
                            original_info = next((student_data[k] for k in student_data if k.replace('【', '').replace('】', '') == cleaned_name), {})
                        else:
                            original_info = {}
                        new_student_data[student_name] = {
                            "id": idx,
                            "exist": exist_status,
                            "gender": original_info.get("gender", ""),
                            "group": original_info.get("group", "")
                        }
                    student_data = new_student_data
                    
                    with open_file(student_file, 'w', encoding='utf-8') as f:
                        json.dump(student_data, f, ensure_ascii=False, indent=4)
                    
                    self.refresh_signal.emit()
                    logger.info(f"学生名单保存成功！")
                except Exception as e:
                    logger.error(f"保存失败: {str(e)}")




class StudentInputDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("输入学生姓名")
        self.setMinimumSize(400, 635)  # 设置最小大小而不是固定大小
        self.saved = False
        self.dragging = False
        
        # 设置无边框窗口
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        # 创建标题栏
        self.title_bar = QWidget()
        self.title_bar.setObjectName("CustomTitleBar")
        self.title_bar.setFixedHeight(35)
        # 标题栏布局
        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(10, 0, 10, 0)
        # 标题标签
        self.title_label = QLabel("输入学生姓名")
        self.title_label.setObjectName("TitleLabel")
        self.title_label.setFont(QFont(load_custom_font(), 12, QFont.Bold))
        # 关闭按钮
        self.close_button = QPushButton("✕")
        self.close_button.setObjectName("CloseButton")
        self.close_button.setFixedSize(25, 25)
        self.close_button.clicked.connect(self.close)
        # 添加到布局
        title_layout.addWidget(self.title_label)
        title_layout.addStretch(1)
        title_layout.addWidget(self.close_button)

        self.text_label = BodyLabel('请输入学生姓名，每行一个\n在输入已经不在当前班级的学生时\n请在姓名前后加上“【】”')
        self.text_label.setFont(QFont(load_custom_font(), 12))

        self.update_theme_style()
        qconfig.themeChanged.connect(self.update_theme_style)
        
        self.textEdit = PlainTextEdit()
        self.textEdit.setPlaceholderText("请输入学生姓名，每行一个")
        self.textEdit.setFont(QFont(load_custom_font(), 12))
        
        self.setFont(QFont(load_custom_font(), 12))
        
        class_name = self.parent().class_combo.currentText()
        try:
            student_file = path_manager.get_resource_path('list', f'{class_name}.json')
            with open_file(student_file, 'r', encoding='utf-8') as f:
                file_content = f.read()
                if not file_content.strip():
                    # 处理空文件情况
                    logger.error(f"JSON文件为空: {student_file}")
                    return
                
                try:
                    data = json.loads(file_content)
                    if not isinstance(data, dict):
                        raise ValueError("JSON格式不正确，应为字典类型")
                    
                    name_list = []
                    for student_name in data:
                        name_list.append(student_name)
                    self.textEdit.setPlainText("\n".join(name_list))
                except json.JSONDecodeError as e:
                    logger.error(f"JSON解析错误: {str(e)}")
                except ValueError as e:
                    logger.error(f"数据格式错误: {str(e)}")
        except FileNotFoundError:
            logger.error(f"文件未找到: {student_file}")
        except json.JSONDecodeError:
            logger.error("JSON文件格式错误，请检查文件内容")
        
        self.saveButton = PrimaryPushButton("保存")
        self.cancelButton = PushButton("取消")
        self.saveButton.clicked.connect(self.accept)
        self.cancelButton.clicked.connect(self.reject)
        self.saveButton.setFont(QFont(load_custom_font(), 12))
        self.cancelButton.setFont(QFont(load_custom_font(), 12))
        

        # 创建主布局
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 添加标题栏到主布局
        layout.addWidget(self.title_bar)
        
        # 创建内容区域布局
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(10, 10, 10, 10)
        content_layout.setSpacing(10)
        
        # 添加UI元素到内容布局
        content_layout.addWidget(self.text_label)
        content_layout.addWidget(self.textEdit)
        
        # 创建按钮布局
        buttonLayout = QHBoxLayout()
        buttonLayout.addStretch(1)
        buttonLayout.addWidget(self.cancelButton)
        buttonLayout.addWidget(self.saveButton)
        
        # 将按钮布局添加到内容布局
        content_layout.addLayout(buttonLayout)
        
        # 将内容布局添加到主布局
        layout.addLayout(content_layout)
        
        # 设置主布局
        self.setLayout(layout)

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
                logger.error(f"标题栏颜色设置失败: {str(e)}")

    def mousePressEvent(self, event):
        # 标题栏拖动
        if event.button() == Qt.LeftButton and self.title_bar.geometry().contains(event.pos()):
            self.dragging = True
            self.drag_start_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        # 窗口拖动
        if self.dragging and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_start_position)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        # 结束拖动
        if self.dragging and event.button() == Qt.LeftButton:
            self.dragging = False
            event.accept()
        else:
            super().mouseReleaseEvent(event)
        
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
