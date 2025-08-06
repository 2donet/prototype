from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, Http404
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.core.exceptions import PermissionDenied, ValidationError
from django.apps import apps
from django.db import IntegrityError
from django.db.models import Q, Prefetch
from .models import Intro, IntroRelation, LinkingIssue
from .forms import IntroForm, IntroLinkForm
from django.core.paginator import Paginator


class BaseIntroView(LoginRequiredMixin):
    """Base class for intro views with common functionality"""
    model = Intro
    
    def dispatch(self, request, *args, **kwargs):
        if hasattr(self, 'get_object'):
            try:
                obj = self.get_object()
                if not obj.can_view(request.user):
                    raise PermissionDenied("You don't have permission to view this intro.")
            except Http404:
                pass  # Let the view handle the 404
        return super().dispatch(request, *args, **kwargs)


class IntroListView(LoginRequiredMixin, ListView):
    """List intros visible to user"""
    model = Intro
    template_name = 'intros/list.html'
    context_object_name = 'intros'
    paginate_by = 20
    
    def get_queryset(self):
        # Get intros visible to user
        queryset = Intro.objects.visible_to_user(self.request.user).select_related(
            'by_user', 'main_project'
        ).prefetch_related(
            Prefetch(
                'relations',
                queryset=IntroRelation.objects.select_related(
                    'to_project', 'to_task', 'to_need', 'to_problem', 'to_plan'
                )
            )
        )
        
        # Filter by main project if specified
        project_id = self.request.GET.get('project')
        if project_id:
            queryset = queryset.filter(main_project_id=project_id)
        
        # Search functionality
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(summary__icontains=search)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_project'] = self.request.GET.get('project', '')
        
        # Get user's projects for filter dropdown
        if self.request.user.is_authenticated:
            from project.models import Project, Membership
            user_projects = Project.objects.filter(
                Q(created_by=self.request.user) |
                Q(membership__user=self.request.user)
            ).distinct()
            context['user_projects'] = user_projects
            
        return context


class IntroDetailView(BaseIntroView, DetailView):
    """Show detailed intro view with all relationships"""
    template_name = 'intros/details.html'
    context_object_name = 'intro'
    
    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        # Increment view count (but not for the creator viewing their own)
        if self.request.user != obj.by_user:
            obj.increment_view_count()
        return obj
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_edit'] = self.object.can_edit(self.request.user)
        
        # Get relationships grouped by status
        all_relations = self.object.relations.select_related(
            'to_task', 'to_project', 'to_need', 'to_problem', 'to_plan', 'linked_by'
        ).all()
        
        # Separate published and draft/pending relations
        published_relations = []
        draft_relations = []
        
        for relation in all_relations:
            if relation.status == IntroRelation.StatusChoices.PUBLISHED:
                published_relations.append(relation)
            else:
                # Only show draft/pending to users who can edit the relation
                if relation.can_edit_status(self.request.user):
                    draft_relations.append(relation)
        
        context['published_relations'] = published_relations
        context['draft_relations'] = draft_relations
        context['can_manage_relations'] = any(r.can_edit_status(self.request.user) for r in all_relations)
        
        return context


