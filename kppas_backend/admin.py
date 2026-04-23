from django.contrib import admin
from .models.scorecard_models import Sector, Subtopic, DashboardLink

@admin.register(Sector)
class SectorAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

@admin.register(Subtopic)
class SubtopicAdmin(admin.ModelAdmin):
    list_display = ('name', 'sector', 'description')
    list_filter = ('sector',)
    search_fields = ('name',)

@admin.register(DashboardLink)
class DashboardLinkAdmin(admin.ModelAdmin):
    list_display = ('title', 'subtopic', 'type', 'url', 'created_at')
    list_filter = ('type', 'subtopic__sector')
    search_fields = ('title', 'url')
