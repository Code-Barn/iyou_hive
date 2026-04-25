# Hiver Style Guide

## Overview
This style guide ensures consistency across the Hiver project, aligning with the Byers Brands ecosystem. Hiver uses a modern, legal-focused design with a honey-orange and Byers blue color scheme.

## Color Palette

### Primary Colors
- **Primary:** Honey-Orange (`#FF8C00`) - Used for accent text, borders, and interactive elements
- **Accent:** Byers Blue (`#0064AA`) - Used for event titles, buttons, and important highlights

### Light Mode
| Element | Color | Hex | Usage |
|---------|-------|-----|-------|
| Background | Off-White | `#F5F5F5` | Page background |
| Text | Dark Gray | `#333333` | Primary text |
| Secondary Text | Gray | `#666666` | Less important text |
| Card Background | White | `#FFFFFF` | Cards, popups |
| Border | Light Gray | `#E0E0E0` | Borders, dividers |

### Dark Mode
| Element | Color | Hex | Usage |
|---------|-------|-----|-------|
| Background | Charcoal | `#1A1A1A` | Page background |
| Text | White | `#FFFFFF` | Primary text |
| Secondary Text | Light Gray | `#CCCCCC` | Less important text |
| Card Background | Dark Gray | `#2A2A2A` | Cards, popups |
| Border | Dark Gray | `#404040` | Borders, dividers |

### CSS Variables
```css
:root {
    --primary: #FF8C00;        /* Honey-Orange */
    --accent: #0064AA;         /* Byers Blue */
    --bg: #F5F5F5;            /* Off-White (light) / Charcoal (dark) */
    --text: #333333;          /* Dark Gray (light) / White (dark) */
    --text-secondary: #666666;
    --bg-card: #FFFFFF;        /* White (light) / Dark Gray (dark) */
    --border: #E0E0E0;
    --shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}
```

## Typography
- **Font Family:** `'Helvetica Neue', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif`
- **Headings:** Bold, sans-serif
- **Body Text:** Regular, sans-serif
- **Line Height:** 1.6 for body text, 1.7 for descriptions

### Heading Hierarchy
- **H1:** 2rem (32px), 700 weight, used for page titles
- **H2:** 1.75rem (28px), 700 weight, used for popup titles
- **H3:** 1.25rem (20px), 700 weight, used for event titles
- **H4:** 1rem (16px), 600 weight, used for section headers

## UI Components

### Navigation Bar
The navigation bar appears at the top of every page and provides access to key features.

#### Structure
```
┌─────────────────────────────────────────────────────────────┐
│  [Logo]                    [Timeline] [Archive] [AI] [Login]  ☀️ │
└─────────────────────────────────────────────────────────────┘
```