class IntroCreateView(LoginRequiredMixin, CreateView):
    """Create intro for specific entity based on URL parameters"""
    model = Intro
    form_class = IntroForm
    template_name = 'intros/create.html'
    
    def dispatch(self, request, *args, **kwargs):
        # Get entity info from URL
        self.entity_type = kwargs.get('entity_type')
        self.entity_id = kwargs.get('entity_id')
        
        # Validate entity type
        valid_types = ['task', 'project', 'need', 'problem', 'plan']
        if self.entity_type not in valid_types:
            raise Http404("Invalid entity type")
        
        # Get the related object
        self.related_object = self.get_related_object()
        
        # Check if user can link intros to this entity
        if not self.can_user_link_to_entity():
            raise PermissionDenied("You don't have permission to create intros for this entity.")
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_related_object(self):
        """Get the object this intro will be related to"""
        model_mapping = {
            'task': 'task.Task',
            'project': 'project.Project', 
            'need': 'need.Need',
            'problem': 'problems.Problem',
            'plan': 'plans.Plan'
        }
        
        app_label, model_name = model_mapping[self.entity_type].split('.')
        model = apps.get_model(app_label, model_name)
        return get_object_or_404(model, pk=self.entity_id)
    
    def can_user_link_to_entity(self):
        """Check if user can create intros for this entity"""
        entity = self.related_object
        
        # Get the project associated with this entity
        entity_project = None
        if hasattr(entity, 'to_project'):
            entity_project = entity.to_project
        elif entity.__class__.__name__ == 'Project':
            entity_project = entity
        
        if entity_project:
            return entity_project.user_can_contribute(self.request.user)
        
        return False
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['entity_type'] = self.entity_type
        kwargs['entity_id'] = self.entity_id
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        # Set the user
        form.instance.by_user = self.request.user
        
        # Set main_project based on entity
        entity_project = None
        if hasattr(self.related_object, 'to_project'):
            entity_project = self.related_object.to_project
        elif self.related_object.__class__.__name__ == 'Project':
            entity_project = self.related_object
        
        if entity_project:
            form.instance.main_project = entity_project
        
        # Save the intro
        response = super().form_valid(form)
        
        # Create the relationship
        field_mapping = {
            'task': 'to_task',
            'project': 'to_project',
            'need': 'to_need',
            'problem': 'to_problem',
            'plan': 'to_plan'
        }
        
        try:
            field_name = field_mapping[self.entity_type]
            relation_data = {
                'intro': self.object,
                field_name: self.related_object,
                'linked_by': self.request.user,
                'status': IntroRelation.StatusChoices.PUBLISHED,  # Default to published
            }
            
            relation = IntroRelation.objects.create(**relation_data)
            messages.success(
                self.request, 
                f'Intro "{self.object.name}" created and linked to {self.related_object}!'
            )
            
        except IntegrityError:
            # This shouldn't happen in create, but just in case
            messages.warning(
                self.request,
                f'Intro created but relationship already exists with {self.related_object}.'
            )
        
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['entity_type'] = self.entity_type  # Original for URLs
        context['entity_type_display'] = self.entity_type.title()  # For display
        context['entity_id'] = self.entity_id
        context['related_object'] = self.related_object
        return context
    
    def get_success_url(self):
        return self.object.get_absolute_url()


