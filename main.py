from fastapi import FastAPI, HTTPException
import dns.asyncresolver
import smtplib
import re
import asyncio

app = FastAPI()

# 1. Syntax validation using regular expression
def validate_syntax(email):
    regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(regex, email))

# 2. Async domain check using only MX records
async def validate_mx_record(email):
    domain = email.split('@')[1]
    try:
        # Perform DNS lookup for MX records asynchronously
        await dns.asyncresolver.resolve(domain, 'MX')
        return True
    except (dns.asyncresolver.NoAnswer, dns.asyncresolver.NXDOMAIN):
        return False

# 3. Minimal SMTP check (only to check if the server is responsive)
async def verify_email_smtp(email):
    domain = email.split('@')[1]
    try:
        # Get MX records asynchronously
        mx_records = await dns.asyncresolver.resolve(domain, 'MX')
        mx_record = str(mx_records[0].exchange)

        # Connect to the SMTP server with a very short timeout (1 second)
        with smtplib.SMTP(mx_record, timeout=1) as server:
            server.set_debuglevel(0)
            server.helo()  # Send 'HELO' command
            server.mail('youremail@yourdomain.com')  # Send MAIL FROM
            code, _ = server.rcpt(email)  # Send RCPT TO

            # If the SMTP server responds with 250, the email is valid
            return code == 250
    except Exception:
        return False

# FastAPI endpoint for verifying the email
@app.get("/verify_email")
async def verify_email(email: str):
    # Step 1: Validate email syntax (basic regex check)
    if not validate_syntax(email):
        raise HTTPException(status_code=400, detail="Invalid email syntax")

    # Step 2: Check if the domain has MX records (async)
    domain_valid = await validate_mx_record(email)
    if not domain_valid:
        raise HTTPException(status_code=400, detail="No MX records found for domain")

    # Step 3: Verify email via SMTP (check if email exists on the server)
    email_exists = await verify_email_smtp(email)
    if email_exists:
        return {"status": "success", "message": "Email exists"}
    else:
        raise HTTPException(status_code=404, detail="Email does not exist")
