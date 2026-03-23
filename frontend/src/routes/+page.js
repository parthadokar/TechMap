const API = 'http://localhost:8000';

export async function load({ fetch }) {
  const res = await fetch(`${API}/companies`);
  if (!res.ok) return { companies: [] };
  return { companies: await res.json() };
}
