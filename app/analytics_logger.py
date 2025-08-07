# app/analytics_logger.py

import gspread
import os
import json
import base64
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# --- Authentication with Google Sheets ---
try:
    # Decode the credentials from the Render environment variable
    creds_b64 = os.getenv("GCP_SA_KEY_B64")
    creds_json_str = base64.b64decode(creds_b64).decode('utf-8')
    creds_dict = json.loads(creds_json_str)
    
    # Authorize and connect to Google Sheets
    gc = gspread.service_account_from_dict(creds_dict)
    # Open the sheet by its exact name. Make sure your sheet is named this.
    sheet = gc.open("YoSahay Bot User Questions").sheet1
    logger.info("Successfully connected to Google Sheets for analytics logging.")
except Exception as e:
    logger.error(f"FATAL: Failed to connect to Google Sheets. Analytics will not be logged. Error: {e}")
    sheet = None

def log_user_question(user_id: str, question_text: str):
    """
    Appends a new row to the Google Sheet with the user's question.
    """
    if not sheet:
        logger.error("Cannot log to Google Sheet, connection is not available.")
        return

    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [timestamp, user_id, question_text]
        sheet.append_row(row, value_input_option='USER_ENTERED')
        logger.info(f"Successfully logged question for user {user_id} to Google Sheet.")
    except Exception as e:
        logger.error(f"Error while logging to Google Sheet: {e}")