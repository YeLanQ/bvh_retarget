"""
BVH Retarget — Operators
All bpy.ops.bvh_retarget.* operators.
"""

import bpy
import os
import json
from bpy.types import Operator
from bpy.props import StringProperty, BoolProperty, IntProperty

from . import retarget as rt


# ---------------------------------------------------------------------------
# BVH importer compatibility (Blender 5.0+)
# ---------------------------------------------------------------------------

def _bvh_operator_registered() -> bool:
    """True only when import_anim.bvh is actually registered."""
    return hasattr(bpy.types, "IMPORT_ANIM_OT_bvh")


def _ensure_bvh_importer() -> bool:
    """Make sure bpy.ops.import_anim.bvh is registered, enabling it if needed."""
    if _bvh_operator_registered():
        return True

    import addon_utils
    candidates = ["io_anim_bvh"]
    try:
        candidates += [
            m.__name__ for m in addon_utils.modules()
            if m.__name__ != "io_anim_bvh" and m.__name__.endswith("io_anim_bvh")
        ]
    except Exception:
        pass

    for module_name in candidates:
        try:
            addon_utils.enable(module_name, default_set=True, persistent=True)
        except Exception:
            continue
        if _bvh_operator_registered():
            return True

    return _bvh_operator_registered()


def _import_bvh(**kwargs):
    """Import a BVH file, self-healing a missing/disabled importer add-on."""
    if not _ensure_bvh_importer():
        raise RuntimeError(
            "Blender's BVH importer is not available. Enable "
            "'Import-Export: BioVision Motion Capture (BVH)' under "
            "Edit > Preferences > Add-ons (search 'BVH'). On Blender 5.0+ you "
            "may need to install it from Get Extensions first."
        )
    try:
        return bpy.ops.import_anim.bvh(**kwargs)
    except (AttributeError, RuntimeError) as e:
        raise RuntimeError(f"BVH import failed: {e}")


# ---------------------------------------------------------------------------
# Import operator
# ---------------------------------------------------------------------------

class BVHRETARGET_OT_ImportBVH(Operator):
    """Import a BVH file and set it as the source armature"""
    bl_idname = "bvh_retarget.import_bvh"
    bl_label = "Import BVH"

    filepath: StringProperty(subtype='FILE_PATH')

    def execute(self, context):
        s = context.scene.bvh_retarget
        path = self.filepath

        if not path or not os.path.exists(path):
            self.report({'ERROR'}, f"File not found: {path}")
            return {'CANCELLED'}

        # Remember which objects exist before import
        before = set(bpy.context.scene.objects)

        try:
            _import_bvh(
                filepath=path,
                axis_forward='-Z',
                axis_up='Y',
                target='ARMATURE',
                global_scale=s.bvh_scale,   # Use configurable scale factor
                frame_start=1,
                use_fps_scale=False,
                update_scene_fps=False,
                update_scene_duration=True,
                use_cyclic=False,
                rotate_mode='NATIVE',
            )
        except RuntimeError as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

        # Find newly added armature
        after = set(bpy.context.scene.objects)
        new_objs = after - before
        new_arm = next((o for o in new_objs if o.type == 'ARMATURE'), None)

        if new_arm:
            new_arm.name = "BVH_Source"
            s.source_armature = new_arm
            self.report({'INFO'}, f"Imported '{new_arm.name}' with {len(new_arm.data.bones)} bones")
        else:
            self.report({'WARNING'}, "BVH imported but no armature found in scene.")

        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


# ---------------------------------------------------------------------------
# Bone mapping operators
# ---------------------------------------------------------------------------

class BVHRETARGET_OT_AutoMapBones(Operator):
    """Auto-match bone names between source and target armature"""
    bl_idname = "bvh_retarget.auto_map_bones"
    bl_label = "Auto-Match Bones"

    def execute(self, context):
        s = context.scene.bvh_retarget
        if not s.source_armature:
            self.report({'ERROR'}, "Set the Source Armature first.")
            return {'CANCELLED'}
        if not s.target_armature:
            self.report({'ERROR'}, "Set the Target Armature first.")
            return {'CANCELLED'}

        pairs = rt.auto_build_mapping(s.source_armature, s.target_armature)
        s.bone_mappings.clear()

        for src, tgt in pairs:
            item = s.bone_mappings.add()
            item.source_bone = src
            item.target_bone = tgt
            item.enabled = True

        self.report({'INFO'}, f"Auto-matched {len(pairs)} bone pairs")
        return {'FINISHED'}


class BVHRETARGET_OT_AddBoneMapping(Operator):
    """Add a new empty bone mapping row"""
    bl_idname = "bvh_retarget.add_bone_mapping"
    bl_label = "Add Bone Pair"

    def execute(self, context):
        s = context.scene.bvh_retarget
        item = s.bone_mappings.add()
        item.source_bone = ""
        item.target_bone = ""
        item.enabled = True
        s.bone_mapping_index = len(s.bone_mappings) - 1
        return {'FINISHED'}


