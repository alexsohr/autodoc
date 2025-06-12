import { NextRequest, NextResponse } from 'next/server';

// The target backend server base URL, derived from environment variable or defaulted.
const TARGET_SERVER_BASE_URL = process.env.SERVER_BASE_URL || 'http://localhost:8001';

// This route handles non-streaming chat completion requests.
export async function POST(req: NextRequest) {
  try {
    const requestBody = await req.json();

    const targetUrl = `${TARGET_SERVER_BASE_URL}/chat/completions`;

    // Make the actual request to the backend service
    const backendResponse = await fetch(targetUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify(requestBody),
    });

    // If the backend service returned an error, forward that error to the client
    if (!backendResponse.ok) {
      const errorBody = await backendResponse.text();
      return new NextResponse(errorBody, {
        status: backendResponse.status,
        statusText: backendResponse.statusText,
      });
    }

    // Get the JSON response from the backend
    const responseBody = await backendResponse.json();

    // Send the JSON response to the client
    return NextResponse.json(responseBody, {
      status: backendResponse.status,
    });

  } catch (error) {
    console.error('Error in API proxy route (/api/chat/complete):', error);
    let errorMessage = 'Internal Server Error in proxy';
    if (error instanceof Error) {
      errorMessage = error.message;
    }
    return new NextResponse(JSON.stringify({ error: errorMessage }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}

// Handle OPTIONS requests for CORS preflight
export async function OPTIONS() {
  return new NextResponse(null, {
    status: 204, // No Content
    headers: {
      'Access-Control-Allow-Origin': '*', // Be more specific in production if needed
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    },
  });
} 