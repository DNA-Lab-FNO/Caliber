export class ApiError extends Error {
  status: number;
  data?: unknown;

  constructor(message: string, status: number, data?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

export function getBasePath(): string {
  if (typeof window !== 'undefined') {
    const injected = (window as any).__CALIBER_BASE_PATH__;
    if (typeof injected === 'string' && injected.length > 0) {
      return injected.replace(/\/+$/, '');
    }
    // Fallback detection: if current location starts with /caliber
    if (window.location.pathname.startsWith('/caliber')) {
      return '/caliber';
    }
  }
  return '';
}

export function apiUrl(path: string): string {
  const base = getBasePath();
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  return `${base}${cleanPath}`;
}

export function getCookie(name: string): string {
  const escapedName = name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const match = document.cookie.match(new RegExp(`(?:^|;\\s*)${escapedName}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : '';
}

export async function parseResponse<T = any>(response: Response): Promise<T> {
  const contentType = (response.headers.get('content-type') || '').toLowerCase();
  const isJson = contentType.includes('application/json') || contentType.includes('+json');

  // 1. Successful Responses (200 - 299)
  if (response.ok) {
    if (response.status === 204 || response.headers.get('content-length') === '0') {
      return null as T;
    }
    if (isJson) {
      return (await response.json()) as T;
    }
    return (await response.text()) as unknown as T;
  }

  // 2. Error Responses with JSON body (from backend app like Django/FastAPI/Express)
  if (isJson) {
    try {
      const errorData = await response.json();
      const message =
        extractErrorMessage(errorData) || `Chyba požadavku (HTTP ${response.status})`;
      throw new ApiError(message, response.status, errorData);
    } catch (err) {
      if (err instanceof ApiError) throw err;
      // Fall through if JSON parsing unexpectedly failed
    }
  }

  // 3. Error Responses with HTML or plain text (Nginx / Gateway / Cloudflare)
  const rawText = await response.text();
  const serverMsg = extractServerMessage(rawText);

  if (response.status === 413) {
    throw new ApiError(
      `Soubor je příliš velký pro nahrání (HTTP 413 ${serverMsg || 'Request Entity Too Large'}).`,
      response.status
    );
  }
  if (response.status === 502 || response.status === 504) {
    throw new ApiError(
      `Server neodpovídá včas (HTTP ${response.status} ${serverMsg || 'Gateway Timeout'}). Zpracování trvalo příliš dlouho.`,
      response.status
    );
  }
  if (response.status === 403) {
    throw new ApiError(
      'Přístup odepřen nebo vypršela platnost relace (HTTP 403). Obnovte prosím stránku.',
      response.status
    );
  }

  throw new ApiError(
    serverMsg
      ? `Chyba serveru (${response.status}): ${serverMsg}`
      : `Neočekávaná odpověď serveru (HTTP ${response.status}).`,
    response.status
  );
}

function extractErrorMessage(data: any): string | null {
  if (!data || typeof data !== 'object') return null;
  const candidate = data.error || data.detail || data.message;
  if (typeof candidate === 'string') return candidate;
  if (typeof candidate === 'object' && candidate !== null) {
    return JSON.stringify(candidate);
  }
  return null;
}

function extractServerMessage(html: string): string {
  if (!html) return '';
  // Support multiline tags using the 's' flag
  const match = html.match(/<title[^>]*>(.*?)<\/title>/is) || html.match(/<h1[^>]*>(.*?)<\/h1>/is);
  return match ? match[1].replace(/<[^>]+>/g, '').trim() : '';
}