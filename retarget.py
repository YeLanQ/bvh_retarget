"""
BVH Retarget — Core retargeting logic
Constraint-based motion retargeting from source armature to target armature.

Three modes per bone pair:
  COPY_ROTATION   Copy Rotation in WORLD space.
                  Root bone additionally gets Copy Location.
                  Good for rigs with the same rest pose as source.

  COPY_TRANSFORMS Copy Transforms in LOCAL space (loc + rot + scale together).
                  Simpler than the split loc/rot approach; useful when the
                  target rig's bone lengths don't match the source.

  CHILD_OF        Full parent-child relationship via a Child Of constraint.
                  Best for floating / weapon bones or when you want exact
                  world-space tracking.

  CHILD_OF_ROTATION  Same as CHILD_OF but with only the rotation channels
                  enabled (location and scale are left off). Useful when you
                  want the parent-child rotation tracking without inheriting
                  the source bone's position.
"""

import bpy
import mathutils
import re


CONSTRAINT_PREFIX = "BVH_RETARGET_"   # prefix for all constraints we add


# ---------------------------------------------------------------------------
# Bone name auto-matching
# ---------------------------------------------------------------------------

# Common bone name pairs: (source_name, common_target_names...)
_BONE_MAP_HINTS = [
    ("Hips",            ["hips", "pelvis", "root", "Hip", "Pelvis", "mixamorig:Hips"]),
    ("Spine",           ["spine", "Spine1", "mixamorig:Spine"]),
    ("Spine1",          ["spine1", "spine_01", "mixamorig:Spine1"]),
    ("Spine2",          ["spine2", "chest", "mixamorig:Spine2"]),
    ("Neck",            ["neck", "Neck1", "mixamorig:Neck"]),
    ("Head",            ["head", "Head", "mixamorig:Head"]),
    ("LeftShoulder",    ["l_shoulder", "shoulder.L", "mixamorig:LeftShoulder", "LeftShoulder"]),
    ("LeftArm",         ["upper_arm.L", "l_arm", "mixamorig:LeftArm", "LeftUpArm"]),
    ("LeftForeArm",     ["forearm.L", "l_forearm", "mixamorig:LeftForeArm"]),
    ("LeftHand",        ["hand.L", "l_hand", "mixamorig:LeftHand"]),
    ("RightShoulder",   ["r_shoulder", "shoulder.R", "mixamorig:RightShoulder", "RightShoulder"]),
    ("RightArm",        ["upper_arm.R", "r_arm", "mixamorig:RightArm", "RightUpArm"]),
    ("RightForeArm",    ["forearm.R", "r_forearm", "mixamorig:RightForeArm"]),
    ("RightHand",       ["hand.R", "r_hand", "mixamorig:RightHand"]),
    ("LeftUpLeg",       ["thigh.L", "l_thigh", "mixamorig:LeftUpLeg", "LeftThigh"]),
    ("LeftLeg",         ["shin.L", "l_shin", "mixamorig:LeftLeg", "LeftShin"]),
    ("LeftFoot",        ["foot.L", "l_foot", "mixamorig:LeftFoot"]),
    ("LeftToeBase",     ["toe.L", "l_toe", "mixamorig:LeftToeBase"]),
    ("RightUpLeg",      ["thigh.R", "r_thigh", "mixamorig:RightUpLeg", "RightThigh"]),
    ("RightLeg",        ["shin.R", "r_shin", "mixamorig:RightLeg", "RightShin"]),
    ("RightFoot",       ["foot.R", "r_foot", "mixamorig:RightFoot"]),
    ("RightToeBase",    ["toe.R", "r_toe", "mixamorig:RightToeBase"]),
]


def _normalize(name: str) -> str:
    """Lowercase, strip prefix up to ':', remove non-alphanumeric except underscore."""
    name = name.lower()
    if ":" in name:
        name = name.split(":")[-1]
    # Keep underscore as it's a common bone naming separator
    return re.sub(r"[^a-z0-9_]", "", name)


