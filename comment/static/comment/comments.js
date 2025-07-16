document.addEventListener('DOMContentLoaded', function() {
    // Helper function to get CSRF token
    function getCSRFToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        return token ? token.value : '';
    }

    // Helper functions
    const showToast = (message, classes = '') => {
        if (typeof M !== 'undefined') {
            M.toast({html: message, classes: classes});
        } else {
            alert(message);
        }
    };

    const disableButton = (button, text = 'Processing...') => {
        button.disabled = true;
        button.innerHTML = `<i class="material-icons left">hourglass_empty</i>${text}`;
    };

    const enableButton = (button, text = 'Post Comment') => {
        button.disabled = false;
        button.innerHTML = `<i class="material-icons left">send</i>${text}`;
    };

    // Main comment form submission
    const addCommentForm = document.getElementById('add-comment-form');
    if (addCommentForm) {
        addCommentForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const submitButton = e.target.querySelector('button[type="submit"]');
            disableButton(submitButton);

            try {
                const formData = new FormData(e.target);
                const response = await fetch('/comments/add/', {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                        'X-CSRFToken': formData.get('csrfmiddlewaretoken')
                    }
                });

                const data = await response.json();
                
                if (data.status === 'error') {
                    throw new Error(data.error || 'Unknown error occurred');
                }

                // Success - add new comment to DOM
                const commentHtml = createCommentHtml(data.comment);
                let commentsContainer = document.getElementById('comments-container');
                
                // If no container exists yet, create one
                if (!commentsContainer) {
                    // Look for existing comments or create a new container
                    const existingComments = document.querySelector('.comment');
                    if (existingComments && existingComments.parentElement) {
                        commentsContainer = existingComments.parentElement;
                    } else {
                        commentsContainer = createCommentsContainer();
                    }
                }
                
                // Insert the new comment
                commentsContainer.insertAdjacentHTML('beforeend', commentHtml);
                
                // Get the newly added element and initialize it
                const newComment = commentsContainer.lastElementChild;
                addCommentEventListeners(newComment);
                
                // Clear the form
                e.target.reset();
                
                // Manually clear and resize textarea for Materialize
                const textarea = e.target.querySelector('textarea[name="content"]');
                if (textarea) {
                    textarea.value = '';
                    if (typeof M !== 'undefined') {
                        M.textareaAutoResize(textarea);
                        M.updateTextFields();
                    }
                }
                
                showToast('Comment posted successfully!', 'green');
                
                // Smooth scroll to new comment
                newComment.scrollIntoView({ behavior: 'smooth', block: 'center' });

            } catch (error) {
                console.error('Comment submission error:', error);
                showToast(error.message || 'Error posting comment', 'red');
            } finally {
                enableButton(submitButton, 'Post Comment');
            }
        });
    }

    // Reply form handling
    document.addEventListener('submit', async (e) => {
        if (e.target.classList.contains('reply-form')) {
            e.preventDefault();
            const submitButton = e.target.querySelector('button[type="submit"]');
            disableButton(submitButton, 'Posting Reply...');

            try {
                const formData = new FormData(e.target);
                const response = await fetch('/comments/add/', {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                        'X-CSRFToken': formData.get('csrfmiddlewaretoken')
                    }
                });

                const data = await response.json();
                
                if (data.status === 'error') {
                    throw new Error(data.error || 'Error posting reply');
                }

                // Success - add reply to DOM
                const replyHtml = createCommentHtml(data.comment, true);
                const parentId = data.comment.parent_id;
                const repliesContainer = document.querySelector(`.replies-container[data-comment-id="${parentId}"]`);
                
                if (repliesContainer) {
                    repliesContainer.insertAdjacentHTML('beforeend', replyHtml);
                    repliesContainer.style.display = 'block';
                    addCommentEventListeners(repliesContainer.lastElementChild);
                    
                    // Update reply count
                    const replyCountElement = document.querySelector(`.comment[data-comment-id="${parentId}"] .reply-count`);
                    if (replyCountElement) {
                        const currentCount = parseInt(replyCountElement.textContent) || 0;
                        replyCountElement.textContent = currentCount + 1;
                    }
                }

                e.target.reset();
                e.target.closest('.reply-form-container').style.display = 'none';
                showToast('Reply posted successfully!', 'green');

            } catch (error) {
                console.error('Reply submission error:', error);
                showToast(error.message, 'red');
            } finally {
                enableButton(submitButton, 'Post Reply');
            }
        }
    });

    // Toggle reply forms
    document.addEventListener('click', (e) => {
        if (e.target.classList.contains('reply-btn') || e.target.parentElement?.classList.contains('reply-btn')) {
            e.preventDefault();
            e.stopPropagation();
            
            const replyBtn = e.target.classList.contains('reply-btn') ? e.target : e.target.parentElement;
            const commentId = replyBtn.getAttribute('data-comment-id');
            const comment = replyBtn.closest('.comment');
            const replyForm = comment.querySelector(`.reply-form-container[data-comment-id="${commentId}"]`);
            
            if (replyForm) {
                const isHidden = replyForm.style.display === 'none' || !replyForm.style.display;
                replyForm.style.display = isHidden ? 'block' : 'none';
                
                if (isHidden) {
                    const textarea = replyForm.querySelector('textarea');
                    if (textarea) {
                        textarea.focus();
                        if (typeof M !== 'undefined') {
                            M.textareaAutoResize(textarea);
                        }
                    }
                }
            }
        }

        // Cancel reply
        if (e.target.classList.contains('cancel-reply')) {
            e.preventDefault();
            const replyForm = e.target.closest('.reply-form-container');
            if (replyForm) {
                replyForm.style.display = 'none';
                const textarea = replyForm.querySelector('textarea');
                if (textarea) textarea.value = '';
            }
        }
    });

    // View replies toggle
    document.addEventListener('click', async (e) => {
        if (e.target.classList.contains('view-replies-btn')) {
            e.preventDefault();
            const commentId = e.target.getAttribute('data-comment-id');
            const repliesContainer = document.querySelector(`.replies-container[data-comment-id="${commentId}"]`);
            
            if (repliesContainer) {
                if (repliesContainer.style.display === 'none' || !repliesContainer.style.display) {
                    // Load replies if not already loaded
                    if (!repliesContainer.hasChildNodes()) {
                        await loadReplies(commentId, repliesContainer);
                    }
                    repliesContainer.style.display = 'block';
                    e.target.textContent = 'Hide Replies';
                } else {
                    repliesContainer.style.display = 'none';
                    e.target.textContent = 'View Replies';
                }
            }
        }
    });

    // Vote handling
    document.addEventListener('click', async (e) => {
        if (e.target.classList.contains('upvote-btn') || e.target.classList.contains('downvote-btn')) {
            e.preventDefault();
            await handleVote(e.target);
        }
    });

    // Reaction handling
    document.addEventListener('click', async (e) => {
        if (e.target.classList.contains('reaction-btn')) {
            e.preventDefault();
            await handleReaction(e.target);
        }
    });

    // Initialize Materialize components
    if (typeof M !== 'undefined') {
        M.Dropdown.init(document.querySelectorAll('.dropdown-trigger'), {
            constrainWidth: false,
            coverTrigger: false,
            alignment: 'right'
        });
        M.Tooltip.init(document.querySelectorAll('.tooltipped'));
        M.Modal.init(document.querySelectorAll('.modal'));
    }

    // Initialize all existing comments
    document.querySelectorAll('.comment').forEach(comment => {
        addCommentEventListeners(comment);
        initializeVoteState(comment);
        initializeReactionState(comment);
    });

    // Helper functions
    function createCommentsContainer() {
        const container = document.createElement('div');
        container.id = 'comments-container';
        
        // Find the best place to insert the container
        const commentsSection = document.querySelector('.newcomments') || 
                              document.querySelector('.comments-section') || 
                              document.querySelector('#comments');
        
        if (commentsSection) {
            const form = commentsSection.querySelector('#add-comment-form');
            if (form) {
                // Insert before the form
                form.parentElement.insertBefore(container, form);
            } else {
                // Just append to the comments section
                commentsSection.appendChild(container);
            }
        } else {
            // Fallback: insert after the form
            const form = document.getElementById('add-comment-form');
            if (form && form.parentElement) {
                form.parentElement.insertBefore(container, form.nextSibling);
            }
        }
        
        return container;
    }

    function createCommentHtml(commentData, isReply = false) {
        // Get CSRF token
        const csrfToken = getCSRFToken();
        
        // Format the time as "just now" for new comments
        const timeDisplay = 'just now';
        
        // Build the HTML matching the structure in comments.html
        return `
            <div class="comment ${isReply ? 'reply' : ''}" data-comment-id="${commentData.id}"
                ${commentData.user_vote ? `data-user-vote="${commentData.user_vote}"` : ''}
                ${commentData.user_reactions ? `data-user-reactions='${JSON.stringify(commentData.user_reactions)}'` : 'data-user-reactions="[]"'}>
                <img class="miniavatar" src="${commentData.author_avatar || '/static/icons/default-avatar.svg'}">
                <span>
                    <i title="${new Date().toISOString()}" style="float: right;">${timeDisplay}</i>
                    ${commentData.user_id ? `<a href="/u/${commentData.user_id}">${commentData.user || 'Anonymous'}</a>` : `<span>${commentData.user || 'Anonymous'}</span>`}
                    
                    <div class="comment-actions">
                        <!-- Vote buttons with improved UI -->
                        <div class="vote-container">
                            <a href="#" class="upvote-btn tooltipped" data-position="top" data-tooltip="Upvote">
                                <i>👍</i>
                            </a>
                            <span class="score">${commentData.score || 0}</span>
                            <a href="#" class="downvote-btn tooltipped" data-position="top" data-tooltip="Downvote">
                                <i>👎</i>
                            </a>
                        </div>
                        
                        <!-- Reactions button -->
                        <div class="reactions-container">
                            <a href="#" class="reaction-dropdown-trigger" data-target="reactions-${commentData.id}">
                                <i class="material-icons">add_reaction</i>
                            </a>
                            
                            <!-- Reaction dropdown -->
                            <div id="reactions-${commentData.id}" class="reaction-dropdown">
                                <a href="#" class="reaction-btn tooltipped" data-reaction-type="LIKE" data-position="top" data-tooltip="Like">👍</a>
                                <a href="#" class="reaction-btn tooltipped" data-reaction-type="LOVE" data-position="top" data-tooltip="Love">❤️</a>
                                <a href="#" class="reaction-btn tooltipped" data-reaction-type="LAUGH" data-position="top" data-tooltip="Laugh">😂</a>
                                <a href="#" class="reaction-btn tooltipped" data-reaction-type="INSIGHTFUL" data-position="top" data-tooltip="Insightful">💡</a>
                                <a href="#" class="reaction-btn tooltipped" data-reaction-type="CONFUSED" data-position="top" data-tooltip="Confused">😕</a>
                                <a href="#" class="reaction-btn tooltipped" data-reaction-type="SAD" data-position="top" data-tooltip="Sad">😢</a>
                                <a href="#" class="reaction-btn tooltipped" data-reaction-type="THANKS" data-position="top" data-tooltip="Thanks">🙏</a>
                            </div>
                            
                            <!-- Reaction counts -->
                            <div class="reaction-counts"></div>
                        </div>
                        
                        <!-- Comment menu -->
                        <a class='dropdown-trigger btn-flat' href='#' data-target='actions-${commentData.id}'>
                            <img src="/static/icons/menu.svg" alt="actions">
                        </a>
                        
                        <!-- Dropdown Structure -->
                        <ul id='actions-${commentData.id}' class='dropdown-content'>
                            ${commentData.user_id ? `<li><a href="/comments/edit/${commentData.id}/">Edit</a></li>` : ''}
                            <li><a href="/comments/report/${commentData.id}/">Report</a></li>
                        </ul>
                    </div>
                </span>

                <p>${commentData.content}</p>

                <!-- Link to single comment view -->
                <a href="/comments/${commentData.id}/">Permalink</a>

                <span></span> ${commentData.total_replies || 0} replies

                ${(commentData.total_replies || 0) > 0 ? `
                    <button class="view-replies-btn" data-comment-id="${commentData.id}">View Replies</button>
                ` : ''}

                <button class="reply-btn" data-comment-id="${commentData.id}">Reply</button>
                
                <div class="reply-form-container" data-comment-id="${commentData.id}" style="display: none;">
                    <form class="reply-form">
                        <input type="hidden" name="csrfmiddlewaretoken" value="${csrfToken}">
                        <div class="input-field">
                            <textarea name="content" class="materialize-textarea" required></textarea>
                            <label>Your reply</label>
                        </div>
                        <input type="hidden" name="parent_id" value="${commentData.id}">
                        ${commentData.to_task_id ? `<input type="hidden" name="to_task_id" value="${commentData.to_task_id}">` : ''}
                        ${commentData.to_project_id ? `<input type="hidden" name="to_project_id" value="${commentData.to_project_id}">` : ''}
                        ${commentData.to_need_id ? `<input type="hidden" name="to_need_id" value="${commentData.to_need_id}">` : ''}
                        <button type="submit" class="btn waves-effect waves-light blue">
                            <i class="material-icons left">send</i>Post Reply
                        </button>
                        <button type="button" class="btn waves-effect waves-light grey cancel-reply">
                            Cancel
                        </button>
                    </form>
                </div>
                
                <div class="replies-container" data-comment-id="${commentData.id}" style="display: none;"></div>
            </div>
        `;
    }

    async function loadReplies(commentId, container) {
        try {
            const response = await fetch(`/comments/load-replies/${commentId}/`);
            if (response.ok) {
                const data = await response.json();
                
                if (data.replies && data.replies.length > 0) {
                    container.innerHTML = data.replies.map(reply => 
                        createCommentHtml(reply, true)
                    ).join('');
                    
                    container.querySelectorAll('.comment').forEach(comment => {
                        addCommentEventListeners(comment);
                    });
                } else {
                    container.innerHTML = '<p class="grey-text">No replies yet</p>';
                }
            }
        } catch (error) {
            console.error('Error loading replies:', error);
            container.innerHTML = '<p class="red-text">Error loading replies</p>';
        }
    }

    async function handleVote(button) {
        const comment = button.closest('.comment');
        if (!comment) return;

        const commentId = comment.dataset.commentId;
        const voteType = button.classList.contains('upvote-btn') ? 'UPVOTE' : 'DOWNVOTE';
        const currentVote = comment.dataset.userVote;

        try {
            const url = currentVote === voteType ? 
                `/comments/${commentId}/remove-vote/` : 
                `/comments/${commentId}/vote/`;
            
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken(),
                },
                body: currentVote === voteType ? null : JSON.stringify({ vote_type: voteType })
            });

            if (response.ok) {
                const data = await response.json();
                comment.querySelector('.score').textContent = data.score;
                comment.dataset.userVote = currentVote === voteType ? '' : voteType;
                
                // Update UI
                comment.querySelectorAll('.upvote-btn, .downvote-btn').forEach(btn => {
                    btn.classList.remove('active');
                });
                
                if (currentVote !== voteType) {
                    button.classList.add('active');
                }
            }
        } catch (error) {
            console.error('Voting error:', error);
            showToast('Error processing vote', 'red');
        }
    }

    async function handleReaction(button) {
        const comment = button.closest('.comment');
        if (!comment) return;

        const commentId = comment.dataset.commentId;
        const reactionType = button.dataset.reactionType;

        try {
            const response = await fetch(`/comments/${commentId}/reaction/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken(),
                },
                body: JSON.stringify({ reaction_type: reactionType })
            });

            if (response.ok) {
                const data = await response.json();
                updateReactionCounts(comment, data.reaction_counts);
                
                // Update user reactions
                let userReactions = JSON.parse(comment.dataset.userReactions || '[]');
                if (data.action === 'added') {
                    if (!userReactions.includes(reactionType)) {
                        userReactions.push(reactionType);
                    }
                    button.classList.add('active');
                } else {
                    userReactions = userReactions.filter(r => r !== reactionType);
                    button.classList.remove('active');
                }
                comment.dataset.userReactions = JSON.stringify(userReactions);
            }
        } catch (error) {
            console.error('Reaction error:', error);
            showToast('Error processing reaction', 'red');
        }
    }

    function addCommentEventListeners(commentElement) {
        // Initialize Materialize components for the new comment
        if (typeof M !== 'undefined') {
            // Initialize dropdowns
            const dropdowns = commentElement.querySelectorAll('.dropdown-trigger');
            M.Dropdown.init(dropdowns, {
                constrainWidth: false,
                coverTrigger: false,
                alignment: 'right'
            });
            
            // Initialize tooltips
            const tooltips = commentElement.querySelectorAll('.tooltipped');
            M.Tooltip.init(tooltips);
            
            // Initialize textareas
            const textareas = commentElement.querySelectorAll('.materialize-textarea');
            textareas.forEach(textarea => {
                M.textareaAutoResize(textarea);
            });
        }
        
        // Initialize vote and reaction states
        initializeVoteState(commentElement);
        initializeReactionState(commentElement);
    }

    function initializeVoteState(comment) {
        const userVote = comment.dataset.userVote;
        if (userVote === 'UPVOTE') {
            comment.querySelector('.upvote-btn')?.classList.add('active');
        } else if (userVote === 'DOWNVOTE') {
            comment.querySelector('.downvote-btn')?.classList.add('active');
        }
    }

    function initializeReactionState(comment) {
        const userReactions = JSON.parse(comment.dataset.userReactions || '[]');
        userReactions.forEach(reactionType => {
            const btn = comment.querySelector(`.reaction-btn[data-reaction-type="${reactionType}"]`);
            if (btn) btn.classList.add('active');
        });
    }

    function updateReactionCounts(comment, counts) {
        const container = comment.querySelector('.reaction-counts');
        if (!container) return;
        
        container.innerHTML = Object.entries(counts)
            .filter(([_, count]) => count > 0)
            .map(([type, count]) => `
                <div class="reaction-count" data-type="${type}">
                    ${getReactionEmoji(type)} ${count}
                </div>
            `).join('');
    }

    function getReactionEmoji(type) {
        const emojiMap = {
            'LIKE': '👍', 'LOVE': '❤️', 'LAUGH': '😂', 
            'INSIGHTFUL': '💡', 'CONFUSED': '😕', 
            'SAD': '😢', 'THANKS': '🙏'
        };
        return emojiMap[type] || '👍';
    }
});