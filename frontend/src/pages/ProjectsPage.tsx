import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { fetchProjects } from "../api/client";

export function ProjectsPage() {
  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ["projects"],
    queryFn: fetchProjects,
  });

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <h1>Projects</h1>
          <p className="muted">Ingested GitHub catalogs ready for multi-agent Q&amp;A.</p>
        </div>
        <div className="actions">
          <button type="button" className="btn ghost" onClick={() => void refetch()} disabled={isFetching}>
            Refresh
          </button>
          <Link className="btn primary" to="/ingest">
            Ingest repo
          </Link>
        </div>
      </div>

      {isLoading && <p className="muted">Loading projects…</p>}
      {error && <p className="error">{(error as Error).message}</p>}

      {!isLoading && data && data.length === 0 && (
        <div className="empty">
          <h2>No projects yet</h2>
          <p className="muted">Ingest a GitHub repository to build a folders/files catalog.</p>
          <Link className="btn primary" to="/ingest">
            Ingest your first repo
          </Link>
        </div>
      )}

      {data && data.length > 0 && (
        <ul className="project-list">
          {data.map((project) => (
            <li key={project.project}>
              <Link to={`/projects/${project.owner}/${project.repo}`} className="project-row">
                <div>
                  <p className="project-title">{project.project}</p>
                  <p className="muted mono">
                    {project.branch} · {project.files_count} files · {project.folders_count} folders
                  </p>
                </div>
                <span className="chevron" aria-hidden>
                  →
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
