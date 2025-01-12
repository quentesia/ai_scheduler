from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/')
def home():
    return "Welcome to the AI-Powered Global Meeting Scheduler!"

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    intent = data.get('queryResult', {}).get('intent', {}).get('displayName')
    
    # Handle different intents
    if intent == 'ScheduleMeeting':
        return jsonify({"fulfillmentText": "Scheduling your meeting!"})
    elif intent == 'CancelMeeting':
        return jsonify({"fulfillmentText": "Your meeting has been canceled!"})
    else:
        return jsonify({"fulfillmentText": "Sorry, I didn't understand that intent."})
    
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Route not found"}), 404

@app.errorhandler(500)
def server_error(error):
    return jsonify({"error": "Internal server error"}), 500



if __name__ == '__main__':
    app.run(debug=True)