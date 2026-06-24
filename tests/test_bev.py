import numpy as np
import pytest
import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from src.bev.simple_bev import SimpleBEVGenerator

def test_simple_bev_generation():
    points_ego = np.array([
        [10.0, 5.0, -1.0, 0.8, 0],
        [-10.0, -5.0, 2.0, 0.5, 0],
        [0.0, 0.0, 0.0, 0.9, 0]
    ])
    
    bev_gen = SimpleBEVGenerator(
        x_range=[-20, 20],
        y_range=[-20, 20],
        z_range=[-5, 5],
        resolution=0.1
    )
    
    h_map, d_map, i_map = bev_gen.generate(points_ego)
    
    # grid size should be 40 / 0.1 = 400
    assert h_map.shape == (400, 400)
    assert d_map.shape == (400, 400)
    assert i_map.shape == (400, 400)
    
    # RGB map shape
    rgb_map = bev_gen.to_rgb(h_map, d_map, i_map)
    assert rgb_map.shape == (400, 400, 3)
