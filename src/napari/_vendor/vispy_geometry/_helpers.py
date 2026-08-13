"""Geometry helpers vendored from vispy.

napari's Shapes layer needs constrained Delaunay triangulation and
Frenet-frame computation. Both live in vispy, which napari's Qt-free model
layer must not depend on: vispy ships no pure-python wheel, and importing
``vispy.visuals.tube`` for ``_frenet_frames`` would drag in ``vispy.gloo`` and
an OpenGL context along with it.

Everything here is pure numpy. Sources:

- ``Triangulation`` -- ``vispy/geometry/triangulation.py`` (see the sibling
  ``triangulation.py``, copied verbatim)
- ``_cross_2d`` -- ``vispy/geometry/calculations.py``, the one helper
  ``Triangulation`` imports
- ``rotate`` -- ``vispy/util/transforms.py``, used by ``_frenet_frames``
- ``_frenet_frames`` -- ``vispy/visuals/tube.py``

vispy is distributed under the 3-clause BSD licence:
Copyright (c) Vispy Development Team. All Rights Reserved.
"""

import math

import numpy as np
from numpy.linalg import norm


def _cross_2d(x, y):
    """Compute the z-component of the cross product of (arrays of) 2D vectors.

    This is meant to replicate the 2D functionality of np.cross(), which is
    deprecated in numpy 2.0.

    x and y must have broadcastable shapes, with the last dimension being 2.

    Parameters
    ----------
    x : array
        Input array 1, shape (..., 2).
    y : array
        Input array 2, shape (..., 2).

    Returns
    -------
    z : array
        z-component of cross products of x and y.

    See: https://github.com/numpy/numpy/issues/26620
    """
    if x.shape[-1] != 2 or y.shape[-1] != 2:
        raise ValueError("Input arrays must have shape (..., 2)")

    return x[..., 0] * y[..., 1] - x[..., 1] * y[..., 0]


def rotate(angle, axis, dtype=None):
    """The 4x4 rotation matrix for rotation about a vector.

    Parameters
    ----------
    angle : float
        The angle of rotation, in degrees.
    axis : ndarray
        The x, y, z coordinates of the axis direction vector.

    Returns
    -------
    M : ndarray
        Transformation matrix describing the rotation.
    """
    angle = np.radians(angle)
    assert len(axis) == 3
    x, y, z = axis / np.linalg.norm(axis)
    c, s = math.cos(angle), math.sin(angle)
    cx, cy, cz = (1 - c) * x, (1 - c) * y, (1 - c) * z
    M = np.array([[cx * x + c, cy * x - z * s, cz * x + y * s, .0],
                  [cx * y + z * s, cy * y + c, cz * y - x * s, 0.],
                  [cx * z - y * s, cy * z + x * s, cz * z + c, 0.],
                  [0., 0., 0., 1.]], dtype).T
    return M


def _frenet_frames(points, closed):
    """Calculates and returns the tangents, normals and binormals for
    the tube.
    """
    tangents = np.zeros((len(points), 3))
    normals = np.zeros((len(points), 3))

    epsilon = 0.0001

    # Compute tangent vectors for each segment
    tangents = np.roll(points, -1, axis=0) - np.roll(points, 1, axis=0)
    if not closed:
        tangents[0] = points[1] - points[0]
        tangents[-1] = points[-1] - points[-2]
    mags = np.sqrt(np.sum(tangents * tangents, axis=1))
    tangents /= mags[:, np.newaxis]

    # Get initial normal and binormal
    t = np.abs(tangents[0])

    smallest = np.argmin(t)
    normal = np.zeros(3)
    normal[smallest] = 1.

    vec = np.cross(tangents[0], normal)

    normals[0] = np.cross(tangents[0], vec)

    # Compute normal and binormal vectors along the path
    for i in range(1, len(points)):
        normals[i] = normals[i-1]

        vec = np.cross(tangents[i-1], tangents[i])
        if norm(vec) > epsilon:
            vec /= norm(vec)
            theta = np.arccos(np.clip(tangents[i-1].dot(tangents[i]), -1, 1))
            normals[i] = rotate(-np.degrees(theta),
                                vec)[:3, :3].dot(normals[i])

    if closed:
        theta = np.arccos(np.clip(normals[0].dot(normals[-1]), -1, 1))
        theta /= len(points) - 1

        if tangents[0].dot(np.cross(normals[0], normals[-1])) > 0:
            theta *= -1.

        for i in range(1, len(points)):
            normals[i] = rotate(-np.degrees(theta*i),
                                tangents[i])[:3, :3].dot(normals[i])

    binormals = np.cross(tangents, normals)

    return tangents, normals, binormals
