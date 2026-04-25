# Testing Checklist for Hiver

This checklist ensures all features work correctly before deployment.

## 📋 Manual Testing

### Timeline Selection Dropdown
- [ ] **Multiple Markdown Files**: Upload 2-3 different Markdown timeline files
- [ ] **Dropdown Population**: Verify all timeline files appear in the dropdown
- [ ] **Selection Persistence**: Select a timeline, refresh page, verify it stays selected
- [ ] **Heading Display**: Verify main heading updates when selecting different timelines
- [ ] **Navigation Links**: Click on heading navigation links, verify smooth scrolling
- [ ] **localStorage**: Check browser localStorage for `selectedTimelinePath` entry

### Collapsible Panes
- [ ] **Archive Pane**: Click collapse button, verify pane collapses
- [ ] **AI Pane**: Click collapse button, verify pane collapses
- [ ] **State Persistence**: Collapse, refresh page, verify state is restored
- [ ] **localStorage**: Check browser localStorage for `{pane_id}_state` entries
- [ ] **Button Icons**: Verify ▼ (expanded) and ▶ (collapsed) icons toggle correctly
- [ ] **Smooth Animation**: Verify collapse/expand has smooth transition

### Dark/Light Mode Toggle
- [ ] **Toggle Button**: Click theme toggle, verify theme switches
- [ ] **Icon Change**: Verify ☀️ (dark mode) ↔ 🌙 (light mode) icon changes
- [ ] **Logo Change**: Verify logo switches between DARK_mode_LOGO.png and light_mode_LOGO.png
- [ ] **CSS Variables**: Verify all colors update via CSS variables
- [ ] **localStorage**: Check browser localStorage for `theme` entry ('dark' or 'light')
- [ ] **Default**: Verify dark mode is default on first visit
- [ ] **All Views**: Test toggle on timeline, archive, AI assistant, and case pages

### Case Management
- [ ] **Case Creation**: Create a new case with name, description, color
- [ ] **Case List**: Verify new case appears in case list
- [ ] **Case Details**: Click on case, verify details page loads
- [ ] **Switch Case**: Click "Switch to Case", verify session updates
- [ ] **Case Deletion**: Create test case, delete it, verify confirmation required
- [ ] **Data Isolation**: Switch to case, verify only that case's data shows in timeline
- [ ] **Active Case Badge**: Verify only one case shows as "Active"

### Authentication
- [ ] **Standard Login**: Login with username/password
- [ ] **DID Login Available**: Verify "Sign In with DID" button appears when Rust-DID available
- [ ] **Logout**: Verify logout redirects to timeline
- [ ] **Session Persistence**: Login, refresh page, verify still logged in
- [ ] **Login Required**: Try to access timeline without login, verify redirect to login page

### Markdown Parsing
- [ ] **Heading Extraction**: Create markdown with H1-H6 headings, verify all appear in navigation
- [ ] **Event Parsing**: Upload markdown with structured events, verify events created
- [ ] **Table Support**: Create markdown with table, verify it renders (if python-markdown available)
- [ ] **List Support**: Create markdown with lists, verify they render correctly
- [ ] **Image Support**: Create markdown with image, verify image URL extracted
- [ ] **Error Handling**: Upload empty file, verify user-friendly error message
- [ ] **Malformed Markdown**: Upload file with no headings, verify warning shown

### Upload Functionality
- [ ] **Markdown Upload**: Upload .md file, verify events parsed and created
- [ ] **PDF Upload**: Upload PDF, verify auto-conversion to markdown starts
- [ ] **Image Upload**: Upload image, verify it saves correctly
- [ ] **Case Association**: Upload with case selected, verify file associated with case

### Popup Modal
- [ ] **Open Popup**: Click timeline event, verify popup opens
- [ ] **Close Button**: Click X button, verify popup closes
- [ ] **ESC Key**: Open popup, press ESC, verify it closes
- [ ] **Click Outside**: Click outside popup, verify it closes
- [ ] **Document Display**: Upload event with documents, verify documents show in popup
- [ ] **AI Button**: Verify "Ask AI About This" button appears and is clickable

## 🔧 Technical Testing

