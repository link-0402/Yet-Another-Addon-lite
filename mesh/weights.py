import bmesh
import numpy as np

from numpy           import float32, uint32
from bpy.types       import Object, VertexGroup
from numpy.typing    import NDArray
from collections.abc import Iterable

from ..props.studio  import YASGroup


def add_to_vgroup(weight_matrix: NDArray, v_group: VertexGroup) -> NDArray:
    indices = np.flatnonzero(weight_matrix[:, v_group.index])
    weights = weight_matrix[:, v_group.index][indices]
    if len(indices) == 0:
        return

    grouped_indices, unique_weights = group_weights(indices, weights)
    
    for array_idx, vert_indices in enumerate(grouped_indices):
        vert_indices = vert_indices.tolist()
        v_group.add(vert_indices, unique_weights[array_idx], type='ADD')

def group_weights(indices: NDArray[uint32], weights: NDArray[float32]) -> tuple[list[NDArray[uint32]], NDArray[float32]]:
    '''Groups vert indices based on unique weight values. 
    This limits the calls to the Blender API vertex_group.add() function.'''
    unique_weights, inverse_indices = np.unique(weights, return_inverse=True)

    sort_order     = np.argsort(inverse_indices)
    sorted_groups  = inverse_indices[sort_order]
    sorted_indices = indices[sort_order]

    split_points    = np.where(np.diff(sorted_groups))[0] + 1
    grouped_indices = np.split(sorted_indices, split_points)

    return grouped_indices, unique_weights

def remove_vertex_groups(obj: Object, skeleton: Object, prefix: str | tuple[str, ...], store_yas=False) -> list[str]:
        """Can remove any vertex group and add weights to parent group. 
        Returns the groups that were left alone because the skeleton has no parent bone for them."""
        group_to_parent, skipped = _get_group_parent(obj, skeleton, prefix)
        source_groups            = list(group_to_parent.keys())

        if not source_groups:
            return skipped

        source_names  = [obj.vertex_groups[idx].name for idx in source_groups]
        weight_matrix = _create_weight_matrix(obj, group_to_parent, source_groups)

        # Adds weights to parent
        updated_groups = {value for value in group_to_parent.values()}
        for v_group in obj.vertex_groups:
            if v_group.index not in updated_groups:
                continue

            add_to_vgroup(weight_matrix, v_group)

        if store_yas:
            _store_yas_groups(obj, group_to_parent, weight_matrix)

        # Removed by name, removing while iterating the vertex groups can skip groups.
        for name in source_names:
            obj.vertex_groups.remove(obj.vertex_groups[name])
        
        return skipped

def _store_yas_groups(obj: Object, group_to_parent: dict[int, int], weight_matrix: NDArray[float32]) -> None:
    yas_groups: Iterable[YASGroup] = obj.yas.v_groups
    
    existing_groups = [group.name for group in yas_groups]
    for group, parent in group_to_parent.items():
        group_name = obj.vertex_groups[group].name
        if group_name in existing_groups:
            continue

        indices = np.flatnonzero(weight_matrix[:, group])
        weights = weight_matrix[:, group][indices]

        new_group: YASGroup  = yas_groups.add()
        new_group.name       = group_name
        # The group that actually received the weights, not necessarily the direct bone parent.
        new_group.parent     = obj.vertex_groups[parent].name

        if len(indices) == 0:
            continue

        for _ in range(len(indices)):
            new_group.vertices.add()

        new_group.vertices.foreach_set("idx", indices)
        new_group.vertices.foreach_set("value", weights)

