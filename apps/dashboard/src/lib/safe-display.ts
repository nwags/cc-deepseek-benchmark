const REDACTED = "[REDACTED]";

const SECRET_ASSIGNMENT_KEY = String.raw`(?:--?)?(?:[A-Za-z0-9.]+[_-])*(?:api[_-]?key|auth(?:entication|orization)?|access[_-]?key|secret(?:[_-]?access)?[_-]?key|client[_-]?secret|refresh[_-]?token|private[_-]?token|token|cookie|session|signed[_-]?url|password|passwd|credential|private[_-]?key|database[_-]?url|db[_-]?url|dsn)(?:[_-][A-Za-z0-9.]+)*`;
const SECRET_ASSIGNMENT_PREFIX = String.raw`((?<![A-Za-z0-9_.-])(?:export\s+)?["']?${SECRET_ASSIGNMENT_KEY}["']?\s*[:=]\s*)`;
const SECRET_DOUBLE_QUOTED_ASSIGNMENT = new RegExp(String.raw`${SECRET_ASSIGNMENT_PREFIX}"(?:\\.|[^"\\])*"`, "gim");
const SECRET_SINGLE_QUOTED_ASSIGNMENT = new RegExp(String.raw`${SECRET_ASSIGNMENT_PREFIX}'(?:\\.|[^'\\])*'`, "gim");
const SECRET_REDACTED_ASSIGNMENT = new RegExp(String.raw`${SECRET_ASSIGNMENT_PREFIX}\[(?:redacted)\]`, "gim");
const SECRET_UNQUOTED_ASSIGNMENT = new RegExp(String.raw`${SECRET_ASSIGNMENT_PREFIX}(?!["']|\[(?:redacted)\])[^\s,;\]})]+`, "gim");
const SECRET_EMPTY_ASSIGNMENT = new RegExp(String.raw`${SECRET_ASSIGNMENT_PREFIX}(?!["']\[(?:redacted)\]["'])(?=$|[\r\n,;\]})"'\x60])`, "gim");

const SECRET_KEY_PATTERN = /(?:^|[_-])(?:api[_-]?key|auth(?:entication|orization)?|access[_-]?key|secret(?:[_-]?access)?[_-]?key|client[_-]?secret|token|password|passwd|credential|private[_-]?key|database[_-]?url|db[_-]?url|dsn|cookie|session|signed[_-]?url)(?:$|[_-])/i;
const SECRET_QUERY_PATTERN = /^(?:x-amz-(?:credential|signature|security-token)|x-goog-(?:credential|signature)|signature|sig|token|access_token|auth|authorization|api[_-]?key|key|password|secret)$/i;
const SAFE_ENV_KEY_PATTERN = /^(?:PATH|HOME|SHELL|LANG|LC_[A-Z_]+|TERM|TZ|CI|NODE_ENV|PYTHONPATH)$/i;
const CREDENTIAL_VALUE_PATTERN = /^(?:bearer\s+\S+|basic\s+\S+|sk-[A-Za-z0-9_-]{12,}|xai-[A-Za-z0-9_-]{12,}|pplx-[A-Za-z0-9_-]{12,}|gsk_[A-Za-z0-9_-]{12,}|hf_[A-Za-z0-9_-]{12,}|gh[opusr]_[A-Za-z0-9_]{12,}|(?:AKIA|ASIA)[A-Z0-9]{12,}|AIza[A-Za-z0-9_-]{12,}|eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9._-]+)$/i;
const INLINE_CREDENTIAL_PATTERN = /\b(?:sk-[A-Za-z0-9_-]{12,}|xai-[A-Za-z0-9_-]{12,}|pplx-[A-Za-z0-9_-]{12,}|gsk_[A-Za-z0-9_-]{12,}|hf_[A-Za-z0-9_-]{12,}|gh[opusr]_[A-Za-z0-9_]{12,}|(?:AKIA|ASIA)[A-Z0-9]{12,}|AIza[A-Za-z0-9_-]{12,})\b/gi;

function isSecretKey(key: string) {
  const normalized = key.replace(/([a-z])([A-Z])/g, "$1_$2").toLowerCase();
  return SECRET_KEY_PATTERN.test(key.toLowerCase()) || SECRET_KEY_PATTERN.test(normalized);
}

function looksLikeEnvironmentContainer(key: string) {
  return /^(?:env|environment|environment_variables|variables)$/i.test(key);
}

function looksExplicitCredential(value: string) {
  const trimmed = value.trim();
  if (CREDENTIAL_VALUE_PATTERN.test(trimmed)) return true;
  if (/-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----/.test(trimmed)) return true;
  return false;
}

function looksCredentialShapedEnvironmentValue(value: string) {
  const trimmed = value.trim();
  return looksExplicitCredential(trimmed)
    || (/^[A-Za-z0-9+/=_-]{40,}$/.test(trimmed) && !/\s/.test(trimmed));
}

function sanitizeUrlObject(url: URL) {
  if (url.username) url.username = "";
  if (url.password) url.password = "";
  for (const key of [...url.searchParams.keys()]) {
    if (SECRET_QUERY_PATTERN.test(key) || isSecretKey(key)) {
      url.searchParams.set(key, REDACTED);
    }
  }
  return url;
}

/**
 * Sanitizes a URI or endpoint for display without changing its host, port,
 * non-secret path, or benign query parameters. This is display-only; immutable
 * artifact bytes and download responses are never passed through this helper.
 */
