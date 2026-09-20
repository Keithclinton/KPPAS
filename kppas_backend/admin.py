from django import forms
from django.contrib import admin
from .models.scorecard_models import PILOT_COUNTIES
from .models.public_feedback import PublicFeedback
from .models.promise_registry import (
    PromiseSource, Promise, PromiseVerification, PromiseComment, CountyProcurementActivity,
)

@admin.register(PublicFeedback)
class PublicFeedbackAdmin(admin.ModelAdmin):
    list_display = ('name', 'county', 'sector', 'submitted_at')
    list_filter = ('county', 'sector')
    search_fields = ('name', 'county', 'comment')


# county is free-text on the model (national-level promises have none, and
# pilot counties may expand later), but manual entry from a Gazette/Hansard
# read is exactly where a typo silently splits one county's promises across
# two spellings -- so the admin form narrows it to a dropdown.
_COUNTY_CHOICES = [('', '(national -- no county)')] + [(c, c) for c in PILOT_COUNTIES]


class PromiseAdminForm(forms.ModelForm):
    county = forms.ChoiceField(choices=_COUNTY_CHOICES, required=False)

    class Meta:
        model = Promise
        fields = '__all__'


class PromiseInline(admin.TabularInline):
    """Lets an analyst log every promise found in one Gazette/Hansard edition
    against that single source, instead of creating the source, then hunting
    for it in a dropdown once per promise."""
    model = Promise
    form = PromiseAdminForm
    extra = 1
    fields = ('text', 'date_made', 'responsible_actor', 'county', 'category', 'stated_deadline', 'status')


@admin.register(PromiseSource)
class PromiseSourceAdmin(admin.ModelAdmin):
    list_display = ('title', 'source_type', 'reference', 'published_date', 'added_by', 'added_at')
    list_filter = ('source_type',)
    search_fields = ('title', 'reference', 'url')
    inlines = [PromiseInline]

    def save_model(self, request, obj, form, change):
        if not obj.added_by:
            obj.added_by = request.user
        super().save_model(request, obj, form, change)


class PromiseVerificationInline(admin.TabularInline):
    model = PromiseVerification
    extra = 0


@admin.register(Promise)
class PromiseAdmin(admin.ModelAdmin):
    form = PromiseAdminForm
    list_display = (
        'short_text', 'responsible_actor', 'county', 'category', 'status',
        'date_made', 'stated_deadline', 'source',
    )
    list_filter = ('status', 'category', 'county')
    search_fields = ('text', 'responsible_actor', 'county')
    inlines = [PromiseVerificationInline]

    @admin.display(description='Promise')
    def short_text(self, obj):
        return obj.text[:80]

    def save_model(self, request, obj, form, change):
        if not obj.logged_by:
            obj.logged_by = request.user
        super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for obj in instances:
            if isinstance(obj, PromiseVerification) and not obj.verified_by:
                obj.verified_by = request.user
            obj.save()
        formset.save_m2m()
        for deleted in formset.deleted_objects:
            deleted.delete()


@admin.register(PromiseVerification)
class PromiseVerificationAdmin(admin.ModelAdmin):
    list_display = ('promise', 'quarter', 'year', 'score', 'verified_by', 'verified_at')
    list_filter = ('score', 'year', 'quarter')
    search_fields = ('promise__text', 'notes')

    def save_model(self, request, obj, form, change):
        if not obj.verified_by:
            obj.verified_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(PromiseComment)
class PromiseCommentAdmin(admin.ModelAdmin):
    list_display = ('promise', 'name', 'short_text', 'parent', 'posted_at', 'is_hidden')
    list_filter = ('is_hidden',)
    search_fields = ('text', 'name', 'promise__text')
    actions = ['hide_comments', 'unhide_comments']

    @admin.display(description='Comment')
    def short_text(self, obj):
        return obj.text[:80]

    @admin.action(description='Hide selected comments')
    def hide_comments(self, request, queryset):
        queryset.update(is_hidden=True)

    @admin.action(description='Unhide selected comments')
    def unhide_comments(self, request, queryset):
        queryset.update(is_hidden=False)


@admin.register(CountyProcurementActivity)
class CountyProcurementActivityAdmin(admin.ModelAdmin):
    list_display = ('county', 'year', 'tenders_published', 'awards_recorded', 'has_award_gap', 'updated_at')
    list_filter = ('year',)
    search_fields = ('county',)

    @admin.display(boolean=True, description='Award gap')
    def has_award_gap(self, obj):
        return obj.has_award_gap
