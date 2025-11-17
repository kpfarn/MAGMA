import React, { useEffect, useMemo, useState } from 'react';
import { getPortfolio } from '../services/api';

const currency = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 });
const percent = new Intl.NumberFormat('en-US', { style: 'percent', minimumFractionDigits: 2 });

const SummaryCard = ({ label, value, subtext }) => (
  <div style={{ flex: 1, padding: 16, border: '1px solid #eee', borderRadius: 8, background: '#fafafa', minWidth: 160 }}>
    <div style={{ fontSize: 12, color: '#666', textTransform: 'uppercase' }}>{label}</div>
    <div style={{ fontSize: 20, fontWeight: 600, marginTop: 4 }}>{value}</div>
    {subtext && <div style={{ fontSize: 12, color: '#999', marginTop: 4 }}>{subtext}</div>}
  </div>
);

const formatCurrency = (value) => (value === null || value === undefined ? '—' : currency.format(value));
const formatPercent = (value) => (value === null || value === undefined ? '—' : percent.format(value));

const Portfolio = () => {
  const [portfolio, setPortfolio] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const data = await getPortfolio();
        setPortfolio(data || { holdings: [], summary: {} });
      } catch (e) {
        setError(e?.message || 'Failed to load portfolio');
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const holdings = portfolio?.holdings || [];
  const summary = portfolio?.summary || {};

  const sectorExposure = useMemo(
    () => (summary.sector_exposure || []).map((row) => ({ ...row, displayWeight: formatPercent(row.weight || 0) })),
    [summary.sector_exposure]
  );
  const topPositions = summary.largest_positions || [];

  if (loading) return <div>Loading portfolio…</div>;
  if (error) return <div style={{ color: 'red' }}>{error}</div>;

  return (
    <div>
      <h2>Portfolio Overview</h2>
      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginBottom: 24 }}>
        <SummaryCard label="Market Value" value={formatCurrency(summary.total_value)} />
        <SummaryCard
          label="Net PnL"
          value={formatCurrency(summary.total_pnl)}
          subtext={formatPercent((summary.pnl_pct || 0) / 100)}
        />
        <SummaryCard
          label="Health Score"
          value={summary.health_score !== undefined ? summary.health_score.toFixed(1) : '—'}
          subtext="0 = weak, 10 = strong"
        />
      </div>

      {holdings.length === 0 ? (
        <div>No holdings found.</div>
      ) : (
        <>
          <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: 24 }}>
            <thead>
              <tr>
                <th style={thLeft}>Ticker</th>
                <th style={thRight}>Shares</th>
                <th style={thRight}>Last</th>
                <th style={thRight}>Market Value</th>
                <th style={thRight}>Weight</th>
                <th style={thRight}>Avg Cost</th>
                <th style={thRight}>PnL</th>
                <th style={thRight}>PnL %</th>
                <th style={thLeft}>Sector</th>
              </tr>
            </thead>
            <tbody>
              {holdings.map((h, idx) => (
                <tr key={h.ticker || idx}>
                  <td style={tdStyle}>{h.ticker}</td>
                  <td style={tdRight}>{h.shares?.toFixed?.(2) ?? h.shares}</td>
                  <td style={tdRight}>{formatCurrency(h.last)}</td>
                  <td style={tdRight}>{formatCurrency(h.market_value)}</td>
                  <td style={tdRight}>{formatPercent(h.weight || 0)}</td>
                  <td style={tdRight}>{formatCurrency(h.avg_cost)}</td>
                  <td style={tdRight}>{formatCurrency(h.pnl)}</td>
                  <td style={tdRight}>{formatPercent((h.pnl_pct || 0) / 100)}</td>
                  <td style={tdStyle}>{h.fundamentals?.sector || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
            <div style={{ flex: 1, minWidth: 280 }}>
              <h3>Sector Exposure</h3>
              {sectorExposure.length === 0 ? (
                <div style={{ color: '#777' }}>No sector metadata yet.</div>
              ) : (
                <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                  {sectorExposure.map((sector) => (
                    <li key={sector.sector} style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0' }}>
                      <span>{sector.sector}</span>
                      <span>{sector.displayWeight}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
            <div style={{ flex: 1, minWidth: 280 }}>
              <h3>Top Positions</h3>
              {topPositions.length === 0 ? (
                <div style={{ color: '#777' }}>No positions to highlight.</div>
              ) : (
                <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                  {topPositions.map((pos) => (
                    <li key={pos.ticker} style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0' }}>
                      <span>{pos.ticker}</span>
                      <span>{formatPercent(pos.weight || 0)}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
};

const thBase = { borderBottom: '1px solid #ddd', padding: 8, textTransform: 'uppercase', fontSize: 12, letterSpacing: 0.5 };
const thLeft = { ...thBase, textAlign: 'left' };
const thRight = { ...thBase, textAlign: 'right' };
const tdStyle = { padding: 8, textAlign: 'left', borderBottom: '1px solid #f1f1f1' };
const tdRight = { ...tdStyle, textAlign: 'right' };

export default Portfolio;
