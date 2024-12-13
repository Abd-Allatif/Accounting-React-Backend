from django.contrib import admin
from django.urls import path
from . import views
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/users/token/', views.CustomTokenObtainPairView.as_view(),name='token_obtain_pair'), 
    path('api/users/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/users/logout/', views.logout, name='auth_logout'),
    path('api/users/register/',views.register),
    path('api/users/reset-password/',views.reset_password),
    path('api/users/<str:username>/setup/',views.setupAccount,name='setup_account'),
    path('api/data/export/export-excel/<str:username>/', views.export_all_data_excel, name='export_all_data_excel'),
    path('api/data/export/export-pdf/<str:username>/', views.export_all_data_pdf, name='export_all_data_pdf'),

]
