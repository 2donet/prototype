document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips and dropdowns if using Materialize CSS
    if (typeof M !== 'undefined') {
        var tooltips = document.querySelectorAll('.tooltipped');
        var dropdowns = document.querySelectorAll('.dropdown-trigger');
        M.Tooltip.init(tooltips);
        M.Dropdown.init(dropdowns);
    }
    
    // Handle vote buttons
    initializeVoteHandlers();
    
    // Handle reaction buttons
    initializeReactionHandlers();
    
    // Initialize active states based on data attributes
    initializeActiveStates();
    
    // Initialize reaction counts display - NEW FUNCTION CALL
    initializeReactionCounts();
});

/**
 * Initialize active states for votes and reactions based on data attributes
 * This will highlight buttons for votes/reactions the user has already made
 */
function initializeActiveStates() {
    // Get all comments
    document.querySelectorAll('.comment').forEach(comment => {
        const commentId = comment.dataset.commentId;
        
        // Check for user vote
        if (comment.hasAttribute('data-user-vote')) {
            const userVote = comment.getAttribute('data-user-vote');
            updateVoteButtonStyles(commentId, userVote);
        }
        
        // Check for user reactions
        if (comment.hasAttribute('data-user-reactions')) {
            const userReactions = JSON.parse(comment.getAttribute('data-user-reactions').replace(/'/g, '"'));
            
            // Highlight active reaction buttons
            userReactions.forEach(reactionType => {
                const reactionBtn = comment.querySelector(`.reaction-btn[data-reaction-type="${reactionType}"]`);
                if (reactionBtn) {
                    reactionBtn.classList.add('active');
                }
            });
        }
    });
}

/**
 * NEW FUNCTION: Initialize reaction counts on page load to ensure they're displayed
 * This ensures all reaction counts with values > 0 are displayed by default
 */
function initializeReactionCounts() {
    // Get all comment elements
    document.querySelectorAll('.comment').forEach(comment => {
        // Get the reaction counts container
        const reactionsContainer = comment.querySelector('.reaction-counts');
        if (!reactionsContainer) return;
        
        // For each reaction count container
        comment.querySelectorAll('.reaction-count-container').forEach(container => {
            const countElement = container.querySelector('.reaction-count');
            if (countElement) {
                const count = parseInt(countElement.textContent, 10);
                // Make sure containers with counts > 0 are displayed
                container.style.display = count > 0 ? 'inline-flex' : 'none';
            }
        });
    });
}

/**
 * Get CSRF token from cookies for POST requests
 * @returns {string} CSRF token
 */
function getCsrfToken() {
    const name = 'csrftoken';
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

/**
 * Show a toast notification if Materialize is available
 * @param {string} message - Message to display
 */
function showToast(message) {
    if (typeof M !== 'undefined') {
        M.toast({html: message, classes: 'rounded'});
    } else {
        console.log(message);
    }
}

/**
 * Set up event handlers for upvote/downvote buttons
 */
function initializeVoteHandlers() {
    // Upvote buttons
    document.querySelectorAll('.upvote-btn').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const commentId = this.closest('.comment').dataset.commentId;
            voteOnComment(commentId, 'UPVOTE', this);
        });
    });
    
    // Downvote buttons
    document.querySelectorAll('.downvote-btn').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const commentId = this.closest('.comment').dataset.commentId;
            voteOnComment(commentId, 'DOWNVOTE', this);
        });
    });
    
    // Remove vote buttons
    document.querySelectorAll('.remove-vote-btn').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const commentId = this.closest('.comment').dataset.commentId;
            removeVote(commentId, this);
        });
    });
}

/**
 * Set up event handlers for reaction buttons
 */
function initializeReactionHandlers() {
    document.querySelectorAll('.reaction-btn').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const commentId = this.closest('.comment').dataset.commentId;
            const reactionType = this.dataset.reactionType;
            toggleReaction(commentId, reactionType, this);
        });
    });
}

/**
 * Vote on a comment
 * @param {string} commentId - ID of the comment
 * @param {string} voteType - Either 'UPVOTE' or 'DOWNVOTE'
 * @param {HTMLElement} clickedButton - The button that was clicked
 */
