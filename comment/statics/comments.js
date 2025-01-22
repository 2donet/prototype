document.getElementById('add-comment-form').addEventListener('submit', async (e) => {
    e.preventDefault(); // Prevent page reload on form submission
    const formData = new FormData(e.target);
    
    // Send the form data to the server
    const response = await fetch('/add_comment/', {
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
                <img class="miniavatar" src="${newComment.author_avatar}">
                <span>
                    <i title="${newComment.pub_date}" style="float: right;">just now</i>
                </span>
                <h4>
                    <a href="/u/${newComment.author_id}">${newComment.author_name}</a>
                </h4>
                <i>${newComment.author_bio}</i>
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