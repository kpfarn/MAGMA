import React from 'react';
import Recommendations from './components/Recommendations';
import Portfolio from './components/Portfolio';
import NewsFeed from './components/NewsFeed';

const App = () => {
  return (
    <div style={{ fontFamily: 'sans-serif', padding: 16, maxWidth: 1200, margin: '0 auto' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1>MAGMA</h1>
        <nav style={{ opacity: 0.7 }}>MVP Dashboard</nav>
      </header>

      <main style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginTop: 16 }}>
        <section style={{ gridColumn: '1 / span 2' }}>
          <Recommendations />
        </section>
        <section>
          <Portfolio />
        </section>
        <section>
          <NewsFeed />
        </section>
      </main>
    </div>
  );
};

export default App;


