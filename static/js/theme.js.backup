/**
 * Hiver - Theme & Timeline Integration
 *
 * This file handles:
 * 1. Dark/Light mode toggle with localStorage persistence
 * 2. Timeline event popup functionality
 * 3. AI Assistant integration
 * 4. Document rendering in popups
 * 5. Animations and transitions
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
  const logo = document.getElementById("site-logo");

  // Load saved theme preference from localStorage, default to dark mode
  const saved = localStorage.getItem("theme") || "dark";
  html.setAttribute("data-theme", saved);
  updateIcon(saved);
  updateLogo(saved);

  // Toggle theme on button click
  if (toggle) {
    toggle.addEventListener("click", function () {
      const current = html.getAttribute("data-theme");
      const next = current === "dark" ? "light" : "dark";
      html.setAttribute("data-theme", next);
      localStorage.setItem("theme", next);
      updateIcon(next);
      updateLogo(next);
    });
  }

  /**
   * Update the theme toggle icon based on current mode
   * @param {string} theme - Current theme ('light' or 'dark')
   */
  function updateIcon(theme) {
    const icon = toggle && toggle.querySelector(".theme-icon");
    if (icon) {
      // Dark mode is default, sun icon means switch to light mode
      icon.textContent = theme === "dark" ? "☀️" : "🌙";
    }
  }

  /**
   * Update the logo based on current theme
   * Switches between dark mode and light mode logos
   * @param {string} theme - Current theme ('light' or 'dark')
   */
  function updateLogo(theme) {
    if (logo) {
      if (theme === "dark") {
        logo.src = "/static/core/images/logos/DARK_mode_LOGO.png";
      } else {
        logo.src = "/static/core/images/logos/light_mode_LOGO.png";
      }
    }
  }

  /**
   * Initialize case selector dropdown
   */
  function initCaseSelector() {
    const caseSelector = document.getElementById("case-selector");
    if (!caseSelector) return;

    fetch("/core/api/cases/")
      .then((response) => response.json())
      .then((cases) => {
        const options = caseSelector.querySelectorAll(
          "option:not(:first-child)",
        );
        options.forEach((opt) => opt.remove());
        cases.forEach((caseItem) => {
          const option = document.createElement("option");
          option.value = caseItem.id;
          option.textContent = caseItem.name;
          caseSelector.appendChild(option);
        });
        const savedCaseId = localStorage.getItem("selectedCaseId");
        if (savedCaseId && cases.some((c) => c.id == savedCaseId)) {
          caseSelector.value = savedCaseId;
        }
      })
      .catch(console.error);

    caseSelector.addEventListener("change", function () {
      const caseId = this.value;
      if (caseId) {
        localStorage.setItem("selectedCaseId", caseId);
        // Reload page to show selected case
        window.location.href = "/timeline/?case_id=" + caseId;
      }
    });
  }

  /**
   * Initialize collapsible panes
   */
  function initCollapsiblePanes() {
    const panes = document.querySelectorAll(".workspace-pane.collapsible");
    panes.forEach((pane) => {
      const collapseButton = pane.querySelector(".collapse-button");
      const savedState = localStorage.getItem(pane.id + "_state");
      if (savedState === "collapsed") {
        pane.classList.add("collapsed");
      }
      if (collapseButton) {
        collapseButton.addEventListener("click", function () {
          const isCollapsed = pane.classList.toggle("collapsed");
          localStorage.setItem(
            pane.id + "_state",
            isCollapsed ? "collapsed" : "expanded",
          );
          this.textContent = isCollapsed ? "▶" : "▼";
        });
      }
    });
  }

  /**
   * Initialize timeline selector dropdown
   * Allows users to select different Markdown-based timelines
   */
  function initTimelineSelector() {
    const timelineSelector = document.getElementById("timeline-selector");
    if (!timelineSelector) return;

    timelineSelector.addEventListener("change", function () {
      const filePath = this.value;
      if (filePath) {
        // Save selection to localStorage
        localStorage.setItem("selectedTimelinePath", filePath);

        // Fetch timeline data
        fetch(
          `/timeline/api/load-timeline/?file_path=${encodeURIComponent(filePath)}`,
        )
          .then((response) => response.json())
          .then((data) => {
            if (data.status === "success") {
              // Update main heading
              const headingEl = document.getElementById("timeline-heading");
              if (headingEl) {
                headingEl.textContent = data.main_heading || "Legal Timeline";
              }

              // Reload page with new timeline selection
              window.location.href = `/timeline/?timeline_file=${encodeURIComponent(filePath)}`;
            }
          })
          .catch((error) => {
            console.error("Failed to load timeline:", error);
          });
      }
    });

    // Restore saved selection
    const savedTimelinePath = localStorage.getItem("selectedTimelinePath");
    if (savedTimelinePath) {
      const option = timelineSelector.querySelector(
        `option[value="${savedTimelinePath}"]`,
      );
      if (option) {
        timelineSelector.value = savedTimelinePath;
      }
    }
  }

  // Initialize workspace features
  initCaseSelector();
  initCollapsiblePanes();
  initTimelineSelector();
  initSubTimelineSelector();
});

