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
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=1000,
        validators=[
            MinLengthValidator(10, "Description must be at least 10 characters long."),
            MaxLengthValidator(1000, "Description cannot exceed 1000 characters."),
        ],
    )
    assignee = UserSerializer(read_only=True)

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
        read_only_fields = ("created_at", "updated_at")
        extra_kwargs = {
            "title": {
                "validators": [
                    MinLengthValidator(3, "Title must be at least 3 characters long."),
                    MaxLengthValidator(100, "Title cannot exceed 100 characters."),
                ]
            }
        }

    def validate_due_date(self, value):
        if value and (value < timezone.now().date() or value > timezone.now().date().replace(year=timezone.now().year + 1)):
            raise serializers.ValidationError(
                "Due date must be in the future and within one year from today."
            )
        return value

    def validate(self, data):
        project_id = data.get('project_id')
        if not project_id:
            raise serializers.ValidationError({"project_id": "Project ID is required."})

        try:
            project = Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            raise serializers.ValidationError({"project_id": "Invalid Project ID"})

        request = self.context.get('request')
        if project.manager != request.user:
            raise serializers.ValidationError("Only project manager can create tasks.")

        return data

    def validate_assigned_to(self, value):
        if not value:
            raise serializers.ValidationError("At least one user must be assigned.")
        
        user_ids = [user.id for user in value]
        existing_users = User.objects.filter(id__in=user_ids)
        
        if len(existing_users) != len(value):
            raise serializers.ValidationError("One or more invalid user IDs.")
        
        return value

    def create(self, validated_data):
        assigned_users = validated_data.pop('assigned_to')
        task = Task.objects.create(**validated_data)
        task.assigned_to.set(assigned_users)
        return task

    def update(self, instance, validated_data):
        project_id = validated_data.get('project_id', None)
        if project_id and project_id != instance.project.id:
            raise serializers.ValidationError("Project ID cannot be changed.")

        if "assigned_to" in validated_data:
            assigned_to_data = validated_data.pop("assigned_to", [])
            assigned_users = self.validate_assigned_to(assigned_to_data)
            instance.assigned_to.set(assigned_users)

        return super().update(instance, validated_data)



class ProjectSerializer(serializers.ModelSerializer):
    title = serializers.CharField(
        required=True,
        validators=[
            MinLengthValidator(3, message="Title must be at least 3 characters long."),
            MaxLengthValidator(100, message="Title cannot exceed 100 characters."),
        ],
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        validators=[
            MaxLengthValidator(
                1000, message="Description cannot exceed 1000 characters."
            )
        ],
    )

    total_members = serializers.SerializerMethodField(read_only=True)

    project_members = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), many=True, required=False, allow_empty=True
    )

    class Meta:
        model = Project
        fields = [
            "id",
            "title",
            "description",
            "manager",
            "created_at",
            "updated_at",
            "project_members",
            "total_members",
        ]
        read_only_fields = [
            "id",
            "manager",
            "created_at",
            "updated_at",
            "total_members",
        ]

    def get_total_members(self, obj):
        return obj.project_members.count()

    def validate(self, data):

        if "title" in data and not data["title"].strip():
            raise serializers.ValidationError(
                {"title": "Title cannot be empty or just whitespace."}
            )

        if "project_members" in data:
            members = data["project_members"]
            if len(set(members)) != len(members):
                raise serializers.ValidationError(
                    {"project_members": "Duplicate members are not allowed."}
                )

        return data

    def create(self, validated_data):
        project_members = validated_data("project_members", [])

        project = Project.objects.create(**validated_data)

        if project_members:
            project.project_members.add(*project_members)

        return project

    def update(self, instance, validated_data):
        if "project_members" in validated_data:
            members = validated_data.pop("project_members")
            instance.project_members.clear()
            if members:
                instance.project_members.add(*members)

        return super().update(instance, validated_data)


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

    def save(self, **kwargs):
        kwargs["task"] = self.context["task"]
        return super().save(**kwargs)


class CommentSerializer(serializers.ModelSerializer):
    created_by = serializers.StringRelatedField(read_only=True)
    task = serializers.PrimaryKeyRelatedField(
        queryset=Task.objects.all(), required=False
    )

    class Meta:
        model = Comment
        fields = ["id", "content", "task", "created_by", "created_at", "updated_at"]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]

    def create(self, validated_data):
        content = validated_data.get("content", "").strip()

        if not content:
            raise serializers.ValidationError(
                {"content": "Content field cannot be empty."}
            )

        return super().create(validated_data)
