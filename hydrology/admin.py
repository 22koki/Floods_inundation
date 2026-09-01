from django.contrib.gis import admin

from .models import Basin, DischargeForecast, ForecastRun, River

admin.site.register(Basin, admin.GISModelAdmin)
admin.site.register(River, admin.GISModelAdmin)
admin.site.register(ForecastRun)
admin.site.register(DischargeForecast)
