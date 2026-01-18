from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.views import TokenObtainPairView as BaseTokenObtainPairView
from .serializers import CustomTokenObtainPairSerializer
from .views import (
    CustomerViewSet, LeadViewSet, FieldVisitViewSet,
    FollowUpViewSet, NotificationLogViewSet, SystemNotificationViewSet,
    TaskViewSet, visit_reports, performance_report, export_reports, custom_reports
)
from .auth_views import get_current_user
from .admin_views import (
    dashboard_stats, dashboard_visits, dashboard_leads,
    dashboard_executives, dashboard_executive_update, dashboard_charts_data,
    dashboard_projects_table, dashboard_orders_history
)
from .fcm_views import update_fcm_token, admin_update_fcm_token
from .test_notification_views import test_notification, list_users_with_tokens


class TokenObtainPairView(BaseTokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


# Create router instance
router = DefaultRouter()
router.register(r'customers', CustomerViewSet, basename='customer')
router.register(r'leads', LeadViewSet, basename='lead')
router.register(r'field-visits', FieldVisitViewSet, basename='fieldvisit')
router.register(r'followups', FollowUpViewSet, basename='followup')
router.register(r'notifications', NotificationLogViewSet, basename='notification')
router.register(r'system-notifications', SystemNotificationViewSet, basename='systemnotification')
router.register(r'tasks', TaskViewSet, basename='task')

# Get router URLs without format suffix to avoid double registration
router_urls = router.urls

urlpatterns = [
    path('', include(router_urls)),
    path('auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/me/', get_current_user, name='current_user'),
    path('reports/visits/', visit_reports, name='visit_reports'),
    path('reports/performance/', performance_report, name='performance_report'),
    path('reports/export/', export_reports, name='export_reports'),
    path('reports/custom/', custom_reports, name='custom_reports'),
    # Admin Dashboard APIs
    path('admin/dashboard/stats/', dashboard_stats, name='admin_dashboard_stats'),
    path('admin/dashboard/visits/', dashboard_visits, name='admin_dashboard_visits'),
    path('admin/dashboard/leads/', dashboard_leads, name='admin_dashboard_leads'),
    path('admin/dashboard/executives/', dashboard_executives, name='admin_dashboard_executives'),
    path('admin/dashboard/executives/<int:executive_id>/', dashboard_executive_update, name='admin_dashboard_executive_update'),
    path('admin/dashboard/charts/', dashboard_charts_data, name='admin_dashboard_charts'),
    path('admin/dashboard/projects/', dashboard_projects_table, name='admin_dashboard_projects'),
    path('admin/dashboard/orders/', dashboard_orders_history, name='admin_dashboard_orders'),
    # FCM Token endpoints
    path('user/fcm-token/', update_fcm_token, name='update_fcm_token'),
    path('admin/fcm-token/', admin_update_fcm_token, name='admin_update_fcm_token'),
    # Test notification endpoints
    path('test-notification/', test_notification, name='test_notification'),
    path('test-notification/users/', list_users_with_tokens, name='list_users_with_tokens'),
]

