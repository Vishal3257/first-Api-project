from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth.hashers import make_password
from rest_framework_simplejwt.tokens import RefreshToken
from myproject.settings import db
from datetime import datetime, timedelta
import random

from drf_spectacular.utils import extend_schema 
from .serializers import SignUpSerializer, SendOTPSerializer, VerifyOTPSerializer


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
# 2. LOGIN - SEND OTP VIEW (Email Based)
# ==========================================
class SendOTPView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=SendOTPSerializer, responses={200: dict})
    def post(self, request):
        serializer = SendOTPSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            
           
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

            return Response({
                "message": f"OTP successfully sent to {email}!",
                "otp_testing_only": otp  
            }, status=status.HTTP_200_OK)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ==========================================
# 3. LOGIN - VERIFY OTP VIEW (Email Based)
# ==========================================
class VerifyOTPView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=VerifyOTPSerializer, responses={200: dict})
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
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
class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            "message": "Welcome to your protected profile!",
            "user": request.user.username if hasattr(request.user, 'username') else "Authenticated User"
        }, status=status.HTTP_200_OK)


# ==========================================
# 5. LOGOUT VIEW
# ==========================================
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if not refresh_token:
                return Response({"error": "Refresh token is required to logout."}, status=status.HTTP_400_BAD_REQUEST)
                
            token = RefreshToken(refresh_token)
            token.blacklist() 

            return Response({"message": "User logged out successfully!"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": "Invalid token or already logged out."}, status=status.HTTP_400_BAD_REQUEST)