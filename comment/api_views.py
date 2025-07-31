from rest_framework import viewsets, permissions, status, views
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import IntegrityError, transaction
from django.db.models import Count
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.decorators import user_passes_test
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from comment.models import Comment, CommentVote, VoteType, CommentStatus
from comment.serializers import (
    CommentSerializer, 
    CommentDetailSerializer, 
    CommentVoteSerializer
)

from django.http import JsonResponse

import json



class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner
        return obj.user == request.user


class CommentViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows comments to be viewed or edited.
    """
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return CommentDetailSerializer
        return CommentSerializer
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def vote(self, request, pk=None):
        """Cast or change a vote on a comment"""
        comment = self.get_object()
        vote_type = request.data.get('vote_type')
        
        if vote_type not in dict(VoteType.choices):
            return Response(
                {'error': f'Invalid vote type. Must be one of {dict(VoteType.choices).keys()}'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            with transaction.atomic():
                # Try to get existing vote
                vote, created = CommentVote.objects.update_or_create(
                    comment=comment,
                    user=request.user,
                    defaults={'vote_type': vote_type}
                )
                
                # Return the updated comment
                serializer = CommentSerializer(comment, context={'request': request})
                return Response(serializer.data)
                
        except IntegrityError:
            return Response(
                {'error': 'Could not process vote'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def remove_vote(self, request, pk=None):
        """Remove a vote from a comment"""
        comment = self.get_object()
        
        try:
            vote = CommentVote.objects.get(comment=comment, user=request.user)
            vote.delete()
            
            # Return the updated comment
            serializer = CommentSerializer(comment, context={'request': request})
            return Response(serializer.data)
            
        except CommentVote.DoesNotExist:
            return Response(
                {'error': 'No vote to remove'},
                status=status.HTTP_404_NOT_FOUND
            )
    


    @action(detail=True, methods=['get'])
    def replies(self, request, pk=None):
        """Get all direct replies to a comment"""
        comment = self.get_object()
        replies = comment.replies.all()
        
        page = self.paginate_queryset(replies)
        if page is not None:
            serializer = CommentSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
            
        serializer = CommentSerializer(replies, many=True, context={'request': request})
        return Response(serializer.data)


class CommentVoteViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows comment votes to be viewed or edited.
    """
    queryset = CommentVote.objects.all()
    serializer_class = CommentVoteSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Optionally restrict to votes by current user"""
        queryset = CommentVote.objects.all()
        user = self.request.query_params.get('user')
        comment = self.request.query_params.get('comment')
        
        if user == 'me':
            queryset = queryset.filter(user=self.request.user)
        if comment:
            queryset = queryset.filter(comment__id=comment)
            
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def filtered_comments_api(request):
    """
    AJAX endpoint for filtering comments with admin controls
    Only accessible to staff/moderators
    """
    if not (request.user.is_staff or request.user.is_superuser):
        return Response({'error': 'Permission denied'}, status=403)

    try:
        # Get filter parameters from request body
        data = json.loads(request.body) if request.body else {}

        statuses = data.get('statuses', ['APPROVED', 'PENDING'])
        object_type = data.get('object_type')  # 'project', 'task', 'need', etc.
        object_id = data.get('object_id')

        # Build the base queryset
        comments = Comment.objects.select_related('user').prefetch_related('replies__user')

        # Filter by object type and ID
        if object_type == 'project' and object_id:
            comments = comments.filter(to_project_id=object_id, parent__isnull=True)
        elif object_type == 'task' and object_id:
            comments = comments.filter(to_task_id=object_id, parent__isnull=True)
        elif object_type == 'need' and object_id:
            comments = comments.filter(to_need_id=object_id, parent__isnull=True)
        elif object_type == 'decision' and object_id:
            comments = comments.filter(to_decision_id=object_id, parent__isnull=True)
        elif object_type == 'membership' and object_id:
            comments = comments.filter(to_membership_id=object_id, parent__isnull=True)
        elif object_type == 'report' and object_id:
            comments = comments.filter(to_report_id=object_id, parent__isnull=True)
        elif object_type == 'problem' and object_id:
            comments = comments.filter(
                to_problem_id=object_id,
                to_task__isnull=True,
                to_project__isnull=True,
                to_need__isnull=True,
                to_decision__isnull=True,
                to_membership__isnull=True,
                to_report__isnull=True,
                parent__isnull=True
            )
        else:
            comments = comments.filter(parent__isnull=True)

        # Apply status filtering
        if statuses:
            comments = comments.filter(status__in=statuses)

        # Get total count before status filtering
        total_comments = Comment.objects.all()
        if object_type == 'project' and object_id:
            total_comments = total_comments.filter(to_project_id=object_id, parent__isnull=True)
        elif object_type == 'task' and object_id:
            total_comments = total_comments.filter(to_task_id=object_id, parent__isnull=True)
        elif object_type == 'need' and object_id:
            total_comments = total_comments.filter(to_need_id=object_id, parent__isnull=True)
        elif object_type == 'decision' and object_id:
            total_comments = total_comments.filter(to_decision_id=object_id, parent__isnull=True)
        elif object_type == 'membership' and object_id:
            total_comments = total_comments.filter(to_membership_id=object_id, parent__isnull=True)
        elif object_type == 'report' and object_id:
            total_comments = total_comments.filter(to_report_id=object_id, parent__isnull=True)
        elif object_type == 'problem' and object_id:
            total_comments = total_comments.filter(
                to_problem_id=object_id,
                to_task__isnull=True,
                to_project__isnull=True,
                to_need__isnull=True,
                to_decision__isnull=True,
                to_membership__isnull=True,
                to_report__isnull=True,
                parent__isnull=True
            )

        total_count = total_comments.count()
        filtered_count = comments.count()

        # Add user vote info
        if request.user.is_authenticated:
            from .models import CommentVote
            user_votes = {
                vote.comment_id: vote.vote_type
                for vote in CommentVote.objects.filter(
                    user=request.user,
                    comment__in=comments
                )
            }
            for comment in comments:
                comment.user_vote = user_votes.get(comment.id)

        # Prepare rendering context
        context = {
            'comments': comments,
            'user': request.user,
            'object_type': object_type,
            'is_nested_include': True,
        }

        # Include object model context if applicable
        if object_type == 'task' and object_id:
            from task.models import Task
            try:
                context['task'] = Task.objects.get(id=object_id)
            except Task.DoesNotExist:
                pass
        elif object_type == 'project' and object_id:
            from project.models import Project
            try:
                context['project'] = Project.objects.get(id=object_id)
            except Project.DoesNotExist:
                pass
        elif object_type == 'problem' and object_id:
            from problems.models import Problem
            try:
                context['problem'] = Problem.objects.get(id=object_id)
            except Problem.DoesNotExist:
                pass

        comments_html = render_to_string('comments.html', context, request=request)

        return Response({
            'success': True,
            'comments_html': comments_html,
            'total_count': total_count,
            'filtered_count': filtered_count,
            'applied_filters': statuses
        })

    except json.JSONDecodeError:
        return Response({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@csrf_exempt
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
def filtered_comments_view(request):
    """
    Django view version for non-DRF usage
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        # Get filter parameters from request body
        data = json.loads(request.body) if request.body else {}
        
        # Get the filtering parameters
        statuses = data.get('statuses', ['APPROVED', 'PENDING'])
        object_type = data.get('object_type')
        object_id = data.get('object_id')
        
        # Build the base queryset
        comments = Comment.objects.select_related('user').prefetch_related('replies__user')
        # Filter by object type and ID
        if object_type == 'project' and object_id:
            comments = comments.filter(to_project_id=object_id, parent__isnull=True)
        elif object_type == 'task' and object_id:
            comments = comments.filter(to_task_id=object_id, parent__isnull=True)
        elif object_type == 'need' and object_id:
            comments = comments.filter(to_need_id=object_id, parent__isnull=True)
        elif object_type == 'decision' and object_id:
            comments = comments.filter(to_decision_id=object_id, parent__isnull=True)
        elif object_type == 'membership' and object_id:
            comments = comments.filter(to_membership_id=object_id, parent__isnull=True)
        elif object_type == 'report' and object_id:
            comments = comments.filter(to_report_id=object_id, parent__isnull=True)
        # NEW: Handle problem comments
        elif object_type == 'problem' and object_id:
            comments = comments.filter(
                to_problem_id=object_id,
                to_task__isnull=True,
                to_project__isnull=True,
                to_need__isnull=True,
                to_decision__isnull=True,
                to_membership__isnull=True,
                to_report__isnull=True,
                parent__isnull=True
            )
        else:
            # Default to no parent comments if no specific object
            comments = comments.filter(parent__isnull=True)


            
        
        # Apply status filtering
        if statuses:
            comments = comments.filter(status__in=statuses)
        
        # Get total count before status filtering for stats
        total_comments = Comment.objects.all()
        if object_type == 'project' and object_id:
            total_comments = total_comments.filter(to_project_id=object_id, parent__isnull=True)
        elif object_type == 'task' and object_id:
            total_comments = total_comments.filter(to_task_id=object_id, parent__isnull=True)
        elif object_type == 'need' and object_id:
            total_comments = total_comments.filter(to_need_id=object_id, parent__isnull=True)
        # NEW: Include problem comments in total count
        elif object_type == 'problem' and object_id:
            total_comments = total_comments.filter(
                to_problem_id=object_id,
                to_task__isnull=True,
                to_project__isnull=True,
                to_need__isnull=True,
                to_decision__isnull=True,
                to_membership__isnull=True,
                to_report__isnull=True,
                parent__isnull=True
            )
            




        comments = comments
        total_count = total_comments.count()
        filtered_count = comments.count()
        
        # Add user vote information
        if request.user.is_authenticated:
            from .models import CommentVote
            user_votes = {
                vote.comment_id: vote.vote_type 
                for vote in CommentVote.objects.filter(
                    user=request.user,
                    comment__in=comments
                )
            }
            
            for comment in comments:
                comment.user_vote = user_votes.get(comment.id)
        
        # Render the comments
        context = {
            'comments': comments,
            'user': request.user,
            'is_nested_include': True,  # Prevent admin panel from rendering in AJAX responses
        }
        
        # Add specific object context
        if object_type == 'task' and object_id:
            from task.models import Task
            try:
                context['task'] = Task.objects.get(id=object_id)
            except Task.DoesNotExist:
                pass
        elif object_type == 'project' and object_id:
            from project.models import Project
            try:
                context['project'] = Project.objects.get(id=object_id)
            except Project.DoesNotExist:
                pass
        elif object_type == 'need' and object_id:
            from need.models import Need
            try:
                context['need'] = Need.objects.get(id=object_id)
            except Need.DoesNotExist:
                pass
        # NEW: Add problem context
        elif object_type == 'problem' and object_id:
            from problems.models import Problem
            try:
                context['problem'] = Problem.objects.get(id=object_id)
            except Problem.DoesNotExist:
                pass
        
        comments_html = render_to_string('comments.html', context, request=request)
        
        return JsonResponse({
            'success': True,
            'comments_html': comments_html,
            'total_count': total_count,
            'filtered_count': filtered_count,
            'applied_filters': statuses
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
