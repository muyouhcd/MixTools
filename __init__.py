bl_info = {
    "name": "MiaoToolBox",
    "author": "MuyouHCD",
    "version": (4,8,58),
    "blender": (3, 6, 1),
    "location": "View3D",
    "description": "如遇到插件无法打开请手动切换至blender的python目录运行以下指令进行安装：python.exe -m pip install pillow",
    "warning": "",
    "wiki_url": "",
    "category": "Object",
}

import sys
import os
import subprocess
import glob
import bpy

#------------------------------------------------------------------------------------------
#自动检测缺失库进行补充安装

def get_addon_path():
    file_path = os.path.normpath(os.path.dirname(__file__))
    while os.path.basename(file_path) != "addons" and os.path.dirname(file_path) != file_path:
        file_path = os.path.dirname(file_path)
    return file_path if os.path.basename(file_path) == "addons" else ''

def install_local_packages(local_package_dir):
    if not os.path.isdir(local_package_dir):
        print(f"目录 '{local_package_dir}' 不存在。")
        return

    package_files = glob.glob(os.path.join(local_package_dir, "*.whl")) + glob.glob(os.path.join(local_package_dir, "*.tar.gz"))
    if not package_files:
        print(f"在目录 '{local_package_dir}' 中未找到任何可安装的文件。")
        return

    for package_file in package_files:
        print(f"正在安装 '{package_file}'...")
        cmd = [sys.executable, "-m", "pip", "install", package_file]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            print(result.stdout)
            if result.returncode != 0:
                print(f"安装 '{package_file}' 失败：{result.stderr}")
            else:
                print(f"安装 '{package_file}' 成功。")
        except Exception as e:
            print(f"安装 '{package_file}' 时出现异常：{e}")

def check_and_install_local_packages():
    local_addon_path = get_addon_path()
    if local_addon_path:
        local_package_dir = os.path.join(local_addon_path, "MiaoTools", "package")
        install_local_packages(local_package_dir)

check_and_install_local_packages()
#------------------------------------------------------------------------------------------

from . import update
from . import operators
from . import panels
from . import CorrectRotation
from . import renderconfig
from . import AutoRender
from . import Exporter
from . import Voxelizer
from . import AutoRig
from . import AutolinkTexture
from . import MoveOrigin
from . import AutoBake
from . import AutoBakeRemesh
from . import Combin
from . import RenameTool
from . import SelectTool
from . import MaterialOperator
from . import UVformater
from . import RenderFrame
from . import Cleaner
from . import LightOperator
from . import animationoperater
from . import RoleReplacer
from . import Importer
from . import BetterFbxOperation
from . import AutoHideClean
# from . import BoneConverter

def register():
    # 先注册基础模块
    update.register()
    operators.register()
    
    # 注册功能模块
    AutoBake.register()
    AutoBakeRemesh.register()
    AutoRender.register()
    AutoRig.register()
    AutolinkTexture.register()
    Combin.register()
    CorrectRotation.register()
    Exporter.register()
    LightOperator.register()
    MaterialOperator.register()
    MoveOrigin.register()
    RenameTool.register()
    renderconfig.register()
    RenderFrame.register()
    SelectTool.register()
    Cleaner.register()
    UVformater.register()
    Voxelizer.register()
    animationoperater.register()
    RoleReplacer.register()
    Importer.register()
    BetterFbxOperation.register()
    AutoHideClean.register()
    # BoneConverter.register()
    
    # 最后注册UI面板
    panels.register()

def unregister():
    # 先注销UI面板
    panels.unregister()
    
    # 注销功能模块
    RoleReplacer.unregister()
    animationoperater.unregister()
    Voxelizer.unregister()
    UVformater.unregister()
    Cleaner.unregister()
    SelectTool.unregister()
    RenderFrame.unregister()
    renderconfig.unregister()
    RenameTool.unregister()
    MoveOrigin.unregister()
    MaterialOperator.unregister()
    LightOperator.unregister()
    Exporter.unregister()
    CorrectRotation.unregister()
    Combin.unregister()
    AutolinkTexture.unregister()
    AutoRig.unregister()
    AutoRender.unregister()
    AutoBakeRemesh.unregister()
    AutoBake.unregister()
    Importer.unregister()
    BetterFbxOperation.unregister()
    AutoHideClean.unregister()
    # BoneConverter.unregister()
    
    # 最后注销基础模块
    operators.unregister()
    update.unregister()

if __name__ == "__main__":
    register()