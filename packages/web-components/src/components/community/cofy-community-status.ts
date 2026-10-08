import { consume } from "@lit/context";
import { css, html, nothing } from "lit";
import type { TemplateResult } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import type { CommunityState, CommunityStatusStore } from "@cofy/frontend-sdk";

import "@awesome.me/webawesome/dist/components/badge/badge.js";
import "@awesome.me/webawesome/dist/components/tooltip/tooltip.js";

import { CofyElement } from "../../cofy-element.js";
import { communityStatusStoreContext } from "../../context.js";

const VARIANTS: Record<CommunityState, string> = {
  live: "success",
  pending: "warning",
  unavailable: "danger",
};

/**
 * Whether a community's API runs its saved settings, as a badge explained by its tooltip.
 *
 * It asks again every few seconds while changes are pending, and now and then once they are not, for as long as it
 * is shown. Until the first answer, or when there is none, it shows nothing.
 */
@customElement("cofy-community-status")
export class CofyCommunityStatus extends CofyElement {
  public static readonly PENDING_INTERVAL = 3_000;
  public static readonly SETTLED_INTERVAL = 30_000;

  public static override styles = css`
    :host {
      display: inline-block;
    }
  `;

  @consume({ context: communityStatusStoreContext, subscribe: true })
  @state()
  public store?: CommunityStatusStore;

  @property({ type: String }) public slug = "";

  private timer: ReturnType<typeof setTimeout> | undefined;
  // Counts refreshes, so only the latest one schedules the next.
  private refreshes = 0;

  public override connectedCallback(): void {
    super.connectedCallback();
    // Shown again after having been taken out, when nothing else changed that would start asking again.
    if (this.hasUpdated) void this.refresh();
  }

  public override disconnectedCallback(): void {
    super.disconnectedCallback();
    clearTimeout(this.timer);
  }

  public override willUpdate(changed: Map<string, unknown>): void {
    if (changed.has("slug") || changed.has("store")) void this.refresh();
  }

  public override render(): TemplateResult | typeof nothing {
    const status = this.store?.status(this.slug);
    if (status === undefined) return nothing;

    return html`
      <wa-badge id="badge" variant=${VARIANTS[status.state]} pill>
        ${this.t(`communityStatus.${status.state}.label`)}
      </wa-badge>
      <wa-tooltip for="badge">${this.t(`communityStatus.${status.state}.description`)}</wa-tooltip>
    `;
  }

  private async refresh(): Promise<void> {
    clearTimeout(this.timer);
    if (this.store === undefined || this.slug === "") return;

    const refresh = ++this.refreshes;
    await this.store.load(this.slug);
    if (refresh !== this.refreshes || !this.isConnected) return;

    const pending = this.store.status(this.slug)?.state === "pending";
    this.timer = setTimeout(
      () => void this.refresh(),
      pending ? CofyCommunityStatus.PENDING_INTERVAL : CofyCommunityStatus.SETTLED_INTERVAL,
    );
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "cofy-community-status": CofyCommunityStatus;
  }
}
