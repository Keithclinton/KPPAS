from django.contrib import admin
from django.utils import timezone
from .models.scorecard_models import Sector, Subtopic, DashboardLink, DataSource, CountyScore, RemediationAction
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

class RemediationActionInline(admin.TabularInline):
    model = RemediationAction
    extra = 0


@admin.register(CountyScore)
class CountyScoreAdmin(admin.ModelAdmin):
    list_display = (
        'county', 'sector', 'quarter', 'year', 'value', 'target', 'score', 'status',
        'data_source', 'is_signed', 'signed_by',
    )
    list_filter = ('status', 'county', 'sector', 'data_source__trust_tier')
    search_fields = ('county', 'sector')
    actions = ['sign_contracts']
    inlines = [RemediationActionInline]

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.is_signed:
            return ('target', 'signed_at', 'signed_by')
        return ('signed_at', 'signed_by')

    @admin.action(description="Sign selected contracts (locks the target)")
    def sign_contracts(self, request, queryset):
        unsigned = queryset.filter(signed_at__isnull=True)
        count = unsigned.update(signed_at=timezone.now(), signed_by=request.user)
        already_signed = queryset.count() - count
        message = f"{count} contract(s) signed and locked."
        if already_signed:
            message += f" {already_signed} were already signed and left unchanged."
        self.message_user(request, message)


@admin.register(RemediationAction)
class RemediationActionAdmin(admin.ModelAdmin):
    list_display = ('county_score', 'responsible_party', 'deadline', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('responsible_party', 'bottleneck')

@admin.register(PublicFeedback)
class PublicFeedbackAdmin(admin.ModelAdmin):
    list_display = ('name', 'county', 'rating', 'submitted_at')
    list_filter = ('county', 'rating')
    search_fields = ('name', 'county', 'comment')
