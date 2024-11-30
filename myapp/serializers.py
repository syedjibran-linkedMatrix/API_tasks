from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Project, Task, Document, Comment
from django.core.validators import MinLengthValidator, MaxLengthValidator
from django.utils import timezone


User = get_user_model()


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = get_user_model()
        fields = ("id", "username", "email", "password")

    def create(self, validated_data):
        user = get_user_model().objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
        )
        return user


class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ("id", "username", "email")


class TaskSerializer(serializers.ModelSerializer):
    project_id = serializers.IntegerField(write_only=True)
    class Meta:
        model = Task
        fields = (
            "id",
            "title",
            "description",
            "project_id",
            "status",
            "assignee",
            "assigned_to",
            "due_date",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("assignee","created_at", "updated_at")
        extra_kwargs = {
            "title": {
                "validators": [
                    MinLengthValidator(3, "Title must be at least 3 characters long."),
                    MaxLengthValidator(100, "Title cannot exceed 100 characters."),
                ]
            }
        }


    def validate(self, data):
        project_id = data.get('project_id')

        instance = getattr(self, 'instance', None)
        if instance:
            if project_id != instance.project.id:
                raise serializers.ValidationError("Project ID cannot be changed.")
        else:
            if not project_id:
                raise serializers.ValidationError({"project_id": "Project ID is required."})


        due_date = data.get('due_date')
        if due_date and (due_date < timezone.now().date() or 
                        due_date > timezone.now().date().replace(year=timezone.now().year + 1)):
            raise serializers.ValidationError(
                "Due date must be in the future and within one year from today."
            )
        
        assigned_to = data.get('assigned_to')
        if not assigned_to:
            raise serializers.ValidationError({"assigned_to": "At least one user must be assigned."})
        
        user_ids = [user.id for user in assigned_to]
        existing_users = User.objects.filter(id__in=user_ids)
        
        if len(existing_users) != len(assigned_to):
            raise serializers.ValidationError({"assigned_to": "One or more invalid user IDs."})
        
        return data
    
    def create(self, validated_data):
        project_id = validated_data.pop('project_id')
        project = Project.objects.get(pk=project_id)
        
        validated_data['project'] = project
        validated_data['assignee'] = project.manager
        
        return super().create(validated_data)
    
    

class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = [
            "id", "title", "description", "manager", 
            "created_at", "updated_at", 
            "project_members"
        ]
        read_only_fields = [
            "id", "manager", "created_at", 
            "updated_at"
        ]

    def validate(self, data):
        is_create = self.instance is None

        if is_create:
            title = data.get("title", "").strip()
            if not title:
                raise serializers.ValidationError({"title": "Title is required and cannot be empty."})

            if len(title) < 3:
                raise serializers.ValidationError({"title": "Title must be at least 3 characters long."})

            if len(title) > 100:
                raise serializers.ValidationError({"title": "Title cannot exceed 100 characters."})

        description = data.get("description", "")
        if description and len(description) > 1000:
            raise serializers.ValidationError({"description": "Description cannot exceed 1000 characters."})

        return data
    
    def create(self, validated_data):
        manager = self.context['request'].user
        
        validated_data['manager'] = manager
        
        return super().create(validated_data)


class AddMembersSerializer(serializers.Serializer):
    user_ids = serializers.ListField(
        child=serializers.IntegerField(), allow_empty=False, write_only=True
    )

    def validate_user_ids(self, value):
        project = self.context.get("project")
        existing_users = User.objects.filter(id__in=value)
        non_existent_ids = set(value) - set(existing_users.values_list("id", flat=True))
        if non_existent_ids:
            raise serializers.ValidationError(
                {
                    "detail": "Some user IDs do not exist",
                    "non_existent_user_ids": list(non_existent_ids),
                }
            )

        existing_members = project.project_members.filter(id__in=value)
        if existing_members.exists():
            raise serializers.ValidationError(
                {
                    "detail": "Some users are already members of this project",
                    "existing_member_ids": list(
                        existing_members.values_list("id", flat=True)
                    ),
                }
            )

        return value


class RemoveMembersSerializer(serializers.Serializer):
    user_ids = serializers.ListField(
        child=serializers.IntegerField(), allow_empty=False, write_only=True
    )

    def validate_user_ids(self, value):
        project = self.context.get("project")

        existing_users = User.objects.filter(id__in=value)
        non_existent_ids = set(value) - set(existing_users.values_list("id", flat=True))
        if non_existent_ids:
            raise serializers.ValidationError(
                {
                    "detail": "Some user IDs do not exist",
                    "non_existent_user_ids": list(non_existent_ids),
                }
            )

        non_members = existing_users.exclude(
            id__in=project.project_members.values_list("id", flat=True)
        )
        if non_members.exists():
            raise serializers.ValidationError(
                {
                    "detail": "Some users are not members of this project",
                    "non_project_member_ids": list(
                        non_members.values_list("id", flat=True)
                    ),
                }
            )

        return value


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ["id", "file", "uploaded_by", "uploaded_at"]
        read_only_fields = ["uploaded_by", "uploaded_at"]


    def create(self, validated_data):
        task = self.context.get('task') 

        if task is None:
            raise serializers.ValidationError("Task is required.") 

        user = self.context["request"].user  
        validated_data["task"] = task
        validated_data["uploaded_by"] = user

        return super().create(validated_data)


class CommentSerializer(serializers.ModelSerializer):

    class Meta:
        model = Comment
        fields = ["id", "content", "task", "created_by", "created_at", "updated_at"]
        read_only_fields = ["id", "created_by", "created_at", "updated_at", "task"]

    def validate(self, data):
        content = data.get("content", "").strip()

        if not content:
            raise serializers.ValidationError(
                {"content": "Content field cannot be empty."}
            )

        return data
    
    def create(self, validated_data):
        request = self.context.get('request')
        task = self.context.get('task')

        validated_data['created_by'] = request.user
        validated_data['task'] = task
        
        return super().create(validated_data)
