"""
BVH Retarget
============
Retarget BVH motion capture data to any Blender armature.

Features:
  - Import BVH files with automatic armature creation
  - Auto-match bone names between source and target armatures
  - Multiple retargeting modes (Copy Rotation, Copy Transforms, Child Of)
  - One-click bake animation to keyframes
  - Save/load bone mapping presets
  - Export/import bone maps as JSON files

Requirements:
  - Blender 4.2+
"""

bl_info = {
    "name": "BVH Retarget",
    "author": "YeLanQ",
    "version": (1, 0, 2),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar (N-Panel) > BVH Retarget",
    "description": "Retarget BVH motion capture data to any Blender armature",
    "category": "Animation",
}

import bpy

from . import properties, operators, ui_list, panels


def register():
    properties.register()
    operators.register()
    ui_list.register()
    panels.register()


def unregister():
    panels.unregister()
    ui_list.unregister()
    operators.unregister()
    properties.unregister()
