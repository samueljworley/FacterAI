// src/static/js/api.js
export const API_ORIGIN = window.location.hostname.endsWith('facter.it.com')
  ? 'https://api.facter.it.com'
  : 'http://127.0.0.1:3000'; // dev fallback

export async function apiPost(path, body) {
  const res = await fetch(`${API_ORIGIN}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    credentials: 'omit'
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`);
  return res.json();
}
