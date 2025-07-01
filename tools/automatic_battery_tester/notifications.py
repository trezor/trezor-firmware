# notifications.py

import json
import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)


def send_slack_message(
    webhook_url: Optional[str],
    message: str,
    fallback_text: str = "Notification from Battery Tester",
) -> bool:
    """
    Send slack message using Incoming Webhook URL

    Args:
        webhook_url: Slack webhook URL.
        message: Message text (may consist of markdown).
        fallback_text: Text, který se zobrazí v notifikacích.

    Returns:
        True if the message was successfully sent (status code 2xx).
    """
    if not webhook_url:
        logger.error("Slack Error: Webhook URL is not configured.")
        return False
    if not message:
        logger.warning("Slack Warning: Attempting to send an empty message.")

    slack_data = {
        "text": fallback_text,
        "blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": message}}],
    }

    try:

        payload_json_string = json.dumps(slack_data)

        post_data = {"payload": payload_json_string}

        logger.info(
            "Sending Slack notification via webhook (using payload parameter)..."
        )
        logger.debug(f"Slack Webhook URL: {webhook_url}")
        logger.debug(f"Slack Payload (JSON String): {payload_json_string}")

        timeout_seconds = 15
        response = requests.post(
            webhook_url,
            data=post_data,
            # headers={'Content-Type': 'application/x-www-form-urlencoded'}
            timeout=timeout_seconds,
        )

        if response.status_code == 200 and response.text.lower() == "ok":
            logger.info("Slack notification request sent successfully.")
            return True
        else:
            error_detail = (
                f"Status: {response.status_code}, Response: '{response.text[:500]}...'"
            )
            logger.error(f"Slack request failed. {error_detail}")
            if response.status_code == 400 and "invalid_payload" in response.text:
                logger.error(
                    "Slack Error Detail: The JSON payload structure might be incorrect."
                )
            elif response.status_code == 403:
                logger.error(
                    "Slack Error Detail: Forbidden - Check webhook URL validity or permissions."
                )
            elif response.status_code == 404:
                logger.error(
                    "Slack Error Detail: Not Found - The webhook URL might be incorrect or deactivated."
                )
            return False

    except requests.exceptions.RequestException as e:
        logger.error(f"Slack request failed (RequestException): {e}")
        return False
    except Exception as e:
        logger.exception(f"An unexpected error occurred during Slack notification: {e}")
        return False
