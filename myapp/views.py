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
        serializer.save(manager=self.request.user)

    def update(self, request, *args, **kwargs):
        project = self.get_object()
        if project.manager != request.user and not request.user.is_staff:
            return Response(
                {'detail': 'Only the project manager or an admin can update this project.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def add_members(self, request, pk=None):
        project = self.get_object()
        if project.manager != request.user and not request.user.is_staff:
            return Response(
                {'detail': 'Only project manager or admin can add members'},
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

        project.project_members.add(*existing_users)
        return Response(
            {'detail': 'Members added successfully'},
            status=status.HTTP_200_OK
        )


class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        project_id = self.request.query_params.get('project_id', None)
        if project_id is None:
            raise ValidationError({"error": "ProjectId must be given"})
        queryset = Task.objects.filter(project_id=project_id)
        
        return queryset

    def perform_create(self, serializer):
        project = Project.objects.get(pk=serializer.validated_data['project'].id)
        if project.manager != self.request.user:
            raise PermissionDenied("Only project managers can create tasks.")
        serializer.save(assignee=project.manager)

    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        task = self.get_object()
        if task.project.manager != request.user:
            return Response(
                {"error": "Only project managers can assign tasks"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            assignee_id = request.data.get('assignee_id')
            assignee = get_user_model().objects.get(pk=assignee_id)
            task.assignee = assignee
            task.save()
            serializer = self.get_serializer(task)
            return Response(serializer.data)
        except get_user_model().DoesNotExist:
            return Response(
                {"error": "User not found"},
                status=status.HTTP_404_NOT_FOUND
            )
