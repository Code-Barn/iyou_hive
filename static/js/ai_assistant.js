/**
 * AI Assistant JavaScript
 * Handles API key management and chat functionality
 */

// Wait for DOM to be ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initAIAssistant);
} else {
  initAIAssistant();
}

function initAIAssistant() {
  // Set up settings toggle
  const settingsToggle = document.getElementById("ai-settings-toggle");
  if (settingsToggle) {
    settingsToggle.addEventListener("click", () => {
      const panel = document.getElementById("ai-settings-panel");
      if (panel.style.display === "none") {
        panel.style.display = "block";
      } else {
        panel.style.display = "none";
      }
    });
  }

  // Set up API key form submission
  const apiKeyForm = document.getElementById("api-key-form");
  if (apiKeyForm) {
    apiKeyForm.addEventListener("submit", handleApiKeySubmit);
  }

  // Set up chat form submission
  const chatForm = document.getElementById("chat-form");
  if (chatForm) {
    chatForm.addEventListener("submit", handleChatSubmit);
  }
}

/**
 * Handle API key form submission
 */
function handleApiKeySubmit(event) {
  event.preventDefault();

  console.log("API settings form submitted"); // Debug log

  const mistralKeyInput = document.getElementById("mistral-key-input");
  const geminiKeyInput = document.getElementById("gemini-key-input");
  const providerInput = document.getElementById("preferred-provider");

  const mistralApiKey = mistralKeyInput ? mistralKeyInput.value.trim() : "";
  const geminiApiKey = geminiKeyInput ? geminiKeyInput.value.trim() : "";
  const preferredProvider = providerInput ? providerInput.value : "mistral";

  if (!mistralApiKey && !geminiApiKey) {
    alert("Please enter at least one API key (Mistral or Gemini).");
    return;
  }

  // Show loading state
  const form = document.getElementById("api-key-form");
  const submitButton = form.querySelector('button[type="submit"]');
  const originalButtonText = submitButton.textContent;
  submitButton.textContent = "Saving...";
  submitButton.disabled = true;

  console.log("Sending request to:", "/ai/save-api-key/"); // Debug log

  // Send API key to server
  fetch("/ai/save-api-key/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCsrfToken(),
    },
    body: JSON.stringify({
      mistral_api_key: mistralApiKey,
      gemini_api_key: geminiApiKey,
      preferred_provider: preferredProvider,
    }),
  })
    .then((response) => {
      console.log("Response received:", response.status); // Debug log
      if (response.ok) {
        return response.json();
      } else {
        return response.json().catch(() => {
          throw new Error("Failed to save API settings: " + response.status);
        });
      }
    })
    .then((data) => {
      console.log("Response data:", data); // Debug log
      if (data.success) {
        console.log("Success! Reloading page..."); // Debug log
        alert("API settings saved successfully! Page will reload now.");
        // Reload the page to update the UI
        window.location.reload();
      } else {
        throw new Error(data.error || "Unknown error");
      }
    })
    .catch((error) => {
      console.error("Error saving API settings:", error);
      alert("Error saving API settings: " + error.message);
      submitButton.textContent = originalButtonText;
      submitButton.disabled = false;
    });
}

/**
 * Handle chat form submission
 */
function handleChatSubmit(event) {
  event.preventDefault();

  const userInput = document.getElementById("user-input");
  const message = userInput.value.trim();

  if (!message) {
    return;
  }

  // Add user message to chat history
  addMessageToChat("user", message);
  userInput.value = "";

  // Show typing indicator
  const typingIndicator = document.createElement("div");
  typingIndicator.className = "message assistant typing-indicator";
  typingIndicator.textContent = "AI is thinking...";
  document.getElementById("chat-history").appendChild(typingIndicator);

  // Scroll to bottom
  scrollChatToBottom();

  // Send message to AI API
  fetch("/ai/query-timeline/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCsrfToken(),
    },
    body: JSON.stringify({ query: message }),
  })
    .then((response) => {
      if (response.ok) {
        return response.json();
      } else {
        throw new Error("AI request failed");
      }
    })
    .then((data) => {
      // Remove typing indicator
      typingIndicator.remove();

      if (data.status === "success") {
        // Add AI response to chat history
        addMessageToChat("assistant", data.response);
      } else {
        addMessageToChat(
          "assistant",
          "Error: " + (data.error || "Unknown error"),
        );
      }

      // Scroll to bottom
      scrollChatToBottom();
    })
    .catch((error) => {
      console.error("Error calling AI API:", error);
      typingIndicator.remove();
      addMessageToChat("assistant", "Error: " + error.message);
      scrollChatToBottom();
    });
}

/**
 * Add a message to the chat history
 */
function addMessageToChat(sender, message) {
  const chatHistory = document.getElementById("chat-history");
  const messageElement = document.createElement("div");
  messageElement.className = `message ${sender}`;
  messageElement.textContent = message;
  chatHistory.appendChild(messageElement);
}

/**
 * Scroll chat to bottom
 */
function scrollChatToBottom() {
  const chatHistory = document.getElementById("chat-history");
  chatHistory.scrollTop = chatHistory.scrollHeight;
}

/**
 * Get CSRF token from cookie
 */
function getCsrfToken() {
  const cookieValue = document.cookie
    .split("; ")
    .find((row) => row.startsWith("csrftoken="));
  return cookieValue ? cookieValue.split("=")[1] : "";
}
