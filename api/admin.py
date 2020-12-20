from django.contrib import admin

from api.models import Radar

# Register your models here.
class RadarAdmin(admin.ModelAdmin):
    pass

admin.site.register(Radar, RadarAdmin)