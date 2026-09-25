import { css, html, nothing } from "lit";
import type { TemplateResult } from "lit";
import { customElement, property } from "lit/decorators.js";
import type { ProblemError, ProblemErrorEntry } from "@cofy/frontend-sdk";

import "@awesome.me/webawesome/dist/components/callout/callout.js";

import { CofyElement } from "../cofy-element.js";
import { nativeStyles } from "../theme/native-styles.js";

/**
 * Renders a rejected request.
 *
 * Field-level failures keep the server's own `loc` path, which names the part of the request
 * that was wrong.
 */
@customElement("cofy-problem-details")
export class CofyProblemDetails extends CofyElement {
  public static override styles = [
    nativeStyles,
    css`
      :host {
        display: block;
      }
      /* <strong> is inline by default; the heading role here wants it to stack above the
         detail text instead of running into it. */
      .title {
        display: block;
      }
      .detail {
        margin: 0;
      }
      ul {
        margin: var(--wa-space-xs) 0 0;
        padding-inline-start: var(--wa-space-m);
      }
    `,
  ];

  @property({ attribute: false }) public problem: ProblemError | null = null;

  public override render(): TemplateResult | typeof nothing {
    if (this.problem === null) return nothing;

    const { problem } = this;
    const fields = problem.errors;

    return html`
      <wa-callout variant="danger">
        <strong class="title">${this.heading(problem)}</strong>
        <p class="detail">${this.body(problem)}</p>
        ${fields.length === 0
          ? nothing
          : html`
              <ul>
                ${fields.map(
                  (field): TemplateResult =>
                    html`<li><code>${field.loc.join(".")}</code> — ${this.fieldMessage(field)}</li>`,
                )}
              </ul>
            `}
      </wa-callout>
    `;
  }

  /**
   * The API names each failure with a stable `code`, so a known one reads in the reader's
   * language while an unknown one still shows what the server said. `title` and `detail` are
   * English prose meant for a person, which makes them the right fallback rather than a key.
   */
  private heading(problem: ProblemError): string {
    const code = typeof problem.problem["code"] === "string" ? problem.problem["code"] : undefined;
    return this.t(`errors.${code ?? "unknown"}.title`, {
      defaultValue: problem.problem.title ?? this.t("errors.unknown.title", { defaultValue: "Request failed" }),
    });
  }

  private body(problem: ProblemError): string {
    const code = typeof problem.problem["code"] === "string" ? problem.problem["code"] : undefined;
    return this.t(`errors.${code ?? "unknown"}.detail`, { defaultValue: problem.message });
  }

  /**
   * pydantic's own code for the failure, which is what makes a field error translatable at
   * all - the message beside it is English written by pydantic.
   */
  private fieldMessage(field: ProblemErrorEntry): string {
    return this.t(`errors.validation.${field.type}`, { defaultValue: field.msg });
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "cofy-problem-details": CofyProblemDetails;
  }
}
