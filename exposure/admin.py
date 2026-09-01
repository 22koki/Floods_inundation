from django.contrib.gis import admin

from .models import Building, CriticalFacility, FloodEvent, FloodPolygon, Road, Ward

admin.site.register(Ward, admin.GISModelAdmin)
admin.site.register(Road, admin.GISModelAdmin)
admin.site.register(Building, admin.GISModelAdmin)
admin.site.register(CriticalFacility, admin.GISModelAdmin)
admin.site.register(FloodPolygon, admin.GISModelAdmin)
admin.site.register(FloodEvent)