async function voteOnComment(commentId, voteType, clickedButton) {
    try {
        const csrfToken = getCsrfToken();
        
        const response = await fetch(`/comments/${commentId}/vote/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
                vote_type: voteType
            })
        });
        
        if (response.ok) {
            const data = await response.json();
            
            // Update the UI
            updateCommentScore(commentId, data.score);
            updateVoteButtonStyles(commentId, voteType);
            
            // Show toast notification
            showToast(`Vote recorded!`);
        } else {
            // Handle errors
            const error = await response.json();
            showToast(`Error: ${error.error || 'Could not process vote'}`);
        }
    } catch (error) {
        console.error('Error casting vote:', error);
        showToast('An error occurred. Please try again.');
    }
}

/**
 * Remove a vote from a comment
 * @param {string} commentId - ID of the comment
 * @param {HTMLElement} clickedButton - The button that was clicked
 */
async function removeVote(commentId, clickedButton) {
    try {
        const csrfToken = getCsrfToken();
        
        const response = await fetch(`/comments/${commentId}/remove-vote/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            
            // Update the UI
            updateCommentScore(commentId, data.score);
            updateVoteButtonStyles(commentId, null);
            
            // Show toast notification
            showToast('Vote removed!');
        } else {
            // Handle errors
            const error = await response.json();
            showToast(`Error: ${error.error || 'Could not remove vote'}`);
        }
    } catch (error) {
        console.error('Error removing vote:', error);
        showToast('An error occurred. Please try again.');
    }
}

/**
 * Toggle a reaction on a comment
 * @param {string} commentId - ID of the comment
 * @param {string} reactionType - Type of reaction (e.g., 'LIKE', 'LOVE')
 * @param {HTMLElement} clickedButton - The button that was clicked
 */
