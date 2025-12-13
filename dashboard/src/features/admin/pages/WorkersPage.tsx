const WorkersPage = () => (
  <div className="admin-view">
    <div className="card stack">
      <h2>Worker Fleet</h2>
      <p className="text-subtle">
        Monitor connected workers, session health, and queued jobs. This view is coming soon.
      </p>
      <p>
        For now use the CLI (`scripts/run_scheduler_api.py --log-level debug`) to inspect worker registration and
        heartbeat events.
      </p>
    </div>
  </div>
);

export default WorkersPage;
