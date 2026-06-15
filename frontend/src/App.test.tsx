import { fireEvent, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import "./test/setup";
import { App } from "./App";
import { renderApp } from "./test/renderApp";

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({ items: [], total: 0, page: 1, page_size: 25 }),
        { status: 200, headers: { "Content-Type": "application/json" } },
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
});
