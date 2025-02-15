document.addEventListener("DOMContentLoaded", function () {
    fetch('/api/skills/')
        .then(response => response.json())
        .then(data => {
            let skillData = {};
            data.forEach(skill => {
                skillData[skill.name] = null;  // Materialize format
            });

            // Initialize chips with autocomplete
            $('.chips-autocomplete').chips({
                autocompleteOptions: {
                    data: skillData,
                    limit: 5,
                    minLength: 1
                },
                placeholder: 'Add skills',
                secondaryPlaceholder: '+Skill'
            });
        });

    // Handle form submission
    document.querySelector("form").addEventListener("submit", function (event) {
        let skillTags = M.Chips.getInstance(document.querySelector('.chips-autocomplete')).chipsData;
        let skills = skillTags.map(tag => tag.tag);  // Extract skill names

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
});