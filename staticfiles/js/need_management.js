// Enhanced Need Management JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Materialize components
    M.FormSelect.init(document.querySelectorAll('select'));
    M.Dropdown.init(document.querySelectorAll('.dropdown-trigger'));
    M.Chips.init(document.querySelectorAll('.chips'));
    
    // Global variables
    let currentPage = 1;
    let isLoading = false;

    // DOM Elements
    const filterToggle = document.getElementById('filter-toggle');
    const filtersPanel = document.getElementById('filters-panel');
    const searchInput = document.getElementById('need-search');
    const sortSelect = document.getElementById('sort-select');
    const needsContainer = document.getElementById('needs-container');
    const loadingIndicator = document.getElementById('loading-indicator');
    const resultsCount = document.getElementById('results-count');
    const emptyState = document.getElementById('empty-state');
    const activeFiltersCount = document.querySelector('.active-filters-count');

    // Filter toggle functionality
    if (filterToggle && filtersPanel) {
        filterToggle.addEventListener('click', function() {
            if (filtersPanel.classList.contains('hide')) {
                filtersPanel.classList.remove('hide');
                filterToggle.innerHTML = '<i class="material-icons left">filter_list</i>Hide Filters';
            } else {
                filtersPanel.classList.add('hide');
                filterToggle.innerHTML = '<i class="material-icons left">filter_list</i>Filters';
            }
        });
    }

    // View options
    const viewButtons = document.querySelectorAll('.view-btn');
    viewButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            viewButtons.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            
            const view = this.dataset.view;
            needsContainer.className = view === 'compact' ? 'row view-compact' : 'row';
        });
    });

    // Search functionality with debounce
    let searchTimeout;
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                currentPage = 1;
                loadNeeds();
            }, 500);
        });
    }

    // Sort functionality
    if (sortSelect) {
        sortSelect.addEventListener('change', function() {
            currentPage = 1;
            loadNeeds();
        });
    }

    // Filter change handlers
    const statusFilters = document.querySelectorAll('.status-filter');
    const priorityFilters = document.querySelectorAll('.priority-filter');
    const workTypeFilters = document.querySelectorAll('.work-type-filter');
    
    [...statusFilters, ...priorityFilters, ...workTypeFilters].forEach(filter => {
        filter.addEventListener('change', function() {
            currentPage = 1;
            updateActiveFiltersCount();
            // Auto-apply filters after a short delay
            setTimeout(loadNeeds, 300);
        });
    });

    // Apply filters button
    const applyFiltersBtn = document.getElementById('apply-filters');
    if (applyFiltersBtn) {
        applyFiltersBtn.addEventListener('click', function() {
            currentPage = 1;
            loadNeeds();
        });
    }

    // Clear filters button
    const clearFiltersBtn = document.getElementById('clear-filters');
    if (clearFiltersBtn) {
        clearFiltersBtn.addEventListener('click', function() {
            // Reset all filters
            if (searchInput) searchInput.value = '';
            
            statusFilters.forEach(f => f.checked = f.value === 'pending' || f.value === 'in_progress');
            priorityFilters.forEach(f => f.checked = true);
            workTypeFilters.forEach(f => f.checked = f.value === 'all');
            
            const skillsChips = M.Chips.getInstance(document.getElementById('skills-filter'));
            if (skillsChips) {
                skillsChips.chipsData = [];
            }
            
            document.getElementById('created-after').value = '';
            document.getElementById('deadline-before').value = '';
            
            const projectSelect = M.FormSelect.getInstance(document.getElementById('project-filter'));
            if (projectSelect) {
                projectSelect.getSelectedValues().forEach(val => {
                    projectSelect.el.querySelector(`option[value="${val}"]`).selected = false;
                });
                projectSelect._setSelectedStates();
            }
            
            updateActiveFiltersCount();
            currentPage = 1;
            loadNeeds();
        });
    }

    // Load needs function
    function loadNeeds() {
        if (isLoading) return;
        
        isLoading = true;
        showLoading();

        const params = new URLSearchParams();
        
        // Search
        if (searchInput && searchInput.value.trim()) {
            params.append('search', searchInput.value.trim());
        }
        
        // Status filters
        statusFilters.forEach(filter => {
            if (filter.checked) {
                params.append('status', filter.value);
            }
        });
        
        // Priority filters
        priorityFilters.forEach(filter => {
            if (filter.checked) {
                params.append('priority', filter.value);
            }
        });
        
        // Project filters
        const projectSelect = document.getElementById('project-filter');
        if (projectSelect) {
            const selectedProjects = M.FormSelect.getInstance(projectSelect).getSelectedValues();
            selectedProjects.forEach(projectId => {
                if (projectId) params.append('projects', projectId);
            });
        }
        
        // Skills filter
        const skillsFilter = document.getElementById('skills-filter');
        if (skillsFilter) {
            const skillsInstance = M.Chips.getInstance(skillsFilter);
            if (skillsInstance && skillsInstance.chipsData) {
                skillsInstance.chipsData.forEach(chip => {
                    params.append('skills', chip.tag);
                });
                
                const skillLogic = document.querySelector('input[name="skill-logic"]:checked');
                if (skillLogic) {
                    params.append('skill_logic', skillLogic.value);
                }
            }
        }
        
        // Date filters
        const createdAfter = document.getElementById('created-after');
        const deadlineBefore = document.getElementById('deadline-before');
        
        if (createdAfter && createdAfter.value) {
            params.append('created_after', createdAfter.value);
        }
        
        if (deadlineBefore && deadlineBefore.value) {
            params.append('deadline_before', deadlineBefore.value);
        }
        
        // Work type filters
        const workTypeChecked = Array.from(workTypeFilters).filter(f => f.checked);
        if (workTypeChecked.length > 0 && !workTypeChecked.some(f => f.value === 'all')) {
            workTypeChecked.forEach(filter => {
                params.append('work_type', filter.value);
            });
        }
        
        // Sorting
        if (sortSelect) {
            params.append('sort', sortSelect.value);
        }
        
        // Pagination
        params.append('page', currentPage);

        // Make AJAX request
        fetch(`/n/api/search/?${params.toString()}`, {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displayResults(data);
                updateResultsCount(data.total_count, data.filtered_count);
            } else {
                throw new Error(data.error || 'Failed to load needs');
            }
            hideLoading();
            isLoading = false;
        })
        .catch(error => {
            console.error('Error loading needs:', error);
            showError('Failed to load needs. Please try again.');
            hideLoading();
            isLoading = false;
        });
    }

    // Display results
    function displayResults(data) {
        if (!needsContainer) return;
        
        if (data.needs.length === 0) {
            needsContainer.innerHTML = '';
            if (emptyState) {
                emptyState.classList.remove('hide');
            }
            return;
        }
        
        if (emptyState) {
            emptyState.classList.add('hide');
        }
        
        const needsHtml = data.needs.map(need => createNeedCard(need)).join('');
        needsContainer.innerHTML = needsHtml;
        
        // Re-initialize dropdowns for new cards
        setTimeout(() => {
            M.Dropdown.init(needsContainer.querySelectorAll('.dropdown-trigger'));
        }, 100);
    }

    // Create need card HTML
    function createNeedCard(need) {
        const deadlineHtml = need.deadline_display ? 
            `<div class="meta-item deadline-item ${need.is_overdue ? 'overdue' : ''}">
                <i class="material-icons tiny">event</i>
                <span class="deadline">${need.deadline_display}</span>
            </div>` : '';
        
        const projectHtml = need.project ? 
            `<div class="project-association">
                <div class="chip project-chip">
                    <i class="material-icons tiny">folder</i>
                    <a href="/${need.project.id}/" class="project-link">${escapeHtml(need.project.name)}</a>
                </div>
            </div>` : '';
        
        const skillsHtml = need.required_skills.length > 0 ? 
            need.required_skills.map(skill => 
                `<a href="/n/skill/${encodeURIComponent(skill.name.toLowerCase())}/" class="chip skill-chip">${escapeHtml(skill.name)}</a>`
            ).join('') :
            '<div class="no-skills"><i class="material-icons tiny">label_outline</i><span>No skills specified</span></div>';

        const costHtml = need.cost_estimate ? 
            `<div class="info-item">
                <i class="material-icons tiny">attach_money</i>
                <span>$${Math.round(need.cost_estimate)}</span>
            </div>` : '';

        const remoteHtml = need.is_remote ? 
            `<div class="info-item remote-work">
                <i class="material-icons tiny">laptop</i>
                <span>Remote</span>
            </div>` : '';

        const stationaryHtml = need.is_stationary ? 
            `<div class="info-item stationary-work">
                <i class="material-icons tiny">location_on</i>
                <span>On-site</span>
            </div>` : '';

        const editButtonHtml = need.can_edit ? 
            `<a href="/n/${need.id}/edit/" class="btn-flat waves-effect action-btn">
                <i class="material-icons left">edit</i>Edit
            </a>` : '';

        const overdueHtml = need.is_overdue ? 
            '<span class="badge overdue-badge" data-badge-caption="Overdue">!</span>' : '';

        return `
            <div class="col s12 m6 l4 need-card-wrapper" data-need-id="${need.id}" data-priority="${need.priority}" data-status="${need.status}">
                <div class="card need-card ${need.priority_class} hoverable">
                    <div class="card-content">
                        <div class="need-header">
                            <div class="need-title-row">
                                <span class="card-title truncate">
                                    <a href="${need.url}" class="need-title-link">${escapeHtml(need.name)}</a>
                                </span>
                                <div class="need-badges">
                                    <span class="badge priority-badge ${need.priority_class}" data-badge-caption="${need.priority}%">${need.priority}</span>
                                    <span class="badge status-badge ${need.status_class}" data-badge-caption="${need.status_display}"></span>
                                    ${overdueHtml}
                                </div>
                            </div>
                            
                            <div class="progress-container">
                                <div class="progress">
                                    <div class="determinate" style="width: ${need.progress}%"></div>
                                </div>
                                <span class="progress-text">${need.progress}% Complete</span>
                            </div>
                        </div>

                        <div class="need-meta">
                            <div class="meta-item">
                                <i class="material-icons tiny">account_circle</i>
                                <a href="/u/${need.created_by.id}" class="creator-link">${escapeHtml(need.created_by.username)}</a>
                            </div>
                            <div class="meta-item">
                                <i class="material-icons tiny">access_time</i>
                                <span class="created-time">${need.created_date_display}</span>
                            </div>
                            ${deadlineHtml}
                        </div>

                        <div class="need-description">
                            <p class="description-text">
                                ${need.description ? escapeHtml(need.description.substring(0, 150)) + (need.description.length > 150 ? '...' : '') : '<em class="no-description">No description provided</em>'}
                            </p>
                        </div>

                        ${projectHtml}

                        <div class="skills-section">
                            <div class="skills-container">
                                ${skillsHtml}
                            </div>
                        </div>

                        <div class="need-info-row">
                            ${costHtml}
                            ${remoteHtml}
                            ${stationaryHtml}
                        </div>
                    </div>

                    <div class="card-action need-actions">
                        <a href="${need.url}" class="btn-flat waves-effect action-btn">
                            <i class="material-icons left">visibility</i>View
                        </a>
                        ${editButtonHtml}
                        <a href="/submissions/create/need/${need.id}/" class="btn-flat waves-effect action-btn apply-btn">
                            <i class="material-icons left">assignment</i>Apply
                        </a>
                        
                        <!-- Quick Actions Dropdown -->
                        <a class="dropdown-trigger btn-flat waves-effect action-btn right" href="#!" data-target="need-actions-${need.id}">
                            <i class="material-icons">more_vert</i>
                        </a>
                        
                        <!-- Dropdown Content -->
                        <ul id="need-actions-${need.id}" class="dropdown-content">
                            <li><a href="/submissions/list/need/${need.id}/"><i class="material-icons">assignment</i>View Submissions</a></li>
                            ${need.can_edit ? `
                            <li><a href="#!" class="quick-status-update" data-need-id="${need.id}" data-status="fulfilled">
                                <i class="material-icons">check_circle</i>Mark Fulfilled
                            </a></li>
                            <li><a href="/n/${need.id}/log-time/">
                                <i class="material-icons">access_time</i>Log Time
                            </a></li>
                            <li class="divider"></li>
                            <li><a href="#!" class="delete-need" data-need-id="${need.id}">
                                <i class="material-icons red-text">delete</i>Delete
                            </a></li>
                            ` : ''}
                        </ul>
                    </div>
                </div>
            </div>
        `;
    }

    // Helper function to escape HTML
    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Update results count
    function updateResultsCount(totalCount, filteredCount) {
        if (resultsCount) {
            if (totalCount === filteredCount) {
                resultsCount.textContent = `Showing ${filteredCount} needs`;
            } else {
                resultsCount.textContent = `Showing ${filteredCount} of ${totalCount} needs`;
            }
        }
    }

    // Update active filters count
    function updateActiveFiltersCount() {
        let count = 0;
        
        // Check search
        if (searchInput && searchInput.value.trim()) count++;
        
        // Check status filters (default is pending + in_progress)
        const checkedStatuses = Array.from(statusFilters).filter(f => f.checked);
        if (checkedStatuses.length !== 2 || !checkedStatuses.some(f => f.value === 'pending') || !checkedStatuses.some(f => f.value === 'in_progress')) {
            count++;
        }
        
        // Check priority filters (default is all checked)
        const checkedPriorities = Array.from(priorityFilters).filter(f => f.checked);
        if (checkedPriorities.length !== priorityFilters.length) count++;
        
        // Check work type filters
        const checkedWorkTypes = Array.from(workTypeFilters).filter(f => f.checked);
        if (checkedWorkTypes.length !== 1 || !checkedWorkTypes.some(f => f.value === 'all')) {
            count++;
        }
        
        // Check date filters
        if (document.getElementById('created-after')?.value) count++;
        if (document.getElementById('deadline-before')?.value) count++;
        
        // Check skills
        const skillsFilter = document.getElementById('skills-filter');
        if (skillsFilter) {
            const skillsInstance = M.Chips.getInstance(skillsFilter);
            if (skillsInstance && skillsInstance.chipsData && skillsInstance.chipsData.length > 0) {
                count++;
            }
        }
        
        // Check projects
        const projectSelect = document.getElementById('project-filter');
        if (projectSelect) {
            const selected = M.FormSelect.getInstance(projectSelect)?.getSelectedValues();
            if (selected && selected.length > 0 && selected[0] !== '') {
                count++;
            }
        }
        
        if (activeFiltersCount) {
            if (count > 0) {
                activeFiltersCount.textContent = count;
                activeFiltersCount.classList.remove('hide');
            } else {
                activeFiltersCount.classList.add('hide');
            }
        }
    }

    // Show loading state
    function showLoading() {
        if (loadingIndicator) {
            loadingIndicator.classList.remove('hide');
        }
    }

    // Hide loading state
    function hideLoading() {
        if (loadingIndicator) {
            loadingIndicator.classList.add('hide');
        }
    }

    // Show error message
    function showError(message) {
        M.toast({
            html: `<i class="material-icons left">error</i>${message}`,
            classes: 'red darken-2',
            displayLength: 5000
        });
    }

    // Quick actions
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('quick-status-update')) {
            e.preventDefault();
            const needId = e.target.dataset.needId;
            const status = e.target.dataset.status;
            quickUpdateNeed(needId, 'status', status);
        }
        
        if (e.target.classList.contains('delete-need')) {
            e.preventDefault();
            const needId = e.target.dataset.needId;
            if (confirm('Are you sure you want to delete this need?')) {
                window.location.href = `/n/${needId}/delete/`;
            }
        }
    });

    // Quick update function
    function quickUpdateNeed(needId, field, value) {
        // Get CSRF token
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
                         document.querySelector('meta[name=csrf-token]')?.getAttribute('content');
        
        fetch(`/n/api/quick-update/${needId}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
                'X-Requested-With': 'XMLHttpRequest',
            },
            body: JSON.stringify({
                field: field,
                value: value
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                M.toast({
                    html: `<i class="material-icons left">check</i>${data.message}`,
                    classes: 'green darken-2',
                    displayLength: 3000
                });
                // Reload the current page to reflect changes
                setTimeout(() => {
                    loadNeeds();
                }, 1000);
            } else {
                throw new Error(data.error || 'Update failed');
            }
        })
        .catch(error => {
            console.error('Quick update error:', error);
            showError('Failed to update need: ' + error.message);
        });
    }

    // Initialize skills filter with autocomplete
    function initializeSkillsFilter() {
        const skillsFilter = document.getElementById('skills-filter');
        if (!skillsFilter) return;

        // Fetch skills for autocomplete
        fetch('/n/api/skills/autocomplete/')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    const autocompleteData = {};
                    data.skills.forEach(skill => {
                        autocompleteData[skill.name] = null; // Materialize format
                    });

                    M.Chips.init(skillsFilter, {
                        placeholder: 'Add skill tags...',
                        secondaryPlaceholder: 'Enter skill name',
                        autocompleteOptions: {
                            data: autocompleteData,
                            limit: 10,
                            minLength: 1
                        },
                        onChipAdd: function() {
                            updateActiveFiltersCount();
                        },
                        onChipDelete: function() {
                            updateActiveFiltersCount();
                        }
                    });
                }
            })
            .catch(error => {
                console.warn('Could not load skills autocomplete:', error);
                // Initialize without autocomplete
                M.Chips.init(skillsFilter, {
                    placeholder: 'Add skill tags...',
                    secondaryPlaceholder: 'Enter skill name',
                    onChipAdd: function() {
                        updateActiveFiltersCount();
                    },
                    onChipDelete: function() {
                        updateActiveFiltersCount();
                    }
                });
            });
    }

    // Initialize everything
    initializeSkillsFilter();
    updateActiveFiltersCount();
    
    // Load initial needs if we're on the needs page
    if (needsContainer) {
        loadNeeds();
    }
});