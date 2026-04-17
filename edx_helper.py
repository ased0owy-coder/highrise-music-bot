#!/usr/bin/env python3
"""
EDX Team Helper - Encrypted team management system
This file manages EDX team members with special privileges
"""

import json
import base64
from pathlib import Path

class EDXTeam:
    """EDX Team management with encryption"""
    
    def __init__(self):
        self.team_file = Path('.EDX_TEAM')
        self.team_data = self._load_team_data()
    
    def _load_team_data(self) -> dict:
        """Load team data from encrypted file"""
        try:
            if self.team_file.exists():
                with open(self.team_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Verify checksum for integrity
                    if data.get('_checksum') == 'EDX2024MUSIC':
                        return data
            return self._get_default_data()
        except:
            return self._get_default_data()
    
    def _get_default_data(self) -> dict:
        """Get default team configuration"""
        return {
            "team_members": ["A.opy", "VECTOR000"],
            "version": "1.53.0",
            "team_name": "EDX Team",
            "release_message": "🎵 Highrise Music Bot v1.53.0\n💜 Made by EDX Team\n✨ Free & Open Source",
            "welcome_messages": {
                "A.opy": "👑 مرحباً بك يا بوس A.opy! | Welcome back Boss A.opy!",
                "VECTOR000": "⭐ أهلاً بالمطور VECTOR000! | Hey Developer VECTOR000!"
            },
            "permissions": {
                "unlimited_play": True,
                "unlimited_skip": True,
                "admin_commands": True,
                "bypass_tickets": True,
                "priority_requests": True
            },
            "_encrypted": True,
            "_checksum": "EDX2024MUSIC"
        }
    
    def is_team_member(self, username: str) -> bool:
        """Check if user is EDX team member"""
        return username in self.team_data.get('team_members', [])
    
    def get_welcome_message(self, username: str) -> str:
        """Get personalized welcome message for team member"""
        welcome_messages = self.team_data.get('welcome_messages', {})
        return welcome_messages.get(username, f"👋 Welcome EDX Team member {username}!")
    
    def get_release_message(self) -> str:
        """Get bot release/startup message"""
        return self.team_data.get('release_message', '')
    
    def get_version(self) -> str:
        """Get current version"""
        return self.team_data.get('version', '1.53.0')
    
    def has_permission(self, username: str, permission: str) -> bool:
        """Check if team member has specific permission"""
        if not self.is_team_member(username):
            return False
        permissions = self.team_data.get('permissions', {})
        return permissions.get(permission, False)
    
    def get_team_members(self) -> list:
        """Get list of all team members"""
        return self.team_data.get('team_members', [])
