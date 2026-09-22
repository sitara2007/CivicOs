export const API_BASE = "https://civicos-480a.onrender.com";
export async function processDocument(text: string) {
  const res = await fetch(`${API_BASE}/api/v1/process`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}
