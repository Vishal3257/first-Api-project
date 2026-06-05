from rest_framework import serializers


class SignUpSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150, required=True)
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, min_length=6, required=True)


class SendOTPSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)


class VerifyOTPSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    otp = serializers.CharField(max_length=6, min_length=6, required=True)