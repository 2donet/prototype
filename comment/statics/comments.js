document.addEventListener('DOMContentLoaded', function() {
    // Existing comment form submission
    const addCommentForm = document.getElementById('add-comment-form');
    if (addCommentForm) {
        addCommentForm.addEventListener('submit', async (e) => {
            e.preventDefault(); // Prevent page reload on form submission
            const formData = new FormData(e.target);
            
            // Send the form data to the server
            const response = await fetch('/comments/add/', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
                },
            });

            if (response.ok) {
                // Parse the response (new comment data)
                const newComment = await response.json();

                // Generate HTML for the new comment (match the structure in comment.html)
                const newCommentHtml = `
                    <div class="comment" data-comment-id="${newComment.id}">
                        <img class="miniavatar" src="${newComment.author_avatar || '/static/icons/default-avatar.svg'}">
                        <span>
                            <i title="${newComment.pub_date}" style="float: right;">just now</i>
                        </span>
                        <h4>
                            <a href="/u/${newComment.user_id}">${newComment.user || 'Anonymous'}</a>
                        </h4>
                        <p>${newComment.content}</p>
                        <br>
                        <button class="reply-btn" data-comment-id="${newComment.id}">Reply</button>
                        <span>0 replies</span>
                        <br>
                        <button class="view-replies-btn" data-comment-id="${newComment.id}">View Replies</button>
                        <br>
                        <div class="replies-container" data-comment-id="${newComment.id}" style="display: none;"></div>
                        <br>
                    </div>
                `;

                // Append the new comment to the comments container
                document.getElementById('comments-container').insertAdjacentHTML('beforeend', newCommentHtml);

                // Clear the form after successful submission
                e.target.reset();
            }
        });
    }

    // Handle reply button clicks
    document.querySelectorAll('.reply-btn').forEach(button => {
        button.addEventListener('click', function() {
            const commentId = this.getAttribute('data-comment-id');
            const replyForm = this.closest('.comment').querySelector('.reply-form-container');
            
            // Toggle form visibility
            if (replyForm.style.display === 'none' || !replyForm.style.display) {
                replyForm.style.display = 'block';
            } else {
                replyForm.style.display = 'none';
            }
        });
    });
    
    // Handle cancel reply button clicks
    document.querySelectorAll('.cancel-reply').forEach(button => {
        button.addEventListener('click', function() {
            const replyForm = this.closest('.reply-form-container');
            replyForm.style.display = 'none';
        });
    });
    
    // Handle reply form submissions
    document.querySelectorAll('.reply-form, #add-reply-form').forEach(form => {
        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const parentId = this.getAttribute('data-parent-id');
            
            try {
                const response = await fetch('/comments/add/', {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
                    },
                });
                
                if (response.ok) {
                    const data = await response.json();
                    
                    if (data.status === 'flagged') {
                        // Display message for flagged comments
                        alert(data.message);
                        this.reset();
                        return;
                    }
                    
                    // Create HTML for the new reply
                    const replyHtml = `
                        <div class="comment reply" data-comment-id="${data.id}">
                            <div class="comment-header">
                                <div class="comment-meta">
                                    <a href="/u/${data.user_id}">${data.user || 'Anonymous'}</a>
                                    <span class="time">just now</span>
                                </div>
                                <div class="comment-actions">
                                    <a href="#" class="upvote-btn" data-position="top" data-tooltip="Upvote">👍</a>
                                    <span class="score">0</span>
                                    <a href="#" class="downvote-btn" data-position="top" data-tooltip="Downvote">👎</a>
                                </div>
                            </div>
                            <div class="comment-content">
                                <p>${data.content}</p>
                            </div>
                            <div class="comment-footer">
                                <button class="reply-btn" data-comment-id="${data.id}">Reply</button>
                            </div>
                        </div>
                    `;
                    
                    // Add to the replies container and hide the form
                    const repliesContainer = document.querySelector(`.replies-container[data-comment-id="${parentId}"]`);
                    if (repliesContainer) {
                        repliesContainer.style.display = 'block';
                        repliesContainer.insertAdjacentHTML('beforeend', replyHtml);
                    }
                    
                    // Clear and hide form
                    this.reset();
                    const formContainer = this.closest('.reply-form-container');
                    if (formContainer) {
                        formContainer.style.display = 'none';
                    }
                    
                    // Update reply count
                    const replyCountElement = document.querySelector(`.comment[data-comment-id="${parentId}"] .reply-count`);
                    if (replyCountElement) {
                        const currentCount = parseInt(replyCountElement.textContent.split(' ')[0], 10);
                        replyCountElement.textContent = `${currentCount + 1} replies`;
                    }
                } else {
                    const error = await response.json();
                    alert('Error: ' + error.error);
                }
            } catch (error) {
                console.error('Error submitting reply:', error);
                alert('An error occurred. Please try again.');
            }
        });
    });
    
    // Handle View Replies button
    document.querySelectorAll('.view-replies-btn').forEach(button => {
        button.addEventListener('click', async function() {
            const commentId = this.getAttribute('data-comment-id');
            const repliesContainer = document.querySelector(`.replies-container[data-comment-id="${commentId}"]`);
            
            if (repliesContainer.style.display === 'none') {
                // Show if already loaded
                repliesContainer.style.display = 'block';
                this.textContent = 'Hide Replies';
            } else if (repliesContainer.style.display === 'block') {
                // Hide if showing
                repliesContainer.style.display = 'none';
                this.textContent = 'View Replies';
            } else {
                // Load from server if not loaded yet
                try {
                    const response = await fetch(`/comments/load-replies/${commentId}/`);
                    if (response.ok) {
                        const data = await response.json();
                        
                        // Only fetch if we have replies to show
                        if (data.replies && data.replies.length > 0) {
                            let repliesHtml = '';
                            
                            data.replies.forEach(reply => {
                                repliesHtml += `
                                    <div class="comment reply" data-comment-id="${reply.id}">
                                        <div class="comment-header">
                                            <div class="comment-meta">
                                                <a href="/u/${reply.user_id}">${reply.user || 'Anonymous'}</a>
                                                <span class="time">recently</span>
                                            </div>
                                            <div class="comment-actions">
                                                <a href="#" class="upvote-btn">👍</a>
                                                <span class="score">${reply.score}</span>
                                                <a href="#" class="downvote-btn">👎</a>
                                            </div>
                                        </div>
                                        <div class="comment-content">
                                            <p>${reply.content}</p>
                                        </div>
                                        <div class="comment-footer">
                                            <button class="reply-btn" data-comment-id="${reply.id}">Reply</button>
                                            ${reply.total_replies > 0 ? 
                                                `<a href="/comments/${reply.id}/">View ${reply.total_replies} nested replies</a>` : ''}
                                        </div>
                                    </div>
                                `;
                            });
                            
                            repliesContainer.innerHTML = repliesHtml;
                            repliesContainer.style.display = 'block';
                            this.textContent = 'Hide Replies';
                            
                            // Add event listeners to newly created reply buttons
                            repliesContainer.querySelectorAll('.reply-btn').forEach(btn => {
                                btn.addEventListener('click', function() {
                                    const replyId = this.getAttribute('data-comment-id');
                                    // Handle nested reply (redirect to single comment view)
                                    window.location.href = `/comments/${replyId}/`;
                                });
                            });
                        } else {
                            repliesContainer.innerHTML = '<p class="no-replies">No replies yet.</p>';
                            repliesContainer.style.display = 'block';
                            this.textContent = 'Hide Replies';
                        }
                    }
                } catch (error) {
                    console.error('Error loading replies:', error);
                }
            }
        });
    });

    // Vote functionality
    document.querySelectorAll('.upvote-btn, .downvote-btn').forEach(button => {
        button.addEventListener('click', async (e) => {
            e.preventDefault();
            
            // Get the comment element and ID
            const commentElement = e.target.closest('.comment');
            if (!commentElement) return;
            
            const commentId = commentElement.dataset.commentId;
            const voteType = e.target.classList.contains('upvote-btn') ? 'UPVOTE' : 'DOWNVOTE';
            
            // Check if already voted
            const userVote = commentElement.dataset.userVote;
            
            try {
                // If already voted the same way, remove vote
                if (userVote === voteType) {
                    const response = await fetch(`/comments/${commentId}/remove-vote/`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
                        }
                    });
                    
                    if (response.ok) {
                        const data = await response.json();
                        commentElement.querySelector('.score').textContent = data.score;
                        commentElement.dataset.userVote = '';
                        e.target.classList.remove('active');
                    }
                } else {
                    // Cast or change vote
                    const response = await fetch(`/comments/${commentId}/vote/`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
                        },
                        body: JSON.stringify({ vote_type: voteType }),
                    });
                    
                    if (response.ok) {
                        const data = await response.json();
                        commentElement.querySelector('.score').textContent = data.score;
                        commentElement.dataset.userVote = voteType;
                        
                        // Update active states
                        commentElement.querySelectorAll('.upvote-btn, .downvote-btn').forEach(btn => {
                            btn.classList.remove('active');
                        });
                        e.target.classList.add('active');
                    }
                }
            } catch (error) {
                console.error('Error voting:', error);
            }
        });
    });
    
    // Reaction functionality
    document.querySelectorAll('.reaction-btn').forEach(button => {
        button.addEventListener('click', async (e) => {
            e.preventDefault();
            
            // Get the comment element and ID
            const commentElement = e.target.closest('.comment');
            if (!commentElement) return;
            
            const commentId = commentElement.dataset.commentId;
            const reactionType = e.target.dataset.reactionType;
            
            try {
                const response = await fetch(`/comments/${commentId}/reaction/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
                    },
                    body: JSON.stringify({ reaction_type: reactionType }),
                });
                
                if (response.ok) {
                    const data = await response.json();
                    
                    // Update reaction counts
                    updateReactionCounts(commentElement, data.reaction_counts);
                    
                    // Toggle user reaction status
                    let userReactions = [];
                    if (commentElement.dataset.userReactions) {
                        try {
                            userReactions = JSON.parse(commentElement.dataset.userReactions);
                        } catch (e) {
                            userReactions = commentElement.dataset.userReactions.split(',');
                        }
                    }
                    
                    if (data.action === 'added') {
                        if (!userReactions.includes(reactionType)) {
                            userReactions.push(reactionType);
                        }
                        e.target.classList.add('active');
                    } else {
                        userReactions = userReactions.filter(r => r !== reactionType);
                        e.target.classList.remove('active');
                    }
                    
                    commentElement.dataset.userReactions = JSON.stringify(userReactions);
                }
            } catch (error) {
                console.error('Error toggling reaction:', error);
            }
        });
    });
    
    // Initialize Materialize components if available
    if (typeof M !== 'undefined') {
        // Initialize dropdowns
        var dropdowns = document.querySelectorAll('.dropdown-trigger');
        M.Dropdown.init(dropdowns);
        
        // Initialize tooltips
        var tooltips = document.querySelectorAll('.tooltipped');
        M.Tooltip.init(tooltips);
        
        // Initialize modals
        var modals = document.querySelectorAll('.modal');
        M.Modal.init(modals);
    }
    
    // Set initial active state for votes and reactions
    document.querySelectorAll('.comment').forEach(comment => {
        // Set vote active state
        const userVote = comment.dataset.userVote;
        if (userVote) {
            if (userVote === 'UPVOTE') {
                comment.querySelector('.upvote-btn')?.classList.add('active');
            } else if (userVote === 'DOWNVOTE') {
                comment.querySelector('.downvote-btn')?.classList.add('active');
            }
        }
        
        // Set reaction active states
        const userReactions = comment.dataset.userReactions;
        if (userReactions) {
            let reactions = [];
            try {
                reactions = JSON.parse(userReactions);
            } catch (e) {
                reactions = userReactions.split(',');
            }
            
            reactions.forEach(reactionType => {
                const reactionBtn = comment.querySelector(`.reaction-btn[data-reaction-type="${reactionType}"]`);
                if (reactionBtn) {
                    reactionBtn.classList.add('active');
                }
            });
        }
    });
});

// Helper function to update reaction counts
function updateReactionCounts(commentElement, reactionCounts) {
    const countsContainer = commentElement.querySelector('.reaction-counts');
    if (!countsContainer) return;
    
    countsContainer.innerHTML = '';
    
    for (const [type, count] of Object.entries(reactionCounts)) {
        if (count > 0) {
            const emoji = getReactionEmoji(type);
            countsContainer.innerHTML += `
                <div class="reaction-count-container" data-reaction-type="${type}">
                    <span class="reaction-emoji">${emoji}</span>
                    <span class="reaction-count">${count}</span>
                </div>
            `;
        }
    }
}

// Helper function to get emoji for a reaction type
function getReactionEmoji(type) {
    const emojiMap = {
        'LIKE': '👍',
        'LOVE': '❤️',
        'LAUGH': '😂',
        'INSIGHTFUL': '💡',
        'CONFUSED': '😕',
        'SAD': '😢',
        'THANKS': '🙏'
    };
    return emojiMap[type] || '👍';
}