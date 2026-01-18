from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Count, Sum
from django.utils import timezone
from datetime import datetime, timedelta
from crm.models import (
    UserProfile, Customer, Lead, FieldVisit, FollowUp, NotificationLog
)
import csv
import json
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors


def is_admin(user):
    """Check if user is admin"""
    return user.is_authenticated and hasattr(user, 'profile') and user.profile.role == 'admin'


def dashboard_login(request):
    """Admin dashboard login with email support"""
    if request.user.is_authenticated and is_admin(request.user):
        return redirect('dashboard_home')
    
    error_message = None
    
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        
        if not email or not password:
            error_message = 'Please provide both email and password'
        else:
            # Authenticate using email (our custom backend handles this)
            user = authenticate(request, username=email, password=password)
            
            if user and is_admin(user):
                login(request, user)
                # Handle remember me
                if request.POST.get('remember_me'):
                    request.session.set_expiry(1209600)  # 2 weeks
                else:
                    request.session.set_expiry(0)  # Session expires when browser closes
                return redirect('dashboard_home')
            else:
                error_message = 'Invalid email/password or insufficient permissions'
    
    return render(request, 'dashboard/login.html', {
        'error': error_message
    })


@login_required
def dashboard_logout(request):
    """Admin dashboard logout"""
    logout(request)
    return redirect('dashboard_login')


@login_required
@user_passes_test(is_admin)
def dashboard_home(request):
    """Dashboard home page"""
    # Statistics
    total_visits = FieldVisit.objects.count()
    total_leads = Lead.objects.count()
    total_customers = Customer.objects.count()
    total_executives = UserProfile.objects.filter(role='sales_executive', is_active=True).count()
    
    # Recent visits
    recent_visits = FieldVisit.objects.select_related('customer', 'sales_executive').order_by('-visit_date')[:10]
    
    # Leads by status
    leads_by_status = list(Lead.objects.values('status').annotate(count=Count('id')))
    
    # Today's visits
    today_visits = FieldVisit.objects.filter(visit_date__date=timezone.now().date()).count()
    
    # Weekly visits data (last 7 days)
    from datetime import timedelta
    weekly_visits = []
    for i in range(6, -1, -1):
        date = timezone.now().date() - timedelta(days=i)
        count = FieldVisit.objects.filter(visit_date__date=date).count()
        weekly_visits.append(count)
    
    context = {
        'total_visits': total_visits,
        'total_leads': total_leads,
        'total_customers': total_customers,
        'total_executives': total_executives,
        'today_visits': today_visits,
        'recent_visits': recent_visits,
        'leads_by_status': json.dumps(list(leads_by_status)),
        'weekly_visits': json.dumps(weekly_visits),
    }
    
    return render(request, 'dashboard/home.html', context)


@login_required
@user_passes_test(is_admin)
def visits_view(request):
    """View all field visits with filters"""
    visits = FieldVisit.objects.select_related('customer', 'sales_executive').all()
    
    # Filters
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    executive_id = request.GET.get('executive')
    customer_id = request.GET.get('customer')
    
    if date_from:
        visits = visits.filter(visit_date__date__gte=date_from)
    if date_to:
        visits = visits.filter(visit_date__date__lte=date_to)
    if executive_id:
        visits = visits.filter(sales_executive_id=executive_id)
    if customer_id:
        visits = visits.filter(customer_id=customer_id)
    
    visits = visits.order_by('-visit_date')[:100]  # Limit to 100 for performance
    
    executives = User.objects.filter(profile__role='sales_executive')
    customers = Customer.objects.all()[:50]  # Limit for dropdown
    
    context = {
        'visits': visits,
        'executives': executives,
        'customers': customers,
        'filters': {
            'date_from': date_from,
            'date_to': date_to,
            'executive': executive_id,
            'customer': customer_id,
        }
    }
    
    return render(request, 'dashboard/visits.html', context)


@login_required
@user_passes_test(is_admin)
def leads_view(request):
    """View all leads"""
    leads = Lead.objects.select_related('customer', 'sales_executive').all()
    
    # Filters
    status_filter = request.GET.get('status')
    executive_id = request.GET.get('executive')
    
    if status_filter:
        leads = leads.filter(status=status_filter)
    if executive_id:
        leads = leads.filter(sales_executive_id=executive_id)
    
    leads = leads.order_by('-created_at')[:100]
    
    executives = User.objects.filter(profile__role='sales_executive')
    
    # Stalled leads (no activity in 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    stalled_leads = Lead.objects.filter(
        updated_at__lt=thirty_days_ago,
        status__in=['interested', 'quotation_requested', 'follow_up_required', 'negotiation_ongoing']
    ).count()
    
    context = {
        'leads': leads,
        'executives': executives,
        'status_choices': Lead.STATUS_CHOICES,
        'stalled_leads': stalled_leads,
        'filters': {
            'status': status_filter,
            'executive': executive_id,
        }
    }
    
    return render(request, 'dashboard/leads.html', context)


