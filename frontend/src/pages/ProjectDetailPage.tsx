import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { fetchProject } from "../api/client";
import type { CatalogFile } from "../types";

function fileInFolder(filePath: string, folder: string): boolean {
  const normalized = filePath.replace(/\\/g, "/");
  const prefix = folder.replace(/\\/g, "/").replace(/\/$/, "");
  return normalized === prefix || normalized.startsWith(`${prefix}/`);
}

export function ProjectDetailPage() {
  const { owner = "", repo = "" } = useParams();
  const [filter, setFilter] = useState("");
  const [selectedFolder, setSelectedFolder] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<CatalogFile | null>(null);
  const selectedFileRef = useRef<HTMLLIElement | null>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ["project", owner, repo],
    queryFn: () => fetchProject(owner, repo),
    enabled: Boolean(owner && repo),
  });

  const files = useMemo(() => {
    if (!data?.files) return [];
    let list = data.files;

    if (selectedFolder) {
      list = list.filter((f) => fileInFolder(f.path, selectedFolder));
    }

    const q = filter.trim().toLowerCase();
    if (!q) return list;
    return list.filter(
      (f) =>
        f.path.toLowerCase().includes(q) ||
        f.name.toLowerCase().includes(q) ||
        (f.symbols || []).some((s) => s.toLowerCase().includes(q)),
    );
  }, [data, filter, selectedFolder]);

  useEffect(() => {
    if (selectedFile && selectedFileRef.current) {
      selectedFileRef.current.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }, [selectedFile]);

  // Drop selection if the file is no longer in the filtered list
  useEffect(() => {
    if (selectedFile && !files.some((f) => f.path === selectedFile.path)) {
      setSelectedFile(null);
    }
  }, [files, selectedFile]);

  function selectFolder(folder: string | null) {
    setSelectedFolder(folder);
    setSelectedFile(null);
  }

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <p className="eyebrow">
            <Link to="/">Projects</Link> / {owner}/{repo}
          </p>
          <h1>{data?.project_name || repo}</h1>
          <p className="muted mono">
            {data ? `${data.branch} · ${data.files.length} files` : "Loading catalog…"}
          </p>
        </div>
        <Link className="btn primary" to={`/ask?project=${encodeURIComponent(`${owner}/${repo}`)}`}>
          Ask about this project
        </Link>
      </div>

      {isLoading && <p className="muted">Loading catalog…</p>}
      {error && <p className="error">{(error as Error).message}</p>}

      {data && (
        <>
          <div className="toolbar">
            <input
              className="input"
              placeholder="Filter files or symbols…"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
            />
          </div>

          <div className="catalog-grid">
            <aside className="panel">
              <h2>Folders</h2>
              <ul className="folder-list">
                <li>
                  <button
                    type="button"
                    className={selectedFolder === null ? "folder-btn active" : "folder-btn"}
                    onClick={() => selectFolder(null)}
                  >
                    All files
                  </button>
                </li>
                {data.folders.length === 0 && (
                  <li className="muted">No nested folders</li>
                )}
                {data.folders.map((folder) => (
                  <li key={folder}>
                    <button
                      type="button"
                      className={
                        selectedFolder === folder ? "folder-btn active mono" : "folder-btn mono"
                      }
                      onClick={() => selectFolder(folder)}
                    >
                      {folder}
                    </button>
                  </li>
                ))}
              </ul>
            </aside>

            <div className="panel">
              <h2>
                Files ({files.length})
                {selectedFolder ? (
                  <span className="muted"> in {selectedFolder}</span>
                ) : null}
              </h2>
              <ul className="file-list">
                {files.map((file) => {
                  const isSelected = selectedFile?.path === file.path;
                  return (
                    <li
                      key={file.path}
                      ref={isSelected ? selectedFileRef : null}
                      className={isSelected ? "file-row selected" : "file-row"}
                    >
                      <button
                        type="button"
                        className="file-btn"
                        onClick={() => setSelectedFile(file)}
                      >
                        <p className="file-path mono">{file.path}</p>
                        <p className="muted">
                          <span className={`badge ${file.type}`}>{file.type}</span>
                          {file.language ? ` · ${file.language}` : ""}
                          {file.symbols?.length
                            ? ` · ${file.symbols.slice(0, 4).join(", ")}`
                            : ""}
                        </p>
                      </button>
                    </li>
                  );
                })}
                {files.length === 0 && <li className="muted">No matching files</li>}
              </ul>
            </div>
          </div>

          {selectedFile && (
            <div className="panel file-detail" id="selected-file">
              <div className="page-header">
                <div>
                  <p className="eyebrow">Selected file</p>
                  <h2 className="mono">{selectedFile.path}</h2>
                  <p className="muted">
                    <span className={`badge ${selectedFile.type}`}>{selectedFile.type}</span>
                    {selectedFile.language ? ` · ${selectedFile.language}` : ""}
                  </p>
                </div>
                <Link
                  className="btn primary"
                  to={`/ask?project=${encodeURIComponent(`${owner}/${repo}`)}&file=${encodeURIComponent(selectedFile.path)}`}
                >
                  Ask about this file
                </Link>
              </div>
              {selectedFile.symbols && selectedFile.symbols.length > 0 && (
                <div className="symbols">
                  <p className="bubble-label">Symbols</p>
                  <ul className="symbol-list">
                    {selectedFile.symbols.map((s) => (
                      <li key={s} className="mono">
                        {s}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </section>
  );
}
