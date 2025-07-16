document.addEventListener('DOMContentLoaded', function() {
    // Add this helper function:
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

            if (data.status === 'success') {
                // Create and append new comment
                const commentHtml = createCommentHtml(data.comment);
                let commentsContainer = document.getElementById('comments-container');

                if (!commentsContainer) {
                    commentsContainer = createCommentsContainer();
                }

                commentsContainer.insertAdjacentHTML('beforeend', commentHtml);
                addCommentEventListeners(commentsContainer.lastElementChild);

                // Reset form
                e.target.reset();

                // Manually clear and update the textarea (Materialize-specific)
                const textarea = e.target.querySelector('textarea[name="content"]');
                if (textarea) {
                    textarea.value = '';
                    if (typeof M !== 'undefined') {
                        M.textareaAutoResize(textarea);
                        M.updateTextFields();
                    }
                }

                showToast('Comment posted successfully!', 'green');

                // Scroll to the new comment
                commentsContainer.lastElementChild.scrollIntoView({ behavior: 'smooth' });
            }

        } catch (error) {
            console.error('Comment submission error:', error);
            showToast(error.message, 'red');
        } finally {
            enableButton(submitButton);
        }
    });
}


    // Reply form handling


// Submit handler for reply forms
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

            if (data.status === 'success') {
                const replyHtml = createCommentHtml(data.comment, true);
                const parentId = data.comment.parent_id;
                const repliesContainer = document.querySelector(`.replies-container[data-comment-id="${parentId}"]`);

                if (repliesContainer) {
                    repliesContainer.insertAdjacentHTML('beforeend', replyHtml);
                    repliesContainer.style.display = 'block';
                    addCommentEventListeners(repliesContainer.lastElementChild);

                    const replyCountElement = document.querySelector(`.comment[data-comment-id="${parentId}"] .reply-count`);
                    if (replyCountElement) {
                        const currentCount = parseInt(replyCountElement.textContent) || 0;
                        replyCountElement.textContent = currentCount + 1;
                    }
                }

                e.target.reset();
                e.target.style.display = 'none';

                const textarea = e.target.querySelector('textarea');
                if (textarea) {
                    textarea.value = '';
                    if (typeof M !== 'undefined') {
                        M.textareaAutoResize(textarea);
                        M.updateTextFields();
                    }
                }

                showToast('Reply posted successfully!', 'green');
            }

        } catch (error) {
            console.error('Reply submission error:', error);
            showToast(error.message, 'red');
        } finally {
            enableButton(submitButton, 'Post Reply');
        }
    }
});

// Toggle reply form (improved for nested icons inside buttons)
document.addEventListener('click', (e) => {
    // Open reply form
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
            const isHidden = repliesContainer.style.display === 'none' || !repliesContainer.style.display;

            if (isHidden) {
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
    M.Dropdown.init(document.querySelectorAll('.dropdown-trigger'));
    M.Tooltip.init(document.querySelectorAll('.tooltipped'));
    M.Modal.init(document.querySelectorAll('.modal'));
}

// Initialize all existing comments
document.querySelectorAll('.comment').forEach(comment => {
    addCommentEventListeners(comment);
    initializeVoteState(comment);
    initializeReactionState(comment);
});

// Helper to create comments container if missing
function createCommentsContainer() {
    const container = document.createElement('div');
    container.id = 'comments-container';
    const commentsSection = document.querySelector('.comments-section') || document.body;
    const form = commentsSection.querySelector('form');

    if (form) {
        commentsSection.insertBefore(container, form);
    } else {
        commentsSection.appendChild(container);
    }

    return container;
}
    function createCommentHtml(commentData, isReply = false) {
    return `
        <div class="comment ${isReply ? 'reply' : ''}" data-comment-id="${commentData.id}"
             data-user-vote="${commentData.user_vote || ''}"
             data-user-reactions='${JSON.stringify(commentData.user_reactions || [])}'>
            <img class="miniavatar" src="${commentData.author_avatar || '/static/icons/default-avatar.svg'}">
            <div class="comment-content">
                <div class="comment-header">
                    <a href="/u/${commentData.user_id}">${commentData.user || 'Anonymous'}</a>
                    <span class="comment-time">just now</span>
                </div>
                <p>${commentData.content}</p>
                <div class="comment-actions">
                    <div class="vote-container">
                        <a href="#" class="upvote-btn tooltipped" data-position="top" data-tooltip="Upvote">
                            <i>👍</i>
                        </a>
                        <span class="score">${commentData.score}</span>
                        <a href="#" class="downvote-btn tooltipped" data-position="top" data-tooltip="Downvote">
                            <i>👎</i>
                        </a>
                    </div>
                    <button class="btn-flat reply-btn" data-comment-id="${commentData.id}">
                        <i class="material-icons left">reply</i>Reply
                    </button>
                    <span class="reply-count">${commentData.total_replies || 0} replies</span>
                    ${commentData.total_replies ? `
                        <button class="btn-flat view-replies-btn" data-comment-id="${commentData.id}">
                            View Replies
                        </button>
                    ` : ''}
                </div>
                <div class="replies-container" data-comment-id="${commentData.id}" style="display: none;"></div>
                <div class="reply-form-container" data-comment-id="${commentData.id}" style="display: none;">
                    <form class="reply-form">
                        <input type="hidden" name="csrfmiddlewaretoken" value="${getCSRFToken()}">
                        <div class="input-field">
                            <textarea name="content" class="materialize-textarea" required></textarea>
                            <label>Your reply</label>
                        </div>
                        <input type="hidden" name="parent_id" value="${commentData.id}">
                        <input type="hidden" name="to_task_id" value="${commentData.to_task_id || ''}">
                        <input type="hidden" name="to_project_id" value="${commentData.to_project_id || ''}">
                        <input type="hidden" name="to_need_id" value="${commentData.to_need_id || ''}">
                        <button type="submit" class="btn waves-effect waves-light blue">
                            <i class="material-icons left">send</i>Post Reply
                        </button>
                        <button type="button" class="btn waves-effect waves-light grey cancel-reply">
                            Cancel
                        </button>
                    </form>
                </div>
            </div>
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
    // Remove any existing reply button listeners by cloning buttons
    commentElement.querySelectorAll('.reply-btn').forEach(btn => {
        const newBtn = btn.cloneNode(true);
        btn.replaceWith(newBtn);
        // Note: The original listener for 'click' on 'reply-btn' is already handled by a delegated event listener.
        // No need to re-add a specific listener here unless there's a reason for a direct handler.
        // For now, removing the direct re-addition to avoid potential duplicate handlers if the delegated event is sufficient.
    });

    // Add upvote/downvote listeners
    commentElement.querySelectorAll('.upvote-btn, .downvote-btn').forEach(btn => {
        // These are already handled by the delegated event listener for 'click' on 'upvote-btn'/'downvote-btn'.
        // No need to add specific listeners here.
    });

    // Add reaction listeners
    commentElement.querySelectorAll('.reaction-btn').forEach(btn => {
        // These are already handled by the delegated event listener for 'click' on 'reaction-btn'.
        // No need to add specific listeners here.
    });

    // Initialize Materialize tooltips and textareas
    if (typeof M !== 'undefined') {
        M.Tooltip.init(commentElement.querySelectorAll('.tooltipped'));

        commentElement.querySelectorAll('.materialize-textarea').forEach(textarea => {
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