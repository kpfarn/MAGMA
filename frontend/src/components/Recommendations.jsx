import React, { useEffect, useState } from 'react';
import { getRecommendations } from '../services/api';

const Recommendations = () => {
  const [recs, setRecs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const data = await getRecommendations();
        setRecs(data?.recommendations || []);
      } catch (e) {
        setError(e?.message || 'Failed to load recommendations');
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) return <div>Loading recommendations…</div>;
  if (error) return <div style={{ color: 'red' }}>{error}</div>;

  return (
    <div>
      <h2>Today's Recommendations</h2>
      {recs.length === 0 ? (
        <div>No recommendations available.</div>
      ) : (
        <ul style={{ listStyle: 'none', padding: 0 }}>
          {recs.map((r, idx) => (
            <li key={idx} style={{ border: '1px solid #ddd', borderRadius: 8, padding: 12, marginBottom: 8 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <strong>{r.ticker}</strong>
                <span>{r.action} · {Math.round((r.confidence || 0) * 100)}%</span>
              </div>
              {r.reason && <div style={{ marginTop: 6, opacity: 0.85 }}>{r.reason}</div>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default Recommendations;


