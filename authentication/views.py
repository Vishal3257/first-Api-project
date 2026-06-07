from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth.hashers import make_password
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed
from myproject.settings import db
from datetime import datetime, timedelta
import random

from django.core.mail import send_mail
from django.conf import settings
from drf_spectacular.utils import extend_schema 
from .serializers import SignUpSerializer, SendOTPSerializer, VerifyOTPSerializer

# ==========================================
# 0. CUSTOM SAFE JWT AUTHENTICATION FOR MONGODB
# ==========================================
class SafeJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        
        try:
            user_data = {
                "id": validated_token.get("user_id"),
                "username": validated_token.get("username"),
                "email": validated_token.get("email"),
                "is_authenticated": True
            }
            
            
            class MockUser:
                def __init__(self, data):
                    self.__dict__.update(data)
                def __str__(self):
                    return self.email
                    
            return MockUser(user_data)
        except Exception:
            raise AuthenticationFailed("Invalid token payload")

# ==========================================
# 1. REGISTER VIEW 
# ==========================================
class RegisterView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=SignUpSerializer, responses={201: dict})
    def post(self, request):
        serializer = SignUpSerializer(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data['username']
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']

            if db.users.find_one({"username": username}) or db.users.find_one({"email": email}):
                return Response({"error": "User already exists"}, status=status.HTTP_400_BAD_REQUEST)

            hashed_password = make_password(password)
            db.users.insert_one({
                "username": username,
                "email": email,
                "password": hashed_password
            })
            return Response({"message": "User registered successfully!"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# ==========================================
# 2. LOGIN - SEND OTP VIEW (Safe Email Fallback)
# ==========================================
class SendOTPView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=SendOTPSerializer, responses={200: dict})
    def post(self, request):
        serializer = SendOTPSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email'].lower()  # केस सेंसिटिविटी से बचने के लिए ईमेल स्मॉल केस में किया
            
            # Check if user exists
            user = db.users.find_one({"email": email})
            if not user:
                return Response({"error": "User with this email not found!"}, status=status.HTTP_404_NOT_FOUND)

            # Generate OTP
            otp = str(random.randint(100000, 999999))
            expires_at = datetime.utcnow() + timedelta(minutes=5)

            # Save to Database
            db.otps.update_one(
                {"email": email},
                {"$set": {"otp": otp, "expires_at": expires_at}},
                upsert=True
            )

            # Safe Email Block to prevent Render from throwing 500 Error
            email_status = "Sent Successfully"
            try:
                subject = "Your OTP Code"
                message = f"Your OTP is: {otp}\nValid for 5 minutes."
                from_email = settings.DEFAULT_FROM_EMAIL
                recipient_list = [email]

                send_mail(subject, message, from_email, recipient_list, fail_silently=False)
            except Exception as email_error:
                email_status = f"Bypassed cloud port restriction. Error: {str(email_error)}"

            return Response({
                "message": f"OTP processed for {email}!",
                "email_delivery_status": email_status,
                "otp": otp  
            }, status=status.HTTP_200_OK)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# ==========================================
# 3. LOGIN - VERIFY OTP VIEW
# ==========================================
class VerifyOTPView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=VerifyOTPSerializer, responses={200: dict})
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email'].lower()  # हमेशा स्मॉल केस में कंपेयर करने के लिए
            user_otp = serializer.validated_data['otp']

            otp_record = db.otps.find_one({"email": email})

            if not otp_record:
                return Response({"error": "No OTP request found for this email."}, status=status.HTTP_400_BAD_REQUEST)

            if datetime.utcnow() > otp_record['expires_at']:
                return Response({"error": "OTP has expired!"}, status=status.HTTP_400_BAD_REQUEST)

            if otp_record['otp'] == user_otp:
                db.otps.delete_one({"email": email})
                user = db.users.find_one({"email": email})
                
                token = RefreshToken()
                token['user_id'] = str(user['_id'])
                token['username'] = user['username']
                token['email'] = user['email']

                return Response({
                    "refresh": str(token),
                    "access": str(token.access_token),
                    "message": "OTP Verified! Login Successful."
                }, status=status.HTTP_200_OK)
            
            return Response({"error": "Invalid OTP. Please try again."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# ==========================================
# 4. PROTECTED PROFILE VIEW (Updated)
# ==========================================
class ProfileView(APIView):
    
    authentication_classes = [SafeJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: dict})
    def get(self, request):
        
        user = request.user
        return Response({
            "message": "Welcome to your protected profile!",
            "user": {
                "id": getattr(user, 'id', None),
                "username": getattr(user, 'username', None),
                "email": getattr(user, 'email', None),
            },
            "server_status": "Operational"
        }, status=status.HTTP_200_OK)

# ==========================================
# 5. LOGOUT VIEW
# ==========================================
class LogoutView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=None, responses={200: dict})
    def post(self, request):
        return Response({"message": "User logged out successfully!"}, status=status.HTTP_200_OK)