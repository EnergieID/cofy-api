import { consume } from "@lit/context";
import { css, html, nothing } from "lit";
import type { TemplateResult } from "lit";
import { customElement, property, state } from "lit/decorators.js";
// Keyed, so a select that moves its options cannot leave Lit patching nodes that have moved.
import { repeat } from "lit/directives/repeat.js";
import {
  validate,
  type AllowedModulesStore,
  type ModuleSettings,
  type ModuleStore,
  type ProblemError,
  type ValidationIssue,
} from "@cofy/frontend-sdk";

import "@awesome.me/webawesome/dist/components/button/button.js";
import "@awesome.me/webawesome/dist/components/option/option.js";
import "@awesome.me/webawesome/dist/components/select/select.js";
import "@awesome.me/webawesome/dist/components/skeleton/skeleton.js";

import { CofyElement } from "../../cofy-element.js";
import { allowedModulesStoreContext, moduleStoreContext } from "../../context.js";
import { layoutStyles } from "../../theme/layout-styles.js";
import { nativeStyles } from "../../theme/native-styles.js";
import { seedFromSchema } from "../../schema-defaults.js";
import { toYaml } from "../../yaml.js";
import "../cofy-problem-details.js";
import "../editor/cofy-yaml-editor.js";
import type { YamlEditorChange } from "../editor/cofy-yaml-editor.js";

/**
 * Creates a module, starting from a skeleton derived from the chosen type's schema.
 *
 * The type list comes from what the community is allowed to configure, so a build that has
 * never heard of a module type still offers it as soon as the server does.
 */
@customElement("cofy-module-create")
export class CofyModuleCreate extends CofyElement {
  public static override styles = [
    nativeStyles,
    layoutStyles,
    css`
      :host {
        display: block;
      }
      .picker {
        max-inline-size: 24rem;
        margin-block-end: 1.5rem;
      }
      .actions {
        display: flex;
        align-items: center;
        gap: var(--wa-space-m);
        margin-block-start: var(--wa-space-l);
      }
      .issues {
        margin: var(--wa-space-m) 0 0;
        padding-inline-start: 1rem;
        color: var(--wa-color-danger-border-loud);
      }
      .skeleton {
        display: flex;
        flex-direction: column;
        gap: var(--wa-space-xs);
      }
    `,
  ];

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

  public override willUpdate(changed: Map<string, unknown>): void {
    if ((changed.has("slug") || changed.has("allowedModules")) && this.slug !== "") {
      void this.allowedModules?.ensure(this.slug);
    }
  }

  public override render(): TemplateResult {
    const allowed = this.allowedModules?.list(this.slug);
    if (allowed === undefined) {
      return html`<div class="skeleton">
        ${Array.from({ length: 4 }, () => html`<wa-skeleton></wa-skeleton>`)}
      </div>`;
    }

    const blocked = this.type === "" || this.syntaxErrors.length > 0 || this.issues.length > 0 || this.saving;

    return html`
      ${this.error === null ? nothing : html`<cofy-problem-details .problem=${this.error}></cofy-problem-details>`}

      <div class="picker">
        <wa-select
          label=${this.t("create.type")}
          placeholder=${this.t("create.choose")}
          .value=${this.type}
          lang=${this.i18n?.resolvedLanguage ?? "en"}
          @change=${(event: Event): void => this.onTypeSelected(event)}
        >
          ${repeat(
            allowed,
            (option) => option.type,
            (option) => html`<wa-option value=${option.type}>${option.type} — ${option.description}</wa-option>`,
          )}
        </wa-select>
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
              <div class="wa-cluster">
                <wa-button variant="brand" ?disabled=${blocked} @click=${(): void => void this.create()}>
                  ${this.saving ? this.t("create.creating") : this.t("create.submit")}
                </wa-button>
                <wa-button appearance="plain" @click=${(): void => this.cancel()}>
                  ${this.t("create.cancel")}
                </wa-button>
              </div>
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

  private onTypeSelected(event: Event): void {
    // Web Awesome's form controls are `ElementInternals`-associated, so they emit a plain
    // `change` and the value lives on the element - not in a `detail` payload.
    const type = (event.target as HTMLElement & { value?: string }).value ?? "";
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
