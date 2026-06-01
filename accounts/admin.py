from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, School, Class, StudentProfile, Subject, Mark, ReportCard, TermConfig, Transcript, Activity

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'get_full_name', 'role', 'school', 'is_active')
    list_filter = ('role', 'is_active', 'school')
    fieldsets = UserAdmin.fieldsets + (
        ('Role & Contact', {'fields': ('role', 'school', 'phone_number')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Role & Contact', {'fields': ('role', 'school', 'phone_number')}),
    )

admin.site.register(School)
admin.site.register(Class)
admin.site.register(StudentProfile)
admin.site.register(Subject)
admin.site.register(Mark)


@admin.register(ReportCard)
class ReportCardAdmin(admin.ModelAdmin):
    list_display = ('student', 'term', 'validated', 'validated_by', 'validated_at',
                    'print_permission', 'print_permission_granted_by')
    list_filter = ('term', 'validated', 'print_permission')
    search_fields = ('student__user__first_name', 'student__user__last_name', 'student__user__username')
    readonly_fields = ('validated_by', 'validated_at', 'print_permission_granted_by', 'print_permission_granted_at')
    fieldsets = (
        ('Report Card Details', {
            'fields': ('student', 'term')
        }),
        ('Validation Information', {
            'fields': ('validated', 'validated_by', 'validated_at'),
            'description': 'Validation status and auditing information'
        }),
        ('Print Permission', {
            'fields': ('print_permission', 'print_permission_granted_by', 'print_permission_granted_at'),
            'description': 'Hard-copy print permission'
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        readonly = list(self.readonly_fields)
        if obj and obj.validated:
            readonly.append('validated')
        return readonly


@admin.register(TermConfig)
class TermConfigAdmin(admin.ModelAdmin):
    list_display = ('school', 'term', 'marks_deadline', 'closing_date', 'closing_time', 'is_active', 'created_at')
    list_filter = ('school', 'is_active', 'term')
    search_fields = ('school__name', 'term')


@admin.register(Transcript)
class TranscriptAdmin(admin.ModelAdmin):
    list_display = ('student', 'generated_by', 'validated', 'validated_by', 'print_permission', 'created_at')
    list_filter = ('validated', 'print_permission')
    search_fields = ('student__user__first_name', 'student__user__last_name')
    readonly_fields = ('generated_by', 'validated_by', 'validated_at')


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ('name', 'school_class', 'max_score', 'created_by', 'created_at')
    list_filter = ('school_class',)
    search_fields = ('name', 'school_class__name')