/**
 * Initialize sub-timeline selector dropdown
 * Allows users to switch between different timelines within the same file
 * (e.g., timelines grouped by heading/subheading)
 */
function initSubTimelineSelector() {
  const subTimelineSelector = document.getElementById("sub-timeline-selector");
  if (!subTimelineSelector) return;

  // Check URL for timeline parameter
  const urlParams = new URLSearchParams(window.location.search);
  const timelineParam = urlParams.get("timeline");

  if (timelineParam) {
    // Set dropdown to match URL
    const option = subTimelineSelector.querySelector(
      `option[value="${timelineParam}"]`,
    );
    if (option) {
      subTimelineSelector.value = timelineParam;
      // Trigger switch to render the correct timeline
      switchSubTimeline(timelineParam);
    }
  }

  subTimelineSelector.addEventListener("change", function () {
    switchSubTimeline(this.value);
  });
}

/**
 * Switch to a different sub-timeline within the current timeline file
 * @param {string} timelineName - Name of the timeline to switch to
 */
function switchSubTimeline(timelineName) {
  const timelineSelector = document.getElementById("sub-timeline-selector");
  const eventsContainer = document.getElementById("timeline-events-container");
  const headingEl = document.getElementById("timeline-heading");

  if (!timelineSelector || !eventsContainer || !window.timelinesData) return;

  // Update the selected option in dropdown
  const option = timelineSelector.querySelector(
    `option[value="${timelineName}"]`,
  );
  if (option) {
    timelineSelector.value = timelineName;
  }

  // Update heading if needed
  if (headingEl && timelineName !== headingEl.textContent) {
    headingEl.textContent = timelineName;
  }

  // Update URL to allow bookmarking and sharing
  const url = new URL(window.location.href);
  url.searchParams.set("timeline", timelineName);
  window.history.pushState({}, "", url);

  // Re-render events for selected timeline
  const events = window.timelinesData[timelineName] || [];

  if (events.length === 0) {
    eventsContainer.innerHTML =
      '<div class="empty-timeline"><p>No events in this timeline.</p></div>';
    return;
  }

  // Build HTML for events
  let html = "";
  let currentYear = null;

  for (const event of events) {
    const year = event.date ? event.date.slice(0, 4) : "";

    // Add year marker if year changed
    if (year !== currentYear) {
      currentYear = year;
      html += `<div class="year-marker" data-year="${year}"><span class="year-text">${year}</span></div>`;
    }

    // Extract date parts
    const month = event.date ? event.date.slice(5, 7) : "01";
    const day = event.date ? event.date.slice(8, 10) : "01";

    // Build event card
    html += `
      <div class="timeline-event" data-date="${event.date || ""}" data-year="${year}" data-section="${event.section || ""}">
        <div class="event-date-badge">
          <span class="date-month">${month}</span>
          <span class="date-day">${day}</span>
          <span class="date-year">${year}</span>
        </div>
        <div class="event-content">
          <h3 class="event-title">${event.event || "Untitled"}</h3>
          <p class="event-category">${(event.category || "other").replace(/\b\w/, (l) => l.toUpperCase())}</p>
          <p class="event-description">${(event.description || event.notes || "").substring(0, 150)}</p>
        `;

    // Add documents indicator if present
    if (event.documents && event.documents.length > 0) {
      html += `
        <div class="event-docs-indicator">
          <span class="docs-icon">📎</span>
          <span class="docs-count">${event.documents.length} document(s)</span>
        </div>
      `;
    }

    html += `
        </div>
        <div class="event-connector"></div>
      </div>
    `;
  }

  eventsContainer.innerHTML = html;
}

