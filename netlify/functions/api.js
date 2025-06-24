const { randomUUID } = require('crypto');

exports.handler = async (event, context) => {
    // CORS headers
    const headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Content-Type': 'application/json'
    };
    
    // Handle CORS preflight
    if (event.httpMethod === 'OPTIONS') {
        return {
            statusCode: 200,
            headers,
            body: ''
        };
    }
    
    const path = event.path;
    
    // Health check
    if (path.includes('/health')) {
        return {
            statusCode: 200,
            headers,
            body: JSON.stringify({
                status: 'healthy',
                timestamp: new Date().toISOString(),
                model_fitted: true,
                platform: 'netlify-functions-js'
            })
        };
    }
    
    // Current regime endpoint
    if (path.includes('/regime/current')) {
        // Simple entropy simulation
        const entropy_score = Math.random() * 3 + 1.5; // 1.5 to 4.5
        const regime_id = entropy_score < 2.2 ? 0 : 
                         entropy_score < 2.8 ? 1 : 
                         entropy_score < 3.5 ? 2 : 3;
        
        const stress_levels = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'];
        const stress_level = entropy_score > 3.5 ? 'CRITICAL' :
                           entropy_score > 3.0 ? 'HIGH' :
                           entropy_score > 2.5 ? 'MEDIUM' : 'LOW';
        
        const regime_data = {
            regime_id: regime_id,
            probability: Math.round((Math.random() * 0.2 + 0.75) * 1000) / 1000,
            entropy_score: Math.round(entropy_score * 1000) / 1000,
            market_stress_level: stress_level,
            timestamp: new Date().toISOString(),
            eigenvalues: Array.from({length: 8}, () => 
                Math.round((Math.random() * 2.3 + 0.2) * 1000) / 1000
            ),
            model_status: 'netlify_js_functions'
        };
        
        return {
            statusCode: 200,
            headers,
            body: JSON.stringify(regime_data)
        };
    }
    
    // Default 404
    return {
        statusCode: 404,
        headers,
        body: JSON.stringify({ error: 'Not found' })
    };
};
