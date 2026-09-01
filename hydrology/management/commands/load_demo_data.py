import random

from django.contrib.gis.geos import LineString, MultiPolygon, Point, Polygon
from django.core.management.base import BaseCommand

from exposure.models import Building, CriticalFacility, FloodEvent, Road, Ward
from hydrology.models import Basin, River

BASE_LON = 36.78
BASE_LAT = -1.22
STEP_LON = 0.035
STEP_LAT = 0.0175


def square(lon, lat, half_deg):
    return Polygon(
        [
            (lon - half_deg, lat - half_deg),
            (lon + half_deg, lat - half_deg),
            (lon + half_deg, lat + half_deg),
            (lon - half_deg, lat + half_deg),
            (lon - half_deg, lat - half_deg),
        ],
        srid=4326,
    )


class Command(BaseCommand):
    help = "Load synthetic demo geodata (Nairobi area) for the MVP pipeline."

    def handle(self, *args, **options):
        random.seed(42)

        FloodEvent.objects.all().delete()
        Basin.objects.all().delete()
        Ward.objects.all().delete()
        Road.objects.all().delete()
        Building.objects.all().delete()
        CriticalFacility.objects.all().delete()

        basins = []
        river_names = ["Nairobi River (upper)", "Mathare River", "Gitathuru River", "Ngong River", "Nairobi River (lower)"]
        for i in range(5):
            lon = BASE_LON + i * STEP_LON
            lat = BASE_LAT - i * STEP_LAT
            basins.append(
                Basin.objects.create(
                    hybas_id=f"demo-{i + 1}",
                    name=f"{river_names[i]} corridor {i + 1}",
                    geom=MultiPolygon(square(lon, lat, 0.016), srid=4326),
                    upstream_area_km2=40.0 * (2 ** i),
                    response_time_h=4.0 + i * 1.5,
                )
            )
        for i in range(4):
            basins[i].downstream = basins[i + 1]
            basins[i].save(update_fields=["downstream"])

        river_lines = []
        for i, basin in enumerate(basins):
            lon = BASE_LON + i * STEP_LON
            lat = BASE_LAT - i * STEP_LAT
            coords = [
                (lon, lat),
                (lon + STEP_LON / 2, lat - 0.004),
                (lon + STEP_LON, lat - STEP_LAT),
            ]
            river_lines.append(coords)
            River.objects.create(
                name=river_names[i],
                basin=basin,
                geom=LineString(coords, srid=4326),
                bankfull_q_m3s=30.0 + 40.0 * i,
            )

        # Wards in the February-March 2026 Nairobi flood corridor; populations
        # are stylized ward-scale figures, vulnerability reflects informal
        # settlement density (Mathare, Mukuru, Kibra are highly vulnerable).
        ward_defs = [
            ("WD-01", "Mathare", 36.80, -1.27, 180000, 0.80),
            ("WD-02", "Mukuru kwa Njenga", 36.90, -1.29, 220000, 0.85),
            ("WD-03", "Kibra", 36.79, -1.32, 250000, 0.82),
            ("WD-04", "Embakasi South B", 36.90, -1.23, 120000, 0.55),
        ]
        for code, name, lon, lat, pop, vuln in ward_defs:
            Ward.objects.create(
                code=code,
                name=name,
                county="Nairobi",
                population=pop,
                vulnerability_index=vuln,
                geom=MultiPolygon(square(lon, lat, 0.03), srid=4326),
            )

        road_defs = [
            ("demo-road-mombasa", "trunk", [(36.75, -1.305), (36.98, -1.305)]),
            ("demo-road-uhuru", "primary", [(36.79, -1.29), (36.98, -1.29)]),
            ("demo-road-thika", "trunk", [(36.80, -1.20), (36.95, -1.20)]),
            ("demo-road-ring", "secondary", [(36.77, -1.25), (36.77, -1.35)]),
            ("demo-road-outer", "primary", [(36.90, -1.19), (36.90, -1.36)]),
            ("demo-road-landhies", "secondary", [(36.82, -1.285), (36.93, -1.285)]),
        ]
        for osm_id, hclass, line in road_defs:
            Road.objects.create(osm_id=osm_id, highway=hclass, geom=LineString(line, srid=4326))

        def river_side_point():
            """A point within ~200m of a random river segment."""
            line = random.choice(river_lines)
            seg = random.randrange(len(line) - 1)
            (x0, y0), (x1, y1) = line[seg], line[seg + 1]
            t = random.random()
            return (
                x0 + (x1 - x0) * t + random.uniform(-0.002, 0.002),
                y0 + (y1 - y0) * t + random.uniform(-0.002, 0.002),
            )

        for i in range(120):
            if random.random() < 0.7:
                lon, lat = river_side_point()
            else:
                lon = random.uniform(36.75, 36.95)
                lat = random.uniform(-1.33, -1.19)
            roll = random.random()
            if roll < 0.7:
                bldg_type, value = "residential", 45000.0
            elif roll < 0.9:
                bldg_type, value = "commercial", 75000.0
            else:
                bldg_type, value = "industrial", 60000.0
            Building.objects.create(
                osm_id=f"demo-b{i + 1}",
                bldg_type=bldg_type,
                footprint=square(lon, lat, 0.00025),
                area_m2=random.uniform(80.0, 400.0),
                replacement_value_per_m2=value,
            )

        facilities = [
            ("Mama Lucy Kibaki Hospital", "hospital", 36.90, -1.315),
            ("Mbagathi County Hospital", "hospital", 36.775, -1.305),
            ("Pumwani Maternity Hospital", "hospital", 36.845, -1.285),
            ("Mathare North Health Centre", "school", 36.865, -1.245),
            ("Riverside School", "school", 36.823, -1.246),
            ("Kangemi Water Works", "water_works", 36.77, -1.30),
            ("Dandora Water Works", "water_works", 36.952, -1.306),
            ("Ruaraka Substation", "substation", 36.85, -1.24),
        ]
        for name, fclass, lon, lat in facilities:
            CriticalFacility.objects.create(name=name, fclass=fclass, geom=Point(lon, lat, srid=4326))

        self.stdout.write(
            self.style.SUCCESS(
                f"Loaded {Basin.objects.count()} basins, {River.objects.count()} rivers, "
                f"{Ward.objects.count()} wards, {Road.objects.count()} roads, "
                f"{Building.objects.count()} buildings, {CriticalFacility.objects.count()} facilities."
            )
        )