/**
 * Timeline Popup Functionality
 *
 * Handles opening and closing of event detail popups with:
 * - Smooth animations
 * - Proper data population
 * - Keyboard accessibility (ESC to close)
 * - Click outside to close
 * - Document rendering
 */

// Global reference to the popup element
let eventPopup = null;
let currentEventId = null;
let isAnalyzingWithAI = false;

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

  currentEventId = eventId;
  const event = timelineEvents[eventId];

  // Populate popup content
  setPopupContent(eventId, event);

  // Reset AI section
  resetAISection();

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
 * Set popup content based on event data
 * @param {number} eventId - The event ID
 * @param {Object} event - The event data object
 */
function setPopupContent(eventId, event) {
  if (!event) return;

  // Set basic fields
  if (document.getElementById("popupTitle")) {
    document.getElementById("popupTitle").textContent = event.title;
  }
  if (document.getElementById("popupDate")) {
    document.getElementById("popupDate").textContent = event.date;
  }
  if (document.getElementById("popupCategory")) {
    document.getElementById("popupCategory").textContent =
      event.category || "Uncategorized";
  }
  if (document.getElementById("popupDescription")) {
    document.getElementById("popupDescription").textContent = event.description;
  }

  // Set documents
  renderDocuments(event);
}

/**
 * Render documents in the popup
 * @param {Object} event - The event data
 */
function renderDocuments(event) {
  const docsContainer = document.getElementById("popupDocs");
  const mediaSection = document.getElementById("popupMedia");

  if (!docsContainer) return;

  // Clear previous content
  docsContainer.innerHTML = "";

  // Check if there are documents
  const docUrls = event.document_urls || [];
  const supportingDocs = event.supporting_docs;

  if (!docUrls || docUrls.length === 0) {
    if (mediaSection) {
      mediaSection.style.display = "none";
    }
    return;
  }

  if (mediaSection) {
    mediaSection.style.display = "block";
  }

  // Render each document
  docUrls.forEach((doc, index) => {
    const docElement = document.createElement("div");
    docElement.className = "document-item";

    // Add loading attribute for lazy loading
    const docLink = document.createElement("a");
    docLink.href = doc.url || "#";
    docLink.target = "_blank";
    docLink.rel = "noopener noreferrer";

    // Determine icon based on file type
    let icon = "📄";
    if (doc.url) {
      const ext = doc.url.split(".").pop().toLowerCase();
      if (ext === "pdf") icon = "📕";
      else if (["png", "jpg", "jpeg", "gif", "webp", "svg"].includes(ext))
        icon = "🖼️";
      else if (["doc", "docx"].includes(ext)) icon = "📝";
      else if (["xls", "xlsx"].includes(ext)) icon = "📊";
      else if (["txt", "md", "markdown"].includes(ext)) icon = "📄";
      else if (["email", "eml"].includes(ext)) icon = "✉️";
    }

    docLink.innerHTML = `<span class="doc-icon">${icon}</span> <span class="doc-title">${doc.title || "Document " + (index + 1)}</span>`;

    // Add file size or type if available
    if (doc.size || doc.type) {
      const metaElement = document.createElement("span");
      metaElement.className = "doc-meta";
      metaElement.textContent = `[${doc.type || "File"} ${doc.size ? " - " + doc.size : ""}]`;
      docLink.appendChild(metaElement);
    }

    docElement.appendChild(docLink);

    // Add preview for images
    if (doc.url && isImageUrl(doc.url)) {
      const previewElement = document.createElement("div");
      previewElement.className = "doc-preview";
      previewElement.innerHTML = `<img src="${doc.url}" alt="${doc.title || "Preview"}" loading="lazy">`;
      docElement.appendChild(previewElement);
    }

    docsContainer.appendChild(docElement);
  });
}

