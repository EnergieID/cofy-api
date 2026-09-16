/** One segment of a parsed JSON Pointer - a property name, or an array index. */
export type PointerSegment = string | number;

/** Decode a JSON Pointer (RFC 6901) into its segments, resolving `~1`/`~0` escapes. */
export function parsePointer(pointer: string): PointerSegment[] {
  if (pointer === "") return [];
  return pointer
    .slice(1)
    .split("/")
    .map((part) => part.replace(/~1/g, "/").replace(/~0/g, "~"))
    .map((part) => (/^\d+$/.test(part) ? Number(part) : part));
}

/** Append one segment to a pointer, escaping it if it is a property name. */
export function pointerFor(parent: string, segment: PointerSegment): string {
  const escaped = typeof segment === "number" ? String(segment) : segment.replace(/~/g, "~0").replace(/\//g, "~1");
  return `${parent}/${escaped}`;
}

/** The value at *pointer* within *doc*, or `undefined` if any segment along the way is missing. */
export function getAtPointer(doc: unknown, pointer: string): unknown {
  return parsePointer(pointer).reduce<unknown>((value, segment) => {
    if (typeof segment === "number") return Array.isArray(value) ? value[segment] : undefined;
    return isRecord(value) ? value[segment] : undefined;
  }, doc);
}

/**
 * A new value equal to *doc* except the value at *pointer* is *value*.
 *
 * Copy-on-write only along the changed path - every ancestor segment must already exist as an
 * object or array; this never fabricates a path, it only replaces along one that is already
 * there. `pointer === ""` replaces the whole document.
 */
export function setAtPointer(doc: unknown, pointer: string, value: unknown): unknown {
  return setAt(doc, parsePointer(pointer), value);
}

function setAt(doc: unknown, path: PointerSegment[], value: unknown): unknown {
  const [head, ...rest] = path;
  if (head === undefined) return value;

  if (typeof head === "number") {
    const array = [...asArray(doc)];
    array[head] = setAt(array[head], rest, value);
    return array;
  }

  const record = isRecord(doc) ? { ...doc } : {};
  record[head] = setAt(record[head], rest, value);
  return record;
}

function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? (value as unknown[]) : [];
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
