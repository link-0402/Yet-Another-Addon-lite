import bpy

from bpy.types        import Object, Context, Panel, Scene, Depsgraph
from bpy.app.handlers import persistent

from .getters         import get_devkit_props, get_studio_props


# The body parts the Mannequin's settings are synced to: the part's settings in the devkit, its mesh, and the
# Mannequin settings it shares. Sizes come before the options the devkit ties to them (Lavabod has no Masc chest,
# Alt Hips no Lavabod or Mini legs), so each change is allowed by the time it's made.
PARTS = (
    ("torso_state", "yam_torso", ("chest_size", "buff", "rue", "better_nipples", "lavabod")),
    ("leg_state",   "yam_legs",  ("leg_size", "alt_hips", "gen", "rue", "small_butt", "soft_butt", "camel_toe", "squish")),
    ("hand_state",  "yam_hands", ("hand_size", "nails", "clawsies")),
    ("feet_state",  "yam_feet",  ("rue_feet",)),
)

HEEL_KEYS = ("Heels", "Cinderella", "Mini Heels")

OVERVIEW_PANEL = "VIEW3D_PT_YA_Overview"

# Changing a devkit setting that has no update function doesn't update the scene, so the depsgraph handler misses
# it: a timer looks at the Mannequin this often (seconds) too.
POLL_INTERVAL = 3.0

# Per scene (by pointer) and part, the Mannequin's settings and slider values it was last synced to, or last seen
# with.
_synced: dict[tuple[int, str], tuple] = {}
# Per Key datablock (by pointer): how many drivers it had and the shape keys they drive.
_driven: dict[int, tuple[int, set[str]]] = {}
_syncing  = False
_reported = False


def _slider_keys(state_name: str, key_blocks) -> list[str]:
    """The Mannequin's shape keys the part takes along with its settings: the chest's sub shape sliders (Squeeze,
    Omoi, Sag...) for the torso, the heel sliders for the feet."""
    if state_name == "torso_state":
        return [key.name for key in key_blocks if key.name.startswith("-")]
    if state_name == "feet_state":
        return [name for name in HEEL_KEYS if name in key_blocks]
    return []

def _driven_keys(obj: Object) -> set[str]:
    """Shape keys of the object whose value a driver sets, kept until its drivers change."""
    key       = obj.data.shape_keys
    animation = key.animation_data
    if animation is None:
        return set()
    count  = len(animation.drivers)
    cached = _driven.get(key.as_pointer())
    if cached is not None and cached[0] == count:
        return cached[1]
    start, end = 'key_blocks["', '"].value'
    names = {curve.data_path[len(start):-len(end)] for curve in animation.drivers
             if curve.data_path.startswith(start) and curve.data_path.endswith(end)}
    _driven[key.as_pointer()] = (count, names)
    return names

def _has_keys(obj: Object | None) -> bool:
    return obj is not None and obj.type == 'MESH' and obj.data.shape_keys is not None

def sync_parts(force: bool=False) -> None:
    """Copy the Mannequin's settings and sliders to each body part whose share of them changed since the last call,
    or to every part with ``force``. The first call only notes them, so parts edited on their own while synced
    keep their edits until the Mannequin changes them again."""
    global _syncing

    props = get_devkit_props()
    if not props or not _has_keys(props.yam_mannequin):
        return

    mannequin = props.mannequin_state
    mq_keys   = props.yam_mannequin.data.shape_keys.key_blocks
    mq_driven = None
    scene     = bpy.context.scene.as_pointer()

    _syncing = True
    changed  = False
    try:
        for state_name, obj_attr, settings in PARTS:
            state = getattr(props, state_name, None)
            if state is None:
                continue
            settings = [name for name in settings if hasattr(mannequin, name) and hasattr(state, name)]

            obj   = getattr(props, obj_attr, None)
            names = []
            if _has_keys(obj):
                part_keys = obj.data.shape_keys.key_blocks
                if mq_driven is None:
                    mq_driven = _driven_keys(props.yam_mannequin)
                skip  = mq_driven | _driven_keys(obj)
                names = [name for name in _slider_keys(state_name, mq_keys) if name in part_keys and name not in skip]

            now = (tuple(getattr(mannequin, name) for name in settings),
                   tuple(names),
                   tuple(mq_keys[name].value for name in names))
            last = _synced.get((scene, state_name))
            _synced[(scene, state_name)] = now
            if not force and (last is None or last == now):
                continue

            for name in settings:
                value = getattr(mannequin, name)
                if getattr(state, name) != value:
                    setattr(state, name, value)
                    changed = True

            # After the settings: toggling Lavabod swaps the part's chest sliders for the ones it stored.
            for name in names:
                value = mq_keys[name].value
                if part_keys[name].value != value:
                    part_keys[name].value = value
                    changed = True
    finally:
        _syncing = False

    # Settings set from a timer or handler don't update the scene either, so the part's drivers would keep
    # showing the old shapes until something else did.
    if changed:
        bpy.context.scene.update_tag()

def sync_scene(scene: Scene | None) -> None:
    """sync_parts when ``scene`` is the current scene and syncs its Mannequin."""
    global _reported

    if _syncing or scene is None or scene != bpy.context.scene:
        return
    studio = getattr(scene, "ya_studio_props", None)
    if studio is None or not studio.sync_mannequin:
        return
    try:
        sync_parts()
    except Exception as error:
        if not _reported:
            print(f"Yet Another Addon: couldn't sync the Mannequin to the body parts: {error}")
            _reported = True

@persistent
def sync_handler(scene: Scene, depsgraph: Depsgraph) -> None:
    sync_scene(scene)

def sync_timer() -> float:
    attach_ui()
    sync_scene(getattr(bpy.context, "scene", None))
    return POLL_INTERVAL

def draw_sync(self: Panel, context: Context) -> None:
    window = getattr(context.window_manager, "ya_devkit_window", None)
    if window is None or window.overview_ui != "Body":
        return
    studio = get_studio_props()
    icon   = "LINKED" if studio.sync_mannequin else "UNLINKED"
    row    = self.layout.row(align=True)
    row.prop(studio, "sync_mannequin", text="Sync Mannequin to Body Parts", icon=icon)

def attach_ui() -> bool:
    """Add the sync toggle to the devkit's panel, which the devkit registers again with each file it loads."""
    panel = getattr(bpy.types, OVERVIEW_PANEL, None)
    if panel is None:
        return False
    if draw_sync not in getattr(panel.draw, "_draw_funcs", ()):
        panel.prepend(draw_sync)
    return True

def detach_ui() -> None:
    panel = getattr(bpy.types, OVERVIEW_PANEL, None)
    if panel is not None and draw_sync in getattr(panel.draw, "_draw_funcs", ()):
        panel.remove(draw_sync)

@persistent
def sync_load_post(dummy) -> None:
    _synced.clear()
    _driven.clear()

def set_sync_handlers() -> None:
    bpy.app.handlers.depsgraph_update_post.append(sync_handler)
    bpy.app.handlers.load_post.append(sync_load_post)
    bpy.app.timers.register(sync_timer, first_interval=POLL_INTERVAL, persistent=True)

def remove_sync_handlers() -> None:
    bpy.app.handlers.depsgraph_update_post.remove(sync_handler)
    bpy.app.handlers.load_post.remove(sync_load_post)
    if bpy.app.timers.is_registered(sync_timer):
        bpy.app.timers.unregister(sync_timer)
    detach_ui()
    _synced.clear()
    _driven.clear()
