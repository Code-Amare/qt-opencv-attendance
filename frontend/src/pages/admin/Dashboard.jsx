import { useEffect, useState } from "react";
import api from "../../lib/axios"; // your axios instance (baseURL + auth header)

const StatCard = ({ label, value }) => (
  <div className="rounded-xl border p-4 shadow-sm">
    <p className="text-sm text-gray-500">{label}</p>
    <p className="text-3xl font-semibold">{value}</p>
  </div>
);

const Dashboard = () => {
  const [stats, setStats] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const load = async () => {
      try {
        const [statsRes, sessionsRes] = await Promise.all([
          api.get("/admin/stats/"),
          api
            .get("/admin/sessions/")
            .catch((e) =>
              e.response?.status === 404
                ? { data: { sessions: [] } }
                : Promise.reject(e),
            ),
        ]);
        setStats(statsRes.data);
        setSessions(sessionsRes.data.sessions);
      } catch (err) {
        setError(err.response?.data?.error || "Failed to load dashboard");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  if (loading) return <p className="p-6">Loading...</p>;
  if (error) return <p className="p-6 text-red-600">{error}</p>;

  return (
    <div className="mx-auto max-w-6xl space-y-8 p-6">
      <h1 className="text-2xl font-bold">Admin Dashboard</h1>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatCard label="Total users" value={stats.total_users} />
        <StatCard label="Active users" value={stats.active_users} />
        <StatCard label="Face registered" value={stats.users_with_face} />
        <StatCard label="Sessions" value={stats.total_sessions} />
      </div>

      <section>
        <h2 className="mb-3 text-lg font-semibold">Attendance by status</h2>
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          {Object.entries(stats.attendance_by_status).map(([status, count]) => (
            <StatCard key={status} label={status} value={count} />
          ))}
        </div>
      </section>

      <section>
        <h2 className="mb-3 text-lg font-semibold">Sessions</h2>
        {sessions.length === 0 ? (
          <p className="text-gray-500">No sessions yet</p>
        ) : (
          <ul className="divide-y rounded-xl border">
            {sessions.map((s) => (
              <li key={s.id} className="flex justify-between p-3">
                <span>{s.name}</span>
                <span className="text-sm text-gray-500">{s.status}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
};

export default Dashboard;
