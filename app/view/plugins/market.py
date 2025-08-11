from qfluentwidgets import *
from qfluentwidgets import FluentIcon as FIF
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

import os
import json
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from datetime import datetime
from loguru import logger

from packaging.version import Version
from app.common.config import get_theme_icon, load_custom_font, VERSION


class MarketPluginButtonGroup(QWidget):
    """插件广场的插件按钮组"""
    def __init__(self, plugin_info, parent=None):
        super().__init__(parent)
        self.plugin_info = plugin_info
        
        # 主水平布局
        self.hBoxLayout = QHBoxLayout(self)
        self.hBoxLayout.setContentsMargins(10, 10, 10, 10)
        self.hBoxLayout.setSpacing(10)
        
        # 检查插件安装状态
        self.installed_version = self._check_installed_version()
        
        # 根据安装状态创建不同的按钮
        self.actionButton = PushButton(self._get_button_text(), self)
        self.actionButton.setIcon(self._get_button_icon())
        self.actionButton.clicked.connect(lambda: self.on_action_clicked())
        
        # 查看说明按钮
        self.readmeButton = PushButton("查看说明", self)
        self.readmeButton.setIcon(FIF.DOCUMENT)
        self.readmeButton.clicked.connect(lambda: self.on_readme_clicked())
        
        # 添加到布局
        self.hBoxLayout.addWidget(self.actionButton)
        self.hBoxLayout.addWidget(self.readmeButton)
        self.hBoxLayout.addStretch(1)
        
        # 设置固定高度
        self.setFixedHeight(50)
        
        # 检查插件版本兼容性并设置操作按钮状态
        self._update_action_button_state()

    def _get_repo_name_from_url(self, url):
        """从GitHub URL中提取仓库名称"""
        if "github.com" in url:
            parts = url.rstrip("/").split("/")
            if len(parts) >= 5:
                return parts[-1]
        return None
    
    def _check_installed_version(self):
        """检查插件是否已安装及版本"""
        plugin_dir = "app/plugin"
        if not os.path.exists(plugin_dir):
            logger.debug(f"插件目录不存在: {plugin_dir}")
            return None
        
        market_plugin_name = self.plugin_info.get("name")
        logger.debug(f"开始检查插件 '{market_plugin_name}' 的安装状态")
        
        # 查找已安装的插件
        for item in os.listdir(plugin_dir):
            item_path = os.path.join(plugin_dir, item)
            if not os.path.isdir(item_path):
                continue
            
            plugin_json_path = os.path.join(item_path, "plugin.json")
            if not os.path.exists(plugin_json_path):
                continue
            
            try:
                with open(plugin_json_path, 'r', encoding='utf-8') as f:
                    plugin_config = json.load(f)
                
                # 获取已安装插件的信息用于日志记录
                installed_plugin_name = plugin_config.get("name", "未知")
                
                # 检查是否是同一个插件
                if self._is_same_plugin(plugin_config):
                    version = plugin_config.get("version")
                    # 如果版本为空或None，返回None而不是空字符串
                    if not version or version.strip() == "":
                        logger.debug(f"插件匹配成功但版本信息为空: 已安装插件='{installed_plugin_name}'")
                        return None
                    logger.info(f"找到匹配的已安装插件: '{installed_plugin_name}'，版本: {version}")
                    return version
                else:
                    logger.debug(f"插件不匹配，跳过: 已安装='{installed_plugin_name}' vs 市场='{market_plugin_name}'")
                    
            except Exception as e:
                logger.error(f"检查已安装插件版本失败: {e}")
                continue
        
        logger.debug(f"未找到已安装的插件 '{market_plugin_name}'")
        return None
    
    def _is_same_plugin(self, plugin_config):
        """检查已安装插件是否与市场插件是同一个插件"""
        installed_plugin_url = plugin_config.get("url")
        market_plugin_url = self.plugin_info.get("url")
        
        # 只使用URL匹配插件
        if installed_plugin_url and market_plugin_url:
            return self._match_by_url(installed_plugin_url, market_plugin_url)
        
        # 如果没有URL信息，则无法匹配
        logger.debug(f"插件缺少URL信息，无法进行匹配")
        return False
    
    def _match_by_url(self, installed_url, market_url):
        """通过URL匹配插件"""
        if installed_url == market_url:
            logger.info(f"插件匹配成功 - URL匹配: {installed_url}")
            return True
        else:
            logger.debug(f"插件URL不匹配: 已安装={installed_url}, 市场={market_url}")
            return False
    
    def _match_by_name_and_author(self, installed_name, market_name, installed_author, market_author):
        """已弃用：此方法不再使用，仅保留URL匹配"""
        logger.debug(f"名称和作者匹配方法已弃用，仅使用URL匹配")
        return False
    
    def _check_plugin_version_compatibility(self):
        """检查插件版本与应用程序的兼容性"""
        try:
            # 获取插件要求的最低应用版本
            plugin_ver = self.plugin_info.get("plugin_ver")
            if not plugin_ver:
                # 如果没有设置插件版本要求，默认兼容
                logger.info(f"插件 {self.plugin_info['name']} 未设置插件版本要求")
                return True
            
            # 获取当前应用版本
            current_version = VERSION.lstrip('v')  # 移除v前缀
            required_version = plugin_ver.lstrip('v')  # 移除v前缀
            
            # 比较版本号
            if Version(current_version) >= Version(required_version):
                logger.info(f"插件 {self.plugin_info['name']} 版本兼容: 当前版本 {current_version} >= 最低要求 {required_version}")
                return True
            else:
                logger.warning(f"插件 {self.plugin_info['name']} 版本不兼容: 当前版本 {current_version} < 最低要求 {required_version}")
                return False
                
        except Exception as e:
            logger.error(f"检查插件版本兼容性失败: {e}")
            # 出错时默认禁用以确保安全
            return False
    
    def _is_plugin_in_market(self, market_plugins=None):
        """检查本地插件是否在插件广场中存在"""
        try:
            # 获取插件名称和URL
            plugin_name = self.plugin_info.get("name")
            plugin_url = self.plugin_info.get("url")
            
            if not plugin_name and not plugin_url:
                logger.warning(f"插件缺少名称和URL信息")
                return False
            
            # 如果没有传入市场插件列表，则获取（保持向后兼容）
            if market_plugins is None:
                plugin_list_url = "https://raw.githubusercontent.com/SECTL/SecRandom-market/master/Plugins/plugin_list.json"
                try:
                    # 设置请求头，模拟浏览器请求
                    req = urllib.request.Request(
                        plugin_list_url,
                        headers={
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                        }
                    )
                    
                    with urllib.request.urlopen(req, timeout=10) as response:
                        market_plugins = json.loads(response.read().decode('utf-8'))
                except urllib.error.HTTPError as e:
                    if e.code == 502:
                        logger.error(f"获取插件广场列表失败: 502 BadGateway")
                    else:
                        logger.error(f"获取插件广场列表失败: HTTP {e.code} {e.reason}")
                    # 如果获取失败，默认允许显示（避免因网络问题导致所有插件都不显示）
                    return True
                except urllib.error.URLError as e:
                    logger.error(f"获取插件广场列表失败: 网络错误 {e.reason}")
                    return True
                except json.JSONDecodeError as e:
                    logger.error(f"获取插件广场列表失败: JSON解析错误 {e}")
                    return True
                except Exception as e:
                    logger.error(f"获取插件广场列表失败: {e}")
                    # 如果获取失败，默认允许显示（避免因网络问题导致所有插件都不显示）
                    return True
            
            # 检查插件是否在广场中
            for market_plugin_key, market_plugin_info in market_plugins.items():
                # 跳过示例条目
                if market_plugin_key in ["其他插件...", "您的插件仓库名称"]:
                    continue
                
                # 仅通过URL匹配
                if plugin_url and market_plugin_info.get("url") == plugin_url:
                    logger.info(f"插件 {plugin_name} 在插件广场中存在")
                    return True
            
            logger.warning(f"插件 {plugin_name} 不在插件广场中")
            return False
            
        except Exception as e:
            logger.error(f"检查插件是否在插件广场中失败: {e}")
            # 出错时默认允许显示（避免因检查失败导致插件不显示）
            return True
    
    def _update_action_button_state(self):
        """根据版本兼容性更新操作按钮状态"""
        try:
            is_compatible = self._check_plugin_version_compatibility()
            
            if is_compatible:
                self.actionButton.setEnabled(True)
                logger.info(f"插件 {self.plugin_info['name']} 版本兼容，操作按钮已启用")
            else:
                self.actionButton.setEnabled(False)
                logger.warning(f"插件 {self.plugin_info['name']} 版本不兼容，操作按钮已禁用")
                
        except Exception as e:
            logger.error(f"更新操作按钮状态失败: {e}")
            self.actionButton.setEnabled(False)
    
    def _get_button_text(self):
        """根据安装状态获取按钮文本"""
        if self.installed_version is None:
            return "安装"
        elif self.installed_version == self.plugin_info.get("version"):
            return "卸载"
        else:
            return "更新"
    
    def _get_button_icon(self):
        """根据安装状态获取按钮图标"""
        if self.installed_version is None:
            return FIF.ADD
        elif self.installed_version == self.plugin_info.get("version"):
            return FIF.DELETE
        else:
            return FIF.SYNC
    
    def _download_plugin(self, url, branch, target_dir):
        """下载插件"""
        try:
            # 确保目标目录存在
            os.makedirs(target_dir, exist_ok=True)
            
            # 创建临时文件路径
            zip_path = os.path.join(target_dir, "plugin.zip")
            
            # 从URL中提取owner和repo名称
            if "github.com" in url:
                parts = url.rstrip("/").split("/")
                if len(parts) >= 5:
                    owner = parts[-2]
                    repo = parts[-1]
                    
                    # 获取插件版本
                    plugin_version = self.plugin_info.get("version", "latest")
                    
                    # 构建GitHub Releases API URL
                    if plugin_version == "latest":
                        releases_url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
                    else:
                        releases_url = f"https://api.github.com/repos/{owner}/{repo}/releases/tags/{plugin_version}"
                    
                    logger.info(f"正在获取发布信息: {releases_url}")
                    
                    # 获取发布信息
                    max_retries = 3
                    retry_count = 0
                    release_info = None
                    
                    while retry_count < max_retries:
                        try:
                            # 创建请求对象并添加User-Agent头
                            request = urllib.request.Request(releases_url)
                            request.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
                            
                            with urllib.request.urlopen(request, timeout=10) as response:
                                release_info = json.loads(response.read().decode('utf-8'))
                                break  # 成功获取，退出重试循环
                        except urllib.error.HTTPError as e:
                            if e.code == 502 and retry_count < max_retries - 1:
                                # 502错误，等待后重试
                                retry_delay = 2 * (retry_count + 1)  # 指数退避：2秒、4秒
                                logger.warning(f"GitHub API返回502错误，{retry_delay}秒后重试 (第{retry_count + 1}次重试): {e}")
                                time.sleep(retry_delay)
                                retry_count += 1
                                continue
                            else:
                                logger.error(f"获取发布信息HTTP错误 (状态码: {e.code}): {e}")
                                break
                        except urllib.error.URLError as e:
                            if retry_count < max_retries - 1:
                                retry_delay = 2 * (retry_count + 1)
                                logger.warning(f"获取发布信息URL错误，{retry_delay}秒后重试 (第{retry_count + 1}次重试): {e}")
                                time.sleep(retry_delay)
                                retry_count += 1
                                continue
                            else:
                                logger.error(f"获取发布信息URL错误: {e}")
                                break
                        except json.JSONDecodeError as e:
                            logger.error(f"解析发布信息JSON失败: {e}")
                            break
                        except Exception as e:
                            logger.error(f"获取发布信息未知错误: {e}")
                            break
                        
                        retry_count += 1
                    
                    if retry_count >= max_retries:
                        logger.error(f"获取发布信息失败：已达到最大重试次数 ({max_retries}次)")
                    
                    # 只有在成功获取发布信息时才处理assets
                    if release_info:
                        # 获取发布包的下载URL
                        assets = release_info.get("assets", [])
                        if assets:
                            # 优先选择.zip文件
                            zip_asset = None
                            for asset in assets:
                                if asset["name"].endswith(".zip"):
                                    zip_asset = asset
                                    break
                            
                            if zip_asset:
                                download_url = zip_asset["browser_download_url"]
                            else:
                                # 如果没有zip文件，使用第一个资源
                                download_url = assets[0]["browser_download_url"]
                    else:
                        logger.error(f"获取插件发布信息失败: {release_info}")
                        return False


            logger.info(f"正在下载插件: {download_url}")
            
            # 改进的下载方法，添加重试机制和错误处理
            max_retries = 3
            retry_count = 0
            download_success = False
            
            while retry_count < max_retries and not download_success:
                try:
                    # 创建请求对象并添加User-Agent头
                    request = urllib.request.Request(download_url)
                    request.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
                    
                    # 使用urlopen获取响应，设置超时
                    with urllib.request.urlopen(request, timeout=30) as response:
                        # 读取数据并写入文件
                        with open(zip_path, 'wb') as f:
                            f.write(response.read())
                        download_success = True
                        logger.info(f"插件下载成功 (第{retry_count + 1}次尝试)")
                        
                except urllib.error.HTTPError as e:
                    if e.code == 502 and retry_count < max_retries - 1:
                        # 502错误，等待后重试
                        retry_delay = 3 * (retry_count + 1)  # 指数退避：3秒、6秒、9秒
                        logger.warning(f"下载插件时返回502错误，{retry_delay}秒后重试 (第{retry_count + 1}次重试): {e}")
                        time.sleep(retry_delay)
                        retry_count += 1
                    else:
                        logger.error(f"下载插件HTTP错误 (状态码: {e.code}): {e}")
                        break
                        
                except urllib.error.URLError as e:
                    if retry_count < max_retries - 1:
                        retry_delay = 3 * (retry_count + 1)
                        logger.warning(f"下载插件URL错误，{retry_delay}秒后重试 (第{retry_count + 1}次重试): {e}")
                        time.sleep(retry_delay)
                        retry_count += 1
                    else:
                        logger.error(f"下载插件URL错误: {e}")
                        break
                        
                except Exception as e:
                    logger.error(f"下载插件未知错误: {e}")
                    break
                
                retry_count += 1
            
            if not download_success:
                logger.error(f"下载插件失败：已达到最大重试次数 ({max_retries}次)")
                return False
            
            # 解压文件
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(target_dir)
            
            # 清理临时文件
            if os.path.exists(zip_path):
                os.remove(zip_path)
            
            logger.info(f"插件下载成功: {target_dir}")
            return True
            
        except Exception as e:
            logger.error(f"下载插件失败: {e}")
            return False
    
    def on_action_clicked(self):
        """处理操作按钮点击事件"""
        button_text = self.actionButton.text()
        plugin_name = self.plugin_info.get("name")
        
        logger.info(f"插件 {plugin_name} 的操作按钮被点击，按钮文本: {button_text}")
        
        # 首先检查版本兼容性（仅对安装和更新操作）
        if button_text in ["安装", "更新"]:
            if not self._check_plugin_version_compatibility():
                # 如果版本不兼容，显示提示信息
                required_version = self.plugin_info.get("plugin_ver", "未知版本")
                
                dialog = Dialog(
                    "版本不兼容", 
                    f"该插件需要应用版本 {required_version} 或更高版本才能安装。\n当前版本: {VERSION}\n请更新应用后再试。", 
                    self
                )
                dialog.yesButton.setText("确定")
                dialog.cancelButton.hide()
                dialog.buttonLayout.insertStretch(1)
                dialog.exec()
                return
        
        if button_text == "安装":
            self._install_plugin()
        elif button_text == "卸载":
            self._uninstall_plugin()
        elif button_text == "更新":
            self._update_plugin()
    
    def _install_plugin(self):
        """安装插件"""
        plugin_name = self.plugin_info.get("name")
        url = self.plugin_info.get("url")
        branch = self.plugin_info.get("branch", "main")
        
        # 创建确认对话框
        install_dialog = Dialog("确认安装", f"确定要安装插件 {plugin_name} 吗？", self)
        install_dialog.yesButton.setText("安装")
        install_dialog.cancelButton.setText("取消")
        
        if install_dialog.exec():
            logger.info(f"开始安装插件: {plugin_name}")
            
            # 创建插件目录
            plugin_dir = "app/plugin"
            os.makedirs(plugin_dir, exist_ok=True)
            
            # 生成插件文件夹名称（使用仓库名称）
            repo_name = self._get_repo_name_from_url(url)
            if repo_name:
                folder_name = repo_name
            else:
                folder_name = plugin_name.lower().replace(" ", "_")
            target_dir = os.path.join(plugin_dir, folder_name)
            
            # 下载插件
            if self._download_plugin(url, branch, target_dir):
                # 检查是否有plugin.json文件
                plugin_json_path = os.path.join(target_dir, "plugin.json")
                if os.path.exists(plugin_json_path):
                    try:
                        with open(plugin_json_path, 'r', encoding='utf-8') as f:
                            plugin_config = json.load(f)
                        # 更新按钮状态
                        self.installed_version = plugin_config.get("version")
                        new_button_text = self._get_button_text()
                        logger.info(f"安装成功，更新按钮状态: {new_button_text}")
                        self.actionButton.setText(new_button_text)
                        self.actionButton.setIcon(self._get_button_icon())
                        
                        success_dialog = Dialog("安装成功", f"插件 {plugin_name} 安装成功！", self)
                        success_dialog.yesButton.setText("确定")
                        success_dialog.cancelButton.hide()
                        success_dialog.buttonLayout.insertStretch(1)
                        success_dialog.exec()
                            
                    except Exception as e:
                        logger.error(f"安装插件配置失败: {e}")
                        # 清理失败的安装
                        if os.path.exists(target_dir):
                            shutil.rmtree(target_dir)
                        
                        error_dialog = Dialog("安装失败", f"插件 {plugin_name} 安装失败: {str(e)}", self)
                        error_dialog.yesButton.setText("确定")
                        error_dialog.cancelButton.hide()
                        error_dialog.buttonLayout.insertStretch(1)
                        error_dialog.exec()
                else:
                    logger.error("未找到plugin.json文件")
                    # 清理失败的安装
                    if os.path.exists(target_dir):
                        shutil.rmtree(target_dir)
                    
                    error_dialog = Dialog("安装失败", f"插件 {plugin_name} 缺少plugin.json文件", self)
                    error_dialog.yesButton.setText("确定")
                    error_dialog.cancelButton.hide()
                    error_dialog.buttonLayout.insertStretch(1)
                    error_dialog.exec()
            else:
                error_dialog = Dialog("安装失败", f"插件 {plugin_name} 下载失败", self)
                error_dialog.yesButton.setText("确定")
                error_dialog.cancelButton.hide()
                error_dialog.buttonLayout.insertStretch(1)
                error_dialog.exec()
    
    def _uninstall_plugin(self):
        """卸载插件"""
        plugin_name = self.plugin_info.get("name")
        
        # 创建确认对话框
        uninstall_dialog = Dialog("确认卸载", f"确定要卸载插件 {plugin_name} 吗？此操作将删除插件文件夹且无法恢复。", self)
        uninstall_dialog.yesButton.setText("卸载")
        uninstall_dialog.cancelButton.setText("取消")
        
        if uninstall_dialog.exec():
            logger.info(f"开始卸载插件: {plugin_name}")
            
            # 查找插件目录
            plugin_dir = "app/plugin"
            if not os.path.exists(plugin_dir):
                error_dialog = Dialog("卸载失败", f"插件目录不存在", self)
                error_dialog.yesButton.setText("确定")
                error_dialog.cancelButton.hide()
                error_dialog.buttonLayout.insertStretch(1)
                error_dialog.exec()
                return
            
            # 查找已安装的插件
            for item in os.listdir(plugin_dir):
                item_path = os.path.join(plugin_dir, item)
                if not os.path.isdir(item_path):
                    continue
                
                plugin_json_path = os.path.join(item_path, "plugin.json")
                if not os.path.exists(plugin_json_path):
                    continue
                
                try:
                    with open(plugin_json_path, 'r', encoding='utf-8') as f:
                        plugin_config = json.load(f)
                    
                    # 获取已安装插件的信息用于日志记录
                    installed_plugin_name = plugin_config.get("name", "未知")
                    installed_plugin_url = plugin_config.get("url", "无")
                    market_plugin_name = plugin_name
                    market_plugin_url = self.plugin_info.get("url", "无")

                    # 检查是否是同一个插件（仅使用URL匹配）
                    if installed_plugin_url and market_plugin_url:
                        # 如果两个插件都有URL，则必须URL匹配
                        if installed_plugin_url == market_plugin_url:
                            match_reason = "URL匹配"
                            should_uninstall = True
                        else:
                            match_reason = "URL不匹配"
                            should_uninstall = False
                    else:
                        # 如果没有URL，则无法匹配（根据新的匹配逻辑）
                        match_reason = "缺少URL信息，无法匹配"
                        should_uninstall = False
                    
                    logger.info(f"匹配结果: {match_reason}, 是否卸载: {should_uninstall}")
                    
                    if should_uninstall:
                        # 删除插件文件夹
                        shutil.rmtree(item_path)
                        logger.info(f"成功卸载插件: {item_path} (匹配条件: 名称={installed_plugin_name == market_plugin_name}, URL={installed_plugin_url == market_plugin_url})")
                        
                        # 更新按钮状态
                        self.installed_version = None
                        new_button_text = self._get_button_text()
                        logger.info(f"卸载成功，更新按钮状态: {new_button_text}")
                        self.actionButton.setText(new_button_text)
                        self.actionButton.setIcon(self._get_button_icon())
                        
                        success_dialog = Dialog("卸载成功", f"插件 {plugin_name} 卸载成功！", self)
                        success_dialog.yesButton.setText("确定")
                        success_dialog.cancelButton.hide()
                        success_dialog.buttonLayout.insertStretch(1)
                        success_dialog.exec()
                        return
                        
                except Exception as e:
                    logger.error(f"卸载插件失败: {e}")
                    continue
            
            error_dialog = Dialog("卸载失败", f"未找到插件 {plugin_name}", self)
            error_dialog.yesButton.setText("确定")
            error_dialog.cancelButton.hide()
            error_dialog.buttonLayout.insertStretch(1)
            error_dialog.exec()
    
    def _update_plugin(self):
        """更新插件"""
        plugin_name = self.plugin_info.get("name")
        
        # 创建确认对话框
        update_dialog = Dialog("确认更新", f"确定要更新插件 {plugin_name} 吗？", self)
        update_dialog.yesButton.setText("更新")
        update_dialog.cancelButton.setText("取消")
        
        if update_dialog.exec():
            logger.info(f"开始更新插件: {plugin_name}")
            
            # 先卸载旧版本
            self._uninstall_plugin_internal()
            
            # 再安装新版本
            url = self.plugin_info.get("url")
            branch = self.plugin_info.get("branch", "main")
            
            # 创建插件目录
            plugin_dir = "app/plugin"
            os.makedirs(plugin_dir, exist_ok=True)
            
            # 生成插件文件夹名称（使用仓库名称）
            repo_name = self._get_repo_name_from_url(url)
            if repo_name:
                folder_name = repo_name
            else:
                folder_name = plugin_name.lower().replace(" ", "_")
            target_dir = os.path.join(plugin_dir, folder_name)
            
            # 下载插件
            if self._download_plugin(url, branch, target_dir):
                # 检查是否有plugin.json文件
                plugin_json_path = os.path.join(target_dir, "plugin.json")
                if os.path.exists(plugin_json_path):
                    try:
                        with open(plugin_json_path, 'r', encoding='utf-8') as f:
                            plugin_config = json.load(f)
                        
                        
                        # 更新按钮状态
                        self.installed_version = plugin_config.get("version")
                        new_button_text = self._get_button_text()
                        logger.info(f"更新成功，更新按钮状态: {new_button_text}")
                        self.actionButton.setText(new_button_text)
                        self.actionButton.setIcon(self._get_button_icon())
                        
                        success_dialog = Dialog("更新成功", f"插件 {plugin_name} 更新成功！", self)
                        success_dialog.yesButton.setText("确定")
                        success_dialog.cancelButton.hide()
                        success_dialog.buttonLayout.insertStretch(1)
                        success_dialog.exec()
                            
                    except Exception as e:
                        logger.error(f"更新插件配置失败: {e}")
                        # 清理失败的安装
                        if os.path.exists(target_dir):
                            shutil.rmtree(target_dir)
                        
                        error_dialog = Dialog("更新失败", f"插件 {plugin_name} 更新失败: {str(e)}", self)
                        error_dialog.yesButton.setText("确定")
                        error_dialog.cancelButton.hide()
                        error_dialog.buttonLayout.insertStretch(1)
                        error_dialog.exec()
                else:
                    logger.error("未找到plugin.json文件")
                    # 清理失败的安装
                    if os.path.exists(target_dir):
                        shutil.rmtree(target_dir)
                    
                    error_dialog = Dialog("更新失败", f"插件 {plugin_name} 缺少plugin.json文件", self)
                    error_dialog.yesButton.setText("确定")
                    error_dialog.cancelButton.hide()
                    error_dialog.buttonLayout.insertStretch(1)
                    error_dialog.exec()
            else:
                error_dialog = Dialog("更新失败", f"插件 {plugin_name} 下载失败", self)
                error_dialog.yesButton.setText("确定")
                error_dialog.cancelButton.hide()
                error_dialog.buttonLayout.insertStretch(1)
                error_dialog.exec()
    
    def _uninstall_plugin_internal(self):
        """内部卸载插件（不显示对话框）"""
        plugin_name = self.plugin_info.get("name")
        plugin_dir = "app/plugin"
        
        if not os.path.exists(plugin_dir):
            return False
        
        # 查找已安装的插件
        for item in os.listdir(plugin_dir):
            item_path = os.path.join(plugin_dir, item)
            if not os.path.isdir(item_path):
                continue
            
            plugin_json_path = os.path.join(item_path, "plugin.json")
            if not os.path.exists(plugin_json_path):
                continue
            
            try:
                with open(plugin_json_path, 'r', encoding='utf-8') as f:
                    plugin_config = json.load(f)
                
                # 检查是否是同一个插件（通过名称或URL匹配，与_check_installed_version保持一致）
                installed_plugin_name = plugin_config.get("name")
                installed_plugin_url = plugin_config.get("url")
                market_plugin_name = plugin_name
                market_plugin_url = self.plugin_info.get("url")
                
                # 优先使用URL匹配，避免同名插件误卸载
                if installed_plugin_url and market_plugin_url:
                    # 如果两个插件都有URL，则必须URL匹配
                    if installed_plugin_url == market_plugin_url:
                        match_reason = "URL匹配"
                        should_uninstall = True
                    else:
                        match_reason = "URL不匹配"
                        should_uninstall = False
                else:
                    # 如果没有URL，则使用名称匹配，但要更严格
                    if installed_plugin_name == market_plugin_name:
                        # 额外检查作者信息，避免同名插件误匹配
                        installed_author = plugin_config.get("author")
                        market_author = self.plugin_info.get("author")
                        if installed_author and market_author and installed_author == market_author:
                            match_reason = "名称和作者匹配"
                            should_uninstall = True
                        else:
                            # 如果没有作者信息或作者不匹配，则不认为是同一个插件
                            match_reason = "名称匹配但作者不匹配"
                            should_uninstall = False
                    else:
                        match_reason = "名称不匹配"
                        should_uninstall = False
                
                logger.info(f"内部卸载匹配结果: {match_reason}, 是否卸载: {should_uninstall}")
                
                if should_uninstall:
                    # 删除插件文件夹
                    shutil.rmtree(item_path)
                    logger.info(f"成功卸载插件: {item_path} (匹配条件: 名称={installed_plugin_name == market_plugin_name}, URL={installed_plugin_url == market_plugin_url})")
                    return True
                    
            except Exception as e:
                logger.error(f"卸载插件失败: {e}")
                continue
        
        return False
    
    def on_readme_clicked(self):
        """处理查看说明按钮点击事件"""
        # 对于插件广场，显示插件描述信息
        plugin_name = self.plugin_info.get("name")
        description = self.plugin_info.get("description", "暂无描述")
        version = self.plugin_info.get("version", "未知版本")
        author = self.plugin_info.get("author", "未知作者")
        url = self.plugin_info.get("url", "")
        
        info_text = f"**插件名称**: {plugin_name}\n\n"
        info_text += f"**版本**: {version}\n\n"
        info_text += f"**作者**: {author}\n\n"
        info_text += f"**描述**: {description}\n\n"
        if url:
            info_text += f"**仓库地址**: [{url}]({url})\n\n"
        
        if self.installed_version:
            info_text += f"**已安装版本**: {self.installed_version}\n\n"
        
        # 创建信息对话框
        info_dialog = Dialog(f"插件信息 - {plugin_name}", info_text, self)
        info_dialog.yesButton.setText("确定")
        info_dialog.cancelButton.hide()
        info_dialog.buttonLayout.insertStretch(1)
        info_dialog.exec()


