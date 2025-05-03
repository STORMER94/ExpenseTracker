import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import url_for

# Email configuration
EMAIL_USERNAME = "prathamesh.k94@outlook.com"
EMAIL_PASSWORD = "Neha!123456"
EMAIL_SERVER = "smtp-mail.outlook.com"
EMAIL_PORT = 587

def send_password_reset_email(user):
    token = user.get_reset_password_token()
    reset_url = url_for('reset_password', token=token, _external=True)
    
    # For development/debugging, print the reset link to console
    print(f"Password reset link (DEVELOPMENT ONLY): {reset_url}")
    
    # Set up email content
    msg = MIMEMultipart("alternative")
    msg['Subject'] = "Reset Your Password - Expense Manager"
    msg['From'] = EMAIL_USERNAME
    msg['To'] = user.email
    
    # Create HTML version of email
    html_content = f"""
    <html>
    <body>
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
    </body>
    </html>
    """
    
    # Create plain text version of email
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
    
    # Attach both versions to the email
    part1 = MIMEText(plain_content, "plain")
    part2 = MIMEText(html_content, "html")
    msg.attach(part1)
    msg.attach(part2)
    
    try:
        # Connect to the SMTP server and send the email
        server = smtplib.SMTP(EMAIL_SERVER, EMAIL_PORT)
        server.starttls()
        server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
        server.sendmail(EMAIL_USERNAME, user.email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Email sending error: {e}")
        return False