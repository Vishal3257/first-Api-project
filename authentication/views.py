from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth.hashers import make_password
from rest_framework_simplejwt.tokens import RefreshToken
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import random
import resend
import os

from myproject.settings import db
from drf_spectacular.utils import extend_schema, extend_schema_view
from .serializers import SignUpSerializer, SendOTPSerializer, VerifyOTPSerializer,TodoSerializer
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
# 2. LOGIN - SEND OTP VIEW (Resend HTTP API)
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
            expires_at = timezone.now() + timedelta(minutes=5)

            db.otps.update_one(
                {"email": email},
                {"$set": {"otp": otp, "expires_at": expires_at}},
                upsert=True
            )

            email_status = "Sent Successfully"
            try:
                
                resend.api_key = os.environ.get("RESEND_API_KEY", "re_JH69DfUg_9F398kKge4Tb2DXD4tdbPDEe")

                params = {
                    "from": "onboarding@resend.dev",
                    "to": [email],
                    "subject": "Your Login OTP Code",
                    "html": f"<strong>Your OTP Code is: {otp}</strong><br>Valid for 5 minutes. Please do not share it."
                }

                resend.Emails.send(params)
                email_status = f"OTP Sent via Resend API successfully to {email}!"
                
            except Exception as email_error:
                email_status = f"Resend API Failed: {str(email_error)}"

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

            current_time = timezone.now()
            record_expiry = otp_record['expires_at']
            
            if record_expiry.tzinfo is None:
                record_expiry = timezone.make_aware(record_expiry)

            if current_time > record_expiry:
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
    





from django.contrib.auth.hashers import check_password
from bson.objectid import ObjectId
from myproject.settings import db

# ==========================================
# 1. NORMAL LOGIN VIEW (Username + Password)
# ==========================================
class NormalLoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request={"application/json": {"type": "object", "properties": {"username": {"type": "string"}, "password": {"type": "string"}}, "required": ["username", "password"]}},
        responses={200: dict}
    )
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response({"error": "Username and password are required"}, status=status.HTTP_400_BAD_REQUEST)

        
        user = db.users.find_one({"username": username})
        if not user:
            return Response({"error": "Invalid username or password"}, status=status.HTTP_401_UNAUTHORIZED)

        
        if check_password(password, user['password']):
            
            token = RefreshToken()
            token['user_id'] = str(user['_id'])
            token['username'] = user['username']
            token['email'] = user['email']

            return Response({
                "refresh": str(token),
                "access": str(token.access_token),
                "message": "Login Successful!"
            }, status=status.HTTP_200_OK)
        
        return Response({"error": "Invalid username or password"}, status=status.HTTP_401_UNAUTHORIZED)


# ==========================================
# 2. TODO LIST & CREATE VIEW (GET & POST)
# ==========================================
class TodoListCreateView(APIView):
    authentication_classes = [SafeJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: list})
    def get(self, request):
        """Logged-in user ke saare tasks dekhna"""
        user_id = str(request.user.id)
        todos = list(db.todos.find({"user_id": user_id}))
        
        for todo in todos:
            todo['_id'] = str(todo['_id'])
        return Response(todos, status=status.HTTP_200_OK)

    @extend_schema(request=TodoSerializer, responses={201: dict})
    def post(self, request):
        """Naya task create karna"""
        serializer = TodoSerializer(data=request.data)
        if serializer.is_valid():
            todo_data = {
                "user_id": str(request.user.id),
                "title": serializer.validated_data['title'],
                "description": serializer.validated_data['description'],
                "is_completed": serializer.validated_data['is_completed'],
                "created_at": timezone.now()
            }
            result = db.todos.insert_one(todo_data)
            todo_data['_id'] = str(result.inserted_id)
            return Response(todo_data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ==========================================
# 3. TODO PATCH & DELETE VIEW (PATCH & DELETE)
# ==========================================
class TodoDetailUpdateDeleteView(APIView):
    authentication_classes = [SafeJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request={"application/json": {"type": "object", "properties": {"is_completed": {"type": "boolean"}}}},
        responses={200: dict}
    )
    def patch(self, request, todo_id):
        """Task ko complete/incomplete mark karna (Partial Update)"""
        user_id = str(request.user.id)
        is_completed = request.data.get('is_completed')

        if is_completed is None:
            return Response({"error": "is_completed field is required"}, status=status.HTTP_400_BAD_REQUEST)

        result = db.todos.update_one(
            {"_id": ObjectId(todo_id), "user_id": user_id},
            {"$set": {"is_completed": is_completed}}
        )

        if result.matched_count == 0:
            return Response({"error": "Todo item not found or unauthorized!"}, status=status.HTTP_404_NOT_FOUND)
        return Response({"message": f"Todo marked as completed: {is_completed}"}, status=status.HTTP_200_OK)

    @extend_schema(responses={200: dict})
    def delete(self, request, todo_id):
        """Kisi task ko delete karna"""
        user_id = str(request.user.id)
        result = db.todos.delete_one({"_id": ObjectId(todo_id), "user_id": user_id})
        
        if result.deleted_count == 0:
            return Response({"error": "Todo item not found or unauthorized!"}, status=status.HTTP_404_NOT_FOUND)
        return Response({"message": "Todo deleted successfully!"}, status=status.HTTP_200_OK)