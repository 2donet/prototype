from django.shortcuts import get_object_or_404, render, redirect
from django.db.models import Prefetch, Q, Count
from django.urls import reverse
from django.contrib import messages
from django.views.generic import CreateView, UpdateView
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.utils import timezone
from django.template.loader import render_to_string
from .models import Task
from .forms import TaskForm
from comment.models import Comment, CommentVote
from skills.models import Skill
from project.models import Project
from django.contrib.auth.decorators import login_required
import json

def task_detail(request, task_id):
    """
    Display details of a specific task, including its comments, replies, and skills.
    """
    task = get_object_or_404(Task, pk=task_id)
    
    # Check visibility permissions
    if not can_view_task(request.user, task):
        messages.error(request, "You don't have permission to view this task.")
        return redirect('task:task_list')
    
    # Fetch top-level comments with all necessary relations
    comments = Comment.objects.filter(
        to_task=task_id, 
        parent__isnull=True
    ).select_related('user').prefetch_related(
        Prefetch('replies', queryset=Comment.objects.select_related('user')),
        'votes')
    
    # Add user vote status to comments
    for comment in comments:
        if request.user.is_authenticated:
            user_vote = comment.votes.filter(user=request.user).first()
            comment.user_vote = user_vote.vote_type if user_vote else None
        else:
            comment.user_vote = None

        for reply in comment.replies.all():
            if request.user.is_authenticated:
                reply_vote = reply.votes.filter(user=request.user).first()
                reply.user_vote = reply_vote.vote_type if reply_vote else None
            else:
                reply.user_vote = None

    context = {
        "task": task,
        "comments": comments,
    }
    return render(request, "task_detail.html", context=context)


def task_list(request):
    """
    Enhanced task list with filtering, searching, and sorting capabilities.
    """
    # Get all projects and skills for filter options
    projects = Project.objects.all().order_by('name')
    skills = Skill.objects.all().order_by('name')
    
    # Get initial task count
    total_tasks = Task.objects.filter(
        visibility__in=get_visible_task_types(request.user)
    ).count()
    
    context = {
        'projects': projects,
        'skills': skills,
        'total_tasks': total_tasks,
    }
    
    return render(request, 'task_list.html', context)


def api_task_search(request):
    """
    AJAX endpoint for searching and filtering tasks.
    Returns JSON response with task data.
    """
    # Get base queryset with visibility filtering
    queryset = Task.objects.filter(
        visibility__in=get_visible_task_types(request.user)
    ).select_related(
        'created_by', 'to_project', 'main_project'
    ).prefetch_related('skills')
    
    # Apply filters
    queryset = apply_task_filters(queryset, request.GET)
    
    # Get total count before pagination
    total_count = Task.objects.filter(
        visibility__in=get_visible_task_types(request.user)
    ).count()
    filtered_count = queryset.count()
    
    # Apply sorting
    sort_by = request.GET.get('sort', '-created_at')
    queryset = queryset.order_by(sort_by)
    
    # Pagination
    page = int(request.GET.get('page', 1))
    per_page = int(request.GET.get('per_page', 24))
    
    paginator = Paginator(queryset, per_page)
    page_obj = paginator.get_page(page)
    
    # Serialize tasks for JSON response
    tasks_data = []
    for task in page_obj:
        task_data = {
            'id': task.id,
            'name': task.name,
            'description': task.desc,
            'priority': task.priority,
            'priority_display': task.priority_display,
            'priority_class': task.priority_class,
            'status': task.status,
            'status_display': task.get_status_display(),
            'status_class': task.status_class,
            'progress_percentage': task.get_progress_percentage(),
            'created_at': task.created_at.isoformat(),
            'created_at_display': task.created_at.strftime('%B %d, %Y'),
            'due_date': task.due_date.isoformat() if task.due_date else None,
            'due_date_display': task.due_date.strftime('%B %d, %Y') if task.due_date else None,
            'is_overdue': task.is_overdue,
            'created_by': {
                'id': task.created_by.id if task.created_by else None,
                'username': task.created_by.username if task.created_by else 'Unknown'
            },
            'project': {
                'id': task.to_project.id,
                'name': task.to_project.name
            } if task.to_project else None,
            'skills': [
                {'id': skill.id, 'name': skill.name} 
                for skill in task.skills.all()
            ],
            'can_edit': request.user.is_authenticated and request.user == task.created_by,
            'estimated_hours': task.estimated_hours,
            'actual_hours': task.actual_hours,
        }
        tasks_data.append(task_data)
    
    return JsonResponse({
        'tasks': tasks_data,
        'total_count': total_count,
        'filtered_count': filtered_count,
        'current_page': page,
        'total_pages': paginator.num_pages,
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous(),
        'per_page': per_page
    })


