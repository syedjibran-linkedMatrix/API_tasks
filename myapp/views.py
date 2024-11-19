from django.forms import ValidationError
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from .models import Project, Task
from .serializers import UserRegistrationSerializer, UserLoginSerializer, ProjectSerializer, TaskSerializer
from rest_framework.decorators import action
from rest_framework.response import Response
from .serializers import (
    ProjectSerializer, TaskSerializer
)
from rest_framework.exceptions import PermissionDenied
from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework import serializers





@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def register_user(request):
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user_id': user.id,
            'username': user.username
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login_user(request):
    serializer = UserLoginSerializer(data=request.data)
    if serializer.is_valid():
        username = serializer.validated_data['username']
        password = serializer.validated_data['password']
        user = authenticate(username=username, password=password)
        
        if user:
            token, _ = Token.objects.get_or_create(user=user)
            return Response({
                'token': token.key,
                'user_id': user.id,
                'username': user.username
            })
        return Response(
            {'error': 'Invalid credentials'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def logout_user(request):
    request.user.auth_token.delete()
    return Response(status=status.HTTP_200_OK)


class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Project.objects.filter(
            Q(project_members=self.request.user) | 
            Q(manager=self.request.user)
        ).distinct()

    def perform_create(self, serializer):
        if self.request.user.role != 'project_manager':
            raise serializers.ValidationError("Only project managers can create projects")
        
        serializer.save(manager=self.request.user)


    def update(self, request, *args, **kwargs):
        project = self.get_object()
        if project.manager != request.user and not request.user.is_staff:
            return Response(
                {'detail': 'Only the project manager or an admin can update this project.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        project = self.get_object()

        if project.manager != request.user and not request.user.is_staff:
            return Response(
                {'detail': 'Only the project manager or an admin can delete this project.'},
                status=status.HTTP_403_FORBIDDEN
            )

        self.perform_destroy(project)
        return Response(
            {'detail': 'Project deleted successfully.'},
            status=status.HTTP_204_NO_CONTENT
        )
    #http://localhost:8000/api/projects/1/add_members/
    @action(detail=True, methods=['post'])
    def add_members(self, request, pk=None):
        project = self.get_object()
        
        if not self.check_project_permission(project, request.user):
            return Response(
                {'detail': 'Only project manager or admin can add members'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        user_ids = request.data.get('user_ids', [])
        if not isinstance(user_ids, list):
            return Response(
                {'detail': 'user_ids must be a list'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            validated_user_ids = self.get_serializer().validate_user_ids(user_ids)
        except serializers.ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        
        User = get_user_model()
        existing_users = User.objects.filter(id__in=validated_user_ids)
        
        project.project_members.add(*existing_users)
        return Response(
            {'detail': 'Members added successfully'},
            status=status.HTTP_200_OK
        )
        
    #http://localhost:8000/api/projects/12/remove_members/
    @action(detail=True, methods=['post'])
    def remove_members(self, request, pk=None):
        project = self.get_object()
        
        if project.manager != request.user and not request.user.is_staff:
            return Response(
                {'detail': 'Only project manager or admin can remove members'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        user_ids = request.data.get('user_ids', [])
        
        if not user_ids:
            return Response(
                {'detail': 'No user IDs provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        User = get_user_model()
        existing_users = User.objects.filter(id__in=user_ids)

        non_existent_ids = set(user_ids) - set(existing_users.values_list('id', flat=True))
        if non_existent_ids:
            return Response(
                {
                    'detail': 'Some user IDs do not exist',
                    'non_existent_user_ids': list(non_existent_ids)
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        non_members = existing_users.exclude(id__in=project.project_members.values_list('id', flat=True))
        if non_members.exists():
            return Response(
                {
                    'detail': 'Some users are not members of this project',
                    'non_project_member_ids': list(non_members.values_list('id', flat=True))
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        project_members_to_remove = existing_users.filter(id__in=project.project_members.values_list('id', flat=True))
        project.project_members.remove(*project_members_to_remove)
        
        return Response(
            {'detail': 'Members removed successfully'},
            status=status.HTTP_200_OK
        )
    


class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        project_id = self.request.query_params.get('project_id', None)
        if project_id is None:
            raise ValidationError({"error": "ProjectId must be given"})
        return Task.objects.filter(
            Q(assigned_to=self.request.user) |
            Q(project__manager=self.request.user)
        ).distinct()

    def perform_create(self, serializer):
        project_id = serializer.validated_data['project'].id
        project = Project.objects.get(pk=project_id)
        
        if project.manager != self.request.user:
            raise PermissionDenied("Only project managers can create tasks.")
        
        assigned_to_users = self.request.data.get('assigned_to', [])
        
        if not assigned_to_users:
            raise ValidationError({"error": "At least one assignee must be specified."})
        
        users = get_user_model().objects.filter(id__in=assigned_to_users)
        
        task = serializer.save(assignee=project.manager)
        task.assigned_to.set(users)
        task.save()

    def update(self, request, *args, **kwargs):
        #http://localhost:8000/api/tasks/5/?project_id=1
        project_id = self.request.query_params.get('project_id')
        if not project_id:
            return Response(
                {"error": "ProjectId must be given in query parameters."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        task = self.get_object()
        if str(task.project.id) != project_id:
            return Response(
                {"error": "The provided ProjectId does not match the task's project."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if task.project.manager != request.user and not request.user.is_staff:
            return Response(
                {'detail': 'Only the project manager or an admin can update this task.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super().update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        project_id = self.request.query_params.get('project_id')
        if not project_id:
            return Response(
                {"error": "ProjectId must be given in query parameters."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        task = self.get_object()

        if str(task.project.id) != project_id:
            return Response(
                {"error": "The provided ProjectId does not match the task's project."},
                status=status.HTTP_400_BAD_REQUEST
            )
        if task.project.manager != request.user and not request.user.is_staff:
            return Response(
                {'detail': 'Only the project manager or an admin can delete this task.'},
                status=status.HTTP_403_FORBIDDEN
            )
        self.perform_destroy(task)
        return Response(
            {'detail': 'Task deleted successfully.'},
            status=status.HTTP_204_NO_CONTENT
        )
