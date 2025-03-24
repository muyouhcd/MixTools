bl_info = {
    "name": "MiaoToolBox",
    "author": "MuyouHCD",
    "version": (4,8,50),
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
from. import Cleaner

def register():
    
    AutoBake.register()
    AutoBakeRemesh.register()
    AutoRender.register()
    AutoRig.register()
    AutolinkTexture.register()
    Combin.register()
    CorrectRotation.register()
    Exporter.register()
    MaterialOperator.register()
    MoveOrigin.register()
    operators.register()
    panels.register()
    RenameTool.register()
    renderconfig.register()
    RenderFrame.register()
    SelectTool.register()
    Cleaner.register()
    UVformater.register()
    update.register()
    Voxelizer.register()

def unregister():
    AutoBake.unregister()
    AutoBakeRemesh.unregister()
    AutoRender.unregister()
    AutoRig.unregister()
    AutolinkTexture.unregister()
    Combin.unregister()
    CorrectRotation.unregister()
    Exporter.unregister()
    MaterialOperator.unregister()
    MoveOrigin.unregister()
    operators.unregister()
    panels.unregister()
    RenameTool.unregister()
    renderconfig.unregister()
    RenderFrame.unregister()
    SelectTool.unregister()
    Cleaner.unregister()
    UVformater.unregister()
    update.unregister()
    Voxelizer.unregister()

if __name__ == "__main__":
    register()