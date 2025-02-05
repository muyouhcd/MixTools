bl_info = {
    "name": "MiaoToolBox",
    "author": "MuyouHCD",
    "version": (4,8,16),
    "blender": (3, 6, 1),
    "location": "View3D",
    "description": "python.exe -m pip install pillow",
    "warning": "",
    "wiki_url": "",
    "category": "Object",
}
import sys
import os
import subprocess
import bpy
#------------------------------------------------------------------------------------------
#自动检测缺失库进行补充安装

def install_and_import(module_name, package_name=None):
    package_name = package_name or module_name
    try:
        __import__(module_name)
        print(f"模块 '{module_name}' 已经安装。")
    except ImportError:
        print(f"模块 '{module_name}' 未安装。正在安装 '{package_name}'...")
        try:
            # 获取 Blender 内置的 Python 解释器路径
            python_executable = sys.executable
            python_bin_dir = os.path.dirname(python_executable)

            # 使用完整的路径，并用引号括起来
            cmd = f'cmd /c "cd /d "{python_bin_dir}" & "{python_executable}" -m pip install {package_name}"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

            print(result.stdout)
            print(result.stderr)

            if result.returncode != 0:
                raise Exception(f"命令执行失败：{result.stderr}")

            print(f"模块 '{package_name}' 安装成功。")
        except Exception as e:
            print(f"模块 '{package_name}' 安装失败：{e}")
            raise
    finally:
        globals()[module_name] = __import__(module_name)
        print(f"模块 '{module_name}' 已经导入。")

# 检查并安装模块
def check_and_install_modules():
    # 使用 'PIL' 模块，实际与 'Pillow' 包名关联
    required_modules = {'PIL': 'Pillow'}
    for module_name, package_name in required_modules.items():
        install_and_import(module_name, package_name)

#------------------检测模块是否存在-------------------
check_and_install_modules()
#------------------------------------------------------------------------------------------

from . import update
from . import operators
from . import panels
from . import CorrectRotation
from . import renderconfig
from . import remove_unused_material_slots
from . import auto_render
from . import AutoRenameCar
from . import ExportFbx
from . import Voxelizer
# from . import AutoRig
from . import AutoRig_2
from . import AutolinkTexture
from . import MoveOrigin
from . import AutoBake
from . import AutoBakeRemesh
from . import Combin
from . import RenameTool
from . import RemoveObj
from . import SelectTool
from . import ExoprtObj
from . import MaterialOperator
from . import UVCleaner
from . import UVformater
from . import RenderFrame
from . import BoneProcess


def register():
    operators.register()
    update.register()
    renderconfig.register()
    CorrectRotation.register()
    remove_unused_material_slots.register()
    auto_render.register()
    panels.register()
    AutoRenameCar.register()
    ExportFbx.register()
    Voxelizer.register()
    AutolinkTexture.register()
    MoveOrigin.register()
    AutoBake.register()
    AutoBakeRemesh.register()
    Combin.register()
    RenameTool.register()
    RemoveObj.register()
    SelectTool.register()
    ExoprtObj.register()
    MaterialOperator.register()
    UVCleaner.register()
    UVformater.register()
    RenderFrame.register()
    BoneProcess.register()
    AutoRig_2.register()
    bpy.ops.object.refresh_json_list()

def unregister():
    update.unregister()
    operators.unregister()
    panels.unregister()
    auto_render.unregister()
    renderconfig.unregister()
    CorrectRotation.unregister()
    remove_unused_material_slots.unregister()
    AutoRenameCar.unregister()
    ExportFbx.unregister()
    Voxelizer.unregister()
    AutolinkTexture.unregister()
    MoveOrigin.unregister()
    AutoBake.unregister()
    AutoBakeRemesh.unregister()
    Combin.unregister()
    RenameTool.unregister()
    RemoveObj.unregister()
    SelectTool.unregister()
    ExoprtObj.unregister()
    MaterialOperator.unregister()
    UVCleaner.unregister()
    UVformater.unregister()
    RenderFrame.unregister()
    BoneProcess.unregister()
    AutoRig_2.unregister()




if __name__ == "__main__":
    register()