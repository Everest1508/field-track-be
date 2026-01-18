from rest_framework import serializers
from django.contrib.auth.models import User
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from crm.models import (
    UserProfile, Customer, Lead, FieldVisit, FollowUp, NotificationLog, SystemNotification, Task
)
from django.contrib.auth import authenticate
from rest_framework_simplejwt.exceptions import AuthenticationFailed



class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom token serializer that includes user data and ensures profile exists"""
    # Allow both email and username for login
    email = serializers.CharField(required=False, write_only=True)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make username field optional since we accept email too
        if 'username' in self.fields:
            self.fields['username'].required = False
    
    def validate(self, attrs):
        # Get email or username from attrs
        email = attrs.get('email', '').strip()
        username = attrs.get('username', '').strip()
        password = attrs.get('password', '')
        print(username, password)
        
        # Use email if provided, otherwise use username
        login_field = email if email else username
        
        
        if not login_field or not password:
            raise AuthenticationFailed('Email/username and password are required')
        
        # Authenticate using email or username (our custom backend handles both)
        user = authenticate(username=login_field, password=password)
        print(user)
        
        if not user:
            raise AuthenticationFailed('Invalid email/username or password')
        
        self.user = user
        
        # Ensure user has a profile
        if not hasattr(self.user, 'profile'):
            UserProfile.objects.get_or_create(
                user=self.user,
                defaults={'role': 'sales_executive'}
            )
        
        # Generate tokens using parent class method
        refresh = self.get_token(self.user)
        
        data = {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
        
        # Add user data to response
        data['user'] = {
            'id': self.user.id,
            'username': self.user.username,
            'email': self.user.email,
            'first_name': self.user.first_name,
            'last_name': self.user.last_name,
            'role': self.user.profile.role if hasattr(self.user, 'profile') else 'sales_executive',
        }

        print(data)
        
        return data


class UserSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    phone = serializers.SerializerMethodField()
    date_joined = serializers.DateTimeField(read_only=True)
    
    def get_role(self, obj):
        if hasattr(obj, 'profile'):
            return obj.profile.role
        return 'sales_executive'
    
    def get_phone(self, obj):
        if hasattr(obj, 'profile'):
            return obj.profile.phone
        return None
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role', 'phone', 'date_joined']
        read_only_fields = ['id', 'date_joined']


class CustomerSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    business_card_image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Customer
        fields = [
            'id', 'name', 'phone', 'email', 'company', 'address',
            'business_card_image', 'business_card_image_url',
            'created_by', 'created_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_business_card_image_url(self, obj):
        if obj.business_card_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.business_card_image.url)
        return None


class LeadSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    customer_company = serializers.CharField(source='customer.company', read_only=True)
    sales_executive_name = serializers.CharField(source='sales_executive.username', read_only=True)
    
    class Meta:
        model = Lead
        fields = [
            'id', 'customer', 'customer_name', 'customer_company',
            'sales_executive', 'sales_executive_name',
            'status', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class FieldVisitSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    customer_company = serializers.CharField(source='customer.company', read_only=True)
    sales_executive_name = serializers.CharField(source='sales_executive.username', read_only=True)
    
    class Meta:
        model = FieldVisit
        fields = [
            'id', 'customer', 'customer_name', 'customer_company',
            'sales_executive', 'sales_executive_name',
            'visit_date', 'purpose', 'notes', 'discussion_status',
            'latitude', 'longitude', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class FollowUpSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    sales_executive_name = serializers.CharField(source='sales_executive.username', read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = FollowUp
        fields = [
            'id', 'lead', 'field_visit', 'customer', 'customer_name',
            'sales_executive', 'sales_executive_name',
            'due_date', 'notes', 'reminder_sent', 'completed',
            'is_overdue', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class NotificationLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = NotificationLog
        fields = [
            'id', 'user', 'user_name', 'title', 'message',
            'notification_type', 'sent_at', 'success', 'error_message'
        ]
        read_only_fields = ['id', 'sent_at']


class SystemNotificationSerializer(serializers.ModelSerializer):
    """Serializer for system notifications"""
    time_ago = serializers.SerializerMethodField()
    
    def get_time_ago(self, obj):
        """Calculate time ago string"""
        from django.utils import timezone
        from datetime import timedelta
        
        now = timezone.now()
        diff = now - obj.created_at
        
        if diff < timedelta(minutes=1):
            return 'Just now'
        elif diff < timedelta(hours=1):
            minutes = int(diff.total_seconds() / 60)
            return f'{minutes} minute{"s" if minutes > 1 else ""} ago'
        elif diff < timedelta(days=1):
            hours = int(diff.total_seconds() / 3600)
            return f'{hours} hour{"s" if hours > 1 else ""} ago'
        elif diff < timedelta(days=7):
            days = diff.days
            return f'{days} day{"s" if days > 1 else ""} ago'
        else:
            return obj.created_at.strftime('%b %d, %Y')
    
    class Meta:
        model = SystemNotification
        fields = [
            'id', 'title', 'message', 'notification_type', 'icon',
            'link', 'is_read', 'created_at', 'read_at', 'time_ago'
        ]
        read_only_fields = ['id', 'created_at', 'read_at']


class CustomerCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating customer with OCR data"""
    class Meta:
        model = Customer
        fields = [
            'name', 'phone', 'email', 'company', 'address',
            'business_card_image', 'created_by'
        ]


class TaskSerializer(serializers.ModelSerializer):
    assigned_to_name = serializers.CharField(source='assigned_to.username', read_only=True)
    assigned_by_name = serializers.CharField(source='assigned_by.username', read_only=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    company_display = serializers.SerializerMethodField()
    
    def get_company_display(self, obj):
        if obj.customer:
            return obj.customer.company or obj.customer.name
        return obj.company
    
    class Meta:
        model = Task
        fields = [
            'id', 'title', 'description', 'task_type', 'priority', 'status',
            'assigned_to', 'assigned_to_name', 'assigned_by', 'assigned_by_name',
            'customer', 'customer_name', 'company', 'company_display',
            'lead', 'field_visit', 'due_date', 'completed_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'completed_at']
