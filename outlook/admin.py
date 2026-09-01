from django.contrib import admin

from .models import ScenarioRun, SeasonalOutlook, SeasonalWardRisk

admin.site.register(SeasonalOutlook)
admin.site.register(ScenarioRun)
admin.site.register(SeasonalWardRisk)
