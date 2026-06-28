# BVH Retarget Blender Extension

一个独立的Blender扩展，用于将BVH动捕数据重定向到任何Blender骨架。

## 功能特性

- **导入BVH文件**：自动创建骨架对象
- **自动骨骼匹配**：智能匹配源骨架和目标骨架的骨骼名称
- **多种重定向模式**：
  - Copy Rotation：仅复制旋转（根骨骼还包括位置）
  - Copy Transforms：复制位置+旋转+缩放
  - Child Of：完整的父子关系约束
  - Child Of (Rotation)：仅旋转的父子关系
- **一键烘焙动画**：将约束驱动的动画转换为关键帧
- **预设管理**：保存/加载骨骼映射预设
- **JSON导入/导出**：支持骨骼映射的文件交换

## 安装方法

### 方法一：作为Blender扩展安装
1. 打开Blender
2. 进入 Edit > Preferences > Add-ons
3. 点击 "Install from Disk"
4. 选择 `extra/bvh_retarget` 目录
5. 启用 "BVH Retarget" 扩展

### 方法二：手动复制
1. 将 `extra/bvh_retarget` 目录复制到Blender的扩展目录：
   - Windows: `%APPDATA%\Blender Foundation\Blender\4.2\extensions\`
   - macOS: `~/Library/Application Support/Blender/4.2/extensions/`
   - Linux: `~/.config/blender/4.2/extensions/`
2. 重启Blender
3. 在Edit > Preferences > Add-ons中启用

## 使用方法

### 基本工作流程

1. **导入BVH文件**
   - 点击 "Import BVH File" 按钮
   - 选择要导入的BVH文件
   - 源骨架会自动创建并设置

2. **设置目标骨架**
   - 在 "Retarget" 面板中，选择你的目标骨架
   - 可选：指定根骨骼名称

3. **自动匹配骨骼**
   - 点击 "Auto-Match Bones" 按钮
   - 系统会自动匹配常见的骨骼名称
   - 你可以手动调整匹配结果

4. **应用约束**
   - 点击 "Apply Constraints" 按钮
   - 目标骨架现在会跟随源骨架运动

5. **烘焙动画**
   - 设置烘焙的帧范围
   - 点击 "Bake & Remove Constraints" 按钮
   - 约束会被移除，动画转换为关键帧

### 高级功能

#### 手动骨骼映射
- 点击 "+" 按钮添加新的骨骼映射
- 选择源骨骼和目标骨骼
- 选择重定向模式

#### 预设管理
- 保存当前的骨骼映射为预设
- 加载之前保存的预设
- 导出/导入预设为JSON文件

#### 重定向模式说明

1. **Copy Rotation**
   - 在世界空间中复制旋转
   - 根骨骼还会复制位置
   - 适用于与源骨架相同休息姿势的骨架

2. **Copy Transforms**
   - 在局部空间中复制所有变换
   - 当目标骨骼长度与源骨骼不匹配时使用

3. **Child Of**
   - 完整的父子关系约束
   - 适用于浮动骨骼或武器骨骼

4. **Child Of (Rotation)**
   - 仅旋转的父子关系
   - 不继承位置，仅跟踪旋转

## 文件结构

```
extra/bvh_retarget/
├── __init__.py          # 插件主入口
├── blender_manifest.toml # Blender扩展配置
├── operators.py         # 操作符定义
├── panels.py           # UI面板
├── properties.py       # 属性定义
├── retarget.py         # 核心重定向逻辑
└── ui_list.py          # UI列表
```

## 兼容性

- Blender 4.2.0 或更高版本
- 支持所有标准BVH文件格式
- 兼容常见的骨骼命名约定（Mixamo、SMPL等）

## 许可证

GPL-3.0-or-later

## 致谢

基于 Kimodo Blender Bridge 项目的重定向功能开发。
