import bpy

from bpy.props       import StringProperty, EnumProperty, BoolProperty
from bpy.types       import Operator, Context, Object, DataTransferModifier

from ..props         import get_window_props, get_studio_props, get_devkit_props
from ..mesh.weights  import remove_vertex_groups, restore_yas_groups
from ..mesh.objects  import get_collection_obj, get_object_from_mesh
from ..utils.typings import DevkitProps


YAS_GENITALIA = (
    "iv_kuritto",
    "iv_inshin_l",
    "iv_inshin_r",
    "iv_omanko",
    "iv_koumon",
    "iv_koumon_l",
    "iv_koumon_r",

    "iv_kintama_phys_l",
    "iv_kintama_phys_r",
    "iv_kougan_l",
    "iv_kougan_r",

    "iv_funyachin_phy_a",
    "iv_funyachin_phy_b",
    "iv_funyachin_phy_c",
    "iv_funyachin_phy_d",
    "iv_ochinko_a",
    "iv_ochinko_b",
    "iv_ochinko_c",
    "iv_ochinko_d",
    "iv_ochinko_e",
    "iv_ochinko_f",
)

YAS_PHYSICS = (
    "ya_shiri_phys_l",  "ya_shiri_phys_r",
    "iv_daitai_phys_l", "iv_daitai_phys_r",
    "ya_daitai_phys_l", "ya_daitai_phys_r",
)

YAS_HANDS = (
    'iv_hito_c_l',
    'iv_ko_c_l',
    'iv_kusu_c_l',
    'iv_naka_c_l',

    'iv_hito_c_r',
    'iv_ko_c_r',
    'iv_kusu_c_r',
    'iv_naka_c_r',
)

YAS_FEET = (
    'iv_asi_oya_a_l',
    'iv_asi_hito_a_l',
    'iv_asi_naka_a_l',
    'iv_asi_kusu_a_l',
    'iv_asi_ko_a_l',
    'iv_asi_oya_b_l',
    'iv_asi_hito_b_l',
    'iv_asi_naka_b_l',
    'iv_asi_kusu_b_l',
    'iv_asi_ko_b_l',

    'iv_asi_oya_a_r',
    'iv_asi_hito_a_r',
    'iv_asi_naka_a_r',
    'iv_asi_kusu_a_r',
    'iv_asi_ko_a_r',
    'iv_asi_oya_b_r',
    'iv_asi_hito_b_r',
    'iv_asi_naka_b_r',
    'iv_asi_kusu_b_r',
    'iv_asi_ko_b_r',
)

YAS_ALL = ("iv_", "ya_")


class RemoveEmptyVGroups(Operator):                         
    bl_idname = "ya.remove_empty_vgroups"
    bl_label = ""
    bl_description = "Removes Vertex Groups with no weights. Ignores locked groups"
    bl_options = {"UNDO"}

    @classmethod
    def poll(cls, context):
        obj = bpy.context.active_object
        return obj is not None and obj.type == 'MESH' and obj.vertex_groups

    def execute(self, context:Context):
        props    = get_studio_props()
        old_mode = context.mode
        match old_mode:
            case "PAINT_WEIGHT":
                old_mode = "WEIGHT_PAINT"
            case "EDIT_MESH":
                old_mode = "EDIT"
   
        bpy.ops.object.mode_set(mode='OBJECT')
        obj = context.active_object
        
        vgroups = {vg.index: False for vg in obj.vertex_groups if not vg.lock_weight}
        self.check_modifiers(obj, vgroups)

        context.window.cursor_set('WAIT')
        try:
            for vert in obj.data.vertices:
                for v_group in vert.groups:
                    if v_group.group in vgroups and v_group.weight > 0:
                        vgroups[v_group.group] = True
            
            removed = []
            for idx, used in sorted(vgroups.items(), reverse=True):
                if not used:
                    removed.append(obj.vertex_groups[idx].name)
                    obj.vertex_groups.remove(obj.vertex_groups[idx])
        finally:
            bpy.ops.object.mode_set(mode=old_mode)
            context.window.cursor_set('DEFAULT')
            
        if removed:
            self.report({'INFO'}, f"Removed {', '.join(removed)}.")
        else:
            self.report({'INFO'}, "No empty groups.")
            
        props.set_yas_ui_vgroups(context)
        return {"FINISHED"}
    
    def check_modifiers(self, obj: Object, vgroups: dict[int, bool]):
        data_source: set[str] = set()
        for modifier in obj.modifiers:
            vgroup = getattr(modifier, "vertex_group", False)
            if vgroup:
                vgroups[obj.vertex_groups.get(vgroup).index] = True

            if modifier.type == 'DATA_TRANSFER':
                modifier: DataTransferModifier
                source: Object = getattr(modifier, "object", False)
                if source and modifier.data_types_verts == 'VGROUP_WEIGHTS':
                    source_vgroups = [vgroup.name for vgroup in source.vertex_groups]
                    data_source.update(source_vgroups)
        
        for vgroup_name in data_source:
            source_vgroup = obj.vertex_groups.get(vgroup_name)
            if source_vgroup:
                vgroups[source_vgroup.index] = True
                    
