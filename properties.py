"""
BVH Retarget — Properties
All bpy.props definitions: addon preferences, scene-level settings, bone mapping.
"""

import bpy
from bpy.props import (
    StringProperty, FloatProperty, IntProperty, BoolProperty,
    EnumProperty, CollectionProperty, PointerProperty,
)
from bpy.types import PropertyGroup, AddonPreferences


# ---------------------------------------------------------------------------
# Bone mapping item (one row in the UIList)
# ---------------------------------------------------------------------------

class BVHRETARGET_BoneMappingItem(PropertyGroup):
    """A single source -> target bone pair for retargeting."""
    source_bone: StringProperty(
        name="Source Bone",
        description="Bone name in the source armature (imported from BVH)",
        default="",
    )
    target_bone: StringProperty(
        name="Target Bone",
        description="Bone name in your target armature",
        default="",
    )
    enabled: BoolProperty(
        name="Enabled",
        description="Include this bone in retargeting",
        default=True,
    )
    retarget_mode: EnumProperty(
        name="Mode",
        description="How this bone pair is driven",
        items=[
            ("COPY_ROTATION", "Copy Rotation", "Copy rotation in local space; root bone also gets Copy Location in world space"),
            ("COPY_TRANSFORMS", "Copy Transforms", "Copy location + rotation + scale together in local space"),
            ("CHILD_OF", "Child Of", "Child Of constraint with automatic inverse matrix; preserves rest-pose offset"),
            ("CHILD_OF_ROTATION", "Child Of (Rotation)", "Child Of constraint with only rotation enabled"),
        ],
        default="COPY_ROTATION",
    )


# ---------------------------------------------------------------------------
# Scene-level settings
# ---------------------------------------------------------------------------

class BVHRETARGET_SceneSettings(PropertyGroup):
    """Stored on bpy.context.scene.bvh_retarget — all per-scene settings."""

    # --- Armature selection ---
    source_armature: PointerProperty(
        name="Source Armature",
        description="The armature imported from BVH (source of motion)",
        type=bpy.types.Object,
        poll=lambda self, obj: obj.type == 'ARMATURE',
    )
    target_armature: PointerProperty(
        name="Target Armature",
        description="Your character's armature to drive with the motion",
        type=bpy.types.Object,
        poll=lambda self, obj: obj.type == 'ARMATURE',
    )

    # --- Bone mapping ---
    bone_mappings: CollectionProperty(type=BVHRETARGET_BoneMappingItem)
    bone_mapping_index: IntProperty(default=0)

    # --- Root bone ---
    retarget_root_bone: StringProperty(
        name="Root Bone (Target)",
        description="Root / hip bone on the target armature (gets position + rotation)",
        default="",
    )

    # --- BVH Import Settings ---
    bvh_scale: FloatProperty(
        name="BVH Scale",
        description="Scale factor for imported BVH (0.01 = cm to meters, 0.1 = mm to meters, 1.0 = meters)",
        default=0.01,
        min=0.001,
        max=100.0,
    )

    # --- Bake settings ---
    bake_start_frame: IntProperty(name="Start Frame", default=1, min=0)
    bake_end_frame: IntProperty(name="End Frame", default=250, min=1)

    # --- Preset name ---
    preset_name: StringProperty(
        name="Preset Name",
        description="Name to save / load bone mapping preset",
        default="default",
    )


# ---------------------------------------------------------------------------
# Addon preferences
# ---------------------------------------------------------------------------

class BVHRETARGET_AddonPreferences(AddonPreferences):
    bl_idname = __package__

    saved_presets: StringProperty(
        name="Saved Presets",
        description="JSON blob of all saved bone-mapping presets",
        default="{}",
    )


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

_classes = [
    BVHRETARGET_BoneMappingItem,
    BVHRETARGET_SceneSettings,
    BVHRETARGET_AddonPreferences,
]


def _safe_register_class(cls):
    """Register a class only if not already registered."""
    try:
        bpy.utils.register_class(cls)
    except ValueError:
        pass  # already registered


def _safe_unregister_class(cls):
    """Unregister a class only if registered."""
    try:
        bpy.utils.unregister_class(cls)
    except RuntimeError:
        pass  # not registered


def register():
    for cls in _classes:
        _safe_register_class(cls)
    bpy.types.Scene.bvh_retarget = PointerProperty(type=BVHRETARGET_SceneSettings)


def unregister():
    del bpy.types.Scene.bvh_retarget
    for cls in reversed(_classes):
        _safe_unregister_class(cls)
