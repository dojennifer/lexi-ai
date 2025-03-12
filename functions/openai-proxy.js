const axios = require('axios');

exports.handler = async function(event, context) {
  // Only allow POST requests
  if (event.httpMethod !== 'POST') {
    return { statusCode: 405, body: 'Method Not Allowed' };
  }

  try {
    const body = JSON.parse(event.body);
    const { action, userMessage, threadId, runId } = body;
    
    // Get API key from environment variable
    const apiKey = process.env.OPENAI_API_KEY;
    
    if (!apiKey) {
      return {
        statusCode: 500,
        body: JSON.stringify({ error: 'API key not configured' })
      };
    }

    // Common headers for all OpenAI API requests
    const headers = {
      'Authorization': `Bearer ${apiKey}`,
      'Content-Type': 'application/json',
      'OpenAI-Beta': 'assistants=v2'
    };

    let response;
    
    // Handle different types of requests
    switch (action) {
      case 'createThread':
        response = await axios.post('https://api.openai.com/v1/threads', {}, { headers });
        return {
          statusCode: 200,
          body: JSON.stringify({ threadId: response.data.id })
        };
        
      case 'addMessage':
        if (!threadId || !userMessage) {
          return { statusCode: 400, body: JSON.stringify({ error: 'Missing threadId or message' }) };
        }
        
        response = await axios.post(`https://api.openai.com/v1/threads/${threadId}/messages`, 
          { role: 'user', content: userMessage },
          { headers }
        );
        return {
          statusCode: 200,
          body: JSON.stringify({ messageId: response.data.id })
        };
        
      case 'runAssistant':
        if (!threadId) {
          return { statusCode: 400, body: JSON.stringify({ error: 'Missing threadId' }) };
        }
        
        const assistantId = "asst_J2SsEMfF2LzQCnmepffEbqnH"; // other assistant id asst_ZPSmASSra6rihtDHfI5gRDbU
        response = await axios.post(`https://api.openai.com/v1/threads/${threadId}/runs`,
          { assistant_id: assistantId },
          { headers }
        );
        return {
          statusCode: 200,
          body: JSON.stringify({ runId: response.data.id })
        };
        
      case 'checkRun':
        if (!threadId || !runId) {
          return { statusCode: 400, body: JSON.stringify({ error: 'Missing threadId or runId' }) };
        }
        
        response = await axios.get(`https://api.openai.com/v1/threads/${threadId}/runs/${runId}`,
          { headers }
        );
        return {
          statusCode: 200,
          body: JSON.stringify({ status: response.data.status })
        };
        
      case 'getMessages':
        if (!threadId) {
          return { statusCode: 400, body: JSON.stringify({ error: 'Missing threadId' }) };
        }
        
        response = await axios.get(`https://api.openai.com/v1/threads/${threadId}/messages`,
          { headers }
        );
        return {
          statusCode: 200,
          body: JSON.stringify({ messages: response.data.data })
        };
        
      default:
        return {
          statusCode: 400,
          body: JSON.stringify({ error: 'Invalid action' })
        };
    }
  } catch (error) {
    console.error('Error:', error);
    return {
      statusCode: 500,
      body: JSON.stringify({ 
        error: 'Error processing request',
        details: error.response ? error.response.data : error.message
      })
    };
  }
}; 