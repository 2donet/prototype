document.addEventListener("DOMContentLoaded", function () {
    var slider = document.getElementById("test-slider");
    noUiSlider.create(slider, {
        start: [20, 80],
        connect: true,
        step: 1,
        orientation: "horizontal",
        range: {
            min: 0,
            max: 100,
        },
        format: wNumb({
            decimals: 0,
        }),
    });

    let existingSkills = {}; // Stores fetched skills to prevent duplicates

    // Function to fetch skills from DRF API
    function fetchSkills() {
        fetch("/api/skills/")
            .then((response) => response.json())
            .then((data) => {
                existingSkills = {}; // Reset local storage
                data.forEach((skill) => {
                    existingSkills[skill.name.toLowerCase()] = null; // Store for duplicate prevention
                });

                // Initialize the chips component with fetched data
                $(".chips-autocomplete").chips({
                    data: [
                        { tag: "Apple" },
                        { tag: "Microsoft" },
                        { tag: "Google" },
                    ],
                    autocompleteOptions: {
                        data: existingSkills, // Inject fetched data here
                        limit: Infinity,
                        minLength: 1,
                    },
                    onChipAdd: function (event, chip) {
                        let newSkill = chip.text().trim();

                        // Check if skill is already in the backend
                        if (!(newSkill.toLowerCase() in existingSkills)) {
                            saveNewSkill(newSkill); // Save to backend
                        }
                    },
                });
            })
            .catch((error) => console.error("Error fetching skills:", error));
    }

    // Function to save a new skill to the API
    function saveNewSkill(skill) {
        fetch("/api/skills/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ name: skill }),
        })
            .then((response) => response.json())
            .then((data) => {
                existingSkills[skill.toLowerCase()] = null; // Add to local store
                console.log(`✅ Skill "${skill}" added successfully!`);
            })
            .catch((error) => console.error("❌ Error adding skill:", error));
    }

    // Fetch skills when page loads
    fetchSkills();
});