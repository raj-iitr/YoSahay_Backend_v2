import gspread
import base64
import json
from datetime import datetime
import logging

from app.config import settings

logger = logging.getLogger(__name__)

# --- Authentication with Google Sheets ---
sheet = None
try:
    creds_b64 = settings.GCP_SA_KEY_B64
    if not creds_b64:
        raise ValueError("GCP_SA_KEY_B64 environment variable not set.")
        
    creds_json_str = base64.b64decode(creds_b64).decode('utf-8')
    creds_dict = json.loads(creds_json_str)
    
    gc = gspread.service_account_from_dict(creds_dict)
    # Ensure your sheet name is correct
    sheet = gc.open("YoSahay User Log").sheet1
    logger.info("Successfully connected to Google Sheets for rich analytics logging.")
except Exception as e:
    logger.error(f"FATAL: Failed to connect to Google Sheets. Analytics will not be logged. Error: {e}")
    sheet = None

def log_analytics_event(analytics_data: dict):
    """
    Appends a new row with a full set of analytics data to the Google Sheet.
    This is the single function responsible for all logging.
    """
    if not sheet:
        logger.error("Cannot log to Google Sheet, connection is not available.")
        return

    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Define the exact order of columns to match the spreadsheet
        # Added 'IntentScheme' to track the new classification step
        headers = ["Timestamp", "UserID", "QueryText", "Language", "CacheStatus", 
                   "IntentScheme", "ContextStatus", "ContextSource", 
                   "RelevanceDistance", "ResponseType"]
        
        # Build the row by getting data from the dictionary, with defaults for missing keys
        row = [timestamp]
        for header in headers[1:]: # Skip timestamp
            value = analytics_data.get(header)
            if header == "RelevanceDistance" and isinstance(value, (int, float)):
                row.append(f"{value:.4f}")
            else:
                row.append(str(value) if value is not None else "")

        sheet.append_row(row, value_input_option='USER_ENTERED')
        
        response_type = analytics_data.get("ResponseType", "INTERACTION")
        user_id = analytics_data.get("UserID", "unknown")
        logger.info(f"Successfully logged event '{response_type}' for user {user_id} to Google Sheet.")
    except Exception as e:
        logger.error(f"Error while logging to Google Sheet: {e}", exc_info=True)