import maya.cmds as cmds


def get_root_node(obj, type_specified=None):
    """Get the root of the object in the hierarchy

    :param obj: scene object
    :param type_specified: (optional), str, restrict the root node type
    :return: root, scene object
    """

    root = None

    # check current node
    if not type_specified:
        root = obj
    else:
        if cmds.objectType(obj, isType=type_specified):
            root = obj

    # search until reached to scene root
    if not type_specified:
        while cmds.listRelatives(obj, parent=1):
            obj = cmds.listRelatives(obj, parent=1)[0]
    else:
        while cmds.listRelatives(obj, parent=1):
            parent = cmds.listRelatives(obj, parent=1)[0]
            if cmds.objectType(parent, isType=type_specified):
                root = parent
            obj = parent

    return root


def get_hierarchy_of_type(root, type_specified):
    """ get all children (including root) in hierarchy of a certain type

    :param root: single scene object
    :param type_specified: str
    :return: list
    """

    obj_list = []
    children = cmds.listRelatives(root, children=1)
    if not children:
        # the root is already at the top
        if cmds.objectType(root, isType=type_specified):
            obj_list.append(root)
    else:
        # the current object has children
        for child in children:
            obj_list += get_hierarchy_of_type(child, type_specified)

    return obj_list


def delete_hierarchy_except_type(roots, type_specified):
    """ delete all other types of objects under hierarchy of root
    note: the function cannot re-parent shape node to another transform
    but since it is always on top, it is safe to delete before hand

    :param roots: scene obj, list or single
    :param type_specified: str
    """

    if not isinstance(roots, list):
        roots = [roots]

    for root_obj in roots:
        children = cmds.listRelatives(root_obj, children=1)
        if not children:
            # the current object is the top object
            if not cmds.objectType(root_obj, isType=type_specified):
                cmds.delete(root_obj)
        else:
            # the current object has children
            for child in children:
                # the child is not top object or different type, re-parent
                if not cmds.objectType(root_obj, isType=type_specified):
                    cmds.parent(child,
                                cmds.listRelatives(root_obj, parent=1))
                delete_hierarchy_except_type(child, type_specified)

            # children moved under another parent, delete original parent
            if not cmds.objectType(root_obj, isType=type_specified):
                cmds.delete(root_obj)


def delete_hierarchy_except_node(roots, type_specified):
    """ delete all other types of objects under hierarchy of root
    note: the function cannot re-parent shape node to another transform
    but since it is always on top, it is safe to delete before hand

    :param roots: scene obj, list or single
    :param type_specified: str
    """

    if not isinstance(roots, list):
        roots = [roots]

    for root_obj in roots:
        children = cmds.listRelatives(root_obj, children=1)
        if not children:
            # the current object is the top object
            if not cmds.listConnections(root_obj, type=type_specified):
                cmds.delete(root_obj)
        else:
            # the current object has children
            for child in children:
                # the child is not top object or different type, re-parent
                if not cmds.listConnections(root_obj, type=type_specified):
                    cmds.parent(child,
                                cmds.listRelatives(root_obj, parent=1))
                delete_hierarchy_except_node(child, type_specified)

            # children moved under another parent, delete original parent
            if not cmds.listConnections(root_obj, type=type_specified):
                cmds.delete(root_obj)


def delete_hierarchy_shape(roots):
    """ Delete all shapes under the given root

    :param roots: scene object, list or single
    """

    if not isinstance(roots, list):
        roots = [roots]

    for root in roots:
        nodes = cmds.listRelatives(root, ad=1)
        shapes = cmds.ls(nodes, shapes=1)
        if shapes:
            cmds.delete(shapes)


def get_shape_from_transform(transform, enable_result_only=True,
                             check_unique_child=True):
    """ get shape nodes under the transform

    :param transform: single scene object
    :param enable_result_only: bool, get only the result shape
    :param check_unique_child: bool, check if transform has multiple shapes
    :return: list, the shape node
    """

    shapes = cmds.listRelatives(transform, shapes=1)
    shapes_result = [shape for shape in shapes if 'Orig' not in shape]

    if check_unique_child:
        assert len(shapes_result) != 0, "no shape node found"
        assert len(shapes_result) == 1, "multiple shape node found in {} " \
                                        "they are: {}"\
            .format(transform, str(shapes_result))

    if enable_result_only:
        return shapes_result
    else:
        return shapes


def get_skin_from_joint(jnt):
    """ get all skinned mesh influenced by certain joint (chain)

    :param jnt: single jnt, preferably jnt root
    :return: list, mesh transform
    """

    cls = cmds.listConnections(jnt, type='skinCluster')
    cls = list(set(cls))

    meshes = []
    for cl in cls:
        meshes += cmds.listConnections(cl, type='mesh')

    return meshes


