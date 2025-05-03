import os
import sys
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
from flask import current_app, url_for

def send_password_reset_email(user):
    token = user.get_reset_password_token()
    reset_url = url_for('reset_password', token=token, _external=True)
    
    # Check if SendGrid API key is available
    sendgrid_key = os.environ.get('SENDGRID_API_KEY')
    if not sendgrid_key:
        # For development, print the reset link to console
        print(f"Password reset link (DEVELOPMENT ONLY): {reset_url}")
        return True
    
    # If SendGrid API key exists, send an actual email
    from_email = Email("noreply@expensetracker.com")
    to_email = To(user.email)
    subject = "Reset Your Password - Expense Manager"
    
    # Create email content with reset link
    html_content = f"""
    <h2>Reset Your Password</h2>
    <p>Dear {user.first_name},</p>
    <p>You have requested to reset your password. Please click the button below to create a new password:</p>
    <p>
        <a href="{reset_url}" style="display: inline-block; background-color: #007bff; color: white; 
                                    font-family: Arial, sans-serif; font-weight: bold; text-decoration: none; 
                                    padding: 10px 18px; border-radius: 5px;">
            Reset Password
        </a>
    </p>
    <p>Or copy and paste this link into your browser:</p>
    <p>{reset_url}</p>
    <p>This link is valid for 10 minutes.</p>
    <p>If you did not request a password reset, please ignore this email and your password will remain unchanged.</p>
    <p>Regards,<br>The Expense Manager Team</p>
    """
    
    plain_content = f"""
    Reset Your Password

    Dear {user.first_name},

    You have requested to reset your password. Please click the link below to create a new password:

    {reset_url}

    This link is valid for 10 minutes.

    If you did not request a password reset, please ignore this email and your password will remain unchanged.

    Regards,
    The Expense Manager Team
    """
    
    message = Mail(
        from_email=from_email,
        to_emails=to_email,
        subject=subject
    )
    
    message.content = Content("text/html", html_content)
    
    try:
        sg = SendGridAPIClient(sendgrid_key)
        sg.send(message)
        return True
    except Exception as e:
        print(f"SendGrid error: {e}")
        return False