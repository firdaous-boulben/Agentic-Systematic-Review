export default function StatCard({ item }) {
  return (
    <div className="stat-card">
      <div className="stat-card-top">
        <span>{item.title}</span>
        <div className={`stat-icon ${item.color}`}>
          <i className={`bi ${item.icon}`}></i>
        </div>
      </div>

      <h3>{item.value}</h3>
      <p>{item.description}</p>
    </div>
  );
}