class IntroLinkView(LoginRequiredMixin, CreateView):
    """Link existing intro to entity"""
    model = IntroRelation
    form_class = IntroLinkForm
    template_name = 'intros/link.html'
    
    def dispatch(self, request, *args, **kwargs):
        self.entity_type = kwargs.get('entity_type')
        self.entity_id = kwargs.get('entity_id')
        
        valid_types = ['task', 'project', 'need', 'problem', 'plan']
        if self.entity_type not in valid_types:
            raise Http404("Invalid entity type")
        
        self.related_object = self.get_related_object()
        
        if not self.can_user_link_to_entity():
            raise PermissionDenied("You don't have permission to link intros to this entity.")
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_related_object(self):
        """Get the object to link intro to"""
        model_mapping = {
            'task': 'task.Task',
            'project': 'project.Project',
            'need': 'need.Need', 
            'problem': 'problems.Problem',
            'plan': 'plans.Plan'
        }
        
        app_label, model_name = model_mapping[self.entity_type].split('.')
        model = apps.get_model(app_label, model_name)
        return get_object_or_404(model, pk=self.entity_id)
    
    def can_user_link_to_entity(self):
        """Check linking permissions"""
        entity = self.related_object
        entity_project = None
        
        if hasattr(entity, 'to_project'):
            entity_project = entity.to_project
        elif entity.__class__.__name__ == 'Project':
            entity_project = entity
        
        if entity_project:
            return entity_project.user_can_contribute(self.request.user)
        
        return False
    
    def get_available_intros(self):
        """Get intros that can be linked to this entity"""
        entity_project = None
        if hasattr(self.related_object, 'to_project'):
            entity_project = self.related_object.to_project
        elif self.related_object.__class__.__name__ == 'Project':
            entity_project = self.related_object
        
        if not entity_project:
            return Intro.objects.none()
        
        # Get intros with matching main_project or main_project's main_project
        available = Intro.objects.filter(
            Q(main_project=entity_project) |
            Q(main_project__main_project=entity_project),
            status=Intro.StatusChoices.PUBLISHED
        ).filter(
            # User must be able to view the intro
            Q(visibility='public') |
            Q(visibility='logged_in') |
            Q(visibility='restricted', main_project__membership__user=self.request.user) |
            Q(by_user=self.request.user)
        ).distinct().select_related('by_user', 'main_project')
        
        return available
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['entity_type'] = self.entity_type
        kwargs['entity_id'] = self.entity_id
        kwargs['available_intros'] = self.get_available_intros()
        return kwargs
    
    def form_valid(self, form):
        intro = form.cleaned_data['intro']
        
        # Set relationship fields
        form.instance.intro = intro
        form.instance.linked_by = self.request.user
        
        # Set the appropriate entity field
        field_mapping = {
            'task': 'to_task',
            'project': 'to_project',
            'need': 'to_need',
            'problem': 'to_problem',
            'plan': 'to_plan'
        }
        
        field_name = field_mapping[self.entity_type]
        setattr(form.instance, field_name, self.related_object)
        
        try:
            response = super().form_valid(form)
            messages.success(
                self.request,
                f'Successfully linked "{intro.name}" to {self.related_object}!'
            )
            return response
            
        except IntegrityError:
            # Duplicate relationship - create linking issue
            LinkingIssue.objects.create(
                intro=intro,
                attempted_target_type=self.entity_type,
                attempted_target_id=self.entity_id,
                attempted_by=self.request.user
            )
            
            messages.error(
                self.request,
                f'"{intro.name}" is already linked to {self.related_object}. '
                'A linking issue has been created for review.'
            )
            
            return redirect('intros:linking_issue', 
                          intro_id=intro.pk, 
                          entity_type=self.entity_type,
                          entity_id=self.entity_id)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['entity_type'] = self.entity_type  # Original for URLs
        context['entity_type_display'] = self.entity_type.title()  # For display
        context['entity_id'] = self.entity_id
        context['related_object'] = self.related_object
        context['available_intros'] = self.get_available_intros()
        return context
    
    def get_success_url(self):
        # Redirect to the entity's page
        entity = self.related_object
        if hasattr(entity, 'get_absolute_url'):
            return entity.get_absolute_url()
        return reverse('intros:list')


class IntroUpdateView(BaseIntroView, UpdateView):
    """Edit existing intro"""
    form_class = IntroForm
    template_name = 'intros/edit.html'
    context_object_name = 'intro'
    
    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if not obj.can_edit(request.user):
            raise PermissionDenied("You don't have permission to edit this intro.")
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, 'Intro updated successfully!')
        return super().form_valid(form)
    
    def get_success_url(self):
        return self.object.get_absolute_url()


