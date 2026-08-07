import { useMemo, useState, type FormEvent } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { askQuestion, fetchProjects } from "../api/client";
import { AskLoader } from "../components/AskLoader";
import type { AgentKind, ChatTurn } from "../types";

const AGENTS: Array<{ value: "" | AgentKind; label: string }> = [
  { value: "", label: "Auto" },
  { value: "code", label: "Code" },
  { value: "docs", label: "Docs" },
  { value: "security", label: "Security" },
];

export function AskPage() {
  const [params] = useSearchParams();
  const initialProject = params.get("project") || "";

  const initialFile = params.get("file") || "";
  const [question, setQuestion] = useState(
    initialFile ? `Explain what ${initialFile} does` : "",
  );
  const [project, setProject] = useState(initialProject);
  const [agent, setAgent] = useState<"" | AgentKind>("");
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [fileContext] = useState(initialFile);

  const projectsQuery = useQuery({
    queryKey: ["projects"],
    queryFn: fetchProjects,
  });

  const askMutation = useMutation({
    mutationFn: askQuestion,
  });

  const projectOptions = useMemo(
    () => projectsQuery.data || [],
    [projectsQuery.data],
  );

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const q = question.trim();
    if (!q || askMutation.isPending) return;

    const id = crypto.randomUUID();
    // Newest questions appear at the top
    setTurns((prev) => [{ id, question: q, pending: true }, ...prev]);
    setQuestion("");

    try {
      const response = await askMutation.mutateAsync({
        question: q,
        project: project || null,
        agent: agent || null,
        context: fileContext || null,
      });
      setTurns((prev) =>
        prev.map((t) => (t.id === id ? { ...t, pending: false, response } : t)),
      );
    } catch (err) {
      setTurns((prev) =>
        prev.map((t) =>
          t.id === id
            ? { ...t, pending: false, error: (err as Error).message }
            : t,
        ),
      );
    }
  }

  return (
    <section className="page ask-page">
      <div className="page-header">
        <div>
          <h1>Ask</h1>
          <p className="muted">
            Route to code, docs, or security agents. Answers include retrieved sources.
          </p>
        </div>
      </div>

      <form className="ask-controls panel" onSubmit={onSubmit}>
        <div className="control-row">
          <label>
            Project
            <select
              className="input"
              value={project}
              onChange={(e) => setProject(e.target.value)}
            >
              <option value="">All projects</option>
              {projectOptions.map((p) => (
                <option key={p.project} value={p.project}>
                  {p.project}
                </option>
              ))}
            </select>
          </label>

          <fieldset className="agent-fieldset">
            <legend>Agent</legend>
            <div className="agent-pills">
              {AGENTS.map((a) => (
                <button
                  key={a.label}
                  type="button"
                  className={agent === a.value ? "pill active" : "pill"}
                  onClick={() => setAgent(a.value)}
                >
                  {a.label}
                </button>
              ))}
            </div>
          </fieldset>
        </div>

        <label className="ask-input-label">
          Question
          <textarea
            className="input textarea"
            rows={3}
            placeholder="How does authentication work in this repo?"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
          />
        </label>

        <div className="actions">
          <button
            type="submit"
            className="btn primary"
            disabled={!question.trim() || askMutation.isPending}
          >
            {askMutation.isPending ? "Thinking…" : "Ask"}
          </button>
        </div>
      </form>

      <div className="chat-stream">
        {turns.length === 0 && (
          <div className="empty soft">
            <p className="muted">Ask a question about an ingested project or uploaded docs.</p>
          </div>
        )}

        {turns.map((turn) => (
          <article key={turn.id} className="chat-turn">
            <div className="bubble question">
              <p className="bubble-label">You</p>
              <p>{turn.question}</p>
            </div>

            <div className="bubble answer">
              {turn.pending && <AskLoader />}
              {turn.error && <p className="error">{turn.error}</p>}
              {turn.response && (
                <>
                  <div className="meta-row">
                    <span className={`badge ${turn.response.agent}`}>{turn.response.agent}</span>
                    {turn.response.model && (
                      <span className="muted mono">{turn.response.model}</span>
                    )}
                    {turn.response.project && (
                      <span className="muted mono">{turn.response.project}</span>
                    )}
                  </div>
                  <p className="answer-text">{turn.response.answer}</p>
                  {turn.response.sources.length > 0 && (
                    <div className="sources">
                      <p className="bubble-label">Sources</p>
                      <ul>
                        {turn.response.sources.map((s) => (
                          <li key={s} className="mono">
                            {s}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </>
              )}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