class BVHRETARGET_OT_RemoveBoneMapping(Operator):
    """Remove the selected bone mapping row"""
    bl_idname = "bvh_retarget.remove_bone_mapping"
    bl_label = "Remove Bone Pair"

    def execute(self, context):
        s = context.scene.bvh_retarget
        idx = s.bone_mapping_index
        if 0 <= idx < len(s.bone_mappings):
            s.bone_mappings.remove(idx)
            s.bone_mapping_index = max(0, idx - 1)
        return {'FINISHED'}


# ---------------------------------------------------------------------------
# Retargeting operators
# ---------------------------------------------------------------------------

class BVHRETARGET_OT_ApplyRetargeting(Operator):
    """Apply constraints to drive target rig from source motion"""
    bl_idname = "bvh_retarget.apply_retargeting"
    bl_label = "Apply Constraints"

    def execute(self, context):
        s = context.scene.bvh_retarget
        if not s.source_armature:
            self.report({'ERROR'}, "Set Source Armature.")
            return {'CANCELLED'}
        if not s.target_armature:
            self.report({'ERROR'}, "Set Target Armature.")
            return {'CANCELLED'}
        if not s.bone_mappings:
            self.report({'ERROR'}, "No bone mappings defined. Use Auto-Match or add manually.")
            return {'CANCELLED'}

        pairs = [(item.source_bone, item.target_bone, item.enabled,
                  item.retarget_mode)
                 for item in s.bone_mappings]

        n, warnings = rt.apply_retargeting_constraints(
            s.source_armature, s.target_armature, pairs, s.retarget_root_bone
        )

        for w in warnings:
            self.report({'WARNING'}, w)

        self.report({'INFO'}, f"Applied retargeting constraints to {n} bones")
        return {'FINISHED'}


class BVHRETARGET_OT_RemoveRetargeting(Operator):
    """Remove all retargeting constraints from target armature"""
    bl_idname = "bvh_retarget.remove_retargeting"
    bl_label = "Remove Constraints"

    def execute(self, context):
        s = context.scene.bvh_retarget
        if not s.target_armature:
            self.report({'ERROR'}, "Set Target Armature.")
            return {'CANCELLED'}
        n = rt.remove_retargeting_constraints(s.target_armature)
        self.report({'INFO'}, f"Removed {n} retargeting constraints")
        return {'FINISHED'}


class BVHRETARGET_OT_RemoveSingleRetargeting(Operator):
    """Remove retargeting constraints from the selected bone mapping's target bone"""
    bl_idname = "bvh_retarget.remove_single_retargeting"
    bl_label = "Remove Single"

    bone_name: StringProperty(
        name="Target Bone",
        description="Remove constraints from this target bone",
        default="",
    )

    def execute(self, context):
        s = context.scene.bvh_retarget
        if not s.target_armature:
            self.report({'ERROR'}, "Set Target Armature.")
            return {'CANCELLED'}
        bone = self.bone_name.strip()
        if not bone:
            self.report({'WARNING'}, "No target bone specified.")
            return {'CANCELLED'}
        if bone not in s.target_armature.data.bones:
            self.report({'WARNING'}, f"Bone '{bone}' not found in target armature.")
            return {'CANCELLED'}
        n = rt.remove_retargeting_constraints_for_bone(s.target_armature, bone)
        if n:
            self.report({'INFO'}, f"Removed {n} constraint(s) from '{bone}'")
        else:
            self.report({'INFO'}, f"No retargeting constraints on '{bone}'")
        return {'FINISHED'}


class BVHRETARGET_OT_BakeRetargeting(Operator):
    """Bake the retargeted animation into keyframes and remove constraints"""
    bl_idname = "bvh_retarget.bake_retargeting"
    bl_label = "Bake Animation"

    def execute(self, context):
        s = context.scene.bvh_retarget
        if not s.target_armature:
            self.report({'ERROR'}, "Set Target Armature.")
            return {'CANCELLED'}

        success = rt.bake_retargeted_animation(
            s.target_armature,
            s.bake_start_frame,
            s.bake_end_frame,
        )
        if success:
            self.report({'INFO'}, "Animation baked successfully")
        else:
            self.report({'ERROR'}, "Bake failed — check console for details")
        return {'FINISHED'} if success else {'CANCELLED'}


# ---------------------------------------------------------------------------
# Preset operators
# ---------------------------------------------------------------------------

class BVHRETARGET_OT_SavePreset(Operator):
    """Save current bone mapping as a named preset"""
    bl_idname = "bvh_retarget.save_preset"
    bl_label = "Save Preset"

    def execute(self, context):
        s = context.scene.bvh_retarget
        prefs = context.preferences.addons[__package__].preferences
        name = s.preset_name.strip()
        if not name:
            self.report({'ERROR'}, "Enter a preset name first.")
            return {'CANCELLED'}

        pairs = [{"src": item.source_bone, "tgt": item.target_bone,
                  "en": item.enabled, "mode": item.retarget_mode}
                 for item in s.bone_mappings]
        rt.save_preset(prefs, name, pairs)
        self.report({'INFO'}, f"Preset '{name}' saved ({len(pairs)} bone pairs)")
        return {'FINISHED'}


