import numpy as np
import pytest
import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from src.geometry.transforms import camera_to_image

def test_camera_to_image():
    # points: N x 3 (x, y, z)
    points = np.array([
        [1.0, 2.0, 5.0],
        [-1.0, -2.0, 10.0]
    ])
    
    # intrinsic: 3x3
    intrinsic = np.array([
        [1000.0, 0.0, 800.0],
        [0.0, 1000.0, 450.0],
        [0.0, 0.0, 1.0]
    ])
    
    res = camera_to_image(points, intrinsic)
    pixels = res[:, :2]
    depth = res[:, 2]
    
    assert pixels.shape == (2, 2)
    assert depth.shape == (2,)
    
    assert np.allclose(depth, [5.0, 10.0])
    
    # Check pixel values
    assert np.allclose(pixels[0], [1000.0, 850.0])
    
    # N x 4 input should also work
    points_nx4 = np.array([
        [1.0, 2.0, 5.0, 1.0],
    ])
    res_4 = camera_to_image(points_nx4, intrinsic)
    pixels_4 = res_4[:, :2]
    depth_4 = res_4[:, 2]
    assert pixels_4.shape == (1, 2)
    assert depth_4.shape == (1,)
    assert depth_4[0] == 5.0
