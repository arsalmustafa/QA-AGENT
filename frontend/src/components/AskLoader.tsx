export function AskLoader() {
  return (
    <div className="ask-loader" role="status" aria-live="polite">
      <div className="cube-scene" aria-hidden>
        <div className="cube">
          <div className="cube-face front" />
          <div className="cube-face back" />
          <div className="cube-face right" />
          <div className="cube-face left" />
          <div className="cube-face top" />
          <div className="cube-face bottom" />
        </div>
      </div>
      <p className="muted ask-loader-text">Retrieving context and generating answer…</p>
    </div>
  );
}
