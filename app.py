import os
import time
import secrets
import hashlib
import ctypes
from flask import Flask, render_template, request, jsonify, session
import requests

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "CHANGE_ME")

OTP_EXPIRY_SECONDS = 600
MAX_OTP_ATTEMPTS = 3

DEFAULT_PIN = 1234
DEFAULT_BALANCE = 5000.00

TOKEN = os.getenv("TEXTPLATE_API_TOKEN", "")
TEMPLATE_ID = os.getenv("TEXTPLATE_TEMPLATE_ID", "")


def load_core():
    candidates = (
        ["atm_core.dll", "./atm_core.dll"]
        if os.name == "nt"
        else ["./libatm_core.so"]
    )

    for path in candidates:
        if os.path.exists(path):
            lib = ctypes.CDLL(path)

            lib.verify_pin.argtypes = [
                ctypes.c_int,
                ctypes.c_int
            ]
            lib.verify_pin.restype = ctypes.c_int

            lib.deposit_money.argtypes = [
                ctypes.POINTER(ctypes.c_double),
                ctypes.c_double
            ]
            lib.deposit_money.restype = ctypes.c_int

            lib.withdraw_money.argtypes = [
                ctypes.POINTER(ctypes.c_double),
                ctypes.c_double
            ]
            lib.withdraw_money.restype = ctypes.c_int

            lib.change_pin.argtypes = [
                ctypes.POINTER(ctypes.c_int),
                ctypes.c_int,
                ctypes.c_int,
                ctypes.c_int
            ]
            lib.change_pin.restype = ctypes.c_int

            return lib

    raise RuntimeError("C core library not found. Build it first.")


core = load_core()


def normalize_mobile(value):
    v = (value or "").strip().replace(" ", "").replace("-", "")

    if v.startswith("+91") and len(v) == 13:
        d = v[3:]
    elif v.startswith("91") and len(v) == 12:
        d = v[2:]
    elif len(v) == 10:
        d = v
    else:
        return None

    if not (d.isdigit() and len(d) == 10 and d[0] in "6789"):
        return None

    return "+91" + d


def hash_otp(otp, salt):
    return hashlib.sha256(
        (salt + str(otp)).encode()
    ).hexdigest()


def send_sms(mobile, otp):
    if not TOKEN or not TEMPLATE_ID:
        return False, "Textplate credentials are not configured on the server."

    try:
        r = requests.post(
            "https://api.textplate.in/v1/send-sms",
            headers={
                "Authorization": f"Bearer {TOKEN}"
            },
            data={
                "mobileNumber": mobile,
                "templateId": TEMPLATE_ID,
                "otpValue": str(otp),
                "expiryValue": "10 minutes"
            },
            timeout=20
        )

    except requests.RequestException as e:
        return False, f"SMS service connection failed: {e}"

    if 200 <= r.status_code < 300:
        return True, "OTP sent successfully."

    return False, (
        f"Textplate returned HTTP {r.status_code}: "
        f"{r.text[:300]}"
    )


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/login")
def login():
    data = request.get_json(silent=True) or {}

    try:
        entered = int(data.get("pin", ""))
    except (TypeError, ValueError):
        return jsonify(
            ok=False,
            message="Enter a 4-digit PIN."
        ), 400

    pin = int(session.get("pin", DEFAULT_PIN))

    if core.verify_pin(pin, entered):
        session["pin_ok"] = True
        session["otp_verified"] = False

        return jsonify(
            ok=True,
            next="mobile"
        )

    return jsonify(
        ok=False,
        message="Incorrect PIN."
    ), 401


@app.post("/api/send-otp")
def send_otp():
    if not session.get("pin_ok"):
        return jsonify(
            ok=False,
            message="Verify your PIN first."
        ), 403

    data = request.get_json(silent=True) or {}

    mobile = normalize_mobile(data.get("mobile"))

    if not mobile:
        return jsonify(
            ok=False,
            message="Enter a valid Indian mobile number."
        ), 400

    otp = secrets.randbelow(900000) + 100000
    salt = secrets.token_hex(16)

    ok, message = send_sms(mobile, otp)

    if not ok:
        return jsonify(
            ok=False,
            message=message
        ), 502

    session.update(
        mobile=mobile,
        otp_salt=salt,
        otp_hash=hash_otp(otp, salt),
        otp_created=time.time(),
        otp_attempts=MAX_OTP_ATTEMPTS
    )

    return jsonify(
        ok=True,
        message="OTP sent successfully. It is valid for 10 minutes."
    )


