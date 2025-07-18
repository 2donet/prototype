document.addEventListener("DOMContentLoaded", function () {
    // Handle create project modal activation
    const createButton = document.querySelector("#create-project-button");
    const modal = document.querySelector("#create-project-modal");

    if (createButton && modal) {
        createButton.addEventListener("click", function () {
            modal.classList.add("is-active");
        });
    }

    // Initialize skills autocomplete chips if element exists
    fetch('/api/skills/')
        .then(response => response.json())
        .then(data => {
            let skillData = {};
            data.forEach(skill => {
                skillData[skill.name] = null; // Materialize format
            });

            const chipsElement = document.querySelector('.chips-autocomplete');
            if (chipsElement) {
                // Initialize chips with autocomplete
                $(chipsElement).chips({
                    autocompleteOptions: {
                        data: skillData,
                        limit: 5,
                        minLength: 1
                    },
                    placeholder: 'Add skills',
                    secondaryPlaceholder: '+Skill'
                });
            }
        });

    // Handle form submission if form exists
    const form = document.querySelector("form");
    if (form) {
        form.addEventListener("submit", function (event) {
            const chipsElement = document.querySelector('.chips-autocomplete');
            const chipsInstance = chipsElement ? M.Chips.getInstance(chipsElement) : null;
            let skillTags = chipsInstance ? chipsInstance.chipsData : [];
            let skills = skillTags.map(tag => tag.tag); // Extract skill names

            if (skills.length > 20) {
                alert("You can add up to 20 skills.");
                event.preventDefault();
                return;
            }

            // Append skills to form
            let skillInput = document.createElement("input");
            skillInput.type = "hidden";
            skillInput.name = "skills";
            skillInput.value = JSON.stringify(skills);
            this.appendChild(skillInput);
        });
    }
});
