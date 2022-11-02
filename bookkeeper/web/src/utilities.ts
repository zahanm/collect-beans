export const errorHandler = (err: Error) => {
  console.error(err);
  alert(err.message);
};

export function arrayRange(num: number): Array<number> {
  return [...Array(num).fill(0)].map((_, ii) => ii);
}
