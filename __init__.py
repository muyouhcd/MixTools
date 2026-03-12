bl_info = {
    "name": "MixToolBox",
    "author": "MuyouHCD",
    "version": (4,8,69),
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
#依赖管理和自动安装系统

class DependencyManager:
    """依赖管理类 - 处理插件依赖的安装和验证"""
    
    def __init__(self):
        self.critical_deps = {
            'PIL': {
                'package_name': 'Pillow',
                'import_name': 'PIL',
                'required': True,
                'fallback_available': True  # PIL有降级处理
            }
        }
        self.dependency_status = {}
        self.installation_log = []
        # 调试选项：禁用联网安装
        self.disable_online_install = False  # 设置为False启用联网安装
    
    def set_online_install_enabled(self, enabled):
        """设置是否允许联网安装"""
        self.disable_online_install = not enabled
        status = "启用" if enabled else "禁用"
        print(f"🔧 联网安装已{status}")
        
    def get_addon_path(self):
        """获取插件路径"""
        file_path = os.path.normpath(os.path.dirname(__file__))
        while os.path.basename(file_path) != "addons" and os.path.dirname(file_path) != file_path:
            file_path = os.path.dirname(file_path)
        return file_path if os.path.basename(file_path) == "addons" else ''
    
    def verify_package_installation(self, package_file):
        """验证包是否成功安装"""
        package_name = os.path.basename(package_file).split('-')[0].lower()
        
        if package_name == 'pillow':
            try:
                import PIL
                from PIL import Image, ImageOps
                # 测试基本功能
                test_img = Image.new('RGB', (1, 1), color='red')
                test_img = ImageOps.expand(test_img, border=1, fill='blue')
                return True, f"Pillow {PIL.__version__} 验证成功"
            except ImportError as e:
                return False, f"Pillow导入失败: {e}"
            except Exception as e:
                return False, f"Pillow功能测试失败: {e}"
        
        return True, f"{package_name} 验证通过"
    
    def get_package_info(self, package_file):
        """解析包文件信息"""
        filename = os.path.basename(package_file)
        if filename.endswith('.whl'):
            # 解析wheel文件名: package-version-python-abi-platform.whl
            parts = filename[:-4].split('-')
            if len(parts) >= 2:
                package_name = parts[0].lower()
                version = parts[1]
                return package_name, version, 'wheel'
        elif filename.endswith('.tar.gz'):
            # 解析源码包文件名: package-version.tar.gz
            parts = filename[:-7].split('-')
            if len(parts) >= 2:
                package_name = parts[0].lower()
                version = parts[1]
                return package_name, version, 'source'
        return None, None, None

    def group_packages_by_name(self, package_files):
        """按包名分组，收集所有版本"""
        packages = {}
        for package_file in package_files:
            package_name, version, package_type = self.get_package_info(package_file)
            if package_name:
                if package_name not in packages:
                    packages[package_name] = []
                packages[package_name].append({
                    'file': package_file,
                    'version': version,
                    'type': package_type,
                    'filename': os.path.basename(package_file)
                })
        return packages

    def check_package_compatibility(self, package_file):
        """检查包文件兼容性"""
        filename = os.path.basename(package_file)
        
        if not filename.endswith('.whl'):
            return True, "源码包，跳过兼容性检查"
        
        # 解析wheel文件名
        parts = filename[:-4].split('-')
        if len(parts) < 4:
            return True, "无法解析wheel文件名"
        
        package_name, version, python_tag, abi_tag, platform_tag = parts[0], parts[1], parts[2], parts[3], parts[4]
        
        # 检查解释器类型兼容性
        current_python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
        
        # 检查是否为PyPy包（在CPython环境中不兼容）
        if python_tag.startswith('pp'):
            return False, f"解释器类型不兼容: 包为PyPy编译 (pp{python_tag[2:]}), 当前为CPython"
        
        # 检查Python版本兼容性（仅对CPython包）
        if python_tag.startswith('cp'):
            required_version = python_tag[2:]
            
            # 标准化版本格式进行比较
            def normalize_version(version_str):
                """标准化版本字符串，处理cp311 -> 3.11的转换"""
                if version_str.isdigit() and len(version_str) == 3:
                    # cp311 -> 3.11
                    return f"{version_str[0]}.{version_str[1:]}"
                return version_str
            
            normalized_required = normalize_version(required_version)
            normalized_current = normalize_version(current_python_version)
            
            if normalized_required != normalized_current:
                # 检查是否是主版本相同但次版本不同
                required_parts = normalized_required.split('.')
                current_parts = normalized_current.split('.')
                
                if len(required_parts) >= 2 and len(current_parts) >= 2:
                    required_major = required_parts[0]
                    current_major = current_parts[0]
                    
                    if required_major != current_major:
                        return False, f"Python主版本不兼容: 需要 {normalized_required}, 当前 {normalized_current}"
                    # 主版本相同，允许尝试安装
                else:
                    return False, f"Python版本格式不兼容: 需要 {normalized_required}, 当前 {normalized_current}"
        
        # 检查平台兼容性
        if platform_tag and 'win' in platform_tag:
            if not sys.platform.startswith('win'):
                return False, f"平台不兼容: 需要Windows, 当前 {sys.platform}"
        
        return True, "兼容性检查通过"

    def try_install_package(self, package_file, package_name, version):
        """尝试安装单个包文件"""
        try:
            # 先检查兼容性
            is_compatible, compat_msg = self.check_package_compatibility(package_file)
            if not is_compatible:
                return False, f"兼容性检查失败: {compat_msg}"
            
            # 使用兼容的安装命令
            cmd = [sys.executable, "-m", "pip", "install", package_file, 
                   "--force-reinstall", "--no-deps", "--no-cache-dir", "--ignore-requires-python"]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                # 验证安装
                is_valid, verify_msg = self.verify_package_installation(package_file)
                if is_valid:
                    print(f"✅ {package_name} {version} 安装成功")
                    return True, verify_msg
                else:
                    return False, f"验证失败: {verify_msg}"
            else:
                return False, result.stderr or "安装命令失败"
                
        except subprocess.TimeoutExpired:
            return False, "安装超时"
        except Exception as e:
            return False, f"安装异常: {e}"

    def try_online_install(self, package_name, critical_deps):
        """尝试联网安装包"""
        # 检查是否是关键依赖（支持多种名称映射）
        critical_package_names = ['PIL', 'pillow']
        is_critical = False
        online_package_name = package_name
        
        for dep_name, dep_info in critical_deps.items():
            if (package_name == dep_name or 
                package_name == dep_info.get('package_name', '').lower() or
                (package_name == 'pillow' and dep_name == 'PIL')):
                is_critical = True
                online_package_name = dep_info.get('package_name', package_name)
                break
        
        if not is_critical:
            return False, "不是关键依赖"
        
        print(f"🌐 从PyPI安装 {online_package_name}...")
        
        try:
            cmd = [sys.executable, "-m", "pip", "install", online_package_name, "--no-cache-dir"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                # 验证安装
                try:
                    if package_name == 'PIL':
                        import PIL
                        from PIL import Image, ImageOps
                        return True, f"联网安装成功 (版本: {PIL.__version__})"
                except ImportError:
                    pass
                return True, "联网安装成功"
            else:
                return False, f"联网安装失败: {result.stderr}"
                
        except subprocess.TimeoutExpired:
            return False, "联网安装超时"
        except Exception as e:
            return False, f"联网安装异常: {e}"

    def install_package_versions(self, package_name, versions, critical_deps):
        """尝试安装某个包的所有版本"""
        print(f"🔍 为 '{package_name}' 找到 {len(versions)} 个版本:")
        for v in versions:
            print(f"   - {v['filename']} (版本: {v['version']}, 类型: {v['type']})")
        
        # 智能排序：优先尝试兼容的wheel文件，然后源码包
        def sort_key(version_info):
            # 检查兼容性
            is_compatible, _ = self.check_package_compatibility(version_info['file'])
            # 文件类型：wheel优先于源码包
            is_wheel = version_info['type'] == 'wheel'
            # 版本号排序（新版本优先）
            version_tuple = self._version_to_tuple(version_info['version'])
            
            # 排序优先级：
            # 1. 兼容性（兼容的优先）
            # 2. 文件类型（wheel优先于源码包）
            # 3. 版本号（新版本优先）
            return (not is_compatible, not is_wheel, tuple(-x for x in version_tuple))
        
        versions.sort(key=sort_key)
        
        # 显示排序后的安装顺序（简化版）
        compatible_count = sum(1 for v in versions if self.check_package_compatibility(v['file'])[0])
        print(f"📋 找到 {len(versions)} 个版本，其中 {compatible_count} 个兼容")
        
        for version_info in versions:
            package_file = version_info['file']
            version = version_info['version']
            package_type = version_info['type']
            filename = version_info['filename']
            
            # 先检查是否已经安装
            if package_name == 'pillow':
                try:
                    import PIL
                    from PIL import Image, ImageOps
                    print(f"✅ {package_name} 已经安装并可用 (版本: {PIL.__version__})")
                    return True, f"已安装 {PIL.__version__}"
                except ImportError:
                    pass
            
            # 检查兼容性，跳过不兼容的wheel包
            is_compatible, compat_msg = self.check_package_compatibility(package_file)
            if not is_compatible and package_type == 'wheel':
                continue  # 静默跳过不兼容的wheel包
            
            print(f"📦 尝试安装 {filename}...")
            
            # 尝试安装当前版本
            success, message = self.try_install_package(package_file, package_name, version)
            if success:
                return True, message
            
            # 特殊处理源码包编译失败
            if package_type == 'source' and 'zlib' in message.lower():
                print(f"⚠️ 源码包编译失败（缺少zlib依赖）: {message}")
                print("💡 建议使用预编译的wheel包或联网安装")
            else:
                print(f"❌ {filename} 安装失败: {message}")
        
        # 所有本地版本都失败，检查是否允许联网安装
        if self.disable_online_install:
            print(f"🚫 联网安装已禁用，跳过联网安装 {package_name}")
            return False, "所有本地版本都失败，联网安装已禁用"
        else:
            print(f"🌐 所有本地版本都失败，尝试联网安装 {package_name}...")
            return self.try_online_install(package_name, critical_deps)
    
    def _version_to_tuple(self, version_str):
        """将版本字符串转换为元组用于排序"""
        try:
            return tuple(map(int, version_str.split('.')))
        except:
            return (0, 0, 0)

    def install_local_packages_with_verification(self, local_package_dir):
        """智能安装本地包并验证安装结果"""
        if not os.path.isdir(local_package_dir):
            error_msg = f"目录 '{local_package_dir}' 不存在"
            print(f"❌ {error_msg}")
            return False, error_msg

        package_files = glob.glob(os.path.join(local_package_dir, "*.whl")) + glob.glob(os.path.join(local_package_dir, "*.tar.gz"))
        if not package_files:
            error_msg = f"在目录 '{local_package_dir}' 中未找到任何可安装的文件"
            print(f"❌ {error_msg}")
            return False, error_msg

        print(f"🔍 发现 {len(package_files)} 个包文件")
        for pkg in package_files:
            print(f"   - {os.path.basename(pkg)}")
        
        # 按包名分组
        packages = self.group_packages_by_name(package_files)
        print(f"📦 识别到 {len(packages)} 个不同的包: {list(packages.keys())}")
        
        # 显示每个包的详细信息
        for package_name, versions in packages.items():
            print(f"   {package_name}: {len(versions)} 个版本")
        
        installation_results = []
        print("🔧 开始智能安装依赖包...")
        
        # 处理每个包
        for package_name, versions in packages.items():
            print(f"\n📦 处理包: {package_name}")
            success, message = self.install_package_versions(package_name, versions, self.critical_deps)
            installation_results.append((package_name, success, message))
            
            if success:
                print(f"✅ {package_name} 安装成功: {message}")
            else:
                print(f"❌ {package_name} 安装失败: {message}")
        
        # 记录安装结果
        self.installation_log = installation_results
        
        # 检查关键依赖安装结果
        failed_critical = []
        for package_name, success, message in installation_results:
            if not success and package_name in self.critical_deps and self.critical_deps[package_name]['required']:
                failed_critical.append(package_name)
        
        if failed_critical:
            error_msg = f"关键依赖安装失败: {', '.join(failed_critical)}"
            print(f"⚠️ {error_msg}")
            return False, error_msg
        
        success_count = len([r for r in installation_results if r[1]])
        print(f"\n🎉 依赖安装完成！成功安装 {success_count}/{len(installation_results)} 个包")
        return True, f"成功安装 {success_count} 个依赖包"
    
    def check_dependencies(self):
        """检查所有依赖的状态"""
        print("🔍 检查依赖状态...")
        for dep_name, dep_info in self.critical_deps.items():
            try:
                if dep_info['import_name']:
                    __import__(dep_info['import_name'])
                self.dependency_status[dep_name] = {
                    'available': True,
                    'error': None,
                    'version': self._get_package_version(dep_info['import_name'])
                }
                print(f"✅ {dep_name} 依赖可用")
            except ImportError as e:
                self.dependency_status[dep_name] = {
                    'available': False,
                    'error': str(e),
                    'version': None
                }
                print(f"❌ {dep_name} 依赖不可用: {e}")
    
    def _get_package_version(self, import_name):
        """获取包版本"""
        try:
            if import_name == 'PIL':
                import PIL
                return PIL.__version__
        except:
            pass
        return "未知"
    
    def get_missing_critical_deps(self):
        """获取缺失的关键依赖"""
        missing = []
        for dep_name, status in self.dependency_status.items():
            if not status['available'] and self.critical_deps[dep_name]['required']:
                missing.append(dep_name)
        return missing
    
    def can_plugin_load_safely(self):
        """检查插件是否可以安全加载"""
        missing_deps = self.get_missing_critical_deps()
        return len(missing_deps) == 0, missing_deps
    
    def get_dependency_status_summary(self):
        """获取依赖状态摘要"""
        total_deps = len(self.critical_deps)
        available_deps = len([s for s in self.dependency_status.values() if s['available']])
        missing_deps = self.get_missing_critical_deps()
        
        return {
            'total': total_deps,
            'available': available_deps,
            'missing': len(missing_deps),
            'missing_list': missing_deps,
            'can_load_safely': len(missing_deps) == 0
        }

# 全局依赖管理器
dependency_manager = DependencyManager()

def safe_plugin_initialization():
    """安全的插件初始化流程"""
    print("MixTools: 初始化...")

    # 检查依赖状态
    dependency_manager.check_dependencies()

    # 如果依赖不可用，尝试安装
    can_load, missing_deps = dependency_manager.can_plugin_load_safely()

    if not can_load:
        print(f"MixTools: 缺失依赖: {missing_deps}, 尝试安装...")

        local_addon_path = dependency_manager.get_addon_path()

        if local_addon_path:
            local_package_dir = os.path.join(local_addon_path, "MixTools", "package")

            if os.path.exists(local_package_dir):
                install_success, install_message = dependency_manager.install_local_packages_with_verification(local_package_dir)

                if install_success:
                    dependency_manager.check_dependencies()
                    can_load, missing_deps = dependency_manager.can_plugin_load_safely()
                else:
                    print(f"MixTools: 依赖安装失败: {install_message}")
            else:
                print(f"MixTools: 包目录不存在: {local_package_dir}")
        else:
            print("MixTools: 无法确定插件路径，跳过依赖安装")

    # 最终检查
    if not can_load:
        print(f"MixTools: 缺少关键依赖: {missing_deps}")
        print("  解决方案: python.exe -m pip install pillow")
        return False  # 返回False表示不是完整模式，但仍会继续注册
    else:
        print("MixTools: 所有依赖可用")
        return True

# 延迟执行插件初始化，避免在导入时触发依赖检查
plugin_initialization_success = None
#------------------------------------------------------------------------------------------

from . import utils
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
from . import AnimationJsonImporter
from . import AnimationAnimImporter
from . import RoleReplacer
from . import Importer
from . import BetterFbxOperation
from . import BetterFbxExport
from . import AutoHideClean
from . import BoneConverter
from . import AssetMarker
from . import EmptySizeSetter
from . import CompositorNodeLibrary
from . import CurveOperators
from . import Random
from . import MeshEditer

def register():
    """插件注册函数 - 支持降级模式"""
    # 在注册时执行依赖检查和初始化
    global plugin_initialization_success
    if plugin_initialization_success is None:
        plugin_initialization_success = safe_plugin_initialization()

    # 检查依赖状态，决定注册模式
    can_load_safely, missing_deps = dependency_manager.can_plugin_load_safely()

    if not can_load_safely:
        print(f"MixTools: 以受限模式注册 (缺失: {missing_deps})")
        register_limited_mode()
    else:
        print("MixTools: 以完整模式注册")
        register_full_mode()

def register_full_mode():
    """完整模式注册 - 所有功能可用"""
    try:
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
        AnimationJsonImporter.register()
        AnimationAnimImporter.register()
        RoleReplacer.register()
        Importer.register()
        BetterFbxOperation.register()
        BetterFbxExport.register()
        AutoHideClean.register()
        BoneConverter.register()
        AssetMarker.register()
        EmptySizeSetter.register()
        CompositorNodeLibrary.register()
        CurveOperators.register()
        Random.register()
        MeshEditer.register()
        
        # 最后注册UI面板
        panels.register()
        
        print_dependency_status()
        print("MixTools: 完整模式注册成功")

    except Exception as e:
        print(f"MixTools: 完整模式注册失败: {e}, 降级到受限模式")
        register_limited_mode()

def register_limited_mode():
    """受限模式注册 - 缺少关键依赖时的降级版本"""
    try:
        # 先注销可能已注册的类，避免重复注册
        try:
            update.unregister()
            operators.unregister()
        except Exception:
            pass
        
        # 注册基础模块（不依赖PIL）
        try:
            update.register()
            operators.register()
        except Exception as e:
            print(f"MixTools: 基础模块注册失败: {e}")
            # 继续尝试注册其他模块
        
        # 注册不依赖PIL的功能模块（安全注册）
        safe_modules = [
            (AutoBake, "AutoBake"),
            (AutoBakeRemesh, "AutoBakeRemesh"),
            (AutoRig, "AutoRig"),
            (AutolinkTexture, "AutolinkTexture"),
            (Combin, "Combin"),
            (CorrectRotation, "CorrectRotation"),
            (Exporter, "Exporter"),
            (LightOperator, "LightOperator"),
            (MaterialOperator, "MaterialOperator"),
            (MoveOrigin, "MoveOrigin"),
            (RenameTool, "RenameTool"),
            (renderconfig, "renderconfig"),
            (SelectTool, "SelectTool"),
            (Cleaner, "Cleaner"),
            (UVformater, "UVformater"),
            (Voxelizer, "Voxelizer"),
            (animationoperater, "animationoperater"),
            (AnimationJsonImporter, "AnimationJsonImporter"),
            (AnimationAnimImporter, "AnimationAnimImporter"),
            (RoleReplacer, "RoleReplacer"),
            (Importer, "Importer"),
            (BetterFbxOperation, "BetterFbxOperation"),
            (BetterFbxExport, "BetterFbxExport"),
            (AutoHideClean, "AutoHideClean"),
            (BoneConverter, "BoneConverter"),
            (AssetMarker, "AssetMarker"),
            (EmptySizeSetter, "EmptySizeSetter"),
            (CompositorNodeLibrary, "CompositorNodeLibrary"),
            (CurveOperators, "CurveOperators"),
            (Random, "Random"),
            (MeshEditer, "MeshEditer")
        ]
        
        # 尝试注册AutoRender模块（即使PIL不可用，也要注册UI属性）
        try:
            AutoRender.register()
        except Exception as e:
            print(f"MixTools: AutoRender 注册失败: {e}")

        for module, name in safe_modules:
            try:
                module.register()
            except Exception as e:
                print(f"MixTools: {name} 注册失败: {e}")
        
        # 注册受限版本的UI面板
        panels.register()
        
        print_dependency_status()
        print("MixTools: 受限模式注册成功 (如需完整功能: pip install pillow)")

    except Exception as e:
        print(f"MixTools: 受限模式注册失败: {e}")

def print_dependency_status():
    """打印依赖状态到控制台"""
    status = dependency_manager.get_dependency_status_summary()
    if status['missing'] > 0:
        print(f"MixTools: 依赖 {status['available']}/{status['total']} 可用, 缺失: {', '.join(status['missing_list'])}")
    else:
        print(f"MixTools: 依赖 {status['available']}/{status['total']} 全部可用")

def unregister():
    """插件注销函数"""
    
    try:
        # 先注销UI面板
        panels.unregister()
        
        # 注销功能模块
        RoleReplacer.unregister()
        AnimationAnimImporter.unregister()
        AnimationJsonImporter.unregister()
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
        BetterFbxExport.unregister()
        AutoHideClean.unregister()
        BoneConverter.unregister()
        AssetMarker.unregister()
        EmptySizeSetter.unregister()
        CompositorNodeLibrary.unregister()
        CurveOperators.unregister()
        Random.unregister()
        MeshEditer.unregister()
        
        # 最后注销基础模块
        operators.unregister()
        update.unregister()
        
    except Exception as e:
        print(f"MixTools: 注销错误: {e}")

if __name__ == "__main__":
    register()