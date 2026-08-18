from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Generic, TypeVar, cast

import numpy as np
import pint
from vispy.visuals.transforms import MatrixTransform

from napari._canvas import compute_layer_transforms
from napari._vispy.utils.gl import BLENDING_MODES, get_max_texture_sizes
from napari.layers import Layer
from napari.utils.events import disconnect_events

if TYPE_CHECKING:
    from vispy.scene import VisualNode

    from napari._vispy.utils.qt_font import FontInfo

_L = TypeVar('_L', bound=Layer)


class VispyBaseLayer(ABC, Generic[_L]):
    """Base object for individual layer views

    Meant to be subclassed.

    Parameters
    ----------
    layer : napari.layers.Layer
        Layer model.
    node : vispy.scene.VisualNode
        Central node with which to interact with the visual.

    Attributes
    ----------
    layer : napari.layers.Layer
        Layer model.
    node : vispy.scene.VisualNode
        Central node with which to interact with the visual.
    scale : sequence of float
        Scale factors for the layer visual in the scenecanvas.
    translate : sequence of float
        Translation values for the layer visual in the scenecanvas.
    MAX_TEXTURE_SIZE_2D : int
        Max texture size allowed by the vispy canvas during 2D rendering.
    MAX_TEXTURE_SIZE_3D : int
        Max texture size allowed by the vispy canvas during 2D rendering.


    Notes
    -----
    _master_transform : vispy.visuals.transforms.MatrixTransform
        Transform positioning the layer visual inside the scenecanvas.
    """

    layer: _L

    def __init__(
        self, layer: _L, node: VisualNode, font_info: FontInfo
    ) -> None:
        super().__init__()
        self.events = None  # Some derived classes have events.

        self.layer = layer
        self.font_info = font_info
        self._array_like = False
        self.node = node
        self.first_visible = False
        self._world_units = layer.units
        self._world_to_layer_units_scale = (1,) * layer.ndim

        (
            self.MAX_TEXTURE_SIZE_2D,
            self.MAX_TEXTURE_SIZE_3D,
        ) = get_max_texture_sizes()

        self.layer.events.refresh.connect(self._on_refresh_change)
        self.layer.events.set_data.connect(self._on_data_change)
        self.layer.events.visible.connect(self._on_visible_change)
        self.layer.events.opacity.connect(self._on_opacity_change)
        self.layer.events.blending.connect(self._on_blending_change)
        self.layer.events.scale.connect(self._on_matrix_change)
        self.layer.events.translate.connect(self._on_matrix_change)
        self.layer.events.rotate.connect(self._on_matrix_change)
        self.layer.events.shear.connect(self._on_matrix_change)
        self.layer.events.affine.connect(self._on_matrix_change)
        self.layer.events.units.connect(self._recalculate_units_scale)
        self.layer.experimental_clipping_planes.events.connect(
            self._on_experimental_clipping_planes_change
        )

    @property
    def world_units(self) -> tuple[pint.Unit, ...]:
        return self._world_units

    @world_units.setter
    def world_units(self, value: tuple[pint.Unit, ...] | None) -> None:
        if value is None:
            self._world_units = self.layer.units
            self._world_to_layer_units_scale = (1,) * self.layer.ndim
        else:
            self._world_units = value[-self.layer.ndim :]
            self._recalculate_units_scale()
        self._on_matrix_change()

    def _recalculate_units_scale(self):
        """Calculate the scale factor between the layer units and the world units.

        This is used to convert the layer's data coordinates to world coordinates.
        If self._units is None, then the scale is set to 1 for all dimensions.
        """
        reg = pint.get_application_registry()
        self._world_to_layer_units_scale = tuple(
            reg.get_base_units(y)[0] / reg.get_base_units(x)[0]
            for x, y in zip(self._world_units, self.layer.units, strict=False)
        )

    @property
    def _master_transform(self):
        """vispy.visuals.transforms.MatrixTransform:
        Central node's firstmost transform.
        """
        # whenever a new parent is set, the transform is reset
        # to a NullTransform so we reset it here
        if not isinstance(self.node.transform, MatrixTransform):
            self.node.transform = MatrixTransform()

        return self.node.transform

    @property
    def translate(self):
        """sequence of float: Translation values."""
        return self._master_transform.matrix[-1, :]

    @property
    def scale(self):
        """sequence of float: Scale factors."""
        matrix = self._master_transform.matrix[:-1, :-1]
        _, upper_tri = np.linalg.qr(matrix)
        return np.diag(upper_tri).copy()

    @property
    def order(self):
        """int: Order in which the visual is drawn in the scenegraph.

        Lower values are closer to the viewer.
        """
        return self.node.order

    @order.setter
    def order(self, order):
        self.node.order = order
        self._on_blending_change()

    @abstractmethod
    def _on_data_change(self):
        raise NotImplementedError

    def _on_refresh_change(self):
        self.node.update()

    def _on_visible_change(self):
        self.node.visible = self.layer.visible

    def _on_opacity_change(self):
        self.node.opacity = self.layer.opacity

    def _on_blending_change(self, event=None):
        blending = self.layer.blending
        blending_kwargs = cast(dict, BLENDING_MODES[blending]).copy()

        if self.first_visible:
            # if the first layer, then we should blend differently
            # the goal is to prevent pathological blending with canvas
            # for minimum, use the src color, ignore alpha & canvas
            if blending == 'minimum':
                src_color_blending = 'one'
                dst_color_blending = 'zero'
            # for additive, use the src alpha and blend to black
            elif blending == 'additive':
                src_color_blending = 'src_alpha'
                dst_color_blending = 'zero'
            # for all others, use translucent blending
            else:
                src_color_blending = 'src_alpha'
                dst_color_blending = 'one_minus_src_alpha'
            blending_kwargs = {
                'depth_test': blending_kwargs['depth_test'],
                'cull_face': False,
                'blend': True,
                'blend_func': (
                    src_color_blending,
                    dst_color_blending,
                    'one',
                    'one',
                ),
                'blend_equation': 'func_add',
            }

        self.node.set_gl_state(**blending_kwargs)
        self.node.update()

    def _on_matrix_change(self):
        # If the layer's dimensionality changed (e.g., data swapped from 2D
        # to 3D), _world_to_layer_units_scale reflects the old ndim
        # and cannot be indexed with the new dims_displayed values.  Refresh
        # both cached unit tracking fields to match the current layer.
        # This is a stateful cache-invalidation concern specific to this
        # visual instance, so it stays here rather than in
        # compute_layer_transforms, which only ever reads an
        # already-current world_to_layer_units_scale.
        if len(self._world_to_layer_units_scale) != self.layer.ndim:
            self._world_units = self.layer.units
            self._world_to_layer_units_scale = (1,) * self.layer.ndim

        affine_matrix, child_matrix = compute_layer_transforms(
            self.layer, self._world_to_layer_units_scale, self._array_like
        )
        self._master_transform.matrix = affine_matrix

        for child in self.node.children:
            child.transform.matrix = child_matrix

    def _on_experimental_clipping_planes_change(self):
        if hasattr(self.node, 'clipping_planes') and hasattr(
            self.layer, 'experimental_clipping_planes'
        ):
            # invert axes because vispy uses xyz but napari zyx
            self.node.clipping_planes = (
                self.layer.experimental_clipping_planes.as_array()[..., ::-1]
            )

    def _on_camera_move(self, event=None):
        return

    def reset(self):
        self._on_visible_change()
        self._on_opacity_change()
        self._on_blending_change()
        self._on_matrix_change()
        self._on_experimental_clipping_planes_change()
        self._on_camera_move()

    def _on_poll(self, event=None):
        """Called when camera moves, before we are drawn.

        Optionally called for some period once the camera stops, so the
        visual can finish up what it was doing, such as loading data into
        VRAM or animating itself.
        """

    def close(self):
        """Vispy visual is closing."""
        disconnect_events(self.layer.events, self)
        self.node.transform = MatrixTransform()
        self.node.parent = None
