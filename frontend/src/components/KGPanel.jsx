import React, { useEffect, useState } from 'react';

/**
 * KGPanel — live view of what HINATA is learning.
 * Shows real-time kg_update events + fetches summary from the backend.
 */
export default function KGPanel({ events }) {
  const [summary, setSummary] = useState(null);

  useEffect(() => {
    const load = () => fetch('/api/kg/summary').then((r) => r.json()).then(setSummary).catch(() => {});
    load();
    const t = setInterval(load, 10000);
    return () => clearInterval(t);
  }, [events]);

  return (
    <section className="kg-panel">
      <h3>Knowledge Graph</h3>
      {summary && (
        <div className="kg-stats">
          <span>{summary.entities} entities</span>
          <span>{summary.triples} triples</span>
          <span>{summary.explicit_facts} facts</span>
        </div>
      )}
      <div className="kg-events">
        {events.slice(-4).reverse().map((ev, i) => (
          <div key={i} className="kg-event">
            {ev.facts_added?.length > 0
              ? <>learned: {ev.facts_added.map((f) => f.object).join(', ')}</>
              : <>noted: {ev.entities.join(', ') || '—'}</>}
          </div>
        ))}
      </div>
    </section>
  );
}
