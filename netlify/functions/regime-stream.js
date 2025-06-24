exports.handler = async (event, context) => {
    const headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Content-Type': 'application/json'
    };
    
    // Generate regime update
    const entropy_score = Math.random() * 3 + 1.5;
    const regime_id = entropy_score < 2.2 ? 0 : 
                     entropy_score < 2.8 ? 1 : 
                     entropy_score < 3.5 ? 2 : 3;
    
    const stress_level = entropy_score > 3.5 ? 'CRITICAL' :
                       entropy_score > 3.0 ? 'HIGH' :
                       entropy_score > 2.5 ? 'MEDIUM' : 'LOW';
    
    const update = {
        type: 'regime_update',
        regime_id: regime_id,
        entropy_score: Math.round(entropy_score * 1000) / 1000,
        stress_level: stress_level,
        timestamp: new Date().toISOString(),
        probability: Math.round((Math.random() * 0.2 + 0.7) * 1000) / 1000,
        model_status: 'netlify_js_functions'
    };
    
    return {
        statusCode: 200,
        headers,
        body: JSON.stringify(update)
    };
};
