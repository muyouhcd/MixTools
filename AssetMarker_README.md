# AssetMarker.py 模块文档

## 概述
`AssetMarker.py` 是一个专门用于批量标记资产的 Blender 插件模块。该模块提供了 `CreateAssemblyAsset` 操作符，可以自动为集合中的顶级物体创建资产标记。

## 主要功能

### 批量标记资产 (CreateAssemblyAsset)
- **功能描述**: 自动为选定集合中的顶级物体创建资产标记
- **递归处理**: 支持递归处理子集合中的物体
- **依赖要求**: 需要安装并启用 Machin3tools 插件
- **操作符ID**: `object.mian_create_assembly_asset`

## 特性

### 核心功能
1. **场景状态管理**: 自动保存和恢复场景的可见性、选择状态和视图设置
2. **递归集合处理**: 自动处理选定集合及其所有子集合中的物体
3. **顶级物体识别**: 只处理没有父级的顶级物体
4. **空物体父级创建**: 可选择为每个资产创建顶级父物体
5. **视图优化**: 自动调整视图以更好地预览资产
6. **错误处理**: 完善的错误处理和用户反馈机制

### 递归处理特性
- **子集合遍历**: 自动遍历选定集合的所有子集合
- **深度优先**: 采用深度优先算法处理嵌套集合结构
- **去重处理**: 避免重复处理同一物体
- **状态保持**: 在处理过程中保持场景状态的一致性

## 使用方法

### 基本使用
1. 在 Blender 中安装并启用 Machin3tools 插件
2. 选择要处理的集合
3. 设置相关参数（如是否创建顶级父物体）
4. 执行批量标记操作

### 参数设置
- **创建顶级父物体**: 控制是否为每个资产创建空物体作为顶级父级
- **集合选择**: 选择要处理的集合（包含其子集合）

## 技术实现

### 主要类和方法

#### CreateAssemblyAsset 类
```python
class CreateAssemblyAsset(bpy.types.Operator):
    bl_idname = "object.mian_create_assembly_asset"
    bl_label = "批量标记资产（需要m3插件）"
    bl_options = {'REGISTER', 'UNDO'}
```

#### 核心方法
1. **get_all_objects_recursive()**: 递归获取集合及其子集合中的所有物体
2. **process_single_object()**: 处理单个物体的资产标记
3. **save_scene_state()**: 保存当前场景状态
4. **restore_scene_state()**: 恢复场景状态
5. **setup_view_for_preview()**: 设置预览视图
6. **create_empty_parent()**: 创建空物体父级

### 场景属性
- `bpy.types.Scene.create_top_level_parent`: 控制是否创建顶级父物体
- `bpy.types.Scene.asset_collection`: 选择要处理的集合

## 依赖关系

### 必需插件
- **Machin3tools**: 提供核心的资产创建功能
  - 操作符: `bpy.ops.machin3.create_assembly_asset`

### 内部依赖
- `bpy`: Blender Python API
- `time`: 时间控制
- `mathutils.Vector`: 数学计算

## 错误处理

### 常见错误
1. **Machin3tools 未安装**: 提示用户安装并启用插件
2. **集合未选择**: 提示用户选择有效集合
3. **3D 视口未找到**: 提示用户确保有可用的 3D 视口
4. **没有顶级物体**: 提示用户检查集合结构

### 错误恢复
- 自动保存和恢复场景状态
- 详细的错误信息报告
- 用户可取消操作

## 性能优化

### 内存管理
- 定期垃圾回收
- 及时释放不需要的对象引用

### 视图更新
- 使用 `bpy.ops.wm.redraw_timer()` 优化重绘
- 适当的延时控制处理速度

## 使用示例

```python
# 在 Blender 中执行
import bpy

# 设置参数
bpy.context.scene.create_top_level_parent = True
bpy.context.scene.asset_collection = bpy.data.collections["MyCollection"]

# 执行批量标记
bpy.ops.object.mian_create_assembly_asset()
```

## 注意事项

1. **插件依赖**: 必须安装 Machin3tools 插件
2. **集合结构**: 确保集合中有有效的顶级物体
3. **性能考虑**: 大量物体处理时可能需要较长时间
4. **场景状态**: 操作过程中会临时改变场景状态，操作完成后会恢复

## 更新日志

### 最新版本
- 添加递归子集合处理功能
- 优化错误处理和用户反馈
- 改进文档和注释

### 历史版本
- 初始版本：基本的批量标记功能
- 添加场景状态管理
- 添加视图优化功能 