# AJAX Views for fetching intros with relationships
def ajax_intros_for_task(request, task_id):
    """Get intros related to a specific task"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    Task = apps.get_model('task', 'Task')
    task = get_object_or_404(Task, pk=task_id)
    
    # Get intro relations for this task
    relations = IntroRelation.objects.filter(
        to_task=task
    ).select_related('intro', 'intro__by_user', 'linked_by')
    
    intro_data = []
    for relation in relations:
        intro = relation.intro
        
        # Check if user can view this intro
        if not intro.can_view(request.user):
            continue
        
        # Check if user should see this relationship
        show_relation = (
            relation.status == IntroRelation.StatusChoices.PUBLISHED or
            relation.can_edit_status(request.user)
        )
        
        if show_relation:
            data = {
                'id': intro.pk,
                'name': intro.name,
                'summary': intro.summary,
                'intro_type': intro.get_intro_type_display(),
                'status': intro.get_status_display(),
                'visibility': intro.get_visibility_display(),
                'created_at': intro.created_at.isoformat(),
                'by_user': intro.by_user.username,
                'order': relation.order,
                'url': intro.get_absolute_url(),
                'can_edit': intro.can_edit(request.user),
                'relation_id': relation.pk,
                'relation_status': relation.get_status_display(),
                'relation_status_code': relation.status,
                'can_edit_relation': relation.can_edit_status(request.user),
                'linked_by': relation.linked_by.username,
                'linked_at': relation.linked_at.isoformat(),
            }
            
            # Add note about draft status for non-published relations
            if relation.status != IntroRelation.StatusChoices.PUBLISHED:
                data['status_note'] = f"Relationship is {relation.get_status_display()}"
            
            intro_data.append(data)
    
    return JsonResponse({
        'intros': intro_data,
        'count': len(intro_data),
        'task_name': str(task),
        'can_link_intros': task.to_project.user_can_contribute(request.user) if task.to_project else False
    })


def ajax_intros_for_project(request, project_id):
    """Get intros related to a specific project"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    Project = apps.get_model('project', 'Project')
    project = get_object_or_404(Project, pk=project_id)
    
    relations = IntroRelation.objects.filter(
        to_project=project
    ).select_related('intro', 'intro__by_user', 'linked_by')
    
    intro_data = []
    for relation in relations:
        intro = relation.intro
        
        if not intro.can_view(request.user):
            continue
        
        show_relation = (
            relation.status == IntroRelation.StatusChoices.PUBLISHED or
            relation.can_edit_status(request.user)
        )
        
        if show_relation:
            data = {
                'id': intro.pk,
                'name': intro.name,
                'summary': intro.summary,
                'intro_type': intro.get_intro_type_display(),
                'status': intro.get_status_display(),
                'visibility': intro.get_visibility_display(),
                'created_at': intro.created_at.isoformat(),
                'by_user': intro.by_user.username,
                'order': relation.order,
                'url': intro.get_absolute_url(),
                'can_edit': intro.can_edit(request.user),
                'relation_id': relation.pk,
                'relation_status': relation.get_status_display(),
                'relation_status_code': relation.status,
                'can_edit_relation': relation.can_edit_status(request.user),
                'linked_by': relation.linked_by.username,
                'linked_at': relation.linked_at.isoformat(),
            }
            
            if relation.status != IntroRelation.StatusChoices.PUBLISHED:
                data['status_note'] = f"Relationship is {relation.get_status_display()}"
            
            intro_data.append(data)
    
    return JsonResponse({
        'intros': intro_data,
        'count': len(intro_data),
        'project_name': str(project),
        'can_link_intros': project.user_can_contribute(request.user)
    })


