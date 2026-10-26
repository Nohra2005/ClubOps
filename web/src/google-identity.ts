/** Google's public browser SDK. Credentials stay in memory until exchanged for an HttpOnly session. */
export interface GoogleIdentity {
  initialize(options: {
    client_id: string;
    auto_select: boolean;
    callback: (value: { credential: string }) => void;
  }): void;
  renderButton(
    element: HTMLElement,
    options: { theme: string; size: string; width: number; text: string },
  ): void;
  disableAutoSelect(): void;
}
declare global {
  interface Window {
    google?: { accounts: { id: GoogleIdentity } };
  }
}
let loading: Promise<GoogleIdentity> | undefined;

export function loadGoogleIdentity(): Promise<GoogleIdentity> {
  if (window.google?.accounts.id) return Promise.resolve(window.google.accounts.id);
  if (loading) return loading;
  loading = new Promise<GoogleIdentity>((resolve, reject) => {
    const script = document.createElement('script');
    const fail = () => {
      clearTimeout(timer);
      script.remove();
      loading = undefined;
      reject(new Error('Google sign-in could not load. Check your connection and try again.'));
    };
    const timer = setTimeout(fail, 15_000);
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;
    script.onload = () => {
      if (!window.google?.accounts.id) {
        fail();
        return;
      }
      clearTimeout(timer);
      resolve(window.google.accounts.id);
    };
    script.onerror = fail;
    document.head.append(script);
  });
  return loading;
}
