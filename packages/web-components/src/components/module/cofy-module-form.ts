import { css, html, nothing } from "lit";
import type { TemplateResult } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { repeat } from "lit/directives/repeat.js";
import type { AllowedModule, JsonSchema, ValidationIssue } from "@cofy/frontend-sdk";

import "@awesome.me/webawesome/dist/components/option/option.js";
import "@awesome.me/webawesome/dist/components/select/select.js";
import "../editor/cofy-yaml-editor.js";
import "../form/cofy-field-shell.js";
import "../form/register.js";

import { CofyElement } from "../../cofy-element.js";
import { seedFromSchema } from "../../schema-defaults.js";
import { isRecord } from "../../schema-ref.js";
import { toYaml } from "../../yaml.js";
import type { YamlEditorChange } from "../editor/cofy-yaml-editor.js";
import { issuesAt } from "../form/issues.js";
import { setAtPointer } from "../form/pointer.js";
import { nativeStyles } from "../../theme/native-styles.js";
import { utilityStyles } from "../../theme/utility-styles.js";

export type ModuleFormMode = "form" | "yaml";

/**
 * The entry point a host mounts to edit one module: the type it is, then a generated form for
 * that type - or, in `mode="yaml"`, the raw YAML editor instead. Both are views of the same
 * *value*, kept in step as it changes either way - switching never needs an explicit save.
 *
 * The module's own `type` is rendered here, not left to the generic dispatch: it is not just
 * another field, it decides which schema the rest of the form even is. Locked once a module
 * exists (`locked`) - a replace cannot change identity - and otherwise a real picker among
 * *catalog*, seeding a fresh document for whichever type is chosen. Hidden once `mode="yaml"`
 * (past the point of still choosing one): the type is already part of that YAML, so a picker
 * beside it would only say the same thing twice.
 *
 * `mode` is host-controlled, not owned here, so a host can put its toggle wherever it likes
 * (its own heading's actions slot, say) rather than this component dictating the chrome around
 * it. Stateless with respect to drafts, like the YAML editor it wraps: `catalog`/`value`/
 * `issues`/`mode` in, one `module-form-change` event out.
 */
@customElement("cofy-module-form")
export class CofyModuleForm extends CofyElement {
  public static override styles = [
    nativeStyles,
    utilityStyles,
    css`
      :host {
        display: block;
      }
    `,
  ];

  @property({ attribute: false }) public catalog: readonly AllowedModule[] = [];
  @property({ attribute: false }) public value: unknown;
  @property({ attribute: false }) public issues: readonly ValidationIssue[] = [];
  @property({ type: Boolean }) public locked = false;
  @property({ type: String }) public mode: ModuleFormMode = "form";

  @state() private text = "";
  @state() private syntaxErrors: string[] = [];

  /** What was last sent out via `module-form-change`, so an echo of our own edit does not clobber in-progress YAML typing. */
  private lastEmitted: unknown;

  public override willUpdate(changed: Map<string, unknown>): void {
    const valueChanged = changed.has("value") && this.value !== this.lastEmitted;
    const enteringYaml = changed.has("mode") && this.effectiveMode() === "yaml";
    if (valueChanged || enteringYaml) {
      this.text = toYaml(this.value);
      this.syntaxErrors = [];
    }
  }

  public override render(): TemplateResult {
    const type = this.currentType();
    const schema = this.schemaFor(type);
    const mode = this.effectiveMode();
    const showPicker = type === "" || mode !== "yaml";

    return html`
      <div class="wa-stack">
        ${showPicker ? this.renderTypePicker(type) : nothing}
        ${type === ""
          ? nothing
          : mode === "form" && schema !== undefined
            ? html`<cofy-object-form
                .schema=${schema}
                .root=${schema}
                .pointer=${""}
                .value=${this.value}
                .issues=${this.issues}
                .hide=${["type"]}
                @field-change=${(event: CustomEvent<{ pointer: string; value: unknown }>): void =>
                  this.onFieldChange(event)}
              ></cofy-object-form>`
            : html`
                <cofy-field-shell .issues=${this.syntaxErrors.map((message) => ({ message }))}>
                  <cofy-yaml-editor
                    .text=${this.text}
                    .issues=${this.issues.map((issue) => ({ pointer: issue.pointer, message: issue.message }))}
                    @yaml-change=${(event: CustomEvent<YamlEditorChange>): void => this.onYamlChange(event)}
                  ></cofy-yaml-editor>
                </cofy-field-shell>
              `}
      </div>
    `;
  }

  /** Whether the module's type has a known schema to generate a form from - if not, YAML is the only option. */
  public hasSchema(): boolean {
    return this.schemaFor(this.currentType()) !== undefined;
  }

  private renderTypePicker(type: string): TemplateResult {
    return html`
      <cofy-field-shell .issues=${issuesAt(this.issues, "/type")}>
        <wa-select
          label=${this.t("form.moduleType")}
          placeholder=${this.t("form.chooseType")}
          .value=${type}
          lang=${this.i18n?.resolvedLanguage ?? "en"}
          ?disabled=${this.locked}
          @change=${(event: Event): void => this.onTypeChange(event)}
        >
          ${repeat(
            this.catalog,
            (option) => option.type,
            (option) => html`<wa-option value=${option.type}>${option.type} — ${option.description}</wa-option>`,
          )}
        </wa-select>
      </cofy-field-shell>
    `;
  }

  private currentType(): string {
    return isRecord(this.value) && typeof this.value["type"] === "string" ? this.value["type"] : "";
  }

  private schemaFor(type: string): JsonSchema | undefined {
    return this.catalog.find((option) => option.type === type)?.schema;
  }

  private effectiveMode(): ModuleFormMode {
    return this.schemaFor(this.currentType()) === undefined ? "yaml" : this.mode;
  }

  private onTypeChange(event: Event): void {
    if (this.locked) return;
    const type = (event.target as HTMLElement & { value?: string }).value ?? "";
    const schema = this.schemaFor(type);
    if (schema === undefined) return;

    const seeded = seedFromSchema(schema) as Record<string, unknown>;
    this.emit({ ...seeded, type, name: "" });
  }

  private onFieldChange(event: CustomEvent<{ pointer: string; value: unknown }>): void {
    event.stopPropagation();
    const value = setAtPointer(this.value, event.detail.pointer, event.detail.value);
    this.emit(value);
  }

  private onYamlChange(event: CustomEvent<YamlEditorChange>): void {
    const { text, value, syntaxErrors } = event.detail;
    this.text = text;
    this.syntaxErrors = syntaxErrors;
    if (syntaxErrors.length > 0) return;
    this.emit(value);
  }

  private emit(value: unknown): void {
    this.lastEmitted = value;
    this.dispatchEvent(new CustomEvent("module-form-change", { bubbles: true, composed: true, detail: { value } }));
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "cofy-module-form": CofyModuleForm;
  }
}