/**
 * Check if a URL points to an image
 * @param {string} url - The URL to check
 * @returns {boolean} - True if URL is an image
 */
function isImageUrl(url) {
  const ext = url.split(".").pop().toLowerCase();
  return ["png", "jpg", "jpeg", "gif", "webp", "svg", "bmp"].includes(ext);
}

/**
 * Reset AI section to initial state
 */
function resetAISection() {
  const aiSection = document.getElementById("aiSection");
  const aiResponse = document.getElementById("aiResponse");
  const aiLoading = document.getElementById("aiLoading");
  const askAIBtn = document.getElementById("askAIBtn");

  if (aiSection) aiSection.style.display = "none";
  if (aiResponse) aiResponse.innerHTML = "";
  if (aiLoading) aiLoading.style.display = "block";
  if (askAIBtn) {
    askAIBtn.disabled = false;
    askAIBtn.innerHTML = '<span class="ai-icon">🤖</span> Ask AI About This';
  }
  isAnalyzingWithAI = false;
}

/**
 * Ask AI about the current event
 */
function askAIAboutEvent() {
  if (!currentEventId || isAnalyzingWithAI) return;

  const askAIBtn = document.getElementById("askAIBtn");
  const aiSection = document.getElementById("aiSection");
  const aiResponse = document.getElementById("aiResponse");
  const aiLoading = document.getElementById("aiLoading");

  if (!aiSection || !aiResponse || !askAIBtn) return;

  // Show AI section and loading state
  aiSection.style.display = "block";
  aiResponse.innerHTML = "";
  aiLoading.style.display = "block";
  askAIBtn.disabled = true;
  askAIBtn.innerHTML = '<span class="ai-icon">🤖</span> Analyzing...';

  isAnalyzingWithAI = true;

  // Make API call to analyze the event
  fetch(`/ai/analyze-event/${currentEventId}/`)
    .then((response) => response.json())
    .then((data) => {
      if (data.status === "success") {
        // Format AI response as markdown
        const formattedResponse = formatMarkdown(data.analysis);
        aiResponse.innerHTML = formattedResponse;
        aiLoading.style.display = "none";
        askAIBtn.disabled = false;
        askAIBtn.innerHTML = '<span class="ai-icon">🤖</span> Ask AI Again';
      } else {
        // Show error
        aiResponse.innerHTML =
          '<p class="ai-error">Error: ' +
          (data.error || "Failed to get AI analysis") +
          "</p>";
        aiLoading.style.display = "none";
        askAIBtn.disabled = false;
        askAIBtn.innerHTML = '<span class="ai-icon">🤖</span> Try Again';
      }
    })
    .catch((error) => {
      console.error("AI analysis error:", error);
      aiResponse.innerHTML =
        '<p class="ai-error">Error: Failed to connect to AI service. Please check your configuration.</p>';
      aiLoading.style.display = "none";
      askAIBtn.disabled = false;
      askAIBtn.innerHTML = '<span class="ai-icon">🤖</span> Try Again';
    })
    .finally(() => {
      isAnalyzingWithAI = false;
    });
}

/**
 * Format markdown text as HTML (simple formatting)
 * @param {string} markdown - Markdown text to format
 * @returns {string} - HTML formatted text
 */