async function toggleReaction(commentId, reactionType, clickedButton) {
    try {
        const csrfToken = getCsrfToken();
        
        // Log what we're sending
        console.log(`Toggling reaction for comment ${commentId}, reaction type: ${reactionType}`);
        
        const response = await fetch(`/comments/${commentId}/reaction/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
                reaction_type: reactionType
            })
        });
        
        // Log the raw response for debugging
        console.log(`Response status: ${response.status}`);
        
        if (response.ok) {
            const data = await response.json();
            console.log('Response data:', data);
            
            // Update the UI based on whether reaction was added or removed
            updateReactionUI(commentId, reactionType, data.action, data.reaction_counts);
            
            // Show toast notification
            const actionText = data.action === 'added' ? 'added' : 'removed';
            showToast(`Reaction ${actionText}!`);
        } else {
            // Handle errors
            try {
                const error = await response.json();
                console.error('Error details:', error);
                showToast(`Error: ${error.error || 'Could not process reaction'}`);
            } catch (e) {
                console.error('Could not parse error response:', e);
                showToast('Server error. Please try again.');
            }
        }
    } catch (error) {
        console.error('Error toggling reaction:', error);
        showToast('An error occurred. Please try again.');
    }
}

/**
 * Update the comment score in the UI
 * @param {string} commentId - ID of the comment
 * @param {number} newScore - The new score to display
 */
function updateCommentScore(commentId, newScore) {
    const scoreElement = document.querySelector(`.comment[data-comment-id="${commentId}"] .score`);
    if (scoreElement) {
        scoreElement.textContent = newScore;
    }
}

/**
 * Update vote button styles based on current vote
 * @param {string} commentId - ID of the comment
 * @param {string|null} currentVote - Current vote type or null if no vote
 */
function updateVoteButtonStyles(commentId, currentVote) {
    const commentElement = document.querySelector(`.comment[data-comment-id="${commentId}"]`);
    if (!commentElement) return;
    
    const upvoteBtn = commentElement.querySelector('.upvote-btn');
    const downvoteBtn = commentElement.querySelector('.downvote-btn');
    
    // Reset all button styles
    if (upvoteBtn) upvoteBtn.classList.remove('active');
    if (downvoteBtn) downvoteBtn.classList.remove('active');
    
    // Apply active style to the current vote button
    if (currentVote === 'UPVOTE' && upvoteBtn) {
        upvoteBtn.classList.add('active');
    } else if (currentVote === 'DOWNVOTE' && downvoteBtn) {
        downvoteBtn.classList.add('active');
    }
}

/**
 * Update the reaction UI after toggling a reaction
 * @param {string} commentId - ID of the comment
 * @param {string} reactionType - Type of reaction
 * @param {string} action - Either 'added' or 'removed'
 * @param {Object} reactionCounts - Object with reaction counts
 */
function updateReactionUI(commentId, reactionType, action, reactionCounts) {
    console.log('Updating reaction UI:', {commentId, reactionType, action, reactionCounts});
    
    const commentElement = document.querySelector(`.comment[data-comment-id="${commentId}"]`);
    if (!commentElement) {
        console.error(`Comment element with ID ${commentId} not found`);
        return;
    }
    
    // Update reaction button style
    const reactionBtn = commentElement.querySelector(`.reaction-btn[data-reaction-type="${reactionType}"]`);
    if (reactionBtn) {
        if (action === 'added') {
            reactionBtn.classList.add('active');
        } else {
            reactionBtn.classList.remove('active');
        }
    } else {
        console.warn(`Reaction button for type ${reactionType} not found`);
    }
    
    // If we don't have reaction counts, exit early
    if (!reactionCounts || Object.keys(reactionCounts).length === 0) {
        console.log('No reaction counts to update');
        return;
    }
    
    // Update reaction counts
    for (const [type, count] of Object.entries(reactionCounts)) {
        // Find the count element
        const countElement = commentElement.querySelector(`.reaction-count[data-reaction-type="${type}"]`);
        
        if (countElement) {
            countElement.textContent = count;
            
            // Show/hide based on count - IMPORTANT: Always display counts greater than 0
            const countContainer = countElement.closest('.reaction-count-container');
            if (countContainer) {
                countContainer.style.display = count > 0 ? 'inline-flex' : 'none';
            }
        } else {
            // If the element doesn't exist and count > 0, create it
            const reactionsContainer = commentElement.querySelector('.reaction-counts');
            if (reactionsContainer && count > 0) {
                const newContainer = document.createElement('div');
                newContainer.className = 'reaction-count-container';
                newContainer.dataset.reactionType = type;
                newContainer.style.display = 'inline-flex';
                
                // Get emoji for this reaction type
                const emoji = getReactionEmoji(type);
                
                newContainer.innerHTML = `
                    <span class="reaction-emoji">${emoji}</span>
                    <span class="reaction-count" data-reaction-type="${type}">${count}</span>
                `;
                
                reactionsContainer.appendChild(newContainer);
            }
        }
    }
    
    // Hide reaction counters with zero count that aren't in reactionCounts
    commentElement.querySelectorAll('.reaction-count-container').forEach(container => {
        const countElement = container.querySelector('.reaction-count');
        if (countElement) {
            const type = countElement.dataset.reactionType;
            if (!(type in reactionCounts) || reactionCounts[type] === 0) {
                container.style.display = 'none';
            }
        }
    });
}

/**
 * Displays reactions summary as a tooltip
 * @param {string} commentId - ID of the comment
 */
async function loadReactionsSummary(commentId) {
    try {
        const response = await fetch(`/comments/${commentId}/reactions/`);
        
        if (response.ok) {
            const data = await response.json();
            
            if (data.length > 0) {
                // Format the reactions summary
                let summaryHTML = '<div class="reactions-summary">';
                data.forEach(reaction => {
                    const emoji = getReactionEmoji(reaction.reaction_type);
                    summaryHTML += `<div class="reaction-summary-item">
                        <span class="reaction-emoji">${emoji}</span>
                        <span class="reaction-count">${reaction.count}</span>
                    </div>`;
                });
                summaryHTML += '</div>';
                
                // Update the tooltip content
                const reactionSummary = document.querySelector(`.comment[data-comment-id="${commentId}"] .reactions-summary-container`);
                if (reactionSummary) {
                    reactionSummary.innerHTML = summaryHTML;
                    reactionSummary.style.display = 'block';
                }
            }
        }
    } catch (error) {
        console.error('Error loading reactions summary:', error);
    }
}

/**
 * Get the emoji representation for a reaction type
 * @param {string} reactionType - Type of reaction
 * @returns {string} Emoji for the reaction
 */
function getReactionEmoji(reactionType) {
    const emojiMap = {
        'LIKE': '👍',
        'LOVE': '❤️',
        'LAUGH': '😂',
        'INSIGHTFUL': '💡',
        'CONFUSED': '😕',
        'SAD': '😢',
        'THANKS': '🙏'
    };
    
    return emojiMap[reactionType] || '👍';
}