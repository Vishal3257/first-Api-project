from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth.hashers import make_password
from rest_framework_simplejwt.tokens import RefreshToken
from myproject.settings import db
from datetime import datetime, timedelta
import random
import resend  # असली ईमेल भेजने के लिए Resend लाइब्रेरी इम्पोर्ट की
import os      # Environment Variables रीड करने के लिए

from django.conf import settings
from drf_spectacular.utils import extend_schema 
from .serializers import SignUpSerializer, SendOTPSerializer, VerifyOTPSerializer

# नई backends.py फ़ाइल से आपकी कस्टम क्लास यहाँ इम्पोर्ट हो रही है
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
# 2. LOGIN - SEND OTP VIEW (Resend HTTP API Integration)
# ==========================================
class SendOTPView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=SendOTPSerializer, responses={200: dict})
    def post(self, request):
        serializer = SendOTPSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email'].lower()  
            
            # Check if user exists
            user = db.users.find_one({"email": email})
            if not user:
                return Response({"error": "User with this email not found!"}, status=status.HTTP_404_NOT_FOUND)

            # Generate OTP
            otp = str(random.randint(100000, 999999))
            expires_at = datetime.utcnow() + timedelta(minutes=5)

            # Save to Database (वर्कर क्रैश न होने के कारण यह अब 100% सेव होगा)
            db.otps.update_one(
                {"email": email},
                {"$set": {"otp": otp, "expires_at": expires_at}},
                upsert=True
            )

            # --- RESEND HTTP API FOR REAL EMAIL DELIVERY ON RENDER ---
            email_status = "Sent Successfully"
            try:
                # Render के Environment Variables से API Key उठाएगा
                resend.api_key = os.environ.get("RESEND_API_KEY")
                
                # अगर Render पर सेट करना भूल जाओ, तो बैकअप के लिए तुम्हारी असली Key यहाँ काम करेगी
                if not resend.api_key:
                    resend.api_key = "re_JH69DfUg_9F398kKge4Tb2DXD4tdbPDEe" 

                params = {
                    "from": "onboarding@resend.dev",  # Resend के फ्री टियर के लिए यही रहेगा
                    "to": [email],                    # यूजर की असली ईमेल आईडी (जैसे vt464670@gmail.com)
                    "subject": "Your OTP Code",
                    "html": f"<strong>Your OTP is: {otp}</strong><br>Valid for 5 minutes."
                }

                # यह HTTP POST के जरिए जाता है, इसलिए Render इसे ब्लॉक नहीं कर सकता
                resend.Emails.send(params)
                email_status = f"OTP Sent via Resend API Successfully to {email}!"
                
            except Exception as email_error:
                email_status = f"Failed to send email via API: {str(email_error)}"
            # ------------------------------------------------------------------

            return Response({
                "message": f"OTP processed for {email}!",
                "email_delivery_status": email_status,
                "otp": otp  # टेस्टिंग के लिए स्वैगर में भी ओटीपी दिखता रहेगा
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
# 4. PROTECTED PROFILE VIEW (Correct Syntax)
# ==========================================
class ProfileView(APIView):
    authentication_classes = [SafeJWTAuthentication]
    permission_classes = [IsAuthenticated]

    
    @extend_schema(
        responses={200: dict},
        security=[{'jwtAuth': []}]  
    )
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