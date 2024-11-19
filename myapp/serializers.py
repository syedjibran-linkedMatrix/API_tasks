from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Project, Task

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

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ('id', 'username', 'email')



class TaskSerializer(serializers.ModelSerializer):
    assignee = UserSerializer(read_only=True)
    assigned_to = UserSerializer(many=True, read_only=True)  
    project_title = serializers.CharField(source='project.title', read_only=True)

    class Meta:
        model = Task
        fields = (
            'id', 'title', 'description', 'project', 'project_title',
            'status', 'assignee', 'assigned_to', 'due_date', 'created_at', 'updated_at'
        )
        read_only_fields = ('project_title',)


class ProjectSerializer(serializers.ModelSerializer):
    manager = serializers.ReadOnlyField(source='manager.username')
    tasks = TaskSerializer(many=True, read_only=True)
    
    class Meta:
        model = Project
        fields = ('id', 'title', 'description', 'manager', 'created_at', 'updated_at', 'project_members', 'tasks')
    