function formatMarkdown(markdown) {
  if (!markdown) return "<p>No response from AI.</p>";

  // Escape HTML first
  let html = markdown
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  // Format headers
  html = html.replace(/^#\s+(.*?)$/gm, "<h2>$1</h2>");
  html = html.replace(/^##\s+(.*?)$/gm, "<h3>$1</h3>");
  html = html.replace(/^###\s+(.*?)$/gm, "<h4>$1</h4>");

  // Format bold and italic
  html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
  html = html.replace(/\*(.*?)\*/g, "<em>$1</em>");

  // Format lists
  html = html.replace(/^\-\s+(.*?)$/gm, "<li>$1</li>");
  html = html.replace(/^\d+\.\s+(.*?)$/gm, "<li>$1</li>");

  // Wrap lists in ul/ol
  html = html.replace(/((?:<li>.*<\/li>\n)+)/g, function (match) {
    return "<ul>" + match.trim().replace(/<\/li>\n/g, "</li>") + "</ul>";
  });

  // Format paragraphs
  html = html.replace(/\n\n+/g, "</p><p>");
  html = html.replace(/\n/g, "<br>");
  html = "<p>" + html + "</p>";

  // Format code blocks
  html = html.replace(/`(.*?)`/g, "<code>$1</code>");

  // Format links
  html = html.replace(
    /\[(.*?)\]\((.*?)\)/g,
    '<a href="$2" target="_blank" rel="noopener">$1</a>',
  );

  // Format horizontal rules
  html = html.replace(/^---$/gm, "<hr>");

  // Format blockquotes
  html = html.replace(/^>\s+(.*?)$/gm, "<blockquote>$1</blockquote>");

  return html;
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

    // Reset AI state when closing
    resetAISection();
    currentEventId = null;

    // Return focus to the event that was clicked
    const activeEvent = document.querySelector(".timeline-event:focus");
    if (activeEvent) {
      activeEvent.blur();
    }
  }
}

/**
 * Close popup by event ID (legacy function for backwards compatibility)
 * @param {number} eventId - The ID of the event whose popup should close
 */
function closePopup(eventId) {
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

/* ========================================
   Test Functions (for manual testing)
   ======================================== */

/**
 * Test function for updateLogo()
 * Can be called from browser console to verify logo toggle functionality
 * Usage: testUpdateLogo()
 */
function testUpdateLogo() {
  const logo = document.getElementById("site-logo");
  const html = document.documentElement;

  if (!logo) {
    console.error("Logo element not found for testing");
    return false;
  }

  // Test dark mode
  const originalTheme = html.getAttribute("data-theme");
  html.setAttribute("data-theme", "dark");
  updateLogo("dark");
  const darkLogo = logo.src.includes("DARK_mode_LOGO.png");

  // Test light mode
  html.setAttribute("data-theme", "light");
  updateLogo("light");
  const lightLogo = logo.src.includes("light_mode_LOGO.png");

  // Restore original theme
  html.setAttribute("data-theme", originalTheme);
  updateLogo(originalTheme);

  if (darkLogo && lightLogo) {
    console.log(
      "✓ updateLogo() test passed: Both dark and light logos load correctly",
    );
    return true;
  } else {
    console.error(
      "✗ updateLogo() test failed: Logo sources not updated correctly",
    );
    return false;
  }
}

/**
 * Test function for updateIcon()
 * Can be called from browser console to verify icon toggle functionality
 * Usage: testUpdateIcon()
 */
function testUpdateIcon() {
  const toggle = document.getElementById("theme-toggle");
  const icon = toggle && toggle.querySelector(".theme-icon");

  if (!icon) {
    console.error("Icon element not found for testing");
    return false;
  }

  // Test dark mode
  updateIcon("dark");
  const darkIcon = icon.textContent === "☀️";

  // Test light mode
  updateIcon("light");
  const lightIcon = icon.textContent === "🌙";

  // Restore
  const html = document.documentElement;
  const currentTheme = html.getAttribute("data-theme");
  updateIcon(currentTheme);

  if (darkIcon && lightIcon) {
    console.log("✓ updateIcon() test passed: Icons toggle correctly");
    return true;
  } else {
    console.error("✗ updateIcon() test failed: Icons not updated correctly");
    return false;
  }
}

/**
 * Run all theme tests
 * Usage: testTheme()
 */
function testTheme() {
  console.log("Running theme tests...");
  const logoTest = testUpdateLogo();
  const iconTest = testUpdateIcon();

  if (logoTest && iconTest) {
    console.log("✓ All theme tests passed!");
    return true;
  } else {
    console.error("✗ Some theme tests failed");
    return false;
  }
}
