import { useEffect, useId, useRef, type ReactNode } from 'react';
import { Link } from 'react-router';
import {
  AlertCircle,
  ArrowRight,
  Check,
  CircleHelp,
  FileText,
  Mail,
  MessageSquare,
  NotebookPen,
  RefreshCw,
  X,
} from 'lucide-react';
import type { Origin, Source } from '../api/types';

const statusLabels: Record<string, string> = {
  draft: 'Draft',
  planned: 'Planned',
  approved: 'Approved',
  done: 'Done',
  closed: 'Closed',
  cancelled: 'Cancelled',
  todo: 'To do',
  due_today: 'Due today',
  overdue: 'Overdue',
  needed: 'Needed',
  requested: 'Requested',
  granted: 'Granted',
  uncertain: 'Check this',
  current: 'Current',
  may_be_outdated: 'May be outdated',
  retired: 'Retired',
  pending: 'Needs review',
  waiting_second_president: 'Waiting for 2nd president',
};
export function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`status status-${status}`}>
      {statusLabels[status] ?? status.replaceAll('_', ' ')}
    </span>
  );
}
const originLabels: Record<Origin, string> = {
  stated: 'You said',
  retrieved: 'From memory',
  computed: 'Calculated',
  inferred: 'Guessed · check this',
  default: 'Default · check this',
  missing: 'Missing',
};
export function OriginTag({ origin }: { origin: Origin }) {
  return <span className={`origin origin-${origin}`}>{originLabels[origin]}</span>;
}
export function SourceChip({ source }: { source: Source }) {
  const Icon =
    source.kind === 'email'
      ? Mail
      : source.kind === 'note'
        ? MessageSquare
        : source.kind === 'debrief'
          ? NotebookPen
          : FileText;
  return (
    <Link
      className="source-chip"
      to={`/knowledge/${encodeURIComponent(source.item_id)}`}
      state={{ source }}
      title={source.quote}
    >
      <Icon size={11} />
      {source.label}
      <ArrowRight size={10} />
    </Link>
  );
}
export function NotSure({
  ask,
  lookIn,
  explanation,
}: {
  ask: { who: string; role?: string | null };
  lookIn?: string | null;
  explanation?: string;
}) {
  return (
    <div className="not-sure">
      <CircleHelp size={21} />
      <div>
        <strong>I don't know this yet.</strong>
        {explanation && explanation !== "I don't know this yet." && <p>{explanation}</p>}
        <p>
          <span>Ask</span> {ask.who}
          {ask.role && <small> · {ask.role}</small>}
        </p>
        {lookIn && (
          <p>
            <span>Look in</span> {lookIn}
          </p>
        )}
      </div>
    </div>
  );
}
export function ErrorNotice({ message, retry }: { message?: string; retry?: () => void }) {
  return message ? (
    <div className="notice error" role="alert">
      <AlertCircle size={17} />
      <div>
        {message}
        {retry && (
          <button className="text-button" onClick={retry}>
            <RefreshCw size={13} /> Try again
          </button>
        )}
      </div>
    </div>
  ) : null;
}
export function FallbackNotice() {
  return (
    <div className="notice warning" role="status">
      <AlertCircle size={17} />
      <span>Simple version: some checks were skipped. Please review carefully.</span>
    </div>
  );
}
export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="empty-panel">
      <NotebookPen size={26} />
      <h2>{title}</h2>
      {description && <p>{description}</p>}
      {action}
    </div>
  );
}
export function Loading({ rows = 3 }: { rows?: number }) {
  return (
    <div className="loading-block" role="status" aria-label="Loading saved information">
      {Array.from({ length: rows }, (_, i) => (
        <div className="skeleton-row" key={i}>
          <div className="skeleton skeleton-icon" />
          <div>
            <div className="skeleton" />
            <div className="skeleton short" />
          </div>
        </div>
      ))}
    </div>
  );
}
export function Resource({
  loading,
  error,
  retry,
  children,
}: {
  loading: boolean;
  error?: string;
  retry: () => void;
  children: ReactNode;
}) {
  return loading ? (
    <Loading />
  ) : error ? (
    <ErrorNotice message={error} retry={retry} />
  ) : (
    <>{children}</>
  );
}
export function FilterTabs<T extends string>({
  value,
  options,
  onChange,
  label,
}: {
  value: T;
  options: { value: T; label: string; count?: number }[];
  onChange: (value: T) => void;
  label: string;
}) {
  return (
    <div className="filter-tabs" role="group" aria-label={label}>
      {options.map((option) => (
        <button
          key={option.value}
          aria-pressed={value === option.value}
          className={value === option.value ? 'selected' : ''}
          onClick={() => onChange(option.value)}
        >
          {option.label}
          {option.count !== undefined && <span>{option.count}</span>}
        </button>
      ))}
    </div>
  );
}
export function Modal({
  open,
  title,
  onClose,
  children,
}: {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const id = useId();
  useEffect(() => {
    const element = dialog.current;
    if (open && !element?.open) element?.showModal();
    if (!open && element?.open) element.close();
    return () => {
      if (element?.open) element.close();
    };
  }, [open]);
  return (
    <dialog
      ref={dialog}
      className="modal"
      aria-labelledby={id}
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      onClick={(event) => {
        if (event.target === event.currentTarget) {
          const rect = event.currentTarget.getBoundingClientRect();
          if (
            event.clientX < rect.left ||
            event.clientX > rect.right ||
            event.clientY < rect.top ||
            event.clientY > rect.bottom
          )
            onClose();
        }
      }}
    >
      <div className="modal-heading">
        <h2 id={id}>{title}</h2>
        <button className="icon-button" aria-label="Close dialog" onClick={onClose}>
          <X size={19} />
        </button>
      </div>
      {children}
    </dialog>
  );
}
export function ApproveBar({
  title,
  description,
  approvedBy,
  pending,
  onApprove,
  onChanges,
}: {
  title: string;
  description: string;
  approvedBy?: string;
  pending?: boolean;
  onApprove?: () => void;
  onChanges?: () => void;
}) {
  return (
    <div className={`approve-bar${approvedBy ? ' is-approved' : ''}`}>
      <div className="approve-icon">
        <Check size={18} />
      </div>
      <div>
        <strong>{approvedBy ? `Approved by ${approvedBy}` : title}</strong>
        <p>{description}</p>
      </div>
      {!approvedBy && (
        <div className="approve-actions">
          {onChanges && (
            <button className="button" onClick={onChanges} disabled={pending}>
              Request changes
            </button>
          )}
          {onApprove && (
            <button className="button primary" onClick={onApprove} disabled={pending}>
              <Check size={15} />
              {pending ? 'Approving…' : 'Approve plan'}
            </button>
          )}
        </div>
      )}
    </div>
  );
}

export function PageHeading({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="page-heading">
      <div>
        <h1>{title}</h1>
        {description && <p>{description}</p>}
      </div>
      {action && <div className="heading-action">{action}</div>}
    </div>
  );
}
