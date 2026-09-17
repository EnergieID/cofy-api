/** One field-level failure, as reported by the API's `errors` array. */
export interface ProblemErrorEntry {
  /** Path to the offending value, the way pydantic reports it, e.g. `["body", "source", "api_key"]`. */
  loc: (string | number)[];
  msg: string;
  type: string;
}

/** An RFC 9457 problem document. */
export interface ProblemDetails {
  title?: string;
  status?: number;
  detail?: string;
  errors?: ProblemErrorEntry[];
  [member: string]: unknown;
}

/** A request the API rejected. */
export class ProblemError extends Error {
  public readonly status: number;
  public readonly problem: ProblemDetails;

  public constructor(status: number, problem: ProblemDetails) {
    super(problem.detail ?? problem.title ?? `Request failed with status ${status}`);
    this.name = "ProblemError";
    this.status = status;
    this.problem = problem;
  }

  /** Field-level failures, empty when the problem is not attributable to specific input. */
  public get errors(): ProblemErrorEntry[] {
    return this.problem.errors ?? [];
  }

  public get isNotFound(): boolean {
    return this.status === 404;
  }

  public get isConflict(): boolean {
    return this.status === 409;
  }

  /**
   * Build from whatever a failed response carried.
   *
   * A body that is not a problem document - an upstream proxy's HTML, an empty 502 - still
   * has to produce a usable error, so anything unrecognised becomes the `detail`.
   */
  public static from(status: number, body: unknown): ProblemError {
    if (body !== null && typeof body === "object" && !Array.isArray(body)) {
      return new ProblemError(status, body as ProblemDetails);
    }
    const detail = typeof body === "string" && body.trim() !== "" ? body : undefined;
    return new ProblemError(status, { status, detail });
  }
}

/** Keep a `ProblemError` as-is, and wrap anything else - a network failure - as one. */
export function asProblem(error: unknown): ProblemError {
  if (error instanceof ProblemError) return error;
  return new ProblemError(0, { detail: error instanceof Error ? error.message : String(error) });
}
