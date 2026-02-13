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
    num_floors: int = 0,
    story_height: float = 0.0,
) -> WindResult:
    if total_height <= 0.0 or building_width_x <= 0.0 or building_width_y <= 0.0:
        return WindResult(
            reference_pressure=reference_pressure,
            code_reference="HK Wind Code 2019 - Invalid geometry (zero dimensions)",
        )

    sz = TERRAIN_FACTORS.get(terrain, TERRAIN_FACTORS[TerrainCategory.URBAN])
    design_pressure = reference_pressure * sz

    area_y_face = total_height * building_width_y
    base_shear_x = design_pressure * force_coefficient * area_y_face

    area_x_face = total_height * building_width_x
    base_shear_y = design_pressure * force_coefficient * area_x_face

    otm_x = base_shear_x * (2.0 / 3.0) * total_height
    otm_y = base_shear_y * (2.0 / 3.0) * total_height

    floor_elevations = []
    floor_wind_x = []
    floor_wind_y = []
    floor_torsion_z = []

    if num_floors > 0 and story_height > 0.0:
        for floor_idx in range(num_floors):
            elevation = (floor_idx + 1) * story_height
            floor_elevations.append(elevation)

            floor_area_y = story_height * building_width_y
            floor_wx = design_pressure * force_coefficient * floor_area_y
            floor_wind_x.append(floor_wx)

            floor_area_x = story_height * building_width_x
            floor_wy = design_pressure * force_coefficient * floor_area_x
            floor_wind_y.append(floor_wy)

            eccentricity = 0.05 * max(building_width_x, building_width_y)
            floor_wtz = max(floor_wx, floor_wy) * eccentricity
            floor_torsion_z.append(floor_wtz)

    terrain_name = {
        TerrainCategory.OPEN_SEA: "Open Sea",
        TerrainCategory.OPEN_COUNTRY: "Open Country",
        TerrainCategory.URBAN: "Urban",
        TerrainCategory.CITY_CENTRE: "City Centre",
    }.get(terrain, "Urban")

    code_ref = (
        f"HK Wind Code 2019 - Simplified Analysis | "
        f"Terrain: {terrain_name} (Sz={sz:.2f}) | "
        f"Cf={force_coefficient:.2f} | "
        f"q_ref={reference_pressure:.2f} kPa"
    )

    return WindResult(
        base_shear=max(base_shear_x, base_shear_y),
        base_shear_x=base_shear_x,
        base_shear_y=base_shear_y,
        overturning_moment=max(otm_x, otm_y),
        reference_pressure=reference_pressure,
        lateral_system="CORE_WALL",
        code_reference=code_ref,
        terrain_factor=sz,
        force_coefficient=force_coefficient,
        design_pressure=design_pressure,
        floor_elevations=floor_elevations,
        floor_wind_x=floor_wind_x,
        floor_wind_y=floor_wind_y,
        floor_torsion_z=floor_torsion_z,
    )
