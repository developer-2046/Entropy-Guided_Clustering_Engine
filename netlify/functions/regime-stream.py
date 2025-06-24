import json
import random
from datetime import datetime

def handler(event, context):
    """Simulate WebSocket data for regime updates."""
    
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Content-Type': 'application/json'
    }
    
    # Generate regime update
    entropy_score = random.uniform(1.5, 4.5)
    regime_id = 0 if entropy_score < 2.2 else 1 if entropy_score < 2.8 else 2 if entropy_score < 3.5 else 3
    stress_level = 'CRITICAL' if entropy_score > 3.5 else 'HIGH' if entropy_score > 3.0 else 'MEDIUM' if entropy_score > 2.5 else 'LOW'
    
    update = {
        'type': 'regime_update',
        'regime_id': regime_id,
        'entropy_score': round(entropy_score, 3),
        'stress_level': stress_level,
        'timestamp': datetime.now().isoformat(),
        'probability': round(random.uniform(0.7, 0.95), 3),
        'model_status': 'netlify_functions'
    }
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps(update)
    }
