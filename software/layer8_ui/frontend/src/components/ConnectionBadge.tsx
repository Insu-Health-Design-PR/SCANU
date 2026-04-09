import type { ConnectionState } from "../types";

export function ConnectionBadge({ state }: { state: ConnectionState }) {
  return <span className={`conn conn-${state}`}>{state.toUpperCase()}</span>;
}
