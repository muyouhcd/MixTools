import bpy
import requests
import zipfile
import os
import shutil
import subprocess

from . import bl_info

def get_addon_path():
    """
    查找addon文件夹路径。
    """
    file_path = os.path.normpath(os.path.dirname(__file__))
    while os.path.basename(file_path) != "addons" and os.path.dirname(file_path) != file_path:
        file_path = os.path.dirname(file_path)
    return file_path if os.path.basename(file_path) == "addons" else ''

def download_file(url, save_path):
    """
    从指定的 URL 下载文件并保存到本地路径。
    """
    try:
        response = requests.get(url)
        response.raise_for_status()
        with open(save_path, 'wb') as file:
            file.write(response.content)
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
    new_version_dir = os.path.join(base_path, expected_name)
    if os.path.exists(new_version_dir):
        return new_version_dir
    raise FileNotFoundError("新版本目录未找到。")

def version_tuple(version_string):
    """
    将字符串格式的版本号转换为整数元组。
    """
    return tuple(map(int, version_string.split(".")))

class UpdateAddonOperator(bpy.types.Operator):
    """Update Addon"""
    bl_idname = "wm.update_addon"
    bl_label = "更新插件"

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        self.start_update_process()
        return {'FINISHED'}

    def start_update_process(self):
        print("正在查找")
        user_repo = 'muyouhcd/MiaoTools'
        latest_release_info = self.get_latest_release_info(user_repo)
        current_version = bl_info["version"]
        latest_version = latest_release_info['tag_name']
        
        print("#####################当前版本#####################")
        print(current_version)
        print("#####################最新版本#####################")
        print(latest_version)

        if latest_release_info:
            latest_ver_tuple = version_tuple(latest_version)
            if current_version < latest_ver_tuple:
                download_url = latest_release_info['zipball_url']
                self.download_latest_version(download_url, latest_version)
            else:
                self.report({'INFO'}, 'No update available.')
        else:
            self.report({'ERROR'}, 'Could not retrieve release information.')

    def get_latest_release_info(self, user_repo):
        api_url = f"https://api.github.com/repos/{user_repo}/releases/latest"
        try:
            response = requests.get(api_url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.report({'ERROR'}, str(e))
            return None

    def download_latest_version(self, download_url, latest_version):
        try:
            response = requests.get(download_url)
            response.raise_for_status()

            temp_dir = bpy.app.tempdir + "addon_update/"
            print("Temp Directory for Update:", temp_dir)

            os.makedirs(temp_dir, exist_ok=True)
            zip_path = os.path.join(temp_dir, 'addon.zip')
            print("Downloading zip file to:", zip_path)

            with open(zip_path, 'wb') as file:
                file.write(response.content)

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)

            print("Extracted zip file to:", temp_dir)

            addon_dir = get_addon_path()
            print("Addon directory:", addon_dir)

            new_addon_dir = os.path.join(temp_dir, 'MiaoTools')
            print("New addon directory:", new_addon_dir)

            if os.path.exists(new_addon_dir):
                print("New MiaoTools directory:", addon_dir)
                self.copy_new_version(addon_dir, new_addon_dir)
            else:
                self.report({'ERROR'}, 'Failed to find MiaoTools folder after extraction')

            self.report({'INFO'}, f'Addon updated to {latest_version} successfully.')
        except Exception as e:
            self.report({'ERROR'}, 'Failed to download or install update: ' + str(e))

    def copy_new_version(self, addon_dir, new_addon_dir):
        old_files = {f for f in os.listdir(addon_dir)}
        new_files = {f for f in os.listdir(new_addon_dir)}
        duplicate_files = old_files.intersection(new_files)

        for file_name in duplicate_files:
            path_to_remove = os.path.join(addon_dir, file_name)
            if os.path.isdir(path_to_remove):
                shutil.rmtree(path_to_remove)
            else:
                os.remove(path_to_remove)
                
        for file_name in new_files:
            src_path = os.path.join(new_addon_dir, file_name)
            dst_path = os.path.join(addon_dir, file_name)
            if os.path.isdir(src_path):
                shutil.copytree(src_path, dst_path)
            else:
                shutil.copy2(src_path, dst_path)

class MyAddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    def draw(self, context):
        layout = self.layout
        layout.operator("wm.update_addon")

def register():
    bpy.utils.register_class(MyAddonPreferences)
    bpy.utils.register_class(UpdateAddonOperator)

def unregister():
    bpy.utils.unregister_class(MyAddonPreferences)
    bpy.utils.unregister_class(UpdateAddonOperator)