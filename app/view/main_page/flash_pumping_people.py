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

from app.common.config import get_theme_icon, load_custom_font, restore_volume
from app.common.path_utils import path_manager, open_file, remove_file, ensure_dir
from app.common.message_sender import message_sender

class instant_draw(QWidget):
    # 抽取完成信号
    draw_finished = pyqtSignal()
    
    def __init__(self, parent=None, draw_count=1, class_name="你暂未添加班级", group_name="你暂未添加小组", gender_name="你暂未添加性别"):
        super().__init__(parent)
        # 定义变量
        self.is_animating = False
        self.max_draw_times_per_person = 1
        self.animation_timer = None
        self.clear_timer = None  # 添加计时器变量，用于自动清除临时抽取记录
        # 音乐播放器初始化 ✧(◍˃̶ᗜ˂̶◍)✩ 感谢白露提供的播放器
        self.music_player = QMediaPlayer()
        self.draw_count = draw_count
        self.class_name = class_name
        self.group_name = group_name
        self.gender_name = gender_name
        self.initUI()
    
    def start_draw(self):
        """开始抽选学生"""
        # 获取抽选模式和动画模式设置
        try:
            with open_file(path_manager.get_settings_path(), 'r', encoding='utf-8') as f:
                settings = json.load(f)
                instant_draw_animation_mode = settings['instant_draw']['animation_mode']
                self.interval = settings['instant_draw']['animation_interval']
                self.auto_play = settings['instant_draw']['animation_auto_play']
                self.animation_music_enabled = settings['instant_draw']['animation_music_enabled']
                self.result_music_enabled = settings['instant_draw']['result_music_enabled']
                self.animation_music_volume = settings['instant_draw']['animation_music_volume']
                self.result_music_volume = settings['instant_draw']['result_music_volume']
                self.music_fade_in = settings['instant_draw']['music_fade_in']
                self.music_fade_out = settings['instant_draw']['music_fade_out']
                self.max_draw_times_per_person = settings['instant_draw']['Draw_pumping']
                self.use_cwci_display = settings['instant_draw']['use_cwci_display']
                self.use_cwci_display_time = settings['instant_draw']['use_cwci_display_time']
                
        except Exception as e:
            instant_draw_animation_mode = 0
            self.interval = 100
            self.auto_play = 5
            self.animation_music_enabled = False
            self.result_music_enabled = False
            self.animation_music_volume = 5
            self.result_music_volume = 5
            self.music_fade_in = 300
            self.music_fade_out = 300
            self.max_draw_times_per_person = 1
            self.use_cwci_display = False
            self.use_cwci_display_time = 3
            logger.error(f"加载设置时出错: {e}, 使用默认设置")

        if instant_draw_animation_mode == 0:  # 自动播放完整动画
            self._play_full_animation()
        elif instant_draw_animation_mode == 1:  # 直接显示结果
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
                clear_time = settings['instant_draw']['max_draw_count']

            self.current_count = 1
                
            # 只有在"定时清临时记录"模式下才启动计时器
            if clear_time > 0:
                self.clear_timer = QTimer()
                self.clear_timer.setSingleShot(True)  # 单次触发
                self.clear_timer.timeout.connect(lambda: self._clean_temp_files())
                self.clear_timer.timeout.connect(lambda: self.clear_layout(self.result_grid))
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
        class_name = self.class_name
        group_name = self.group_name
        genders = self.gender_name

        try:
            settings_path = path_manager.get_settings_path('Settings.json')
            with open_file(settings_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                instant_clear = settings['instant_draw']['instant_clear']

        except Exception as e:
            instant_clear = False
            logger.error(f"加载抽选模式设置失败: {e}")

        if instant_clear:
            instant_clear = '_instant'
        else:
            instant_clear = ''

        if class_name and class_name not in ["你暂未添加班级", "加载班级列表失败", "你暂未添加小组", "加载小组列表失败"] and group_name and group_name not in ["你暂未添加小组", "加载小组列表失败"]:
            student_file = path_manager.get_resource_path('list', f'{class_name}.json')

            if group_name == '抽取全班学生':    
                draw_record_file = path_manager.get_temp_path(f'{class_name}_{group_name}_{genders}{instant_clear}.json')
            elif group_name == '抽取小组组号':
                draw_record_file = path_manager.get_temp_path(f'{class_name}_{group_name}{instant_clear}.json')
            else:
                draw_record_file = path_manager.get_temp_path(f'{class_name}_{group_name}_{genders}{instant_clear}.json')
            
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
                        # 过滤掉已经抽取过的小组
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
                        settings_file = path_manager.get_settings_path('Settings.json')
                        try:
                            with open_file(settings_file, 'r', encoding='utf-8') as f:
                                settings = json.load(f)
                                instant_draw_student_id = settings['instant_draw']['student_id']
                                instant_draw_student_name = settings['instant_draw']['student_name']
                                display_format = settings['instant_draw']['display_format']
                                font_size = settings['instant_draw']['font_size']
                                animation_color = settings['instant_draw']['animation_color']
                                _animation_color = settings['instant_draw'].get('_animation_color', '#ffffff')
                                show_student_image = settings['instant_draw']['show_student_image']
                        except Exception as e:
                            instant_draw_student_id = 0
                            instant_draw_student_name = 0
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
                            student_id_format = instant_draw_student_id
                            student_name_format = instant_draw_student_name
                            # 为每个奖励单独查找对应的图片文件
                            current_image_path = None
                            if show_student_image:
                                # 支持多种图片格式：png、jpg、jpeg、svg
                                image_extensions = ['.png', '.jpg', '.jpeg', '.svg']
                                
                                # 遍历所有支持的图片格式，查找存在的图片文件
                                for ext in image_extensions:
                                    temp_path = path_manager.get_resource_path("images/students", f"{selected}{ext}")
                                    if os.path.isfile(temp_path):
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
                                student_file = path_manager.get_resource_path("list", f"{self.class_name}.json")
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
                                    with open_file(settings_file, 'r', encoding='utf-8') as f:
                                        settings = json.load(f)
                                        show_random = settings['instant_draw'].get('show_random_member', False)
                                        format_str = settings['instant_draw'].get('random_member_format', FORMAT_GROUP_SIMPLE)
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
            
            settings_file = path_manager.get_settings_path()
            try:
                with open_file(settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    font_size = settings['instant_draw']['font_size']
            except Exception as e:
                font_size = 50
                logger.error(f"加载字体设置时出错: {e}, 使用默认设置")
            error_label.setFont(QFont(load_custom_font(), font_size))
            self.result_grid.addWidget(error_label)
    
    # 停止动画并显示最终结果
    def _stop_animation(self):
        """停止动画并显示最终结果"""
        self.animation_timer.stop()
        if self.animation_music_enabled:
            # 创建音量渐出动画
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
        
        # 显示最终结果
        self.random()
        self.voice_play()
        # 发射抽取完成信号
        self.draw_finished.emit()
    
    def _play_full_animation(self):
        """播放完整动画（快速显示n个随机学生后显示最终结果）🎵"""
        self.is_animating = True
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self._show_random_student)
        self.animation_timer.start(self.interval)
        if self.animation_music_enabled:
            self._play_animation_music()
        
        # n次随机后停止
        QTimer.singleShot(self.auto_play * self.interval, lambda: [
            self.animation_timer.stop(),
            self._stop_animation(),
          ])
    
    # 直接显示结果（无动画效果）
    def _show_result_directly(self):
        """直接显示结果（无动画效果）"""
        if self.result_music_enabled:
            self._play_result_music()
        self.random()
        self.voice_play()
        # 延迟1秒后发射抽取完成信号
        QTimer.singleShot(1000, self.draw_finished.emit)

    def _play_result_music(self):
        """播放结果音乐"""
        try:
            BGM_RESULT_PATH = path_manager.get_resource_path("music/instant_draw/result_music")
            # 检查音乐目录是否存在
            if not path_manager.file_exists(BGM_RESULT_PATH):
                logger.error(f"结果音乐目录不存在: {BGM_RESULT_PATH}")
                return

            # 获取所有支持的音乐文件
            music_extensions = ['*.mp3', '*.wav', '*.ogg', '*.flac']
            music_files = []
            for ext in music_extensions:
                music_files.extend(glob.glob(os.path.join(BGM_RESULT_PATH, ext)))

            if not music_files:
                logger.error(f"结果音乐目录中没有找到音乐文件: {BGM_RESULT_PATH}")
                return

            # 随机选择一首音乐
            selected_music = random.choice(music_files)
            logger.info(f"正在播放结果音乐: {selected_music}")

            # 设置并播放音乐，准备渐入效果
            self.music_player.setMedia(QMediaContent(QUrl.fromLocalFile(selected_music)))
            if self.music_player.mediaStatus() == QMediaPlayer.InvalidMedia:
                logger.error(f"无效的媒体文件: {selected_music}")
                return
            self.music_player.setVolume(0)  # 初始音量设为0
            self.music_player.play()
            # 连接错误信号
            self.music_player.error.connect(self.handle_media_error)
            
            # 创建音量渐入动画
            self.fade_in_animation = QPropertyAnimation(self.music_player, b"volume")
            self.fade_in_animation.setDuration(self.music_fade_in)
            self.fade_in_animation.setStartValue(0)
            self.fade_in_animation.setEndValue(self.result_music_volume)
            self.fade_in_animation.setEasingCurve(QEasingCurve.InOutQuad)
            self.fade_in_animation.start()

            # 延迟1秒后开始音量渐出动画，让音乐能正常播放一段时间
            QTimer.singleShot(self.music_fade_in + 1000, self._start_fade_out_animation)

        except Exception as e:
            logger.error(f"播放音乐时出错: {e}")

    def _start_fade_out_animation(self):
        """开始音量渐出动画，让音乐逐渐淡出"""
        try:
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
            else:
                # 如果音乐没有在播放，直接停止并重置音量
                self.music_player.stop()
                self.music_player.setVolume(self.result_music_volume)
        except Exception as e:
            logger.error(f"音量渐出动画出错: {e}")
            # 出错时确保停止播放并重置音量
            self.music_player.stop()
            self.music_player.setVolume(self.result_music_volume)

    def _play_animation_music(self):
        """播放动画背景音乐"""
        try:
            BGM_ANIMATION_PATH = path_manager.get_resource_path("music/instant_draw/Animation_music")
            # 检查音乐目录是否存在
            if not path_manager.file_exists(BGM_ANIMATION_PATH):
                logger.error(f"音乐目录不存在: {BGM_ANIMATION_PATH}")
                return

            # 获取所有支持的音乐文件 (｡･ω･｡)ﾉ♡
            music_extensions = ['*.mp3', '*.wav', '*.ogg', '*.flac']
            music_files = []
            for ext in music_extensions:
                music_files.extend(glob.glob(os.path.join(BGM_ANIMATION_PATH, ext)))

            if not music_files:
                logger.error(f"音乐目录中没有找到音乐文件: {BGM_ANIMATION_PATH}")
                return

            # 随机选择一首音乐 ♪(^∇^*)
            selected_music = random.choice(music_files)
            logger.info(f"正在播放音乐: {selected_music}")

            # 设置并播放音乐，准备渐入效果 ✧*｡٩(ˊᗜˋ*)و✧*｡
            self.music_player.setMedia(QMediaContent(QUrl.fromLocalFile(selected_music)))
            if self.music_player.mediaStatus() == QMediaPlayer.InvalidMedia:
                logger.error(f"无效的媒体文件: {selected_music}")
                return
            self.music_player.setVolume(0)  # 初始音量设为0
            self.music_player.play()
            # 连接错误信号
            self.music_player.error.connect(self.handle_media_error)
            
            # 创建音量渐入动画
            self.fade_in_animation = QPropertyAnimation(self.music_player, b"volume")
            self.fade_in_animation.setDuration(self.music_fade_in)
            self.fade_in_animation.setStartValue(0)
            self.fade_in_animation.setEndValue(self.animation_music_volume)
            self.fade_in_animation.setEasingCurve(QEasingCurve.InOutQuad)
            self.fade_in_animation.start()
        except Exception as e:
            logger.error(f"播放音乐时出错: {e}")

    def handle_media_error(self, error):
        """处理媒体播放错误"""
        error_str = self.music_player.errorString()
        logger.error(f"媒体播放错误: {error_str} (错误代码: {error})")
        self.music_player.stop()
    
    # 根据抽取模式抽选学生
    def random(self):
        """根据抽取模式抽选学生"""
        class_name = self.class_name
        group_name = self.group_name
        genders = self.gender_name

        try:
            settings_path = path_manager.get_settings_path('Settings.json')
            with open_file(settings_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                instant_clear = settings['instant_draw']['instant_clear']

        except Exception as e:
            instant_clear = False
            logger.error(f"加载抽选模式设置失败: {e}")

        if instant_clear:
            instant_clear = '_instant'
        else:
            instant_clear = ''
        
        if class_name and class_name not in ["你暂未添加班级", "加载班级列表失败", "你暂未添加小组", "加载小组列表失败"] and group_name and group_name not in ["你暂未添加小组", "加载小组列表失败"]:
            student_file = path_manager.get_resource_path("list", f"{class_name}.json")

            if group_name == '抽取全班学生':
                draw_record_file = path_manager.get_temp_path(f"{class_name}_{group_name}_{genders}{instant_clear}.json")
            elif group_name == '抽取小组组号':
                draw_record_file = path_manager.get_temp_path(f"{class_name}_{group_name}{instant_clear}.json")
            else:
                draw_record_file = path_manager.get_temp_path(f"{class_name}_{group_name}_{genders}{instant_clear}.json")
       
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
                                student_history = history_data.get("instant_draw", {}).get(student_name, {
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
                        
                        settings = path_manager.get_settings_path()
                        try:
                            with open_file(settings, 'r', encoding='utf-8') as f:
                                settings = json.load(f)
                                instant_draw_student_id = settings['instant_draw']['student_id']
                                instant_draw_student_name = settings['instant_draw']['student_name']
                                display_format = settings['instant_draw']['display_format']
                                font_size = settings['instant_draw']['font_size']
                                animation_color = settings['instant_draw']['animation_color']
                                _result_color = settings['instant_draw'].get('_result_color', '#ffffff')
                                show_student_image = settings['instant_draw']['show_student_image']
                        except Exception as e:
                            instant_draw_student_id = 0
                            instant_draw_student_name = 0
                            display_format = 0
                            font_size = 50
                            animation_color = 0
                            _result_color = "#ffffff"
                            show_student_image = False

                        self.student_labels = []
                        for num, selected, exist in selected_students:
                            student_id_format = instant_draw_student_id
                            student_name_format = instant_draw_student_name
                            # 为每个奖励单独查找对应的图片文件
                            current_image_path = None
                            if show_student_image:
                                # 支持多种图片格式：png、jpg、jpeg、svg
                                image_extensions = ['.png', '.jpg', '.jpeg', '.svg']
                                
                                # 遍历所有支持的图片格式，查找存在的图片文件
                                for ext in image_extensions:
                                    temp_path = path_manager.get_resource_path("images/students", f"{selected}{ext}")
                                    if os.path.isfile(temp_path):
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
                                student_file = path_manager.get_resource_path("list", f"{self.class_name}.json")
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
                                    settings_path = path_manager.get_settings_path()
                                    with open_file(settings_path, 'r', encoding='utf-8') as f:
                                        settings_data = json.load(f)
                                        show_random = settings_data['instant_draw'].get('show_random_member', False)
                                        format_str = settings_data['instant_draw'].get('random_member_format', FORMAT_GROUP_SIMPLE)
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

                        # 发送抽选结果消息
                        try:
                            if self.use_cwci_display:
                                # 从selected_students中提取学生姓名并用逗号分隔
                                student_names = []
                                for student in selected_students:
                                    # student是元组(num, selected, exist)，其中selected是学生姓名
                                    student_name = student[1].replace(' ', '') if isinstance(student[1], str) else str(student[1])
                                    student_names.append(student_name)
                                
                                # 将学生姓名用逗号连接成一个字符串
                                names_str = ",".join(student_names)
                            
                                # 发送抽选结果
                                message_sender.send_selection_result_json(selected_name=names_str, use_cwci_display_time=self.use_cwci_display_time)
                                logger.info(f"已发送抽选结果消息")
                        except Exception as e:
                            logger.error(f"发送抽选结果消息失败: {e}")

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
            
            settings = path_manager.get_settings_path()

            try:
                with open_file(settings, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    font_size = settings['instant_draw']['font_size']
            except Exception as e:
                font_size = 50
                logger.error(f"加载字体设置时出错: {e}, 使用默认设置")
            error_label.setFont(QFont(load_custom_font(), font_size))
            self.result_grid.addWidget(error_label)

    def _generate_vibrant_color(self):
        """生成鲜艳的随机颜色
        使用HSV色彩空间生成高饱和度和适中亮度的颜色，确保颜色鲜艳直观
        返回格式为"rgb(r,g,b)"的字符串
        """
        import colorsys
        # 随机生成色调 (0-1)
        h = random.random()
        # 高饱和度 (0.7-1.0) 确保颜色鲜艳
        s = random.uniform(0.7, 1.0)
        # 适中亮度 (0.7-1.0) 避免过暗或过亮
        v = random.uniform(0.7, 1.0)
        
        # 将HSV转换为RGB
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        # 转换为0-255范围的整数
        r, g, b = int(r * 255), int(g * 255), int(b * 255)
        
        return f"rgb({r},{g},{b})"

    # 清除旧布局和标签
    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    # 获取随机抽取方法的设置
    def get_random_method_setting(self):
        """获取随机抽取方法的设置"""
        settings = path_manager.get_settings_path()
        try:
            with open_file(settings, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                random_method = settings['instant_draw']['draw_pumping']
                return random_method
        except Exception as e:
            logger.error(f"加载随机抽取方法设置时出错: {e}, 使用默认设置")
            return 0

    # 更新历史记录
    def _update_history(self, class_name, group_name, genders, selected_students):
        """更新历史记录"""
        settings = path_manager.get_settings_path()
        try:
            with open_file(settings, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                history_enabled = settings['history']['history_enabled']
        except Exception as e:
            history_enabled = False
            logger.error(f"加载历史记录设置时出错: {e}, 使用默认设置")
        
        if not history_enabled:
            logger.info("历史记录功能已被禁用。")
            return
        
        history_file = path_manager.get_resource_path("history", f"{class_name}.json")
        path_manager.ensure_directory_exists(history_file.parent)
        history_data = {}
        if path_manager.file_exists(history_file):
            with open_file(history_file, 'r', encoding='utf-8') as f:
                try:
                    history_data = json.load(f)
                except json.JSONDecodeError:
                    history_data = {}
        
        # 初始化数据结构
        if "instant_draw" not in history_data:
            history_data["instant_draw"] = {}
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
                if student_name not in history_data["instant_draw"]:
                    if not genders or '抽取所有性别' in genders:
                        history_data["instant_draw"][student_name] = {
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
                        history_data["instant_draw"][student_name] = {
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
                        history_data["instant_draw"][student_name]["total_number_of_times"] += 1
                    else:
                        history_data["instant_draw"][student_name]["total_number_auxiliary"] += 1
                    history_data["instant_draw"][student_name]["last_drawn_time"] = current_time
                    history_data["instant_draw"][student_name]["rounds_missed"] = 0
                    history_data["instant_draw"][student_name]["time"].append({
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
            if student_name in history_data["instant_draw"] and student_name not in selected_names:
                history_data["instant_draw"][student_name]["rounds_missed"] += 1
        
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
        
        # 自定义组名直接使用中文排序
        return (3, group) # 其他名称组，保持排序功能不变
    
    # 恢复初始状态
    def _reset_to_initial_state(self):
        """恢复初始状态"""
        # 停止计时器
        self._stop_clear_timer()
        self._clean_temp_files()
        self.clear_layout(self.result_grid)

    # 清理临时文件
    def _clean_temp_files(self):
        try:
            settings_path = path_manager.get_settings_path('Settings.json')
            with open_file(settings_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                instant_clear_mode = settings['instant_draw']['clear_mode']
                instant_clear = settings['instant_draw']['instant_clear']
                logger.info(f"准备执行对应清理方案")

        except Exception as e:
            instant_clear_mode = 1
            instant_clear = False
            logger.error(f"加载抽选模式设置失败了喵～ {e}")

        import glob
        temp_dir = path_manager.get_temp_path('')
        ensure_dir(temp_dir)

        if instant_clear_mode != 1 and not instant_clear:
            if path_manager.file_exists(temp_dir):
                for file in glob.glob(f"{temp_dir}/*.json"):
                    try:
                        os.remove(file)
                        logger.info(f"已删除临时抽取记录文件: {file}")
                    except Exception as e:
                        logger.error(f"删除临时文件出错: {e}")
        elif instant_clear_mode != 1 and instant_clear:
            if path_manager.file_exists(temp_dir):
                for file in glob.glob(f"{temp_dir}/*_instant.json"):
                    try:
                        os.remove(file)
                        logger.info(f"已删除临时抽取记录文件: {file}")
                    except Exception as e:
                        logger.error(f"删除临时文件出错: {e}")

    # 初始化UI
    def __del__(self):
        """析构函数，清理计时器资源"""
        if hasattr(self, 'clear_timer') and self.clear_timer is not None:
            self.clear_timer.stop()
            self.clear_timer = None

    # 初始化UI
    def initUI(self): 
        # 保存原始的resizeEvent方法
        self.original_resizeEvent = self.resizeEvent
        # 重写resizeEvent方法，调整背景大小
        self.resizeEvent = self._on_resize_event
        
        # 创建背景标签
        self.background_label = QLabel(self)
        self.background_label.setGeometry(0, 0, self.width(), self.height())
        self.background_label.lower()  # 将背景标签置于底层
        
        # 设置窗口属性，确保背景可见
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")
        
        # 尝试加载背景图片
        self.apply_background_image()
        
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

        # 班级下拉框
        self.class_combo = ComboBox()
        self.class_combo.addItems([self.class_name])
        self.class_combo.setCurrentText(self.class_name)

        # 小组下拉框
        self.group_combo = ComboBox()
        self.group_combo.addItems([self.group_name])
        self.group_combo.setCurrentText(self.group_name)

        # 性别下拉框
        self.gender_combo = ComboBox()
        self.gender_combo.addItems([self.gender_name])
        self.gender_combo.setCurrentText(self.gender_name)
        
        # 初始化抽取人数
        self.current_count = self.draw_count
        self.max_count = 0

        # 结果区域布局
        self.result_grid = QGridLayout()
        self.result_grid.setSpacing(1)
        self.result_grid.setAlignment(Qt.AlignTop | Qt.AlignCenter)

        scroll_area_container.addLayout(self.result_grid)
        
        # 设置容器并应用布局
        main_layout = QHBoxLayout(self)

        control_button_layout = QVBoxLayout()

        control_button_layout.addStretch(1)
        
        # 将control_panel布局包裹在QWidget中
        control_panel_widget = QWidget()
        control_button_layout.addWidget(control_panel_widget, 0, Qt.AlignBottom)

        # 将scroll_area添加到主布局中
        scroll_area.setWidget(container)
        # 创建一个QWidget来包含control_button_layout
        control_button_widget = QWidget()
        control_button_widget.setLayout(control_button_layout)
        # 将control_button_widget添加到主布局中
        main_layout.addWidget(control_button_widget)
        main_layout.addWidget(scroll_area)

        # 显示主布局
        self.setLayout(main_layout)
    
    def apply_background_image(self):
        """
        检查设置中的 enable_flash_background 和 enable_flash_background_color，
        如果开启则应用闪抽界面背景图片或背景颜色
        让界面变得更加美观个性化，就像给房间贴上漂亮的壁纸或涂上漂亮的颜色一样！"""
        try:
            # 读取自定义设置
            custom_settings_path = path_manager.get_settings_path('custom_settings.json')
            with open_file(custom_settings_path, 'r', encoding='utf-8') as f:
                custom_settings = json.load(f)
                
            # 检查是否启用了闪抽界面背景图标
            personal_settings = custom_settings.get('personal', {})
            enable_flash_background = personal_settings.get('enable_flash_background', True)
            enable_flash_background_color = personal_settings.get('enable_flash_background_color', False)
            
            # 优先应用背景颜色（如果启用）
            if enable_flash_background_color:
                flash_background_color = personal_settings.get('flash_background_color', '#FFFFFF')
                
                # 创建背景颜色标签并设置样式（使用标签方式，与图片保持一致）
                self.background_label = QLabel(self)
                self.background_label.setGeometry(0, 0, self.width(), self.height())
                self.background_label.setStyleSheet(f"background-color: {flash_background_color};")
                self.background_label.lower()  # 将背景标签置于底层
                
                # 设置窗口属性，确保背景可见
                self.setAttribute(Qt.WA_TranslucentBackground)
                self.setStyleSheet("background: transparent;")
                
                # 保存原始的resizeEvent方法
                self.original_resizeEvent = super(instant_draw, self).resizeEvent
                
                # 重写resizeEvent方法，调整背景大小
                self.resizeEvent = self._on_resize_event
                
                logger.info(f"已成功应用闪抽界面背景颜色 {flash_background_color}")
                
            # 如果背景颜色未启用，但背景图片启用了，则应用背景图片
            elif enable_flash_background:
                # 获取闪抽界面背景图片设置
                flash_background_image = personal_settings.get('flash_background_image', '')
                
                # 检查是否选择了背景图片
                if flash_background_image and flash_background_image != "无背景图":
                    # 获取背景图片文件夹路径
                    background_dir = path_manager.get_resource_path('images', 'background')
                    
                    # 检查文件夹是否存在
                    if background_dir.exists():
                        # 构建图片完整路径
                        image_path = background_dir / flash_background_image
                        
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
                                self.original_resizeEvent = super(instant_draw, self).resizeEvent
                                
                                # 重写resizeEvent方法，调整背景大小
                                self.resizeEvent = self._on_resize_event
                                
                                logger.info(f"已成功应用闪抽界面背景图片 {flash_background_image}，模糊度: {blur_value}，亮度: {brightness_value}%")
                            else:
                                logger.error(f"闪抽界面背景图片 {flash_background_image} 加载失败")
                        else:
                            logger.error(f"闪抽界面背景图片 {flash_background_image} 不存在")
                    else:
                        logger.error("背景图片文件夹不存在")
                else:
                    logger.info("未选择闪抽界面背景图片")
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
                
                logger.info("闪抽界面背景图片和颜色功能均未启用，使用默认背景")
                
        except FileNotFoundError:
            logger.error("自定义设置文件不存在，使用默认设置")
        except Exception as e:
            logger.error(f"应用闪抽界面背景图片或颜色时发生异常: {e}")
    
    def _on_resize_event(self, event):
        """
        当窗口大小改变时，自动调整背景图片大小，确保背景始终填满整个窗口
        就像魔法地毯一样，无论房间多大都能完美铺满！"""
        # 调用原始的resizeEvent，确保布局正确更新
        if hasattr(self, 'original_resizeEvent') and self.original_resizeEvent:
            self.original_resizeEvent(event)
        else:
            super(instant_draw, self).resizeEvent(event)
        
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
        """
        当窗口最大化时，确保所有控件正确适应新的窗口大小
        就像魔法变形术一样，让界面完美适应全屏状态！"""
        # 确保所有子控件适应最大化窗口
        for child in self.findChildren(QWidget):
            child.updateGeometry()
        
        # 强制重新布局
        QApplication.processEvents()
        
        # 延迟再次更新布局，确保所有控件都已适应
        QTimer.singleShot(100, self._delayed_layout_update)
    
    def _delayed_layout_update(self):
        """
        在窗口最大化后延迟执行布局更新，确保所有控件都已正确适应
        就像魔法延时术一样，给界面一些时间来完美调整！"""
        # 再次强制更新布局
        self.updateGeometry()
        self.update()
        
        # 确保所有子控件再次更新
        for child in self.findChildren(QWidget):
            child.updateGeometry()
        
        # 最后一次强制重新布局
        QApplication.processEvents()
