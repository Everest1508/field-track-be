from django.contrib import admin
from .models import UserProfile, Customer, Lead, FieldVisit, FollowUp, NotificationLog, SystemNotification


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'is_active', 'phone', 'created_at']
    list_filter = ['role', 'is_active']
    search_fields = ['user__username', 'user__email', 'phone']


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['name', 'company', 'phone', 'email', 'created_by', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'company', 'phone', 'email']


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ['customer', 'status', 'sales_executive', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['customer__name', 'customer__company']


@admin.register(FieldVisit)
class FieldVisitAdmin(admin.ModelAdmin):
    list_display = ['customer', 'visit_date', 'discussion_status', 'sales_executive', 'created_at']
    list_filter = ['discussion_status', 'visit_date']
    search_fields = ['customer__name', 'purpose']


@admin.register(FollowUp)
class FollowUpAdmin(admin.ModelAdmin):
    list_display = ['customer', 'due_date', 'completed', 'reminder_sent', 'sales_executive']
    list_filter = ['completed', 'reminder_sent', 'due_date']
    search_fields = ['customer__name']


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'notification_type', 'success', 'sent_at']
    list_filter = ['success', 'notification_type', 'sent_at']
    search_fields = ['user__username', 'title', 'message']
    readonly_fields = ['sent_at']


@admin.register(SystemNotification)
class SystemNotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'notification_type', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['title', 'message', 'user__username']
    readonly_fields = ['created_at', 'read_at']
    list_editable = ['is_read']
