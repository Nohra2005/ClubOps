import type { ReactNode } from 'react';

const URL_PATTERN = /(https?:\/\/[^\s<>"')\]]+)/g;

/** Plain text in which every http(s) address is a link that opens in a new tab. Nothing else is interpreted. */
export function Linkified({ text }: { text: string }) {
  const parts: ReactNode[] = [];
  text.split(URL_PATTERN).forEach((part, index) => {
    if (index % 2 === 1) {
      const trimmed = part.replace(/[.,;:!?]+$/, '');
      parts.push(
        <a key={index} href={trimmed} target="_blank" rel="noopener noreferrer">
          {trimmed}
        </a>,
      );
      if (trimmed.length < part.length) parts.push(part.slice(trimmed.length));
    } else if (part) {
      parts.push(part);
    }
  });
  return <>{parts}</>;
}