def skill_tasks(request, skill_name):
    """
    Display tasks that require a specific skill.
    """
    try:
        skill = Skill.objects.get(name__iexact=skill_name)
    except Skill.DoesNotExist:
        messages.error(request, f"Skill '{skill_name}' not found.")
        return redirect('task:task_list')
    
    # Get tasks with this skill
    queryset = Task.objects.filter(
        skills=skill,
        visibility__in=get_visible_task_types(request.user)
    ).select_related(
        'created_by', 'to_project'
    ).prefetch_related('skills').distinct()
    
    # Apply additional filters if present
    queryset = apply_task_filters(queryset, request.GET)
    
    # Get related skills (skills that appear in same tasks)
    related_skills = Skill.objects.filter(
        task__in=queryset
    ).exclude(id=skill.id).annotate(
        task_count=Count('task')
    ).order_by('-task_count')[:10]
    
    # Pagination
    paginator = Paginator(queryset.order_by('-created_at'), 24)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    
    # Get statistics
    stats = {
        'total_tasks': queryset.count(),
        'completed_tasks': queryset.filter(status='completed').count(),
        'in_progress_tasks': queryset.filter(status='in_progress').count(),
        'todo_tasks': queryset.filter(status='todo').count(),
    }
    
    context = {
        'skill': skill,
        'tasks': page_obj,
        'related_skills': related_skills,
        'stats': stats,
        'projects': Project.objects.all().order_by('name'),  # For filters
    }
    
    return render(request, 'skill_tasks.html', context)


def apply_task_filters(queryset, params):
    """
    Apply filters to task queryset based on GET parameters.
    """
    # Search filter
    search = params.get('search', '').strip()
    if search:
        queryset = queryset.filter(
            Q(name__icontains=search) |
            Q(desc__icontains=search) |
            Q(skills__name__icontains=search) |
            Q(created_by__username__icontains=search)
        ).distinct()
    
    # Project filter
    projects = params.get('projects', '').strip()
    if projects:
        project_ids = [int(pid) for pid in projects.split(',') if pid.isdigit()]
        if project_ids:
            queryset = queryset.filter(to_project__id__in=project_ids)
    
    # Skills filter
    skills = params.get('skills', '').strip()
    if skills:
        skill_names = [s.strip() for s in skills.split(',') if s.strip()]
        skill_logic = params.get('skill_logic', 'any')
        
        if skill_names:
            skill_objs = Skill.objects.filter(name__in=skill_names)
            if skill_logic == 'all':
                # Must have ALL selected skills
                for skill in skill_objs:
                    queryset = queryset.filter(skills=skill)
            else:
                # Must have ANY selected skill
                queryset = queryset.filter(skills__in=skill_objs).distinct()
    
    # Status filter
    statuses = params.get('statuses', '').strip()
    if statuses:
        status_list = [s.strip() for s in statuses.split(',') if s.strip()]
        if status_list:
            queryset = queryset.filter(status__in=status_list)
    
    # Priority filter
    priorities = params.get('priorities', '').strip()
    if priorities:
        priority_list = [int(p) for p in priorities.split(',') if p.isdigit()]
        if priority_list:
            queryset = queryset.filter(priority__in=priority_list)
    
    # Date filters
    created_after = params.get('created_after', '').strip()
    if created_after:
        try:
            from datetime import datetime
            date_obj = datetime.strptime(created_after, '%Y-%m-%d').date()
            queryset = queryset.filter(created_at__date__gte=date_obj)
        except ValueError:
            pass
    
    due_before = params.get('due_before', '').strip()
    if due_before:
        try:
            from datetime import datetime
            date_obj = datetime.strptime(due_before, '%Y-%m-%d').date()
            queryset = queryset.filter(due_date__date__lte=date_obj)
        except ValueError:
            pass
    
    return queryset


def get_visible_task_types(user):
    """
    Get list of task visibility types the user can see.
    """
    if user.is_authenticated:
        if user.is_staff or user.is_superuser:
            return ['public', 'logged_in', 'restricted']
        else:
            return ['public', 'logged_in']
    else:
        return ['public']


def can_view_task(user, task):
    """
    Check if user can view a specific task.
    """
    if task.visibility == 'public':
        return True
    elif task.visibility == 'logged_in':
        return user.is_authenticated
    elif task.visibility == 'restricted':
        return user.is_authenticated and (
            user.is_staff or 
            user == task.created_by or
            # Add more conditions for restricted access if needed
            user.is_superuser
        )
    return False


def add_skill_to_task(request, task_id):
    """Handle adding skills to tasks"""
    if request.method == 'POST':
        task = get_object_or_404(Task, pk=task_id)
        if request.user != task.created_by:
            messages.error(request, "You can only add skills to tasks you created")
            return redirect('task:task_detail', task_id=task_id)
            
        skill_name = request.POST.get('skill_name', '').strip()
        if skill_name:
            try:
                task.add_skill(skill_name)
                messages.success(request, f"Added skill: {skill_name}")
            except ValueError as e:
                messages.error(request, str(e))
        
    return redirect('task:task_detail', task_id=task_id)




