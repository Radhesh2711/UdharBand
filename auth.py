import streamlit as st

import db


def require_login() -> str:
    """Block the app until the user is logged in. Returns the user's email."""
    # Dev mode: use a configured email for local testing
    try:
        dev_email = st.secrets["dev_email"]
    except (KeyError, FileNotFoundError):
        dev_email = None
    if dev_email:
        email = dev_email.strip().lower()
        db.ensure_user(email)
        return email

    # Production: Streamlit Community Cloud with Google OAuth
    if not st.user.is_logged_in:
        st.markdown("""
        <div style="text-align: center; padding: 3rem 0;">
            <div style="font-size: 4rem; font-weight: 700;
                 background: linear-gradient(135deg, #6C5CE7, #a29bfe, #fd79a8);
                 -webkit-background-clip: text; -webkit-text-fill-color: transparent;
                 margin-bottom: 0.5rem;">UdharBand</div>
            <div style="color: #8888aa; font-size: 1.1rem; margin-bottom: 2rem;">
                Split expenses with friends, effortlessly.</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("""
        <style>
        .stButton > button {
            padding-top: 1rem !important;
            padding-bottom: 1rem !important;
        }
        </style>
        """, unsafe_allow_html=True)
        _, col_btn, _ = st.columns([1.5, 1.5, 1.5])
        with col_btn:
            if st.button("SIGN IN", type="primary", use_container_width=True, icon=":material/login:"):
                st.login("google")
        st.stop()

    email = st.user.get("email")
    if not email:
        st.markdown("""
        <div style="font-size: 2rem; font-weight: 700;
             background: linear-gradient(135deg, #6C5CE7, #a29bfe);
             -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
             UdharBand</div>
        """, unsafe_allow_html=True)
        st.error("Could not retrieve your email. Please try logging in again.")
        if st.button("Try again"):
            st.logout()
        st.stop()

    email = email.strip().lower()
    if not st.session_state.get("_user_ensured"):
        name = st.user.get("name")
        first_name = name.split()[0] if name else None
        db.ensure_user(email, first_name)
        st.session_state["_user_ensured"] = True
    return email


def get_display_name(email: str) -> str:
    return email.split("@")[0]


def build_display_map(members: list[dict]) -> dict[str, str]:
    """Build {email: display_name} from a list of member dicts."""
    return {m["email"]: m["display_name"] for m in members}
