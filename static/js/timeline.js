/**
 * Timeline JavaScript - Dynamic rendering with color-coding
 * Handles fetching timeline data and rendering events with source_party styling
 */

// Global state
let currentCaseId = null;
let currentTimelineData = [];

/**
 * Fetch timeline data from the API
 */
async function fetchTimelineData(caseId) {
    try {
        const response = await fetch(`/api/timeline/${caseId}/`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Failed to fetch timeline data:', error);
        return { timeline: [] };
    }
}

/**
 * Get CSRF token from cookies
 */
function getCSRFToken() {
    const cookieValue = document.cookie
        .split('; ')
        .find(row => row.startsWith('csrftoken='));
    return cookieValue ? cookieValue.split('=')[1] : '';
}

/**
 * Map source_party value to CSS class
 */
function getTimelineClass(sourceParty) {
    const mapping = {
        'CLIENT': 'client',
        'OPPOSING': 'opposing',
        'NEUTRAL': 'neutral',
    };
    return mapping[sourceParty] || 'neutral';
}

/**
 * Map source_party value to human-readable label
 */
function getSourcePartyLabel(sourceParty) {
    const mapping = {
        'CLIENT': 'Client',
        'OPPOSING': 'Opposing Party',
        'NEUTRAL': 'Neutral',
    };
    return mapping[sourceParty] || 'Unknown';
}

/**
 * Map category to badge class
 */
function getCategoryBadgeClass(category) {
    const mapping = {
        'VERIFIED': 'verified',
        'CONTESTED': 'contested',
    };
    return mapping[category] || 'contested';
}

/**
 * Create a timeline event element with color-coding
 */
function createTimelineEventElement(event) {
    const eventDiv = document.createElement('div');
    const sourceParty = event.source_party || 'NEUTRAL';
    const timelineClass = getTimelineClass(sourceParty);
    const label = getSourcePartyLabel(sourceParty);
    const categoryClass = getCategoryBadgeClass(event.category);

    // Parse date for display
    let year, month, day;
    if (event.date) {
        const dateParts = event.date.split('-');
        year = dateParts[0];
        month = dateParts[1] || '01';
        day = dateParts[2] || '01';
    } else {
        year = '----';
        month = '--';
        day = '--';
    }

    eventDiv.className = `timeline-event ${timelineClass}`;
    eventDiv.dataset.date = event.date || '';
    eventDiv.dataset.year = year;
    eventDiv.dataset.section = event.section || '';
    eventDiv.dataset.sourceParty = sourceParty;

    eventDiv.innerHTML = `
        <span class="source-party">${label}</span>
        <div class="event-date-badge">
            <span class="date-month">${month}</span>
            <span class="date-day">${day}</span>
            <span class="date-year">${year}</span>
        </div>
        <div class="event-content">
            <h3 class="event-title">${event.title || event.event || 'Untitled Event'}</h3>
            <p class="event-category">${(event.category || '').charAt(0).toUpperCase() + (event.category || '').slice(1)}</p>
            <p class="event-description">${event.content || event.description || ''}</p>
            ${event.citation ? `<div class="citation">(${event.category ? event.category.charAt(0).toUpperCase() + event.category.slice(1) : 'Document'}: ${event.citation})</div>` : ''}
        </div>
        <div class="event-connector"></div>
    `;

    return eventDiv;
}

/**
 * Render timeline events into container
 */
function renderTimelineEvents(data, containerId = 'timeline-events-container') {
    const container = document.getElementById(containerId);
    if (!container) {
        console.error(`Container #${containerId} not found`);
        return;
    }

    // Clear existing events
    container.innerHTML = '';

    if (!data || !data.timeline || data.timeline.length === 0) {
        container.innerHTML = '<div class="empty-timeline"><p>No timeline events yet. Upload a markdown file to get started.</p></div>';
        return;
    }

    // Sort events by date
    const sortedEvents = [...data.timeline].sort((a, b) => {
        const dateA = a.date || '0000-00-00';
        const dateB = b.date || '0000-00-00';
        return dateA.localeCompare(dateB);
    });

    // Group events by year for year markers
    let currentYear = null;
    sortedEvents.forEach(event => {
        const eventYear = event.date ? event.date.split('-')[0] : '----';

        // Add year marker if year changed
        if (eventYear !== currentYear) {
            const yearMarker = document.createElement('div');
            yearMarker.className = 'year-marker';
            yearMarker.dataset.year = eventYear;
            yearMarker.innerHTML = `<span class="year-text">${eventYear}</span>`;
            container.appendChild(yearMarker);
            currentYear = eventYear;
        }

        // Create and append event
        const eventElement = createTimelineEventElement(event);
        container.appendChild(eventElement);
    });
}

/**
 * Initialize timeline with color-coding
 */
async function initTimeline(caseId, useDynamicRendering = false) {
    currentCaseId = caseId;

    if (useDynamicRendering) {
        // Fetch and render dynamically
        const data = await fetchTimelineData(caseId);
        currentTimelineData = data;
        renderTimelineEvents(data);
    }
}

/**
 * Render timeline from existing template data (for server-side rendered pages)
 * This enhances existing events with color-coding
 */
function enhanceExistingTimeline() {
    const events = document.querySelectorAll('.timeline-event');
    events.forEach(event => {
        const sourceParty = event.dataset.sourceParty || 'NEUTRAL';
        const timelineClass = getTimelineClass(sourceParty);

        // Add the color-coding class if not already present
        if (!event.classList.contains(timelineClass)) {
            event.classList.add(timelineClass);
        }

        // Ensure source-party label exists
        if (!event.querySelector('.source-party')) {
            const label = getSourcePartyLabel(sourceParty);
            const sourceSpan = document.createElement('span');
            sourceSpan.className = 'source-party';
            sourceSpan.textContent = label;
            // Insert as first child
            if (event.firstChild) {
                event.insertBefore(sourceSpan, event.firstChild);
            } else {
                event.appendChild(sourceSpan);
            }
        }
    });
}

/**
 * Refresh timeline data
 */
async function refreshTimeline() {
    if (currentCaseId) {
        const data = await fetchTimelineData(currentCaseId);
        currentTimelineData = data;
        renderTimelineEvents(data);
    }
}

/**
 * Filter timeline by source party
 */
function filterTimelineBySource(sourceParty) {
    const events = document.querySelectorAll('.timeline-event');
    events.forEach(event => {
        const eventSource = event.dataset.sourceParty || 'NEUTRAL';
        if (sourceParty === 'ALL' || eventSource === sourceParty) {
            event.style.display = '';
        } else {
            event.style.display = 'none';
        }
    });
}

/**
 * Add source party filter controls to the page
 */
function addSourcePartyFilters() {
    const header = document.querySelector('.timeline-header');
    if (!header) return;

    const filterHtml = `
        <div class="source-party-filters">
            <span class="filter-label">Filter by source:</span>
            <button class="filter-btn active" data-filter="ALL" onclick="filterTimelineBySource('ALL')">All</button>
            <button class="filter-btn" data-filter="CLIENT" onclick="filterTimelineBySource('CLIENT')">Client</button>
            <button class="filter-btn" data-filter="OPPOSING" onclick="filterTimelineBySource('OPPOSING')">Opposing</button>
            <button class="filter-btn" data-filter="NEUTRAL" onclick="filterTimelineBySource('NEUTRAL')">Neutral</button>
        </div>
    `;

    header.insertAdjacentHTML('beforeend', filterHtml);

    // Add styles for filters
    const style = document.createElement('style');
    style.textContent = `
        .source-party-filters {
            margin-top: 10px;
            display: flex;
            align-items: center;
            gap: 10px;
            flex-wrap: wrap;
        }
        .filter-label {
            font-size: 14px;
            font-weight: 600;
            color: var(--text-secondary);
        }
        .filter-btn {
            padding: 6px 12px;
            border: 1px solid var(--border);
            background: var(--bg);
            color: var(--text);
            border-radius: 4px;
            cursor: pointer;
            font-size: 13px;
            transition: all 0.2s ease;
        }
        .filter-btn:hover {
            border-color: var(--primary);
            background: var(--bg-alt);
        }
        .filter-btn.active {
            background: var(--primary);
            border-color: var(--primary);
            color: #000;
            font-weight: 600;
        }
        .filter-btn[data-filter="CLIENT"].active {
            background: #22c55e;
            border-color: #22c55e;
            color: white;
        }
        .filter-btn[data-filter="OPPOSING"].active {
            background: #ef4444;
            border-color: #ef4444;
            color: white;
        }
        .filter-btn[data-filter="NEUTRAL"].active {
            background: #64748b;
            border-color: #64748b;
            color: white;
        }
    `;
    document.head.appendChild(style);

    // Update active state on click
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
        });
    });
}

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', function() {
    // Extract case_id from URL or data attributes
    const caseId = window.location.pathname.split('/').pop() ||
                  document.getElementById('timeline-events-container')?.dataset.caseId ||
                  document.querySelector('[data-case-id]')?.dataset.caseId;

    if (caseId && caseId !== 'timeline') {
        // Try to use dynamic rendering if API endpoint exists
        initTimeline(caseId, true).then(() => {
            // If no events were rendered, enhance existing ones
            const container = document.getElementById('timeline-events-container');
            if (!container || container.children.length === 0 ||
                container.querySelector('.empty-timeline')) {
                enhanceExistingTimeline();
            }
        });
    } else {
        // Enhance existing server-rendered events
        enhanceExistingTimeline();
    }

    // Add filter controls
    addSourcePartyFilters();
});

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        fetchTimelineData,
        renderTimelineEvents,
        initTimeline,
        refreshTimeline,
        filterTimelineBySource,
        getTimelineClass,
        getSourcePartyLabel,
        getCategoryBadgeClass
    };
}
