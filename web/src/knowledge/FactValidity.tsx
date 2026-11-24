import { formatDate } from '../lib';

/** A reminder to check the source, never an inferred expiry or university rule. */
export function needsEndDateCheck(validTo: string | null | undefined, text: string) {
  return (
    validTo === null &&
    /\b(?:\d{4}-\d{2}-\d{2}|\d{1,2}[/.]\d{1,2}(?:[/.]\d{2,4})?|(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?\s+\d{1,2}|\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)|this (?:term|semester)|(?:fall|spring|summer|winter) (?:term|semester|20\d{2}))\b/i.test(
      text,
    )
  );
}

export default function FactValidity({ validTo, text }: { validTo?: string | null; text: string }) {
  return (
    <div className="fact-validity">
      <p className="inline-note">
        {validTo === undefined ? (
          'End date unavailable on this server'
        ) : validTo === null ? (
          'No end date'
        ) : (
          <>
            Valid until <time dateTime={validTo}>{formatDate(validTo, true)}</time>
          </>
        )}
      </p>
      {needsEndDateCheck(validTo, text) && (
        <p className="notice warning">
          This text mentions a date or term but has no end date. Check the source and confirm
          whether an end date is needed.
        </p>
      )}
    </div>
  );
}
