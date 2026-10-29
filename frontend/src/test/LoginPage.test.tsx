import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { AuthProvider } from "../features/auth/AuthContext";
import { LoginPage } from "../pages/LoginPage";

describe("LoginPage", () => {
  it("renders login form in Russian", () => {
    const client = new QueryClient();
    render(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <AuthProvider>
            <LoginPage />
          </AuthProvider>
        </MemoryRouter>
      </QueryClientProvider>
    );
    expect(screen.getByText("Вход в систему")).toBeInTheDocument();
    expect(screen.getByText("Войти")).toBeInTheDocument();
  });
});