export function sanitizeDisplayedUri(value: string | null | undefined): string | null {
  if (!value) return value ?? null;
  const trimmed = value.trim();

  try {
    if (/^[a-z][a-z0-9+.-]*:\/\//i.test(trimmed)) {
      return sanitizeUrlObject(new URL(trimmed)).toString();
    }
  } catch {
    // Fall through to conservative string redaction for malformed URI-like data.
  }

  return trimmed
    .replace(/([a-z][a-z0-9+.-]*:\/\/)([^/@\s:]+)(?::[^/@\s]*)?@/gi, "$1")
    .replace(/([?&](?:x-amz-(?:credential|signature|security-token)|x-goog-(?:credential|signature)|signature|sig|token|access_token|auth|authorization|api[_-]?key|key|password|secret)=)[^&#\s]*/gi, `$1${REDACTED}`);
}

export function sanitizeDisplayedValue(value: unknown, key = ""): unknown {
  if (value === null || value === undefined) return value;
  if (isSecretKey(key)) return REDACTED;

  if (typeof value === "string") {
    if (looksExplicitCredential(value) && !SAFE_ENV_KEY_PATTERN.test(key)) return REDACTED;
    return redactSecretsInText(value);
  }

  if (Array.isArray(value)) {
    return value.map((item) => sanitizeDisplayedValue(item, key));
  }

  if (typeof value === "object") {
    return redactStructuredValue(value, looksLikeEnvironmentContainer(key));
  }

  return value;
}

/** Recursively redacts secret-bearing structured configuration values. */
export function redactStructuredValue(value: unknown, environmentValues = false): unknown {
  if (Array.isArray(value)) {
    return value.map((item) => {
      if (typeof item === "string") {
        if (environmentValues && looksCredentialShapedEnvironmentValue(item)) return REDACTED;
        return redactSecretsInText(item);
      }
      return redactStructuredValue(item, environmentValues);
    });
  }
  if (typeof value === "string") {
    if (environmentValues && looksCredentialShapedEnvironmentValue(value)) return REDACTED;
    return redactSecretsInText(value);
  }
  if (!value || typeof value !== "object") return value;

  const output: Record<string, unknown> = {};
  for (const [key, item] of Object.entries(value as Record<string, unknown>)) {
    if (isSecretKey(key)) {
      output[key] = REDACTED;
      continue;
    }

    const nestedEnvironment = environmentValues || looksLikeEnvironmentContainer(key);
    if (nestedEnvironment && typeof item === "string" && !SAFE_ENV_KEY_PATTERN.test(key) && looksCredentialShapedEnvironmentValue(item)) {
      output[key] = REDACTED;
      continue;
    }

    if (item && typeof item === "object") {
      output[key] = redactStructuredValue(item, nestedEnvironment);
    } else {
      output[key] = sanitizeDisplayedValue(item, key);
    }
  }
  return output;
}

/** Best-effort redaction for non-structured preview text such as YAML. */
export function redactSecretsInText(text: string): string {
  const bearerRedacted = text.replace(/\b(Bearer|Basic)\s+(?!\[REDACTED\])\S+/gi, `$1 ${REDACTED}`);
  return bearerRedacted
    .replace(SECRET_DOUBLE_QUOTED_ASSIGNMENT, (_match, prefix: string) => `${prefix}"${REDACTED}"`)
    .replace(SECRET_SINGLE_QUOTED_ASSIGNMENT, (_match, prefix: string) => `${prefix}'${REDACTED}'`)
    .replace(SECRET_REDACTED_ASSIGNMENT, (_match, prefix: string) => `${prefix}${REDACTED}`)
    .replace(SECRET_UNQUOTED_ASSIGNMENT, (_match, prefix: string) => `${prefix}${REDACTED}`)
    .replace(SECRET_EMPTY_ASSIGNMENT, (_match, prefix: string) => `${prefix}${REDACTED}`)
    .replace(INLINE_CREDENTIAL_PATTERN, REDACTED)
    .replace(/([a-z][a-z0-9+.-]*:\/\/)([^/@\s:]+)(?::[^/@\s]*)?@/gi, "$1")
    .replace(/([?&](?:x-amz-(?:credential|signature|security-token)|x-goog-(?:credential|signature)|signature|sig|token|access_token|auth|authorization|api[_-]?key|key|password|secret)=)[^&#\s]*/gi, `$1${REDACTED}`);
}

/**
 * Final display/evidence sink. Call this immediately before rendering any
 * retained free-text fact, label, path, URI, excerpt, or exception string.
 */
export function sanitizeEvidenceText(value: string | null | undefined): string | null {
  if (value === null || value === undefined) return null;
  return redactSecretsInText(value);
}

/** Recursively sanitizes a derived evidence value without mutating its source. */
export function sanitizeEvidenceOutput(value: unknown): unknown {
  if (typeof value === "string") return redactSecretsInText(value);
  if (Array.isArray(value)) return value.map((item) => sanitizeEvidenceOutput(item));
  if (!value || typeof value !== "object") return value;

  const output: Record<string, unknown> = {};
  for (const [key, item] of Object.entries(value as Record<string, unknown>)) {
    output[key] = isSecretKey(key) ? REDACTED : sanitizeEvidenceOutput(item);
  }
  return output;
}

export function redactedMarker() {
  return REDACTED;
}
