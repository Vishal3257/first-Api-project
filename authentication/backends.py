# authentication/backends.py फ़ाइल का पूरा कोड
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed

class SafeJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        try:
            user_data = {
                "id": validated_token.get("user_id"),
                "username": validated_token.get("username"),
                "email": validated_token.get("email"),
                "is_authenticated": True,
                "is_active": True,       # जांगो परमिशन के लिए ज़रूरी
                "is_staff": False,
                "_backend": 'django.contrib.auth.backends.ModelBackend',
            }
            
            class MockUser:
                def __init__(self, data):
                    self.__dict__.update(data)
                def __str__(self):
                    return self.email
                def __eq__(self, other):
                    return other and getattr(other, 'id', None) == self.id
                def __ne__(self, other):
                    return not self.__eq__(other)
                    
            return MockUser(user_data)
        except Exception:
            raise AuthenticationFailed("Invalid token payload")