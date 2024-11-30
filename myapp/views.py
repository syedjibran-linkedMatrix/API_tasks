from rest_framework import viewsets, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from .models import Project, Task, Document, Comment
from rest_framework.decorators import action
from rest_framework.response import Response
from .serializers import (
    ProjectSerializer,
    TaskSerializer,
    DocumentSerializer,
    UserRegistrationSerializer,
    UserLoginSerializer,
    RemoveMembersSerializer,
    AddMembersSerializer,
    CommentSerializer,
)
from rest_framework.exceptions import PermissionDenied
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.shortcuts import get_object_or_404


User = get_user_model()


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def register_user(request):
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response(
            {"token": token.key, "user_id": user.id, "username": user.username},
            status=status.HTTP_201_CREATED,
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def login_user(request):
    serializer = UserLoginSerializer(data=request.data)
    if serializer.is_valid():
        username = serializer.validated_data["username"]
        password = serializer.validated_data["password"]
        user = authenticate(username=username, password=password)

        if user:
            token, _ = Token.objects.get_or_create(user=user)
            return Response(
                {"token": token.key, "user_id": user.id, "username": user.username}
            )
        return Response(
            {"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def logout_user(request):
    request.user.auth_token.delete()
    return Response(status=status.HTTP_200_OK)


class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(
            Q(project_members=self.request.user) | Q(manager=self.request.user)
        ).distinct()

    def create(self, request, *args, **kwargs):
        if request.user.role != "project_manager":
            raise PermissionDenied("Only project managers can create projects")

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        project = self.get_object()
        if project.manager != request.user and not request.user.is_staff:
            return Response(
                {
                    "detail": "Only the project manager or an admin can update this project."
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        project = self.get_object()

        if project.manager != request.user and not request.user.is_staff:
            return Response(
                {
                    "detail": "Only the project manager or an admin can delete this project."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        self.perform_destroy(project)
        return Response(
            {"detail": "Project deleted successfully."},
            status=status.HTTP_204_NO_CONTENT,
        )

    # http://localhost:8000/api/projects/1/add_members/
    @action(detail=True, methods=["post"])
    def add_members(self, request, pk=None):
        project = self.get_object()

        if project.manager != request.user and not request.user.is_staff:
            return Response(
                {"detail": "Only project manager or admin can add members"},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = AddMembersSerializer(
            data=request.data, context={"project": project}
        )
        serializer.is_valid(raise_exception=True)

        user_ids = serializer.validated_data["user_ids"]
        users_to_add = User.objects.filter(id__in=user_ids)
        project.project_members.add(*users_to_add)

        return Response(
            {"detail": "Members added successfully"}, status=status.HTTP_200_OK
        )

    # http://localhost:8000/api/projects/12/remove_members/
    @action(detail=True, methods=["post"])
    def remove_members(self, request, pk=None):
        project = self.get_object()

        if project.manager != request.user and not request.user.is_staff:
            return Response(
                {"detail": "Only the project manager or admin can remove members"},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = RemoveMembersSerializer(
            data=request.data, context={"project": project}
        )
        serializer.is_valid(raise_exception=True)

        user_ids = serializer.validated_data["user_ids"]
        users_to_remove = User.objects.filter(id__in=user_ids)
        project.project_members.remove(*users_to_remove)

        return Response(
            {"detail": "Members removed successfully"}, status=status.HTTP_200_OK
        )


class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Task.objects.all()

    def get_queryset(self):
        return self.queryset.filter(
            Q(assigned_to=self.request.user) | Q(project__manager=self.request.user)
        ).distinct()

    def create(self, request, *args, **kwargs):
        project_id = request.data.get("project_id")

        try:
            project = Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            raise PermissionDenied("Invalid Project ID")

        if project.manager != request.user:
            raise PermissionDenied("Only the project manager can create tasks.")

        serializer = self.get_serializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        serializer.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        task = self.get_object()

        if task.project.manager != request.user:
            raise PermissionDenied("Only the project manager can update this task.")

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        task = self.get_object()

        if task.project.manager != request.user:
            raise PermissionDenied("Only the project manager can delete this task.")

        self.perform_destroy(task)
        return Response(
            {"detail": "Task deleted successfully."}, status=status.HTTP_204_NO_CONTENT
        )

    @action(detail=True, methods=["post"])
    def upload_document(self, request, pk=None):
        task = get_object_or_404(Task, pk=pk)
        if request.user != task.assignee and request.user not in task.assigned_to.all():
            return Response(
                {
                    "detail": "You do not have permission to upload documents for this task."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = DocumentSerializer(
            data={**request.data, "task": task.id, "uploaded_by": request.user.id}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    # http://localhost:8000/api/tasks/8/documents/
    @action(detail=True, methods=["get"])
    def documents(self, request, pk=None):

        task = get_object_or_404(Task, pk=pk)

        if request.user != task.assignee and request.user not in task.assigned_to.all():
            return Response(
                {
                    "detail": "You do not have permission to view documents for this task."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        documents = task.documents.all()
        serializer = DocumentSerializer(documents, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)

    # http://localhost:8000/api/tasks/8/documents/1/
    @action(
        detail=True,
        url_path="documents/(?P<document_id>[^/.]+)",
        methods=["delete"],
    )
    def delete_document(self, request, pk=None, document_id=None):

        task = get_object_or_404(Task, pk=pk)
        document = get_object_or_404(Document, pk=document_id, task=task)

        if request.user != document.uploaded_by and request.user != task.assignee:
            raise PermissionDenied(
                "You do not have permission to delete this document."
            )

        document.delete()
        return Response(
            {"detail": "Document deleted successfully."},
            status=status.HTTP_204_NO_CONTENT,
        )

    # http://localhost:8000/api/tasks/8/add_comment/
    @action(detail=True, methods=["post"])
    def add_comment(self, request, pk=None):
        task = get_object_or_404(Task, pk=pk)

        if request.user != task.assignee and request.user not in task.assigned_to.all():
            raise Response(
                {"detail": "You do not have permission to add comment for this task."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = CommentSerializer(
            data=request.data, context={"request": request, "task": task}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    # http://localhost:8000/api/tasks/8/comments/
    @action(detail=True, methods=["get"])
    def comments(self, request, pk=None):

        task = get_object_or_404(Task, pk=pk)

        if request.user != task.assignee and request.user not in task.assigned_to.all():
            return Response(
                {"detail": "You do not have permission to view comment for this task."},
                status=status.HTTP_403_FORBIDDEN,
            )

        comments = task.comments.all()
        serializer = CommentSerializer(comments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # http://localhost:8000/api/tasks/8/comments/1/
    @action(
        detail=True,
        url_path="comments/(?P<comment_id>[^/.]+)",
        methods=["delete"],
    )
    def delete_comment(self, request, pk=None, comment_id=None):

        task = get_object_or_404(Task, pk=pk)
        comment = get_object_or_404(Comment, pk=comment_id, task=task)

        if request.user != comment.created_by and request.user != task.assignee:
            raise PermissionDenied("You do not have permission to delete this comment.")

        comment.delete()
        return Response(
            {"detail": "Comment deleted successfully."},
            status=status.HTTP_204_NO_CONTENT,
        )