class RemoveSelectedVGroups(Operator):
    bl_idname = "ya.remove_select_vgroups"
    bl_label = ""
    bl_description = "Removes selected group and adds the weights to the parent group"
    bl_options = {"UNDO"}

    preset: StringProperty() # type: ignore

    @classmethod
    def poll(cls, context:Context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH' and obj.vertex_groups

    def execute(self, context:Context):
        props    = get_studio_props()
        window   = get_window_props()
        old_mode = context.mode

        if self.preset == "PANEL" and props.yas_empty and window.filter_vgroups:
            self.report({"ERROR"}, "No YAS group selected.")
            return {"CANCELLED"}

        if old_mode == 'PAINT_WEIGHT':
            old_mode = 'WEIGHT_PAINT'

        bpy.ops.object.mode_set(mode='OBJECT')
        obj = context.active_object

        if self.preset != "MENU" and window.filter_vgroups:
            yas_vgroups  = props.yas_ui_vgroups
            index        = props.yas_vindex
            vertex_group = obj.vertex_groups.get(yas_vgroups[index].name)
        else: 
            vertex_group = obj.vertex_groups.active

        if not obj.parent or obj.parent.type != 'ARMATURE':
            self.report({'ERROR'}, "Mesh is missing a parent skeleton")
            return {'CANCELLED'}

        if not obj.parent.data.bones.get(vertex_group.name):
            self.report({'ERROR'}, "Selected group has no parent.")
            return {'CANCELLED'}
        
        remove_vertex_groups(obj, obj.parent, (vertex_group.name))

        parent_vgroup = obj.parent.data.bones.get(vertex_group.name).parent.name
        self.report({'INFO'}, f"Removed {vertex_group.name}, weights added to {parent_vgroup}.")
        bpy.ops.object.mode_set(mode=old_mode)
        props.set_yas_ui_vgroups(context)
        return {"FINISHED"}

class AddSymmetryGroup(Operator):
    bl_idname = "ya.add_symmetry_vgroup"
    bl_label = ""
    bl_description = "Add missing symmetry groups with empty weights"
    bl_options = {"UNDO"}

    def execute(self, context: Context):
        right_suffix = get_window_props().sym_group_r.strip()
        left_suffix  = get_window_props().sym_group_l.strip()

        if len(right_suffix) != len(left_suffix):
            self.report({'ERROR'}, "Both suffix need to be the same length")
            return {'CANCELLED'}
        
        symmetry_groups: dict[str, str] = {}
        obj = context.active_object

        for v_group in obj.vertex_groups:
            if v_group.name.endswith((left_suffix, right_suffix)):
                symmetry_groups[v_group.name] = None

        for v_group in obj.vertex_groups:
            opposite_suffix = None
            if v_group.name.endswith(left_suffix):
                opposite_suffix = right_suffix
            elif v_group.name.endswith(right_suffix):
                opposite_suffix = left_suffix
            if opposite_suffix:
                opposite = v_group.name[:-(len(opposite_suffix))] + opposite_suffix 
                if opposite in symmetry_groups:
                    symmetry_groups[v_group.name] = opposite
                
        added_groups = 0
        for v_group, opposite in symmetry_groups.items():
            if opposite is None:
                suffix   = right_suffix if v_group[-len(left_suffix):] == left_suffix else left_suffix
                new_name = v_group[:-(len(left_suffix))] + suffix
                obj.vertex_groups.new(name=new_name)
                added_groups += 1

        if added_groups:
            self.report({'INFO'}, "Symmetry groups added.")
        else:
            self.report({'INFO'}, "No symmetry groups to add.")
        return {'FINISHED'}

class AddYASGroups(Operator):
    bl_idname = "ya.add_yas_vgroups"
    bl_label = ""
    bl_description = "Add YAS related Vertex Groups"
    bl_options = {"UNDO"}


    user_input: EnumProperty(
        name="",
        items=[("TORSO", "Torso", ""),
               ("FINGERS", "Hands", ""),
               ("LEGS", "Legs", ""),
               ("TOES", "Feet", "")]) # type: ignore
    
    torso: BoolProperty(default=False) # type: ignore
    fingers: BoolProperty(default=False) # type: ignore
    legs: BoolProperty(default=False) # type: ignore
    toes: BoolProperty(default=False) # type: ignore

    anus: BoolProperty(default=False) # type: ignore
    penis: BoolProperty(default=False) # type: ignore
    vagina: BoolProperty(default=False) # type: ignore

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == "MESH"
    
    def invoke(self, context, event):
        context.window_manager.invoke_props_dialog(self, confirm_text="Confirm", title="", width=2)
        return {'RUNNING_MODAL'}
    
    def draw(self, context):
        layout = self.layout
        layout.label(text="Select categories:")

        row = layout.row(align=True)
        row.prop(self, "torso", icon="CHECKMARK" if self.torso else "X", text="Torso")
        row.prop(self, "fingers", icon="CHECKMARK" if self.fingers else "X", text="Fingers")

        row = layout.row(align=True)
        row.prop(self, "legs", icon="CHECKMARK" if self.legs else "X", text="Legs")
        row.prop(self, "toes", icon="CHECKMARK" if self.toes else "X", text="Toes")

        layout.separator(type="LINE")

        row = layout.row(align=True)
        row.prop(self, "anus", icon="CHECKMARK" if self.anus else "X", text="Anus")
        row.prop(self, "penis", icon="CHECKMARK" if self.penis else "X", text="Penis")

        row = layout.row(align=True)
        row.prop(self, "vagina", icon="CHECKMARK" if self.vagina else "X", text="Vagina")
        
    def execute(self, context):
        props = get_studio_props()

        torso_groups = [
            'iv_nitoukin_l',
            'iv_nitoukin_r',

            'ya_fukubu_phys',             
            'iv_fukubu_phys',            
            'iv_fukubu_phys_l',       
            'iv_fukubu_phys_r',
        ]
        
        fingers_groups = YAS_HANDS
        
        leg_groups = [
            'iv_shiri_l',
            'iv_shiri_r',
            'ya_shiri_phys_l',        
            'ya_shiri_phys_r',

            'ya_fukubu_phys',            
            'iv_fukubu_phys',            
            'iv_fukubu_phys_l',       
            'iv_fukubu_phys_r',

            'iv_daitai_phys_l',    
            'ya_daitai_phys_l',   
            'iv_daitai_phys_r',    
            'ya_daitai_phys_r'   
        ]

        toe_groups = YAS_FEET

        penis_groups = [
            'iv_kintama_phys_l',              
            'iv_kintama_phys_r',    
            'iv_kougan_l',
            'iv_kougan_r',

            'iv_funyachin_phy_a',           
            'iv_funyachin_phy_b',        
            'iv_funyachin_phy_c',        
            'iv_funyachin_phy_d',     
            'iv_ochinko_a',                 
            'iv_ochinko_b',              
            'iv_ochinko_c',              
            'iv_ochinko_d',                 
            'iv_ochinko_e',         
            'iv_ochinko_f',  
        ]

        vagina_groups = [
            'iv_kuritto',                   
            'iv_inshin_l',               
            'iv_inshin_r',               
            'iv_omanko',           
        ]

        anus_groups = [
            'iv_koumon',                      
            'iv_koumon_l',                 
            'iv_koumon_r',         
        ]
        
        obj                   = context.active_object
        to_transfer: set[str] = set()
        if self.torso:
            to_transfer.update(torso_groups)
        if self.fingers:
            to_transfer.update(fingers_groups)
        if self.legs:
            to_transfer.update(leg_groups)
        if self.anus:
            to_transfer.update(anus_groups)
        if self.penis:
            to_transfer.update(penis_groups)
        if self.vagina:
            to_transfer.update(vagina_groups)
        if self.toes:
            to_transfer.update(toe_groups)

        for group in to_transfer:
            if obj.vertex_groups.get(group):
                continue
            bpy.ops.object.vertex_group_add()
            obj.vertex_groups.active.name = group

        props.set_yas_ui_vgroups(context)
        return {"FINISHED"}  

class YASManager(Operator):
    bl_idname = "ya.yas_manager"
    bl_label = ""

    bl_options = {'UNDO', 'REGISTER'}

    mode: StringProperty(default="ACTIVE", options={'HIDDEN', 'SKIP_SAVE'}) # type: ignore
    target: StringProperty(options={'HIDDEN', 'SKIP_SAVE'}) # type: ignore
    store: BoolProperty(default=True, options={'HIDDEN', 'SKIP_SAVE'}) # type: ignore

    @classmethod
    def description(cls, context, properties):
        mannequin = ""
        if properties.target in ("HANDS", "FEET"):
            mannequin = f"\n    Includes the Mannequin's {properties.target.lower()} weights"

        if properties.mode == "RESTORE":
            return f'''Restore weights to target object.{mannequin}
    *CTRL click to delete the stored weights'''

        elif properties.target == "DEVKIT":
            return "Store weights for devkit meshes"

        else:
            return f'''Store target weights.{mannequin}
    *CTRL click to delete without storing'''

    def invoke(self, context, event):
        if self.target == 'DEVKIT':
            return self.execute(context)

        devkit     = get_devkit_props()
        self.store = not event.ctrl
        target     = self._devkit_objects(devkit).get(self.target) if self.target != 'ACTIVE' else context.active_object
        dependent  = self._dependent_target([target], devkit) or self._mannequin_groups(context, devkit) is not None
        delete_dep = dependent and not self.store

        if (self.target == "ACTIVE" or delete_dep) and dependent:
            cond_text = "restored" if self.mode == "RESTORE" else "stored"
            if delete_dep:
                cond_text = "deleted"

            context.window_manager.invoke_confirm(
                self,
                event=None,
                title="YAS Manager",
                message=f"The selected mesh is dependent on other devkit source meshes, the dependencies will also be {cond_text}.",
                icon='INFO'
                )
            return {'RUNNING_MODAL'}
        else:
            return self.execute(context)

    def execute(self, context: Context):
        props   = get_studio_props()
        devkit  = get_devkit_props()
        targets = self.get_targets(context, devkit)

        # Validate everything up front so a failure doesn't leave the targets half processed.
        if self.mode == "RESTORE":
            for obj, groups in targets.items():
                if not self._has_stored(obj, groups):
                    continue
                if len(obj.data.vertices) != obj.yas.old_count:
                    self.report({'ERROR'}, f"{obj.name}'s vertex count has changed, not possible to restore.")
                    return {'CANCELLED'}
        else:
            skeletons = {obj: self._get_skeleton(obj, devkit) for obj in targets}
            for obj, skeleton in skeletons.items():
                if skeleton is None:
                    self.report({'ERROR'}, f"{obj.name} is not parented to a skeleton.")
                    return {'CANCELLED'}

        skipped: list[str] = []
        context.window.cursor_set('WAIT')
        try:
            if self.mode == "RESTORE":
                for obj, groups in targets.items():
                    if not self._has_stored(obj, groups):
                        continue

                    if self.store:
                        restore_yas_groups(obj, groups)
                    else:
                        self._discard_stored(obj, groups)

                    self._update_flags(obj)

            else:
                prefix = self.get_prefix()
                for obj, groups in targets.items():
                    skipped += remove_vertex_groups(obj, skeletons[obj], groups or prefix, self.store)
                    if obj.yas.v_groups:
                        obj.yas.old_count = len(obj.data.vertices)

                    self._update_flags(obj)
        finally:
            context.window.cursor_set('DEFAULT')

        if skipped:
            self.report({'WARNING'}, f"No parent bone found for {', '.join(sorted(set(skipped)))}, left unchanged.")

        props.set_yas_ui_vgroups(context)
        return {'FINISHED'}

    def get_targets(self, context: Context, devkit: DevkitProps) -> dict[Object, tuple[str, ...] | None]:
        """Target objects mapped to the groups to handle, None means the groups of the selected mode."""
        base_targets = self._get_base_targets(context, devkit)

        if self.target == 'DEVKIT' or self._dependent_target(base_targets, devkit):
            base_targets.extend(self._get_devkit_targets(devkit))

        if devkit:
            self._add_secondary_meshes(base_targets, devkit)

        targets: dict[Object, tuple[str, ...] | None] = {
            obj: None for obj in base_targets if obj and obj.type == 'MESH'
            }

        mannequin_groups = self._mannequin_groups(context, devkit)
        if mannequin_groups and devkit.yam_mannequin not in targets:
            targets[devkit.yam_mannequin] = mannequin_groups

        return targets

    def get_prefix(self) -> tuple[str, ...]:
        prefixes = {
            "ALL"  : YAS_ALL,
            "PHYS" : YAS_PHYSICS,
            "HANDS": YAS_HANDS,
            "FEET" : YAS_FEET,
        }

        return prefixes.get(self.mode, YAS_GENITALIA)

    def _devkit_objects(self, devkit: DevkitProps) -> dict[str, Object]:
        if not devkit:
            return {}

        return {
            "TORSO": devkit.yam_torso,
            "LEGS":  devkit.yam_legs,
            "HANDS": devkit.yam_hands,
            "FEET":  devkit.yam_feet,
            "MANNEQUIN": devkit.yam_mannequin,
        }

    def _get_base_targets(self, context: Context, devkit: DevkitProps) -> list[Object]:
        if self.target == "DEVKIT":
            return []

        devkit_targets = self._devkit_objects(devkit)
        if self.target in devkit_targets:
            return [devkit_targets[self.target]]

        return [context.active_object] if context.active_object else []

    def _dependent_target(self, base_targets: list[Object], devkit: DevkitProps) -> bool:
        if not devkit or not base_targets or not base_targets[0]:
            return False

        if self.target == "DEVKIT":
            return self.mode not in ("GEN", "PHYS")

        if self.mode == "RESTORE":
            if not base_targets[0].yas.all_groups:
                return False

        if self.mode in ("ALL", "RESTORE"):
            dependent_targets = {"TORSO", "LEGS", "MANNEQUIN"}

            if self.target in dependent_targets:
                return True

            if self.target == "ACTIVE":
                devkit_objects = [devkit.yam_torso, devkit.yam_legs, devkit.yam_mannequin]
                return base_targets[0] in devkit_objects

        return False

    def _mannequin_groups(self, context: Context, devkit: DevkitProps) -> tuple[str, ...] | None:
        """The Mannequin contains the devkit hands and feet as well, so their weights are handled there too."""
        if not devkit or not devkit.yam_mannequin or self.target == "DEVKIT":
            return None

        source = self._devkit_objects(devkit).get(self.target) if self.target != 'ACTIVE' else context.active_object
        if source is None:
            return None

        if source == devkit.yam_hands and self.mode in ("ALL", "HANDS", "RESTORE"):
            groups = YAS_HANDS
        elif source == devkit.yam_feet and self.mode in ("ALL", "FEET", "RESTORE"):
            groups = YAS_FEET
        else:
            return None

        if self.mode == "RESTORE" and not self._has_stored(devkit.yam_mannequin, groups):
            return None

        return groups

    def _get_devkit_targets(self, devkit: DevkitProps) -> list[Object]:
        if self.target == "DEVKIT" and self.mode == "ALL":
            devkit_objects = [devkit.yam_torso, devkit.yam_legs,devkit.yam_hands, devkit.yam_feet, devkit.yam_mannequin]
        elif self.target == "DEVKIT" and self.mode == "HANDS":
            devkit_objects = [devkit.yam_hands, devkit.yam_mannequin]
        elif self.target == "DEVKIT" and self.mode == "FEET":
            devkit_objects = [devkit.yam_feet, devkit.yam_mannequin]
        else:
            devkit_objects = [devkit.yam_torso, devkit.yam_legs, devkit.yam_mannequin]

        data_source_objects = get_collection_obj("Data Sources", type='MESH', sub_collections=True)

        devkit_targets = devkit_objects + data_source_objects
        return devkit_targets

    def _add_secondary_meshes(self, targets: list[Object], devkit: DevkitProps):
        if devkit.yam_torso in targets:
            targets.append(get_object_from_mesh("Neck"))
            targets.append(get_object_from_mesh("Elbow"))
            targets.append(get_object_from_mesh("Wrist"))
            targets.append(get_object_from_mesh("PiercBelly"))
            targets.extend(get_collection_obj("Nipple Piercings", type='MESH'))

        if devkit.yam_hands in targets:
            targets.extend(get_collection_obj("Nails", type='MESH', sub_collections=True))
            targets.extend(get_collection_obj("Clawsies", type='MESH'))

        if devkit.yam_legs in targets:
            targets.append(get_object_from_mesh("Knees"))
            targets.extend(get_collection_obj("Pubes", type='MESH'))

        if devkit.yam_feet in targets:
            targets.extend(get_collection_obj("Toenails", type='MESH'))
            targets.extend(get_collection_obj("Toe Clawsies", type='MESH'))

    def _get_skeleton(self, obj: Object, devkit: DevkitProps) -> Object | None:
        skeleton = bpy.data.objects.get("Skeleton") if devkit else None
        if skeleton is None or skeleton.type != 'ARMATURE':
            skeleton = obj.parent

        if skeleton is None or skeleton.type != 'ARMATURE':
            return None

        return skeleton

    def _has_stored(self, obj: Object, groups: tuple[str, ...] | None) -> bool:
        if groups is None:
            return bool(obj.yas.v_groups)

        return any(v_group.name in groups for v_group in obj.yas.v_groups)

    def _discard_stored(self, obj: Object, groups: tuple[str, ...] | None) -> None:
        v_groups = obj.yas.v_groups
        for idx in reversed(range(len(v_groups))):
            if groups is None or v_groups[idx].name in groups:
                v_groups.remove(idx)

    def _update_flags(self, obj: Object) -> None:
        """A category counts as stored when its groups are in storage and none are left on the mesh."""
        stored  = {v_group.name for v_group in obj.yas.v_groups}
        present = {v_group.name for v_group in obj.vertex_groups}

        def category_stored(groups: tuple[str, ...]) -> bool:
            return bool(stored.intersection(groups)) and not present.intersection(groups)

        obj.yas.all_groups = bool(stored) and not any(name.startswith(YAS_ALL) for name in present)
        obj.yas.genitalia  = category_stored(YAS_GENITALIA)
        obj.yas.physics    = category_stored(YAS_PHYSICS)
        obj.yas.hands      = category_stored(YAS_HANDS)
        obj.yas.feet       = category_stored(YAS_FEET)

    
CLASSES = [
    RemoveEmptyVGroups,
    RemoveSelectedVGroups,
    AddSymmetryGroup,
    AddYASGroups,
    YASManager
]
