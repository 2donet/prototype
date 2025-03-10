from rest_framework import viewsets, permissions, status, views
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import IntegrityError, transaction
from django.db.models import Count

from comment.models import Comment, CommentVote, CommentReaction, VoteType, ReactionType
from comment.serializers import (
    CommentSerializer, 
    CommentDetailSerializer, 
    CommentVoteSerializer, 
    CommentReactionSerializer,
    CommentReactionCountSerializer
)


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
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def react(self, request, pk=None):
        """Add a reaction to a comment"""
        comment = self.get_object()
        reaction_type = request.data.get('reaction_type')
        
        if reaction_type not in dict(ReactionType.choices):
            return Response(
                {'error': f'Invalid reaction type. Must be one of {dict(ReactionType.choices).keys()}'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            # Toggle reaction (create if doesn't exist, delete if it does)
            try:
                # Check if reaction already exists
                reaction = CommentReaction.objects.get(
                    comment=comment,
                    user=request.user,
                    reaction_type=reaction_type
                )
                # If it exists, delete it (toggle off)
                reaction.delete()
                action = 'removed'
            except CommentReaction.DoesNotExist:
                # If it doesn't exist, create it
                CommentReaction.objects.create(
                    comment=comment,
                    user=request.user,
                    reaction_type=reaction_type
                )
                action = 'added'
                
            # Return the updated comment
            serializer = CommentSerializer(comment, context={'request': request})
            return Response({
                'action': action,
                'comment': serializer.data
            })
                
        except IntegrityError as e:
            return Response(
                {'error': f'Could not process reaction: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def reactions(self, request, pk=None):
        """Get all reactions for a comment with counts"""
        comment = self.get_object()
        
        # Count reactions by type
        reaction_counts = CommentReaction.objects.filter(comment=comment) \
            .values('reaction_type') \
            .annotate(count=Count('reaction_type')) \
            .order_by('-count')
        
        serializer = CommentReactionCountSerializer(reaction_counts, many=True)
        return Response(serializer.data)
    
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


class CommentReactionViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows comment reactions to be viewed or edited.
    """
    queryset = CommentReaction.objects.all()
    serializer_class = CommentReactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Optionally restrict to reactions by current user"""
        queryset = CommentReaction.objects.all()
        user = self.request.query_params.get('user')
        comment = self.request.query_params.get('comment')
        reaction_type = self.request.query_params.get('reaction_type')
        
        if user == 'me':
            queryset = queryset.filter(user=self.request.user)
        if comment:
            queryset = queryset.filter(comment__id=comment)
        if reaction_type:
            queryset = queryset.filter(reaction_type=reaction_type)
            
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)