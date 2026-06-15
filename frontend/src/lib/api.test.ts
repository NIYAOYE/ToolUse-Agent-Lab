import { describe, expect, it, vi } from "vitest";

import "../test/setup";
import { ApiError, apiRequest } from "./api";

describe("apiRequest", () => {
  it("returns typed JSON responses", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ status: "ok" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    const result = await apiRequest<{ status: string }>("/health");

    expect(result).toEqual({ status: "ok" });
    expect(fetch).toHaveBeenCalledWith(
      "/health",
      expect.objectContaining({ headers: { Accept: "application/json" } }),
    );
  });

  it("throws the stable backend error contract", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            code: "ticket_not_found",
            message: "Ticket was not found.",
            request_id: "request-1",
            details: { ticket_id: "INC-missing" },
          }),
          {
            status: 404,
            headers: { "Content-Type": "application/json" },
          },
        ),
      ),
    );

    await expect(apiRequest("/v1/tickets/INC-missing")).rejects.toEqual(
      expect.objectContaining({
        code: "ticket_not_found",
        requestId: "request-1",
        status: 404,
      }),
    );
  });
});
