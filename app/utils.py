import json
import re
from datetime import datetime


# 從 LinkedIn 貼文的 URL 中解析日期
def get_post_id(linkedin_url):
    regex = re.compile(r"([0-9]{19})")  # Match LinkedIn post ID
    match = regex.search(linkedin_url)
    if match:
        return match.group(1)
    else:
        print("Invalid LinkedIn URL")
        return None

def extract_unix_timestamp(post_id):
    if not post_id:
        return None
    
    as_binary = bin(int(post_id))[2:]  # Convert post ID to binary
    return int(as_binary[:41], 2)  # Extract the first 41 bits as timestamp

def unix_timestamp_to_human_date(timestamp):
    date_object = datetime.utcfromtimestamp(timestamp / 1000)  # Convert to datetime object
    date_utc = date_object.strftime("%a, %d %b %Y %H:%M:%S GMT")
    date_local = date_object.strftime("%a %d %b %Y %I:%M:%S %p %Z")
    return {"dateUTC": date_utc, "dateLocal": date_local}

def get_date_from_url(linkedin_url):
    post_id = get_post_id(linkedin_url)
    if not post_id:
        return
    
    unix_timestamp = extract_unix_timestamp(post_id)
    if not unix_timestamp:
        print("Error processing timestamp")
        return
    
    dates = unix_timestamp_to_human_date(unix_timestamp)
    # print(f"UTC Date: {dates['dateUTC']}")
    # print(f"Local Date: {dates['dateLocal']}")
    return dates['dateUTC']


def parse_str_to_dict(response: str) -> dict:
    """Parse the ChatGPT response string into a dictionary.
    
    Args:
        response (str): The response string from ChatGPT
        
    Returns:
        dict: Parsed response containing Headline, Contents, and Good News Category
    """
    try:
        # Remove any markdown code block indicators if present
        response = response.replace('```json', '').replace('```', '').strip()
        return json.loads(response)
    except json.JSONDecodeError as e:
        print(f"Error parsing response: {e}")
        return {
            "Headline": "Error parsing response",
            "Contents": response,
            "Good News Category": "None"
        }