def auto_build_mapping(source_arm: bpy.types.Object,
                       target_arm: bpy.types.Object) -> list[tuple[str, str]]:
    """
    Attempt to auto-match bones between source and target armatures.
    Returns list of (source_bone_name, target_bone_name) pairs.
    """
    src_bones = {b.name for b in source_arm.data.bones}
    tgt_bones = {b.name: _normalize(b.name) for b in target_arm.data.bones}

    result = []
    for src_name, alternatives in _BONE_MAP_HINTS:
        if src_name not in src_bones:
            continue
        # Try exact match first
        matched = None
        for tgt_name in target_arm.data.bones.keys():
            if tgt_name == src_name:
                matched = tgt_name
                break
        # Try normalized match
        if not matched:
            src_norm = _normalize(src_name)
            for tgt_name, tgt_norm in tgt_bones.items():
                if src_norm == tgt_norm:
                    matched = tgt_name
                    break
        # Try alternatives
        if not matched:
            for alt in alternatives:
                if alt in tgt_bones:
                    matched = alt
                    break
                alt_norm = _normalize(alt)
                for tgt_name, tgt_norm in tgt_bones.items():
                    if alt_norm == tgt_norm:
                        matched = tgt_name
                        break
                if matched:
                    break
        if matched:
            result.append((src_name, matched))

    return result


# ---------------------------------------------------------------------------
# Constraint setup
# ---------------------------------------------------------------------------

def apply_retargeting_constraints(
    source_arm: bpy.types.Object,
    target_arm: bpy.types.Object,
    bone_pairs: "list[tuple]",
    root_bone: str = "",
) -> "tuple[int, list[str]]":
    """
    Add retargeting constraints to each enabled bone pair.
    Returns (n_applied, [warning_messages]).

    bone_pairs tuples: (source_bone, target_bone, enabled, retarget_mode)
    retarget_mode:  'COPY_ROTATION' | 'COPY_TRANSFORMS' | 'CHILD_OF'
                    | 'CHILD_OF_ROTATION'
    """
    source_arm.hide_viewport = False
    target_arm.hide_viewport = False

    tgt_pose = target_arm.pose
    applied = 0
    warnings = []

    for entry in bone_pairs:
        if len(entry) == 4:
            src_name, tgt_name, enabled, mode = entry
        elif len(entry) == 3:
            src_name, tgt_name, enabled = entry
            mode = "COPY_ROTATION"
        else:
            continue

        if not enabled:
            continue

        tgt_pbone = tgt_pose.bones.get(tgt_name)
        if not tgt_pbone:
            warnings.append(f"Target bone '{tgt_name}' not found — skipped.")
            continue
        if src_name not in source_arm.data.bones:
            warnings.append(f"Source bone '{src_name}' not in source armature — skipped.")
            continue

        # Clear previous retargeting constraints on this bone
        for c in list(tgt_pbone.constraints):
            if c.name.startswith(CONSTRAINT_PREFIX):
                tgt_pbone.constraints.remove(c)

        # Root bone detection: user-specified takes priority, then auto-detect
        if root_bone:
            is_root = (tgt_name == root_bone)
        else:
            # Auto-detect root bone by checking common naming conventions
            src_name_lower = src_name.lower()
            is_root = src_name_lower in ("hips", "pelvis", "root") or \
                      src_name_lower.endswith(":hips") or \
                      src_name_lower.endswith(":pelvis") or \
                      src_name_lower.endswith(":root")

        if mode == "COPY_ROTATION":
            _add_copy_rotation(tgt_pbone, source_arm, src_name, is_root)
        elif mode == "COPY_TRANSFORMS":
            _add_copy_transforms(tgt_pbone, source_arm, src_name)
        elif mode == "CHILD_OF":
            _add_child_of(tgt_pbone, source_arm, src_name)
        elif mode == "CHILD_OF_ROTATION":
            _add_child_of(tgt_pbone, source_arm, src_name, rotation_only=True)
        else:
            warnings.append(f"Unknown retarget mode '{mode}' for '{tgt_name}' — using Copy Rotation.")
            _add_copy_rotation(tgt_pbone, source_arm, src_name, is_root)

        applied += 1

    return applied, warnings


# ---------------------------------------------------------------------------
# Per-mode helpers
# ---------------------------------------------------------------------------

def _add_copy_rotation(pbone, source_arm, src_name: str, is_root: bool = False) -> None:
    """Copy Rotation in local space; root bone also gets Copy Location."""
    if is_root:
        loc = pbone.constraints.new("COPY_LOCATION")
        loc.name = CONSTRAINT_PREFIX + "Location"
        loc.target = source_arm
        loc.subtarget = src_name
        loc.mix_mode = 'REPLACE'
        loc.owner_space = 'LOCAL'
        loc.target_space = 'LOCAL'
        loc.use_offset = False

    rot = pbone.constraints.new("COPY_ROTATION")
    rot.name = CONSTRAINT_PREFIX + "Rotation"
    rot.target = source_arm
    rot.subtarget = src_name
    rot.mix_mode = 'REPLACE'
    rot.owner_space = 'LOCAL'
    rot.target_space = 'LOCAL'


