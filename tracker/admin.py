from django.contrib import admin
from django.utils.html import format_html
from .models import Member, Transaction, Organization, OrganizationTheme, OrganizationUser


class CustomAdminMixin:
    """Mixin to add custom CSS to admin classes"""
    class Media:
        css = {
            'all': ('css/admin_custom.css',)
        }


@admin.register(Organization)
class OrganizationAdmin(CustomAdminMixin, admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active', 'member_count', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'slug']
    readonly_fields = ['created_at', 'updated_at']
    prepopulated_fields = {'slug': ('name',)}
    fields = ('name', 'slug', 'description', 'is_active', 'created_at', 'updated_at')

    def member_count(self, obj):
        count = obj.members.count()
        return format_html('<span style="color: #2563eb; font-weight: bold;">{}</span>', count)
    member_count.short_description = 'Staff Members'


@admin.register(OrganizationTheme)
class OrganizationThemeAdmin(CustomAdminMixin, admin.ModelAdmin):
    list_display = ['organization', 'primary_color_display', 'has_logo']
    list_filter = ['organization']
    search_fields = ['organization__name']
    readonly_fields = ['created_at', 'updated_at', 'color_preview']
    fieldsets = (
        ('Organization', {
            'fields': ('organization',)
        }),
        ('Branding', {
            'fields': ('logo', 'favicon', 'navbar_title')
        }),
        ('Colors', {
            'fields': ('primary_color', 'secondary_color', 'success_color', 'warning_color', 'danger_color', 'color_preview')
        }),
        ('Text & Watermark', {
            'fields': ('footer_text', 'watermark_text')
        }),
        ('Financial Settings', {
            'fields': ('default_pledge_amount', 'target_amount'),
            'description': 'Customize the default pledge amount for new members and the organization\'s collection target.'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def primary_color_display(self, obj):
        return format_html(
            '<span style="display: inline-block; width: 20px; height: 20px; background-color: {}; border-radius: 3px; margin-right: 10px;"></span>{}',
            obj.primary_color,
            obj.primary_color
        )
    primary_color_display.short_description = 'Primary Color'

    def has_logo(self, obj):
        if obj.logo:
            return format_html('<span style="color: green;">✓ Yes</span>')
        return format_html('<span style="color: red;">✗ No</span>')
    has_logo.short_description = 'Has Logo'

    def color_preview(self, obj):
        colors = [
            ('Primary', obj.primary_color),
            ('Secondary', obj.secondary_color),
            ('Success', obj.success_color),
            ('Warning', obj.warning_color),
            ('Danger', obj.danger_color),
        ]
        html = '<div style="display: flex; gap: 10px; flex-wrap: wrap;">'
        for label, color in colors:
            html += f'<div style="text-align: center;"><div style="width: 50px; height: 50px; background-color: {color}; border-radius: 5px; border: 1px solid #ccc;"></div><small>{label}</small></div>'
        html += '</div>'
        return format_html(html)
    color_preview.short_description = 'Color Preview'


@admin.register(OrganizationUser)
class OrganizationUserAdmin(CustomAdminMixin, admin.ModelAdmin):
    list_display = ['user', 'organization', 'role', 'is_active', 'joined_at']
    list_filter = ['organization', 'role', 'is_active', 'joined_at']
    search_fields = ['user__username', 'organization__name']
    readonly_fields = ['joined_at', 'updated_at']
    fieldsets = (
        ('Membership', {
            'fields': ('organization', 'user', 'role', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('joined_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Member)
class MemberAdmin(CustomAdminMixin, admin.ModelAdmin):
    list_display = ['name', 'organization', 'pledge', 'paid_total', 'remaining', 'status', 'phone', 'email']
    list_filter = ['organization', 'created_at', 'updated_at', 'is_active']
    search_fields = ['name', 'phone', 'email', 'course', 'organization__name']
    readonly_fields = ['paid_total', 'created_at', 'updated_at']
    fieldsets = (
        ('Organization', {
            'fields': ('organization',)
        }),
        ('Basic Information', {
            'fields': ('name', 'pledge', 'paid_total', 'is_active')
        }),
        ('Contact Information', {
            'fields': ('phone', 'email'),
            'classes': ('collapse',)
        }),
        ('Academic Information', {
            'fields': ('course', 'year'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def status(self, obj):
        if obj.is_complete:
            return format_html('<span style="color: green;">✓ Complete</span>')
        elif obj.is_incomplete:
            return format_html('<span style="color: orange;">⚠ Incomplete</span>')
        else:
            return format_html('<span style="color: red;">✗ Not Started</span>')
    status.short_description = 'Status'

    def remaining(self, obj):
        return f"TZS {obj.remaining:,.2f}"
    remaining.short_description = 'Remaining'


@admin.register(Transaction)
class TransactionAdmin(CustomAdminMixin, admin.ModelAdmin):
    list_display = ['member', 'organization', 'amount', 'date', 'added_by', 'note_preview']
    list_filter = ['organization', 'date', 'added_by', 'member']
    search_fields = ['member__name', 'note', 'organization__name']
    readonly_fields = ['created_at']
    date_hierarchy = 'date'
    fieldsets = (
        ('Organization', {
            'fields': ('organization',)
        }),
        ('Transaction Details', {
            'fields': ('member', 'amount', 'date', 'added_by', 'note')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def note_preview(self, obj):
        if obj.note:
            return obj.note[:50] + '...' if len(obj.note) > 50 else obj.note
        return '-'
    note_preview.short_description = 'Note'

    def amount(self, obj):
        return f"TZS {obj.amount:,.2f}"
    amount.short_description = 'Amount'
