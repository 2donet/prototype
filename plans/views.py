from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib.contenttypes.models import ContentType
from django.db.models import Prefetch, Q
from django.core.paginator import Paginator
from django.utils import timezone
import json

from .models import Plan, Step, PlanSuggestion, PlanSuggestionStatus
from project.models import Project
from task.models import Task
from need.models import Need
from utils.permissions import user_has_project_permission


@login_required
def create_plan(request):
    """Create a new plan"""
    # Check if coming from project moderation context
    project_id = request.GET.get('project')
    target_project = None
    is_moderation_context = False
    
    if project_id:
        try:
            target_project = Project.objects.get(id=project_id)
            # Check if user is admin of this specific project
            is_moderation_context = target_project.membership_set.filter(
                user=request.user,
                is_administrator=True
            ).exists()
        except Project.DoesNotExist:
            pass
    
    # Get projects where user is admin (for auto-suggestion)
    admin_projects = []
    if request.user.is_authenticated:
        from project.models import Membership
        admin_projects = Project.objects.filter(
            membership__user=request.user,
            membership__is_administrator=True
        ).distinct()
    
    if request.method == 'POST':
        name = request.POST.get('name')
        desc = request.POST.get('desc', '')
        
        if not name:
            messages.error(request, "Plan name is required.")
            context = {
                'admin_projects': admin_projects,
                'target_project': target_project,
                'is_moderation_context': is_moderation_context,
            }
            return render(request, 'plans/create_plan.html', context)
        
        # Create the plan
        plan = Plan.objects.create(
            name=name,
            desc=desc,
            created_by=request.user
        )
        
        # Handle initial steps
        step_names = request.POST.getlist('step_name[]')
        step_descs = request.POST.getlist('step_desc[]')
        
        for i, (step_name, step_desc) in enumerate(zip(step_names, step_descs)):
            if step_name.strip():
                Step.objects.create(
                    plan=plan,
                    name=step_name,
                    desc=step_desc,
                    order=i + 1
                )
        
        # Handle moderation context (priority)
        if is_moderation_context and target_project:
            # Auto-suggest and approve for the target project
            from django.contrib.contenttypes.models import ContentType
            project_ct = ContentType.objects.get_for_model(Project)
            
            suggestion = PlanSuggestion.objects.create(
                plan=plan,
                content_type=project_ct,
                object_id=target_project.id,
                suggested_by=request.user,
                suggestion_note=f'Plan created by project admin from moderation dashboard',
                status=PlanSuggestionStatus.APPROVED,  # Auto-approve for admins
                reviewed_by=request.user,
                reviewed_at=timezone.now(),
                review_note="Auto-approved: Plan created by project admin from moderation context"
            )
            
            messages.success(request, f"Plan '{plan.name}' created and automatically added to {target_project.name}!")
            return redirect('project:plans_management', project_id=target_project.id)
        
        # Handle regular auto-suggestion for selected projects
        selected_projects = request.POST.getlist('auto_suggest_projects')
        suggestion_note = request.POST.get('auto_suggest_note', f'Plan created by project admin: {request.user.username}')
        
        if selected_projects:
            from django.contrib.contenttypes.models import ContentType
            project_ct = ContentType.objects.get_for_model(Project)
            
            for project_id in selected_projects:
                try:
                    project = Project.objects.get(id=project_id)
                    # Verify user is still admin (security check)
                    if project.membership_set.filter(user=request.user, is_administrator=True).exists():
                        # Create auto-approved suggestion
                        suggestion = PlanSuggestion.objects.create(
                            plan=plan,
                            content_type=project_ct,
                            object_id=project.id,
                            suggested_by=request.user,
                            suggestion_note=suggestion_note,
                            status=PlanSuggestionStatus.APPROVED,  # Auto-approve for admins
                            reviewed_by=request.user,
                            reviewed_at=timezone.now(),
                            review_note="Auto-approved: Plan created by project admin"
                        )
                        
                except Project.DoesNotExist:
                    continue
        
        if selected_projects:
            messages.success(request, f"Plan '{plan.name}' created and automatically added to {len(selected_projects)} project(s)!")
        else:
            messages.success(request, f"Plan '{plan.name}' created successfully!")
        
        return redirect('plans:plan_detail', plan_id=plan.id)
    
    context = {
        'admin_projects': admin_projects,
        'target_project': target_project,
        'is_moderation_context': is_moderation_context,
    }
    return render(request, 'plans/create_plan.html', context)


