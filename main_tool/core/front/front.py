import streamlit as st
import requests
import pandas as pd
import json


API_URL = "http://127.0.0.1:8000"

st.title("Document Evaluation Tool")

# --- 1. Login/Register Form ---
if "auth_cookie" not in st.session_state:
    tab1, tab2 = st.tabs(["Login", "Register"])

    with tab1:
        st.subheader("Login")
        login_email = st.text_input("Email", key="login_email")
        login_password = st.text_input("Password", type="password", key="login_pwd")
        col_login, col_forgot = st.columns(2)
        with col_login:
            if st.button("Login"):
                resp = requests.post(
                    f"{API_URL}/auth/jwt/login",
                    data={"username": login_email, "password": login_password},
                )
                if resp.status_code == 204:
                    st.session_state["auth_cookie"] = resp.cookies.get("fastapiusersauth")
                    st.success("Logged in!")
                    st.rerun()
                else:
                    st.error("Login failed.")

        with col_forgot:
            if st.button("Forgot Password?", key="forgot_button"):
                st.session_state["show_forgot"] = True

        if st.session_state.get("show_forgot", False):
            st.markdown("----\n### Reset Your Password")

            forgot_email = st.text_input("Email for password reset", key="forgot_email")
            if st.button("Send reset email or token", key="forgot_send"):
                r = requests.post(f"{API_URL}/auth/forgot-password", json={"email": forgot_email})
                if r.status_code in (200, 202):
                    st.success("If this email exists," \
                    "you'll receive a reset token (see server log for now).")
                else:
                    st.error("Reset failed.")

            st.info("If you have a token, set a new password:")
            reset_token = st.text_input("Reset token", key="reset_token_forgot")
            new_pwd = st.text_input("New password", type="password", key="reset_pwd1_forgot")
            new_pwd2 = st.text_input("Repeat new password",
                                     type="password", key="reset_pwd2_forgot")
            if st.button("Reset Password", key="reset_button"):
                if new_pwd != new_pwd2:
                    st.error("Passwords do not match.")
                elif len(new_pwd) < 8:
                    st.error("Password must be at least 8 characters.")
                else:
                    r = requests.post(
                        f"{API_URL}/auth/reset-password",
                        json={
                            "token": reset_token,
                            "password": new_pwd,
                        }
                    )
                    if r.status_code == 200:
                        st.success("Password reset successful! Please login.")
                        st.session_state["show_forgot"] = False
                        st.rerun()
                    else:
                        st.error(f"Reset failed: {r.text}")


    with tab2:
        st.subheader("Register")
        reg_email = st.text_input("Email", key="reg_email")
        reg_password = st.text_input("Password", type="password", key="reg_pwd")
        reg_password2 = st.text_input("Repeat Password", type="password", key="reg_pwd2")
        if st.button("Register"):
            if reg_password != reg_password2:
                st.error("Passwords do not match.")
            elif len(reg_password) < 8:
                st.error("Password must be at least 8 characters.")
            else:
                reg_resp = requests.post(
                    f"{API_URL}/auth/register",
                    json={"email": reg_email, "password": reg_password},
                )
                if reg_resp.status_code == 201:
                    st.success("Registration successful! Please log in.")
                else:
                    st.error(f"Registration failed: {reg_resp.text}")

    st.stop()

# --log out--

if "auth_cookie" in st.session_state:
    st.sidebar.success(f"Logged in as: {st.session_state.get('login_email', 'User')}")
    if st.sidebar.button("Logout"):
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
cookies = {"fastapiusersauth": st.session_state["auth_cookie"]}
config_resp = requests.get(f"{API_URL}/config", cookies=cookies)
if config_resp.status_code != 200:
    st.error("Could not fetch config.")
    st.stop()

config = config_resp.json()
evaluator = config.get("evaluator", {})
thresholds = evaluator.get("thresholds", {})

# --- 3. Editable Thresholds Table ---
st.subheader("Edit Thresholds")
df = pd.DataFrame(list(thresholds.items()), columns=["Key", "Value"])
edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)

# --- 4. Save Config ---
if st.button("Save Config"):
    # Update the config dict
    evaluator["thresholds"] = {
        row["Key"]: float(row["Value"])
        for _, row in edited_df.iterrows()
        if str(row["Key"]).strip() != "" and row["Value"] is not None
    }
    config["evaluator"] = evaluator
    # Save to backend (send as JSON, backend will convert to YAML)
    resp = requests.post(
        f"{API_URL}/config",
        json=config,
        cookies=cookies,
    )
    if resp.status_code == 200:
        st.success("Config saved successfully!")
    else:
        st.error("Failed to save config.")

# --- 5. Evaluation ---
st.subheader("Run Evaluation")
gt_file = st.file_uploader("Upload ground truth Excel", type=["xlsx"])
predictions_file = st.file_uploader("Upload predictions ZIP", type=["zip"])
config = requests.get(f"{API_URL}/config", cookies=cookies).json()
json_config_str = json.dumps(config)
data = {"config": json_config_str}

if st.button("Evaluate") and gt_file and predictions_file:
    files = {
        "ground_truth": (gt_file.name, gt_file, gt_file.type),
        "predictions": (predictions_file.name, predictions_file, predictions_file.type)
    }
    eval_resp = requests.post(f"{API_URL}/evaluate/", files=files, data=data, cookies=cookies)
    if eval_resp.status_code == 200:
        st.download_button("Download Result Excel", data=eval_resp.content, file_name="result.xlsx")
    else:
        st.error("Evaluation failed.")
