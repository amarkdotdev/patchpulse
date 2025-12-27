"""Slack webhook handler for button callbacks."""

from flask import Flask, request, jsonify
from notifier import SlackNotifier
import os

app = Flask(__name__)
notifier = SlackNotifier()


@app.route("/slack/events", methods=["POST"])
def slack_events():
    """Handle Slack event callbacks."""
    data = request.json
    
    # URL verification
    if data.get("type") == "url_verification":
        return jsonify({"challenge": data.get("challenge")})
    
    # Handle button interactions
    if data.get("type") == "block_actions":
        payload = data
        if notifier:
            result = notifier.handle_button_callback(payload)
            return jsonify(result)
        return jsonify({"text": "Slack notifier not configured"})
    
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)

