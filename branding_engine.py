"""
Module: branding_engine.py
Purpose: Branding Engine for Nexus Hub. Handles Programmatic Color Management 
across Gmail and Google Drive based on Section 2.2 of ARCHITECTURE.md.
"""

import math
from typing import Dict, Tuple

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

# ---------------------------------------------------------------------------
# Gmail API Allowed Color Pairs (35 standard pairs)
# ---------------------------------------------------------------------------
GMAIL_ALLOWED_COLORS = [
    {"backgroundColor": "#000000", "textColor": "#ffffff"},
    {"backgroundColor": "#434343", "textColor": "#ffffff"},
    {"backgroundColor": "#666666", "textColor": "#ffffff"},
    {"backgroundColor": "#999999", "textColor": "#ffffff"},
    {"backgroundColor": "#cccccc", "textColor": "#000000"},
    {"backgroundColor": "#efefef", "textColor": "#000000"},
    {"backgroundColor": "#f3f3f3", "textColor": "#000000"},
    {"backgroundColor": "#ffffff", "textColor": "#000000"},
    {"backgroundColor": "#fb4c2f", "textColor": "#ffffff"},
    {"backgroundColor": "#ffad47", "textColor": "#000000"},
    {"backgroundColor": "#fad165", "textColor": "#000000"},
    {"backgroundColor": "#16a766", "textColor": "#ffffff"},
    {"backgroundColor": "#43d692", "textColor": "#000000"},
    {"backgroundColor": "#4a86e8", "textColor": "#ffffff"},
    {"backgroundColor": "#a479e2", "textColor": "#ffffff"},
    {"backgroundColor": "#f691b3", "textColor": "#ffffff"},
    {"backgroundColor": "#f6c5be", "textColor": "#000000"},
    {"backgroundColor": "#ffe6c7", "textColor": "#000000"},
    {"backgroundColor": "#fef1d1", "textColor": "#000000"},
    {"backgroundColor": "#b9e4d0", "textColor": "#000000"},
    {"backgroundColor": "#c6f3de", "textColor": "#000000"},
    {"backgroundColor": "#c9daf8", "textColor": "#000000"},
    {"backgroundColor": "#e4d7f5", "textColor": "#000000"},
    {"backgroundColor": "#fcdee8", "textColor": "#000000"},
    {"backgroundColor": "#efa093", "textColor": "#000000"},
    {"backgroundColor": "#ffd6a2", "textColor": "#000000"},
    {"backgroundColor": "#fce8b3", "textColor": "#000000"},
    {"backgroundColor": "#89d3b2", "textColor": "#000000"},
    {"backgroundColor": "#a0eac9", "textColor": "#000000"},
    {"backgroundColor": "#a4c2f4", "textColor": "#000000"},
    {"backgroundColor": "#d0bdf1", "textColor": "#000000"},
    {"backgroundColor": "#fbc8d9", "textColor": "#000000"},
    {"backgroundColor": "#e66550", "textColor": "#ffffff"},
    {"backgroundColor": "#ffbc6b", "textColor": "#000000"},
    {"backgroundColor": "#fcda83", "textColor": "#000000"},
]

def hex_to_rgb(hex_str: str) -> Tuple[int, int, int]:
    """
    Purpose: Converts a hex color string to an RGB tuple.
    Expected Inputs: hex_str (str) - The hex color string (e.g., '#FF0000' or 'FFF').
    Expected Outputs: Tuple[int, int, int] - The RGB components as a tuple.
    """
    hex_str = hex_str.lstrip('#')
    # If the hex string is short-hand (e.g., 'FFF'), expand it.
    if len(hex_str) == 3:
        hex_str = ''.join(c + c for c in hex_str)
    return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))

def color_distance(rgb1: Tuple[int, int, int], rgb2: Tuple[int, int, int]) -> float:
    """
    Purpose: Calculates the Euclidean distance between two RGB colors to find visual similarity.
    Expected Inputs: 
        rgb1 (Tuple[int, int, int]) - First RGB color.
        rgb2 (Tuple[int, int, int]) - Second RGB color.
    Expected Outputs: float - The numerical distance between the colors.
    """
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(rgb1, rgb2)))

