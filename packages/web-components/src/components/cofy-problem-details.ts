import { LitElement, css, html, nothing } from "lit";
import type { TemplateResult } from "lit";
import { customElement, property } from "lit/decorators.js";
import type { ProblemError } from "@cofy/frontend-sdk";

import "@carbon/web-components/es/components/notification/inline-notification.js";

/**
 * Renders a rejected request.
 *
 * Field-level failures keep the server's own `loc` path, which names the part of the request
 * that was wrong.
 */
@customElement("cofy-problem-details")
export class CofyProblemDetails extends LitElement {
  public static override styles = css`
    :host {
      display: block;
    }
    ul {
      margin: 0.5rem 0 0;
      padding-left: 1rem;
    }
    code {
      font-family: var(--cds-code-01-font-family, monospace);
    }
  `;

  @property({ attribute: false }) public problem: ProblemError | null = null;

  public override render(): TemplateResult | typeof nothing {
    if (this.problem === null) return nothing;

    const { problem } = this;
    const fields = problem.errors;

    return html`
      <cds-inline-notification
        kind="error"
        hide-close-button
        title=${problem.problem.title ?? "Request failed"}
        subtitle=${problem.message}
      >
        ${fields.length === 0
          ? nothing
          : html`
              <ul slot="subtitle">
                ${fields.map(
                  (field) => html`<li><code>${field.loc.join(".")}</code> — ${field.msg}</li>`,
                )}
              </ul>
            `}
      </cds-inline-notification>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "cofy-problem-details": CofyProblemDetails;
  }
}
