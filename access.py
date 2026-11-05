"""
Client upload lock.

The public app only shows demo data. Uploading real scorecards is unlocked
with a password, so a DSP can see the demo but can't run its own data
without going through Meschac.

The password is NOT in this code. It's set in Streamlit Cloud under
Settings > Secrets as:

    UPLOAD_PASSWORD = "your-password-here"

If no password is set (for example when running locally), uploads stay off.
"""

import hmac

import streamlit as st

CONTACT_LINE = "Want to see this on your own DAs? Message Meschac Goredji on LinkedIn for a free trial."


def uploads_unlocked():
    """True once the correct password has been entered in this browser session."""
    try:
        secret = st.secrets["UPLOAD_PASSWORD"]
    except Exception:
        return False  # no password set, so the app stays demo-only

    if st.session_state.get("uploads_unlocked"):
        return True

    with st.sidebar.expander("🔒 Client uploads"):
        entered = st.text_input("Password", type="password", key="upload_password")
        if entered:
            # compare_digest compares safely, without leaking how close a guess was
            if hmac.compare_digest(entered, str(secret)):
                st.session_state["uploads_unlocked"] = True
                st.rerun()
            else:
                st.error("Wrong password.")
    return False
