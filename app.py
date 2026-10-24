"""BatchWatch: Streamlit entry point.

    streamlit run app.py

If no user role is selected in the session, the landing/role-picker page is displayed.
Once signed in, pages shown depend on the signed-in role (admin / pharmacist / household).
The backend enforces the same permissions, so hiding a page is not the only security control.
"""
import streamlit as st

st.set_page_config(page_title="BatchWatch", page_icon="💊", layout="wide")

import ui  # noqa: E402

ui.ensure_db()
a = ui.actor()

if not a:
    # No persona signed in: render the clean full-page landing/login page
    landing_page = st.Page("views/landing.py", title="Welcome to BatchWatch", icon="💊")
    st.navigation([landing_page], position="hidden").run()
else:
    # Persona active: show sidebar and role-authorized navigation
    ui.sidebar()
    home = st.Page("views/home.py", title="Home", icon="🏠", default=True)
    pages = {
        "admin": [
            home,
            st.Page("views/admin.py", title="Alert data (admin)", icon="🗂️"),
            st.Page("views/audit.py", title="Audit & reports", icon="🧾"),
        ],
        "pharmacist": [
            home,
            st.Page("views/pharmacy.py", title="Stock check", icon="🏥"),
            st.Page("views/audit.py", title="Audit & reports", icon="🧾"),
        ],
        "household": [
            home,
            st.Page("views/household.py", title="Scan a medicine", icon="📷"),
            st.Page("views/audit.py", title="My activity log", icon="🧾"),
        ],
    }
    st.navigation(pages[a["role"]]).run()
