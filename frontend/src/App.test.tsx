import { fireEvent, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import "./test/setup";
import { App } from "./App";
import { renderApp } from "./test/renderApp";

beforeEach(() => {
  window.localStorage.clear();
  vi.stubGlobal(
    "fetch",
    vi.fn((input: RequestInfo | URL) =>
      Promise.resolve(
        new Response(
          JSON.stringify(
            String(input) === "/v1/metrics/diagnosis-time"
              ? { count: 0, median_seconds: null, p75_seconds: null }
              : { items: [], total: 0, page: 1, page_size: 25 },
          ),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      ),
    ),
  );
});

describe("SupportOps application shell", () => {
  it("renders the ticket queue and navigates to the create route", () => {
    renderApp(<App />);

    expect(
      screen.getByRole("heading", { name: "Ticket Queue" }),
    ).toBeInTheDocument();
    expect(screen.getByText("HUMAN REVIEW REQUIRED")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("link", { name: "New Ticket" }));

    expect(
      screen.getByRole("heading", { name: "Create Ticket" }),
    ).toBeInTheDocument();
  });

  it("marks the current route in the navigation", () => {
    renderApp(<App />, "/metrics");

    expect(screen.getByRole("link", { name: "Metrics" })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });

  it("switches the shell and queue page to Chinese", async () => {
    renderApp(<App />);

    fireEvent.click(screen.getByRole("button", { name: "中文" }));

    expect(
      screen.getByRole("heading", { name: "工单队列" }),
    ).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "新建工单" }).length).toBeGreaterThan(
      0,
    );
    expect(await screen.findByText("暂无工单")).toBeInTheDocument();
    expect(screen.getByText("需要人工审核")).toBeInTheDocument();
  });
});
