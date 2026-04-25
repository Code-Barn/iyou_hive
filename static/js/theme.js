/**
 * Hiver - Theme & Popup Management
 *
 * This file handles:
 * 1. Dark/Light mode toggle with localStorage persistence
 * 2. Timeline event popup functionality
 * 3. Animations and transitions
 */

/**
 * Theme Toggle Functionality
 *
 * Handles dark/light mode switching with:
 * - localStorage persistence for user preference
 * - Smooth transitions between themes
 * - Icon updates to reflect current mode
 */
document.addEventListener("DOMContentLoaded", function () {
  const toggle = document.getElementById("theme-toggle");
  const html = document.documentElement;

  // Load saved theme preference from localStorage, default to light mode
  const saved = localStorage.getItem("theme") || "light";
  html.setAttribute("data-theme", saved);
  updateIcon(saved);

  // Toggle theme on button click
  toggle.addEventListener("click", function () {
    const current = html.getAttribute("data-theme");
    const next = current === "light" ? "dark" : "light";
    html.setAttribute("data-theme", next);
    localStorage.setItem("theme", next);
    updateIcon(next);
  });

  /**
   * Update the theme toggle icon based on current mode
   * @param {string} theme - Current theme ('light' or 'dark')
   */
  function updateIcon(theme) {
    const icon = toggle.querySelector(".theme-icon");
    if (icon) {
      icon.textContent = theme === "light" ? "🌙" : "☀️";
    }
  }
});

/**
 * Timeline Popup Functionality
 *
 * Handles opening and closing of event detail popups with:
 * - Smooth animations
 * - Proper data population
 * - Keyboard accessibility (ESC to close)
 * - Click outside to close
 */

// Global reference to the popup element
let eventPopup = null;

/**
 * Initialize popup functionality
 * Called when DOM is loaded and popup element exists
 */
function initPopup() {
  eventPopup = document.getElementById("eventPopup");

  if (eventPopup) {
    // Close popup when clicking the overlay
    const overlay = eventPopup.querySelector(".popup-overlay");
    if (overlay) {
      overlay.addEventListener("click", closeEventPopup);
    }

    // Close popup with ESC key
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && eventPopup.classList.contains("active")) {
        closeEventPopup();
      }
    });

    // Prevent body scroll when popup is open
    document.addEventListener("click", function () {
      if (eventPopup.classList.contains("active")) {
        document.body.style.overflow = "hidden";
      } else {
        document.body.style.overflow = "";
      }
    });
  }
}

/**
 * Open event popup with specified event ID
 * @param {number} eventId - The ID of the timeline event to display
 */
function openEventPopup(eventId) {
  eventPopup = document.getElementById("eventPopup");

  if (!eventPopup || !timelineEvents || !timelineEvents[eventId]) {
    console.error("Popup element or event data not found");
    return;
  }

  // Initialize popup if not already done
  if (!eventPopup.onclick) {
    initPopup();
  }

  const event = timelineEvents[eventId];

  // Populate popup content
  if (document.getElementById("popupTitle")) {
    document.getElementById("popupTitle").textContent = event.title;
  }
  if (document.getElementById("popupDate")) {
    document.getElementById("popupDate").textContent = event.date;
  }
  if (document.getElementById("popupCategory")) {
    document.getElementById("popupCategory").textContent = event.category;
  }
  if (document.getElementById("popupDescription")) {
    document.getElementById("popupDescription").textContent = event.description;
  }
  if (document.getElementById("popupNotes")) {
    document.getElementById("popupNotes").textContent = event.description;
  }

  // Handle supporting documents
  const docsContainer = document.getElementById("popupDocs");
  const mediaSection = document.getElementById("popupMedia");

  if (docsContainer && event.supporting_docs) {
    // Parse documents string and create links
    const docs = parseDocuments(event.supporting_docs);
    if (docs.length > 0) {
      docsContainer.innerHTML = docs
        .map(
          (doc) => `
                <a href="${doc.url}" target="_blank" rel="noopener noreferrer">
                    <span class="doc-icon">📄</span> ${doc.text || doc.url}
                </a>
            `,
        )
        .join("");
      mediaSection.style.display = "block";
    } else {
      mediaSection.style.display = "none";
    }
  } else if (mediaSection) {
    mediaSection.style.display = "none";
  }

  // Show popup with animation
  eventPopup.classList.add("active");
  document.body.style.overflow = "hidden";

  // Focus on close button for accessibility
  const closeBtn = eventPopup.querySelector(".popup-close");
  if (closeBtn) {
    closeBtn.focus();
  }

  // Track popup open for analytics/debugging
  console.log(`Opened popup for event ${eventId}: ${event.title}`);
}

/**
 * Close the event popup
 */
function closeEventPopup() {
  if (!eventPopup) {
    eventPopup = document.getElementById("eventPopup");
  }

  if (eventPopup) {
    eventPopup.classList.remove("active");
    document.body.style.overflow = "";

    // Return focus to the event that was clicked
    const activeEvent = document.querySelector(".timeline-event:focus");
    if (activeEvent) {
      activeEvent.blur();
    }
  }
}

/**
 * Parse supporting documents string into array of document objects
 * @param {string} docsString - The supporting_docs string from event data
 * @returns {Array} Array of document objects with url and text properties
 */
function parseDocuments(docsString) {
  if (!docsString || docsString.trim() === "") {
    return [];
  }

  // Simple parsing for markdown-style links: [text](url)
  const linkRegex = /\[(.*?)\]\((.*?)\)/g;
  const matches = [];
  let match;

  while ((match = linkRegex.exec(docsString)) !== null) {
    matches.push({
      text: match[1],
      url: match[2],
    });
  }

  // If no markdown links found, just split by commas/newlines
  if (matches.length === 0) {
    return docsString
      .split(/[,\n]/)
      .map((url) => url.trim())
      .filter((url) => url)
      .map((url) => ({ text: url, url: url }));
  }

  return matches;
}

/**
 * Close popup by event ID (legacy function for backwards compatibility)
 * @param {number} eventId - The ID of the event whose popup should close
 */
function closePopup(eventId) {
  // Legacy support - close the main popup
  closeEventPopup();
}

/**
 * Show popup by event ID (legacy function for backwards compatibility)
 * @param {number} eventId - The ID of the event whose popup should open
 */
function showPopup(eventId) {
  openEventPopup(eventId);
}

// Initialize popup on DOM load
document.addEventListener("DOMContentLoaded", function () {
  initPopup();

  // Add click handlers for any legacy popup elements
  document.querySelectorAll('[id^="popup-"]').forEach((popup) => {
    const closeBtn = popup.querySelector(".popup-close");
    if (closeBtn) {
      closeBtn.addEventListener("click", () => {
        popup.classList.remove("active");
      });
    }
  });
});

// Close popup when clicking anywhere on the document that's not part of the popup
eventPopup = document.getElementById("eventPopup");
document.addEventListener("click", function (e) {
  if (eventPopup && eventPopup.classList.contains("active")) {
    if (!eventPopup.contains(e.target)) {
      closeEventPopup();
    }
  }
});
