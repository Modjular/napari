import numpy as np
import pytest

from napari._canvas._texture import fix_data_dtype, texture_dtypes


@pytest.mark.parametrize('dtype', texture_dtypes)
def test_fix_data_dtype_already_acceptable(dtype):
    data = np.zeros((4, 4), dtype=dtype)
    assert fix_data_dtype(data) is data


@pytest.mark.parametrize(
    ('dtype', 'expected'),
    [
        (np.int8, np.float32),
        (np.int32, np.float32),
        (np.uint32, np.float32),
        (np.bool_, np.uint8),
        (np.float64, np.float32),
    ],
)
def test_fix_data_dtype_coerces(dtype, expected):
    data = np.zeros((4, 4), dtype=dtype)
    fixed = fix_data_dtype(data)
    assert fixed.dtype == np.dtype(expected)


def test_fix_data_dtype_rejects_unsupported_kind():
    data = np.zeros((4, 4), dtype=np.complex64)
    with pytest.raises(TypeError, match='not allowed for texture'):
        fix_data_dtype(data)
