// Runs only on the server — uses internal Docker URL when in a container,
// falls back to localhost for normal development.
const API = process.env.INTERNAL_API_URL ?? 'http://localhost:8000';

export async function load({ fetch }) {
  const res = await fetch(`${API}/companies`);
  if (!res.ok) return { companies: [] };
  return { companies: await res.json() };
}
