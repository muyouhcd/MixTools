import bpy
import requests
import zipfile
import os
import shutil
import subprocess
import threading
import time
from . import bl_info

def get_addon_path():
    file_path = os.path.normpath(os.path.dirname(__file__))
    while os.path.basename(file_path) != "addons" and os.path.dirname(file_path) != file_path:
        file_path = os.path.dirname(file_path)
    return file_path if os.path.basename(file_path) == "addons" else ''

def download_file(url, save_path, callback=None):
    """
    下载文件并支持进度回调
    """
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        # 获取文件大小
        total_size = int(response.headers.get('content-length', 0))
        block_size = 1024  # 每次读取的块大小
        downloaded = 0
        
        with open(save_path, 'wb') as file:
            for data in response.iter_content(block_size):
                downloaded += len(data)
                file.write(data)
                if callback and total_size > 0:
                    progress = downloaded / total_size
                    callback(progress)
        
        return True
    except Exception as e:
        raise IOError(f"文件下载失败: {e}")

def create_temp_directory(base_path, folder_name="addon_update"):
    """
    在基础路径中创建临时的文件夹。
    """
    temp_dir = os.path.join(base_path, folder_name)
    os.makedirs(temp_dir, exist_ok=True)
    return temp_dir

def unzip_file(zip_path, extract_to):
    """
    将 zip 文件解压缩到指定的目录中。
    """
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)

def find_new_version_directory(base_path, expected_name="MiaoTools"):
    """
    在基路径中查找预期名称的新版本目录。
    """
    for root, dirs, _ in os.walk(base_path):
        for dir_name in dirs:
            if expected_name in dir_name:
                return os.path.join(root, dir_name)
    
    # 尝试查找包含预期名称的任何目录
    extracted_dirs = next(os.walk(base_path))[1]
    if extracted_dirs:
        return os.path.join(base_path, extracted_dirs[0])
        
    raise FileNotFoundError("新版本目录未找到。")

# def backup_current_addon(addon_dir, backup_dir=None):
#     """
#     备份当前插件
#     """
#     if not backup_dir:
#         backup_dir = os.path.join(os.path.dirname(addon_dir), "MiaoTools_backup_" + time.strftime("%Y%m%d%H%M%S"))
    
#     if os.path.exists(addon_dir):
#         try:
#             shutil.copytree(addon_dir, backup_dir)
#             return backup_dir
#         except Exception as e:
#             print(f"备份失败: {e}")
#     return None

def version_tuple(version_string):
    """
    将字符串格式的版本号转换为整数元组。
    支持处理非数字版本号情况
    """
    parts = []
    for part in version_string.split("."):
        try:
            parts.append(int(part))
        except ValueError:
            # 处理包含非数字的部分（如 "1.2.3a"）
            for i, char in enumerate(part):
                if not char.isdigit():
                    numeric_part = part[:i]
                    parts.append(int(numeric_part) if numeric_part else 0)
                    break
            else:
                parts.append(int(part))
    return tuple(parts)

def clean_temp_files(directory):
    """
    清理临时文件
    """
    try:
        if os.path.exists(directory):
            shutil.rmtree(directory)
    except Exception as e:
        print(f"清理临时文件失败: {e}")

class UpdateStatus:
    """
    更新状态管理类
    """
    def __init__(self):
        self.message = "就绪"
        self.progress = 0
        self.is_updating = False
        self.error = None
        self.complete = False
        self.needs_restart = False

    def reset(self):
        self.message = "就绪"
        self.progress = 0
        self.is_updating = False
        self.error = None
        self.complete = False
        self.needs_restart = False

    def update(self, message, progress=None):
        self.message = message
        if progress is not None:
            self.progress = progress

# 全局状态对象
update_status = UpdateStatus()

