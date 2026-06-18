export const SEED_COMMAND = "python3 scripts/demo_seed.py --api-base-url http://localhost:8010";

export function getErrorMessage(error: unknown) {
  if (error instanceof Error && error.message) return error.message;
  if (typeof error === "string") return error;
  return "Unable to load data from the backend.";
}
