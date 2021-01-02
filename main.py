#!/usr/bin/env python
""" Extract game-ready rig from animation rig

Animation rig has complex constraints, helper joints, while joint used for
binding contains the model weight information. The models and joints are
extracted maintaining only the hierarchy information. The models are then
combined and re-bind with the same weight distribution
"""

import maya.cmds as cmds
from utility import outliner, other

mesh_sources = []
mesh_targets = []


def extract_clean_bone():
    # get all root that contains joint type object
    jnt_roots = []
    jnts = cmds.ls(type='joint')
    for jnt in jnts:
        jnt_root = outliner.get_root_node(jnt, 'joint')
        if jnt_root not in jnt_roots:
            jnt_roots.append(jnt_root)

    # get all root that contains joint type object used for binding
    jnt_bind_roots = []
    for jnt_root in jnt_roots:
        if not cmds.listRelatives(jnt_root, ad=1):
            jnt_chain = [jnt_root]
        else:
            jnt_chain = [jnt_root] + cmds.listRelatives(jnt_root, ad=1)

        for jnt in jnt_chain:
            if cmds.listConnections(jnt, type='dagPose'):
                jnt_bind_roots.append(jnt_root)
                break

    # duplicate joints into a group remaining hierarchy
    jnt_grp = cmds.group(name='clean_joint_group', empty=1)
    for jnt_root in jnt_bind_roots:
        jnt_root_dup = cmds.duplicate(jnt_root, ic=0, rc=1)[0]
        cmds.parent(jnt_root_dup, jnt_grp)

        # multiple shape under transform cause error in deleting, re-parenting
        outliner.delete_hierarchy_shape(jnt_root_dup)
        outliner.delete_hierarchy_except_type(jnt_root_dup, 'joint')

    # joint clean-up
    for jnt in cmds.listRelatives(jnt_grp, ad=1):
        other.restore_channel(jnt)
        cmds.makeIdentity(jnt, apply=1, t=0, r=1, s=1, n=0)


def extract_clean_mesh():
    # get all result mesh, original mesh used for blendshape is deleted
    meshes = cmds.ls(type='mesh')
    meshes_result = [mesh for mesh in meshes if 'Orig' not in mesh]

    # get all mesh used for binding
    clusters = cmds.ls(type='skinCluster')
    meshes_bind = set(sum([cmds.skinCluster(c, query=1, geometry=1)
                      for c in clusters
                           if cmds.skinCluster(c, query=1, geometry=1)], []))

    # get all result mesh used for binding
    global mesh_sources
    mesh_sources = list(meshes_bind.intersection(meshes_result))

    # duplicate meshes in a group
    mesh_grp = cmds.group(name='clean_mesh_group', empty=1)
    for mesh in mesh_sources:
        mesh_dup = cmds.duplicate(mesh, ic=0, rc=1, rr=0)[0]
        cmds.parent(mesh_dup, mesh_grp)

        # mesh clean-up
        other.restore_channel(mesh_dup)
        cmds.makeIdentity(mesh_dup, apply=1, t=1, r=1, s=1, n=0)
        cmds.delete(mesh_dup, constructionHistory=1)

        mesh_targets.append(outliner.get_shape_from_transform
                            (mesh_dup, check_unique_child=0)[0])


def transfer_weight():
    # bind skin to create a skin cluster
    joints = cmds.listRelatives('clean_joint_group', children=1)
    meshes = cmds.listRelatives('clean_mesh_group', ad=1)
    mesh_transforms = [mesh for mesh in meshes
                       if cmds.objectType(mesh, isType='transform')]
    for mesh in mesh_transforms:
        cmds.skinCluster(joints, mesh)

    # copy weight from original skin to target
    if len(mesh_sources) == len(mesh_targets):
        for index, mesh in enumerate(mesh_targets):
            cmds.select(mesh_sources[index], mesh_targets[index])
            cmds.copySkinWeights(noMirror=1, surfaceAssociation='closestPoint',
                                 influenceAssociation='closestJoint',
                                 normalize=1)

    # combine all skinned mesh
    mesh_shapes = [outliner.get_shape_from_transform(transform,
                                                     check_unique_child=0)[0]
                   for transform in mesh_transforms]
    if len(mesh_shapes) > 1:
        mesh_unite = cmds.polyUniteSkinned(mesh_shapes, ch=0)[0]
        cmds.rename(mesh_unite, 'unite_mesh')
        cmds.delete(cmds.ls('clean_mesh_group'))
        mesh_grp = cmds.group(name='clean_mesh_group', empty=1)
        cmds.parent('unite_mesh', mesh_grp)