class UpdateAddonOperator(bpy.types.Operator):
    """更新MiaoTools插件到最新版本"""
    bl_idname = "wm.update_addon"
    bl_label = "更新插件(仅支持blender3.4及以上版本)"
    
    _timer = None
    _thread = None

    @classmethod
    def poll(cls, context):
        # 只有在未进行更新时才允许操作
        return not update_status.is_updating

    def execute(self, context):
        # 重置状态
        update_status.reset()
        update_status.is_updating = True
        
        # 启动后台线程检查更新
        self._thread = threading.Thread(target=self.start_update_process)
        self._thread.daemon = True
        self._thread.start()
        
        # 启动定时器更新UI
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.5, window=context.window)
        wm.modal_handler_add(self)
        
        return {'RUNNING_MODAL'}
    
    def modal(self, context, event):
        if event.type == 'TIMER':
            # 更新界面显示
            for area in context.screen.areas:
                if area.type == 'PREFERENCES':
                    area.tag_redraw()
            
            # 检查是否完成或出错
            if update_status.error:
                self.report({'ERROR'}, update_status.error)
                self.cancel(context)
                return {'CANCELLED'}
            
            if update_status.complete:
                if update_status.needs_restart:
                    self.report({'INFO'}, "更新成功，请重启Blender以应用更改")
                else:
                    self.report({'INFO'}, "更新成功")
                self.cancel(context)
                return {'FINISHED'}
                
        return {'PASS_THROUGH'}
    
    def cancel(self, context):
        # 清除定时器
        if self._timer:
            wm = context.window_manager
            wm.event_timer_remove(self._timer)
            self._timer = None
        
        # 重置状态
        update_status.is_updating = False
    
    def start_update_process(self):
        try:
            update_status.update("正在获取最新版本信息...", 0.1)
            user_repo = 'muyouhcd/MiaoTools'
            latest_release_info = self.get_latest_release_info(user_repo)
            
            if not latest_release_info:
                update_status.error = "无法获取版本信息"
                return
                
            current_version = bl_info["version"]
            latest_version = latest_release_info['tag_name']
            
            print("当前版本:", current_version)
            print("最新版本:", latest_version)
            update_status.update(f"当前版本: {'.'.join(map(str, current_version))}, 最新版本: {latest_version}", 0.2)
            
            latest_ver_tuple = version_tuple(latest_version)
            if current_version < latest_ver_tuple:
                download_url = latest_release_info['zipball_url']
                changelog = latest_release_info.get('body', '无更新日志')
                
                # 显示更新信息并提示用户确认
                update_status.update(f"发现新版本 {latest_version}\n\n更新日志:\n{changelog}", 0.3)
                time.sleep(1)  # 给用户一些时间查看信息
                
                # 执行更新
                self.download_latest_version(download_url, latest_version)
            else:
                update_status.update("已经是最新版本", 1.0)
                update_status.complete = True
        except Exception as e:
            update_status.error = f"更新过程出错: {str(e)}"
            print(f"更新错误: {str(e)}")

    def get_latest_release_info(self, user_repo):
        api_url = f"https://api.github.com/repos/{user_repo}/releases/latest"
        try:
            # 添加超时和用户代理
            headers = {'User-Agent': 'MiaoTools-Updater/1.0'}
            response = requests.get(api_url, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError:
            update_status.error = "网络连接错误，请检查网络设置"
            return None
        except requests.exceptions.Timeout:
            update_status.error = "连接超时，请稍后再试"
            return None
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                update_status.error = "API请求限制，请稍后再试"
            else:
                update_status.error = f"HTTP错误: {e.response.status_code}"
            return None
        except Exception as e:
            update_status.error = f"获取版本信息失败: {str(e)}"
            return None

    def download_latest_version(self, download_url, latest_version):
        try:
            # 准备临时目录
            temp_dir = create_temp_directory(bpy.app.tempdir)
            update_status.update("准备下载更新...", 0.3)
            
            # 指定zip文件的保存路径
            zip_path = os.path.join(temp_dir, 'addon.zip')
            
            # 下载进度回调函数
            def download_progress(progress):
                update_status.update(f"正在下载更新... {int(progress * 100)}%", 0.3 + progress * 0.3)
            
            # 下载文件
            download_file(download_url, zip_path, download_progress)
            
            update_status.update("正在解压文件...", 0.6)
            # 解压zip文件
            unzip_file(zip_path, temp_dir)
            
            # 查找解压后的目录
            update_status.update("正在查找新版本目录...", 0.7)
            new_addon_dir = find_new_version_directory(temp_dir)
            
            if not new_addon_dir or not os.path.exists(new_addon_dir):
                update_status.error = "未在解压目录中找到预期的插件文件夹"
                return
            
            # 获取插件目录
            addon_dir = get_addon_path()
            if not addon_dir:
                update_status.error = "无法确定插件安装目录"
                return
                
            # 定位MiaoTools子目录
            mian_tools_path = os.path.join(addon_dir, "MiaoTools")
            if not os.path.exists(mian_tools_path):
                os.makedirs(mian_tools_path)
            
            # 备份当前版本
            update_status.update("正在备份当前版本...", 0.8)
            # backup_path = backup_current_addon(mian_tools_path)
            
            # 安装新版本
            update_status.update("正在安装新版本...", 0.9)
            self.copy_new_version(mian_tools_path, new_addon_dir)
            
            # 清理临时文件
            update_status.update("正在清理临时文件...", 0.95)
            clean_temp_files(temp_dir)
            
            # 更新完成
            update_status.update(f"更新成功! 当前版本：{latest_version}", 1.0)
            update_status.complete = True
            update_status.needs_restart = True
            
        except Exception as e:
            update_status.error = f"更新失败: {str(e)}"

    def copy_new_version(self, addon_dir, new_addon_dir):
        # 首先清除旧文件
        old_files = {f for f in os.listdir(addon_dir)}
        new_files = {f for f in os.listdir(new_addon_dir)}
        duplicate_files = old_files.intersection(new_files)

        for file_name in duplicate_files:
            path_to_remove = os.path.join(addon_dir, file_name)
            if os.path.isdir(path_to_remove):
                shutil.rmtree(path_to_remove)
            else:
                os.remove(path_to_remove)
                
        # 复制新文件
        for file_name in new_files:
            src_path = os.path.join(new_addon_dir, file_name)
            dst_path = os.path.join(addon_dir, file_name)
            if os.path.isdir(src_path):
                if os.path.exists(dst_path):
                    shutil.rmtree(dst_path)
                shutil.copytree(src_path, dst_path)
            else:
                shutil.copy2(src_path, dst_path)

class UpdateAddonPanel(bpy.types.Panel):
    """显示更新状态的面板"""
    bl_label = "插件更新状态"
    bl_idname = "OBJECT_PT_update_status"
    bl_space_type = 'PREFERENCES'
    bl_region_type = 'WINDOW'
    bl_context = "addons"
    
    @classmethod
    def poll(cls, context):
        # 只在更新过程中或有更新结果时显示
        return update_status.is_updating or update_status.complete or update_status.error
    
    def draw(self, context):
        layout = self.layout
        
        # 显示当前状态
        box = layout.box()
        box.label(text=update_status.message)
        
        # 如果正在更新，显示进度条
        if update_status.is_updating:
            progress = layout.row()
            progress.prop(context.window_manager, "progress", text="")
            context.window_manager.progress = update_status.progress
        
        # 如果更新完成，显示重启提示
        if update_status.complete and update_status.needs_restart:
            layout.label(text="请重启Blender以应用更改", icon='INFO')

class MyAddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    def draw(self, context):
        layout = self.layout
        
        # 检查是否可以显示更新按钮
        if update_status.is_updating:
            layout.label(text="正在更新中...", icon='LOOP_FORWARDS')
        else:
            row = layout.row()
            row.operator("wm.update_addon", icon='URL')
            
            # 如果有错误，显示错误信息
            if update_status.error:
                box = layout.box()
                box.label(text="更新出错:", icon='ERROR')
                box.label(text=update_status.error)
            
            # 如果更新完成，显示成功信息
            if update_status.complete:
                box = layout.box()
                box.label(text="更新成功!", icon='CHECKMARK')
                if update_status.needs_restart:
                    box.label(text="请重启Blender以应用更改")

def register():
    # 注册更新进度属性
    bpy.types.WindowManager.progress = bpy.props.FloatProperty(
        name="更新进度",
        default=0.0,
        min=0.0,
        max=1.0,
        subtype='PERCENTAGE'
    )
    
    # 安全地注册类
    classes = [
        UpdateAddonOperator,
        UpdateAddonPanel,
        MyAddonPreferences
    ]
    
    for cls in classes:
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass
        bpy.utils.register_class(cls)

def unregister():
    # 注销类
    classes = [
        MyAddonPreferences,
        UpdateAddonPanel,
        UpdateAddonOperator
    ]
    
    for cls in classes:
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass
    
    # 删除属性
    if hasattr(bpy.types.WindowManager, "progress"):
        delattr(bpy.types.WindowManager, "progress")