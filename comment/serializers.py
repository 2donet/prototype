from rest_framework import serializers
from comment.models import Comment, CommentVote, CommentReaction, VoteType, ReactionType


class CommentVoteSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.username')
    
    class Meta:
        model = CommentVote
        fields = ['id', 'comment', 'user', 'vote_type', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']
        
    def validate(self, data):
        # Make sure vote_type is valid
        if data.get('vote_type') not in [VoteType.UPVOTE, VoteType.DOWNVOTE]:
            raise serializers.ValidationError({"vote_type": "Invalid vote type"})
        return data


class CommentReactionSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.username')
    
    class Meta:
        model = CommentReaction
        fields = ['id', 'comment', 'user', 'reaction_type', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']
        
    def validate(self, data):
        # Make sure reaction_type is valid
        if data.get('reaction_type') not in dict(ReactionType.choices):
            raise serializers.ValidationError({"reaction_type": "Invalid reaction type"})
        return data


class CommentReactionCountSerializer(serializers.Serializer):
    reaction_type = serializers.CharField()
    count = serializers.IntegerField()


class CommentSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.username')
    user_id = serializers.ReadOnlyField(source='user.id')
    author_name = serializers.CharField(required=False, allow_blank=True)
    replies_count = serializers.IntegerField(source='total_replies', read_only=True)
    current_user_vote = serializers.SerializerMethodField()
    current_user_reactions = serializers.SerializerMethodField()
    reaction_counts = serializers.SerializerMethodField()
    
    class Meta:
        model = Comment
        fields = [
            'id', 'content', 'score', 'parent', 'user', 'user_id', 
            'author_name', 'created_at', 'updated_at', 'replies_count',
            'current_user_vote', 'current_user_reactions', 'reaction_counts'
        ]
        read_only_fields = ['id', 'score', 'created_at', 'updated_at', 'replies_count']
    
    def get_current_user_vote(self, obj):
        """Get the current user's vote on this comment"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                vote = CommentVote.objects.get(comment=obj, user=request.user)
                return vote.vote_type
            except CommentVote.DoesNotExist:
                return None
        return None
    
    def get_current_user_reactions(self, obj):
        """Get the current user's reactions on this comment"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            reactions = CommentReaction.objects.filter(
                comment=obj, 
                user=request.user
            ).values_list('reaction_type', flat=True)
            return list(reactions)
        return []
    
    def get_reaction_counts(self, obj):
        """Get counts for each reaction type on this comment"""
        reaction_counts = {}
        for reaction_type, _ in ReactionType.choices:
            count = CommentReaction.objects.filter(
                comment=obj, 
                reaction_type=reaction_type
            ).count()
            if count > 0:
                reaction_counts[reaction_type] = count
        return reaction_counts


class CommentDetailSerializer(CommentSerializer):
    """Extended serializer for comment detail views"""
    replies = serializers.SerializerMethodField()
    
    class Meta(CommentSerializer.Meta):
        fields = CommentSerializer.Meta.fields + ['replies']
    
    def get_replies(self, obj):
        """Get first-level replies to this comment"""
        replies = obj.replies.all()
        return CommentSerializer(replies, many=True, context=self.context).data