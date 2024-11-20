from datetime import timezone
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Project, Task, Document
from django.core.validators import MinLengthValidator, MaxLengthValidator

User = get_user_model()
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
    assigned_to = serializers.PrimaryKeyRelatedField(
        many=True, 
        queryset=User.objects.all(),
    )
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    
    project_title = serializers.CharField(source='project.title', read_only=True)

    class Meta:
        model = Task
        fields = (
            'id', 'title', 'description', 'project', 'project_title',
            'status', 'assignee', 'assigned_to', 'due_date', 'created_at', 'updated_at'
        )
        read_only_fields = ('project', 'project_title', 'created_at', 'updated_at')

    def create(self, validated_data):
        assigned_to_users = validated_data.pop('assigned_to', [])
        
        task = Task.objects.create(**validated_data)
        
        if assigned_to_users:
            task.assigned_to.add(*assigned_to_users)
        
        return task

    def validate_due_date(self, value):
        if value and value < timezone.now().date():
            raise serializers.ValidationError("Due date must be in the future.")
        return value



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


    def validate_title(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Title must not be empty.")
        return value

    def validate(self, data):
        if 'description' in data and data['description'] and not data['description'].strip():
            raise serializers.ValidationError({'description': "Description cannot be empty if provided."})
        
        return data
    

class AddMembersSerializer(serializers.Serializer):
    user_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False,
        write_only=True
    )

    def validate_user_ids(self, value):
        project = self.context.get('project')
        User = get_user_model()

        existing_users = User.objects.filter(id__in=value)
        non_existent_ids = set(value) - set(existing_users.values_list('id', flat=True))
        if non_existent_ids:
            raise serializers.ValidationError({
                'detail': 'Some user IDs do not exist',
                'non_existent_user_ids': list(non_existent_ids)
            })

        existing_members = project.project_members.filter(id__in=value)
        if existing_members.exists():
            raise serializers.ValidationError({
                'detail': 'Some users are already members of this project',
                'existing_member_ids': list(existing_members.values_list('id', flat=True))
            })

        return value
    
class RemoveMembersSerializer(serializers.Serializer):
    user_ids = serializers.ListField(
        child=serializers.IntegerField(), allow_empty=False, write_only=True
    )

    def validate_user_ids(self, value):
        project = self.context.get('project')

        existing_users = User.objects.filter(id__in=value)
        non_existent_ids = set(value) - set(existing_users.values_list('id', flat=True))
        if non_existent_ids:
            raise serializers.ValidationError(
                {
                    'detail': 'Some user IDs do not exist',
                    'non_existent_user_ids': list(non_existent_ids),
                }
            )

        non_members = existing_users.exclude(id__in=project.project_members.values_list('id', flat=True))
        if non_members.exists():
            raise serializers.ValidationError(
                {
                    'detail': 'Some users are not members of this project',
                    'non_project_member_ids': list(non_members.values_list('id', flat=True)),
                }
            )

        return value
    

class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ['id', 'file', 'uploaded_by', 'uploaded_at']
        read_only_fields = ['uploaded_by', 'uploaded_at']

    def save(self, **kwargs):
        kwargs['task'] = self.context['task']
        return super().save(**kwargs)


    



