from django.contrib import admin
from django.utils.html import format_html
from .models import Member, Transaction


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ['name', 'pledge', 'paid_total', 'remaining', 'status', 'phone', 'email']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['name', 'phone', 'email', 'course']
    readonly_fields = ['paid_total', 'created_at', 'updated_at']
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'pledge', 'paid_total')
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
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['member', 'amount', 'date', 'added_by', 'note_preview']
    list_filter = ['date', 'added_by', 'member']
    search_fields = ['member__name', 'note']
    readonly_fields = ['created_at']
    date_hierarchy = 'date'
    
    def note_preview(self, obj):
        if obj.note:
            return obj.note[:50] + '...' if len(obj.note) > 50 else obj.note
        return '-'
    note_preview.short_description = 'Note'

    def amount(self, obj):
        return f"TZS {obj.amount:,.2f}"
    amount.short_description = 'Amount'
