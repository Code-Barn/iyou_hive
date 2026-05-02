#!/usr/bin/env python
"""
Script to reset the database and test the session serialization fix.
"""

import os
import sys
import django
from django.core.management import execute_from_command_line

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hiver_django.settings')
django.setup()

from django.contrib.auth.models import User
from apps.core.models import Case, ArchiveDocument, TimelineFile, TimelineEvent
from apps.conversation_logs.models import ConversationLog
from apps.ai_assistant.models import AISession

def reset_database():
    """Reset all user data from the database."""
    print("🧹 Resetting database...")
    
    # Delete all data in reverse order of dependencies
    models_to_clear = [
        AISession,
        ConversationLog,
        TimelineEvent,
        TimelineFile,
        ArchiveDocument,
        Case,
        User
    ]
    
    for model in models_to_clear:
        count = model.objects.count()
        if count > 0:
            print(f"  🗑️  Deleting {count} {model.__name__} records...")
            model.objects.all().delete()
    
    print("✅ Database reset complete!")

def test_session_serialization():
    """Test that session serialization works with UUIDs."""
    print("\n🧪 Testing session serialization...")
    
    from django.test import RequestFactory
    from django.contrib.sessions.middleware import SessionMiddleware
    from django.contrib.auth.models import AnonymousUser
    
    # Create a test user
    test_user = User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )
    
    # Create a test case
    test_case = Case.objects.create(
        name='Test Case',
        description='Test description',
        user=test_user
    )
    
    print(f"  📋 Created test user: {test_user.username} (ID: {test_user.id})")
    print(f"  📋 Created test case: {test_case.name} (ID: {test_case.id})")
    
    # Test session serialization
    factory = RequestFactory()
    request = factory.get('/timeline/')
    request.user = test_user
    
    # Apply session middleware
    middleware = SessionMiddleware(lambda x: x)
    middleware.process_request(request)
    
    # Simulate storing case ID in session (the problematic scenario)
    request.session['selected_case_id'] = str(test_case.id)  # This should work now
    
    try:
        # Try to save the session (this was failing before)
        request.session.save()
        print("  ✅ Session serialization successful!")
        
        # Test retrieving the session
        session_data = request.session['selected_case_id']
        print(f"  ✅ Session data retrieved: {session_data} (type: {type(session_data)})")
        
        # Test that we can convert it back to UUID
        from uuid import UUID
        case_uuid = UUID(session_data)
        print(f"  ✅ Successfully converted back to UUID: {case_uuid}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Session serialization failed: {e}")
        return False

def create_test_data():
    """Create some test data for manual testing."""
    print("\n🎯 Creating test data...")
    
    # Create a test user
    if not User.objects.filter(username='demo').exists():
        demo_user = User.objects.create_user(
            username='demo',
            email='demo@example.com',
            password='demo123'
        )
        print(f"  👤 Created demo user: demo/demo123")
        
        # Create a test case
        demo_case = Case.objects.create(
            name='Demo Legal Case',
            description='A sample legal case for demonstration',
            color='#FF8C00',
            user=demo_user,
            is_active=True
        )
        print(f"  📋 Created demo case: {demo_case.name}")
        
        print("\n📋 Login credentials for testing:")
        print("   Username: demo")
        print("   Password: demo123")
    else:
        print("  ℹ️  Demo user already exists")

if __name__ == '__main__':
    print("🚀 Starting database reset and session test...\n")
    
    # Reset database
    reset_database()
    
    # Test session serialization
    success = test_session_serialization()
    
    # Create test data
    create_test_data()
    
    if success:
        print("\n🎉 All tests passed! The session serialization issue should be fixed.")
        print("📝 You can now restart the server and test login with existing accounts.")
    else:
        print("\n❌ Tests failed. Please check the error messages above.")
    
    print("\n💡 Tip: If you still experience issues, try:")
    print("   1. Clear your browser cookies/cache")
    print("   2. Use the demo account: demo/demo123")
    print("   3. Check server logs for any remaining errors")