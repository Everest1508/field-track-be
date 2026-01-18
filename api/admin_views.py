from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q, Count, Sum
from django.utils import timezone
from datetime import datetime, timedelta
from django.contrib.auth.models import User
from crm.models import (
    UserProfile, Customer, Lead, FieldVisit, FollowUp, NotificationLog
)
from api.serializers import (
    CustomerSerializer, LeadSerializer, FieldVisitSerializer,
    UserSerializer
)
import json


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    """Get dashboard statistics for admin"""
    user = request.user
    
    # Check if user is admin
    if not (hasattr(user, 'profile') and user.profile.role == 'admin'):
        return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
    
    # Calculate statistics
    # Get today's date in server timezone (Asia/Kolkata)
    # timezone.localtime() converts UTC to server timezone
    now = timezone.localtime(timezone.now())
    today_date = now.date()
    
    # Today's visits - compare date part in server timezone
    # Django's __date filter automatically uses server timezone when USE_TZ=True
    today_visits = FieldVisit.objects.filter(
        visit_date__date=today_date
    ).count()
    
    # Total statistics
    total_visits = FieldVisit.objects.count()
    total_leads = Lead.objects.count()
    total_customers = Customer.objects.count()
    total_executives = UserProfile.objects.filter(role='sales_executive', is_active=True).count()
    
    # Weekly visits data (last 7 days)
    weekly_visits = []
    for i in range(6, -1, -1):
        date = today_date - timedelta(days=i)
        count = FieldVisit.objects.filter(visit_date__date=date).count()
        weekly_visits.append(count)
    
    # Leads by status
    leads_by_status = list(Lead.objects.values('status').annotate(count=Count('id')))
    
    # Recent visits (last 10)
    recent_visits = FieldVisit.objects.select_related('customer', 'sales_executive').order_by('-visit_date')[:10]
    recent_visits_data = FieldVisitSerializer(recent_visits, many=True, context={'request': request}).data
    
    # Calculate changes (mock for now, can be improved with historical data)
    stats = [
        {
            'title': "Today's Visits",
            'value': today_visits,
            'prefix': '',
            'suffix': f'+{today_visits} today',
            'status': 'success',
        },
        {
            'title': "Total Leads",
            'value': total_leads,
            'prefix': '',
            'suffix': 'Active',
            'status': 'success',
        },
        {
            'title': "Customers",
            'value': total_customers,
            'prefix': '',
            'suffix': 'Growing',
            'status': 'success',
        },
        {
            'title': "Executives",
            'value': total_executives,
            'prefix': '',
            'suffix': 'Active',
            'status': 'success',
        },
    ]
    
    return Response({
        'stats': stats,
        'weekly_visits': weekly_visits,
        'leads_by_status': leads_by_status,
        'recent_visits': recent_visits_data,
        'totals': {
            'visits': total_visits,
            'leads': total_leads,
            'customers': total_customers,
            'executives': total_executives,
        }
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_visits(request):
    """Get field visits for dashboard table"""
    user = request.user
    
    if not (hasattr(user, 'profile') and user.profile.role == 'admin'):
        return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
    
    # Get filter parameters
    date_from = request.query_params.get('date_from')
    date_to = request.query_params.get('date_to')
    executive_id = request.query_params.get('executive')
    customer_id = request.query_params.get('customer')
    
    visits = FieldVisit.objects.select_related('customer', 'sales_executive').all()
    
    if date_from:
        visits = visits.filter(visit_date__date__gte=date_from)
    if date_to:
        visits = visits.filter(visit_date__date__lte=date_to)
    if executive_id:
        visits = visits.filter(sales_executive_id=executive_id)
    if customer_id:
        visits = visits.filter(customer_id=customer_id)
    
    # Pagination
    page = int(request.query_params.get('page', 1))
    page_size = int(request.query_params.get('page_size', 10))
    start = (page - 1) * page_size
    end = start + page_size
    
    visits_data = FieldVisitSerializer(visits[start:end], many=True, context={'request': request}).data
    
    return Response({
        'data': visits_data,
        'total': visits.count(),
        'page': page,
        'page_size': page_size,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_leads(request):
    """Get leads for dashboard"""
    user = request.user
    
    if not (hasattr(user, 'profile') and user.profile.role == 'admin'):
        return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
    
    status_filter = request.query_params.get('status')
    executive_id = request.query_params.get('executive')
    exclude_status = request.query_params.get('exclude_status')  # Comma-separated list
    view_type = request.query_params.get('view_type', 'table')  # 'table' or 'kanban'
    
    leads = Lead.objects.select_related('customer', 'sales_executive').all()
    
    if status_filter:
        # If multiple statuses (comma-separated), filter by any of them
        statuses = [s.strip() for s in status_filter.split(',')]
        leads = leads.filter(status__in=statuses)
    
    if exclude_status:
        # Exclude specific statuses
        exclude_statuses = [s.strip() for s in exclude_status.split(',')]
        leads = leads.exclude(status__in=exclude_statuses)
    
    if executive_id:
        leads = leads.filter(sales_executive_id=executive_id)
    
    if view_type == 'kanban':
        # Return leads grouped by status for kanban board
        leads_by_status = {}
        for status_code, status_label in Lead.STATUS_CHOICES:
            status_leads = leads.filter(status=status_code)
            leads_data = LeadSerializer(status_leads, many=True, context={'request': request}).data
            leads_by_status[status_code] = {
                'label': status_label,
                'leads': leads_data,
                'count': status_leads.count()
            }
        
        return Response({
            'view_type': 'kanban',
            'leads_by_status': leads_by_status,
            'total': leads.count(),
        })
    else:
        # Table view with pagination
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 10))
        start = (page - 1) * page_size
        end = start + page_size
        
        leads_data = LeadSerializer(leads[start:end], many=True, context={'request': request}).data
        
        return Response({
            'view_type': 'table',
            'data': leads_data,
            'total': leads.count(),
            'page': page,
            'page_size': page_size,
        })


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def dashboard_executive_update(request, executive_id):
    """Update an existing sales executive"""
    user = request.user
    
    if not (hasattr(user, 'profile') and user.profile.role == 'admin'):
        return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        exec_user = User.objects.get(id=executive_id)
        profile = exec_user.profile
        
        # Update user fields
        if 'first_name' in request.data:
            exec_user.first_name = request.data.get('first_name', exec_user.first_name)
        if 'last_name' in request.data:
            exec_user.last_name = request.data.get('last_name', exec_user.last_name)
        if 'email' in request.data:
            email = request.data.get('email')
            if email and User.objects.filter(email=email).exclude(id=executive_id).exists():
                return Response({'error': 'Email already exists'}, status=status.HTTP_400_BAD_REQUEST)
            exec_user.email = email
        if 'password' in request.data and request.data.get('password'):
            exec_user.set_password(request.data.get('password'))
        
        exec_user.save()
        
        # Update profile fields
        if 'phone' in request.data:
            profile.phone = request.data.get('phone', profile.phone)
        if 'is_active' in request.data:
            profile.is_active = request.data.get('is_active', profile.is_active)
        
        profile.save()
        
        # Return updated executive data
        total_visits = FieldVisit.objects.filter(sales_executive=exec_user).count()
        total_leads = Lead.objects.filter(sales_executive=exec_user).count()
        closed_deals = Lead.objects.filter(sales_executive=exec_user, status='deal_closed').count()
        conversion_rate = (closed_deals / total_leads * 100) if total_leads > 0 else 0
        
        return Response({
            'id': exec_user.id,
            'username': exec_user.username,
            'email': exec_user.email,
            'first_name': exec_user.first_name,
            'last_name': exec_user.last_name,
            'phone': profile.phone,
            'is_active': profile.is_active,
            'stats': {
                'total_visits': total_visits,
                'total_leads': total_leads,
                'closed_deals': closed_deals,
                'conversion_rate': round(conversion_rate, 2),
            }
        })
    except User.DoesNotExist:
        return Response({'error': 'Executive not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def dashboard_executives(request):
    """Get list of sales executives or create a new one"""
    user = request.user
    
    if not (hasattr(user, 'profile') and user.profile.role == 'admin'):
        return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
    
    if request.method == 'POST':
        try:
            exec_user = User.objects.get(id=executive_id)
            profile = exec_user.profile
            
            # Update user fields
            if 'first_name' in request.data:
                exec_user.first_name = request.data.get('first_name', exec_user.first_name)
            if 'last_name' in request.data:
                exec_user.last_name = request.data.get('last_name', exec_user.last_name)
            if 'email' in request.data:
                email = request.data.get('email')
                if email and User.objects.filter(email=email).exclude(id=executive_id).exists():
                    return Response({'error': 'Email already exists'}, status=status.HTTP_400_BAD_REQUEST)
                exec_user.email = email
            if 'password' in request.data and request.data.get('password'):
                exec_user.set_password(request.data.get('password'))
            
            exec_user.save()
            
            # Update profile fields
            if 'phone' in request.data:
                profile.phone = request.data.get('phone', profile.phone)
            if 'is_active' in request.data:
                profile.is_active = request.data.get('is_active', profile.is_active)
            
            profile.save()
            
            # Return updated executive data
            total_visits = FieldVisit.objects.filter(sales_executive=exec_user).count()
            total_leads = Lead.objects.filter(sales_executive=exec_user).count()
            closed_deals = Lead.objects.filter(sales_executive=exec_user, status='deal_closed').count()
            conversion_rate = (closed_deals / total_leads * 100) if total_leads > 0 else 0
            
            return Response({
                'id': exec_user.id,
                'username': exec_user.username,
                'email': exec_user.email,
                'first_name': exec_user.first_name,
                'last_name': exec_user.last_name,
                'phone': profile.phone,
                'is_active': profile.is_active,
                'stats': {
                    'total_visits': total_visits,
                    'total_leads': total_leads,
                    'closed_deals': closed_deals,
                    'conversion_rate': round(conversion_rate, 2),
                }
            })
        except User.DoesNotExist:
            return Response({'error': 'Executive not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'POST':
        # Create new sales executive
        username = request.data.get('username')
        password = request.data.get('password')
        email = request.data.get('email', '')
        first_name = request.data.get('first_name', '')
        last_name = request.data.get('last_name', '')
        phone = request.data.get('phone', '')
        
        if not username or not password:
            return Response({'error': 'Username and password are required'}, status=status.HTTP_400_BAD_REQUEST)
        
        if User.objects.filter(username=username).exists():
            return Response({'error': 'Username already exists'}, status=status.HTTP_400_BAD_REQUEST)
        
        if email and User.objects.filter(email=email).exists():
            return Response({'error': 'Email already exists'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Create user
        new_user = User.objects.create_user(
            username=username,
            password=password,
            email=email,
            first_name=first_name,
            last_name=last_name
        )
        
        # Profile is created by signal, just update it
        profile = new_user.profile
        profile.role = 'sales_executive'
        profile.phone = phone
        profile.is_active = True
        profile.save()
        
        # Return created executive data
        return Response({
            'id': new_user.id,
            'username': new_user.username,
            'email': new_user.email,
            'first_name': new_user.first_name,
            'last_name': new_user.last_name,
            'phone': profile.phone,
            'is_active': profile.is_active,
            'stats': {
                'total_visits': 0,
                'total_leads': 0,
                'closed_deals': 0,
                'conversion_rate': 0,
            }
        }, status=status.HTTP_201_CREATED)
    
    # GET request - return list of executives
    executives = UserProfile.objects.filter(role='sales_executive', is_active=True).select_related('user')
    
    executives_data = []
    for profile in executives:
        user = profile.user
        total_visits = FieldVisit.objects.filter(sales_executive=user).count()
        total_leads = Lead.objects.filter(sales_executive=user).count()
        closed_deals = Lead.objects.filter(sales_executive=user, status='deal_closed').count()
        conversion_rate = (closed_deals / total_leads * 100) if total_leads > 0 else 0
        
        executives_data.append({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'phone': profile.phone,
            'is_active': profile.is_active,
            'stats': {
                'total_visits': total_visits,
                'total_leads': total_leads,
                'closed_deals': closed_deals,
                'conversion_rate': round(conversion_rate, 2),
            }
        })
    
    return Response({'data': executives_data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_charts_data(request):
    """Get chart data for dashboard"""
    user = request.user
    
    if not (hasattr(user, 'profile') and user.profile.role == 'admin'):
        return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
    
    chart_type = request.query_params.get('type', 'visits')
    
    if chart_type == 'visits':
        # Weekly visits data
        # Use server timezone (Asia/Kolkata) for date calculations
        today_date = timezone.localtime(timezone.now()).date()
        weekly_visits = []
        labels = []
        for i in range(6, -1, -1):
            date = today_date - timedelta(days=i)
            count = FieldVisit.objects.filter(visit_date__date=date).count()
            weekly_visits.append(count)
            labels.append(date.strftime('%a'))
        
        return Response({
            'labels': labels,
            'data': weekly_visits,
        })
    
    elif chart_type == 'leads':
        # Leads by status
        leads_by_status = list(Lead.objects.values('status').annotate(count=Count('id')))
        
        return Response({
            'labels': [item['status'].replace('_', ' ').title() for item in leads_by_status],
            'data': [item['count'] for item in leads_by_status],
        })
    
    elif chart_type == 'sales_overview':
        # Sales overview (traffic and sales)
        # Use server timezone (Asia/Kolkata) for date calculations
        today = timezone.localtime(timezone.now()).date()
        months = []
        traffic_data = []
        sales_data = []
        
        for i in range(8, -1, -1):
            month_date = today - timedelta(days=30 * i)
            month_start = month_date.replace(day=1)
            if month_start.month == 12:
                month_end = month_start.replace(year=month_start.year + 1, month=1) - timedelta(days=1)
            else:
                month_end = month_start.replace(month=month_start.month + 1) - timedelta(days=1)
            
            visits_count = FieldVisit.objects.filter(
                visit_date__date__gte=month_start,
                visit_date__date__lte=month_end
            ).count()
            
            leads_count = Lead.objects.filter(
                created_at__date__gte=month_start,
                created_at__date__lte=month_end
            ).count()
            
            months.append(month_start.strftime('%b'))
            traffic_data.append(visits_count * 10)  # Scale for visualization
            sales_data.append(leads_count * 5)  # Scale for visualization
        
        return Response({
            'labels': months,
            'traffic': traffic_data,
            'sales': sales_data,
        })
    
    return Response({'error': 'Invalid chart type'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_projects_table(request):
    """Get recent field visits table data"""
    user = request.user
    
    if not (hasattr(user, 'profile') and user.profile.role == 'admin'):
        return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
    
    visits = FieldVisit.objects.select_related('customer', 'sales_executive').order_by('-visit_date')[:6]
    
    visits_data = FieldVisitSerializer(visits, many=True, context={'request': request}).data
    
    return Response({'data': visits_data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_orders_history(request):
    """Get orders/visits history for timeline"""
    user = request.user
    
    if not (hasattr(user, 'profile') and user.profile.role == 'admin'):
        return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
    
    visits = FieldVisit.objects.select_related('customer', 'sales_executive').order_by('-visit_date')[:5]
    
    orders_data = []
    for visit in visits:
        orders_data.append({
            'title': visit.customer.name,
            'time': visit.visit_date.strftime('%d %b %I:%M %p'),
            'status': 'success',
        })
    
    return Response({'data': orders_data})

