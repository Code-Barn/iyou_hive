#!/usr/bin/env python
"""
Simple test script for Add Event functionality
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import RequestFactory, Client
from django.contrib.auth.models import User
from django.contrib.sessions.middleware import SessionMiddleware
from apps.core.models import Case
from apps.timeline.views import create_event

def test_add_event_functionality():
    print("🧪 Testing Add Event functionality...")
    
    # Create test user and case (use unique username with timestamp)
    import time
    timestamp = int(time.time())
    user = User.objects.create_user(username=f'testuser_{timestamp}', password='test123')
    case = Case.objects.create(name=f'Test Case {timestamp}', user=user)
    print(f"✅ Created test user: {user.username}")
    print(f"✅ Created test case: {case.name}")
    
    # Test with RequestFactory
    factory = RequestFactory()
    request = factory.post('/timeline/create-event/', {
        'date': '2023-01-15',
        'event': 'Test Event',
        'category': 'other',
        'description': 'Test description',
        'supporting_docs': ''
    })
    
    # Add user and session
    request.user = user
    
    # Add session with case ID
    middleware = SessionMiddleware(lambda x: x)
    middleware.process_request(request)
    request.session['selected_case_id'] = str(case.id)
    request.session.save()
    
    # Test the view
    try:
        response = create_event(request)
        print(f"✅ View executed successfully")
        print(f"Status: {response.status_code}")
        print(f"Content-Type: {response.get('Content-Type', 'unknown')}")
        
        if response.status_code == 200:
            import json
            data = json.loads(response.content)
            print(f"Response data: {data}")
            if data.get('status') == 'success':
                print("🎉 Add Event functionality is working!")
                return True
            else:
                print(f"❌ Error in response: {data.get('error', 'Unknown error')}")
                return False
        else:
            print(f"❌ Unexpected status code: {response.status_code}")
            print(f"Response: {response.content.decode()[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ Exception occurred: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_csrf_token():
    """Test CSRF token functionality"""
    print("\n🔒 Testing CSRF token...")
    
    # Test with Django test client (handles CSRF automatically)
    client = Client()
    
    # Create and login user (use unique username with timestamp)
    import time
    from django.contrib.auth.models import User
    timestamp = int(time.time())
    User.objects.create_user(username=f'csrfuser_{timestamp}', password='csrf123')
    logged_in = client.login(username=f'csrfuser_{timestamp}', password='csrf123')
    print(f"✅ Login successful: {logged_in}")
    
    # Create case for user
    from apps.core.models import Case
    user_obj = User.objects.get(username=f'csrfuser_{timestamp}')
    case = Case.objects.create(name=f'CSRF Test Case {timestamp}', user=user_obj)
    
    # Set session
    session = client.session
    session['selected_case_id'] = str(case.id)
    session.save()
    
    # Test POST request
    try:
        response = client.post('/timeline/create-event/', {
            'date': '2023-02-20',
            'event': 'CSRF Test Event',
            'category': 'other',
            'description': 'Testing CSRF',
            'supporting_docs': ''
        })
        
        print(f"✅ Request sent successfully")
        print(f"Status: {response.status_code}")
        print(f"Content-Type: {response.get('Content-Type', 'unknown')}")
        
        if response.status_code == 200:
            import json
            data = json.loads(response.content)
            print(f"Response: {data}")
            if data.get('status') == 'success':
                print("🎉 CSRF functionality is working!")
                return True
            else:
                print(f"❌ Error in CSRF test: {data.get('error', 'Unknown error')}")
                return False
        else:
            print(f"❌ CSRF test failed with status: {response.status_code}")
            print(f"Response: {response.content.decode()[:300]}")
            return False
            
    except Exception as e:
        print(f"❌ CSRF test exception: {e}")
        return False

if __name__ == '__main__':
    print("🚀 Starting Add Event functionality tests...\n")
    
    success1 = test_add_event_functionality()
    success2 = test_csrf_token()
    
    if success1 and success2:
        print("\n🎉 All tests passed! Add Event functionality is working correctly.")
    else:
        print("\n❌ Some tests failed. Please check the error messages above.")
        print("\n💡 Troubleshooting tips:")
        print("   1. Check that you're logged in when testing")
        print("   2. Ensure a case is selected (session['selected_case_id'])")
        print("   3. Verify CSRF token is being sent correctly")
        print("   4. Check server logs for detailed error messages")