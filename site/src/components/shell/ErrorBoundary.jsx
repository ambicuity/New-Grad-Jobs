import { Component } from 'react';
import { BBG, FONT_STACK, REPO_URL } from '../../lib/theme.js';

// Last line of defence against a blank page: any render error below this
// boundary shows a terminal-styled notice with a reload button and links to
// the README and the raw jobs.json feed, instead of React unmounting the tree.
// Error boundaries still have to be class components in React 18.
export class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error(`[terminal] render crash (${this.props.scope || 'app'}):`, error, info && info.componentStack);
  }

  render() {
    if (!this.state.error) return this.props.children;
    const linkStyle = { color: BBG.acc, textDecoration: 'none', borderBottom: `1px dotted ${BBG.acc}` };
    return (
      <div role="alert" style={{
        height: '100%', background: BBG.bg, color: BBG.ink, padding: '32px 24px',
        fontFamily: FONT_STACK, fontSize: 12, lineHeight: 1.7,
      }}>
        <div style={{ color: BBG.hot, fontWeight: 700, letterSpacing: 0.8 }}>ERR · SOMETHING BROKE</div>
        <div style={{ color: BBG.dim, marginTop: 6 }}>
          The {this.props.scope ? `${this.props.scope} view` : 'terminal'} hit an unexpected error. Reloading usually fixes it.
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 14, marginTop: 16 }}>
          <button onClick={() => window.location.reload()} style={{
            background: BBG.acc, color: '#000', border: 'none', padding: '8px 14px', minHeight: 36,
            fontFamily: 'inherit', fontWeight: 700, letterSpacing: 0.5, cursor: 'pointer',
          }}>RELOAD ↻</button>
          <a href={`${REPO_URL}#readme`} target="_blank" rel="noopener noreferrer" style={linkStyle}>README ↗</a>
          <a href="./jobs.json" style={linkStyle}>raw jobs.json</a>
        </div>
      </div>
    );
  }
}
