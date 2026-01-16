"""
Load Tables per HK Code 2011 (Tables 3.1, 3.2) and Exposure Covers (Table 4.1)
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class LiveLoadEntry:
    """Single live load entry from HK Code Table 3.2"""
    code: str
    description: str
    qk: Optional[float] = None      # Fixed load value (kPa)
    per_m: Optional[float] = None   # Load per meter height (kPa/m)
    min_value: Optional[float] = None  # Minimum value for height-dependent loads

    def get_load(self, height: float = 0) -> float:
        """Calculate live load, considering height if applicable"""
        if self.qk is not None:
            return self.qk
        elif self.per_m is not None:
            load = self.per_m * height
            if self.min_value is not None:
                return max(load, self.min_value)
            return load
        return 0.0

    @property
    def is_height_dependent(self) -> bool:
        return self.per_m is not None


# Live Load Table per HK Code 2011 Tables 3.1 and 3.2
LIVE_LOAD_TABLE = {
    # Class 1: Domestic and residential floors
    "1": {
        "name": "Domestic and residential floors",
        "loads": [
            LiveLoadEntry("1.1", "Domestic uses", qk=2.0),
            LiveLoadEntry("1.2", "Dormitories", qk=2.0),
            LiveLoadEntry("1.3", "Hotel rooms", qk=2.0),
            LiveLoadEntry("1.4", "Hospital wards", qk=2.0),
            LiveLoadEntry("1.5", "Bathrooms", qk=2.0),
            LiveLoadEntry("1.6", "Pantries", qk=2.0),
            LiveLoadEntry("1.7", "Kitchens", qk=2.0),
        ]
    },
    # Class 2: Offices and non-industrial workplaces
    "2": {
        "name": "Offices and non-industrial workplaces",
        "loads": [
            LiveLoadEntry("2.1", "Medical consulting rooms", qk=2.5),
            LiveLoadEntry("2.2", "Hospital operating theatres", qk=2.5),
            LiveLoadEntry("2.3", "Laboratories", qk=3.0),
            LiveLoadEntry("2.4", "Light workrooms", qk=3.0),
            LiveLoadEntry("2.5", "Offices for general use", qk=3.0),
            LiveLoadEntry("2.6", "Electrical installations", qk=3.0),
            LiveLoadEntry("2.7", "Meter rooms", qk=3.0),
            LiveLoadEntry("2.8", "Pantries", qk=3.0),
            LiveLoadEntry("2.9", "Banking halls", qk=4.0),
            LiveLoadEntry("2.10", "Kitchens and laundries", qk=4.0),
            LiveLoadEntry("2.11", "Projection rooms", qk=5.0),
        ]
    },
    # Class 3: Areas where people congregate
    "3": {
        "name": "Areas where people congregate",
        "loads": [
            LiveLoadEntry("3.1", "Childcare centers", qk=2.5),
            LiveLoadEntry("3.2", "Classrooms", qk=3.0),
            LiveLoadEntry("3.3", "Computer rooms", qk=3.0),
            LiveLoadEntry("3.4", "Recreational areas", qk=3.0),
            LiveLoadEntry("3.5", "Massage rooms", qk=3.0),
            LiveLoadEntry("3.6", "Reading rooms", qk=3.0),
            LiveLoadEntry("3.7", "Cafes and amusement centers", qk=4.0),
            LiveLoadEntry("3.8", "Restaurants and bars", qk=4.0),
        ]
    },
    # Class 4: Shopping areas
    "4": {
        "name": "Shopping areas",
        "loads": [
            LiveLoadEntry("4.1", "Department stores and shops", qk=5.0),
        ]
    },
    # Class 5: Storage and industrial uses
    "5": {
        "name": "Storage and industrial uses",
        "loads": [
            LiveLoadEntry("5.1", "Library rooms", qk=5.0),
            LiveLoadEntry("5.2", "Offices for storage", qk=5.0),
            LiveLoadEntry("5.3", "Refuse storage", per_m=2.5),
            LiveLoadEntry("5.4", "Stack rooms", per_m=3.5, min_value=10.0),
            LiveLoadEntry("5.5", "Cold storage", per_m=5.0, min_value=15.0),
            LiveLoadEntry("5.6", "Paper storage", per_m=8.0),
            LiveLoadEntry("5.7", "Battery rooms", per_m=10.0),
            LiveLoadEntry("5.8", "General storage", per_m=2.5),
            LiveLoadEntry("5.9", "Plant rooms", qk=7.5),
            LiveLoadEntry("5.10", "Light workshops", qk=5.0),
            LiveLoadEntry("5.11", "Medium workshops", qk=7.5),
            LiveLoadEntry("5.12", "Heavy workshops", qk=10.0),
        ]
    },
    # Class 6: Vehicular traffic areas
    "6": {
        "name": "Vehicular traffic areas",
        "loads": [
            LiveLoadEntry("6.1", "Areas for vehicular traffic", qk=5.0),
        ]
    },
    # Class 7: Roofs
    "7": {
        "name": "Roofs",
        "loads": [
            LiveLoadEntry("7.1", "Roofs (slope <= 5 deg)", qk=2.0),
            LiveLoadEntry("7.2", "Roofs (5 < slope <= 20 deg)", qk=0.75),
            LiveLoadEntry("7.3", "Roofs (20 < slope < 40 deg)", qk=0.375),
            LiveLoadEntry("7.4", "Roofs (slope >= 40 deg)", qk=0.0),
            LiveLoadEntry("7.5", "Roofs with access", qk=2.0),
            LiveLoadEntry("7.6", "Lightweight canopy", qk=0.75),
            LiveLoadEntry("7.7", "Concrete canopy", qk=2.0),
        ]
    },
    # Class 8: Affiliated building elements
    "8": {
        "name": "Affiliated building elements",
        "loads": [
            LiveLoadEntry("8.1", "Window hoods", qk=2.0),
            LiveLoadEntry("8.2", "Utility platforms", qk=4.0),
            LiveLoadEntry("8.3", "Balconies", qk=3.0),
            LiveLoadEntry("8.4", "Stairs and corridors", qk=4.0),
            LiveLoadEntry("8.5", "Maintenance catwalks", qk=1.0),
        ]
    },
}


# Exposure Covers per HK Code Table 4.1 (mm)
# Keys: Exposure class -> Concrete grade -> Cover (mm)
EXPOSURE_COVERS = {
    "1": {  # Mild
        25: 35, 30: 30, 35: 30, 40: 30, 45: 25, 50: 25, 55: 25, 60: 25
    },
    "2": {  # Moderate
        25: 40, 30: 35, 35: 35, 40: 35, 45: 30, 50: 30, 55: 30, 60: 30
    },
    "3": {  # Severe
        25: 50, 30: 50, 35: 50, 40: 50, 45: 45, 50: 45, 55: 45, 60: 45
    },
    "4": {  # Very Severe
        25: 60, 30: 60, 35: 55, 40: 55, 45: 50, 50: 50, 55: 50, 60: 50
    },
    "5": {  # Abrasive
        25: 65, 30: 65, 35: 60, 40: 60, 45: 55, 50: 55, 55: 55, 60: 55
    },
}


def get_cover(exposure_class: str, fcu: int) -> int:
    """Get concrete cover in mm based on exposure class and concrete grade"""
    if exposure_class in EXPOSURE_COVERS:
        covers = EXPOSURE_COVERS[exposure_class]
        if fcu in covers:
            return covers[fcu]
    return 35  # Default cover


def get_live_load(class_code: str, sub_code: str, height: float = 0) -> float:
    """Get live load value from tables"""
    if class_code in LIVE_LOAD_TABLE:
        for entry in LIVE_LOAD_TABLE[class_code]["loads"]:
            if entry.code == sub_code:
                return entry.get_load(height)
    return 0.0
