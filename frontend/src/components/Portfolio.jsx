import React, { useEffect, useState } from 'react';
import { getPortfolio } from '../services/api';

const Portfolio = () => {
  const [portfolio, setPortfolio] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const data = await getPortfolio();
        setPortfolio(data?.holdings || []);
      } catch (e) {
        setError(e?.message || 'Failed to load portfolio');
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) return <div>Loading portfolio…</div>;
  if (error) return <div style={{ color: 'red' }}>{error}</div>;

  return (
    <div>
      <h2>Portfolio</h2>
      {portfolio.length === 0 ? (
        <div>No holdings found.</div>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th style={{ textAlign: 'left', borderBottom: '1px solid #ddd', padding: 8 }}>Ticker</th>
              <th style={{ textAlign: 'right', borderBottom: '1px solid #ddd', padding: 8 }}>Shares</th>
              <th style={{ textAlign: 'right', borderBottom: '1px solid #ddd', padding: 8 }}>Avg Cost</th>
              <th style={{ textAlign: 'right', borderBottom: '1px solid #ddd', padding: 8 }}>PnL</th>
            </tr>
          </thead>
          <tbody>
            {portfolio.map((h, idx) => (
              <tr key={idx}>
                <td style={{ padding: 8 }}>{h.ticker}</td>
                <td style={{ padding: 8, textAlign: 'right' }}>{h.shares}</td>
                <td style={{ padding: 8, textAlign: 'right' }}>{h.avg_cost}</td>
                <td style={{ padding: 8, textAlign: 'right' }}>{h.pnl}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};

export default Portfolio;


