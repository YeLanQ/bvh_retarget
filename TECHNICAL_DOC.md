# BVH Retarget Blender Extension 技术文档

## 概述

BVH Retarget 是一个独立的 Blender 扩展，用于将 BVH 动捕数据重定向到任何 Blender 骨架。

## 架构设计

### 目录结构

```
bvh_retarget/
├── __init__.py          # 插件主入口，注册/注销逻辑
├── blender_manifest.toml # Blender 扩展配置文件
├── operators.py         # 操作符定义 (bpy.ops.bvh_retarget.*)
├── panels.py           # UI 面板 (N-Panel)
├── properties.py       # 属性定义 (PropertyGroup, Preferences)
├── retarget.py         # 核心重定向逻辑
└── ui_list.py          # 自定义 UIList
```

### 模块依赖关系

```
__init__.py
    ├── properties.py   (最先注册)
    ├── operators.py    (依赖 properties)
    ├── ui_list.py      (依赖 properties)
    └── panels.py       (依赖 operators, ui_list)
```

## 核心模块

### 1. properties.py

定义所有 Blender 属性：

```python
# 骨骼映射项
class BVHRETARGET_BoneMappingItem(PropertyGroup):
    source_bone: StringProperty()
    target_bone: StringProperty()
    enabled: BoolProperty()
    retarget_mode: EnumProperty()

# 场景级设置
class BVHRETARGET_SceneSettings(PropertyGroup):
    source_armature: PointerProperty()
    target_armature: PointerProperty()
    bone_mappings: CollectionProperty(type=BVHRETARGET_BoneMappingItem)
    retarget_root_bone: StringProperty()
    bake_start_frame: IntProperty()
    bake_end_frame: IntProperty()
    preset_name: StringProperty()

# 插件偏好
class BVHRETARGET_AddonPreferences(AddonPreferences):
    saved_presets: StringProperty()  # JSON 存储
```

### 2. retarget.py

核心重定向逻辑：

```python
# 骨骼名称自动匹配
def auto_build_mapping(source_arm, target_arm) -> list[tuple[str, str]]

# 应用重定向约束
def apply_retargeting_constraints(source_arm, target_arm, bone_pairs, root_bone)
    -> tuple[int, list[str]]

# 移除约束
def remove_retargeting_constraints(target_arm) -> int

# 烘焙动画
def bake_retargeted_animation(target_arm, frame_start, frame_end) -> bool

# 预设管理
def save_preset(prefs, preset_name, bone_pairs)
def load_preset(prefs, preset_name) -> list[dict] | None
def list_presets(prefs) -> list[str]
```

### 3. operators.py

操作符定义：

```python
# BVH 导入
class BVHRETARGET_OT_ImportBVH(Operator)
    bl_idname = "bvh_retarget.import_bvh"

# 骨骼映射
class BVHRETARGET_OT_AutoMapBones(Operator)
class BVHRETARGET_OT_AddBoneMapping(Operator)
class BVHRETARGET_OT_RemoveBoneMapping(Operator)

# 重定向
class BVHRETARGET_OT_ApplyRetargeting(Operator)
class BVHRETARGET_OT_RemoveRetargeting(Operator)
class BVHRETARGET_OT_BakeRetargeting(Operator)

# 预设
class BVHRETARGET_OT_SavePreset(Operator)
class BVHRETARGET_OT_LoadPreset(Operator)
class BVHRETARGET_OT_DeletePreset(Operator)
class BVHRETARGET_OT_ExportPresetFile(Operator)
class BVHRETARGET_OT_ImportPresetFile(Operator)
```

### 4. panels.py

UI 面板：

```python
class BVHRETARGET_PT_Import(Panel)     # 导入面板
class BVHRETARGET_PT_Retarget(Panel)   # 重定向面板
class BVHRETARGET_PT_Bake(Panel)       # 烘焙面板
class BVHRETARGET_PT_Presets(Panel)    # 预设面板
```