def _add_copy_transforms(pbone, source_arm, src_name: str) -> None:
    """Copy Transforms in local space (location + rotation + scale)."""
    ct = pbone.constraints.new("COPY_TRANSFORMS")
    ct.name = CONSTRAINT_PREFIX + "CopyTransforms"
    ct.target = source_arm
    ct.subtarget = src_name
    ct.mix_mode = 'REPLACE'
    ct.owner_space = 'LOCAL'
    ct.target_space = 'LOCAL'


def _add_child_of(pbone, source_arm, src_name: str, rotation_only: bool = False) -> None:
    """
    Child Of constraint with the inverse matrix set automatically.
    When rotation_only is True, only the rotation channels are enabled.
    """
    use_location = not rotation_only

    co = pbone.constraints.new("CHILD_OF")
    co.name = CONSTRAINT_PREFIX + ("ChildOfRotation" if rotation_only else "ChildOf")
    co.target = source_arm
    co.subtarget = src_name
    co.use_location_x = use_location
    co.use_location_y = use_location
    co.use_location_z = use_location
    co.use_rotation_x = True
    co.use_rotation_y = True
    co.use_rotation_z = True
    co.use_scale_x = False
    co.use_scale_y = False
    co.use_scale_z = False

    # Set Inverse: invert the source bone's rest pose world matrix so the
    # target bone stays exactly where it is when the constraint first fires.
    # Using the bone's rest pose matrix instead of current pose matrix
    # ensures correct behavior regardless of which frame the constraint is applied on.
    src_bone = source_arm.data.bones.get(src_name)
    if src_bone:
        co.inverse_matrix = (source_arm.matrix_world @ src_bone.matrix_local).inverted()
    else:
        co.inverse_matrix = mathutils.Matrix.Identity(4)


def remove_retargeting_constraints(target_arm: bpy.types.Object) -> int:
    """Removes all retargeting constraints from target armature. Returns count removed."""
    removed = 0
    for pbone in target_arm.pose.bones:
        for c in list(pbone.constraints):
            if c.name.startswith(CONSTRAINT_PREFIX):
                pbone.constraints.remove(c)
                removed += 1
    return removed


# ---------------------------------------------------------------------------
# Baking
# ---------------------------------------------------------------------------

def bake_retargeted_animation(
    target_arm: bpy.types.Object,
    frame_start: int,
    frame_end: int,
) -> bool:
    """
    Bakes the driven (constraint) animation into actual keyframes,
    then removes the retargeting constraints.
    Returns True on success.
    """
    try:
        # Select only target armature
        bpy.ops.object.select_all(action='DESELECT')
        target_arm.select_set(True)
        bpy.context.view_layer.objects.active = target_arm

        # Enter pose mode for baking
        bpy.ops.object.mode_set(mode='POSE')
        bpy.ops.pose.select_all(action='SELECT')

        bpy.ops.nla.bake(
            frame_start=frame_start,
            frame_end=frame_end,
            only_selected=False,
            visual_keying=True,
            clear_constraints=True,
            clear_parents=False,
            use_current_action=True,
            bake_types={'POSE'},
        )

        bpy.ops.object.mode_set(mode='OBJECT')
        return True

    except Exception as e:
        print(f"[BVH Retarget] Bake error: {e}")
        return False


# ---------------------------------------------------------------------------
# Preset save / load
# ---------------------------------------------------------------------------

def save_preset(prefs, preset_name: str, bone_pairs: list[dict]) -> None:
    """Save bone mapping to addon preferences."""
    import json
    try:
        presets = json.loads(prefs.saved_presets)
    except Exception:
        presets = {}
    presets[preset_name] = bone_pairs
    prefs.saved_presets = json.dumps(presets)


def load_preset(prefs, preset_name: str) -> list[dict] | None:
    """Load bone mapping from addon preferences. Returns None if not found."""
    import json
    try:
        presets = json.loads(prefs.saved_presets)
        return presets.get(preset_name)
    except Exception:
        return None


def list_presets(prefs) -> list[str]:
    """Returns list of saved preset names."""
    import json
    try:
        return list(json.loads(prefs.saved_presets).keys())
    except Exception:
        return []
