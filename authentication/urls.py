from django.urls import path
from .views import (
    RegisterView, SendOTPView, VerifyOTPView, ProfileView, LogoutView,
    NormalLoginView, TodoListCreateView, TodoDetailUpdateDeleteView  
)

urlpatterns = [
    # Authentication endpoints
    path('register/', RegisterView.as_view(), name='api_register'),
    path('login/send-otp/', SendOTPView.as_view(), name='api_send_otp'),
    path('login/verify-otp/', VerifyOTPView.as_view(), name='api_verify_otp'),
    path('profile/', ProfileView.as_view(), name='api_profile'),
    path('logout/', LogoutView.as_view(), name='api_logout'),
    
    # todo endpoints
    path('login/', NormalLoginView.as_view(), name='api_normal_login'),
    path('todos/', TodoListCreateView.as_view(), name='todo_list_create'),
    path('todos/<str:todo_id>/', TodoDetailUpdateDeleteView.as_view(), name='todo_detail_update_delete'),
]