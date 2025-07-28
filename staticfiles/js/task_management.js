/**
 * Enhanced Task Management System - Main JavaScript File (FIXED)
 * Handles search, filtering, sorting, and AJAX updates
 */

class TaskManager {
    constructor() {
        this.currentPage = 1;
        this.tasksPerPage = 24;
        this.searchTimeout = null;
        this.currentFilters = {
            search: '',
            projects: [],
            skills: [],
            skill_logic: 'any',
            statuses: ['todo', 'in_progress', 'review'],
            priorities: [1, 2, 3, 4],
            created_after: '',
            due_before: '',
            sort: '-created_at'
        };
        this.currentView = 'cards';
        this.isLoading = false;
        this.hasNextPage = true;  // Track if there are more pages
        this.totalPages = 0;      // Track total pages
        this.skillsInstance = null; // Store chips instance
        
        this.init();
    }

    init() {
        this.bindEvents();
        this.initializeComponents();
        this.loadTasks();
    }

    bindEvents() {
        // Search functionality
        const searchInput = document.getElementById('task-search');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                clearTimeout(this.searchTimeout);
                this.searchTimeout = setTimeout(() => {
                    this.currentFilters.search = e.target.value.trim();
                    this.resetPagination();
                    this.loadTasks();
                }, 300);
            });
        }

        // Filter toggle
        const filterToggle = document.getElementById('filter-toggle');
        const filtersPanel = document.getElementById('filters-panel');
        if (filterToggle) {
            filterToggle.addEventListener('click', () => {
                filtersPanel.classList.toggle('hide');
                this.updateFilterToggleState();
            });
        }

        // Sort dropdown
        const sortSelect = document.getElementById('sort-select');
        if (sortSelect) {
            sortSelect.addEventListener('change', (e) => {
                this.currentFilters.sort = e.target.value;
                this.resetPagination();
                this.loadTasks();
            });
        }

        // View toggle buttons
        const viewButtons = document.querySelectorAll('.view-btn');
        viewButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                this.changeView(btn.dataset.view);
            });
        });

        // Filter controls
        this.bindFilterEvents();

        // Clear filters button
        const clearFiltersBtn = document.getElementById('clear-filters');
        if (clearFiltersBtn) {
            clearFiltersBtn.addEventListener('click', () => {
                this.clearAllFilters();
            });
        }

        // Apply filters button
        const applyFiltersBtn = document.getElementById('apply-filters');
        if (applyFiltersBtn) {
            applyFiltersBtn.addEventListener('click', () => {
                this.applyFilters();
            });
        }

        // Infinite scroll / Load more functionality
        this.bindScrollEvents();
    }

    bindFilterEvents() {
        // Project filter
        const projectFilter = document.getElementById('project-filter');
        if (projectFilter) {
            // Materialize select change event
            projectFilter.addEventListener('change', () => {
                this.updateProjectFilters();
            });
        }

        // Status checkboxes
        const statusFilters = document.querySelectorAll('.status-filter');
        statusFilters.forEach(checkbox => {
            checkbox.addEventListener('change', () => {
                this.updateStatusFilters();
            });
        });

        // Priority checkboxes
        const priorityFilters = document.querySelectorAll('.priority-filter');
        priorityFilters.forEach(checkbox => {
            checkbox.addEventListener('change', () => {
                this.updatePriorityFilters();
            });
        });

        // Date filters
        const createdAfter = document.getElementById('created-after');
        const dueBefore = document.getElementById('due-before');
        
        if (createdAfter) {
            createdAfter.addEventListener('change', (e) => {
                this.currentFilters.created_after = e.target.value;
            });
        }

        if (dueBefore) {
            dueBefore.addEventListener('change', (e) => {
                this.currentFilters.due_before = e.target.value;
            });
        }

        // Skill logic radio buttons
        const skillLogicRadios = document.querySelectorAll('input[name="skill-logic"]');
        skillLogicRadios.forEach(radio => {
            radio.addEventListener('change', (e) => {
                this.currentFilters.skill_logic = e.target.value;
            });
        });
    }

    bindScrollEvents() {
        // Implement infinite scroll or load more button
        window.addEventListener('scroll', () => {
            if (this.isLoading) return;
            
            const scrollPosition = window.innerHeight + window.scrollY;
            const documentHeight = document.documentElement.offsetHeight;
            
            if (scrollPosition >= documentHeight - 1000) {
                this.loadMoreTasks();
            }
        });
    }

    async initializeComponents() {
        // Initialize Materialize components
        this.initializeMaterialize();
        
        // Initialize skills chips
        await this.initializeSkillsFilter();
        
        // Update URL state
        this.updateUrlState();
    }

    initializeMaterialize() {
        // Initialize dropdowns
        const dropdowns = document.querySelectorAll('.dropdown-trigger');
        M.Dropdown.init(dropdowns, {
            constrainWidth: false,
            coverTrigger: false
        });

        // Initialize select elements
        const selects = document.querySelectorAll('select');
        M.FormSelect.init(selects);

        // Initialize tooltips
        const tooltips = document.querySelectorAll('.tooltipped');
        M.Tooltip.init(tooltips);
    }

    async initializeSkillsFilter() {
        const skillsFilter = document.getElementById('skills-filter');
        if (skillsFilter) {
            try {
                // Fetch skills data first
                const autocompleteData = await this.getSkillsAutocompleteData();
                
                // Initialize chips for skills filter
                this.skillsInstance = M.Chips.init(skillsFilter, {
                    placeholder: 'Add skill tags...',
                    secondaryPlaceholder: 'Enter skill name',
                    autocompleteOptions: {
                        data: autocompleteData,
                        limit: 10,
                        minLength: 1
                    },
                    onChipAdd: () => {
                        console.log('Chip added, updating skills filter');
                        this.updateSkillsFilter();
                    },
                    onChipDelete: () => {
                        console.log('Chip deleted, updating skills filter');
                        this.updateSkillsFilter();
                    }
                });
                
                console.log('Skills filter initialized with autocomplete data:', Object.keys(autocompleteData).length, 'skills');
            } catch (error) {
                console.error('Error initializing skills filter:', error);
                // Fallback initialization without autocomplete
                this.skillsInstance = M.Chips.init(skillsFilter, {
                    placeholder: 'Add skill tags...',
                    secondaryPlaceholder: 'Enter skill name',
                    onChipAdd: () => {
                        this.updateSkillsFilter();
                    },
                    onChipDelete: () => {
                        this.updateSkillsFilter();
                    }
                });
            }
        }
    }

    async loadTasks(append = false) {
        if (this.isLoading) return;
        
        this.isLoading = true;
        this.showLoading();

        try {
            const params = new URLSearchParams({
                page: this.currentPage,
                per_page: this.tasksPerPage,
                ...this.currentFilters
            });

            // Convert arrays to comma-separated strings
            if (this.currentFilters.projects.length > 0) {
                params.set('projects', this.currentFilters.projects.join(','));
            }
            if (this.currentFilters.skills.length > 0) {
                params.set('skills', this.currentFilters.skills.join(','));
                console.log('Sending skills filter:', this.currentFilters.skills);
            }
            if (this.currentFilters.statuses.length > 0) {
                params.set('statuses', this.currentFilters.statuses.join(','));
            }
            if (this.currentFilters.priorities.length > 0) {
                params.set('priorities', this.currentFilters.priorities.join(','));
            }

            console.log('Loading tasks with params:', params.toString());

            const response = await fetch(`/t/api/search/?${params}`, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'Content-Type': 'application/json',
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            this.renderTasks(data.tasks, append);
            this.updateResultsCount(data.total_count, data.filtered_count);
            this.updatePagination(data.has_next, data.has_previous, data.current_page, data.total_pages);
            
            // Update pagination state
            this.hasNextPage = data.has_next;
            this.totalPages = data.total_pages;
            
        } catch (error) {
            console.error('Error loading tasks:', error);
            this.showError('Failed to load tasks. Please try again.');
        } finally {
            this.isLoading = false;
            this.hideLoading();
        }
    }

    renderTasks(tasks, append = false) {
        const container = document.getElementById('tasks-container');
        const emptyState = document.getElementById('empty-state');
        
        if (!append) {
            container.innerHTML = '';
        }

        if (tasks.length === 0 && !append) {
            container.classList.add('hide');
            emptyState.classList.remove('hide');
            return;
        }

        container.classList.remove('hide');
        emptyState.classList.add('hide');

        tasks.forEach(task => {
            const taskCard = this.createTaskCard(task);
            container.appendChild(taskCard);
        });

        // Re-initialize Materialize components for new cards
        this.initializeMaterialize();
        
        // Add animation class for new cards
        if (!append) {
            const cards = container.querySelectorAll('.task-card-wrapper');
            cards.forEach((card, index) => {
                setTimeout(() => {
                    card.classList.add('new-card');
                }, index * 50);
            });
        }
    }

    createTaskCard(task) {
        const wrapper = document.createElement('div');
        wrapper.className = `col s12 m6 l4 task-card-wrapper`;
        wrapper.setAttribute('data-task-id', task.id);
        wrapper.setAttribute('data-priority', task.priority);
        wrapper.setAttribute('data-status', task.status);
        wrapper.setAttribute('data-created', task.created_at);
        
        // This would typically be rendered server-side, but for dynamic content:
        wrapper.innerHTML = this.getTaskCardHTML(task);
        
        return wrapper;
    }

    getTaskCardHTML(task) {
        // Enhanced task card HTML with proper skills display
        return `
            <div class="card task-card ${task.priority_class} hoverable">
                <div class="card-content">
                    <div class="task-header">
                        <div class="task-title-row">
                            <span class="card-title truncate">
                                <a href="/t/${task.id}/" class="task-title-link">${this.escapeHtml(task.name)}</a>
                            </span>
                            <div class="task-badges">
                                <span class="badge priority-badge ${task.priority_class}" data-badge-caption="${task.priority_display}">${task.priority}</span>
                                <span class="badge status-badge ${task.status_class}" data-badge-caption="${task.status_display}"></span>
                                ${task.is_overdue ? '<span class="badge overdue-badge" data-badge-caption="Overdue">!</span>' : ''}
                            </div>
                        </div>
                        <div class="progress-container">
                            <div class="progress">
                                <div class="determinate" style="width: ${task.progress_percentage}%"></div>
                            </div>
                            <span class="progress-text">${task.progress_percentage}%</span>
                        </div>
                    </div>
                    
                    <div class="task-meta">
                        <div class="meta-item">
                            <i class="material-icons tiny">account_circle</i>
                            <a href="/u/${task.created_by.id}" class="creator-link">${this.escapeHtml(task.created_by.username)}</a>
                        </div>
                        <div class="meta-item">
                            <i class="material-icons tiny">access_time</i>
                            <span class="created-time">${task.created_at_display}</span>
                        </div>
                        ${task.due_date ? `
                        <div class="meta-item due-date-item ${task.is_overdue ? 'overdue' : ''}">
                            <i class="material-icons tiny">event</i>
                            <span class="due-date">${task.due_date_display}</span>
                        </div>
                        ` : ''}
                    </div>
                    
                    <div class="task-description">
                        <p class="description-text">${task.description ? this.escapeHtml(task.description) : '<em class="no-description">No description provided</em>'}</p>
                    </div>
                    
                    ${task.project ? `
                    <div class="project-association">
                        <div class="chip project-chip">
                            <i class="material-icons tiny">folder</i>
                            <a href="/${task.project.id}" class="project-link">${this.escapeHtml(task.project.name)}</a>
                        </div>
                    </div>
                    ` : ''}
                    
                    <div class="skills-section">
                        ${task.skills && task.skills.length > 0 ? `
                        <div class="skills-container">
                            ${task.skills.map(skill => `
                                <a href="/p/skill/${encodeURIComponent(skill.name.toLowerCase())}/" class="chip skill-chip">${this.escapeHtml(skill.name)}</a>
                            `).join('')}
                        </div>
                        ` : '<div class="no-skills"><i class="material-icons tiny">label_outline</i><span>No skills specified</span></div>'}
                    </div>
                </div>
                
                <div class="card-action task-actions">
                    <a href="/t/${task.id}/" class="btn-flat waves-effect action-btn">
                        <i class="material-icons left">visibility</i>View
                    </a>
                    ${task.can_edit ? `
                    <a href="/t/${task.id}/edit/" class="btn-flat waves-effect action-btn">
                        <i class="material-icons left">edit</i>Edit
                    </a>
                    ` : ''}
                    <a href="/submissions/create/task/${task.id}/" class="btn-flat waves-effect action-btn apply-btn">
                        <i class="material-icons left">assignment</i>Apply
                    </a>
                </div>
            </div>
        `;
    }

    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    resetPagination() {
        this.currentPage = 1;
        this.hasNextPage = true;
        this.totalPages = 0;
    }

    updateProjectFilters() {
        const projectSelect = document.getElementById('project-filter');
        if (projectSelect) {
            const selectedOptions = Array.from(projectSelect.selectedOptions);
            this.currentFilters.projects = selectedOptions
                .map(option => option.value)
                .filter(value => value !== '');
        }
    }

    updateStatusFilters() {
        const statusCheckboxes = document.querySelectorAll('.status-filter:checked');
        this.currentFilters.statuses = Array.from(statusCheckboxes).map(cb => cb.value);
    }

    updatePriorityFilters() {
        const priorityCheckboxes = document.querySelectorAll('.priority-filter:checked');
        this.currentFilters.priorities = Array.from(priorityCheckboxes).map(cb => parseInt(cb.value));
    }

    updateSkillsFilter() {
        // Get the chips instance we stored during initialization
        if (this.skillsInstance && this.skillsInstance.chipsData) {
            const skillNames = this.skillsInstance.chipsData.map(chip => chip.tag);
            this.currentFilters.skills = skillNames;
            console.log('Updated skills filter:', skillNames);
        } else {
            console.log('Skills instance not found, trying fallback method');
            // Fallback method - try to get instance directly
            const skillsFilterElement = document.getElementById('skills-filter');
            if (skillsFilterElement) {
                const instance = M.Chips.getInstance(skillsFilterElement);
                if (instance && instance.chipsData) {
                    const skillNames = instance.chipsData.map(chip => chip.tag);
                    this.currentFilters.skills = skillNames;
                    console.log('Updated skills filter (fallback):', skillNames);
                } else {
                    console.log('Could not get chips instance');
                }
            }
        }
    }

    changeView(viewType) {
        this.currentView = viewType;
        
        // Update button states
        document.querySelectorAll('.view-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-view="${viewType}"]`).classList.add('active');
        
        // Apply view class to container
        const container = document.getElementById('tasks-container');
        container.className = `row view-${viewType}`;
        
        // Adjust card classes based on view
        if (viewType === 'compact') {
            container.querySelectorAll('.task-card-wrapper').forEach(card => {
                card.className = 'col s12 task-card-wrapper';
            });
        } else {
            container.querySelectorAll('.task-card-wrapper').forEach(card => {
                card.className = 'col s12 m6 l4 task-card-wrapper';
            });
        }
    }

    clearAllFilters() {
        // Reset filters to default
        this.currentFilters = {
            search: '',
            projects: [],
            skills: [],
            skill_logic: 'any',
            statuses: ['todo', 'in_progress', 'review'],
            priorities: [1, 2, 3, 4],
            created_after: '',
            due_before: '',
            sort: '-created_at'
        };

        // Reset pagination
        this.resetPagination();

        // Clear UI elements
        document.getElementById('task-search').value = '';
        
        // Reset checkboxes
        document.querySelectorAll('.status-filter').forEach(cb => {
            cb.checked = ['todo', 'in_progress', 'review'].includes(cb.value);
        });
        
        document.querySelectorAll('.priority-filter').forEach(cb => {
            cb.checked = true;
        });

        // Clear date inputs
        document.getElementById('created-after').value = '';
        document.getElementById('due-before').value = '';

        // Clear skills chips
        if (this.skillsInstance) {
            // Clear chips data
            this.skillsInstance.chipsData = [];
            this.skillsInstance._renderChips();
        }

        // Reset project select
        const projectSelect = document.getElementById('project-filter');
        if (projectSelect) {
            projectSelect.selectedIndex = 0;
            M.FormSelect.init(projectSelect);
        }

        // Reset skill logic
        document.querySelector('input[name="skill-logic"][value="any"]').checked = true;

        this.loadTasks();
    }

    applyFilters() {
        // CRITICAL FIX: Update all filters before applying
        this.updateProjectFilters();
        this.updateStatusFilters();
        this.updatePriorityFilters();
        this.updateSkillsFilter();  // This was missing!
        
        console.log('Applying filters:', this.currentFilters);
        
        this.resetPagination();
        this.loadTasks();
        this.updateFilterToggleState();
    }

    loadMoreTasks() {
        if (this.isLoading || !this.hasNextPage) {
            console.log('Not loading more tasks:', { isLoading: this.isLoading, hasNextPage: this.hasNextPage });
            return;
        }
        
        this.currentPage++;
        this.loadTasks(true);
    }

    updateResultsCount(totalCount, filteredCount) {
        const resultsCount = document.getElementById('results-count');
        if (resultsCount) {
            if (totalCount === filteredCount) {
                resultsCount.textContent = `Showing ${filteredCount} tasks`;
            } else {
                resultsCount.textContent = `Showing ${filteredCount} of ${totalCount} tasks`;
            }
        }
    }

    updatePagination(hasNext, hasPrevious, currentPage, totalPages) {
        const container = document.getElementById('pagination-container');
        if (!container) return;
        
        container.innerHTML = '';
        
        if (hasNext) {
            // Show Load More button
            const loadMoreBtn = document.createElement('button');
            loadMoreBtn.id = 'load-more-btn';
            loadMoreBtn.className = 'btn waves-effect waves-light';
            loadMoreBtn.innerHTML = '<i class="material-icons left">expand_more</i>Load More Tasks';
            
            const wrapper = document.createElement('div');
            wrapper.className = 'center-align';
            wrapper.appendChild(loadMoreBtn);
            
            container.appendChild(wrapper);
        } else if (currentPage > 1) {
            // Show "no more tasks" message
            const endMessage = document.createElement('p');
            endMessage.className = 'center-align grey-text';
            endMessage.innerHTML = '<i class="material-icons tiny">done_all</i> All tasks loaded';
            container.appendChild(endMessage);
        }
        
        // Show pagination info if there are multiple pages
        if (totalPages > 1) {
            const paginationInfo = document.createElement('p');
            paginationInfo.className = 'center-align pagination-info';
            paginationInfo.innerHTML = `Page ${currentPage} of ${totalPages}`;
            container.appendChild(paginationInfo);
        }
    }

    updateFilterToggleState() {
        const activeFiltersCount = this.getActiveFiltersCount();
        const badge = document.querySelector('.active-filters-count');
        
        if (activeFiltersCount > 0) {
            badge.textContent = activeFiltersCount;
            badge.classList.remove('hide');
        } else {
            badge.classList.add('hide');
        }
    }

    getActiveFiltersCount() {
        let count = 0;
        if (this.currentFilters.search) count++;
        if (this.currentFilters.projects.length > 0) count++;
        if (this.currentFilters.skills.length > 0) count++;
        if (this.currentFilters.statuses.length !== 3) count++; // Default is 3 statuses
        if (this.currentFilters.priorities.length !== 4) count++; // Default is 4 priorities
        if (this.currentFilters.created_after) count++;
        if (this.currentFilters.due_before) count++;
        return count;
    }

    updateUrlState() {
        // Update browser URL with current filters for bookmarking
        const params = new URLSearchParams();
        Object.entries(this.currentFilters).forEach(([key, value]) => {
            if (value && value.length > 0) {
                if (Array.isArray(value)) {
                    params.set(key, value.join(','));
                } else {
                    params.set(key, value);
                }
            }
        });
        
        const newUrl = `${window.location.pathname}?${params.toString()}`;
        window.history.replaceState(null, '', newUrl);
    }

    async getSkillsAutocompleteData() {
        try {
            const response = await fetch('/t/api/skills/autocomplete/');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            const autocompleteData = {};
            
            if (data.skills && Array.isArray(data.skills)) {
                data.skills.forEach(skill => {
                    autocompleteData[skill.name] = null; // Materialize format
                });
            }
            
            return autocompleteData;
        } catch (error) {
            console.error('Error fetching skills autocomplete data:', error);
            return {};
        }
    }

    showLoading() {
        const loading = document.getElementById('loading-indicator');
        if (loading) {
            loading.classList.remove('hide');
        }
        
        // Show loading state on Load More button
        const loadMoreBtn = document.getElementById('load-more-btn');
        if (loadMoreBtn) {
            loadMoreBtn.disabled = true;
            loadMoreBtn.innerHTML = '<i class="material-icons left">hourglass_empty</i>Loading...';
        }
        
        // Disable form controls during main loading
        if (!loadMoreBtn) {
            const controls = document.querySelectorAll('input, select, button');
            controls.forEach(control => {
                control.disabled = true;
            });
        }
    }

    hideLoading() {
        const loading = document.getElementById('loading-indicator');
        if (loading) {
            loading.classList.add('hide');
        }
        
        // Reset Load More button
        const loadMoreBtn = document.getElementById('load-more-btn');
        if (loadMoreBtn) {
            loadMoreBtn.disabled = false;
            loadMoreBtn.innerHTML = '<i class="material-icons left">expand_more</i>Load More Tasks';
        }
        
        // Re-enable form controls
        const controls = document.querySelectorAll('input, select, button');
        controls.forEach(control => {
            control.disabled = false;
        });
    }

    showError(message) {
        // Create toast notification
        M.toast({
            html: `<i class="material-icons left">error</i>${message}`,
            classes: 'red darken-2',
            displayLength: 5000
        });
    }
}

// Initialize task manager when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Only initialize on task list pages
    if (document.getElementById('tasks-container')) {
        window.taskManager = new TaskManager();
    }
});

// Export for potential external use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = TaskManager;
}