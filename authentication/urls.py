from django.urls import path
from .views import RegisterView, SendOTPView, VerifyOTPView, ProfileView, LogoutView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='api_register'),
    path('login/send-otp/', SendOTPView.as_view(), name='api_send_otp'),
    path('login/verify-otp/', VerifyOTPView.as_view(), name='api_verify_otp'),
    path('profile/', ProfileView.as_view(), name='api_profile'),
    path('logout/', LogoutView.as_view(), name='api_logout'),
]