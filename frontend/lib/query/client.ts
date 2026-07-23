"use client";
import { QueryClient } from "@tanstack/react-query";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: false, // don't retry on 4xx/5xx — show error state instead
      throwOnError: false, // never bubble to the error boundary; use isError instead
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: 0,
      throwOnError: false,
    },
  },
});