class PluginMarketPage(GroupHeaderCardWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("插件广场")
        self.setBorderRadius(8)
        self.settings_file = "app/Settings/plugin_settings.json"
        
        # 插件市场仓库信息
        self.market_repo_url = "https://github.com/SECTL/SecRandom-market"
        self.plugin_list_url = "https://raw.githubusercontent.com/SECTL/SecRandom-market/master/Plugins/plugin_list.json"
        
        # 初始化时加载插件列表
        self.load_market_plugins()
    
    def load_plugin_settings(self):
        """🌟 小鸟游星野 - 加载插件设置"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    return settings.get("plugin_settings", {})
            else:
                return {"run_plugins_on_startup": False, "fetch_plugin_list_on_startup": True}
        except Exception as e:
            logger.error(f"🌟 小鸟游星野 - 加载插件设置失败: {str(e)}")
            return {"run_plugins_on_startup": False, "fetch_plugin_list_on_startup": True}
    
    def fetch_plugin_list(self):
        """从远程仓库获取插件列表"""
        import time
        
        max_retries = 3
        retry_delay = 2  # 秒
        
        for attempt in range(max_retries):
            try:
                logger.info(f"正在获取插件列表: {self.plugin_list_url} (尝试 {attempt + 1}/{max_retries})")
                
                # 设置请求头，模拟浏览器请求
                req = urllib.request.Request(
                    self.plugin_list_url,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                    }
                )
                
                # 发送HTTP请求获取插件列表
                with urllib.request.urlopen(req, timeout=10) as response:
                    data = response.read().decode('utf-8')
                    plugin_list = json.loads(data)
                
                logger.info(f"成功获取插件列表，共 {len(plugin_list)} 个插件")
                return plugin_list
                
            except urllib.error.HTTPError as e:
                if e.code == 502:
                    logger.warning(f"遇到502 BadGateway错误，第{attempt + 1}次重试")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        retry_delay *= 2  # 指数退避
                        continue
                    else:
                        logger.error(f"获取插件列表失败: 502 BadGateway (已重试{max_retries}次)")
                        return {}
                else:
                    logger.error(f"获取插件列表失败: HTTP {e.code} {e.reason}")
                    return {}
                    
            except urllib.error.URLError as e:
                logger.error(f"获取插件列表失败: 网络错误 {e.reason}")
                return {}
                
            except json.JSONDecodeError as e:
                logger.error(f"获取插件列表失败: JSON解析错误 {e}")
                return {}
                
            except Exception as e:
                logger.error(f"获取插件列表失败: {e}")
                return {}
        
        return {}
    
    def get_plugin_repo_icon(self, repo_url, branch="main"):
        """获取插件仓库图标"""
        try:
            # 从GitHub URL中提取owner和repo
            if "github.com/" in repo_url:
                # 处理GitHub URL
                if repo_url.endswith(".git"):
                    repo_url = repo_url[:-4]  # 移除.git后缀
                
                parts = repo_url.split("github.com/")[-1].split("/")
                if len(parts) >= 2:
                    owner = parts[0]
                    repo = parts[1]
                    
                    # 添加调试日志
                    logger.debug(f"解析仓库信息 - owner: {owner}, repo: {repo}, branch: {branch}")
                    
                    # 构建图标文件URL：插件仓库名称\icon.png
                    raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{repo}/icon.png"
                    
                    # 添加调试日志
                    logger.debug(f"尝试获取图标: {raw_url}")
                    
                    try:
                        # 设置请求头，模拟浏览器请求
                        req = urllib.request.Request(
                            raw_url,
                            headers={
                                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                            }
                        )
                        
                        # 尝试访问图标文件
                        with urllib.request.urlopen(req, timeout=5) as response:
                            if response.status == 200:
                                # 下载图标数据
                                icon_data = response.read()
                                
                                # 直接从内存数据创建QIcon
                                pixmap = QPixmap()
                                pixmap.loadFromData(icon_data)
                                
                                if not pixmap.isNull():
                                    logger.info(f"成功获取插件图标: {raw_url}")
                                    return QIcon(pixmap)
                                else:
                                    logger.debug(f"图标数据无效，无法创建QPixmap")
                            else:
                                logger.debug(f"图标文件访问失败，状态码: {response.status}")
                    except urllib.error.HTTPError as e:
                        if e.code == 502:
                            logger.debug(f"获取图标文件遇到502 BadGateway错误: {raw_url}")
                        else:
                            logger.debug(f"获取图标文件HTTP错误 {e.code}: {raw_url}")
                    except urllib.error.URLError as e:
                        logger.debug(f"获取图标文件网络错误: {e.reason} - {raw_url}")
                    except Exception as e:
                        logger.debug(f"访问图标文件异常: {e}")
                else:
                    logger.warning(f"无法解析GitHub URL: {repo_url}, parts: {parts}")
            else:
                logger.warning(f"非GitHub URL: {repo_url}")
            
            logger.warning(f"无法获取插件仓库图标: {repo_url}")
            return None
            
        except Exception as e:
            logger.error(f"获取插件仓库图标失败: {e}")
            return None
    
    def create_plugin_button_group(self, plugin_info):
        """创建插件按钮组"""
        button_group = MarketPluginButtonGroup(plugin_info, self)
        return button_group
    
    def load_market_plugins(self):
        """🌟 小鸟游星野 - 加载插件市场中的插件列表"""
        # 🌟 小鸟游星野 - 检查是否需要在启动时获取插件列表
        plugin_settings = self.load_plugin_settings()
        if not plugin_settings.get("fetch_plugin_list_on_startup", True):
            logger.info("🌟 小鸟游星野 - 根据设置，跳过获取插件列表")
            # 显示跳过获取插件列表的提示
            no_plugin_label = BodyLabel("根据设置，跳过获取插件列表", self)
            no_plugin_label.setAlignment(Qt.AlignCenter)
            self.addGroup(get_theme_icon("ic_fluent_cloud_off_20_filled"), "跳过获取插件列表", "可在插件设置中启用此功能", no_plugin_label)
            return
        
        # 获取插件列表
        plugin_list = self.fetch_plugin_list()
        
        if not plugin_list:
            # 显示无插件提示
            no_plugin_label = BodyLabel("无法获取插件列表，请检查网络连接", self)
            no_plugin_label.setAlignment(Qt.AlignCenter)
            self.addGroup(get_theme_icon("ic_fluent_cloud_download_20_filled"), "无法获取插件列表", "请检查网络连接后重试", no_plugin_label)
            return
        
        # 过滤掉示例条目
        filtered_plugins = {}
        for key, value in plugin_list.items():
            # 跳过"其他插件..."等示例条目
            if key in ["其他插件...", "您的插件仓库名称"]:
                continue
            
            # 检查必需字段
            required_fields = ["name", "version", "description", "author", "url", "branch"]
            if all(field in value for field in required_fields):
                filtered_plugins[key] = value
            else:
                logger.warning(f"插件 {key} 缺少必需字段，跳过")
        
        if not filtered_plugins:
            # 显示无有效插件提示
            no_plugin_label = BodyLabel("暂无可用插件", self)
            no_plugin_label.setAlignment(Qt.AlignCenter)
            self.addGroup(get_theme_icon("ic_fluent_extensions_20_filled"), "暂无可用插件", "插件市场中暂无可用插件", no_plugin_label)
            return
        
        # 一次性获取插件广场列表，避免重复请求
        market_plugins = None
        try:
            plugin_list_url = "https://raw.githubusercontent.com/SECTL/SecRandom-market/master/Plugins/plugin_list.json"
            
            # 设置请求头，模拟浏览器请求
            req = urllib.request.Request(
                plugin_list_url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                market_plugins = json.loads(response.read().decode('utf-8'))
            logger.info(f"成功获取插件广场列表，共 {len(market_plugins)} 个插件")
        except urllib.error.HTTPError as e:
            if e.code == 502:
                logger.error(f"获取插件广场列表失败: 502 BadGateway")
            else:
                logger.error(f"获取插件广场列表失败: HTTP {e.code} {e.reason}")
            # 如果获取失败，设置为None，让每个插件自己处理
            market_plugins = None
        except urllib.error.URLError as e:
            logger.error(f"获取插件广场列表失败: 网络错误 {e.reason}")
            market_plugins = None
        except json.JSONDecodeError as e:
            logger.error(f"获取插件广场列表失败: JSON解析错误 {e}")
            market_plugins = None
        except Exception as e:
            logger.error(f"获取插件广场列表失败: {e}")
            # 如果获取失败，设置为None，让每个插件自己处理
            market_plugins = None
        
        # 为每个插件创建按钮组
        for plugin_key, plugin_info in filtered_plugins.items():
            try:
                button_group = self.create_plugin_button_group(plugin_info)
                
                # 检查插件是否在插件广场中存在（传入已获取的列表）
                if button_group._is_plugin_in_market(market_plugins):
                    # 获取插件仓库图标
                    repo_url = plugin_info.get("url", "")
                    branch = plugin_info.get("branch", "main")
                    
                    icon = self.get_plugin_repo_icon(repo_url, branch)
                    
                    # 如果获取仓库图标失败，使用默认图标
                    if icon is None:
                        icon = get_theme_icon("ic_fluent_branch_fork_link_20_filled")
                    
                    # 构建描述信息
                    description = plugin_info.get("description", "暂无描述")
                    version = plugin_info.get("version", "未知版本")
                    author = plugin_info.get("author", "未知作者")
                    update_date = plugin_info.get("update_date", "未知")
                    
                    subtitle = f"版本: {version} | 作者: {author} | 更新: {update_date} | 仓库: {description}"

                    # 添加到界面
                    self.addGroup(icon, plugin_info["name"], subtitle, button_group)
                else:
                    logger.info(f"插件 {plugin_info.get('name')} 不在插件广场中，跳过显示")
                    button_group.deleteLater()
                    
            except Exception as e:
                logger.error(f"创建插件 {plugin_key} 的界面失败: {e}")
                continue
        
        logger.info(f"插件市场加载完成，共显示 {len(filtered_plugins)} 个插件")
    
    def refresh_plugin_list(self):
        """🌟 小鸟游星野 - 刷新插件列表"""
        # 🌟 小鸟游星野 - 检查是否允许获取插件列表
        plugin_settings = self.load_plugin_settings()
        if not plugin_settings.get("fetch_plugin_list_on_startup", True):
            logger.info("🌟 小鸟游星野 - 根据设置，不允许获取插件列表")
            info_dialog = Dialog("设置限制", "当前设置禁止获取插件列表，请先在插件设置中启用此功能", self)
            info_dialog.yesButton.setText("确定")
            info_dialog.cancelButton.hide()
            info_dialog.buttonLayout.insertStretch(1)
            info_dialog.exec()
            return
            
        logger.info("🌟 小鸟游星野 - 刷新插件列表")
        self.load_market_plugins()