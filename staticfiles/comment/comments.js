console.log('Comments script loaded!aaa');
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
    const replyButton = e.target.closest('.reply-btn');
    if (replyButton) {
        e.preventDefault();

        const commentElement = replyButton.closest('.comment');
        const replyFormContainer = commentElement.querySelector('.reply-form-container');

        if (replyFormContainer) {
            replyFormContainer.style.display = 'block';  // Always show it
            const textarea = replyFormContainer.querySelector('textarea');
            if (textarea) textarea.focus();
        }
    }
});
// Cancel reply form
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('cancel-reply')) {
        e.preventDefault();
        const replyFormContainer = e.target.closest('.reply-form-container');
        if (replyFormContainer) {
            replyFormContainer.style.display = 'none';
            
            // Clear the form
            const form = replyFormContainer.querySelector('form');
            if (form) {
                form.reset();
                
                // Clear textarea for Materialize
                const textarea = form.querySelector('textarea');
                if (textarea) {
                    textarea.value = '';
                    if (typeof M !== 'undefined') {
                        M.textareaAutoResize(textarea);
                        M.updateTextFields();
                    }
                }
            }
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
    
    // Get the problem ID from the current page's form
    const problemIdInput = document.querySelector('input[name="to_problem_id"]');
    const problemId = problemIdInput ? problemIdInput.value : null;
    
    // Build the HTML matching the structure in comments.html
    return `
        <div class="comment ${isReply ? 'reply' : ''}" data-comment-id="${commentData.id}"
            ${commentData.user_vote ? `data-user-vote="${commentData.user_vote}"` : ''}
            <img class="miniavatar" src="${commentData.author_avatar || '/static/icons/default-avatar.svg'}">
            <span>
                <i title="${new Date().toISOString()}" style="float: right;">${timeDisplay}</i>
                ${commentData.user_id ? `<a href="/u/${commentData.user_id}">${commentData.user || 'Anonymous'}</a>` : `<span>${commentData.user || 'Anonymous'}</span>`}
                
                <div class="comment-actions">
                    <div class="vote-container">
                        <a href="#" class="upvote-btn tooltipped" data-position="top" data-tooltip="Upvote">
                            <i>👍</i>
                        </a>
                        <span class="score">${commentData.score || 0}</span>
                        <a href="#" class="downvote-btn tooltipped" data-position="top" data-tooltip="Downvote">
                            <i>👎</i>
                        </a>
                    </div>
                    
                    <a class='dropdown-trigger btn-flat' href='#' data-target='actions-${commentData.id}'>
                        <img src="/static/icons/menu.svg" alt="actions">
                    </a>
                    
                    <ul id='actions-${commentData.id}' class='dropdown-content'>
                        ${commentData.user_id ? `<li><a href="/comments/edit/${commentData.id}/">Edit</a></li>` : ''}
                        <li><a href="/comments/report/${commentData.id}/">Report</a></li>
                    </ul>
                </div>
            </span>

            <p>${commentData.content}</p>

            <a href="/comments/${commentData.id}/">Permalink</a>

            <span></span> ${commentData.total_replies || 0} replies

            ${(commentData.total_replies || 0) > 0 ? `
                <button class="view-replies-btn" data-comment-id="${commentData.id}">View Replies</button>
            ` : ''}

            <button class="reply-btn" data-comment-id="${commentData.id}" data-controls="reply-form-${commentData.id}">Reply</button>
            
            <div class="reply-form-container" id="reply-form-${commentData.id}" data-comment-id="${commentData.id}" style="display: none;">
                <form class="reply-form">
                    <input type="hidden" name="csrfmiddlewaretoken" value="${csrfToken}">
                    <div class="input-field">
                        <textarea name="content" class="materialize-textarea" required></textarea>
                        <label>Your reply</label>
                    </div>
                    <input type="hidden" name="parent_id" value="${commentData.id}">
                    <input type="hidden" name="to_problem_id" value="${commentData.to_problem_id}">
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
        
        // Initialize vote state
        initializeVoteState(commentElement);
    }

    function initializeVoteState(comment) {
        const userVote = comment.dataset.userVote;
        if (userVote === 'UPVOTE') {
            comment.querySelector('.upvote-btn')?.classList.add('active');
        } else if (userVote === 'DOWNVOTE') {
            comment.querySelector('.downvote-btn')?.classList.add('active');
        }
    }

});