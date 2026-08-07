import { useState, type FormEvent } from "react";
import { useMutation } from "@tanstack/react-query";
import { uploadDocument } from "../api/client";
import type { UploadResponse } from "../types";

const ACCEPT = ".pdf,.txt,.md,.markdown,.csv,.json,.log";

export function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<UploadResponse | null>(null);

  const mutation = useMutation({
    mutationFn: uploadDocument,
    onSuccess: (data) => setResult(data),
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!file) return;
    setResult(null);
    mutation.mutate(file);
  }

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <h1>Upload documents</h1>
          <p className="muted">
            Saves to storage, extracts text, and embeds into Pinecone when configured.
            Supported: {ACCEPT.replaceAll(",", ", ")}
          </p>
        </div>
      </div>

      <form className="panel form-grid" onSubmit={onSubmit}>
        <label className="file-drop">
          <span>Choose a file</span>
          <input
            type="file"
            accept={ACCEPT}
            onChange={(e) => setFile(e.target.files?.[0] || null)}
          />
          {file && <p className="mono">{file.name}</p>}
        </label>

        <div className="actions">
          <button
            type="submit"
            className="btn primary"
            disabled={!file || mutation.isPending}
          >
            {mutation.isPending ? "Uploading…" : "Upload & ingest"}
          </button>
        </div>
      </form>

      {mutation.isError && <p className="error">{(mutation.error as Error).message}</p>}

      {result && (
        <div className="panel success-panel">
          <h2>Upload complete</h2>
          <p className="muted">{result.message}</p>
          <p className="mono">
            {result.filename} · {result.chunks} chunks · {result.chars} chars
            {result.pinecone ? " · Pinecone synced" : " · Pinecone skipped"}
          </p>
        </div>
      )}
    </section>
  );
}
