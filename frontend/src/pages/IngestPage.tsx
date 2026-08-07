import { useState, type FormEvent } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { ingestRepo } from "../api/client";
import type { RepoIngestResponse } from "../types";

export function IngestPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [owner, setOwner] = useState("");
  const [repo, setRepo] = useState("");
  const [branch, setBranch] = useState("");
  const [pathPrefix, setPathPrefix] = useState("");
  const [result, setResult] = useState<RepoIngestResponse | null>(null);

  const mutation = useMutation({
    mutationFn: ingestRepo,
    onSuccess: (data) => {
      setResult(data);
      void queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    setResult(null);
    mutation.mutate({
      owner: owner.trim(),
      repo: repo.trim(),
      branch: branch.trim() || undefined,
      path_prefix: pathPrefix.trim() || undefined,
    });
  }

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <h1>Ingest GitHub repo</h1>
          <p className="muted">
            Fetches via GitHub API + tree-sitter — no local clone. Builds Pinecone chunks and a project catalog.
          </p>
        </div>
      </div>

      <form className="panel form-grid" onSubmit={onSubmit}>
        <label>
          Owner
          <input
            className="input"
            required
            placeholder="octocat"
            value={owner}
            onChange={(e) => setOwner(e.target.value)}
          />
        </label>
        <label>
          Repo
          <input
            className="input"
            required
            placeholder="Hello-World"
            value={repo}
            onChange={(e) => setRepo(e.target.value)}
          />
        </label>
        <label>
          Branch (optional)
          <input
            className="input"
            placeholder="main"
            value={branch}
            onChange={(e) => setBranch(e.target.value)}
          />
        </label>
        <label>
          Path prefix (optional)
          <input
            className="input"
            placeholder="src/"
            value={pathPrefix}
            onChange={(e) => setPathPrefix(e.target.value)}
          />
        </label>

        <div className="actions">
          <button type="submit" className="btn primary" disabled={mutation.isPending}>
            {mutation.isPending ? "Ingesting…" : "Start ingest"}
          </button>
        </div>
      </form>

      {mutation.isError && <p className="error">{(mutation.error as Error).message}</p>}

      {result && (
        <div className="panel success-panel">
          <h2>Ingest complete</h2>
          <p className="muted mono">
            {result.project} · branch {result.branch} · {result.files_ingested} files ·{" "}
            {result.chunks} chunks
            {result.pinecone ? " · Pinecone synced" : " · Pinecone skipped"}
          </p>
          <div className="actions">
            <Link className="btn primary" to={`/projects/${result.owner}/${result.repo}`}>
              Open catalog
            </Link>
            <button
              type="button"
              className="btn ghost"
              onClick={() =>
                navigate(`/ask?project=${encodeURIComponent(result.project)}`)
              }
            >
              Ask about it
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
