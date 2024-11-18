from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Project

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    
    class Meta:
        model = get_user_model()
        fields = ('id', 'username', 'email', 'password')
    
    def create(self, validated_data):
        user = get_user_model().objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        return user

class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

class ProjectSerializer(serializers.ModelSerializer):
    manager = serializers.ReadOnlyField(source='manager.username')
    is_manager = serializers.SerializerMethodField()

    
    class Meta:
        model = Project
        fields = ('id', 'title', 'description', 'manager', 'created_at', 'updated_at', 'is_manager')
        read_only_fields = ['created_by', 'created_at', 'updated_at']

    def get_is_manager(self, obj):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            return obj.manager == request.user
        return False