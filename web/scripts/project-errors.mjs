/** Operational guidance without echoing API diagnostics, task bodies or credentials. */
export function publicFailure(result, response) {
  const diagnostics = `${result.stderr}\n${JSON.stringify(response?.errors ?? [])}`;
  if (
    /INSUFFICIENT_SCOPES|missing required scopes|requires.*scope|expected scopes/i.test(diagnostics)
  )
    return new Error(
      'GitHub Projects access is missing. Run gh auth refresh -s project and complete authorization; do not paste a token into this tool.',
    );
  if (/timeout|timed out/i.test(`${diagnostics}\n${result.stdout}`))
    return new Error(
      'GitHub timed out while applying the batch. Resume after read-back; do not blindly repeat mutations.',
    );
  if (/rate.?limit|submitted too quickly|abuse detection|secondary limit/i.test(diagnostics))
    return new Error(
      'GitHub temporarily throttled board writes. Wait before resuming; existing cards are reconciled without duplication.',
    );
  const known = new Set([
    'FORBIDDEN',
    'NOT_FOUND',
    'UNPROCESSABLE',
    'INTERNAL',
    'RATE_LIMITED',
    'INSUFFICIENT_SCOPES',
  ]);
  const kinds = [
    ...new Set(
      (response?.errors ?? []).map((entry) => entry.type).filter((kind) => known.has(kind)),
    ),
  ].join(', ');
  return new Error(
    `GitHub rejected the operation${kinds ? ` (${kinds})` : ''} or returned incomplete data. Check account access/schema and rerun; completed task cards are reconciled without deletion.`,
  );
}
