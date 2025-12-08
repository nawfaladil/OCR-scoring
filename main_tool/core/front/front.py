"""
Streamlit frontend
"""
import streamlit as st
import requests
import pandas as pd
import json


API_URL = "http://127.0.0.1:8000"

st.title("Document Evaluation Tool")

# --- 1. Login/Register Form ---
if "auth_cookie" not in st.session_state: # Which means we are not authentificated
    tab1, tab2 = st.tabs(["Login", "Register"])

    # Setup the login form
    with tab1:
        st.subheader("Login")
        login_email = st.text_input("Email", key="login_email")
        login_password = st.text_input("Password", type="password", key="login_pwd")
        col_login, col_forgot = st.columns(2)

        # Setup login button logic
        with col_login:
            if st.button("Login"):
                resp = requests.post(
                    f"{API_URL}/auth/jwt/login",
                    data={"username": login_email, "password": login_password},
                    timeout=10
                )

                if resp.status_code == 204: # Code fastAPI users return with success login
                    st.session_state["auth_cookie"] = resp.cookies.get("fastapiusersauth")
                    st.success("Logged in!")
                    st.rerun()

                else:
                    st.error("Login failed.")

        # Setup forgot password button logic
        with col_forgot:
            if st.button("Forgot Password?", key="forgot_button"):
                st.session_state["show_forgot"] = True

        if st.session_state.get("show_forgot", False): # In case button was clicked
            st.markdown("----\n### Reset Your Password")

            forgot_email = st.text_input("Email for password reset", key="forgot_email")

            if st.button("Send reset email or token", key="forgot_send"):
                # We use the FastAPI users router 'forgot-password'
                r = requests.post(f"{API_URL}/auth/forgot-password",
                                  json={"email": forgot_email},
                                  timeout=10
                )
                # Wether email exists or not we send same message for security reasons
                if r.status_code in (200, 202):
                    st.success("If this email exists," \
                    "you'll receive a reset token (You need to check server logs for now).")
                else: # In case of a bug
                    st.error("Reset failed.")

            st.info("If you have a token, set a new password:")

            reset_token = st.text_input("Reset token", key="reset_token_forgot")

            new_pwd = st.text_input("New password",
                                    type="password",
                                    key="reset_pwd1_forgot"
            )

            new_pwd2 = st.text_input("Repeat new password",
                                     type="password",
                                     key="reset_pwd2_forgot"
            )

            if st.button("Reset Password", key="reset_button"):
                if new_pwd != new_pwd2:
                    st.error("Passwords do not match.")

                # You can ensure same password rules here
                # elif len(new_pwd) < 8:
                #     st.error("Password must be at least 8 characters.")

                # elif forgot_email in new_pwd:
                #     st.error("Password should not contain e-mail")

                else:
                    r = requests.post(
                        f"{API_URL}/auth/reset-password",
                        json={
                            "token": reset_token,
                            "password": new_pwd,
                        },
                        timeout=10
                    )
                    if r.status_code == 200:
                        st.success("Password reset successful! Please login.")
                        st.session_state["show_forgot"] = False
                        st.rerun()
                    else:
                        st.error(f"Reset failed: {r.text}")

    # Setup Register form
    with tab2:
        st.subheader("Register")

        reg_email = st.text_input("Email", key="reg_email")

        reg_password = st.text_input("Password",
                                     type="password",
                                     key="reg_pwd"
        )

        reg_password2 = st.text_input("Repeat Password",
                                      type="password",
                                      key="reg_pwd2"
        )

        # Setup register button logic
        if st.button("Register"):
            if reg_password != reg_password2:
                st.error("Passwords do not match.")

            else:
                reg_resp = requests.post(
                    f"{API_URL}/auth/register",
                    json={"email": reg_email, "password": reg_password},
                    timeout=10
                )
                if reg_resp.status_code == 201: # Code for successful registration
                    st.success("Registration successful! Please log in.")
                else:
                    st.error(f"Registration failed: {reg_resp.text}")

    st.stop()

# --log out--

# Check if a user is logged in
if "auth_cookie" in st.session_state:
    # I made the log out button on a side bar
    st.sidebar.success(f"Logged in as: {st.session_state.get('login_email', 'User')}")
    if st.sidebar.button("Logout"):
        # When log out button is clicked, remove all user information from session
        for k in [
            "auth_cookie",
            "login_email",
            "login_pwd",
            "reg_email",
            "reg_pwd",
            "reg_pwd2",
        ]:
            if k in st.session_state:
                del st.session_state[k]
        st.success("Logged out!")
        st.rerun()

# --- 2. Fetch User Config ---

# Get cookies from session to request user config
cookies = {"fastapiusersauth": st.session_state["auth_cookie"]}
config_resp = requests.get(f"{API_URL}/config",
                           cookies=cookies,
                           timeout=10
)
if config_resp.status_code != 200:
    st.error("Could not fetch config.")
    st.stop()

# Make config into a dictionnary (response is in json)
config = config_resp.json()

# Config is setup to have a key for each component of the system that needs a config
# example:
#{
#   evaluator:{
#       thresholds:{
#           field:custom_threshold
#       }
#   }
#   json_loader:{
#       some_parameter: foobar
#   }
#}
# Right now we only need the thresholds, but you get the idea.

evaluator = config.get("evaluator", {})
thresholds = evaluator.get("thresholds", {})

# --- 3. Editable Thresholds Table ---

# The user will see his config and modify it through a simple table
st.subheader("Edit Thresholds")

# For that, we create a dataframe
df = pd.DataFrame(list(thresholds.items()), columns=["Key", "Value"])

# Display a data editor table, check streamlit documentation
edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)

# --- 4. Save Config ---
if st.button("Save Config"):
    # Update the config dict
    evaluator["thresholds"] = {
        row["Key"]: float(row["Value"])
        for _, row in edited_df.iterrows()
        # Make sure both key and value aren't empty
        if str(row["Key"]).strip() != "" and row["Value"] is not None
    }
    config["evaluator"] = evaluator
    # Save to backend (send as JSON, backend will convert to dict and use it)
    resp = requests.post(
        f"{API_URL}/config",
        json=config,
        cookies=cookies,
        timeout=10
    )
    if resp.status_code == 200:
        st.success("Config saved successfully!")
    else:
        st.error("Failed to save config.")

# --- 5. Evaluation ---
st.subheader("Run Evaluation")
gt_file = st.file_uploader("Upload ground truth file", type=["xlsx", "csv", "txt"])

predictions_file = st.file_uploader("Upload predictions ZIP", type=["zip"])

config = requests.get(f"{API_URL}/config",
                      cookies=cookies,
                      timeout=10
).json()

json_config_str = json.dumps(config) # Turn into json

data = {"config": json_config_str} # Create response body to send to backend

if st.button("Evaluate") and gt_file and predictions_file:
    files = {
        "ground_truth": (gt_file.name, gt_file, gt_file.type),
        "predictions": (predictions_file.name, predictions_file, predictions_file.type)
    }
    eval_resp = requests.post(f"{API_URL}/evaluate/",
                              files=files,
                              data=data,
                              cookies=cookies,
                              timeout=10
    )
    # If evaluation is successful, backend sent excel file result
    if eval_resp.status_code == 200:
        st.download_button("Download Result Excel", data=eval_resp.content, file_name="result.xlsx")
    else:
        st.error("Evaluation failed.")