def plan_detail(request, plan_id):
    """Display plan details with steps"""
    plan = get_object_or_404(
        Plan.objects.select_related('created_by').prefetch_related(
            'steps', 'suggestions__content_type'
        ), 
        pk=plan_id
    )
    
    # Check permissions
    if not plan.user_can_view(request.user):
        messages.error(request, "You don't have permission to view this plan.")
        return redirect('project:index')
    
    # Get suggestions for this plan
    suggestions = plan.suggestions.select_related(
        'suggested_by', 'reviewed_by', 'content_type'
    ).order_by('-created_at')
    
    # Check if user can edit
    can_edit = plan.user_can_edit(request.user)
    
    context = {
        'plan': plan,
        'suggestions': suggestions,
        'can_edit': can_edit,
    }
    return render(request, 'plans/plan_detail.html', context)


@login_required
def edit_plan(request, plan_id):
    """Edit an existing plan"""
    plan = get_object_or_404(Plan, pk=plan_id)
    
    if not plan.user_can_edit(request.user):
        messages.error(request, "You don't have permission to edit this plan.")
        return redirect('plans:plan_detail', plan_id=plan.id)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        desc = request.POST.get('desc', '')
        
        if not name:
            messages.error(request, "Plan name is required.")
            return render(request, 'plans/edit_plan.html', {'plan': plan})
        
        plan.name = name
        plan.desc = desc
        plan.save()
        
        messages.success(request, "Plan updated successfully!")
        return redirect('plans:plan_detail', plan_id=plan.id)
    
    context = {
        'plan': plan,
    }
    return render(request, 'plans/edit_plan.html', context)


@login_required
def delete_plan(request, plan_id):
    """Delete a plan"""
    plan = get_object_or_404(Plan, pk=plan_id)
    
    if not plan.user_can_edit(request.user):
        messages.error(request, "You don't have permission to delete this plan.")
        return redirect('plans:plan_detail', plan_id=plan.id)
    
    if request.method == 'POST':
        plan_name = plan.name
        plan.delete()
        messages.success(request, f"Plan '{plan_name}' deleted successfully.")
        return redirect('project:index')
    
    context = {
        'plan': plan,
    }
    return render(request, 'plans/delete_plan.html', context)


@login_required
def add_step(request, plan_id):
    """Add a new step to a plan"""
    plan = get_object_or_404(Plan, pk=plan_id)
    
    if not plan.user_can_edit(request.user):
        messages.error(request, "You don't have permission to edit this plan.")
        return redirect('plans:plan_detail', plan_id=plan.id)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        desc = request.POST.get('desc', '')
        
        if not name:
            messages.error(request, "Step name is required.")
            return redirect('plans:plan_detail', plan_id=plan.id)
        
        # Get the next order number
        last_step = plan.steps.order_by('-order').first()
        next_order = (last_step.order + 1) if last_step else 1
        
        Step.objects.create(
            plan=plan,
            name=name,
            desc=desc,
            order=next_order
        )
        
        messages.success(request, "Step added successfully!")
        return redirect('plans:plan_detail', plan_id=plan.id)
    
    context = {
        'plan': plan,
    }
    return render(request, 'plans/add_step.html', context)


@login_required
def edit_step(request, plan_id, step_id):
    """Edit a step"""
    plan = get_object_or_404(Plan, pk=plan_id)
    step = get_object_or_404(Step, pk=step_id, plan=plan)
    
    if not plan.user_can_edit(request.user):
        messages.error(request, "You don't have permission to edit this plan.")
        return redirect('plans:plan_detail', plan_id=plan.id)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        desc = request.POST.get('desc', '')
        
        if not name:
            messages.error(request, "Step name is required.")
            return render(request, 'plans/edit_step.html', {'plan': plan, 'step': step})
        
        step.name = name
        step.desc = desc
        step.save()
        
        messages.success(request, "Step updated successfully!")
        return redirect('plans:plan_detail', plan_id=plan.id)
    
    context = {
        'plan': plan,
        'step': step,
    }
    return render(request, 'plans/edit_step.html', context)


@login_required
def delete_step(request, plan_id, step_id):
    """Delete a step"""
    plan = get_object_or_404(Plan, pk=plan_id)
    step = get_object_or_404(Step, pk=step_id, plan=plan)
    
    if not plan.user_can_edit(request.user):
        messages.error(request, "You don't have permission to edit this plan.")
        return redirect('plans:plan_detail', plan_id=plan.id)
    
    if request.method == 'POST':
        step.delete()
        messages.success(request, "Step deleted successfully!")
        return redirect('plans:plan_detail', plan_id=plan.id)
    
    context = {
        'plan': plan,
        'step': step,
    }
    return render(request, 'plans/delete_step.html', context)


