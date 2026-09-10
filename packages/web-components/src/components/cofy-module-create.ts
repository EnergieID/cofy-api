import { consume } from "@lit/context";
import { StateController } from "@dodona/lit-state";
import { LitElement, css, html, nothing } from "lit";
import type { TemplateResult } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import {
  validate,
  type AllowedModulesStore,
  type ModuleSettings,
  type ModuleStore,
  type ProblemError,
  type ValidationIssue,
} from "@cofy/frontend-sdk";

import "@carbon/web-components/es/components/button/button.js";
import "@carbon/web-components/es/components/select/index.js";
import "@carbon/web-components/es/components/stack/index.js";
import "@carbon/web-components/es/components/skeleton-text/skeleton-text.js";

import { allowedModulesStoreContext, moduleStoreContext } from "../context.js";
import { seedFromSchema } from "../schema-defaults.js";
import { toYaml } from "../yaml.js";
import "./cofy-problem-details.js";
import "./cofy-yaml-editor.js";
import type { YamlEditorChange } from "./cofy-yaml-editor.js";

/**
 * Creates a module, starting from a skeleton derived from the chosen type's schema.
 *
 * The type list comes from what the community is allowed to configure, so a build that has
 * never heard of a module type still offers it as soon as the server does.
 */
@customElement("cofy-module-create")
export class CofyModuleCreate extends LitElement {
  public static override styles = css`
    :host {
      display: block;
    }
    .picker {
      max-inline-size: 24rem;
      margin-block-end: 1.5rem;
    }
    /* cds-stack leaves its own host as an inline box, so a block margin on it does
       nothing - it groups the buttons, and this row places them. */
    .actions {
      display: flex;
      align-items: center;
      gap: var(--cds-spacing-05);
      margin-block-start: var(--cds-spacing-06);
    }
    .issues {
      margin: var(--cds-spacing-05) 0 0;
      padding-inline-start: 1rem;
      color: var(--cds-text-error);
    }
  `;

  @consume({ context: moduleStoreContext, subscribe: true })
  public moduleStore!: ModuleStore;

  @consume({ context: allowedModulesStoreContext, subscribe: true })
  public allowedModules!: AllowedModulesStore;

  @property({ type: String }) public slug = "";

  @state() private type = "";
  @state() private text = "";
  @state() private value: ModuleSettings | null = null;
  @state() private syntaxErrors: string[] = [];
  @state() private issues: ValidationIssue[] = [];
  @state() private saving = false;
  @state() private error: ProblemError | null = null;

  public readonly stateController = new StateController(this);

  public override willUpdate(changed: Map<string, unknown>): void {
    if ((changed.has("slug") || changed.has("allowedModules")) && this.slug !== "") {
      void this.allowedModules?.ensure(this.slug);
    }
  }

  public override render(): TemplateResult {
    const allowed = this.allowedModules?.list(this.slug);
    if (allowed === undefined) return html`<cds-skeleton-text paragraph line-count="4"></cds-skeleton-text>`;

    const blocked = this.type === "" || this.syntaxErrors.length > 0 || this.issues.length > 0 || this.saving;

    return html`
      ${this.error === null ? nothing : html`<cofy-problem-details .problem=${this.error}></cofy-problem-details>`}

      <div class="picker">
        <cds-select
          label-text="Module type"
          value=${this.type}
          @cds-select-selected=${(e: CustomEvent<{ value?: string }>): void => this.onTypeSelected(e)}
        >
          <cds-select-item value="">Choose a type…</cds-select-item>
          ${allowed.map(
            (option) => html`<cds-select-item value=${option.type}>${option.type} — ${option.description}</cds-select-item>`,
          )}
        </cds-select>
      </div>

      ${this.type === ""
        ? nothing
        : html`
            <cofy-yaml-editor
              .text=${this.text}
              .issues=${this.issues.map((issue) => ({ pointer: issue.pointer, message: issue.message }))}
              @yaml-change=${(e: CustomEvent<YamlEditorChange>): void => this.onChange(e)}
            ></cofy-yaml-editor>
            ${this.problems()}
            <footer class="actions">
              <cds-stack orientation="horizontal" gap="3">
                <cds-button ?disabled=${blocked} @click=${(): void => void this.create()}>
                  ${this.saving ? "Creating…" : "Create module"}
                </cds-button>
                <cds-button kind="ghost" @click=${(): void => this.cancel()}>Cancel</cds-button>
              </cds-stack>
            </footer>
          `}
    `;
  }

  private problems(): TemplateResult | typeof nothing {
    const messages = this.syntaxErrors.length > 0 ? this.syntaxErrors : this.issues.map((i) => `${i.pointer} — ${i.message}`);
    if (messages.length === 0) return nothing;
    return html`<ul class="issues">
      ${messages.map((message) => html`<li>${message}</li>`)}
    </ul>`;
  }

  private onTypeSelected(event: CustomEvent<{ value?: string }>): void {
    const type = event.detail.value ?? "";
    this.type = type;
    this.error = null;
    if (type === "") {
      this.text = "";
      return;
    }

    const schema = this.allowedModules.find(this.slug, type)?.schema;
    const seeded = schema === undefined ? { type } : (seedFromSchema(schema) as Record<string, unknown>);
    const module = { ...seeded, type, name: "" } as ModuleSettings;
    this.value = module;
    this.text = toYaml(module);
    this.check(module);
  }

  private onChange(event: CustomEvent<YamlEditorChange>): void {
    const { text, value, syntaxErrors } = event.detail;
    // Track what the editor holds, so switching type can push a fresh document into it.
    this.text = text;
    this.syntaxErrors = syntaxErrors;
    if (syntaxErrors.length > 0) return;

    this.value = value as ModuleSettings;
    this.check(this.value);
  }

  private check(module: ModuleSettings): void {
    const schema = this.allowedModules.find(this.slug, this.type)?.schema;
    this.issues = schema === undefined ? [] : validate(schema, module);
  }

  private async create(): Promise<void> {
    if (this.value === null) return;

    this.saving = true;
    this.error = null;
    try {
      const created = await this.moduleStore.create(this.slug, this.value);
      this.dispatchEvent(
        new CustomEvent("module-created", {
          detail: { slug: this.slug, id: { type: created.type, name: created.name } },
          bubbles: true,
          composed: true,
        }),
      );
    } catch (error) {
      this.error = error as ProblemError;
    } finally {
      this.saving = false;
    }
  }

  private cancel(): void {
    this.dispatchEvent(new CustomEvent("create-cancelled", { bubbles: true, composed: true }));
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "cofy-module-create": CofyModuleCreate;
  }
}
