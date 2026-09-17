import { beforeEach, describe, expect, it } from "vitest";
import { ProblemError } from "@cofy/frontend-sdk";

import { CofyProblemDetails } from "../../src/components/cofy-problem-details.js";
import { testI18n } from "../support/i18n.js";

async function mount(problem: ProblemError): Promise<CofyProblemDetails> {
  const element = new CofyProblemDetails();
  element.i18n = await testI18n();
  element.problem = problem;
  document.body.append(element);
  await element.updateComplete;
  return element;
}

/** The callout's heading and body, which are slotted content rather than attributes. */
function shown(element: CofyProblemDetails): { title: string; detail: string } {
  const root = element.shadowRoot!;
  return {
    title: root.querySelector(".title")!.textContent.trim(),
    detail: root.querySelector(".detail")!.textContent.trim(),
  };
}

describe("cofy-problem-details", () => {
  beforeEach(() => {
    document.body.replaceChildren();
  });

  it("translates a failure the API names with a code", async () => {
    const element = await mount(
      new ProblemError(404, { status: 404, title: "Not Found", detail: "No community 'x'.", code: "resource-not-found" }),
    );

    // Nothing parameterises the sentence yet, so the server's own prose is still what says
    // *which* thing was missing.
    expect(shown(element)).toEqual({ title: "Not found", detail: "No community 'x'." });
  });

  it("shows what the server said when the code is one it has no translation for", async () => {
    const element = await mount(
      new ProblemError(503, { status: 503, title: "Service Unavailable", detail: "Upstream is down.", code: "upstream-down" }),
    );

    expect(shown(element)).toEqual({ title: "Service Unavailable", detail: "Upstream is down." });
  });

  it("still reads as an error when the response carried no problem document at all", async () => {
    const element = await mount(ProblemError.from(502, "<html>bad gateway</html>"));

    expect(shown(element).title).toBe("Request failed");
  });

  it("translates each field failure by pydantic's own code, keeping the path it names", async () => {
    const element = await mount(
      new ProblemError(422, {
        status: 422,
        code: "validation-failed",
        detail: "Request validation failed.",
        errors: [
          { loc: ["body", "source", "token"], msg: "Field required", type: "missing" },
          { loc: ["body", "interval"], msg: "Input should be a valid integer", type: "int_type" },
        ],
      }),
    );

    const items = Array.from(element.shadowRoot!.querySelectorAll("li")).map((item) =>
      item.textContent.replaceAll(/\s+/g, " ").trim(),
    );

    expect(items).toEqual([
      "body.source.token — This field is required.",
      "body.interval — This must be a whole number.",
    ]);
  });

  it("falls back to pydantic's English for a code it does not know", async () => {
    const element = await mount(
      new ProblemError(422, {
        status: 422,
        code: "validation-failed",
        errors: [{ loc: ["body", "cron"], msg: "Value error, not a cron expression", type: "cron_invalid" }],
      }),
    );

    expect(element.shadowRoot!.querySelector("li")!.textContent).toContain("not a cron expression");
  });
});
