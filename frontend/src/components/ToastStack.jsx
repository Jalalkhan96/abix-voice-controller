export default function ToastStack({ toasts, onDismiss }) {
  if (toasts.length === 0) return null;

  return (
    <div className="toast-stack">
      {toasts.map((toast) => (
        <div key={toast.id} className="toast">
          <span className="toast-message">{toast.message}</span>
          <button
            className="toast-dismiss"
            onClick={() => onDismiss(toast.id)}
            aria-label="Dismiss"
          >
            {"✕"}
          </button>
        </div>
      ))}
    </div>
  );
}
