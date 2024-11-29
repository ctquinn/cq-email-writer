function waitForGmail() {
    const emailBodySelector = "div[aria-label='Message Body']";
    const emailSubjectSelector = "input[name='subjectbox']";

    // Poll for the Gmail elements
    const interval = setInterval(() => {
        const emailBody = document.querySelector(emailBodySelector);
        const emailSubject = document.querySelector(emailSubjectSelector);

        if (emailBody && emailSubject) {
            console.log("Gmail Auto-Complete Content Script Running!");
            clearInterval(interval);

            // Observe email input
            observeEmailInput(emailBody, emailSubject);
        }
    }, 500);
}

function observeEmailInput(emailBody, emailSubject) {
    console.log("Observing Email Inputs...");
    let userInput = ""; // Manually track input

    emailBody.addEventListener("keydown", async (event) => {
        const subject = emailSubject.value;

        // Update `userInput` based on key pressed
        if (event.key === "Backspace") {
            userInput = userInput.slice(0, -1);
        } else if (event.key.length === 1) {
            userInput += event.key; // Add visible characters (letters, spaces, etc.)
        }

        console.log(`User Input: '${userInput}'`);

        if (event.key === " " && userInput.endsWith(" ")) {
            console.log("Space detected, fetching suggestion...");
            const suggestion = await fetchSuggestion(subject, userInput);
            console.log("Suggestion:", suggestion);
            showSuggestion(emailBody, suggestion);
        }
    });

    // Periodically synchronize userInput with Gmail's actual content
    setInterval(() => {
        const actualText = emailBody.textContent || "";
        if (!actualText.startsWith(userInput)) {
            console.log("Resyncing userInput with actual content...");
            userInput = actualText;
        }
    }, 1000);
}

async function fetchSuggestion(subject, textSoFar) {
    try {
        const response = await fetch("http://127.0.0.1:5000/autocomplete", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ subject, text_so_far: textSoFar }),
        });

        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }

        const data = await response.json();
        return data.suggestion || "";
    } catch (error) {
        console.error("Error fetching suggestion:", error);
        return ""; // Fallback to no suggestion
    }
}

function showSuggestion(emailBody, suggestion) {
    if (!suggestion) return;

    let suggestionElement = document.querySelector(".autocomplete-suggestion");
    if (!suggestionElement) {
        suggestionElement = document.createElement("span");
        suggestionElement.className = "autocomplete-suggestion";
        suggestionElement.style.color = "gray";
        suggestionElement.style.fontStyle = "italic";
        suggestionElement.style.marginLeft = "5px";
        emailBody.appendChild(suggestionElement);
    }

    suggestionElement.innerText = suggestion;

    emailBody.addEventListener("keydown", (event) => {
        if (event.key === "Tab") {
            event.preventDefault();
            acceptSuggestion(emailBody, suggestionElement);
        }
    });
}

function acceptSuggestion(emailBody, suggestionElement) {
    if (!suggestionElement) return;

    emailBody.textContent += suggestionElement.innerText;
    suggestionElement.remove();

    const range = document.createRange();
    const selection = window.getSelection();
    range.selectNodeContents(emailBody);
    range.collapse(false);
    selection.removeAllRanges();
    selection.addRange(range);
}

// Start polling for Gmail when the content script is loaded
waitForGmail();
