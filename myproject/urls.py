"""
URL configuration for myproject project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from drf_yasg.generators import OpenAPISchemaGenerator
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed


FIXED_SWAGGER_TOKEN = "thakur_secret_key_123"

# ==========================================
# BACKEND SECURITY CHECK
# ==========================================
class SwaggerDoubleValidationAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if not auth_header:
            return None
        
        
        if auth_header == FIXED_SWAGGER_TOKEN:
            from django.contrib.auth.models import User
            dummy_admin = User(username="swagger_admin", is_staff=True)
            return (dummy_admin, None)
            
        
        if auth_header.startswith('Bearer '):
            
            from rest_framework_simplejwt.authentication import JWTAuthentication
            try:
                validated_token = JWTAuthentication().get_validated_token(auth_header.split()[1])
                user = JWTAuthentication().get_user(validated_token)
                return (user, validated_token)
            except Exception:
                return None

        return None

# ==========================================
# SWAGGER GENERATOR 
# ==========================================
class UltimateSchemaGenerator(OpenAPISchemaGenerator):
    def get_security_definitions(self):
        return {
            
            '1_Main_Swagger_Lock': {
                'type': 'apiKey',
                'name': 'Authorization',
                'in': 'header',
                'description': "🔐"
            },
            
            '2_User_JWT_Bearer_Lock': {
                'type': 'apiKey',
                'name': 'Authorization',
                'in': 'header',
                'description': "🎫  'access' : Bearer <token>"
            }
        }

schema_view = get_schema_view(
   openapi.Info(
      title="User Auth OTP API Documentation",
      default_version='v1',
      description="MongoDB, JWT, and OTP based authentication API system",
   ),
   public=True,
   permission_classes=(permissions.IsAuthenticated,), 
   generator_class=UltimateSchemaGenerator,
)

# ==========================================
# URL PATTERNS
# ==========================================
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('authentication.urls')),
    
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]