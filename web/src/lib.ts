export function formatDate(value: string, long = false) {
  const date = new Date(value.length === 10 ? `${value}T12:00:00` : value);
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleDateString('en-GB', {
        day: 'numeric',
        month: long ? 'long' : 'short',
        ...(long ? { year: 'numeric' } : {}),
      });
}
export function formatTime(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? ''
    : date.toLocaleTimeString('en-GB', {
        hour: '2-digit',
        minute: '2-digit',
        timeZone: 'Asia/Beirut',
      });
}
export function downloadText(name: string, content: string) {
  const url = URL.createObjectURL(new Blob([content], { type: 'text/plain;charset=utf-8' }));
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = name;
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export async function copyText(content: string) {
  if (!navigator.clipboard)
    throw new Error('Clipboard access is unavailable. Select the text to copy it.');
  await navigator.clipboard.writeText(content);
}
