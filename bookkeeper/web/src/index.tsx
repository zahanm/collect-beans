import React from "react";
import ReactDOM from "react-dom/client";
import { createBrowserRouter, RouterProvider } from "react-router-dom";

import reportWebVitals from "./reportWebVitals";
import App from "./App";
import ErrorPage from "./ErrorPage";
import SortOptions from "./SortOptions";
import SortChoose from "./SortChoose";
import SortCommit from "./SortCommit";
import SortReview from "./SortReview";

import "./index.css";

const router = createBrowserRouter([
  {
    path: "/",
    element: <App />,
    errorElement: <ErrorPage />,
  },
  {
    path: "/sort",
    element: <SortOptions />,
  },
  {
    path: "/sort/choose",
    element: <SortChoose />,
  },
  {
    path: "/sort/commit",
    element: <SortCommit />,
  },
  {
    path: "/sort/review",
    element: <SortReview />,
  },
]);

const root = ReactDOM.createRoot(
  document.getElementById("root") as HTMLElement
);
root.render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>
);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();
