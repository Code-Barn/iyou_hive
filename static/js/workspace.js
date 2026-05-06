/**
 * Hiver Workspace - Dynamic 3-Panel Collapsing/Expanding UI
 *
 * Uses two-button system (Left/Right arrows) for pane control
 * with data-state attribute for state management
 */

(function() {
    'use strict';

    // Toast notification container (created on demand)
    let toastContainer = null;
    let spinnerOverlay = null;

    /**
     * Show a loading spinner
     * @param {string} message - Optional message to display
     */
    function showSpinner(message = 'Loading...') {
        if (!spinnerOverlay) {
            spinnerOverlay = document.createElement('div');
            spinnerOverlay.className = 'spinner-overlay';
            spinnerOverlay.innerHTML = `
                <div style="text-align: center;">
                    <div class="spinner"></div>
                    <p style="color: white; margin-top: 10px; font-family: sans-serif;">${message}</p>
                </div>
            `;
            document.body.appendChild(spinnerOverlay);
        }
        spinnerOverlay.style.display = 'flex';
    }

    /**
     * Hide the loading spinner
     */
    function hideSpinner() {
        if (spinnerOverlay) {
            spinnerOverlay.style.display = 'none';
        }
    }

    /**
     * Show a toast notification
     * @param {string} message - The message to display
     * @param {string} type - Type of toast: 'success', 'error', 'info', 'warning'
     * @param {number} duration - Duration in ms (default: 3000)
     */
    function showToast(message, type = 'success', duration = 3000) {
        // Create container if it doesn't exist
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toast-container';
            toastContainer.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 9999;
                display: flex;
                flex-direction: column;
                gap: 10px;
                pointer-events: none;
            `;
            document.body.appendChild(toastContainer);
        }

        // Create toast element
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.style.cssText = `
            background: ${type === 'error' ? '#ef4444' : type === 'warning' ? '#f59e0b' : type === 'info' ? '#3b82f6' : '#10b981'};
            color: white;
            padding: 12px 20px;
            border-radius: 6px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            font-size: 14px;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            animation: slideIn 0.3s ease-out;
            pointer-events: auto;
            max-width: 400px;
            word-wrap: break-word;
        `;

        // Add icon based on type
        const icons = {
            'success': '✓',
            'error': '✗',
            'info': 'ℹ',
            'warning': '⚠'
        };
        toast.innerHTML = `<span style="margin-right: 8px;">${icons[type] || icons.info}</span>${message}`;

        // Add to container
        toastContainer.appendChild(toast);

        // Remove after duration
        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease-out';
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        }, duration);

        // Add CSS animations if not already added
        if (!document.getElementById('toast-styles')) {
            const style = document.createElement('style');
            style.id = 'toast-styles';
            style.textContent = `
                @keyframes slideIn {
                    from { transform: translateX(400px); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
                @keyframes slideOut {
                    from { transform: translateX(0); opacity: 1; }
                    to { transform: translateX(400px); opacity: 0; }
                }
            `;
            document.head.appendChild(style);
        }
    }

    /**
     * Initialize workspace panes
     * Sets up event delegation and restores saved states
     */
    function initWorkspace() {
        const workspace = document.querySelector('.workspace-body');
        if (!workspace) {
            console.warn('Workspace body not found');
            return;
        }

        // Restore pane states from localStorage
        restorePaneStates();

        // Set up event delegation for pane controls
        workspace.addEventListener('click', handlePaneControlClick);

        // Initialize button visibility
        document.querySelectorAll('.workspace-pane').forEach(updateButtonVisibility);

        // Listen for HTMX content swaps to re-initialize
        document.body.addEventListener('htmx:afterSwap', function(e) {
            // Only re-init if workspace content was swapped
            if (e.target.closest('.workspace-body')) {
                restorePaneStates();
                document.querySelectorAll('.workspace-pane').forEach(updateButtonVisibility);
            }
        });

        console.log('Workspace initialized with two-button collapse/expand system');
    }

    /**
     * Restore pane states from localStorage
     */
    function restorePaneStates() {
        document.querySelectorAll('.workspace-pane').forEach(pane => {
            const paneId = pane.id || pane.dataset.pane;
            if (!paneId) return;

            const savedState = localStorage.getItem(`pane-${paneId}-state`);
            if (savedState && ['default', 'collapsed', 'fullscreen'].includes(savedState)) {
                pane.dataset.state = savedState;
            } else {
                pane.dataset.state = 'default';
            }
        });
    }

    /**
     * Handle click events on pane control buttons (event delegation)
     * @param {Event} e - Click event
     */
    function handlePaneControlClick(e) {
        const button = e.target.closest('.pane-control');
        if (!button) return;

        e.preventDefault();
        e.stopPropagation();

        const pane = button.closest('.workspace-pane');
        if (!pane) return;

        const action = button.dataset.action;
        const paneId = pane.id || pane.dataset.pane;

        if (action === 'collapse') {
            handleCollapse(pane, paneId);
        } else if (action === 'expand') {
            handleExpand(pane, paneId);
        }

        // Update button visibility for all panes
        document.querySelectorAll('.workspace-pane').forEach(updateButtonVisibility);
    }

    /**
     * Handle collapse action
     * - If pane is default → set to collapsed
     * - If pane is fullscreen → restore all panes to default
     * @param {HTMLElement} pane - The pane element
     * @param {string} paneId - The pane identifier
     */
    function handleCollapse(pane, paneId) {
        if (pane.dataset.state === 'fullscreen') {
            // Restore all panes to default
            document.querySelectorAll('.workspace-pane').forEach(p => {
                p.dataset.state = 'default';
                const id = p.id || p.dataset.pane;
                localStorage.setItem(`pane-${id}-state`, 'default');
            });
            showToast('All panes restored to default view', 'info');
        } else {
            pane.dataset.state = 'collapsed';
            localStorage.setItem(`pane-${paneId}-state`, 'collapsed');
            const paneName = getPaneName(pane);
            showToast(`${paneName} pane collapsed`, 'info');
        }
    }

    /**
     * Handle expand action
     * - If pane is default → set to fullscreen (collapse others)
     * - If pane is collapsed → restore to default
     * @param {HTMLElement} pane - The pane element
     * @param {string} paneId - The pane identifier
     */
    function handleExpand(pane, paneId) {
        if (pane.dataset.state === 'collapsed') {
            pane.dataset.state = 'default';
            localStorage.setItem(`pane-${paneId}-state`, 'default');
            const paneName = getPaneName(pane);
            showToast(`${paneName} pane restored`, 'success');
        } else {
            // Set this pane to fullscreen, collapse others
            document.querySelectorAll('.workspace-pane').forEach(p => {
                const id = p.id || p.dataset.pane;
                if (p === pane) {
                    p.dataset.state = 'fullscreen';
                    localStorage.setItem(`pane-${id}-state`, 'fullscreen');
                } else {
                    p.dataset.state = 'collapsed';
                    localStorage.setItem(`pane-${id}-state`, 'collapsed');
                }
            });
            const paneName = getPaneName(pane);
            showToast(`${paneName} pane expanded to fullscreen`, 'success');
        }
    }

    /**
     * Get human-readable pane name
     * @param {HTMLElement} pane - The pane element
     * @returns {string} The pane name
     */
    function getPaneName(pane) {
        const h2 = pane.querySelector('.pane-header h2');
        return h2 ? h2.textContent : 'Unknown';
    }

    /**
     * Update button text/visibility based on pane state
     * @param {HTMLElement} pane - The pane element
     */
    function updateButtonVisibility(pane) {
        const leftArrow = pane.querySelector('.pane-control[data-action="collapse"]');
        const rightArrow = pane.querySelector('.pane-control[data-action="expand"]');

        if (!leftArrow || !rightArrow) return;

        const state = pane.dataset.state || 'default';

        switch (state) {
            case 'default':
                leftArrow.textContent = '←';
                leftArrow.title = 'Collapse pane';
                rightArrow.textContent = '→';
                rightArrow.title = 'Expand to fullscreen';
                break;
            case 'collapsed':
                leftArrow.textContent = '←';
                leftArrow.title = 'Collapse pane';
                rightArrow.textContent = '↗';
                rightArrow.title = 'Restore pane';
                break;
            case 'fullscreen':
                leftArrow.textContent = '↖';
                leftArrow.title = 'Restore all panes';
                rightArrow.textContent = '→';
                rightArrow.title = 'Expand to fullscreen';
                break;
        }
    }

    /**
     * Public API - expose functions for debugging if needed
     */
    window.HiverWorkspace = {
        init: initWorkspace,
        restoreStates: restorePaneStates,
        updateButtons: function() {
            document.querySelectorAll('.workspace-pane').forEach(updateButtonVisibility);
        }
    };

    // Initialize on DOMContentLoaded
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initWorkspace);
    } else {
        // DOM is already ready
        initWorkspace();
    }

})();
