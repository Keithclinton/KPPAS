from django.contrib import admin
from .models.scorecard_models import Sector, Subtopic, DashboardLink, DataSource, CountyScore
from .models.public_feedback import PublicFeedback

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

@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    list_display = ('label', 'source_type', 'trust_tier', 'uploaded_by', 'imported_at')
    list_filter = ('source_type', 'trust_tier')
    search_fields = ('label', 'origin_url')

@admin.register(CountyScore)
class CountyScoreAdmin(admin.ModelAdmin):
    list_display = ('county', 'sector', 'quarter', 'year', 'value', 'target', 'score', 'status', 'data_source')
    list_filter = ('status', 'county', 'sector', 'data_source__trust_tier')
    search_fields = ('county', 'sector')

@admin.register(PublicFeedback)
class PublicFeedbackAdmin(admin.ModelAdmin):
    list_display = ('name', 'county', 'rating', 'submitted_at')
    list_filter = ('county', 'rating')
    search_fields = ('name', 'county', 'comment')
