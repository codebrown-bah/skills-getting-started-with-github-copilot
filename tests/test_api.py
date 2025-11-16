"""
Tests for the High School Management System API
"""
import pytest
from fastapi.testclient import TestClient


class TestBasicEndpoints:
    """Test basic API functionality"""
    
    def test_root_redirect(self, client):
        """Test that root endpoint redirects to static HTML"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert "/static/index.html" in response.headers["location"]
    
    def test_get_activities(self, client, reset_activities):
        """Test getting all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        
        data = response.json()
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Gym Class" in data
        
        # Verify structure
        chess_club = data["Chess Club"]
        assert "description" in chess_club
        assert "schedule" in chess_club
        assert "max_participants" in chess_club
        assert "participants" in chess_club
        assert chess_club["max_participants"] == 12


class TestSignupFunctionality:
    """Test activity signup functionality"""
    
    def test_signup_success(self, client, reset_activities):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Chess Club/signup?email=test@mergington.edu"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "test@mergington.edu" in data["message"]
        assert "Chess Club" in data["message"]
        
        # Verify participant was added
        activities_response = client.get("/activities")
        activities = activities_response.json()
        assert "test@mergington.edu" in activities["Chess Club"]["participants"]
    
    def test_signup_nonexistent_activity(self, client, reset_activities):
        """Test signup for non-existent activity"""
        response = client.post(
            "/activities/Nonexistent Activity/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404
        
        data = response.json()
        assert data["detail"] == "Activity not found"
    
    def test_signup_multiple_participants(self, client, reset_activities):
        """Test multiple people can sign up for the same activity"""
        # Sign up first person
        response1 = client.post(
            "/activities/Chess Club/signup?email=student1@mergington.edu"
        )
        assert response1.status_code == 200
        
        # Sign up second person
        response2 = client.post(
            "/activities/Chess Club/signup?email=student2@mergington.edu"
        )
        assert response2.status_code == 200
        
        # Verify both are registered
        activities_response = client.get("/activities")
        activities = activities_response.json()
        participants = activities["Chess Club"]["participants"]
        assert "student1@mergington.edu" in participants
        assert "student2@mergington.edu" in participants
    
    def test_signup_with_special_characters(self, client, reset_activities):
        """Test signup with URL-encoded activity names"""
        response = client.post(
            "/activities/Programming%20Class/signup?email=test@mergington.edu"
        )
        assert response.status_code == 200


class TestUnregisterFunctionality:
    """Test activity unregister functionality"""
    
    def test_unregister_success(self, client, reset_activities):
        """Test successful unregister from an activity"""
        # First sign up
        client.post("/activities/Chess Club/signup?email=test@mergington.edu")
        
        # Then unregister
        response = client.delete(
            "/activities/Chess Club/unregister?email=test@mergington.edu"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "test@mergington.edu" in data["message"]
        assert "Chess Club" in data["message"]
        
        # Verify participant was removed
        activities_response = client.get("/activities")
        activities = activities_response.json()
        assert "test@mergington.edu" not in activities["Chess Club"]["participants"]
    
    def test_unregister_not_registered(self, client, reset_activities):
        """Test unregister when student is not registered"""
        response = client.delete(
            "/activities/Chess Club/unregister?email=notregistered@mergington.edu"
        )
        assert response.status_code == 400
        
        data = response.json()
        assert data["detail"] == "Student is not registered for this activity"
    
    def test_unregister_nonexistent_activity(self, client, reset_activities):
        """Test unregister from non-existent activity"""
        response = client.delete(
            "/activities/Nonexistent Activity/unregister?email=test@mergington.edu"
        )
        assert response.status_code == 404
        
        data = response.json()
        assert data["detail"] == "Activity not found"
    
    def test_unregister_existing_participant(self, client, reset_activities):
        """Test unregister an existing participant"""
        response = client.delete(
            "/activities/Chess Club/unregister?email=michael@mergington.edu"
        )
        assert response.status_code == 200
        
        # Verify participant was removed
        activities_response = client.get("/activities")
        activities = activities_response.json()
        assert "michael@mergington.edu" not in activities["Chess Club"]["participants"]
        # But daniel should still be there
        assert "daniel@mergington.edu" in activities["Chess Club"]["participants"]


class TestDataIntegrity:
    """Test data integrity and edge cases"""
    
    def test_participant_count_updates(self, client, reset_activities):
        """Test that participant counts are accurate"""
        # Get initial count
        response = client.get("/activities")
        initial_count = len(response.json()["Chess Club"]["participants"])
        
        # Add participant
        client.post("/activities/Chess Club/signup?email=test@mergington.edu")
        
        # Check count increased
        response = client.get("/activities")
        new_count = len(response.json()["Chess Club"]["participants"])
        assert new_count == initial_count + 1
        
        # Remove participant
        client.delete("/activities/Chess Club/unregister?email=test@mergington.edu")
        
        # Check count decreased
        response = client.get("/activities")
        final_count = len(response.json()["Chess Club"]["participants"])
        assert final_count == initial_count
    
    def test_activity_structure_preserved(self, client, reset_activities):
        """Test that activity structure is preserved after operations"""
        # Perform some operations
        client.post("/activities/Chess Club/signup?email=test@mergington.edu")
        client.delete("/activities/Chess Club/unregister?email=test@mergington.edu")
        
        # Check structure is still intact
        response = client.get("/activities")
        activities = response.json()
        
        chess_club = activities["Chess Club"]
        required_fields = ["description", "schedule", "max_participants", "participants"]
        for field in required_fields:
            assert field in chess_club
        
        assert isinstance(chess_club["participants"], list)
        assert isinstance(chess_club["max_participants"], int)
    
    def test_all_activities_have_required_fields(self, client, reset_activities):
        """Test that all activities have required fields"""
        response = client.get("/activities")
        activities = response.json()
        
        required_fields = ["description", "schedule", "max_participants", "participants"]
        
        for activity_name, activity_data in activities.items():
            for field in required_fields:
                assert field in activity_data, f"Activity {activity_name} missing field {field}"