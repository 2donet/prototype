document.addEventListener("DOMContentLoaded", function () {
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

    // Handle top-level comment submission
    const commentForm = document.getElementById("add-comment-form");
    commentForm.addEventListener("submit", async function (e) {
        e.preventDefault();

        const formData = new FormData(commentForm);
        const response = await fetch("/comments/add/", {
            method: "POST",
            body: formData,
            headers: {
                "X-CSRFToken": csrfToken,
            },
        });

        if (response.ok) {
            const newComment = await response.json();
            const commentsContainer = document.getElementById("comments");
            commentsContainer.insertAdjacentHTML(
                "beforeend",
                `
                <div class="comment" data-comment-id="${newComment.id}">
                    <strong>${newComment.user}</strong>: ${newComment.content}
                    <button class="reply-btn" data-comment-id="${newComment.id}">Reply</button>
                    <button class="view-replies-btn" data-comment-id="${newComment.id}">View Replies</button>
                    <span>${newComment.total_replies} replies</span>
                    <div class="replies-container" data-comment-id="${newComment.id}" style="display: none;"></div>
                </div>
                `
            );
            commentForm.reset();
        } else {
            const error = await response.json();
            console.error("Error:", error.error || "Failed to add comment.");
        }
    });

    // Delegate click events for reply buttons, view/hide replies, and reply submission
    document.addEventListener("click", async function (e) {
        // Show reply form
        if (e.target.classList.contains("reply-btn")) {
            const commentId = e.target.getAttribute("data-comment-id");
            const container = document.querySelector(
                `.replies-container[data-comment-id="${commentId}"]`
            );

            // Avoid adding duplicate reply forms
            if (!container.querySelector("textarea")) {
                container.insertAdjacentHTML(
                    "beforeend",
                    `
                    <textarea placeholder="Write your reply..."></textarea>
                    <button class="submit-reply-btn" data-comment-id="${commentId}">Submit</button>
                    `
                );
                container.style.display = "block"; // Ensure the container is visible
            }
        }

        // Handle submitting a reply
        if (e.target.classList.contains("submit-reply-btn")) {
            const commentId = e.target.getAttribute("data-comment-id");
            const container = document.querySelector(
                `.replies-container[data-comment-id="${commentId}"]`
            );
            const textarea = container.querySelector("textarea");
            const content = textarea.value.trim();

            if (!content) {
                alert("Reply cannot be empty!");
                return;
            }

            const response = await fetch("/comments/add/", {
                method: "POST",
                headers: {
                    "X-CSRFToken": csrfToken,
                },
                body: new URLSearchParams({ parent_id: commentId, content: content }),
            });

            if (response.ok) {
                const newReply = await response.json();
                container.insertAdjacentHTML(
                    "beforeend",
                    `
                    <div class="comment" data-comment-id="${newReply.id}">
                        <strong>${newReply.user}</strong>: ${newReply.content}
                        <button class="reply-btn" data-comment-id="${newReply.id}">Reply</button>
                        <div class="replies-container" data-comment-id="${newReply.id}" style="display: none;"></div>
                    </div>
                    `
                );

                // Update total replies count dynamically
                const replyCountSpan = document.querySelector(
                    `.comment[data-comment-id="${commentId}"] span`
                );
                if (replyCountSpan) {
                    const totalReplies = parseInt(replyCountSpan.textContent) || 0;
                    replyCountSpan.textContent = `${totalReplies + 1} replies`;
                }

                textarea.remove(); // Remove the reply textarea after submission
            } else {
                const error = await response.json();
                console.error("Error:", error.error || "Failed to add reply.");
            }
        }

        // Handle "View Replies" button click
        if (e.target.classList.contains("view-replies-btn")) {
            const commentId = e.target.getAttribute("data-comment-id");
            const container = document.querySelector(
                `.replies-container[data-comment-id="${commentId}"]`
            );

            if (container.style.display === "none" || container.style.display === "") {
                // Show replies
                container.style.display = "block";
                e.target.textContent = "Hide Replies";

                // Load replies dynamically if not already loaded
                if (container.innerHTML === "") {
                    const response = await fetch(`/comments/load-replies/${commentId}/`);
                    if (response.ok) {
                        const data = await response.json();
                        data.replies.forEach((reply) => {
                            container.insertAdjacentHTML(
                                "beforeend",
                                `
                                <div class="comment" data-comment-id="${reply.id}">
                                    <strong>${reply.user}</strong>: ${reply.content}
                                    <button class="reply-btn" data-comment-id="${reply.id}">Reply</button>
                                    <div class="replies-container" data-comment-id="${reply.id}" style="display: none;"></div>
                                </div>
                                `
                            );
                        });
                    } else {
                        console.error("Failed to load replies.");
                    }
                }
            } else {
                // Hide replies
                container.style.display = "none";
                e.target.textContent = "View Replies";
            }
        }
    });
});