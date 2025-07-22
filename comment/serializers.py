from rest_framework import serializers
from comment.models import Comment, CommentVote, VoteType


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



class CommentSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.username')
    user_id = serializers.ReadOnlyField(source='user.id')
    author_name = serializers.CharField(required=False, allow_blank=True)
    replies_count = serializers.IntegerField(source='total_replies', read_only=True)
    current_user_vote = serializers.SerializerMethodField()
    
    class Meta:
        model = Comment
        fields = [
            'id', 'content', 'score', 'parent', 'user', 'user_id', 
            'author_name', 'created_at', 'updated_at',
            'current_user_vote', 
        ]
        read_only_fields = ['id', 'score', 'created_at', 'updated_at',]
    
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
    

    



class CommentDetailSerializer(CommentSerializer):
    """Extended serializer for comment detail views"""
    replies = serializers.SerializerMethodField()
    
    class Meta(CommentSerializer.Meta):
        fields = CommentSerializer.Meta.fields + ['replies']
    
    def get_replies(self, obj):
        """Get first-level replies to this comment"""
        replies = obj.replies.all()
        return CommentSerializer(replies, many=True, context=self.context).data