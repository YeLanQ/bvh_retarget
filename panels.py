"""
BVH Retarget — Panels
N-panel UI panels in the 3D Viewport -> BVH Retarget tab.
"""

import bpy
from bpy.types import Panel


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------

class BVHRETARGET_PanelBase:
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'BVH Retarget'


# ---------------------------------------------------------------------------
# Panel 1: Import
# ---------------------------------------------------------------------------

class BVHRETARGET_PT_Import(BVHRETARGET_PanelBase, Panel):
    bl_label = "Import BVH"
    bl_idname = "BVHRETARGET_PT_Import"
    bl_order = 10

    def draw(self, context):
        layout = self.layout
        s = context.scene.bvh_retarget

        # Import settings
        box = layout.box()
        box.label(text="Import Settings:", icon='PREFERENCES')
        box.prop(s, "bvh_scale", text="Scale")

        # Import button
        row = layout.row(align=True)
        row.scale_y = 1.5
        row.operator("bvh_retarget.import_bvh", text="Import BVH File", icon='IMPORT')

        # Source armature display
        if s.source_armature:
            box = layout.box()
            box.label(text="Source Armature:", icon='ARMATURE_DATA')
            box.prop(s, "source_armature", text="")


# ---------------------------------------------------------------------------
# Panel 2: Retarget
# ---------------------------------------------------------------------------

class BVHRETARGET_PT_Retarget(BVHRETARGET_PanelBase, Panel):
    bl_label = "Retarget"
    bl_idname = "BVHRETARGET_PT_Retarget"
    bl_order = 20

    def draw(self, context):
        layout = self.layout
        s = context.scene.bvh_retarget

        # Armature pickers
        box = layout.box()
        box.label(text="Armatures", icon='ARMATURE_DATA')
        box.prop(s, "source_armature", text="Source")
        box.prop(s, "target_armature", text="Target")
        box.prop(s, "retarget_root_bone", text="Root Bone")

        layout.separator()

        # Bone mapping list
        layout.label(text="Bone Mapping:", icon='BONE_DATA')

        if s.source_armature and s.target_armature:
            # Auto-match button
            layout.operator("bvh_retarget.auto_map_bones",
                            text="Auto-Match Bones", icon='SHADERFX')

        row = layout.row()
        row.template_list(
            "BVHRETARGET_UL_BoneMappings", "",
            s, "bone_mappings",
            s, "bone_mapping_index",
            rows=6,
        )

        col = row.column(align=True)
        col.operator("bvh_retarget.add_bone_mapping", text="", icon='ADD')
        col.operator("bvh_retarget.remove_bone_mapping", text="", icon='REMOVE')

        layout.separator()

        # Apply / Remove constraints
        row = layout.row(align=True)
        row.operator("bvh_retarget.apply_retargeting", text="Apply Constraints", icon='CONSTRAINT_BONE')
        row.operator("bvh_retarget.remove_retargeting", text="", icon='X')


# ---------------------------------------------------------------------------
# Panel 3: Bake
# ---------------------------------------------------------------------------

class BVHRETARGET_PT_Bake(BVHRETARGET_PanelBase, Panel):
    bl_label = "Bake Animation"
    bl_idname = "BVHRETARGET_PT_Bake"
    bl_order = 30

    def draw(self, context):
        layout = self.layout
        s = context.scene.bvh_retarget

        box = layout.box()
        box.label(text="Bake to Keyframes", icon='RENDER_ANIMATION')
        row = box.row(align=True)
        row.prop(s, "bake_start_frame", text="Start")
        row.prop(s, "bake_end_frame", text="End")
        box.operator("bvh_retarget.bake_retargeting",
                     text="Bake & Remove Constraints", icon='NLA_PUSHDOWN')


# ---------------------------------------------------------------------------
# Panel 4: Presets
# ---------------------------------------------------------------------------

class BVHRETARGET_PT_Presets(BVHRETARGET_PanelBase, Panel):
    bl_label = "Presets"
    bl_idname = "BVHRETARGET_PT_Presets"
    bl_order = 40
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        s = context.scene.bvh_retarget

        box = layout.box()
        box.label(text="Bone Map Presets", icon='PRESET')
        row = box.row(align=True)
        row.prop(s, "preset_name", text="")
        row.operator("bvh_retarget.save_preset", text="", icon='FILE_TICK')
        row.operator("bvh_retarget.load_preset", text="", icon='IMPORT').preset_name = s.preset_name

        # List saved presets
        try:
            prefs = context.preferences.addons[__package__].preferences
            from . import retarget as rt
            preset_names = rt.list_presets(prefs)
        except Exception:
            preset_names = []

        if preset_names:
            col = box.column(align=True)
            for name in preset_names:
                row2 = col.row(align=True)
                op_load = row2.operator("bvh_retarget.load_preset", text=name, icon='IMPORT')
                op_load.preset_name = name
                op_del = row2.operator("bvh_retarget.delete_preset", text="", icon='TRASH')
                op_del.preset_name = name

        # File export / import
        row = box.row(align=True)
        row.operator("bvh_retarget.export_preset_file", text="Export to File", icon='EXPORT')
        row.operator("bvh_retarget.import_preset_file", text="Import from File", icon='IMPORT')


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

_classes = [
    BVHRETARGET_PT_Import,
    BVHRETARGET_PT_Retarget,
    BVHRETARGET_PT_Bake,
    BVHRETARGET_PT_Presets,
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
