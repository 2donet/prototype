document.getElementById('add-comment-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);

    const response = await fetch('/add_comment/', {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
        },
    });

    if (response.ok) {
        const newComment = await response.json();
        // Dynamically add the new comment to the comments section
    }
});

document.querySelectorAll('.reply-btn').forEach((btn) => {
    btn.addEventListener('click', async () => {
        const commentId = btn.getAttribute('data-comment-id');

        const response = await fetch(`/load_replies/${commentId}/`);
        if (response.ok) {
            const replies = await response.json();
            // Render replies dynamically
        }
    });
});