@login_required
def quick_task_update(request, task_id):
    """
    AJAX endpoint for quick task updates (status, priority, etc.)
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    task = get_object_or_404(Task, pk=task_id)
    
    # Check permissions
    if request.user != task.created_by:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        data = json.loads(request.body)
        field = data.get('field')
        value = data.get('value')
        
        if field == 'status' and value in ['todo', 'in_progress', 'review', 'completed']:
            task.status = value
            task.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Task status updated to {task.get_status_display()}',
                'new_status': task.status,
                'new_status_display': task.get_status_display(),
                'progress_percentage': task.get_progress_percentage()
            })
        
        elif field == 'priority' and str(value) in ['1', '2', '3', '4']:
            task.priority = int(value)
            task.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Task priority updated to {task.priority_display}',
                'new_priority': task.priority,
                'new_priority_display': task.priority_display
            })
        
        else:
            return JsonResponse({'error': 'Invalid field or value'}, status=400)
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

class CreateTaskView(CreateView):
    model = Task
    form_class = TaskForm
    template_name = 'task_form.html'

    def get_form_kwargs(self):
        """Pass user to form for proper project filtering"""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_initial(self):
        """Pre-populate form with URL parameters"""
        initial = super().get_initial()
        
        # Pre-populate skills from URL parameter
        skill_param = self.request.GET.get('skill')
        if skill_param:
            initial['skills_input'] = json.dumps([skill_param])
        
        return initial

    def form_valid(self, form):
        """Handle form submission and skills processing"""
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        
        # Handle skills from chips input
        skills = form.cleaned_data.get('skills_input', [])
        print(f"DEBUG: Creating task with skills: {skills}")  # Debug line
        
        if skills:
            self.object.skills.set(skills)
            print(f"DEBUG: Skills set successfully: {[s.name for s in self.object.skills.all()]}")
        
        messages.success(self.request, "Task created successfully!")
        return response

    def get_success_url(self):
        return reverse('task:task_detail', kwargs={'task_id': self.object.id})


class UpdateTaskView(UpdateView):
    model = Task
    form_class = TaskForm
    template_name = 'task_form.html'
    pk_url_kwarg = 'task_id'

    def get_form_kwargs(self):
        """Pass user to form for proper project filtering"""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_queryset(self):
        # Only allow task creator to edit
        return super().get_queryset().filter(created_by=self.request.user)

    def form_valid(self, form):
        """Handle form submission and skills processing"""
        response = super().form_valid(form)
        
        # Handle skills from chips input
        skills = form.cleaned_data.get('skills_input', [])
        
        if skills:
            # Completely replace existing skills with new ones
            self.object.skills.set(skills)
        else:
            # Clear skills if none provided
            self.object.skills.clear()
        
        messages.success(self.request, "Task updated successfully!")
        return response
    def get_success_url(self):
        return reverse('task:task_detail', kwargs={'task_id': self.object.id})
def api_skills_autocomplete(request):
    """
    AJAX endpoint for skills autocomplete in filters.
    """
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'skills': []})
    
    skills = Skill.objects.filter(
        name__icontains=query
    ).annotate(
        task_count=Count('task')
    ).order_by('-task_count', 'name')[:20]
    
    skills_data = [
        {
            'name': skill.name,
            'task_count': skill.task_count
        }
        for skill in skills
    ]
    
    return JsonResponse({'skills': skills_data})


def api_filter_options(request):
    """
    AJAX endpoint to get available filter options.
    """
    visible_tasks = Task.objects.filter(
        visibility__in=get_visible_task_types(request.user)
    )
    
    projects = Project.objects.filter(
        task__in=visible_tasks
    ).distinct().order_by('name').values('id', 'name')
    
    skills = Skill.objects.filter(
        task__in=visible_tasks
    ).distinct().annotate(
        task_count=Count('task')
    ).order_by('-task_count', 'name').values('name', 'task_count')
    
    return JsonResponse({
        'projects': list(projects),
        'skills': list(skills),
        'statuses': [
            {'value': 'todo', 'label': 'To Do'},
            {'value': 'in_progress', 'label': 'In Progress'},
            {'value': 'review', 'label': 'Under Review'},
            {'value': 'completed', 'label': 'Completed'},
        ],
        'priorities': [
            {'value': 1, 'label': 'Low'},
            {'value': 2, 'label': 'Medium'},
            {'value': 3, 'label': 'High'},
            {'value': 4, 'label': 'Critical'},
        ]
    })

def debug_task_form(request, task_id):
    """Debug view to check task form and skills"""
    task = get_object_or_404(Task, pk=task_id)
    
    if request.method == 'GET':
        form = TaskForm(instance=task, user=request.user)
        print(f"DEBUG GET: Task {task_id} has {task.skills.count()} skills")
        for skill in task.skills.all():
            print(f"  - {skill.name} (ID: {skill.id})")
        print(f"DEBUG GET: Form skills_input value: {form.fields['skills_input'].initial}")
        
    return render(request, 'task_debug.html', {'form': form, 'task': task})