@login_required
@user_passes_test(is_admin)
def reports_view(request):
    """Reports and analytics view"""
    report_type = request.GET.get('type', 'daily')
    date = request.GET.get('date', timezone.now().date())
    
    if isinstance(date, str):
        date = datetime.strptime(date, '%Y-%m-%d').date()
    
    # Visit reports
    if report_type == 'daily':
        visits = FieldVisit.objects.filter(visit_date__date=date)
    elif report_type == 'weekly':
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        visits = FieldVisit.objects.filter(
            visit_date__date__gte=week_start,
            visit_date__date__lte=week_end
        )
    else:  # monthly
        today = timezone.now().date()
        month_start = today.replace(day=1)
        if month_start.month == 12:
            month_end = month_start.replace(year=month_start.year + 1, month=1) - timedelta(days=1)
        else:
            month_end = month_start.replace(month=month_start.month + 1) - timedelta(days=1)
        visits = FieldVisit.objects.filter(
            visit_date__date__gte=month_start,
            visit_date__date__lte=month_end
        )
    
    # Lead conversion funnel
    funnel_data = []
    for status, label in Lead.STATUS_CHOICES:
        count = Lead.objects.filter(status=status).count()
        funnel_data.append({'status': status, 'label': label, 'count': count})
    funnel_data_json = json.dumps(funnel_data)
    
    # Executive performance
    executives = UserProfile.objects.filter(role='sales_executive', is_active=True)
    executive_performance = []
    for exec_profile in executives:
        user = exec_profile.user
        total_visits = FieldVisit.objects.filter(sales_executive=user).count()
        total_leads = Lead.objects.filter(sales_executive=user).count()
        closed_deals = Lead.objects.filter(sales_executive=user, status='deal_closed').count()
        conversion_rate = (closed_deals / total_leads * 100) if total_leads > 0 else 0
        
        executive_performance.append({
            'user': user,
            'total_visits': total_visits,
            'total_leads': total_leads,
            'closed_deals': closed_deals,
            'conversion_rate': round(conversion_rate, 2)
        })
    
    # Convert to JSON-serializable format
    executive_performance_list = []
    for perf in executive_performance:
        executive_performance_list.append({
            'user': {'username': perf['user'].username},
            'total_visits': perf['total_visits'],
            'total_leads': perf['total_leads'],
            'closed_deals': perf['closed_deals'],
            'conversion_rate': perf['conversion_rate']
        })
    executive_performance_json = json.dumps(executive_performance_list)
    
    context = {
        'report_type': report_type,
        'date': date,
        'visits': visits[:100],
        'funnel_data': funnel_data_json,
        'executive_performance': executive_performance,
        'executive_performance_json': executive_performance_json,
    }
    
    return render(request, 'dashboard/reports.html', context)


@login_required
@user_passes_test(is_admin)
def staff_view(request):
    """Staff management view"""
    staff = UserProfile.objects.filter(role='sales_executive').select_related('user')
    
    context = {
        'staff': staff,
    }
    
    return render(request, 'dashboard/staff.html', context)


@login_required
@user_passes_test(is_admin)
def create_staff(request):
    """Create new sales executive"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        email = request.POST.get('email', '')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        phone = request.POST.get('phone', '')
        
        if User.objects.filter(username=username).exists():
            return JsonResponse({'error': 'Username already exists'}, status=400)
        
        user = User.objects.create_user(
            username=username,
            password=password,
            email=email,
            first_name=first_name,
            last_name=last_name
        )
        
        # Profile is created by signal, just update it
        profile = user.profile
        profile.role = 'sales_executive'
        profile.phone = phone
        profile.save()
        
        return redirect('staff_view')
    
    return render(request, 'dashboard/create_staff.html')


@login_required
@user_passes_test(is_admin)
def toggle_staff_status(request, user_id):
    """Activate/deactivate staff member"""
    user = get_object_or_404(User, id=user_id)
    if hasattr(user, 'profile'):
        user.profile.is_active = not user.profile.is_active
        user.profile.save()
        user.is_active = user.profile.is_active
        user.save()
    return redirect('staff_view')


@login_required
@user_passes_test(is_admin)
def export_report(request):
    """Export reports as Excel or PDF"""
    export_format = request.GET.get('format', 'excel')
    report_type = request.GET.get('type', 'visits')
    
    if export_format == 'excel':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{report_type}_report.csv"'
        
        writer = csv.writer(response)
        
        if report_type == 'visits':
            visits = FieldVisit.objects.select_related('customer', 'sales_executive').all()[:1000]
            writer.writerow(['Customer', 'Date', 'Purpose', 'Status', 'Sales Executive', 'Notes'])
            for visit in visits:
                writer.writerow([
                    visit.customer.name,
                    visit.visit_date.strftime('%Y-%m-%d %H:%M'),
                    visit.purpose,
                    visit.discussion_status or 'N/A',
                    visit.sales_executive.username if visit.sales_executive else 'N/A',
                    visit.notes[:100]
                ])
        elif report_type == 'leads':
            leads = Lead.objects.select_related('customer', 'sales_executive').all()[:1000]
            writer.writerow(['Customer', 'Company', 'Status', 'Sales Executive', 'Created Date'])
            for lead in leads:
                writer.writerow([
                    lead.customer.name,
                    lead.customer.company or 'N/A',
                    lead.get_status_display(),
                    lead.sales_executive.username if lead.sales_executive else 'N/A',
                    lead.created_at.strftime('%Y-%m-%d')
                ])
        
        return response
    
    elif export_format == 'pdf':
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        
        elements.append(Paragraph(f"{report_type.title()} Report", styles['Title']))
        elements.append(Spacer(1, 12))
        
        if report_type == 'visits':
            visits = FieldVisit.objects.select_related('customer', 'sales_executive').all()[:100]
            data = [['Customer', 'Date', 'Purpose', 'Status', 'Executive']]
            for visit in visits:
                data.append([
                    visit.customer.name[:30],
                    visit.visit_date.strftime('%Y-%m-%d'),
                    visit.purpose[:40],
                    (visit.discussion_status or 'N/A')[:20],
                    (visit.sales_executive.username if visit.sales_executive else 'N/A')[:20]
                ])
        
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
        ]))
        elements.append(table)
        
        doc.build(elements)
        buffer.seek(0)
        
        response = HttpResponse(buffer.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{report_type}_report.pdf"'
        return response
    
    return HttpResponse('Invalid format', status=400)
