# v3.6 Performance Baseline

- Platform: Windows-10-10.0.26200-SP0
- Benchmark project: floors=10, bays=3x3, bay=6.0x5.0m, story=3.0m
- Options: include_core_wall=False, include_slabs=False, apply_wind_loads=False, apply_gravity_loads=True

- build_fem_model (ms): {'min': 5.105899999762187, 'avg': 6.387479999830248, 'max': 6.986599997617304}
- create_plan_view (ms): {'min': 27.77760000026319, 'avg': 61.72420000002603, 'max': 172.5138000001607}
- create_elevation_view (ms): {'min': 127.624000000651, 'avg': 139.46923999974388, 'max': 160.9532999973453}
- create_3d_view (ms): {'min': 33.658600001217565, 'avg': 42.356000001746, 'max': 68.97640000170213}
