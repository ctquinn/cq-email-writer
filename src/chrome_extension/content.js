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
    let userInput = ""; // Track the user's current input
    let suggestionActive = false; // Whether a suggestion is currently active
    let suggestionText = ""; // Store the current suggestion

    emailBody.addEventListener("keydown", async (event) => {
        const subject = emailSubject.value;
    
        // Update `userInput` based on key pressed
        if (event.key === "Backspace") {
            userInput = userInput.slice(0, -1);
        } else if (event.key.length === 1) {
            userInput += event.key; // Add visible characters (letters, spaces, etc.)
        }
    
        console.log(`User Input: '${userInput}'`);
    
        // Clear the active suggestion if the user starts typing
        if (suggestionActive && event.key.length === 1 && event.key !== "Tab") {
            clearSuggestion(emailBody);
            suggestionActive = false;
        }
    
        // Fetch and display a new suggestion if the user presses space
        if (event.key === " " && userInput.endsWith(" ")) {
            console.log("Space detected, fetching suggestion...");
            suggestionText = await fetchSuggestion(subject, userInput);
            console.log("Suggestion:", suggestionText);
            if (suggestionText) {
                showSuggestion(emailBody, suggestionText);
                suggestionActive = true;
            }
        }
    
        // Handle Tab key to accept the suggestion
        if (event.key === "Tab" && suggestionActive) {
            event.preventDefault(); // Prevent default Tab behavior
            clearSuggestion(emailBody);
            acceptSuggestion(emailBody, suggestionText);
            // clearSuggestion(emailBody);
            userInput = emailBody.innerText || emailBody.textContent || "";
            suggestionActive = false;
        }
    });
    

    // Periodically synchronize `userInput` with the actual content
    setInterval(() => {
        const actualText = emailBody.innerText || emailBody.textContent || "";
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
    clearSuggestion(emailBody); // Remove any existing suggestion

    // Create or reuse the suggestion element
    let suggestionElement = document.querySelector(".autocomplete-suggestion");
    if (!suggestionElement) {
        suggestionElement = document.createElement("span");
        suggestionElement.className = "autocomplete-suggestion";
        suggestionElement.style.color = "gray"; // Grayed-out text
        suggestionElement.style.fontStyle = "italic";
        suggestionElement.style.pointerEvents = "none"; // Prevent interaction
        suggestionElement.style.marginLeft = "5px"; // Add a gap
        emailBody.appendChild(suggestionElement);
    }

    // Set the suggestion text
    suggestionElement.innerText = suggestion;

    console.log("Suggestion displayed:", suggestion);
}


function clearSuggestion(emailBody) {
    const suggestionElement = document.querySelector(".autocomplete-suggestion");
    if (suggestionElement) {
        suggestionElement.remove(); // Remove the suggestion element from the UI
    }

    // Reset internal suggestion-related state
    suggestionText = ""; // Clear the suggestion text globally
}

function acceptSuggestion(emailBody, suggestionText) {
    if (!suggestionText) return;

    // Check if the suggestion is already part of the content
    const currentText = emailBody.innerText || emailBody.textContent || "";
    if (currentText.endsWith(suggestionText)) {
        console.log("Suggestion already appended, skipping...");
        return; // Avoid appending the same suggestion again
    }

    // Append the suggestion as a text node to ensure Gmail updates properly
    const suggestionNode = document.createTextNode(suggestionText + " ");
    emailBody.appendChild(suggestionNode);

    // Move the cursor to the end of the new content
    const range = document.createRange();
    const selection = window.getSelection();
    range.selectNodeContents(emailBody);
    range.collapse(false); // Move to the end
    selection.removeAllRanges();
    selection.addRange(range);

    console.log(`Accepted suggestion: '${suggestionText}'`);
}



// Start the content script
waitForGmail();
