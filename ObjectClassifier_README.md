# 物体分类功能说明

## 功能概述

这个新功能可以根据物体名称中的关键字自动将物体分类并放置到不同的集合中。

## 命名规则

物体名称需要按照以下格式命名，各部分用下划线（_）分隔：

```
[性别]_[部位]_[套装标识]
```

### 关键字说明

#### 性别关键字
- `male` - 男性
- `female` - 女性

#### 部位关键词
- `upper` - 上身
- `lower` - 下身
- `feet` - 脚部
- `mouth` - 嘴部
- `top` - 顶部
- `bottom` - 底部
- `hair` - 头发
- `nose` - 鼻子
- `eyes` - 眼睛

#### 套装关键词
- `sets` - 表示是套装（可选）

## 命名示例

### 有效命名示例
- `male_upper_sets` - 男性上身套装
- `female_lower_sets` - 女性下身套装
- `male_feet` - 男性脚部（非套装）
- `female_hair_sets` - 女性头发套装
- `male_eyes` - 男性眼睛（非套装）

### 无效命名示例
- `upper_male_sets` - 性别应该在第一位
- `male_upper` - 缺少部位信息
- `male_sets` - 缺少部位信息

## 集合结构

功能会自动创建以下集合层级结构：

```
Object_Classification/
├── Male/
│   ├── Male_Upper/
│   ├── Male_Lower/
│   ├── Male_Feet/
│   ├── Male_Mouth/
│   ├── Male_Top/
│   ├── Male_Bottom/
│   ├── Male_Hair/
│   ├── Male_Nose/
│   └── Male_Eyes/
└── Female/
    ├── Female_Upper/
    ├── Female_Lower/
    ├── Female_Feet/
    ├── Female_Mouth/
    ├── Female_Top/
    ├── Female_Bottom/
    ├── Female_Hair/
    ├── Female_Nose/
    └── Female_Eyes/
```

## 使用方法

1. 在Blender中选择需要分类的物体
2. 确保物体名称符合命名规则
3. 在工具箱面板中找到"动画处理工具"部分
4. 展开"角色部件替换"工具组
5. 点击"按名称分类物体"按钮

## 功能特点

- **自动创建集合**：如果目标集合不存在，会自动创建
- **智能分类**：根据物体名称中的关键字自动分类
- **保持原有数据**：只移动物体到新集合，不修改物体数据
- **错误处理**：对于无法分类的物体会给出提示信息
- **支持撤销**：操作支持撤销功能

## 注意事项

1. 只有网格类型的物体会被分类
2. 物体名称必须包含性别和部位信息才能被分类
3. 如果物体名称不符合规则，会被标记为"无法分类"
4. 套装标识（sets）是可选的，不影响分类结果

## 测试

可以使用提供的测试脚本 `test_classifier.py` 来测试功能：

1. 在Blender中打开文本编辑器
2. 加载 `test_classifier.py` 文件
3. 运行脚本创建测试物体
4. 执行分类操作验证功能 