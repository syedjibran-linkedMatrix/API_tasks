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
    assigned_to = serializers.PrimaryKeyRelatedField(
        many=True, 
        queryset=User.objects.all(),
        required=True
    )

    description = serializers.CharField(
        required=False, 
        allow_blank=True, 
        allow_null=True,
        max_length=1000,
        validators=[
            MinLengthValidator(10, message="Description must be at least 10 characters long."),
            MaxLengthValidator(1000, message="Description cannot exceed 1000 characters.")
        ]
    )

    project_title = serializers.CharField(
        source='project.title', 
        read_only=True
    )
    assignee = UserSerializer(read_only=True)

    class Meta:
        model = Task
        fields = (
            'id', 'title', 'description', 
            'project', 'project_title',
            'status', 'assignee', 'assigned_to', 
            'due_date', 'created_at', 'updated_at',
        )
        read_only_fields = (
            'project', 'project_title', 
            'created_at', 'updated_at', 
        )
        extra_kwargs = {
            'title': {
                'validators': [
                    MinLengthValidator(3, message="Title must be at least 3 characters long."),
                    MaxLengthValidator(100, message="Title cannot exceed 100 characters.")
                ]
            }
        }


    def validate(self, data):
        if 'title' in data and not data['title'].strip():
            raise serializers.ValidationError({
                'title': 'Title cannot be empty or just whitespace.'
            })

        if 'assigned_to' in data:
            assigned_users = data['assigned_to']
            if len(set(assigned_users)) != len(assigned_users):
                raise serializers.ValidationError({
                    'assigned_to': 'Duplicate users are not allowed.'
                })

        return data

    def validate_due_date(self, value):
        if value:
            if value < timezone.now().date():
                raise serializers.ValidationError("Due date must be in the future.")
            
            max_due_date = timezone.now().date().replace(year=timezone.now().year + 1)
            if value > max_due_date:
                raise serializers.ValidationError("Due date cannot be more than one year in the future.")
        
        return value

    def create(self, validated_data):
        assigned_to_users = validated_data.pop('assigned_to', [])
        task = Task.objects.create(**validated_data)
        
        if assigned_to_users:
            task.assigned_to.add(*assigned_to_users)
        
        return task

    def update(self, instance, validated_data):
        if 'assigned_to' in validated_data:
            assigned_to_users = validated_data.pop('assigned_to')
            instance.assigned_to.clear()
            if assigned_to_users:
                instance.assigned_to.add(*assigned_to_users)
        
        return super().update(instance, validated_data)



class ProjectSerializer(serializers.ModelSerializer):
    title = serializers.CharField(
        required=True,
        validators=[
            MinLengthValidator(3, message="Title must be at least 3 characters long."),
            MaxLengthValidator(100, message="Title cannot exceed 100 characters.")
        ]
    )
    description = serializers.CharField(
        required=False, 
        allow_blank=True, 
        allow_null=True,
        validators=[
            MaxLengthValidator(1000, message="Description cannot exceed 1000 characters.")
        ]
    )
    
    total_members = serializers.SerializerMethodField(read_only=True)
    
    project_members = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        many=True,
        required=False,
        allow_empty=True
    )

    class Meta:
        model = Project
        fields = [
            'id', 'title', 'description', 
            'manager', 'created_at', 'updated_at', 
            'project_members', 'total_members'
        ]
        read_only_fields = [
            'id', 'manager', 
            'created_at', 'updated_at', 
            'total_members'
        ]

    def get_total_members(self, obj):
        return obj.project_members.count()


    def validate(self, data):

        if 'title' in data and not data['title'].strip():
            raise serializers.ValidationError({
                'title': 'Title cannot be empty or just whitespace.'
            })

        if 'project_members' in data:
            members = data['project_members']
            if len(set(members)) != len(members):
                raise serializers.ValidationError({
                    'project_members': 'Duplicate members are not allowed.'
                })

        return data

    def create(self, validated_data):
        project_members = validated_data.pop('project_members', [])
        
        project = Project.objects.create(**validated_data)
        
        if project_members:
            project.project_members.add(*project_members)
        
        return project

    def update(self, instance, validated_data):
        if 'project_members' in validated_data:
            members = validated_data.pop('project_members')
            instance.project_members.clear()
            if members:
                instance.project_members.add(*members)
        
        return super().update(instance, validated_data)
    

class AddMembersSerializer(serializers.Serializer):
    user_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False,
        write_only=True
    )

    def validate_user_ids(self, value):
        project = self.context.get('project')
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