def ajax_intros_for_need(request, need_id):
    """Get intros related to a specific need"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    Need = apps.get_model('need', 'Need')
    need = get_object_or_404(Need, pk=need_id)
    
    relations = IntroRelation.objects.filter(
        to_need=need
    ).select_related('intro', 'intro__by_user', 'linked_by')
    
    intro_data = []
    for relation in relations:
        intro = relation.intro
        
        if not intro.can_view(request.user):
            continue
        
        show_relation = (
            relation.status == IntroRelation.StatusChoices.PUBLISHED or
            relation.can_edit_status(request.user)
        )
        
        if show_relation:
            data = {
                'id': intro.pk,
                'name': intro.name,
                'summary': intro.summary,
                'intro_type': intro.get_intro_type_display(),
                'status': intro.get_status_display(),
                'visibility': intro.get_visibility_display(),
                'created_at': intro.created_at.isoformat(),
                'by_user': intro.by_user.username,
                'order': relation.order,
                'url': intro.get_absolute_url(),
                'can_edit': intro.can_edit(request.user),
                'relation_id': relation.pk,
                'relation_status': relation.get_status_display(),
                'relation_status_code': relation.status,
                'can_edit_relation': relation.can_edit_status(request.user),
                'linked_by': relation.linked_by.username,
                'linked_at': relation.linked_at.isoformat(),
            }
            
            if relation.status != IntroRelation.StatusChoices.PUBLISHED:
                data['status_note'] = f"Relationship is {relation.get_status_display()}"
            
            intro_data.append(data)
    
    return JsonResponse({
        'intros': intro_data,
        'count': len(intro_data),
        'need_name': str(need),
        'can_link_intros': need.to_project.user_can_contribute(request.user) if need.to_project else False
    })


def ajax_intros_for_problem(request, problem_id):
    """Get intros related to a specific problem"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    Problem = apps.get_model('problems', 'Problem')
    problem = get_object_or_404(Problem, pk=problem_id)
    
    relations = IntroRelation.objects.filter(
        to_problem=problem
    ).select_related('intro', 'intro__by_user', 'linked_by')
    
    intro_data = []
    for relation in relations:
        intro = relation.intro
        
        if not intro.can_view(request.user):
            continue
        
        show_relation = (
            relation.status == IntroRelation.StatusChoices.PUBLISHED or
            relation.can_edit_status(request.user)
        )
        
        if show_relation:
            data = {
                'id': intro.pk,
                'name': intro.name,
                'summary': intro.summary,
                'intro_type': intro.get_intro_type_display(),
                'status': intro.get_status_display(),
                'visibility': intro.get_visibility_display(),
                'created_at': intro.created_at.isoformat(),
                'by_user': intro.by_user.username,
                'order': relation.order,
                'url': intro.get_absolute_url(),
                'can_edit': intro.can_edit(request.user),
                'relation_id': relation.pk,
                'relation_status': relation.get_status_display(),
                'relation_status_code': relation.status,
                'can_edit_relation': relation.can_edit_status(request.user),
                'linked_by': relation.linked_by.username,
                'linked_at': relation.linked_at.isoformat(),
            }
            
            if relation.status != IntroRelation.StatusChoices.PUBLISHED:
                data['status_note'] = f"Relationship is {relation.get_status_display()}"
            
            intro_data.append(data)
    
    return JsonResponse({
        'intros': intro_data,
        'count': len(intro_data),
        'problem_name': str(problem),
        'can_link_intros': getattr(problem, 'can_be_edited_by', lambda u: False)(request.user)
    })


