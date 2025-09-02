import React, { useEffect, useState } from 'react';
import { getNews } from '../services/api';

const NewsFeed = () => {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const data = await getNews();
        setItems(data?.news || []);
      } catch (e) {
        setError(e?.message || 'Failed to load news');
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) return <div>Loading news…</div>;
  if (error) return <div style={{ color: 'red' }}>{error}</div>;

  return (
    <div>
      <h2>News</h2>
      {items.length === 0 ? (
        <div>No news available.</div>
      ) : (
        <ul style={{ listStyle: 'none', padding: 0 }}>
          {items.map((n, idx) => (
            <li key={idx} style={{ borderBottom: '1px solid #eee', padding: '8px 0' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <a href={n.url} target="_blank" rel="noreferrer">{n.title}</a>
                <span style={{ opacity: 0.8 }}>Sentiment: {n.sentiment ?? 'N/A'}</span>
              </div>
              {n.summary && <div style={{ marginTop: 4, opacity: 0.85 }}>{n.summary}</div>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default NewsFeed;


