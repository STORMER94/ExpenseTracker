import os
from flask import url_for, flash, current_app

def send_password_reset_email(user):
    token = user.get_reset_password_token()
    reset_url = url_for('reset_password', token=token, _external=True)
    
    # For development/debugging, print the reset link to console
    print(f"\n=== IMPORTANT ===")
    print(f"Password reset link for {user.email} (Copy and use this link for testing):")
    print(f"{reset_url}")
    print(f"=== END ===\n")
    
    # In a production environment, you would send an actual email here
    # For now, we'll just use console output to get the password reset link
    
    return True