def ajax_intros_for_plan(request, plan_id):
    """Get intros related to a specific plan"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    Plan = apps.get_model('plans', 'Plan')
    plan = get_object_or_404(Plan, pk=plan_id)
    
    relations = IntroRelation.objects.filter(
        to_plan=plan
    ).select_related('intro', 'intro__by_user', 'linked_by')
    
    intro_data = []
    for relation in relations:
        intro = relation.intro
        
        if not intro.can_view(request.user):
            continue
        
        show_relation = (
            relation.status == IntroRelation.StatusChoices.PUBLISHED or
            relation.can_edit_status(request.user)
        )
        
        if show_relation:
            data = {
                'id': intro.pk,
                'name': intro.name,
                'summary': intro.summary,
                'intro_type': intro.get_intro_type_display(),
                'status': intro.get_status_display(),
                'visibility': intro.get_visibility_display(),
                'created_at': intro.created_at.isoformat(),
                'by_user': intro.by_user.username,
                'order': relation.order,
                'url': intro.get_absolute_url(),
                'can_edit': intro.can_edit(request.user),
                'relation_id': relation.pk,
                'relation_status': relation.get_status_display(),
                'relation_status_code': relation.status,
                'can_edit_relation': relation.can_edit_status(request.user),
                'linked_by': relation.linked_by.username,
                'linked_at': relation.linked_at.isoformat(),
            }
            
            if relation.status != IntroRelation.StatusChoices.PUBLISHED:
                data['status_note'] = f"Relationship is {relation.get_status_display()}"
            
            intro_data.append(data)
    
    return JsonResponse({
        'intros': intro_data,
        'count': len(intro_data),
        'plan_name': str(plan),
        'can_link_intros': getattr(plan, 'created_by', None) == request.user  # Basic permission check
    })


@login_required
def relation_status_update(request, relation_id):
    """Update relationship status (AJAX)"""
    relation = get_object_or_404(IntroRelation, pk=relation_id)
    
    if not relation.can_edit_status(request.user):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': 'Permission denied'}, status=403)
        raise PermissionDenied("You don't have permission to edit this relationship.")
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        note = request.POST.get('note', '')
        
        if new_status in [choice[0] for choice in IntroRelation.StatusChoices.choices]:
            old_status = relation.get_status_display()
            relation.status = new_status
            if note:
                relation.note = note
            relation.save()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'new_status': relation.get_status_display(),
                    'message': f'Relationship status changed from {old_status} to {relation.get_status_display()}'
                })
            
            messages.success(request, f'Relationship status updated to {relation.get_status_display()}')
            return redirect(relation.intro.get_absolute_url())
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'error': 'Invalid status'}, status=400)
            messages.error(request, 'Invalid status selected.')
    
    return redirect(relation.intro.get_absolute_url())


@login_required
def delete_intro(request, pk):
    """Delete an intro (AJAX or redirect)"""
    intro = get_object_or_404(Intro, pk=pk)
    
    if not intro.can_edit(request.user):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': 'Permission denied'}, status=403)
        raise PermissionDenied("You don't have permission to delete this intro.")
    
    if request.method == 'POST':
        intro_name = intro.name
        intro.delete()
        messages.success(request, f'Intro "{intro_name}" deleted successfully!')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        
        return redirect('intros:list')
    
    # GET request - show confirmation
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'confirm': True,
            'message': f'Are you sure you want to delete "{intro.name}"? This will also delete all relationships.'
        })
    
    return render(request, 'intros/delete_confirm.html', {'intro': intro})


@login_required
def delete_relation(request, relation_id):
    """Delete a specific intro-entity relationship"""
    relation = get_object_or_404(IntroRelation, pk=relation_id)
    
    if not relation.can_edit_status(request.user):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': 'Permission denied'}, status=403)
        raise PermissionDenied("You don't have permission to delete this relationship.")
    
    if request.method == 'POST':
        intro = relation.intro
        entity = relation.get_related_entity()
        entity_name = str(entity)
        
        relation.delete()
        messages.success(request, f'Removed relationship between "{intro.name}" and {entity_name}')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        
        return redirect(intro.get_absolute_url())
    
    # GET request - show confirmation
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        entity = relation.get_related_entity()
        return JsonResponse({
            'confirm': True,
            'message': f'Are you sure you want to remove the relationship between "{relation.intro.name}" and {entity}?'
        })
    
    return render(request, 'intros/delete_relation_confirm.html', {'relation': relation})


@login_required
def linking_issue_view(request, intro_id, entity_type, entity_id):
    """Handle linking issues when duplicate relationships are detected"""
    intro = get_object_or_404(Intro, pk=intro_id)
    
    # Get the target entity
    model_mapping = {
        'task': ('task', 'Task'),
        'project': ('project', 'Project'),
        'need': ('need', 'Need'),
        'problem': ('problems', 'Problem'),
        'plan': ('plans', 'Plan'),
    }
    
    if entity_type not in model_mapping:
        raise Http404("Invalid entity type")
    
    app_label, model_name = model_mapping[entity_type]
    model = apps.get_model(app_label, model_name)
    target_entity = get_object_or_404(model, pk=entity_id)
    
    # Get existing relationship
    field_mapping = {
        'task': 'to_task',
        'project': 'to_project',
        'need': 'to_need',
        'problem': 'to_problem',
        'plan': 'to_plan',
    }
    
    filter_kwargs = {'intro': intro, field_mapping[entity_type]: target_entity}
    existing_relation = IntroRelation.objects.filter(**filter_kwargs).first()
    
    context = {
        'intro': intro,
        'target_entity': target_entity,
        'entity_type': entity_type,  # Original for any URLs
        'entity_type_display': entity_type.title(),  # For display
        'existing_relation': existing_relation,
    }
    
    return render(request, 'intros/linking_issue.html', context)