from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth.hashers import make_password
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.mail import send_mail
from django.conf import settings
from datetime import datetime, timedelta
import random

from myproject.settings import db
from drf_spectacular.utils import extend_schema, extend_schema_view
from .serializers import SignUpSerializer, SendOTPSerializer, VerifyOTPSerializer
from .backends import SafeJWTAuthentication

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
# 2. LOGIN - SEND OTP VIEW (Gmail SMTP)
# ==========================================
class SendOTPView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=SendOTPSerializer, responses={200: dict})
    def post(self, request):
        serializer = SendOTPSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email'].lower()  
            
            user = db.users.find_one({"email": email})
            if not user:
                return Response({"error": "User with this email not found!"}, status=status.HTTP_404_NOT_FOUND)

            otp = str(random.randint(100000, 999999))
            expires_at = datetime.utcnow() + timedelta(minutes=5)

            db.otps.update_one(
                {"email": email},
                {"$set": {"otp": otp, "expires_at": expires_at}},
                upsert=True
            )

            email_status = "Sent Successfully"
            try:
                subject = "Your Login OTP Code"
                message = f"Your OTP for login is: {otp}\nValid for 5 minutes. Please do not share it with anyone."
                from_email = settings.EMAIL_HOST_USER
                recipient_list = [email]

                send_mail(subject, message, from_email, recipient_list, fail_silently=False)
                email_status = f"OTP Sent via Gmail SMTP successfully to {email}!"
                
            except Exception as email_error:
                email_status = f"Gmail SMTP Failed: {str(email_error)}"

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
            email = serializer.validated_data['email'].lower()  
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
# 4. PROTECTED PROFILE VIEW
# ==========================================
@extend_schema_view(
    get=extend_schema(responses={200: dict})
)
class ProfileView(APIView):
    authentication_classes = [SafeJWTAuthentication]
    permission_classes = [IsAuthenticated]

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