import { Link } from "react-router-dom";

const demoWorkflowId = "wf-demo";

const WorkflowsPage = () => {
  return (
    <div className="card stack">
      <header className="card__header">
        <div>
          <h2>Workflows</h2>
          <p className="text-subtle">
            Curate workflow definitions and open them in the interactive builder.
          </p>
        </div>
      </header>
      <div className="card card--surface">
        <h3>Example Workflow</h3>
        <p className="text-subtle">
          Kick the tyres with the sample definition that ships with the local worker.
        </p>
        <Link className="btn" to={`/workflows/${demoWorkflowId}`}>
          Open Builder
        </Link>
      </div>
      <p className="text-subtle">
        Full workflow catalog management is coming soon — for now, use the REST API or CLI to
        create new definitions and open them directly via URL.
      </p>
    </div>
  );
};

export default WorkflowsPage;