def get_closest_gmail_color(requested_hex: str) -> Dict[str, str]:
    """
    Purpose: Finds the closest matching allowed Gmail color pair using simple Euclidean 
             distance in RGB color space.
    Expected Inputs: requested_hex (str) - The desired color in hex format.
    Expected Outputs: Dict[str, str] - A dictionary containing the closest 'backgroundColor' and 'textColor'.
    """
    requested_rgb = hex_to_rgb(requested_hex)
    best_match = GMAIL_ALLOWED_COLORS[0]
    min_distance = float('inf')

    # Iterate through all allowed Gmail colors to find the best match.
    for color_pair in GMAIL_ALLOWED_COLORS:
        allowed_rgb = hex_to_rgb(color_pair["backgroundColor"])
        dist = color_distance(requested_rgb, allowed_rgb)
        # If the current distance is smaller than the minimum found so far, update the best match.
        if dist < min_distance:
            min_distance = dist
            best_match = color_pair

    return best_match

def sync_workspace_colors(creds: Credentials, entity_name: str, requested_hex: str) -> None:
    """
    Purpose: Applies the matched color pair to the corresponding nested Label in Gmail
             and the exact same hex color to the folderColorRgb property in Drive.
    Expected Inputs:
        creds (Credentials) - Google Workspace OAuth credentials.
        entity_name (str) - The name of the label/folder to update.
        requested_hex (str) - The hex color to apply.
    Expected Outputs: None. Modifies Gmail labels and Drive folders via API.
    """
    closest_color = get_closest_gmail_color(requested_hex)
    matched_hex = closest_color["backgroundColor"]
    
    print(f"Requested color {requested_hex} mapped to {matched_hex} for entity '{entity_name}'")
    
    # 1. Update Gmail Label
    gmail_service = build('gmail', 'v1', credentials=creds)
    try:
        labels_response = gmail_service.users().labels().list(userId='me').execute()
        labels = labels_response.get('labels', [])
        
        target_label = next((label for label in labels if label['name'] == entity_name), None)
        
        # If the target label exists in Gmail, update its color.
        if target_label:
            label_id = target_label['id']
            # Only update the color property
            body = {
                "color": closest_color
            }
            gmail_service.users().labels().patch(userId='me', id=label_id, body=body).execute()
            print(f"Successfully updated Gmail Label '{entity_name}' with color {matched_hex}.")
        # Otherwise, report that it was not found.
        else:
            print(f"Gmail Label '{entity_name}' not found. Skipping Gmail update.")
    except Exception as e:
        print(f"Failed to update Gmail Label: {e}")

    # 2. Update Google Drive Folder
    drive_service = build('drive', 'v3', credentials=creds)
    try:
        # Escape single quotes in entity name for query
        query_name = entity_name.replace("'", "\\'")
        query = f"name='{query_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        folders_response = drive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        folders = folders_response.get('files', [])
        
        # If matching folders are found in Drive, update their color property.
        if folders:
            # Update all folders matching the name
            # Iterate through each folder returned by the query to apply the color.
            for folder in folders:
                folder_id = folder['id']
                body = {
                    "folderColorRgb": matched_hex
                }
                drive_service.files().update(fileId=folder_id, body=body).execute()
                print(f"Successfully updated Drive Folder '{folder['name']}' (ID: {folder_id}) with color {matched_hex}.")
        # Otherwise, report that the folder was not found.
        else:
            print(f"Drive Folder '{entity_name}' not found. Skipping Drive update.")
    except Exception as e:
        print(f"Failed to update Drive Folder: {e}")

# Block executed when the script runs directly.
if __name__ == "__main__":
    from auth import authenticate
    print("Testing Branding Engine Initialization...")
    # Example execution logic would go here
    pass
