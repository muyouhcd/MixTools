bl_info = {
    "name": "MiAO",
    "author": "MuyouHCD",
    "version": (4,6,0),
    "blender": (3, 6, 1),
    "location": "View3D",
    "description": "python.exe -m pip install pillow",
    "warning": "",
    "wiki_url": "",
    "category": "Object",
}

import bpy
from . import operators
from . import panels
from . import CorrectRotation
from . import renderconfig
from . import remove_unused_material_slots
from . import auto_render
from . import AutoRenameCar
from . import ExportFbx
from . import Voxelizer


import requests
import zipfile
import os
import shutil


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
        print("+++++++++++++++++++++++++++++++++++++++++++++++++++++")
        user_repo = 'muyouhcd/MiaoTools'
        current_version = bl_info["version"]
        latest_release_info = self.get_latest_release_info(user_repo)
        # print(user_repo)
        print("#####################当前版本#####################")
        print(current_version)
        print("##############################################")
        # print(latest_release_info)

        if latest_release_info:
            latest_version = latest_release_info['tag_name']
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
            os.makedirs(temp_dir, exist_ok=True)

            zip_path = os.path.join(temp_dir, 'addon.zip')
            with open(zip_path, 'wb') as file:
                file.write(response.content)

            # 解压缩文件
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)

            # 根据你的情况找到插件的文件夹和新解压出来的版本目录
            addon_dir = os.path.join(bpy.utils.user_resource('SCRIPTS'), 'addons', 'your_addon_folder_name/')
            new_addon_dir = temp_dir + [name for name in os.listdir(temp_dir) if os.path.isdir(os.path.join(temp_dir, name))][0]

            # 将新版本文件复制到插件目录
            self.copy_new_version(addon_dir, new_addon_dir)

            self.report({'INFO'}, f'Addon updated to {latest_version} successfully.')
        except Exception as e:
            self.report({'ERROR'}, 'Failed to download or install update: ' + str(e))

    def copy_new_version(self, addon_dir, new_addon_dir):
        # 删除旧文件
        shutil.rmtree(addon_dir)  
        # 把新版本复制到插件目录
        shutil.copytree(new_addon_dir, addon_dir)  


class MyAddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    # 这里可以添加其他你插件中的选项

    def draw(self, context):
        layout = self.layout
        layout.operator("wm.update_addon")




def register():
    bpy.utils.register_class(MyAddonPreferences)
    bpy.utils.register_class(UpdateAddonOperator)

    operators.register()
    renderconfig.register()
    CorrectRotation.register()
    remove_unused_material_slots.register()
    auto_render.register()
    panels.register()
    AutoRenameCar.register()
    ExportFbx.register()
    Voxelizer.register()
    # AutoRig.register()


def unregister():
    bpy.utils.unregister_class(MyAddonPreferences)
    bpy.utils.unregister_class(UpdateAddonOperator)    

    operators.unregister()
    panels.unregister()
    auto_render.unregister()
    renderconfig.unregister()
    CorrectRotation.unregister()
    remove_unused_material_slots.unregister()
    AutoRenameCar.unregister()
    ExportFbx.unregister()
    Voxelizer.unregister()
    # AutoRig.unregister()

    
    
    

if __name__ == "__main__":
    register()