def get_joint_from_skin(mesh):
    """ get all joints influencing certain skinned mesh

    :param mesh: scene object, could be transform or shape
    :return: list, joints
    """

    if cmds.objectType(mesh, isType='transform'):
        mesh = get_shape_from_transform(mesh)
    elif cmds.objectType(mesh, isType='mesh'):
        pass
    else:
        raise RuntimeError("skin selected is neither transform or mesh type")

    cls = cmds.listConnections(mesh, type='skinCluster')
    jnts = []
    for cl in cls:
        jnt = cmds.listConnections(cl, type='joint')
        jnt = list(set(jnt))
        jnts += jnt

    return jnts


def restore_channel(obj):
    """ restore channel box to default setting

    :param obj: scene object
    """

    kwargs = {
        'lock': 0,
        'keyable': 1,
    }

    for transform in ['t', 'r', 's']:
        for axis in ['x', 'y', 'z']:
            cmds.setAttr('{}.{}{}'.format(obj, transform, axis), **kwargs)
    cmds.setAttr('{}.visibility'.format(obj), **kwargs)
    cmds.setAttr('{}.visibility'.format(obj), 1)


def enable_joint_visibility(roots):
    """ Toggle on joint visibility by all means

    :param roots: joint roots, list or single
    """

    if not isinstance(roots, list):
        roots = [roots]

    for root in roots:
        jnts = get_hierarchy_of_type(root, 'joint')
        for jnt in jnts:
            # visibility
            try:
                cmds.setAttr('{}.v'.format(jnt), lock=0)
                cmds.setAttr('{}.v'.format(jnt), 1)
            except:
                raise RuntimeWarning("channel-box occupied, unable to unlock")

            # draw style
            cmds.setAttr('{}.drawStyle'.format(jnt), 0)

    # model panel joint show
    model_panels = cmds.getPanel(type='modelPanel')
    for model_panel in model_panels:
        cmds.modelEditor(model_panel, e=1, joints=1)

    # layer toggle on


def check_duplicates(enable_rename=True):
    """ Find all duplicated short names in scene and rename them

    :param enable_rename: bool
    """

    import re
    # Find all objects that have the same short name as another by find '|'
    duplicates = [f for f in cmds.ls() if '|' in f]
    # Sort them by hierarchy so no parent is renamed before a child.
    duplicates.sort(key=lambda obj: obj.count('|'), reverse=True)

    if not duplicates:
        print "No Duplicates"
    else:
        if enable_rename:
            name = duplicates[0]
            match_short = re.compile("[^|]*$").search(name)
            short_name = match_short.group(0)

            # extract the numeric suffix
            match_suffix = re.compile(".*[^0-9]").match(short_name)
            if match_suffix:
                suffix = match_suffix.group(0)
            else:
                suffix = short_name

            # add '#' as the suffix, maya will find the next available number
            new_name = cmds.rename(name, '{}#'.format(suffix))
            print "renamed {} to {}".format(name, new_name)
            check_duplicates(enable_rename=True)
        else:
            print "Found Duplicates"


def is_name_unique(obj):
    """ Check if the object short name is unique in the scene

    :param obj: scene object
    :return: bool
    """
    short_name = obj.split('|')
    try:
        long_names = cmds.ls(short_name[-1], l=True)
    except:
        long_names = cmds.ls('*{}'.format(short_name[-1]), l=True)

    if len(long_names) > 1:
        return 0
    else:
        return 1


def clear_joint_orientation(root):
    """ Clear out all joints' rotation to zero but keep weight

    :param root: scene object
    """

    # get all joint orientation from root
    jnts = get_hierarchy_of_type(root, 'joint')

    non_zero_jnts = []
    for jnt in jnts:
        for axis in ['x', 'y', 'z']:
            rot_value = cmds.getAttr('{}.r{}'.format(jnt, axis))
            if rot_value != 0:
                non_zero_jnts.append(jnt)
                break

    for jnt in non_zero_jnts:
        rot_x = cmds.getAttr('{}.rx'.format(jnt))
        rot_y = cmds.getAttr('{}.ry'.format(jnt))
        rot_z = cmds.getAttr('{}.rz'.format(jnt))
        print 'non-zero rotation value found in jnt: {}; ' \
              'rotation value: ({},{},{})'.format(jnt, rot_x, rot_y, rot_z)

    # unbind skin, clear rotation, re-bind skin
    meshes = get_skin_from_joint(root)
    cmds.skinCluster(meshes, edit=1, unbindKeepHistory=1)
    jnts = []
    for mesh in meshes:
        jnts += get_joint_from_skin(mesh)
    jnts = list(set(jnts))
    cmds.skinCluster(jnts, meshes)

