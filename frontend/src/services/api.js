const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:8000';

async function httpGet(path) {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`Request failed: ${res.status}`);
  return res.json();
}

export async function getRecommendations() {
  return httpGet('/recommendations');
}

export async function getPortfolio() {
  return httpGet('/portfolio');
}

export async function getNews() {
  return httpGet('/news');
}


