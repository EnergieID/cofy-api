/** Maps a schema's own type name to the tag of a hand-written element that should render it instead of the generic dispatch. */
export interface FieldRegistry {
  /** The tag name to mount for *typeName*, or `undefined` to fall through to the generic dispatch. */
  customFieldFor(typeName: string | undefined): string | undefined;
}

/** Registers nothing - every field renders through the generic dispatch. */
export const defaultFieldRegistry: FieldRegistry = { customFieldFor: (): undefined => undefined };

/** Build a registry from a plain `{ typeName: tagName }` map. */
export function createFieldRegistry(entries: Readonly<Record<string, string>>): FieldRegistry {
  return { customFieldFor: (typeName): string | undefined => (typeName === undefined ? undefined : entries[typeName]) };
}
