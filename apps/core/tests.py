# Copyright (C) 2026 Byers Brands, LLC
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.core.models import Case


class CaseModelTest(TestCase):
    """Tests for the Case model."""
    
    def setUp(self):
        self.User = get_user_model()
        self.user = self.User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
    
    def test_create_case(self):
        """Test creating a case."""
        case = Case.objects.create(
            name='Test Case',
            user=self.user,
            description='Test description'
        )
        self.assertEqual(case.name, 'Test Case')
        self.assertEqual(case.user, self.user)
        self.assertFalse(case.is_active)
    
    def test_get_default_case(self):
        """Test getting default case for a user."""
        # Test that get_default_case returns None when no cases exist
        case = Case.get_default_case(self.user)
        self.assertIsNone(case)
        
        # Test that it returns the most recent case when cases exist
        case1 = Case.objects.create(
            name='First Case',
            user=self.user,
            description='First case'
        )
        case2 = Case.objects.create(
            name='Second Case',
            user=self.user,
            description='Second case'
        )
        
        # get_default_case should return the most recently updated case
        returned_case = Case.get_default_case(self.user)
        self.assertIsNotNone(returned_case)
        self.assertEqual(returned_case.name, 'Second Case')
    
    def test_case_unique_together(self):
        """Test that case name must be unique per user."""
        Case.objects.create(name='Unique Case', user=self.user)
        with self.assertRaises(Exception):
            Case.objects.create(name='Unique Case', user=self.user)
    
    def test_case_event_count(self):
        """Test event count property."""
        case = Case.objects.create(name='Test Case', user=self.user)
        self.assertEqual(case.event_count, 0)
    
    def test_case_document_count(self):
        """Test document count property."""
        case = Case.objects.create(name='Test Case', user=self.user)
        self.assertEqual(case.document_count, 0)


class CaseCompartmentalizationTest(TestCase):
    """Tests for case compartmentalization."""
    
    def setUp(self):
        self.User = get_user_model()
        self.user1 = self.User.objects.create_user(
            username='user1',
            password='testpass123'
        )
        self.user2 = self.User.objects.create_user(
            username='user2',
            password='testpass123'
        )
        self.case1 = Case.objects.create(name='Case 1', user=self.user1)
        self.case2 = Case.objects.create(name='Case 2', user=self.user1)
        self.case3 = Case.objects.create(name='Case 3', user=self.user2)
    
    def test_user_can_only_see_own_cases(self):
        """Test that users can only see their own cases."""
        user1_cases = Case.objects.filter(user=self.user1)
        user2_cases = Case.objects.filter(user=self.user2)
        
        self.assertEqual(user1_cases.count(), 2)
        self.assertEqual(user2_cases.count(), 1)
    
    def test_case_isolation(self):
        """Test that cases are isolated between users."""
        self.assertFalse(self.case1.can_access(self.user2))
        self.assertTrue(self.case1.can_access(self.user1))
        self.assertTrue(self.case3.can_access(self.user2))