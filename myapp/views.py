from django.forms import ValidationError
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from .models import Project, Task
from .serializers import UserRegistrationSerializer, UserLoginSerializer, ProjectSerializer, TaskSerializer
from .custom_permissions import IsProjectManagerOrReadOnly
from rest_framework.decorators import action
from rest_framework.response import Response
from .serializers import (
    ProjectSerializer, TaskSerializer
)
from rest_framework.exceptions import PermissionDenied



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
    permission_classes = [permissions.IsAuthenticated, IsProjectManagerOrReadOnly]

    def get_queryset(self):
        return Project.objects.all()

    def perform_create(self, serializer):
        serializer.save(manager=self.request.user)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        return context


class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated, IsProjectManagerOrReadOnly]

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

    def get_serializer_context(self):
        context = super().get_serializer_context()
        return context

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
