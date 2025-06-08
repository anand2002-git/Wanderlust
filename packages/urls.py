from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from .forms import UserLoginForm

app_name = 'packages'

urlpatterns = [
    # Main pages
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    
    # Package related URLs
    path('packages/', views.package_list, name='package_list'),
    path('package/<int:pk>/', views.package_detail, name='package_detail'),
    path('package/<int:pk>/book/', views.book_package, name='book_package'),
    
    # Vendor specific URLs
    path('vendor/dashboard/', views.vendor_dashboard, name='vendor_dashboard'),
    path('vendor/add-package/', views.add_package, name='add_package'),
    path('package/<int:pk>/edit/', views.edit_package, name='edit_package'),
    path('package/<int:pk>/delete/', views.delete_package, name='delete_package'),
    
    # Admin specific URLs
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('package/approve/<int:pk>/', views.approve_package, name='approve_package'),
    
    # Authentication URLs
    path('register/', views.register, name='register'),
    path('register/vendor/', views.vendor_register, name='vendor_register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Password reset URLs
    # Password reset URLs
    path('password-reset/',
        auth_views.PasswordResetView.as_view(
            template_name='accounts/password_reset.html',
            email_template_name='accounts/password_reset_email.html',
            subject_template_name='accounts/password_reset_subject.txt',
            success_url='done/'
    ),
     name='password_reset'),
    path('password-reset/done/',
     auth_views.PasswordResetDoneView.as_view(
         template_name='accounts/password_reset_done.html'
     ),
     name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/',
     auth_views.PasswordResetConfirmView.as_view(
         template_name='accounts/password_reset_confirm.html',
         success_url='/password-reset-complete/'
     ),
     name='password_reset_confirm'),
path('password-reset-complete/',
     auth_views.PasswordResetCompleteView.as_view(
         template_name='accounts/password_reset_complete.html'
     ),
     name='password_reset_complete'),
    
    # User profile URLs
    path('profile/', views.profile, name='profile'),
    path('profile/update/', views.profile_update, name='profile_update'),
    
    # Booking management
    path('booking/<int:booking_id>/cancel/', views.cancel_booking, name='cancel_booking'),
    # Payment URLs
    path('payment/success/', views.payment_success, name='payment_success'),
]