### Database Integrity
- [ ] **Migrations**: Run `python manage.py migrate`, verify no errors
- [ ] **Case Model**: Verify Case model created with all fields
- [ ] **TimelineEvent**: Verify timeline_file and case fields added
- [ ] **TimelineFile**: Verify TimelineFile model created
- [ ] **Relationships**: Verify FK relationships work (Case → User, TimelineFile → Case, etc.)

### URL Routing
- [ ] **URLs**: Run `python manage.py check`, verify no URL errors
- [ ] **Login URL**: Verify `/accounts/login/` accessible
- [ ] **DID Login URL**: Verify `/accounts/did/login/` accessible
- [ ] **Case URLs**: Verify `/core/cases/`, `/core/cases/create/` accessible
- [ ] **Timeline URLs**: Verify `/timeline/`, `/timeline/upload/` accessible
- [ ] **Archive URLs**: Verify `/archive/`, `/archive/upload/` accessible

### JavaScript Functionality
- [ ] **theme.js**: Verify all functions defined (initCaseSelector, initCollapsiblePanes, initTimelineSelector)
- [ ] **No Console Errors**: Open browser dev tools, verify no console errors on page load
- [ ] **Event Listeners**: Verify all button clicks and form submissions work
- [ ] **API Calls**: Test `/timeline/api/load-timeline/`, verify it returns valid JSON

### Error Handling
- [ ] **404 Pages**: Visit non-existent URL, verify custom 404 page (if configured)
- [ ] **500 Errors**: Cause server error, verify error doesn't crash server
- [ ] **Permission Denied**: Try to access another user's case, verify access denied
- [ ] **Login Required**: Visit protected view without auth, verify redirect to login

## 📝 API Testing

### Case API
```bash
# Test authentication required
curl -v http://localhost:8000/core/api/cases/

# Test with authentication (replace with actual cookie)
curl -H "Cookie: sessionid=..." http://localhost:8000/core/api/cases/
```

### Timeline API
```bash
# Load timeline file
curl -v http://localhost:8000/timeline/api/load-timeline/?file_path=/path/to/file.md

# Get timeline headings
curl -v http://localhost:8000/timeline/api/timeline-headings/
```

### Expected Responses
- [ ] **Success**: 200 OK with valid JSON
- [ ] **Authentication Required**: 302 redirect to login (for protected endpoints)
- [ ] **Invalid Request**: 400 Bad Request for missing parameters
- [ ] **Not Found**: 404 for non-existent resources
- [ ] **Server Error**: 500 only for unexpected errors

## 📊 Browser Testing

- [ ] **Chrome**: Test all features in latest Chrome
- [ ] **Firefox**: Test all features in latest Firefox
- [ ] **Safari**: Test all features in latest Safari (if available)
- [ ] **Mobile Chrome**: Test on Android iOS
- [ ] **Mobile Safari**: Test on iPhone/iPad

## 🎯 Performance Testing

- [ ] **Page Load**: Timeline with 50+ events loads in < 2 seconds
- [ ] **Markdown Parsing**: Large markdown file (1MB) parses in < 1 second
- [ ] **Image Loading**: Images load with lazy loading, no layout shift
- [ ] **Collapsible Panes**: Collapse/expand animation is smooth (60fps)
- [ ] **Theme Toggle**: Theme switch is instant (< 100ms)

## ✅ Deployment Readiness

- [ ] **All Tests Pass**: Run through entire checklist, all items checked
- [ ] **No Console Errors**: No JavaScript errors in browser console
- [ ] **System Check**: `python manage.py check` shows no issues
- [ ] **Migrations Applied**: All migrations ran successfully
- [ ] **Static Files**: `python manage.py collectstatic` works without errors
- [ ] **Environment Variables**: All required env vars set (SECRET_KEY, DATABASE, etc.)

## 📅 Scheduled Testing

- [ ] **Weekly**: Run through critical path (login → create case → upload timeline → view events)
- [ ] **Monthly**: Full regression test using this checklist
- [ ] **After Changes**: Run tests for any modified functionality

---

**Last Updated**: {{ date }}
**Tester**: _______________
**Status**: [ ] All Pass [ ] Minor Issues [ ] Major Issues
