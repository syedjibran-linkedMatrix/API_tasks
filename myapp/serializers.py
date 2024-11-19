from datetime import timezone
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Project, Task
from django.core.validators import MinLengthValidator, MaxLengthValidator


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
    
    title = serializers.CharField(
        required=True,
        validators=[
            MinLengthValidator(3, message="Task title must be at least 3 characters long."),
            MaxLengthValidator(100, message="Task title cannot exceed 100 characters.")
        ]
    )
    
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        validators=[
            MaxLengthValidator(500, message="Task description cannot exceed 500 characters.")
        ]
    )
    
    due_date = serializers.DateField(
        required=False,
        allow_null=True
    )

    class Meta:
        model = Task
        fields = (
            'id', 'title', 'description', 'project', 'project_title',
            'status', 'assignee', 'assigned_to', 'due_date', 'created_at', 'updated_at'
        )
        read_only_fields = ('project_title', 'created_at', 'updated_at')
    
    def validate_due_date(self, value):
        if value and value < timezone.now().date():
            raise serializers.ValidationError("Due date must be in the future.")
        return value
    
    def validate(self, data):
        if data.get('status') and not data.get('assigned_to'):
            raise serializers.ValidationError({
                "assigned_to": "Tasks with a status must have at least one assignee."
            })
        return data


class ProjectSerializer(serializers.ModelSerializer):
    title = serializers.CharField(required=False)
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = Project
        fields = ['id', 'title', 'description', 'manager', 'created_at', 'updated_at', 'project_members']
        read_only_fields = ['id', 'manager', 'created_at', 'updated_at']

        user_ids = serializers.ListField(
            child=serializers.IntegerField(),
            allow_empty=False
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance:
            self.fields['title'].required = True

    def validate_user_ids(self, value):
        User = get_user_model()
        existing_users = User.objects.filter(id__in=value)
        
        non_existent_ids = set(value) - set(existing_users.values_list('id', flat=True))
        if non_existent_ids:
            raise serializers.ValidationError({
                'detail': 'Some user IDs do not exist',
                'non_existent_user_ids': list(non_existent_ids)
            })
        
        return value

    def validate_title(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Title must not be empty.")
        return value

    def validate(self, data):
        if 'description' in data and data['description'] and not data['description'].strip():
            raise serializers.ValidationError({'description': "Description cannot be empty if provided."})
        
        return data


    



