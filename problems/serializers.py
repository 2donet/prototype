# problems/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Problem, ProblemActivity
from skills.models import Skill

User = get_user_model()

from django.utils import timezone

class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ['id', 'name']


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'full_name', 'avatar_url']
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username
    
    def get_avatar_url(self, obj):
        if hasattr(obj, 'profile') and obj.profile and obj.profile.avatar:
            return obj.profile.avatar_small.url if hasattr(obj.profile, 'avatar_small') else obj.profile.avatar.url
        return '/static/icons/default-avatar.svg'


class ProblemActivitySerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    activity_type_display = serializers.CharField(source='get_activity_type_display', read_only=True)
    
    class Meta:
        model = ProblemActivity
        fields = ['id', 'activity_type', 'activity_type_display', 'desc', 'user', 'created_at']


class ProblemSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    assigned_to = UserSerializer(many=True, read_only=True)
    skills = SkillSerializer(many=True, read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    visibility_display = serializers.CharField(source='get_visibility_display', read_only=True)
    related_object_type = serializers.CharField(source='get_related_object_type', read_only=True)
    related_object_name = serializers.SerializerMethodField()
    is_overdue = serializers.BooleanField(read_only=True)
    status_color = serializers.CharField(source='get_status_color', read_only=True)
    priority_color = serializers.CharField(source='get_priority_color', read_only=True)
    assigned_users_display = serializers.CharField(source='get_assigned_users_display', read_only=True)
    skills_display = serializers.CharField(source='get_skills_display', read_only=True)
    
    # Skill names for creation/update
    skill_names = serializers.ListField(
        child=serializers.CharField(max_length=50),
        write_only=True,
        required=False
    )
    
    # User IDs for assignment
    assigned_user_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = Problem
        fields = [
            'id', 'name', 'summary', 'desc', 'priority', 'priority_display',
            'status', 'status_display', 'visibility', 'visibility_display',
            'created_by', 'assigned_to', 'assigned_users_display',
            'created_at', 'updated_at', 'due_date', 'resolved_at', 'resolution',
            'to_project', 'to_task', 'to_need',
            'skills', 'skills_display', 'skill_names',
            'related_object_type', 'related_object_name',
            'is_overdue', 'status_color', 'priority_color',
            'assigned_user_ids'
        ]
        read_only_fields = [
            'id', 'created_by', 'created_at', 'updated_at', 'resolved_at'
        ]
    
    def get_related_object_name(self, obj):
        related_obj = obj.get_related_object()
        return related_obj.name if related_obj else None
    
    def create(self, validated_data):
        # Handle skill names
        skill_names = validated_data.pop('skill_names', [])
        assigned_user_ids = validated_data.pop('assigned_user_ids', [])
        
        problem = Problem.objects.create(**validated_data)
        
        # Add skills
        for skill_name in skill_names:
            problem.add_skill(skill_name)
        
        # Assign users
        for user_id in assigned_user_ids:
            try:
                user = User.objects.get(id=user_id)
                problem.assign_user(user)
            except User.DoesNotExist:
                pass
        
        return problem
    
    def update(self, instance, validated_data):
        # Handle skill names
        skill_names = validated_data.pop('skill_names', None)
        assigned_user_ids = validated_data.pop('assigned_user_ids', None)
        
        # Update basic fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Handle status change logic
        if instance.status == 'solved' and not instance.resolved_at:
            instance.resolved_at = timezone.now()
        elif instance.status != 'solved':
            instance.resolved_at = None
            instance.resolution = ''
        
        instance.save()
        
        # Update skills if provided
        if skill_names is not None:
            instance.skills.clear()
            for skill_name in skill_names:
                instance.add_skill(skill_name)
        
        # Update assignments if provided
        if assigned_user_ids is not None:
            # Remove all current assignments
            current_users = list(instance.assigned_to.all())
            for user in current_users:
                instance.unassign_user(user)
            
            # Add new assignments
            for user_id in assigned_user_ids:
                try:
                    user = User.objects.get(id=user_id)
                    instance.assign_user(user)
                except User.DoesNotExist:
                    pass
        
        return instance


class ProblemDetailSerializer(ProblemSerializer):
    """Extended serializer for problem detail views"""
    activities = ProblemActivitySerializer(many=True, read_only=True)
    recent_activities = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    can_comment = serializers.SerializerMethodField()
    
    class Meta(ProblemSerializer.Meta):
        fields = ProblemSerializer.Meta.fields + [
            'activities', 'recent_activities', 'can_edit', 'can_comment'
        ]
    
    def get_recent_activities(self, obj):
        """Get the 5 most recent activities"""
        recent = obj.activities.select_related('user').order_by('-created_at')[:5]
        return ProblemActivitySerializer(recent, many=True).data
    
    def get_can_edit(self, obj):
        """Check if current user can edit this problem"""
        request = self.context.get('request')
        if request and request.user:
            return obj.can_be_edited_by(request.user)
        return False
    
    def get_can_comment(self, obj):
        """Check if current user can comment on this problem"""
        request = self.context.get('request')
        if request and request.user:
            return obj.can_be_commented_by(request.user)
        return False