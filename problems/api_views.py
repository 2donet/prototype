# problems/api_views.py
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.contrib.auth import get_user_model
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .models import Problem, ProblemActivity
from .serializers import ProblemSerializer, ProblemDetailSerializer
from project.models import Project
from task.models import Task
from need.models import Need
from skills.models import Skill

User = get_user_model()

import json
import logging
from django.utils import timezone
logger = logging.getLogger(__name__)


class IsOwnerOrCanEdit(permissions.BasePermission):
    """
    Custom permission to only allow users who can edit the problem to modify it.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions for anyone who can view
        if request.method in permissions.SAFE_METHODS:
            return obj.can_be_viewed_by(request.user)
        
        # Write permissions only for those who can edit
        return obj.can_be_edited_by(request.user)


class ProblemViewSet(viewsets.ModelViewSet):
    """
    API endpoint for problems CRUD operations
    """
    queryset = Problem.objects.all()
    serializer_class = ProblemSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrCanEdit]
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ProblemDetailSerializer
        return ProblemSerializer
    
    def get_queryset(self):
        """Filter problems based on user permissions and query parameters"""
        queryset = Problem.objects.select_related(
            'created_by', 'to_project', 'to_task', 'to_need'
        ).prefetch_related('assigned_to', 'skills')
        
        # Filter by parent object
        project_id = self.request.query_params.get('project')
        task_id = self.request.query_params.get('task')
        need_id = self.request.query_params.get('need')
        
        if project_id:
            queryset = queryset.filter(
                Q(to_project=project_id) |
                Q(to_task__to_project=project_id) |
                Q(to_need__to_project=project_id)
            )
        elif task_id:
            queryset = queryset.filter(to_task=task_id)
        elif need_id:
            queryset = queryset.filter(to_need=need_id)
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter and status_filter != 'all':
            queryset = queryset.filter(status=status_filter)
        
        # Filter by priority
        priority_filter = self.request.query_params.get('priority')
        if priority_filter and priority_filter != 'all':
            queryset = queryset.filter(priority=priority_filter)
        
        # Filter by assignment
        assigned_filter = self.request.query_params.get('assigned')
        if assigned_filter == 'me' and self.request.user.is_authenticated:
            queryset = queryset.filter(assigned_to=self.request.user)
        elif assigned_filter == 'unassigned':
            queryset = queryset.filter(assigned_to__isnull=True)
        
        # Apply permission filtering
        if self.request.user.is_authenticated:
            # This is a simplified approach - in production you might want to optimize this
            filtered_ids = []
            for problem in queryset:
                if problem.can_be_viewed_by(self.request.user):
                    filtered_ids.append(problem.id)
            queryset = queryset.filter(id__in=filtered_ids)
        else:
            # Anonymous users can only see public problems
            queryset = queryset.filter(visibility='public')
        
        return queryset.distinct()
    
    def perform_create(self, serializer):
        """Set the creator when creating a problem"""
        serializer.save(created_by=self.request.user)
        
        # Create activity log
        problem = serializer.instance
        ProblemActivity.objects.create(
            problem=problem,
            user=self.request.user,
            activity_type='created',
            desc=f"Problem '{problem.name}' was created"
        )
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def assign_user(self, request, pk=None):
        """Assign a user to this problem"""
        problem = self.get_object()
        
        if not problem.can_be_edited_by(request.user):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({'error': 'user_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user_to_assign = User.objects.get(id=user_id)
            
            if user_to_assign in problem.assigned_to.all():
                return Response({'error': 'User already assigned'}, status=status.HTTP_400_BAD_REQUEST)
            
            problem.assign_user(user_to_assign)
            
            # Return updated problem data
            serializer = self.get_serializer(problem)
            return Response(serializer.data)
            
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error assigning user: {str(e)}")
            return Response({'error': 'An error occurred'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def unassign_user(self, request, pk=None):
        """Unassign a user from this problem"""
        problem = self.get_object()
        
        if not problem.can_be_edited_by(request.user):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({'error': 'user_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user_to_unassign = User.objects.get(id=user_id)
            
            if user_to_unassign not in problem.assigned_to.all():
                return Response({'error': 'User not assigned'}, status=status.HTTP_400_BAD_REQUEST)
            
            problem.unassign_user(user_to_unassign)
            
            # Return updated problem data
            serializer = self.get_serializer(problem)
            return Response(serializer.data)
            
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error unassigning user: {str(e)}")
            return Response({'error': 'An error occurred'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def update_status(self, request, pk=None):
        """Update problem status"""
        problem = self.get_object()
        
        if not problem.can_be_edited_by(request.user):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        new_status = request.data.get('status')
        if new_status not in dict(Problem.STATUS_CHOICES):
            return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)
        
        old_status = problem.status
        problem.status = new_status
        
        # Handle resolution for solved problems
        if new_status == 'solved' and not problem.resolved_at:
            problem.resolved_at = timezone.now()
            problem.resolution = request.data.get('resolution', '')
        elif new_status != 'solved':
            problem.resolved_at = None
            problem.resolution = ''
        
        problem.save()
        
        # Create activity log
        ProblemActivity.objects.create(
            problem=problem,
            user=request.user,
            activity_type='status_changed',
            desc=f"Status changed from '{old_status}' to '{new_status}'"
        )
        
        serializer = self.get_serializer(problem)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def activities(self, request, pk=None):
        """Get problem activities"""
        problem = self.get_object()
        
        if not problem.can_be_viewed_by(request.user):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        activities = problem.activities.select_related('user').order_by('-created_at')[:20]
        
        activity_data = []
        for activity in activities:
            activity_data.append({
                'id': activity.id,
                'activity_type': activity.activity_type,
                'activity_type_display': activity.get_activity_type_display(),
                'desc': activity.desc,
                'user': activity.user.username if activity.user else 'System',
                'created_at': activity.created_at.isoformat(),
            })
        
        return Response({'activities': activity_data})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def filtered_problems_api(request):
    """
    AJAX endpoint for filtering problems - similar to filtered_comments_api
    """
    try:
        data = json.loads(request.body) if request.body else {}
        
        # Get filtering parameters
        project_id = data.get('project_id')
        statuses = data.get('statuses', [])
        priorities = data.get('priorities', [])
        assigned_filter = data.get('assigned')
        
        if not project_id:
            return Response({'error': 'project_id is required'}, status=400)
        
        # Get project and check permissions
        try:
            project = Project.objects.get(id=project_id)
            if not project.user_can_view(request.user):
                return Response({'error': 'Permission denied'}, status=403)
        except Project.DoesNotExist:
            return Response({'error': 'Project not found'}, status=404)
        
        # Build queryset
        problems = Problem.objects.filter(
            Q(to_project=project) |
            Q(to_task__to_project=project) |
            Q(to_need__to_project=project)
        ).select_related(
            'created_by', 'to_project', 'to_task', 'to_need'
        ).prefetch_related('assigned_to', 'skills').distinct()
        
        # Apply filters
        if statuses:
            problems = problems.filter(status__in=statuses)
        
        if priorities:
            problems = problems.filter(priority__in=priorities)
        
        if assigned_filter == 'me':
            problems = problems.filter(assigned_to=request.user)
        elif assigned_filter == 'unassigned':
            problems = problems.filter(assigned_to__isnull=True)
        
        # Apply permission filtering
        filtered_problems = []
        for problem in problems:
            if problem.can_be_viewed_by(request.user):
                filtered_problems.append(problem)
        
        # Render problems HTML
        context = {
            'problems': filtered_problems,
            'user': request.user,
            'project': project,
        }
        
        problems_html = render_to_string('problems/problems_list_partial.html', context, request=request)
        
        return Response({
            'success': True,
            'problems_html': problems_html,
            'total_count': len(filtered_problems),
            'applied_filters': {
                'statuses': statuses,
                'priorities': priorities,
                'assigned': assigned_filter,
            }
        })
        
    except json.JSONDecodeError:
        return Response({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error filtering problems: {str(e)}")
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
def search_users_for_assignment(request):
    """
    Search users that can be assigned to problems
    Used for autocomplete in assignment forms
    """
    query = request.GET.get('q', '').strip()
    project_id = request.GET.get('project_id')
    
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    # Base user search
    users = User.objects.filter(
        Q(username__icontains=query) | 
        Q(first_name__icontains=query) | 
        Q(last_name__icontains=query)
    ).select_related('profile')[:10]
    
    # If project_id is provided, prioritize project members
    if project_id:
        try:
            project = Project.objects.get(id=project_id)
            # Get project members first
            project_members = users.filter(membership__project=project).distinct()
            # Get non-members
            non_members = users.exclude(membership__project=project).distinct()
            # Combine with members first
            users = list(project_members) + list(non_members)
        except Project.DoesNotExist:
            pass
    
    results = []
    for user in users[:10]:  # Limit to 10 results
        results.append({
            'id': user.id,
            'username': user.username,
            'full_name': f"{user.first_name} {user.last_name}".strip() or user.username,
            'avatar_url': getattr(user.profile, 'avatar_small_url', '/static/icons/default-avatar.svg') if hasattr(user, 'profile') else '/static/icons/default-avatar.svg'
        })
    
    return JsonResponse({'results': results})