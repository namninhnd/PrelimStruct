from src.core.data_models import TerrainCategory, WindResult


TERRAIN_FACTORS = {
    TerrainCategory.OPEN_SEA: 1.0,
    TerrainCategory.OPEN_COUNTRY: 0.85,
    TerrainCategory.URBAN: 0.72,
    TerrainCategory.CITY_CENTRE: 0.60,
}


def calculate_hk_wind(
    total_height: float,
    building_width_x: float,
    building_width_y: float,
    terrain: TerrainCategory,
    reference_pressure: float = 3.0,
    force_coefficient: float = 1.3,
) -> WindResult:
    if total_height <= 0.0 or building_width_x <= 0.0 or building_width_y <= 0.0:
        return WindResult(reference_pressure=reference_pressure)

    sz = TERRAIN_FACTORS.get(terrain, TERRAIN_FACTORS[TerrainCategory.URBAN])
    design_pressure = reference_pressure * sz

    area_y_face = total_height * building_width_y
    base_shear_x = design_pressure * force_coefficient * area_y_face

    area_x_face = total_height * building_width_x
    base_shear_y = design_pressure * force_coefficient * area_x_face

    otm_x = base_shear_x * (2.0 / 3.0) * total_height
    otm_y = base_shear_y * (2.0 / 3.0) * total_height

    return WindResult(
        base_shear=max(base_shear_x, base_shear_y),
        base_shear_x=base_shear_x,
        base_shear_y=base_shear_y,
        overturning_moment=max(otm_x, otm_y),
        reference_pressure=design_pressure,
        lateral_system="CORE_WALL",
    )
