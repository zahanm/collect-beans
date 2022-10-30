export const errorHandler = (err: Error) => {
  console.error(err);
  alert(err.message);
};