def restore_yas_groups(obj: Object, names: Iterable[str] | None = None) -> None:
    """Restores all stored groups, or only the ones in names, and removes them from storage."""
    yas_groups: Iterable[YASGroup] = obj.yas.v_groups
    yas_to_parent = {v_group.name: v_group.parent for v_group in yas_groups}

    def weighted_parent(name: str) -> str:
        # Older storage saved the direct bone parent, which can itself be a stored group.
        # Its weights were merged into the first ancestor that was kept on the mesh.
        parent  = yas_to_parent[name]
        visited = {name}
        while parent in yas_to_parent and parent not in visited:
            visited.add(parent)
            parent = yas_to_parent[parent]
        return parent

    restored = [idx for idx, v_group in enumerate(yas_groups) if names is None or v_group.name in names]
    for idx in restored:
        v_group   = yas_groups[idx]
        yas_group = obj.vertex_groups.get(v_group.name) or obj.vertex_groups.new(name=v_group.name)
        verts     = len(v_group.vertices)
        if not verts:
            continue

        indices = np.zeros(verts, dtype=uint32)
        weights = np.zeros(verts, dtype=float32)

        v_group.vertices.foreach_get("idx", indices)
        v_group.vertices.foreach_get("value", weights)

        grouped_indices, unique_weights = group_weights(indices, weights)

        parent = obj.vertex_groups.get(weighted_parent(v_group.name))
        for array_idx, vert_indices in enumerate(grouped_indices):
            vert_indices = vert_indices.tolist()
            if parent:
                parent.add(vert_indices, unique_weights[array_idx], type='SUBTRACT')
            yas_group.add(vert_indices, unique_weights[array_idx], type='REPLACE')
    
    for idx in reversed(restored):
        yas_groups.remove(idx)

def _get_group_parent(obj: Object, skeleton: Object, prefix: str | tuple[str, ...]) -> tuple[dict[int, int | str], list[str]]:
    group_to_parent = {}
    skipped         = []

    for v_group in obj.vertex_groups:
        if not v_group.name.startswith(prefix):
            continue
        
        bone   = skeleton.data.bones.get(v_group.name)
        parent = bone.parent if bone else None
        # Parents that are removed as well pass their weights on, so skip straight to the first kept ancestor.
        while parent and parent.name.startswith(prefix):
            parent = parent.parent

        if parent is None:
            skipped.append(v_group.name)
            continue

        parent_group = obj.vertex_groups.get(parent.name)
        if parent_group:
            group_to_parent[v_group.index] = parent_group.index
        else:
            group_to_parent[v_group.index] = parent.name
    
    return group_to_parent, skipped

def _create_weight_matrix(obj: Object, group_to_parent: dict[int, int | str], source_groups: list[int]) -> NDArray[float32]:
    verts          = len(obj.data.vertices)
    missing_groups = {value for value in group_to_parent.values() if isinstance(value, str)}
    max_groups     = len(obj.vertex_groups) + len(missing_groups)
    weight_matrix  = np.zeros((verts, max_groups), dtype=float32)
    
    if len(source_groups) == 1:
        bm = bmesh.new()
        bm.from_mesh(obj.data)

        group_idx = source_groups[0]
        deform_layer = bm.verts.layers.deform.active
        for vert_idx, vert in enumerate(bm.verts):
            weight_matrix[vert_idx, group_idx] = vert[deform_layer].get(group_idx, 0)

        bm.free()
    else:
        for vertex_idx, vertex in enumerate(obj.data.vertices):
            for group in vertex.groups:
                if group.group in source_groups:
                    weight_matrix[vertex_idx, group.group] = group.weight

    _create_missing_parents(obj, group_to_parent)

    for group_idx, parent in group_to_parent.items():
        weight_matrix[:, parent] += weight_matrix[:, group_idx]

    return weight_matrix

def _create_missing_parents(obj: Object, group_to_parent: dict[int, int | str]) -> None:
    created: dict[str, int] = {}
    for group_idx, parent in group_to_parent.items():
        if not isinstance(parent, str):
            continue
        if parent not in created:
            created[parent] = obj.vertex_groups.new(name=parent).index

        group_to_parent[group_idx] = created[parent]


def combine_v_groups(obj: Object, v_groups: list[int]) -> VertexGroup:
    bm = bmesh.new()
    bm.from_mesh(obj.data)

    deform_layer = bm.verts.layers.deform.active

    vertex_weights = np.zeros((len(bm.verts), len(v_groups)), dtype=np.float32)
    for idx, vert in enumerate(bm.verts):
        for col_idx, group_idx in enumerate(v_groups):
            vertex_weights[idx, col_idx] = vert[deform_layer].get(group_idx, 0)
    
    bm.free()

    indices = np.where(np.any(vertex_weights > 0, axis=1))[0]
    indices = indices.tolist()

    combined_group = obj.vertex_groups.new()
    combined_group.add(indices, 1.0, type='REPLACE')

    return combined_group