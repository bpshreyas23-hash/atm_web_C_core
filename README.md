# ATM Web + C Core

Mobile-friendly ATM demo: PIN -> mobile number -> real Textplate SMS OTP -> ATM menu.

The ATM operations are implemented in C (`atm_core.c`). Flask provides the web interface and keeps the SMS API token on the server.

## Local Windows run

1. Install Python and GCC.
2. Open CMD in this folder.
3. Run `start_atm.bat`.
4. Enter your NEW Textplate token and template ID when asked.
5. Open `http://127.0.0.1:5000` if it does not open automatically.
6. Demo PIN is `1234`; starting balance is Rs. 5000.

The Textplate API used is `POST https://api.textplate.in/v1/send-sms` with Bearer auth and the form fields `mobileNumber`, `templateId`, `otpValue`, and `expiryValue`, as documented by Textplate.

## Important

Your previously posted API token should be revoked/regenerated. Do not put a real token in the code or upload it to GitHub.

## Share with phones/friends

`127.0.0.1` only works on your own computer. To give a teacher/friend a clickable link, deploy this project to a Python host (for example Render) and set these environment variables there:

- TEXTPLATE_API_TOKEN
- TEXTPLATE_TEMPLATE_ID
- FLASK_SECRET_KEY

The host must build the C shared library using:
`gcc -shared -fPIC -O2 -o libatm_core.so atm_core.c`

and start with:
`gunicorn app:app`

A public deployment should use HTTPS and rate limiting. This is a college/demo ATM simulator, not a real banking system.
