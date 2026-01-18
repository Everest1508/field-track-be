from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_home, name='dashboard_home'),
    path('login/', views.dashboard_login, name='dashboard_login'),
    path('logout/', views.dashboard_logout, name='dashboard_logout'),
    path('visits/', views.visits_view, name='visits_view'),
    path('leads/', views.leads_view, name='leads_view'),
    path('reports/', views.reports_view, name='reports_view'),
    path('staff/', views.staff_view, name='staff_view'),
    path('staff/create/', views.create_staff, name='create_staff'),
    path('staff/<int:user_id>/toggle/', views.toggle_staff_status, name='toggle_staff_status'),
    path('reports/export/', views.export_report, name='export_report'),
]