@login_required
def reorder_steps(request, plan_id):
    """AJAX endpoint to reorder steps"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    
    plan = get_object_or_404(Plan, pk=plan_id)
    
    if not plan.user_can_edit(request.user):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        step_orders = json.loads(request.body)
        
        # Validate that all steps belong to this plan
        step_ids = [step_data['id'] for step_data in step_orders]
        existing_steps = Step.objects.filter(id__in=step_ids, plan=plan)
        
        if len(existing_steps) != len(step_ids):
            return JsonResponse({'error': 'Invalid step IDs'}, status=400)
        
        # Use a transaction to ensure atomicity
        from django.db import transaction
        
        with transaction.atomic():
            # Update all steps in a single transaction
            for step_data in step_orders:
                step_id = step_data['id']
                new_order = step_data['order']
                
                # Validate order is positive
                if new_order <= 0:
                    return JsonResponse({'error': 'Order must be positive'}, status=400)
                
                Step.objects.filter(id=step_id, plan=plan).update(order=new_order)
        
        return JsonResponse({
            'success': True, 
            'message': 'Steps reordered successfully',
            'updated_count': len(step_orders)
        })
    
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except KeyError as e:
        return JsonResponse({'error': f'Missing required field: {e}'}, status=400)
    except Exception as e:
        # Log the error for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error reordering steps for plan {plan_id}: {e}")
        
        return JsonResponse({'error': 'Internal server error'}, status=500)

@login_required
def suggest_plan(request, content_type, object_id):
    """Suggest a plan for specific content (Project/Task/Need)"""
    # Get content type
    try:
        content_type_obj = ContentType.objects.get(model=content_type.lower())
        content_object = content_type_obj.get_object_for_this_type(pk=object_id)
    except (ContentType.DoesNotExist, content_type_obj.model_class().DoesNotExist):
        messages.error(request, "Content not found.")
        return redirect('project:index')
    
    # Check if user can suggest plans for this content
    main_project = None
    if hasattr(content_object, 'main_project'):
        main_project = content_object.main_project or content_object
    elif hasattr(content_object, 'to_project'):
        project = content_object.to_project
        main_project = project.main_project if project and project.main_project else project
    
    if not main_project or not main_project.user_can_view(request.user):
        messages.error(request, "You don't have permission to suggest plans for this content.")
        return redirect('project:index')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        suggestion_note = request.POST.get('suggestion_note', '')
        
        if action == 'create_new':
            # Create new plan and suggest it
            plan_name = request.POST.get('plan_name')
            plan_desc = request.POST.get('plan_desc', '')
            
            if not plan_name:
                messages.error(request, "Plan name is required.")
                return render(request, 'plans/suggest_plan.html', {
                    'content_object': content_object,
                    'content_type': content_type,
                })
            
            # Create the plan
            plan = Plan.objects.create(
                name=plan_name,
                desc=plan_desc,
                created_by=request.user
            )
            
            # Handle initial steps
            step_names = request.POST.getlist('step_name[]')
            step_descs = request.POST.getlist('step_desc[]')
            
            for i, (step_name, step_desc) in enumerate(zip(step_names, step_descs)):
                if step_name.strip():
                    Step.objects.create(
                        plan=plan,
                        name=step_name,
                        desc=step_desc,
                        order=i + 1
                    )
        
        elif action == 'suggest_existing':
            # Suggest existing plan
            plan_id = request.POST.get('plan_id')
            try:
                plan = Plan.objects.get(pk=plan_id)
            except Plan.DoesNotExist:
                messages.error(request, "Selected plan not found.")
                return render(request, 'plans/suggest_plan.html', {
                    'content_object': content_object,
                    'content_type': content_type,
                })
        
        else:
            messages.error(request, "Invalid action.")
            return render(request, 'plans/suggest_plan.html', {
                'content_object': content_object,
                'content_type': content_type,
            })
        
        # Check if suggestion already exists
        existing = PlanSuggestion.objects.filter(
            plan=plan,
            content_type=content_type_obj,
            object_id=object_id
        ).first()
        
        if existing:
            messages.error(request, "This plan is already suggested for this content.")
            return redirect('plans:plan_detail', plan_id=plan.id)
        
        # Check if user is admin of the target project (for auto-approval)
        is_admin = False
        if main_project:
            is_admin = main_project.membership_set.filter(
                user=request.user, 
                is_administrator=True
            ).exists()
        
        # Create suggestion
        suggestion = PlanSuggestion.objects.create(
            plan=plan,
            content_type=content_type_obj,
            object_id=object_id,
            suggested_by=request.user,
            suggestion_note=suggestion_note
        )
        
        # Auto-approve if user is admin
        if is_admin:
            suggestion.status = PlanSuggestionStatus.APPROVED
            suggestion.reviewed_by = request.user
            suggestion.reviewed_at = timezone.now()
            suggestion.review_note = "Auto-approved: Suggested by project admin"
            suggestion.save()
            
            messages.success(request, f"Plan '{plan.name}' automatically approved and added to the project!")
        else:
            messages.success(request, f"Plan '{plan.name}' suggested successfully! Waiting for admin approval.")
        
        return redirect('plans:plan_detail', plan_id=plan.id)
    
    # GET request - show suggestion form
    # Get available plans user can suggest
    available_plans = Plan.objects.filter(created_by=request.user).order_by('-created_at')
    
    context = {
        'content_object': content_object,
        'content_type': content_type,
        'available_plans': available_plans,
    }
    return render(request, 'plans/suggest_plan.html', context)


@login_required
def approve_suggestion(request, suggestion_id):
    """Approve a plan suggestion (admin only)"""
    suggestion = get_object_or_404(
        PlanSuggestion.objects.select_related('plan', 'suggested_by'),
        pk=suggestion_id
    )
    
    if not suggestion.user_can_review(request.user):
        messages.error(request, "You don't have permission to review this suggestion.")
        return redirect('project:index')
    
    if request.method == 'POST':
        review_note = request.POST.get('review_note', '')
        suggestion.approve(request.user, review_note)
        
        messages.success(request, f"Plan suggestion approved successfully.")
        
        # Redirect back to moderation dashboard
        main_project = suggestion.get_main_project()
        if main_project:
            return redirect('project:plans_management', project_id=main_project.id)
    
    return redirect('project:index')


@login_required
def reject_suggestion(request, suggestion_id):
    """Reject a plan suggestion (admin only)"""
    suggestion = get_object_or_404(
        PlanSuggestion.objects.select_related('plan', 'suggested_by'),
        pk=suggestion_id
    )
    
    if not suggestion.user_can_review(request.user):
        messages.error(request, "You don't have permission to review this suggestion.")
        return redirect('project:index')
    
    if request.method == 'POST':
        review_note = request.POST.get('review_note', '')
        suggestion.reject(request.user, review_note)
        
        messages.success(request, f"Plan suggestion rejected.")
        
        # Redirect back to moderation dashboard
        main_project = suggestion.get_main_project()
        if main_project:
            return redirect('project:plans_management', project_id=main_project.id)
    
    return redirect('project:index')


@login_required
def withdraw_suggestion(request, suggestion_id):
    """Withdraw a plan suggestion (suggester only)"""
    suggestion = get_object_or_404(PlanSuggestion, pk=suggestion_id)
    
    if suggestion.suggested_by != request.user:
        messages.error(request, "You can only withdraw your own suggestions.")
        return redirect('project:index')
    
    if request.method == 'POST':
        suggestion.withdraw()
        messages.success(request, "Plan suggestion withdrawn.")
        return redirect('plans:plan_detail', plan_id=suggestion.plan.id)
    
    return redirect('project:index')


def project_plans(request, project_id):
    """View all plans associated with a project"""
    project = get_object_or_404(Project, pk=project_id)
    
    if not project.user_can_view(request.user):
        messages.error(request, "You don't have permission to view this project.")
        return redirect('project:index')
    
    # Get all approved plan suggestions for this project and its content
    project_ct = ContentType.objects.get_for_model(Project)
    task_ct = ContentType.objects.get_for_model(Task)
    need_ct = ContentType.objects.get_for_model(Need)
    
    # Get suggestions for the project itself
    project_suggestions = PlanSuggestion.objects.filter(
        content_type=project_ct,
        object_id=project.id,
        status=PlanSuggestionStatus.APPROVED
    ).select_related('plan', 'suggested_by')
    
    # Get suggestions for project's tasks
    task_suggestions = PlanSuggestion.objects.filter(
        content_type=task_ct,
        object_id__in=project.task_set.values_list('id', flat=True),
        status=PlanSuggestionStatus.APPROVED
    ).select_related('plan', 'suggested_by').prefetch_related('content_object')
    
    # Get suggestions for project's needs
    need_suggestions = PlanSuggestion.objects.filter(
        content_type=need_ct,
        object_id__in=project.need_set.values_list('id', flat=True),
        status=PlanSuggestionStatus.APPROVED
    ).select_related('plan', 'suggested_by').prefetch_related('content_object')
    
    # Get pending suggestions if user can moderate
    pending_suggestions = []
    can_moderate = user_has_project_permission(request.user, project, 'can_admin')
    
    if can_moderate:
        pending_suggestions = PlanSuggestion.objects.filter(
            Q(content_type=project_ct, object_id=project.id) |
            Q(content_type=task_ct, object_id__in=project.task_set.values_list('id', flat=True)) |
            Q(content_type=need_ct, object_id__in=project.need_set.values_list('id', flat=True)),
            status=PlanSuggestionStatus.PENDING
        ).select_related('plan', 'suggested_by').prefetch_related('content_object')
    
    context = {
        'project': project,
        'project_suggestions': project_suggestions,
        'task_suggestions': task_suggestions,
        'need_suggestions': need_suggestions,
        'pending_suggestions': pending_suggestions,
        'can_moderate': can_moderate,
    }
    return render(request, 'plans/project_plans.html', context)