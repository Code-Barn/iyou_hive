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

  console.log("API key form submitted"); // Debug log

  const apiKeyInput = document.getElementById("api-key-input");
  const apiKey = apiKeyInput.value.trim();

  if (!apiKey) {
    console.log("Empty API key"); // Debug log
    alert("Please enter your Mistral API key");
    return;
  }

  console.log("API key:", apiKey.substring(0, 10) + "..."); // Debug log

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
    body: JSON.stringify({ api_key: apiKey }),
  })
    .then((response) => {
      console.log("Response received:", response.status); // Debug log
      if (response.ok) {
        return response.json();
      } else {
        return response.json().catch(() => {
          throw new Error("Failed to save API key: " + response.status);
        });
      }
    })
    .then((data) => {
      console.log("Response data:", data); // Debug log
      if (data.success) {
        console.log("Success! Reloading page..."); // Debug log
        alert("API key saved successfully! Page will reload now.");
        // Reload the page to update the UI
        window.location.reload();
      } else {
        throw new Error(data.error || "Unknown error");
      }
    })
    .catch((error) => {
      console.error("Error saving API key:", error);
      alert("Error saving API key: " + error.message);
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