### 5. ui_list.py

自定义列表：

```python
class BVHRETARGET_UL_BoneMappings(UIList)
    bl_idname = "BVHRETARGET_UL_BoneMappings"
```

## 重定向模式

### 1. Copy Rotation

- 在世界空间中复制旋转
- 根骨骼额外复制位置
- 适用于相同休息姿势的骨架

### 2. Copy Transforms

- 在局部空间复制所有变换 (位置+旋转+缩放)
- 适用于骨骼长度不匹配的情况

### 3. Child Of

- 完整的父子关系约束
- 自动设置逆矩阵
- 适用于浮动骨骼或武器骨骼

### 4. Child Of Rotation

- 仅旋转的父子关系
- 不继承位置
- 适用于需要旋转跟踪的场景

## 注册机制

### 安全注册

```python
def _safe_register_class(cls):
    try:
        bpy.utils.register_class(cls)
    except ValueError:
        pass  # 已注册
```

### 注册顺序

```python
def register():
    properties.register()   # 1. 属性类
    operators.register()    # 2. 操作符
    ui_list.register()      # 3. UI 列表
    panels.register()       # 4. UI 面板
```

### 注销顺序

```python
def unregister():
    panels.unregister()     # 4. UI 面板
    ui_list.unregister()    # 3. UI 列表
    operators.unregister()  # 2. 操作符
    properties.unregister() # 1. 属性类
```

## BVH 导入兼容性

### Blender 5.0+ 支持

```python
def _ensure_bvh_importer() -> bool:
    # 检查 io_anim_bvh 是否注册
    # 如果没有，尝试启用它
    if _bvh_operator_registered():
        return True
    # 尝试启用插件
    for module_name in candidates:
        addon_utils.enable(module_name, default_set=True, persistent=True)
        if _bvh_operator_registered():
            return True
```

## 骨骼名称匹配

### 匹配策略

1. 精确匹配
2. 规范化匹配 (去除特殊字符，统一大小写)
3. 替代名称匹配 (Mixamo, SMPL 等)

### 规范化函数

```python
def _normalize(name: str) -> str:
    name = name.lower()
    if ":" in name:
        name = name.split(":")[-1]
    return re.sub(r"[^a-z0-9]", "", name)
```

## 预设系统

### 存储格式

```json
[
    {
        "src": "Hips",
        "tgt": "mixamorig:Hips",
        "en": true,
        "mode": "CHILD_OF"
    }
]
```

### 插件偏好存储

```python
class BVHRETARGET_AddonPreferences(AddonPreferences):
    saved_presets: StringProperty(default="{}")  # JSON 字符串
```

## 安装方式

### 方法一：Blender 扩展安装

1. `Edit > Preferences > Add-ons > Install from Disk`
2. 选择 `bvh_retarget` 目录
3. 启用扩展

### 方法二：手动复制

复制到 Blender 扩展目录：
- Windows: `%APPDATA%\Blender Foundation\Blender\<version>\extensions\`
- macOS: `~/Library/Application Support/Blender/<version>/extensions/`
- Linux: `~/.config/blender/<version>/extensions/`

## 故障排除

### 常见问题

1. **注册错误**: 确保完全禁用旧版本并重启 Blender
2. **图标不存在**: 检查图标名称是否有效
3. **BVH 导入失败**: 确保 `io_anim_bvh` 插件已启用

### 调试方法

```python
# 在 Blender Python 控制台中运行
import bpy
print(dir(bpy.types.BVHRETARGET_SceneSettings))
```

## 开发规范

### 命名约定

- 类名: `BVHRETARGET_OT_OperationName`
- 操作符 ID: `bvh_retarget.operation_name`
- 属性组: `BVHRETARGET_PropertyGroupName`

### 代码风格

- 使用类型注解
- 添加 docstring
- 错误处理使用 try/except
- 使用安全注册函数