class BVHRETARGET_OT_LoadPreset(Operator):
    """Load a saved bone mapping preset"""
    bl_idname = "bvh_retarget.load_preset"
    bl_label = "Load Preset"

    preset_name: StringProperty()

    def execute(self, context):
        s = context.scene.bvh_retarget
        prefs = context.preferences.addons[__package__].preferences
        name = self.preset_name or s.preset_name.strip()

        pairs = rt.load_preset(prefs, name)
        if pairs is None:
            self.report({'ERROR'}, f"Preset '{name}' not found.")
            return {'CANCELLED'}

        s.bone_mappings.clear()
        for p in pairs:
            item = s.bone_mappings.add()
            item.source_bone = p.get("src", "")
            item.target_bone = p.get("tgt", "")
            item.enabled = p.get("en", True)
            item.retarget_mode = p.get("mode", "COPY_ROTATION")

        self.report({'INFO'}, f"Loaded preset '{name}' ({len(pairs)} bone pairs)")
        return {'FINISHED'}


class BVHRETARGET_OT_DeletePreset(Operator):
    """Delete a saved bone mapping preset"""
    bl_idname = "bvh_retarget.delete_preset"
    bl_label = "Delete Preset"

    preset_name: StringProperty()

    def execute(self, context):
        prefs = context.preferences.addons[__package__].preferences
        name = self.preset_name
        try:
            presets = json.loads(prefs.saved_presets)
            if name in presets:
                del presets[name]
                prefs.saved_presets = json.dumps(presets)
                self.report({'INFO'}, f"Deleted preset '{name}'")
            else:
                self.report({'WARNING'}, f"Preset '{name}' not found")
        except Exception as e:
            self.report({'ERROR'}, str(e))
        return {'FINISHED'}


class BVHRETARGET_OT_ExportPresetFile(Operator):
    """Export the current bone mapping to a JSON file"""
    bl_idname = "bvh_retarget.export_preset_file"
    bl_label = "Export Bone Map"

    filepath: StringProperty(subtype='FILE_PATH')
    filename_ext = ".json"
    filter_glob: StringProperty(default="*.json", options={'HIDDEN'})

    def invoke(self, context, event):
        s = context.scene.bvh_retarget
        self.filepath = (s.preset_name.strip() or "bone_map") + ".json"
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        s = context.scene.bvh_retarget
        pairs = [{"src": item.source_bone, "tgt": item.target_bone,
                  "en": item.enabled, "mode": item.retarget_mode}
                 for item in s.bone_mappings]
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(pairs, f, indent=2)
            self.report({'INFO'}, f"Exported {len(pairs)} bone pairs to {self.filepath}")
        except Exception as e:
            self.report({'ERROR'}, f"Export failed: {e}")
            return {'CANCELLED'}
        return {'FINISHED'}


class BVHRETARGET_OT_ImportPresetFile(Operator):
    """Import a bone mapping from a JSON file"""
    bl_idname = "bvh_retarget.import_preset_file"
    bl_label = "Import Bone Map"

    filepath: StringProperty(subtype='FILE_PATH')
    filename_ext = ".json"
    filter_glob: StringProperty(default="*.json", options={'HIDDEN'})

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        s = context.scene.bvh_retarget
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                pairs = json.load(f)
            if not isinstance(pairs, list):
                self.report({'ERROR'}, "File does not contain a JSON array.")
                return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Import failed: {e}")
            return {'CANCELLED'}

        s.bone_mappings.clear()
        for p in pairs:
            item = s.bone_mappings.add()
            item.source_bone = p.get("src", "")
            item.target_bone = p.get("tgt", "")
            item.enabled = p.get("en", True)
            item.retarget_mode = p.get("mode", "COPY_ROTATION")

        self.report({'INFO'}, f"Imported {len(pairs)} bone pairs from {self.filepath}")
        return {'FINISHED'}


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

_classes = [
    BVHRETARGET_OT_ImportBVH,
    BVHRETARGET_OT_AutoMapBones,
    BVHRETARGET_OT_AddBoneMapping,
    BVHRETARGET_OT_RemoveBoneMapping,
    BVHRETARGET_OT_ApplyRetargeting,
    BVHRETARGET_OT_RemoveRetargeting,
    BVHRETARGET_OT_RemoveSingleRetargeting,
    BVHRETARGET_OT_BakeRetargeting,
    BVHRETARGET_OT_SavePreset,
    BVHRETARGET_OT_LoadPreset,
    BVHRETARGET_OT_DeletePreset,
    BVHRETARGET_OT_ExportPresetFile,
    BVHRETARGET_OT_ImportPresetFile,
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


def unregister():
    for cls in reversed(_classes):
        _safe_unregister_class(cls)
