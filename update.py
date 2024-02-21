
import bpy
import requests
import zipfile
import os
import shutil
import subprocess

from . import bl_info

#查找addon文件夹路径
def get_addon_path():
    # 获取插件的文件名（通常是__init__.py或其他主文件）
    file_path = os.path.normpath(os.path.dirname(__file__))
    # 循环向上寻找，直到到达"addons"文件夹
    while os.path.basename(file_path) != "addons" and os.path.dirname(file_path) != file_path:
        file_path = os.path.dirname(file_path)
    # 最终file_path将是插件根目录的路径
    return file_path if os.path.basename(file_path) == "addons" else ''

#更新脚本
def version_tuple(version_string):
    # 假设：'version_string' 是一个像 '1.0.2' 这样的字符串
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
        
        # print(user_repo)
        print("#####################当前版本#####################")
        print(current_version)
        print("#####################最新版本#####################")
        print(latest_version)
        # print(latest_release_info)

        if latest_release_info:
            
            # 将字符串格式的版本号转换为整数元组
            latest_ver_tuple = version_tuple(latest_version)

            # 不需要转换current_version，因为它已经是一个元组
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
            response.raise_for_status()  # 抛出HTTP错误
            return response.json()
        except Exception as e:
            self.report({'ERROR'}, str(e))
            return None

    def download_latest_version(self, download_url, latest_version):
        try:
            # 下载最新版本
            response = requests.get(download_url)
            response.raise_for_status()
            
            # 确保有一个用于下载和解压的临时目录
            temp_dir = bpy.app.tempdir + "addon_update/"

            print("Temp Directory for Update:", temp_dir)  # 打印临时目录路径

            os.makedirs(temp_dir, exist_ok=True)

            zip_path = os.path.join(temp_dir, 'addon.zip')

            print("Downloading zip file to:", zip_path)  # 正在下载.zip文件到该路径

            with open(zip_path, 'wb') as file:
                file.write(response.content)

            # 解压缩文件
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)

            print("Extracted zip file to:", temp_dir)  # 解压后的文件存放于此目录

            # 根据你的情况找到插件的文件夹和新解压出来的版本目录
            # addon_dir = os.path.join(bpy.utils.user_resource('SCRIPTS'), 'addons', 'your_addon_folder_name/')
            addon_dir = get_addon_path()

            # new_addon_dir = temp_dir + [name for name in os.listdir(temp_dir) if os.path.isdir(os.path.join(temp_dir, name))][0]
            repo_dir_name = next(os.walk(temp_dir))[1][0]
            repo_dir = os.path.join(temp_dir, repo_dir_name)
            miatools_dir_name = 'MiaoTools' # 如果它在不同的路径下，请相应调整这个变量
            new_addon_dir = os.path.join(repo_dir, miatools_dir_name)   
            
            print("New addon directory:", new_addon_dir)  # 新插件目录的路径

            # 将新版本文件复制到插件目录
            
            if os.path.exists(new_addon_dir):
                print("New MiaoTools directory:", new_addon_dir)  # 打印新插件目录的路径
                self.copy_new_version(addon_dir, new_addon_dir)
            else:
                self.report({'ERROR'}, 'Failed to find MiaoTools folder after extraction')


            self.report({'INFO'}, f'Addon updated to {latest_version} successfully.')
        except Exception as e:
            self.report({'ERROR'}, 'Failed to download or install update: ' + str(e))

    def copy_new_version(self, addon_dir, new_addon_dir):
        # 获取当前插件目录中的所有文件和文件夹的列表
        old_files = {f for f in os.listdir(addon_dir)}

        # 获取解压后新版本中的所有文件和文件夹的列表
        new_files = {f for f in os.listdir(new_addon_dir)}

        # 找出重复的文件，即旧插件目录中需要被替换的文件
        duplicate_files = old_files.intersection(new_files)

        # 遍历重复文件列表，并只删除这些文件和文件夹
        for file_name in duplicate_files:
            path_to_remove = os.path.join(addon_dir, file_name)
            if os.path.isdir(path_to_remove):
                shutil.rmtree(path_to_remove)
            else:
                os.remove(path_to_remove)
                
        # 现在，旧目录中没有重复文件，可以把新版本复制过去了
        for file_name in new_files:
            src_path = os.path.join(new_addon_dir, file_name)
            dst_path = os.path.join(addon_dir, file_name)
            if os.path.isdir(src_path):
                shutil.copytree(src_path, dst_path)
            else:
                shutil.copy2(src_path, dst_path)



class MyAddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    # 这里可以添加其他你插件中的选项

    def draw(self, context):
        layout = self.layout
        layout.operator("wm.update_addon")


def register():
    bpy.utils.register_class(MyAddonPreferences)
    bpy.utils.register_class(UpdateAddonOperator)


def unregister():
    bpy.utils.unregister_class(MyAddonPreferences)
    bpy.utils.unregister_class(UpdateAddonOperator)    
