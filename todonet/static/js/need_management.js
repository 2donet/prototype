/**
 * Enhanced Need Management System - Main JavaScript File
 * Handles search, filtering, sorting, and AJAX updates for needs
 */

class NeedManager {
    constructor() {
        this.currentPage = 1;
        this.needsPerPage = 24;
        this.searchTimeout = null;
        this.currentFilters = {
            search: '',
            projects: [],
            skills: [],
            skill_logic: 'any',
            statuses: ['pending', 'in_progress'],
            priorities: ['high', 'medium', 'low', 'minimal'],
            work_types: ['all'],
            created_after: '',
            deadline_before: '',
            sort: '-created_date'
        };
        this.currentView = 'cards';
        this.isLoading = false;
        this.hasNextPage = true;
        this.totalPages = 0;
        this.skillsInstance = null;
        
        this.init();
    }

    init() {
        this.bindEvents();
        this.initializeComponents();
        this.loadNeeds();
    }

    bindEvents() {
        // Search functionality
        const searchInput = document.getElementById('need-search');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                clearTimeout(this.searchTimeout);
                this.searchTimeout = setTimeout(() => {
                    this.currentFilters.search = e.target.value.trim();
                    this.resetPagination();
                    this.loadNeeds();
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
                this.loadNeeds();
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

        // Load more button event delegation
        document.addEventListener('click', (e) => {
            if (e.target && e.target.id === 'load-more-btn') {
                e.preventDefault();
                this.loadMoreNeeds();
            }
        });

        // Infinite scroll
        this.bindScrollEvents();

        // Quick actions
        this.bindQuickActions();
    }

    bindFilterEvents() {
        // Project filter
        const projectFilter = document.getElementById('project-filter');
        if (projectFilter) {
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

        // Work type checkboxes
        const workTypeFilters = document.querySelectorAll('.work-type-filter');
        workTypeFilters.forEach(checkbox => {
            checkbox.addEventListener('change', () => {
                this.updateWorkTypeFilters();
            });
        });

        // Date filters
        const createdAfter = document.getElementById('created-after');
        const deadlineBefore = document.getElementById('deadline-before');
        
        if (createdAfter) {
            createdAfter.addEventListener('change', (e) => {
                this.currentFilters.created_after = e.target.value;
            });
        }

        if (deadlineBefore) {
            deadlineBefore.addEventListener('change', (e) => {
                this.currentFilters.deadline_before = e.target.value;
            });
        }

        // Skill logic radio buttons
        const skillLogicRadios = document.querySelectorAll('input[name="skill-logic"]');
        skillLogicRadios.forEach(radio => {
            radio.addEventListener('change', (e) => {
                this.currentFilters.skill_logic = e.target.value;
                console.log('Skill logic changed to:', e.target.value);
            });
        });
    }

    bindScrollEvents() {
        let scrollTimeout = null;
        
        window.addEventListener('scroll', () => {
            if (scrollTimeout) {
                clearTimeout(scrollTimeout);
            }
            
            scrollTimeout = setTimeout(() => {
                if (this.isLoading || !this.hasNextPage) return;
                
                const scrollPosition = window.innerHeight + window.scrollY;
                const documentHeight = document.documentElement.offsetHeight;
                
                if (scrollPosition >= documentHeight - 200) {
                    console.log('Scroll triggered load more');
                    this.loadMoreNeeds();
                }
            }, 100);
        });
    }

    bindQuickActions() {
        // Quick status updates
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('quick-status-update')) {
                e.preventDefault();
                const needId = e.target.dataset.needId;
                const status = e.target.dataset.status;
                this.quickUpdateNeed(needId, 'status', status);
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
        if (!skillsFilter) {
            console.log('Skills filter element not found');
            return;
        }

        try {
            console.log('Initializing skills filter...');
            
            // Fetch autocomplete data
            const autocompleteData = await this.getSkillsAutocompleteData();
            console.log('Fetched autocomplete data:', Object.keys(autocompleteData).length, 'skills');
            
            // Initialize chips with autocomplete
            this.skillsInstance = M.Chips.init(skillsFilter, {
                placeholder: 'Add skill tags...',
                secondaryPlaceholder: 'Enter skill name',
                autocompleteOptions: {
                    data: autocompleteData,
                    limit: 10,
                    minLength: 1
                },
                onChipAdd: (element, chip) => {
                    console.log('Chip added:', chip.tag);
                    setTimeout(() => {
                        this.updateSkillsFilter();
                    }, 50);
                },
                onChipDelete: (element, chip) => {
                    console.log('Chip deleted:', chip.tag);
                    setTimeout(() => {
                        this.updateSkillsFilter();
                    }, 50);
                }
            });
            
            console.log('Skills chips initialized successfully');
            
        } catch (error) {
            console.error('Error initializing skills filter:', error);
            
            // Fallback initialization without autocomplete
            this.skillsInstance = M.Chips.init(skillsFilter, {
                placeholder: 'Add skill tags...',
                secondaryPlaceholder: 'Enter skill name',
                onChipAdd: (element, chip) => {
                    console.log('Chip added (fallback):', chip.tag);
                    setTimeout(() => {
                        this.updateSkillsFilter();
                    }, 50);
                },
                onChipDelete: (element, chip) => {
                    console.log('Chip deleted (fallback):', chip.tag);
                    setTimeout(() => {
                        this.updateSkillsFilter();
                    }, 50);
                }
            });
        }
    }

    async getSkillsAutocompleteData() {
        try {
            console.log('Fetching skills autocomplete data from /n/api/skills/autocomplete/');
            
            const response = await fetch('/n/api/skills/autocomplete/', {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'Content-Type': 'application/json',
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            console.log('Autocomplete API response:', data);
            
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

    async loadNeeds(append = false) {
        if (this.isLoading) return;
        
        this.isLoading = true;
        this.showLoading();

        try {
            const params = new URLSearchParams({
                page: this.currentPage,
                per_page: this.needsPerPage,
                search: this.currentFilters.search,
                skill_logic: this.currentFilters.skill_logic,
                created_after: this.currentFilters.created_after,
                deadline_before: this.currentFilters.deadline_before,
                sort: this.currentFilters.sort
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
            if (this.currentFilters.work_types.length > 0 && !this.currentFilters.work_types.includes('all')) {
                params.set('work_types', this.currentFilters.work_types.join(','));
            }

            console.log('Loading needs with params:', params.toString());

            const response = await fetch(`/n/api/search/?${params}`, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'Content-Type': 'application/json',
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            this.renderNeeds(data.needs, append);
            this.updateResultsCount(data.total_count, data.filtered_count);
            this.updatePagination(data.has_next, data.has_previous, data.current_page, data.total_pages);
            
            this.hasNextPage = data.has_next;
            this.totalPages = data.total_pages;
            
        } catch (error) {
            console.error('Error loading needs:', error);
            this.showError('Failed to load needs. Please try again.');
        } finally {
            this.isLoading = false;
            this.hideLoading();
        }
    }

    renderNeeds(needs, append = false) {
        const container = document.getElementById('needs-container');
        const emptyState = document.getElementById('empty-state');
        
        if (!append) {
            container.innerHTML = '';
        }

        if (needs.length === 0 && !append) {
            container.classList.add('hide');
            emptyState.classList.remove('hide');
            return;
        }

        container.classList.remove('hide');
        emptyState.classList.add('hide');

        needs.forEach(need => {
            const needCard = this.createNeedCard(need);
            container.appendChild(needCard);
        });

        this.initializeMaterialize();
        
        if (!append) {
            const cards = container.querySelectorAll('.need-card-wrapper');
            cards.forEach((card, index) => {
                setTimeout(() => {
                    card.classList.add('new-card');
                }, index * 50);
            });
        }
    }

    createNeedCard(need) {
        const wrapper = document.createElement('div');
        wrapper.className = `col s12 m6 l4 need-card-wrapper`;
        wrapper.setAttribute('data-need-id', need.id);
        wrapper.setAttribute('data-priority', need.priority);
        wrapper.setAttribute('data-status', need.status);
        wrapper.setAttribute('data-created', need.created_date);
        
        wrapper.innerHTML = this.getNeedCardHTML(need);
        
        return wrapper;
    }

    getNeedCardHTML(need) {
        return `
            <div class="card need-card ${need.priority_class} hoverable">
                <div class="card-content">
                    <div class="need-header">
                        <div class="need-title-row">
                            <span class="card-title truncate">
                                <a href="/n/${need.id}/" class="need-title-link">${this.escapeHtml(need.name)}</a>
                            </span>
                            <div class="need-badges">
                                <span class="badge priority-badge ${need.priority_class}" data-badge-caption="${need.priority}%">${need.priority}</span>
                                <span class="badge status-badge ${need.status_class}" data-badge-caption="${need.status_display}"></span>
                                ${need.is_overdue ? '<span class="badge overdue-badge" data-badge-caption="Overdue">!</span>' : ''}
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
                            <a href="/u/${need.created_by.id}" class="creator-link">${this.escapeHtml(need.created_by.username)}</a>
                        </div>
                        <div class="meta-item">
                            <i class="material-icons tiny">access_time</i>
                            <span class="created-time">${need.created_date_display}</span>
                        </div>
                        ${need.deadline ? `
                        <div class="meta-item deadline-item ${need.is_overdue ? 'overdue' : ''}">
                            <i class="material-icons tiny">event</i>
                            <span class="deadline">${need.deadline_display}</span>
                        </div>
                        ` : ''}
                    </div>
                    
                    <div class="need-description">
                        <p class="description-text">${need.description ? this.escapeHtml(need.description) : '<em class="no-description">No description provided</em>'}</p>
                    </div>
                    
                    ${need.project ? `
                    <div class="project-association">
                        <div class="chip project-chip">
                            <i class="material-icons tiny">folder</i>
                            <a href="/${need.project.id}" class="project-link">${this.escapeHtml(need.project.name)}</a>
                        </div>
                    </div>
                    ` : ''}
                    
                    <div class="skills-section">
                        ${need.required_skills && need.required_skills.length > 0 ? `
                        <div class="skills-container">
                            ${need.required_skills.map(skill => `
                                <a href="/n/skill/${encodeURIComponent(skill.name.toLowerCase())}/" class="chip skill-chip">${this.escapeHtml(skill.name)}</a>
                            `).join('')}
                        </div>
                        ` : '<div class="no-skills"><i class="material-icons tiny">label_outline</i><span>No skills specified</span></div>'}
                    </div>

                    <div class="need-info-row">
                        ${need.cost_estimate ? `
                        <div class="info-item">
                            <i class="material-icons tiny">attach_money</i>
                            <span>$${Math.round(need.cost_estimate)}</span>
                        </div>
                        ` : ''}
                        
                        ${need.is_remote ? `
                        <div class="info-item remote-work">
                            <i class="material-icons tiny">laptop</i>
                            <span>Remote</span>
                        </div>
                        ` : ''}
                        
                        ${need.is_stationary ? `
                        <div class="info-item stationary-work">
                            <i class="material-icons tiny">location_on</i>
                            <span>On-site</span>
                        </div>
                        ` : ''}
                    </div>
                </div>
                
                <div class="card-action need-actions">
                    <a href="/n/${need.id}/" class="btn-flat waves-effect action-btn">
                        <i class="material-icons left">visibility</i>View
                    </a>
                    ${need.can_edit ? `
                    <a href="/n/${need.id}/edit/" class="btn-flat waves-effect action-btn">
                        <i class="material-icons left">edit</i>Edit
                    </a>
                    ` : ''}
                    <a href="/submissions/create/need/${need.id}/" class="btn-flat waves-effect action-btn apply-btn">
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
            console.log('Updated project filters:', this.currentFilters.projects);
        }
    }

    updateStatusFilters() {
        const statusCheckboxes = document.querySelectorAll('.status-filter:checked');
        this.currentFilters.statuses = Array.from(statusCheckboxes).map(cb => cb.value);
        console.log('Updated status filters:', this.currentFilters.statuses);
    }

    updatePriorityFilters() {
        const priorityCheckboxes = document.querySelectorAll('.priority-filter:checked');
        this.currentFilters.priorities = Array.from(priorityCheckboxes).map(cb => cb.value);
        console.log('Updated priority filters:', this.currentFilters.priorities);
    }

    updateWorkTypeFilters() {
        const workTypeCheckboxes = document.querySelectorAll('.work-type-filter:checked');
        this.currentFilters.work_types = Array.from(workTypeCheckboxes).map(cb => cb.value);
        console.log('Updated work type filters:', this.currentFilters.work_types);
    }

    updateSkillsFilter() {
        console.log('updateSkillsFilter called');
        
        let skillNames = [];
        let method = 'none';
        
        // Method 1: Use stored instance
        if (this.skillsInstance && this.skillsInstance.chipsData && this.skillsInstance.chipsData.length > 0) {
            skillNames = this.skillsInstance.chipsData.map(chip => chip.tag).filter(tag => tag && tag.trim());
            method = 'stored instance';
        }
        
        // Method 2: Get instance directly if method 1 failed
        if (skillNames.length === 0) {
            const skillsFilterElement = document.getElementById('skills-filter');
            if (skillsFilterElement) {
                const instance = M.Chips.getInstance(skillsFilterElement);
                if (instance && instance.chipsData && instance.chipsData.length > 0) {
                    skillNames = instance.chipsData.map(chip => chip.tag).filter(tag => tag && tag.trim());
                    method = 'direct instance';
                    this.skillsInstance = instance;
                }
            }
        }
        
        // Method 3: Parse DOM directly as fallback
        if (skillNames.length === 0) {
            const skillsFilterElement = document.getElementById('skills-filter');
            if (skillsFilterElement) {
                const chipElements = skillsFilterElement.querySelectorAll('.chip:not(.input)');
                skillNames = Array.from(chipElements).map(chip => {
                    const text = chip.textContent || '';
                    return text.replace(/close\s*$/, '').trim();
                }).filter(name => name && name !== 'close');
                
                if (skillNames.length > 0) {
                    method = 'DOM parsing';
                }
            }
        }
        
        this.currentFilters.skills = skillNames;
        console.log(`Updated skills filter (${method}):`, skillNames);
        
        if (this.skillsInstance && this.skillsInstance.chipsData) {
            console.log('Raw chips data:', this.skillsInstance.chipsData);
        }
    }

    changeView(viewType) {
        this.currentView = viewType;
        
        document.querySelectorAll('.view-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-view="${viewType}"]`).classList.add('active');
        
        const container = document.getElementById('needs-container');
        container.className = `row view-${viewType}`;
        
        if (viewType === 'compact') {
            container.querySelectorAll('.need-card-wrapper').forEach(card => {
                card.className = 'col s12 need-card-wrapper';
            });
        } else {
            container.querySelectorAll('.need-card-wrapper').forEach(card => {
                card.className = 'col s12 m6 l4 need-card-wrapper';
            });
        }
    }

    clearAllFilters() {
        console.log('Clearing all filters');
        
        this.currentFilters = {
            search: '',
            projects: [],
            skills: [],
            skill_logic: 'any',
            statuses: ['pending', 'in_progress'],
            priorities: ['high', 'medium', 'low', 'minimal'],
            work_types: ['all'],
            created_after: '',
            deadline_before: '',
            sort: '-created_date'
        };

        this.resetPagination();

        // Clear UI elements
        document.getElementById('need-search').value = '';
        
        // Reset checkboxes
        document.querySelectorAll('.status-filter').forEach(cb => {
            cb.checked = ['pending', 'in_progress'].includes(cb.value);
        });
        
        document.querySelectorAll('.priority-filter').forEach(cb => {
            cb.checked = true;
        });

        document.querySelectorAll('.work-type-filter').forEach(cb => {
            cb.checked = cb.value === 'all';
        });

        // Clear date inputs
        document.getElementById('created-after').value = '';
        document.getElementById('deadline-before').value = '';

        // Clear skills chips
        this.clearSkillsChips();

        // Reset project select
        const projectSelect = document.getElementById('project-filter');
        if (projectSelect) {
            projectSelect.selectedIndex = 0;
            M.FormSelect.init(projectSelect);
        }

        // Reset skill logic
        const anyRadio = document.querySelector('input[name="skill-logic"][value="any"]');
        if (anyRadio) anyRadio.checked = true;

        this.loadNeeds();
    }

    clearSkillsChips() {
        if (this.skillsInstance) {
            this.skillsInstance.chipsData = [];
            this.skillsInstance._renderChips();
            console.log('Cleared chips using stored instance');
            return;
        }
        
        const skillsFilterElement = document.getElementById('skills-filter');
        if (skillsFilterElement) {
            const instance = M.Chips.getInstance(skillsFilterElement);
            if (instance) {
                instance.chipsData = [];
                instance._renderChips();
                this.skillsInstance = instance;
                console.log('Cleared chips using direct instance');
                return;
            }
        }
        
        if (skillsFilterElement) {
            const existingChips = skillsFilterElement.querySelectorAll('.chip:not(.input)');
            existingChips.forEach(chip => chip.remove());
            console.log('Cleared chips using DOM manipulation');
        }
    }

    applyFilters() {
        console.log('=== APPLYING FILTERS ===');
        
        this.refreshChipsData();
        
        // Update all filters before applying
        this.updateProjectFilters();
        this.updateStatusFilters();
        this.updatePriorityFilters();
        this.updateWorkTypeFilters();
        this.updateSkillsFilter();
        
        // Update skill logic
        const skillLogicRadio = document.querySelector('input[name="skill-logic"]:checked');
        if (skillLogicRadio) {
            this.currentFilters.skill_logic = skillLogicRadio.value;
        }
        
        console.log('Final filters to apply:', this.currentFilters);
        
        this.resetPagination();
        this.loadNeeds();
        this.updateFilterToggleState();
    }

    refreshChipsData() {
        const skillsFilterElement = document.getElementById('skills-filter');
        if (skillsFilterElement) {
            const instance = M.Chips.getInstance(skillsFilterElement);
            if (instance) {
                this.skillsInstance = instance;
                console.log('Refreshed chips instance, current data:', instance.chipsData);
            }
        }
    }

    loadMoreNeeds() {
        if (this.isLoading) {
            console.log('Not loading more needs: already loading');
            return;
        }
        
        if (!this.hasNextPage) {
            console.log('Not loading more needs: no more pages available');
            return;
        }
        
        console.log(`Loading more needs - current page: ${this.currentPage}, total pages: ${this.totalPages}`);
        this.currentPage++;
        this.loadNeeds(true);
    }

    updateResultsCount(totalCount, filteredCount) {
        const resultsCount = document.getElementById('results-count');
        if (resultsCount) {
            if (totalCount === filteredCount) {
                resultsCount.textContent = `Showing ${filteredCount} needs`;
            } else {
                resultsCount.textContent = `Showing ${filteredCount} of ${totalCount} needs`;
            }
        }
    }

    updatePagination(hasNext, hasPrevious, currentPage, totalPages) {
        const container = document.getElementById('pagination-container');
        if (!container) return;
        
        container.innerHTML = '';
        
        if (hasNext) {
            const loadMoreBtn = document.createElement('button');
            loadMoreBtn.id = 'load-more-btn';
            loadMoreBtn.className = 'btn waves-effect waves-light';
            loadMoreBtn.innerHTML = '<i class="material-icons left">expand_more</i>Load More Needs';
            
            const wrapper = document.createElement('div');
            wrapper.className = 'center-align';
            wrapper.appendChild(loadMoreBtn);
            
            container.appendChild(wrapper);
        } else if (currentPage > 1) {
            const endMessage = document.createElement('p');
            endMessage.className = 'center-align grey-text';
            endMessage.innerHTML = '<i class="material-icons tiny">done_all</i> All needs loaded';
            container.appendChild(endMessage);
        }
        
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
        
        if (badge) {
            if (activeFiltersCount > 0) {
                badge.textContent = activeFiltersCount;
                badge.classList.remove('hide');
            } else {
                badge.classList.add('hide');
            }
        }
    }

    getActiveFiltersCount() {
        let count = 0;
        if (this.currentFilters.search) count++;
        if (this.currentFilters.projects.length > 0) count++;
        if (this.currentFilters.skills.length > 0) count++;
        if (this.currentFilters.statuses.length !== 2) count++; // Default is 2 statuses
        if (this.currentFilters.priorities.length !== 4) count++; // Default is 4 priorities
        if (this.currentFilters.work_types.length > 0 && !this.currentFilters.work_types.includes('all')) count++;
        if (this.currentFilters.created_after) count++;
        if (this.currentFilters.deadline_before) count++;
        return count;
    }

    updateUrlState() {
        const params = new URLSearchParams();
        Object.entries(this.currentFilters).forEach(([key, value]) => {
            if (value && (Array.isArray(value) ? value.length > 0 : true)) {
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

    async quickUpdateNeed(needId, field, value) {
        try {
            const response = await fetch(`/n/api/quick-update/${needId}/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': window.csrfToken,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    field: field,
                    value: value
                })
            });

            const data = await response.json();
            
            if (data.success) {
                M.toast({
                    html: `<i class="material-icons left">check</i>${data.message}`,
                    classes: 'green darken-2',
                    displayLength: 3000
                });
                
                // Reload needs to reflect changes
                this.loadNeeds();
            } else {
                throw new Error(data.error || 'Update failed');
            }
        } catch (error) {
            console.error('Quick update error:', error);
            this.showError('Failed to update need: ' + error.message);
        }
    }

    showLoading() {
        const loading = document.getElementById('loading-indicator');
        if (loading) {
            loading.classList.remove('hide');
        }
        
        const loadMoreBtn = document.getElementById('load-more-btn');
        if (loadMoreBtn) {
            loadMoreBtn.disabled = true;
            loadMoreBtn.innerHTML = '<i class="material-icons left">hourglass_empty</i>Loading...';
        }
    }

    hideLoading() {
        const loading = document.getElementById('loading-indicator');
        if (loading) {
            loading.classList.add('hide');
        }
        
        const loadMoreBtn = document.getElementById('load-more-btn');
        if (loadMoreBtn) {
            loadMoreBtn.disabled = false;
            loadMoreBtn.innerHTML = '<i class="material-icons left">expand_more</i>Load More Needs';
        }
    }

    showError(message) {
        M.toast({
            html: `<i class="material-icons left">error</i>${message}`,
            classes: 'red darken-2',
            displayLength: 5000
        });
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('needs-container')) {
        console.log('Initializing Need Manager');
        window.needManager = new NeedManager();
    }
});

if (typeof module !== 'undefined' && module.exports) {
    module.exports = NeedManager;
}