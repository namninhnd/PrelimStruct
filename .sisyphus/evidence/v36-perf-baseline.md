# v3.6 Performance Baseline

- Platform: Windows-10-10.0.26200-SP0
- Benchmark project: floors=10, bays=3x3, bay=6.0x5.0m, story=3.0m
- Options: include_core_wall=False, include_slabs=False, apply_wind_loads=False, apply_gravity_loads=True

- build_fem_model (ms): {'min': 6.363500000588829, 'avg': 8.434440000200993, 'max': 10.984600001393119}
- create_plan_view (ms): {'min': 25.695700000142097, 'avg': 55.36621999999625, 'max': 163.68359999978566}
- create_elevation_view (ms): {'min': 137.78789999923902, 'avg': 150.59600000022328, 'max': 164.6147999999812}
- create_3d_view (ms): {'min': 34.256400000231224, 'avg': 41.83173999990686, 'max': 61.95350000052713}
