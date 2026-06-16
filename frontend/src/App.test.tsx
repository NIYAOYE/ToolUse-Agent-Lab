import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { App } from "./App";

describe("SupportOps application shell", () => {
  it("renders the ticket queue and navigates to the create route", () => {
    render(
      <MemoryRouter initialEntries={["/tickets"]}>
        <App />
      </MemoryRouter>,
    );

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
    render(
      <MemoryRouter initialEntries={["/metrics"]}>
        <App />
      </MemoryRouter>,
    );

    expect(screen.getByRole("link", { name: "Metrics" })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });
});
