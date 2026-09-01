# FloodSentry — Reproduction Guide

## Requirements
- Python
- PostgreSQL
- PostGIS
- pip
- Git

## 1. Clone the repository
```bash
git clone <YOUR-REPOSITORY-URL>
cd Floods_inundation
```

## 2. Create the database
```bash
createdb floodsentry
psql -d floodsentry -c "CREATE EXTENSION IF NOT EXISTS postgis;"
```

Configure the database/environment variables required by the project.

## 3. Install dependencies
```bash
pip install -r requirements.txt
```

## 4. Run migrations
```bash
python manage.py migrate
```

## 5. Load reproducible demo data
```bash
python manage.py load_demo_data
```

## 6. Run the baseline/single-event simulation
```bash
python manage.py run_forecast
```

## 7. Run the advanced seasonal workflow
```bash
python manage.py run_seasonal_outlook
```

The demonstration uses three scenario levels:
- Baseline: 100 mm
- Moderate: 130 mm
- Strong: 160 mm

## 8. Start the application
```bash
python manage.py runserver
```

Open:
```text
http://localhost:8000
```

## 9. Verify API outputs
Example endpoints:
```text
/api/events/
/api/events/{id}/ward-risk/
/api/events/{id}/flood-polygons.geojson
/api/events/{id}/wards.geojson
/api/forecast/{basin}/
/api/seasonal-outlooks/latest/
```

## 10. Run tests
```bash
python manage.py test
```

## Expected result
After completing the steps above, an evaluator should be able to:
1. rebuild the Nairobi demo dataset;
2. run a flood simulation;
3. run the seasonal scenarios;
4. inspect ward-level impacts;
5. view flood polygons;
6. inspect risk rankings;
7. inspect affected/displaced population;
8. inspect infrastructure exposure;
9. inspect estimated KES losses;
10. access machine-readable outputs through the API.

> Before submission, replace `<YOUR-REPOSITORY-URL>` and verify every command on a clean environment.
