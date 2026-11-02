import bpy

from typing          import TYPE_CHECKING, Literal
from bpy.types       import PropertyGroup, Object, Context
from bpy.props       import StringProperty, EnumProperty, BoolProperty, PointerProperty

from .getters        import get_studio_props
from ..utils.typings import BlendEnum


class StudioWindow(PropertyGroup):

    def get_deform_modifiers(self, context: Context) -> BlendEnum:
        modifiers = get_studio_props().shape_modifiers_group
        if not modifiers:
            return [("None", "No Valid Modifiers", "")]
        return [(modifier.name, modifier.name, "", modifier.icon, index) for index, modifier in enumerate(modifiers)]
 
    shape_modifiers: EnumProperty(
    name= "",
    description= "Select a deform modifier",
    items=get_deform_modifiers
    )  # type: ignore

    def _shapes_type_validate(self, context) -> None:
        if not self.include_deforms and self.shapes_type == 'SINGLE':
            self.shapes_type = 'EXISTING'
    
    def _set_shape_enums(self, context):
        props = get_studio_props()

        if self.shapes_type == 'SINGLE':
            self.include_deforms = True
            props.validate_shapes_source_enum(context)
            props.validate_shapes_target_enum(context)
  
    shapes_method: EnumProperty(
        name= "",
        description= "Select an overview",
        items= [
            ("Selected", "Selection", "Uses the selected mesh as the source"),
            ("Chest", "Chest", "Uses the YAB Chest mesh as source"),
            ("Legs", "Legs", "Uses the YAB leg mesh as source"),
            ("Seams", "Seams", "Transfer seam related shape keys"),
        ]
        )  # type: ignore
    
    shapes_type: EnumProperty(
        name= "",
        description= "Select which keys to transfer",
        default=0,
        items=[
                ('EXISTING', "Existing", "Transfer/link all keys that already exist on the target"),
                ('ALL', "All Keys", "Transfer/link all keys"),
                ('SINGLE', "Single", "Transfers/links the selected key"),
            ],
        update=_set_shape_enums
        )  # type: ignore
    
    include_deforms: BoolProperty(
        default=False, 
        name="", 
        description="Enable this to include deforms. If disabled only the shape key entries are added", 
        update=_shapes_type_validate
        ) # type: ignore
    
    shape_leg_base: EnumProperty(
        name= "",
        description= "Select the base size",
        items= [
            ("Melon", "Watermelon Crushers", ""),
            ("Skull", "Skull Crushers", ""),
            ("Yanilla", "Yanilla", ""),
            ("Mini", "Mini", ""),
            ("Lavabod", "Lavabod", ""),
            ("Masc", "Masc", ""),
        ],
        )  # type: ignore
    
    shape_seam_base: EnumProperty(
        name= "",
        description= "Select the base size, only affects waist seam",
        items= [
            ("LARGE", "YAB", ""),
            ("Lavabod", "Lavabod", ""),
            ("Yanilla", "Yanilla", ""),
            ("Masc", "Masc", ""),
            ("Mini", "Mini", ""),
        ],
        )  # type: ignore
    
    def get_shape_key_enum(self, context:Context, obj:Object, new:bool=False) -> None:
        if obj is not None and obj.data.shape_keys:
            shape_keys = []
            if new:
                shape_keys.extend([("", "NEW:", ""),("None", "New Key", "")])
            shape_keys.append(("", "BASE:", ""))
            for index, key in enumerate(obj.data.shape_keys.key_blocks):
                if key.name.endswith(":"):
                    shape_keys.append(("", key.name, ""))
                    continue
                shape_keys.append((key.name, key.name, ""))
            return shape_keys
        else:
            return [("None", "New Key", "")]

    shapes_source_enum: EnumProperty(
        name= "",
        description= "Select a shape key",
        items=lambda self, context: self.get_shape_key_enum(context, bpy.context.scene.ya_studio_props.shapes_source)
        )  # type: ignore
    
    shapes_target_enum: EnumProperty(
        name= "",
        description= "Select a shape key",
        items=lambda self, context: self.get_shape_key_enum(context, bpy.context.scene.ya_studio_props.shapes_target, new=True)
        )  # type: ignore

    shapes_corrections: EnumProperty(
        name= "",
        default= "None",
        description= "Choose level of Corrective Smooth",
        items= [("", "Select degree of smoothing", ""),
                ("None", "None", ""),
                ("Smooth", "Smooth", ""),
                ("Aggressive", "Aggresive", ""),]
        )  # type: ignore
    
    def get_vertex_groups(self, context:Context, obj:Object) -> BlendEnum:
        if obj and obj.type == "MESH":
            return [("None", "None", "")] + [(group.name, group.name, "") for group in obj.vertex_groups]
        else:
            return [("None", "Select a target", "")]

    obj_vertex_groups: EnumProperty(
        name= "",
        description= "Select a group to pin, it will be ignored by any deforms",
        items=lambda self, context: self.get_vertex_groups(context, get_studio_props().shapes_target)
        )  # type: ignore
    
    exclude_vertex_groups: EnumProperty(
        name= "",
        description= "Select a group to exclude from shrinkwrapping",
        items=lambda self, context: self.get_vertex_groups(context, get_studio_props().shapes_target)
        )  # type: ignore
    
    yas_storage: EnumProperty(
        name="",
        description="Select what vertex groups to store",
        items=[
            ('ALL', "All Weights", "Store all YAS weights"),
            ('PHYS', "Physics", "Store all thigh/butt physics related weights"),
            ('GEN', "Genitalia", "Store all genitalia related weights"),
            ('HANDS', "Hands", "Store all finger related weights"),
            ('FEET', "Feet", "Store all toe related weights"),
        ]
        ) # type: ignore
    
    if TYPE_CHECKING:
        shapes_method        : Literal['Select', 'Chest', 'Legs', "Seams"]
        shapes_type          : Literal['EXISTING', 'ALL', 'SINGLE']
        shape_leg_base       : Literal['Melon', 'Skull', 'Yanilla', 'Mini', 'Lavabod', 'Masc']
        shape_seam_base      : Literal['LARGE', 'Lavabod', 'Yanilla', 'Masc', 'Mini']
        shapes_corrections   : Literal['None', 'Smooth', 'Aggressive']

        shape_modifiers      : str
        include_deforms      : bool
        shapes_source_enum   : str
        shapes_target_enum   : str
        obj_vertex_groups    : str
        exclude_vertex_groups: str
        yas_storage          : str