@app.post("/api/verify-otp")
def verify_otp():
    if not session.get("pin_ok"):
        return jsonify(
            ok=False,
            message="Verify your PIN first."
        ), 403

    data = request.get_json(silent=True) or {}

    entered = str(data.get("otp", "")).strip()

    if not (entered.isdigit() and len(entered) == 6):
        return jsonify(
            ok=False,
            message="Enter the 6-digit OTP."
        ), 400

    created = float(
        session.get("otp_created", 0)
    )

    attempts = int(
        session.get("otp_attempts", 0)
    )

    if not created:
        return jsonify(
            ok=False,
            message="Request an OTP first."
        ), 400

    if time.time() - created > OTP_EXPIRY_SECONDS:
        return jsonify(
            ok=False,
            message="OTP expired. Request a new OTP."
        ), 400

    if attempts <= 0:
        return jsonify(
            ok=False,
            message="Too many incorrect attempts."
        ), 403

    if hash_otp(
        entered,
        session.get("otp_salt", "")
    ) != session.get("otp_hash", ""):

        attempts -= 1
        session["otp_attempts"] = attempts

        return jsonify(
            ok=False,
            message=f"Incorrect OTP. Attempts remaining: {attempts}."
        ), 401

    session["otp_verified"] = True
    session.pop("otp_hash", None)

    return jsonify(
        ok=True,
        next="menu"
    )


@app.post("/api/action")
def action():
    if not session.get("otp_verified"):
        return jsonify(
            ok=False,
            message="OTP verification required."
        ), 403

    data = request.get_json(silent=True) or {}
    name = data.get("action")

    # -------------------------
    # LOGOUT
    # -------------------------
    if name == "logout":

        # Save PIN and balance before clearing
        # the temporary login/session information.
        saved_pin = session.get(
            "pin",
            DEFAULT_PIN
        )

        saved_balance = session.get(
            "balance",
            DEFAULT_BALANCE
        )

        session.clear()

        # Restore PIN and balance
        # so they survive logout.
        session["pin"] = saved_pin
        session["balance"] = saved_balance

        return jsonify(
            ok=True,
            next="login"
        )

    # -------------------------
    # LOAD BALANCE AND PIN
    # -------------------------
    balance = ctypes.c_double(
        float(
            session.get(
                "balance",
                DEFAULT_BALANCE
            )
        )
    )

    pin = ctypes.c_int(
        int(
            session.get(
                "pin",
                DEFAULT_PIN
            )
        )
    )

    # -------------------------
    # CHECK BALANCE
    # -------------------------
    if name == "balance":
        return jsonify(
            ok=True,
            message=f"Current Balance: Rs. {balance.value:.2f}"
        )

    # -------------------------
    # DEPOSIT / WITHDRAW
    # -------------------------
    if name in ("deposit", "withdraw"):

        try:
            amount = float(
                data.get("amount")
            )

        except (TypeError, ValueError):
            return jsonify(
                ok=False,
                message="Enter a valid amount."
            ), 400

        fn = (
            core.deposit_money
            if name == "deposit"
            else core.withdraw_money
        )

        if fn(
            ctypes.byref(balance),
            amount
        ):

            session["balance"] = balance.value

            label = (
                "Deposit"
                if name == "deposit"
                else "Withdrawal"
            )

            return jsonify(
                ok=True,
                message=(
                    f"{label} successful. "
                    f"New balance: Rs. {balance.value:.2f}"
                )
            )

        return jsonify(
            ok=False,
            message="Invalid amount or insufficient balance."
        ), 400

    # -------------------------
    # CHANGE PIN
    # -------------------------
    if name == "change_pin":

        try:
            old_pin = int(
                data.get("old_pin")
            )

            new_pin = int(
                data.get("new_pin")
            )

            confirm = int(
                data.get("confirm_pin")
            )

        except (TypeError, ValueError):

            return jsonify(
                ok=False,
                message="PINs must be numbers."
            ), 400

        if core.change_pin(
            ctypes.byref(pin),
            old_pin,
            new_pin,
            confirm
        ):

            session["pin"] = pin.value

            return jsonify(
                ok=True,
                message="PIN changed successfully."
            )

        return jsonify(
            ok=False,
            message=(
                "PIN change failed. "
                "Check the old PIN, 4-digit format "
                "and confirmation."
            )
        ), 400

    return jsonify(
        ok=False,
        message="Unknown action."
    ), 400


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(
            os.getenv("PORT", "5000")
        ),
        debug=False
    )