#### Specifications
- **Background**: var(--bg-navbar) - #1E1E1E (dark mode), #FFFFFF (light mode)
- **Border**: 2px solid Honey-Orange (#FF8C00) at bottom
- **Position**: Sticky at top with z-index: 100
- **Padding**: 1rem 2rem
- **Logo**: Centered on left, 120px height (3x original), links to home (`/`)
- **Navigation Links**: Centered, using .nav-button class with hover effects
- **Theme Toggle**: Right side, using .theme-toggle class

#### Navigation Buttons
- **Timeline**: Links to `/timeline/` - Honey-Orange hover effect
- **Archive**: Links to `/archive/` - Honey-Orange hover effect
- **AI Assistant**: Links to `/ai/` - Honey-Orange hover effect (authenticated users only)
- **Login/Logout**: Links to authentication pages - Honey-Orange hover effect

#### Theme Toggle Button
- **Class**: `.theme-toggle`
- **Styles**:
  - Border: 2px solid var(--primary)
  - Padding: 0.5rem 1rem
  - Border-radius: 4px
  - Color: var(--text)
  - Hover: background var(--primary), color white
- **Icon**: .theme-icon with sun (☀️) for dark mode, moon (🌙) for light mode
- **Functionality**:
  - Persists preference to localStorage
  - Calls updateIcon() and updateLogo() on theme change
  - Defaults to dark mode if no preference saved

#### Logo Toggle Implementation
The logo automatically switches based on the current theme using JavaScript:

```javascript
// In theme.js
function updateLogo(theme) {
  const logo = document.getElementById('site-logo');
  if (logo) {
    if (theme === 'dark') {
      logo.src = '/static/core/images/logos/DARK_mode_LOGO.png';
    } else {
      logo.src = '/static/core/images/logos/light_mode_LOGO.png';
    }
  }
}

// Called on DOMContentLoaded and theme toggle
updateLogo(saved);
```

**Logo Assets:**
- Dark mode: `/static/core/images/logos/DARK_mode_LOGO.png`
- Light mode: `/static/core/images/logos/light_mode_LOGO.png`
- Size: 120px height (desktop), 80px (mobile)

### Timeline
The timeline is the core component of Hiver, displaying legal events in a vertical scrolling layout.

#### Layout Structure
```
┌─────────────────────────────────────────┐
│            Timeline Container             │
│  ┌─────────────────────────────────────┐│
│  │        Timeline Header                ││
│  │  [Title]              [Upload Btn]    ││
│  └─────────────────────────────────────┘│
│                                         │
│  ┌─────────────────────────────────────┐│
│  │        Year 2023 (Sticky)             ││
│  └─────────────────────────────────────┘│
│                                         │
│  ┌─────┐                               ││
│  │     │  ┌───────────────────────────┐││
│  │ M15 │  │ Event Title               │││
│  │     │  │ Category                 │││
│  │ D   │  │ Description text...      │││
│  │     │  │ 📎 Documents available   │││
│  │ Y   │  └───────────────────────────┘││
│  │     │                               ││
│  └─────┘                               ││
│  ┌─────┐                               ││
│  │     │  ┌───────────────────────────┐││
│  │ JAN │  │ Next Event                │││
│  │     │  │ ...                       │││
│  │ 1   │  └───────────────────────────┘││
│  │     │                               ││
│  └─────┘                               ││
└─────────────────────────────────────────┘
```

#### Timeline Element Specifications

**Container**
- Max-width: 900px
- Centered on page
- Padding: 1rem

**Vertical Line**
- Position: Absolute, left-aligned
- Width: 2px
- Color: Honey-Orange (#FF8C00)
- Spans entire height of timeline

**Year Marker (Sticky Header)**
- Position: Sticky, top: 80px (below navbar)
- Background: Inherits from page background
- Padding: 0.5rem 1rem
- Border-radius: 4px
- Box-shadow: var(--shadow)
- Color: Byers Blue (#0064AA)
- Font: 1.5rem, 700 weight

**Event Card**
- Background: var(--bg-card) - White in light mode, dark gray in dark mode
- Border: 1px solid var(--border)
- Border-radius: 8px
- Padding: 1.5rem
- Margin: 1.5rem 0
- Box-shadow: var(--shadow)
- Cursor: pointer (entire card is clickable)
- Transition: All 0.3s ease (for hover effects)

**Event Card Hover State**
- Transform: translateX(5px)
- Background: rgba(255, 140, 0, 0.1) in light mode, rgba(255, 140, 0, 0.2) in dark mode
- Box-shadow: 0 4px 15px rgba(255, 140, 0, 0.2)

**Date Badge**
- Position: Absolute, left: -3rem (outside card)
- Width/Height: 60px (50px on tablet, 45px on mobile)
- Background: var(--bg-card)
- Border: 2px solid Byers Blue (#0064AA)
- Border-radius: 50% (circular)
- Display: Flex column
- Align-items: center
- Justify-content: center
- Box-shadow: var(--shadow)
- Z-index: 5 (above connector line)

**Date Badge Content**
- Month: 0.7rem (0.65rem on mobile), Honey-Orange (#FF8C00)
- Day: 1.5rem (1.25rem on tablet, 1rem on mobile), Byers Blue (#0064AA)
- Year: 0.7rem (0.65rem on mobile), Secondary text color

**Connector Line**
- Position: Absolute, left: -1.5rem
- Top: 2.5rem (vertsically centers with date badge)
- Width: 1.5rem
- Height: 2px
- Background: Byers Blue (#0064AA)
- Z-index: 1 (below date badge)

**Event Content**
- Margin-left: 1rem (offset for date badge)
- Title: 1.25rem (1.1rem on mobile), 700 weight, Byers Blue (#0064AA)
- Category: 0.9rem, 600 weight, Honey-Orange (#FF8C00), uppercase, letter-spacing: 0.5px
- Description: 0.95rem, Secondary text color
- Truncated: 150 characters with ellipsis

**Document Indicator**
- Display: Inline-flex
- Align-items: center
- Gap: 0.5rem
- Background: rgba(255, 140, 0, 0.1)
- Padding: 0.25rem 0.75rem
- Border-radius: 20px
- Font-size: 0.85rem
- Color: Honey-Orange (#FF8C00)
- Icon: 📎 (paperclip emoji)

### Buttons

**Primary Button**
- Background: Honey-Orange (#FF8C00)
- Color: White
- Hover: Darker honey-orange (#E67E00)
- Border: None
- Border-radius: 4px
- Padding: 0.75rem 1.5rem
- Font-weight: 600
- Transition: Background 0.3s ease, transform 0.2s ease
- Hover transform: translateY(-1px)

**Secondary Button**
- Background: Byers Blue (#0064AA)
- Color: White
- Hover: Darker Byers blue (#005288)
- Border: None
- Border-radius: 4px
- Padding: 0.75rem 1.5rem
- Font-weight: 600
- Transition: Background 0.3s ease, transform 0.2s ease
- Hover transform: translateY(-1px)

### Forms

**Input Fields**
- Width: 100%
- Padding: 0.75rem
- Border: 1px solid var(--border)
- Border-radius: 4px
- Background: var(--bg-card)
- Color: var(--text)
- Transition: Border-color 0.3s ease, box-shadow 0.3s ease

**Input Focus State**
- Outline: None
- Border-color: var(--primary)
- Box-shadow: 0 0 0 3px rgba(255, 140, 0, 0.2)

**Labels**
- Display: Block
- Margin-bottom: 0.5rem
- Color: var(--text)
- Font-weight: 600

### Popups
The popup modal displays detailed information when a timeline event is clicked.

#### Popup Structure
```
┌─────────────────────────────────────────┐
│                 Overlay                   │
│  (rgba(0, 0, 0, 0.7) + backdrop blur)    │
│                                             │
│  ┌─────────────────────────────────────┐│
│  │         Popup Content                 ││
│  │  ×──────────────────────────────────││
│  │                                     ││
│  │  [Event Title]            [Date Badge]││
│  │                                     ││
│  │  Category                              ││
│  │                                     ││
│  │  Description text...                  ││
│  │                                     ││
│  │  ─────────────────────────────────  ││
│  │  Supporting Documents                 │││
│  │  ├── 📄 Document 1                    ││
│  │  ├── 📄 Document 2                    ││
│  │  └─────────────────────────────────┘│
│  │                                     ││
│  │  ─────────────────────────────────  ││
│  │                             [Close]   ││
│  └─────────────────────────────────────┘│
└─────────────────────────────────────────┘
```

#### Popup Specifications

**Modal Container**
- Position: Fixed
- Top: 0, Left: 0
- Width/Height: 100%
- Z-index: 1000
- Display: Flex, align-items: center, justify-content: center
- Opacity: 0 (hidden), 1 (visible)
- Visibility: hidden (hidden), visible (visible)
- Transition: Opacity 0.3s ease, visibility 0.3s ease

**Overlay**
- Position: Absolute
- Top/Left: 0
- Width/Height: 100%
- Background: rgba(0, 0, 0, 0.7)
- Backdrop-filter: blur(5px)

**Popup Content**
- Position: Relative
- Background: var(--bg-card)
- Border: 2px solid Honey-Orange (#FF8C00)
- Border-radius: 12px
- Padding: 2rem
- Max-width: 700px
- Width: 90% (95% on tablet, 98% on mobile)
- Max-height: 90vh
- Overflow-y: auto
- Box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3)
- Animation: popupSlideIn 0.3s ease
- Color: var(--text)

**Slide-in Animation**
```css
@keyframes popupSlideIn {
    from {
        transform: translateY(-20px);
        opacity: 0;
    }
    to {
        transform: translateY(0);
        opacity: 1;
    }
}
```

**Close Button**
- Position: Absolute, top: 1rem, right: 1rem
- Background: None
- Border: None
- Font-size: 1.5rem
- Cursor: pointer
- Color: var(--text-secondary)
- Width/Height: 36px
- Display: Flex, align-items: center, justify-content: center
- Border-radius: 50%
- Transition: Color 0.3s ease, background 0.3s ease
- Hover: Color changes to Honey-Orange (#FF8C00), background: rgba(255, 140, 0, 0.1)

**Popup Header**
- Display: Flex, justify-content: space-between, align-items: flex-start
- Margin-bottom: 1.5rem
- Padding-right: 2rem (space for close button)

**Popup Title**
- Font: 1.75rem (1.5rem on small mobile), 700 weight
- Color: Byers Blue (#0064AA)
- Margin-bottom: 0.5rem

**Popup Date Badge**
- Background: Honey-Orange (#FF8C00)
- Color: White
- Padding: 0.25rem 1rem
- Border-radius: 20px
- Font: 0.85rem, 600 weight

**Popup Category**
- Font: 1rem, 600 weight
- Color: Honey-Orange (#FF8C00)
- Text-transform: uppercase
- Letter-spacing: 0.5px
- Margin-bottom: 1rem

**Popup Description**
- Color: var(--text)
- Line-height: 1.7
- Margin-bottom: 1rem
- Font-size: 1rem

**Popup Notes**
- Color: var(--text-secondary)
- Line-height: 1.7
- Margin-bottom: 1rem
- Font-size: 0.95rem

**Media Section**
- Margin-top: 1.5rem
- Border-top: 1px solid var(--border)
- Padding-top: 1.5rem
- Display: None (shown only when documents exist)

**Media Title**
- Font: 1rem, 600 weight
- Color: Byers Blue (#0064AA)
- Margin-bottom: 1rem

**Document Links**
- Color: Honey-Orange (#FF8C00)
- Text-decoration: None
- Display: Block
- Margin-bottom: 0.5rem
- Transition: Color 0.3s ease
- Hover: Color changes to #E67E00, text-decoration: underline
- Target: _blank
- Rel: noopener noreferrer

**Popup Footer**
- Display: Flex, justify-content: flex-end
- Border-top: 1px solid var(--border)
- Padding-top: 1.5rem

## Animations & Transitions

### Timeline Events
- **Hover:** Smooth transform (translateX) and box-shadow change over 0.3s
- **Click:** Instant response with ripple effect (browser default)

### Popups
- **Open:** Fade in (opacity) + slide down (transform) over 0.3s
- **Close:** Reverse of open animation
- **Overlay:** Fade in/out over 0.3s

### Theme Toggle
- **Transition:** Background and color changes over 0.3s ease
- **Icon Change:** Instant (no animation)

### General
- All transitions use `ease` timing function
- Reduced motion preference is respected (see Accessibility)

## Layout
- **Grid System:** 12-column concept for responsiveness
- **Spacing:** Use multiples of 8px for margins and padding
- **Max Widths:** 900px for timeline, 700px for popups

## Icons
- Use simple, bold icons for actions (e.g., upload, edit, delete)
- Color: Honey-Orange (#FF8C00) for active states, gray for inactive
- Emoji icons: 📎 (paperclip), 📄 (document)

## Responsive Design

### Breakpoints
| Breakpoint | Max-Width | Description |
|------------|-----------|-------------|
| Desktop | No limit | Full layout |
| Tablet Portrait | 900px | Adjusted padding and sizing |
| Mobile | 768px | Stacked navigation, simplified layout |
| Small Mobile | 480px | Minimal padding, smallest text |

### Responsive Adjustments

**Timeline (900px breakpoint)**
- Container padding: 1rem → 0.5rem
- Wrapper padding-left: 3rem → 2.5rem
- Timeline line position: 1.5rem → 1rem
- Date badge: 60px → 50px, left: -3rem → -2.5rem
- Connector: left: -1.5rem → -1rem

**Timeline (768px breakpoint)**
- Navigation: Flex-direction column
- Year marker: Position static (not sticky)
- Date badge: 50px → 45px, left: -2.5rem → -2rem
- Event content: margin-left: 1rem → 0.5rem

**Popup (900px breakpoint)**
- Width: 90% → 95%
- Padding: 2rem → 1.5rem

**Popup (768px breakpoint)**
- Width: 95% → 98%
- Margin: 0 auto → 0 1rem
- Overlay: Background rgba(0,0,0,0.7) → rgba(0,0,0,0.8)

**Popup (480px breakpoint)**
- Title: 1.75rem → 1.5rem
- Header: Flex-direction column, padding-right: 2rem → 0
- Date badge: 40px, Day: 1rem, Month/Year: 0.65rem

## Accessibility
- Ensure color contrast meets WCAG standards (minimum 4.5:1 for normal text)
- Provide alt text for images and icons
- Support keyboard navigation:
  - Tab through all interactive elements
  - ESC to close popups
  - Focus visible on all focusable elements
- Reduced motion preference:
  - Respect `prefers-reduced-motion: reduce`
  - Remove or minimize animations for users who prefer reduced motion

## Focus States
- Outline: 2px solid Honey-Orange (#FF8C00)
- Outline-offset: 2px
- Applied to: All focusable elements (:focus-visible)

## Code Style
- Follow Django and Python best practices
- Use descriptive variable and function names
- Comment complex logic for clarity
- Use JSDoc comments for functions
- Group related CSS selectors together

## File Organization
```
static/
├── css/
│   └── style.css          # Main stylesheet with all styles
└── js/
    └── theme.js           # Theme toggle and popup functionality

templates/
└── timeline/
    └── timeline.html      # Timeline template

STYLE_GUIDE.md           # This file
TIMELINE_SCHEMA.md        # Timeline data schema
```

## Documentation
- Keep documentation up-to-date in the project root
- Use Markdown for readability
- Include code examples where helpful
- Document all major components and their specifications

## Timeline Components

### Timeline Selector
- Dropdown select element for choosing between multiple Markdown-based timelines
- Full width, max-width: 500px
- Padding: 0.75rem
- Border: 2px solid var(--border), rounds to var(--primary) on hover/focus
- Background: var(--bg-card)
- Color: var(--text)
- Border-radius: 6px
- Font-size: 1rem
- Box-shadow on focus: 0 0 0 3px rgba(255, 140, 0, 0.2)
- Persists selection in localStorage

### Timeline Navigation
- Displays headings from the parsed Markdown file
- Flexbox layout with flex-wrap
- Gap: 0.5rem
- Padding: 0.5rem 0
- Overflow-x: auto for horizontal scrolling on small screens

### Navigation Links
- Display: inline-block
- Padding: 0.375rem 0.75rem
- Border: 1px solid var(--border)
- Border-radius: 4px
- Background: var(--bg-card)
- Color: var(--text)
- Font-size: 0.875rem
- White-space: nowrap
- Transition: all 0.2s ease
- Hover: Border color → var(--primary), background → rgba(255, 140, 0, 0.1)
- Indentation based on heading level:
  - h1: No indent, font-weight: 700, font-size: 1rem
  - h2: padding-left: 1rem, font-weight: 600
  - h3: padding-left: 1.5rem, font-weight: 500

### Upload Buttons
- Display: flex, gap: 1rem
- Padding-top: 0.5rem
- Button styling:
  - Padding: 0.5rem 1rem
  - Border-radius: 6px
  - Font-size: 0.875rem
  - Transition: all 0.3s ease
  - Primary: background: var(--primary), color: white, border: 2px solid var(--primary)
  - Secondary: background: var(--bg-card), color: var(--text), border: 2px solid var(--border)
  - Hover: Primary inverts, Secondary gets primary color border

## Markdown Parsing

### Supported Formats
1. **Event Format (Legacy)**:
   ```markdown
   # Date
   **Event:** Event Title
   **Category:** category_name
   **Notes:** Event notes
   **Supporting Docs:** doc1, doc2
   ```

2. **Structured Timeline Format**:
   ```markdown
   # My Timeline Name
   
   ## Event 1
   **Date:** 2024-01-15
   **Event:** Event Title
   **Category:** contract
   **Notes:** Detailed notes
   **Description:** Additional description
   
   ## Event 2
   **Date:** 2024-03-20
   ...
   ```

3. **Section Headings**: Any heading (H1-H6) is extracted for navigation
   - H1 becomes the main timeline title
   - H2-H6 appear in the navigation bar
   - Anchors are generated from heading text (lowercase, hyphens)

### Parsing Functions
- `parse_markdown_file(file_path)`: Parse file and return headings, sections, HTML
- `extract_headings(html_content, markdown_content)`: Extract heading structure
- `get_main_heading(markdown_content, file_path)`: Get first H1 heading
- `parse_timeline_events_from_markdown(content)`: Parse events from structured format

## JavaScript Components

### Timeline Selector (initTimelineSelector)
- Listens for change events on dropdown
- Saves selection to localStorage with key 'selectedTimelinePath'
- Fetches timeline data via `/timeline/api/load-timeline/`
- Updates main heading and reloads page with new timeline file

### Collapsible Panes (initCollapsiblePanes)
- Toggles 'collapsed' class on workspace panes
- Saves state to localStorage with key `{pane_id}_state`
- Updates button text (▼ for expanded, ▶ for collapsed)
- Restores state on page load

### Theme Toggle
- Persists theme preference in localStorage with key 'theme'
- Default: 'dark'
- Toggles between 'light' and 'dark'
- Updates icon (☀️ for dark mode, 🌙 for light mode)
- Updates logo (DARK_mode_LOGO.png / light_mode_LOGO.png)

## Case Compartmentalization

### Case Model
```python
class Case(models.Model):
    name: CharField(max_length=255)
    description: TextField(blank=True)
    color: CharField(max_length=7, default='#FF8C00')
    is_active: BooleanField(default=False)
    created_at: DateTimeField(auto_now_add=True)
    updated_at: DateTimeField(auto_now=True)
    user: ForeignKey(User, on_delete=CASCADE)
```

### TimelineEvent Model Updates
```python
class TimelineEvent(models.Model):
    # ... existing fields ...
    timeline_file: CharField(max_length=512, blank=True, null=True)
    case: ForeignKey(Case, on_delete=SET_NULL, null=True, blank=True)
```

### TimelineFile Model
```python
class TimelineFile(models.Model):
    name: CharField(max_length=255)
    file_path: CharField(max_length=512)
    case: ForeignKey(Case, on_delete=CASCADE, null=True, blank=True)
    description: TextField(blank=True)
    created_at: DateTimeField(auto_now_add=True)
    updated_at: DateTimeField(auto_now=True)
    user: ForeignKey(User, on_delete=CASCADE)
```

## Version History
- **v1.0** (Initial): Basic brand colors and component styles
- **v1.1**: Added timeline and popup specifications
- **v1.2**: Added case compartmentalization and workspace redesign
- **v1.3**: Added Markdown parsing, timeline selector, and improved UI components

## License
This style guide is part of the Byers Brands ecosystem and follows the same licensing terms.