class YAWindowProps(PropertyGroup):
    
    studio: PointerProperty(
        type=StudioWindow
        ) # type: ignore
    
    ui_buttons_list = [
            ("backfaces",   "expand",     "Opens the category"),
            ("modifiers",   "expand",     "Opens the category"),
            ("transp",      "expand",     "Opens the category"),
            ("yas_man",     "expand",     "Opens the category"),
        ]
    
    extra_options = [
            ("shapes",   "category",    True,   "Enables shape transfer menu"),
            ("mesh",     "category",    False,  "Enables mesh editing menu"),
            ("weights",  "category",    False,  "Enables weight editing menu"),

            ("file",     "category",    True,   "General file utilities"),
            ("phyb",     "category",    False,  "Phyb file utilities"),
            ("model",    "category",    False,  "Model file utilities"),

            ("filter",   "vgroups",     True,   "Switches between showing all vertex groups or just YAS groups"),
            ("keep",      "modifier",   False,  "Keeps the modifier after applying. Unable to keep Data Transfers"),
            ("all",       "keys",       False,  "Transfers all shape keys from source to target"),
            ("existing",  "only",       False,  "Only updates deforms of shape keys that already exist on the target"),
            ("adjust",    "overhang",   False,  "Tries to adjust for clothing that hangs off of the breasts"),
            ("add",       "shrinkwrap", False,  "Applies a shrinkwrap modifier when deforming the mesh. Remember to exclude parts of the mesh overlapping with the body"),
            ("seam",      "waist",      False,  "Applies the selected seam shape key to your mesh"),
            ("seam",      "wrist",      False,  "Applies the selected seam shape key to your mesh"),
            ("seam",      "ankle",      False,  "Applies the selected seam shape key to your mesh"),
            ("sub",       "shape_keys", False,  """Includes minor shape keys without deforms:
            - Squeeze
            - Push-Up
            - Omoi
            - Sag
            - Nip Nops"""),
        ]

    @staticmethod
    def set_extra_options() -> None:
        for (name, category, default, description) in YAWindowProps.extra_options:
            category_lower = category.lower()
            name_lower = name.lower()
            
            prop_name = f"{name_lower}_{category_lower}"
            prop = BoolProperty(
                name="", 
                description=description,
                default=default, 
                )
            setattr(YAWindowProps, prop_name, prop)

    insp_file1: StringProperty(
        name="",
        default="",
        description="File to inspect", 
        maxlen=255,
        )  # type: ignore
    
    insp_file2: StringProperty(
        name="",
        default="",
        description="File to inspect", 
        maxlen=255,
        )  # type: ignore
    
    sym_group_l: StringProperty(
        name="",
        default="_l",
        description="Left group suffix", 
        maxlen=10,
        )  # type: ignore
    
    sym_group_r: StringProperty(
        name="",
        default="_r",
        description="Right group suffix", 
        maxlen=10,
        )  # type: ignore
    

    @staticmethod
    def ui_buttons() -> None:
        for (name, category, description) in YAWindowProps.ui_buttons_list:
            category_lower = category.lower()
            name_lower = name.lower()

            default = False
            if name_lower == "advanced":
                default = True
            
            prop_name = f"button_{name_lower}_{category_lower}"
            prop = BoolProperty(
                name="", 
                description=description,
                default=default, 
                )
            setattr(YAWindowProps, prop_name, prop)

    if TYPE_CHECKING:
        studio          : StudioWindow

        insp_file1 : str
        insp_file2 : str
        sym_group_l: str
        sym_group_r: str
 
        # Created at registration
        shapes_category  : bool
        mesh_category    : bool
        weights_category : bool
        filter_vgroups   : bool
        file_category    : bool
        phyb_category    : bool
        model_category   : bool

        button_backfaces_expand: bool
        button_modifiers_expand: bool
        button_transp_expand   : bool
        button_yas_man_expand  : bool

        keep_modifier   : bool
        adjust_overhang : bool
        add_shrinkwrap  : bool
        seam_waist      : bool
        seam_wrist      : bool
        seam_ankle      : bool
        sub_shape_keys  : bool


CLASSES = [
    StudioWindow,
    YAWindowProps,
]