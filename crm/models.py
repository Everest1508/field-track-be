from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import RegexValidator
from cryptography.fernet import Fernet
from django.conf import settings
import base64
import hashlib


class EncryptionMixin:
    """Mixin to encrypt/decrypt sensitive fields"""
    
    def _get_cipher(self):
        key = settings.ENCRYPTION_KEY.encode()
        # Ensure key is 32 bytes for Fernet
        key_hash = hashlib.sha256(key).digest()
        key_b64 = base64.urlsafe_b64encode(key_hash)
        return Fernet(key_b64)
    
    def encrypt_field(self, value):
        if not value:
            return value
        cipher = self._get_cipher()
        return cipher.encrypt(value.encode()).decode()
    
    def decrypt_field(self, value):
        if not value:
            return value
        try:
            cipher = self._get_cipher()
            return cipher.decrypt(value.encode()).decode()
        except:
            return value


class UserProfile(models.Model):
    """Extended user profile with role"""
    ROLE_CHOICES = [
        ('sales_executive', 'Sales Executive'),
        ('admin', 'Admin'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='sales_executive')
    phone = models.CharField(max_length=15, blank=True)
    is_active = models.BooleanField(default=True)
    fcm_token = models.TextField(blank=True, null=True, help_text="Firebase Cloud Messaging token")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"
    
    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"


class Customer(models.Model):
    """Customer model"""
    name = models.CharField(max_length=200)
    phone = models.CharField(
        max_length=15,
        validators=[RegexValidator(regex=r'^\+?1?\d{9,15}$', message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.")]
    )
    email = models.EmailField(blank=True, null=True)
    company = models.CharField(max_length=200, blank=True)
    address = models.TextField(blank=True)
    business_card_image = models.ImageField(upload_to='business_cards/', blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_customers')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Customer"
        verbose_name_plural = "Customers"
    
    def __str__(self):
        return f"{self.name} - {self.company or 'N/A'}"


class Lead(models.Model):
    """Lead model"""
    STATUS_CHOICES = [
        ('interested', 'Interested'),
        ('quotation_requested', 'Quotation Requested'),
        ('follow_up_required', 'Follow-up Required'),
        ('negotiation_ongoing', 'Negotiation Ongoing'),
        ('not_interested', 'Not Interested'),
        ('deal_closed', 'Deal Closed'),
    ]
    
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='leads')
    sales_executive = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='leads')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='interested')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Lead"
        verbose_name_plural = "Leads"
    
    def __str__(self):
        return f"{self.customer.name} - {self.get_status_display()}"


class FieldVisit(models.Model):
    """Field visit tracking model"""
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='visits')
    sales_executive = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='field_visits')
    visit_date = models.DateTimeField(default=timezone.now)
    purpose = models.CharField(max_length=500)
    notes = models.TextField(blank=True)
    discussion_status = models.CharField(
        max_length=30,
        choices=Lead.STATUS_CHOICES,
        blank=True,
        null=True
    )
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-visit_date']
        verbose_name = "Field Visit"
        verbose_name_plural = "Field Visits"
    
    def __str__(self):
        return f"{self.customer.name} - {self.visit_date.strftime('%Y-%m-%d %H:%M')}"


class FollowUp(models.Model):
    """Follow-up and reminder model"""
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='followups', blank=True, null=True)
    field_visit = models.ForeignKey(FieldVisit, on_delete=models.CASCADE, related_name='followups', blank=True, null=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='followups')
    sales_executive = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='followups')
    due_date = models.DateTimeField()
    notes = models.TextField(blank=True)
    reminder_sent = models.BooleanField(default=False)
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['due_date']
        verbose_name = "Follow-up"
        verbose_name_plural = "Follow-ups"
    
    def __str__(self):
        return f"{self.customer.name} - {self.due_date.strftime('%Y-%m-%d')}"
    
    def is_overdue(self):
        return not self.completed and self.due_date < timezone.now()


class NotificationLog(models.Model):
    """Notification log for FCM messages"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=50, default='followup_reminder')
    fcm_token = models.TextField(blank=True, null=True)
    sent_at = models.DateTimeField(auto_now_add=True)
    success = models.BooleanField(default=False)
    error_message = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-sent_at']
        verbose_name = "Notification Log"
        verbose_name_plural = "Notification Logs"
    
    def __str__(self):
        return f"{self.user.username} - {self.title} - {self.sent_at.strftime('%Y-%m-%d %H:%M')}"


class SystemNotification(models.Model):
    """System notifications for in-app notifications (header dropdown)"""
    NOTIFICATION_TYPES = [
        ('new_lead', 'New Lead'),
        ('new_visit', 'New Visit'),
        ('followup_due', 'Follow-up Due'),
        ('lead_status_change', 'Lead Status Change'),
        ('visit_reminder', 'Visit Reminder'),
        ('system', 'System'),
        ('info', 'Information'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='system_notifications', null=True, blank=True, help_text="If null, notification is for all users")
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES, default='info')
    icon = models.CharField(max_length=50, blank=True, help_text="Icon identifier (e.g., 'bell', 'check', 'warning')")
    link = models.CharField(max_length=500, blank=True, help_text="Optional link to related page")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "System Notification"
        verbose_name_plural = "System Notifications"
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'is_read']),
        ]
    
    def __str__(self):
        user_str = self.user.username if self.user else "All Users"
        return f"{user_str} - {self.title} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])


class Task(models.Model):
    """Task/Assignment model for admin to assign visits to sales executives"""
    TASK_TYPES = [
        ('visit', 'Field Visit'),
        ('followup', 'Follow-up'),
        ('lead_contact', 'Lead Contact'),
        ('other', 'Other'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    task_type = models.CharField(max_length=20, choices=TASK_TYPES, default='visit')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Assignment
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='assigned_tasks', help_text="Sales executive assigned to this task")
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_tasks', help_text="Admin who created this task")
    
    # Related entities
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='tasks', null=True, blank=True)
    company = models.CharField(max_length=200, blank=True, help_text="Company name if customer not selected")
    lead = models.ForeignKey(Lead, on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks')
    field_visit = models.ForeignKey(FieldVisit, on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks')
    
    # Dates
    due_date = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Task"
        verbose_name_plural = "Tasks"
        indexes = [
            models.Index(fields=['assigned_to', 'status']),
            models.Index(fields=['status', 'due_date']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.get_status_display()}"
    
    def mark_completed(self):
        """Mark task as completed"""
        if self.status != 'completed':
            self.status = 'completed'
            self.completed_at = timezone.now()
            self.save(update_fields=['status', 'completed_at'])
