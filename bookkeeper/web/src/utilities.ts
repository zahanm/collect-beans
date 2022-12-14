export const errorHandler = (err: Error) => {
  console.error(err);
  alert(err.message);
};

export function arrayRange(num: number): Array<number> {
  return [...Array(num).fill(0)].map((_, ii) => ii);
}

export function invariant(condition: any, message?: string) {
  if (!condition) {
    throw new InvariantViolationError(message || "Invariant failed");
  }
}

class InvariantViolationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = this.constructor.name;
  }
}

export const API = process.env.REACT_APP_API_HOST;

export function absDiff(a: number, b: number): number {
  return Math.abs(Math.abs(a) - Math.abs(b));
}
