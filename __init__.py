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
    bl_idname = "wm.update_addon"
    bl_label = "更新插件"
    
    # GitHub 仓库信息
    user_repo = 'muyouhcd/MiaoTools'

    def execute(self, context):
        self.start_update_process()
        return {'FINISHED'}

    def start_update_process(self):
        download_url = self.get_latest_release_download_url()

        if download_url:
            try:
                addon_path = self.get_addon_path()
                print("###############输出目录：########################")
                print(addon_path)
                self.download_and_unzip(download_url, addon_path)
                self.report({'INFO'}, f'插件更新成功，请重启Blender。')
            except Exception as e:
                self.report({'ERROR'}, f'插件更新失败: {e}')
        else:
            self.report({'ERROR'}, '最新版本下载链接未找到。')

    def get_addon_path(self):
        # 动态获取当前插件路径
        current_file_dir = os.path.dirname(os.path.realpath(__file__))
        return current_file_dir

    def get_latest_release_download_url(self):
        # 从GitHub API获取最新release的下载链接
        url = f"https://api.github.com/repos/{self.user_repo}/releases/latest"

        try:
            response = requests.get(url)
            latest_release = response.json()
            return latest_release['zipball_url']
        except Exception as e:
            print(f'获取最新版本链接失败: {e}')
            return None

    def download_and_unzip(self, url, addon_path):
        # 下载并解压zip到临时目录
        temp_extract_dir = os.path.join(addon_path, 'update_temp')

        # 如果临时目录存在，就先删除它
        if os.path.exists(temp_extract_dir):
            shutil.rmtree(temp_extract_dir)
        os.makedirs(temp_extract_dir)

        local_zip_path = os.path.join(addon_path, 'update.zip')

        with requests.get(url, stream=True) as r:
            with open(local_zip_path, 'wb') as f:
                shutil.copyfileobj(r.raw, f)

        with zipfile.ZipFile(local_zip_path, 'r') as zip_ref:
            # 解压到临时目录
            zip_ref.extractall(temp_extract_dir)

        # 删除下载的zip文件
        os.remove(local_zip_path)

        # 移动解压内容到正确的文件夹内，假设GitHub仓库名与插件名相同
        # GitHub将仓库名和提交/标签参考名追加到文件夹名
        top_level_dir = os.path.join(temp_extract_dir, os.listdir(temp_extract_dir)[0])
        addon_target_dir = os.path.join(addon_path, 'MiaoTools')

        # 如果目标插件目录已存在，则先删除
        if os.path.exists(addon_target_dir):
            shutil.rmtree(addon_target_dir)

        # 移动GitHub解压目录到addon_target_dir
        shutil.move(top_level_dir, addon_target_dir)

        # 移除临时目录
        shutil.rmtree(temp_extract_dir)

        self.report({'INFO'}, f'已成功更新至最新版本：{addon_target_dir}')

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