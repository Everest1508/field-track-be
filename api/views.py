from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import User
from django.db.models import Q, Count, Sum
from django.utils import timezone
from datetime import datetime, timedelta
from crm.models import (
    UserProfile, Customer, Lead, FieldVisit, FollowUp, NotificationLog, SystemNotification, Task
)
from .serializers import (
    UserSerializer, CustomerSerializer, LeadSerializer,
    FieldVisitSerializer, FollowUpSerializer, NotificationLogSerializer,
    CustomerCreateSerializer, SystemNotificationSerializer, TaskSerializer
)
from django_filters.rest_framework import DjangoFilterBackend
import json
from django.http import HttpResponse
import csv
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from django.utils.dateparse import parse_date

class CustomerViewSet(viewsets.ModelViewSet):
    """ViewSet for Customer CRUD operations"""
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['created_by']
    search_fields = ['name', 'company', 'phone', 'email']
    ordering_fields = ['created_at', 'name']
    ordering = ['-created_at']
    
    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'profile') and user.profile.role == 'admin':
            return Customer.objects.all()
        return Customer.objects.filter(created_by=user)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CustomerCreateSerializer
        return CustomerSerializer
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Search customers by name, phone, or company"""
        query = request.query_params.get('q', '')
        customers = Customer.objects.filter(
            Q(name__icontains=query) |
            Q(phone__icontains=query) |
            Q(company__icontains=query)
        )[:10]
        serializer = self.get_serializer(customers, many=True)
        return Response(serializer.data)


class LeadViewSet(viewsets.ModelViewSet):
    """ViewSet for Lead CRUD operations"""
    serializer_class = LeadSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'sales_executive', 'customer']
    search_fields = ['customer__name', 'customer__company', 'notes']
    ordering_fields = ['created_at', 'status']
    ordering = ['-created_at']
    
    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'profile') and user.profile.role == 'admin':
            return Lead.objects.all()
        return Lead.objects.filter(sales_executive=user)
    
    def perform_create(self, serializer):
        serializer.save(sales_executive=self.request.user)
    
    @action(detail=False, methods=['get'])
    def by_status(self, request):
        """Get leads grouped by status"""
        user = self.request.user
        queryset = self.get_queryset()
        
        status_counts = queryset.values('status').annotate(
            count=Count('id')
        ).order_by('status')
        
        return Response(status_counts)
    
    @action(detail=False, methods=['get'])
    def conversion_funnel(self, request):
        """Get lead conversion funnel data"""
        user = self.request.user
        queryset = self.get_queryset()
        
        funnel_data = []
        statuses = ['interested', 'quotation_requested', 'negotiation_ongoing', 'deal_closed']
        
        for status in statuses:
            count = queryset.filter(status=status).count()
            funnel_data.append({'status': status, 'count': count})
        
        return Response(funnel_data)
    
    @action(detail=True, methods=['patch'])
    def update_status(self, request, pk=None):
        """Update lead status (for drag-drop in kanban)"""
        lead = self.get_object()
        new_status = request.data.get('status')
        
        if not new_status:
            return Response({'error': 'Status is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate status
        valid_statuses = [choice[0] for choice in Lead.STATUS_CHOICES]
        if new_status not in valid_statuses:
            return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)
        
        lead.status = new_status
        lead.save()
        
        serializer = self.get_serializer(lead)
        return Response(serializer.data)


class FieldVisitViewSet(viewsets.ModelViewSet):
    """ViewSet for Field Visit CRUD operations"""
    serializer_class = FieldVisitSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['customer', 'sales_executive', 'discussion_status']
    search_fields = ['customer__name', 'purpose', 'notes']
    ordering_fields = ['visit_date', 'created_at']
    ordering = ['-visit_date']
    
    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'profile') and user.profile.role == 'admin':
            return FieldVisit.objects.all()
        return FieldVisit.objects.filter(sales_executive=user)
    
    def perform_create(self, serializer):
        serializer.save(sales_executive=self.request.user)
    
    @action(detail=False, methods=['get'])
    def daily(self, request):
        """Get daily visits"""
        date = request.query_params.get('date', timezone.now().date())
        if isinstance(date, str):
            date = datetime.strptime(date, '%Y-%m-%d').date()
        
        queryset = self.get_queryset().filter(visit_date__date=date)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def weekly(self, request):
        """Get weekly visits summary"""
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        
        queryset = self.get_queryset().filter(
            visit_date__date__gte=week_start,
            visit_date__date__lte=week_end
        )
        
        summary = {
            'week_start': week_start,
            'week_end': week_end,
            'total_visits': queryset.count(),
            'visits_by_day': {}
        }
        
        for i in range(7):
            day = week_start + timedelta(days=i)
            count = queryset.filter(visit_date__date=day).count()
            summary['visits_by_day'][day.strftime('%Y-%m-%d')] = count
        
        serializer = self.get_serializer(queryset, many=True)
        summary['visits'] = serializer.data
        
        return Response(summary)
    
    @action(detail=False, methods=['get'])
    def monthly(self, request):
        """Get monthly visits summary"""
        today = timezone.now().date()
        month_start = today.replace(day=1)
        
        # Calculate month end
        if month_start.month == 12:
            month_end = month_start.replace(year=month_start.year + 1, month=1) - timedelta(days=1)
        else:
            month_end = month_start.replace(month=month_start.month + 1) - timedelta(days=1)
        
        queryset = self.get_queryset().filter(
            visit_date__date__gte=month_start,
            visit_date__date__lte=month_end
        )
        
        summary = {
            'month': month_start.strftime('%B %Y'),
            'total_visits': queryset.count(),
            'visits_by_status': {}
        }
        
        for status, _ in Lead.STATUS_CHOICES:
            count = queryset.filter(discussion_status=status).count()
            summary['visits_by_status'][status] = count
        
        serializer = self.get_serializer(queryset, many=True)
        summary['visits'] = serializer.data
        
        return Response(summary)


class FollowUpViewSet(viewsets.ModelViewSet):
    """ViewSet for Follow-up CRUD operations"""
    serializer_class = FollowUpSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['customer', 'sales_executive', 'completed']
    search_fields = ['customer__name', 'notes']
    ordering_fields = ['due_date', 'created_at']
    ordering = ['due_date']
    
    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'profile') and user.profile.role == 'admin':
            return FollowUp.objects.all()
        return FollowUp.objects.filter(sales_executive=user)
    
    def perform_create(self, serializer):
        serializer.save(sales_executive=self.request.user)
    
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Get upcoming follow-ups"""
        queryset = self.get_queryset().filter(
            completed=False,
            due_date__gte=timezone.now()
        ).order_by('due_date')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def overdue(self, request):
        """Get overdue follow-ups"""
        queryset = self.get_queryset().filter(
            completed=False,
            due_date__lt=timezone.now()
        ).order_by('due_date')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def mark_completed(self, request, pk=None):
        """Mark follow-up as completed"""
        followup = self.get_object()
        followup.completed = True
        followup.save()
        serializer = self.get_serializer(followup)
        return Response(serializer.data)


class NotificationLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for Notification Log (read-only)"""
    serializer_class = NotificationLogSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['user', 'notification_type', 'success']
    ordering_fields = ['sent_at']
    ordering = ['-sent_at']
    
    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'profile') and user.profile.role == 'admin':
            return NotificationLog.objects.all()
        return NotificationLog.objects.filter(user=user)


class SystemNotificationViewSet(viewsets.ModelViewSet):
    """ViewSet for System Notifications"""
    serializer_class = SystemNotificationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['notification_type', 'is_read']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        user = self.request.user
        # Get notifications for this user or for all users (user=None)
        return SystemNotification.objects.filter(
            Q(user=user) | Q(user=None)
        )
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark notification as read"""
        notification = self.get_object()
        notification.mark_as_read()
        serializer = self.get_serializer(notification)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all notifications as read for current user"""
        user = request.user
        count = SystemNotification.objects.filter(
            (Q(user=user) | Q(user=None)),
            is_read=False
        ).update(
            is_read=True,
            read_at=timezone.now()
        )
        return Response({'marked_read': count})
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get count of unread notifications"""
        user = request.user
        count = SystemNotification.objects.filter(
            (Q(user=user) | Q(user=None)),
            is_read=False
        ).count()
        return Response({'unread_count': count})


# Report views
from rest_framework.decorators import api_view, permission_classes
from api.auth_views import get_current_user


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def visit_reports(request):
    """Generate visit reports (daily/weekly/monthly)"""
    report_type = request.query_params.get('type', 'daily')
    user = request.user
    
    if hasattr(user, 'profile') and user.profile.role == 'admin':
        queryset = FieldVisit.objects.all()
    else:
        queryset = FieldVisit.objects.filter(sales_executive=user)
    
    if report_type == 'daily':
        date = request.query_params.get('date', timezone.now().date())
        if isinstance(date, str):
            date = datetime.strptime(date, '%Y-%m-%d').date()
        visits = queryset.filter(visit_date__date=date)
        serializer = FieldVisitSerializer(visits, many=True, context={'request': request})
        return Response({
            'type': 'daily',
            'date': date,
            'total_visits': visits.count(),
            'visits': serializer.data
        })
    
    elif report_type == 'weekly':
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        visits = queryset.filter(
            visit_date__date__gte=week_start,
            visit_date__date__lte=week_end
        )
        serializer = FieldVisitSerializer(visits, many=True, context={'request': request})
        return Response({
            'type': 'weekly',
            'week_start': week_start,
            'week_end': week_end,
            'total_visits': visits.count(),
            'visits': serializer.data
        })
    
    elif report_type == 'monthly':
        today = timezone.now().date()
        month_start = today.replace(day=1)
        if month_start.month == 12:
            month_end = month_start.replace(year=month_start.year + 1, month=1) - timedelta(days=1)
        else:
            month_end = month_start.replace(month=month_start.month + 1) - timedelta(days=1)
        visits = queryset.filter(
            visit_date__date__gte=month_start,
            visit_date__date__lte=month_end
        )
        serializer = FieldVisitSerializer(visits, many=True, context={'request': request})
        return Response({
            'type': 'monthly',
            'month': month_start.strftime('%B %Y'),
            'total_visits': visits.count(),
            'visits': serializer.data
        })
    
    return Response({'error': 'Invalid report type'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def performance_report(request):
    """Generate performance report for sales executive"""
    user = request.user
    executive_id = request.query_params.get('executive_id')
    
    if hasattr(user, 'profile') and user.profile.role == 'admin' and executive_id:
        target_user = User.objects.get(id=executive_id)
    else:
        target_user = user
    
    # Get statistics
    total_visits = FieldVisit.objects.filter(sales_executive=target_user).count()
    total_leads = Lead.objects.filter(sales_executive=target_user).count()
    closed_deals = Lead.objects.filter(sales_executive=target_user, status='deal_closed').count()
    pending_followups = FollowUp.objects.filter(sales_executive=target_user, completed=False).count()
    
    # Monthly stats
    today = timezone.now().date()
    month_start = today.replace(day=1)
    if month_start.month == 12:
        month_end = month_start.replace(year=month_start.year + 1, month=1) - timedelta(days=1)
    else:
        month_end = month_start.replace(month=month_start.month + 1) - timedelta(days=1)
    
    monthly_visits = FieldVisit.objects.filter(
        sales_executive=target_user,
        visit_date__date__gte=month_start,
        visit_date__date__lte=month_end
    ).count()
    
    conversion_rate = (closed_deals / total_leads * 100) if total_leads > 0 else 0
    
    return Response({
        'executive': {
            'id': target_user.id,
            'username': target_user.username,
            'name': f"{target_user.first_name} {target_user.last_name}".strip() or target_user.username
        },
        'statistics': {
            'total_visits': total_visits,
            'monthly_visits': monthly_visits,
            'total_leads': total_leads,
            'closed_deals': closed_deals,
            'conversion_rate': round(conversion_rate, 2),
            'pending_followups': pending_followups
        }
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_reports(request):
    """Export reports as Excel or PDF with custom filters"""
    print("hey"*58)

    
    export_format = request.query_params.get('format', 'excel')
    report_type = request.query_params.get('type', 'visits')
    user = request.user
    is_admin = hasattr(user, 'profile') and user.profile.role == 'admin'
    
    # Get filter parameters
    date_from = request.query_params.get('date_from')
    date_to = request.query_params.get('date_to')
    executive_ids = request.query_params.getlist('executive_ids')
    customer_ids = request.query_params.getlist('customer_ids')
    
    # Convert date strings to date objects
    if date_from:
        date_from = parse_date(date_from) if isinstance(date_from, str) else date_from
    if date_to:
        date_to = parse_date(date_to) if isinstance(date_to, str) else date_to
    
    # Build querysets with filters
    visits_queryset = FieldVisit.objects.select_related('customer', 'sales_executive').all()
    leads_queryset = Lead.objects.select_related('customer', 'sales_executive').all()
    
    if not is_admin:
        visits_queryset = visits_queryset.filter(sales_executive=user)
        leads_queryset = leads_queryset.filter(sales_executive=user)
    
    if date_from:
        visits_queryset = visits_queryset.filter(visit_date__date__gte=date_from)
        leads_queryset = leads_queryset.filter(created_at__date__gte=date_from)
    if date_to:
        visits_queryset = visits_queryset.filter(visit_date__date__lte=date_to)
        leads_queryset = leads_queryset.filter(created_at__date__lte=date_to)
    if executive_ids:
        visits_queryset = visits_queryset.filter(sales_executive_id__in=executive_ids)
        leads_queryset = leads_queryset.filter(sales_executive_id__in=executive_ids)
    if customer_ids:
        visits_queryset = visits_queryset.filter(customer_id__in=customer_ids)
        leads_queryset = leads_queryset.filter(customer_id__in=customer_ids)
    
    if export_format == 'excel' or export_format == 'csv':
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{report_type}_report_{timezone.now().strftime("%Y%m%d")}.csv"'
        
        writer = csv.writer(response)
        
        if report_type == 'visits':
            writer.writerow(['Customer', 'Company', 'Date', 'Purpose', 'Status', 'Sales Executive', 'Notes'])
            for visit in visits_queryset:
                writer.writerow([
                    visit.customer.name,
                    visit.customer.company or 'N/A',
                    visit.visit_date.strftime('%Y-%m-%d %H:%M'),
                    visit.purpose,
                    visit.discussion_status or 'N/A',
                    visit.sales_executive.username if visit.sales_executive else 'N/A',
                    visit.notes or ''
                ])
        elif report_type == 'leads':
            writer.writerow(['Customer', 'Company', 'Status', 'Sales Executive', 'Created Date', 'Notes'])
            for lead in leads_queryset:
                writer.writerow([
                    lead.customer.name,
                    lead.customer.company or 'N/A',
                    lead.get_status_display(),
                    lead.sales_executive.username if lead.sales_executive else 'N/A',
                    lead.created_at.strftime('%Y-%m-%d %H:%M'),
                    lead.notes or ''
                ])
        elif report_type == 'combined':
            writer.writerow(['Type', 'Customer', 'Company', 'Date', 'Status', 'Sales Executive', 'Details'])
            for visit in visits_queryset:
                writer.writerow([
                    'Visit',
                    visit.customer.name,
                    visit.customer.company or 'N/A',
                    visit.visit_date.strftime('%Y-%m-%d %H:%M'),
                    visit.discussion_status or 'N/A',
                    visit.sales_executive.username if visit.sales_executive else 'N/A',
                    visit.purpose
                ])
            for lead in leads_queryset:
                writer.writerow([
                    'Lead',
                    lead.customer.name,
                    lead.customer.company or 'N/A',
                    lead.created_at.strftime('%Y-%m-%d %H:%M'),
                    lead.get_status_display(),
                    lead.sales_executive.username if lead.sales_executive else 'N/A',
                    lead.notes or ''
                ])
        
        return response
    
    elif export_format == 'pdf':
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        
        # Use the filtered querysets
        if report_type == 'visits':
            visits = visits_queryset.select_related('customer', 'sales_executive')
            
            elements.append(Paragraph("Field Visit Report", styles['Title']))
            if date_from or date_to:
                date_range = f"Period: {date_from or 'Start'} to {date_to or 'End'}"
                elements.append(Paragraph(date_range, styles['Normal']))
            elements.append(Spacer(1, 12))
            
            data = [['Customer', 'Company', 'Date', 'Purpose', 'Status', 'Sales Executive']]
            for visit in visits[:500]:  # Limit to 500 rows
                data.append([
                    visit.customer.name if visit.customer else 'N/A',
                    visit.customer.company if visit.customer and visit.customer.company else 'N/A',
                    visit.visit_date.strftime('%Y-%m-%d %H:%M'),
                    visit.purpose[:40] if visit.purpose else 'N/A',
                    visit.discussion_status or 'N/A',
                    visit.sales_executive.username if visit.sales_executive else 'N/A'
                ])
            
            table = Table(data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(table)
        elif report_type == 'leads':
            leads = leads_queryset.select_related('customer', 'sales_executive')
            
            elements.append(Paragraph("Leads Report", styles['Title']))
            if date_from or date_to:
                date_range = f"Period: {date_from or 'Start'} to {date_to or 'End'}"
                elements.append(Paragraph(date_range, styles['Normal']))
            elements.append(Spacer(1, 12))
            
            data = [['Customer', 'Company', 'Status', 'Sales Executive', 'Created Date', 'Notes']]
            for lead in leads[:500]:
                data.append([
                    lead.customer.name if lead.customer else 'N/A',
                    lead.customer.company if lead.customer and lead.customer.company else 'N/A',
                    lead.get_status_display(),
                    lead.sales_executive.username if lead.sales_executive else 'N/A',
                    lead.created_at.strftime('%Y-%m-%d %H:%M'),
                    (lead.notes[:30] + '...') if lead.notes and len(lead.notes) > 30 else (lead.notes or 'N/A')
                ])
            
            table = Table(data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(table)
        elif report_type == 'combined':
            elements.append(Paragraph("Combined Report", styles['Title']))
            if date_from or date_to:
                date_range = f"Period: {date_from or 'Start'} to {date_to or 'End'}"
                elements.append(Paragraph(date_range, styles['Normal']))
            elements.append(Spacer(1, 12))
            
            data = [['Type', 'Customer', 'Company', 'Date', 'Status', 'Sales Executive', 'Details']]
            for visit in visits_queryset.select_related('customer', 'sales_executive')[:250]:
                data.append([
                    'Visit',
                    visit.customer.name if visit.customer else 'N/A',
                    visit.customer.company if visit.customer and visit.customer.company else 'N/A',
                    visit.visit_date.strftime('%Y-%m-%d %H:%M'),
                    visit.discussion_status or 'N/A',
                    visit.sales_executive.username if visit.sales_executive else 'N/A',
                    visit.purpose[:30] if visit.purpose else 'N/A'
                ])
            for lead in leads_queryset.select_related('customer', 'sales_executive')[:250]:
                data.append([
                    'Lead',
                    lead.customer.name if lead.customer else 'N/A',
                    lead.customer.company if lead.customer and lead.customer.company else 'N/A',
                    lead.created_at.strftime('%Y-%m-%d %H:%M'),
                    lead.get_status_display(),
                    lead.sales_executive.username if lead.sales_executive else 'N/A',
                    (lead.notes[:30] + '...') if lead.notes and len(lead.notes) > 30 else (lead.notes or 'N/A')
                ])
            
            table = Table(data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(table)
        
        doc.build(elements)
        buffer.seek(0)
        
        response = HttpResponse(buffer.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{report_type}_report_{timezone.now().strftime("%Y%m%d")}.pdf"'
        return response
    
    return Response({'error': 'Invalid export format'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def custom_reports(request):
    """Generate custom reports with filters and charts"""
    user = request.user
    
    # Check if user is admin
    is_admin = hasattr(user, 'profile') and user.profile.role == 'admin'
    
    # Get filter parameters
    if request.method == 'POST':
        data = request.data
        date_from = data.get('date_from')
        date_to = data.get('date_to')
        executive_ids = data.get('executive_ids', [])
        customer_ids = data.get('customer_ids', [])
        report_type = data.get('report_type', 'visits')  # visits, leads, performance, combined
        include_charts = data.get('include_charts', True)
    else:
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        executive_ids = request.query_params.getlist('executive_ids')
        customer_ids = request.query_params.getlist('customer_ids')
        report_type = request.query_params.get('report_type', 'visits')
        include_charts = request.query_params.get('include_charts', 'true').lower() == 'true'
    
    # Convert date strings to date objects
    from django.utils.dateparse import parse_date
    if date_from:
        date_from = parse_date(date_from) if isinstance(date_from, str) else date_from
    if date_to:
        date_to = parse_date(date_to) if isinstance(date_to, str) else date_to
    
    # Default to last 30 days if no date range specified
    if not date_from or not date_to:
        today = timezone.localtime(timezone.now()).date()
        if not date_to:
            date_to = today
        if not date_from:
            date_from = date_to - timedelta(days=30)
    
    # Build base querysets
    visits_queryset = FieldVisit.objects.select_related('customer', 'sales_executive').all()
    leads_queryset = Lead.objects.select_related('customer', 'sales_executive').all()
    
    # Apply filters
    if not is_admin:
        visits_queryset = visits_queryset.filter(sales_executive=user)
        leads_queryset = leads_queryset.filter(sales_executive=user)
    
    # Date filters
    visits_queryset = visits_queryset.filter(
        visit_date__date__gte=date_from,
        visit_date__date__lte=date_to
    )
    leads_queryset = leads_queryset.filter(
        created_at__date__gte=date_from,
        created_at__date__lte=date_to
    )
    
    # Executive filter
    if executive_ids:
        visits_queryset = visits_queryset.filter(sales_executive_id__in=executive_ids)
        leads_queryset = leads_queryset.filter(sales_executive_id__in=executive_ids)
    
    # Customer filter
    if customer_ids:
        visits_queryset = visits_queryset.filter(customer_id__in=customer_ids)
        leads_queryset = leads_queryset.filter(customer_id__in=customer_ids)
    
    # Prepare response data
    response_data = {
        'filters': {
            'date_from': str(date_from),
            'date_to': str(date_to),
            'executive_ids': [int(eid) for eid in executive_ids] if executive_ids else [],
            'customer_ids': [int(cid) for cid in customer_ids] if customer_ids else [],
            'report_type': report_type,
        },
        'summary': {},
        'data': {},
        'charts': {},
    }
    
    # Generate report data based on type
    if report_type in ['visits', 'combined']:
        visits_data = FieldVisitSerializer(visits_queryset, many=True, context={'request': request}).data
        response_data['data']['visits'] = visits_data
        response_data['summary']['total_visits'] = visits_queryset.count()
        response_data['summary']['unique_customers'] = visits_queryset.values('customer').distinct().count()
        response_data['summary']['unique_executives'] = visits_queryset.values('sales_executive').distinct().count()
        
        # Visits by status
        visits_by_status = visits_queryset.values('discussion_status').annotate(count=Count('id'))
        response_data['summary']['visits_by_status'] = {
            item['discussion_status'] or 'No Status': item['count']
            for item in visits_by_status
        }
        
        if include_charts:
            # Daily visits chart
            daily_visits = []
            daily_labels = []
            current_date = date_from
            while current_date <= date_to:
                count = visits_queryset.filter(visit_date__date=current_date).count()
                daily_visits.append(count)
                daily_labels.append(current_date.strftime('%m/%d'))
                current_date += timedelta(days=1)
            
            response_data['charts']['daily_visits'] = {
                'labels': daily_labels,
                'data': daily_visits,
            }
            
            # Visits by executive chart
            visits_by_exec = visits_queryset.values(
                'sales_executive__first_name',
                'sales_executive__last_name'
            ).annotate(count=Count('id')).order_by('-count')[:10]
            
            response_data['charts']['visits_by_executive'] = {
                'labels': [
                    f"{item['sales_executive__first_name'] or ''} {item['sales_executive__last_name'] or ''}".strip() or 'Unknown'
                    for item in visits_by_exec
                ],
                'data': [item['count'] for item in visits_by_exec],
            }
    
    if report_type in ['leads', 'combined']:
        leads_data = LeadSerializer(leads_queryset, many=True, context={'request': request}).data
        response_data['data']['leads'] = leads_data
        response_data['summary']['total_leads'] = leads_queryset.count()
        response_data['summary']['closed_deals'] = leads_queryset.filter(status='deal_closed').count()
        response_data['summary']['conversion_rate'] = round(
            (response_data['summary']['closed_deals'] / response_data['summary']['total_leads'] * 100)
            if response_data['summary']['total_leads'] > 0 else 0, 2
        )
        
        # Leads by status
        leads_by_status = leads_queryset.values('status').annotate(count=Count('id'))
        response_data['summary']['leads_by_status'] = {
            item['status']: item['count']
            for item in leads_by_status
        }
        
        if include_charts:
            # Leads by status chart
            response_data['charts']['leads_by_status'] = {
                'labels': [item['status'].replace('_', ' ').title() for item in leads_by_status],
                'data': [item['count'] for item in leads_by_status],
            }
            
            # Daily leads chart
            daily_leads = []
            daily_lead_labels = []
            current_date = date_from
            while current_date <= date_to:
                count = leads_queryset.filter(created_at__date=current_date).count()
                daily_leads.append(count)
                daily_lead_labels.append(current_date.strftime('%m/%d'))
                current_date += timedelta(days=1)
            
            response_data['charts']['daily_leads'] = {
                'labels': daily_lead_labels,
                'data': daily_leads,
            }
    
    if report_type in ['performance', 'combined']:
        # Performance metrics
        if executive_ids:
            executives = User.objects.filter(id__in=executive_ids)
        elif is_admin:
            executives = User.objects.filter(profile__role='sales_executive', profile__is_active=True)
        else:
            executives = [user]
        
        performance_data = []
        for exec_user in executives:
            exec_visits = visits_queryset.filter(sales_executive=exec_user)
            exec_leads = leads_queryset.filter(sales_executive=exec_user)
            
            performance_data.append({
                'executive_id': exec_user.id,
                'executive_name': f"{exec_user.first_name} {exec_user.last_name}".strip() or exec_user.username,
                'total_visits': exec_visits.count(),
                'total_leads': exec_leads.count(),
                'closed_deals': exec_leads.filter(status='deal_closed').count(),
                'conversion_rate': round(
                    (exec_leads.filter(status='deal_closed').count() / exec_leads.count() * 100)
                    if exec_leads.count() > 0 else 0, 2
                ),
            })
        
        response_data['data']['performance'] = performance_data
        
        if include_charts:
            # Performance comparison chart
            response_data['charts']['performance_comparison'] = {
                'labels': [item['executive_name'] for item in performance_data],
                'visits': [item['total_visits'] for item in performance_data],
                'leads': [item['total_leads'] for item in performance_data],
                'closed_deals': [item['closed_deals'] for item in performance_data],
            }
    
    return Response(response_data)


class TaskViewSet(viewsets.ModelViewSet):
    """ViewSet for Task CRUD operations"""
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'assigned_to', 'task_type', 'priority']
    search_fields = ['title', 'description', 'company', 'customer__name']
    ordering_fields = ['created_at', 'due_date', 'priority']
    ordering = ['-created_at']
    
    def get_queryset(self):
        user = self.request.user
        # Admin can see all tasks, sales executives see only assigned tasks
        if hasattr(user, 'profile') and user.profile.role == 'admin':
            return Task.objects.select_related('assigned_to', 'assigned_by', 'customer', 'lead', 'field_visit').all()
        return Task.objects.filter(assigned_to=user).select_related('assigned_to', 'assigned_by', 'customer', 'lead', 'field_visit')
    
    def perform_create(self, serializer):
        # Set assigned_by to current user (admin)
        serializer.save(assigned_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def mark_completed(self, request, pk=None):
        """Mark task as completed"""
        task = self.get_object()
        task.mark_completed()
        serializer = self.get_serializer(task)
        return Response(serializer.data)
