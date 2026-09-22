export const API_BASE_URL = 'https://civicos-480a.onrender.com';

export async function healthCheck() {
  const res = await fetch(`${API_BASE_URL}/healthz`, { cache: 'no-store' });
  if (!res.ok) {
    throw new Error(`Health check failed: ${res.status}`);
  }
  return res.json();
}

export async function processDocument(payload: string) {
  const res = await fetch(`${API_BASE_URL}/api/v1/process`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      text: payload,
      source: 'frontend-demo',
    }),
  });

  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`API request failed: ${res.status} ${errorText}`);
  }

  return res.json();
}
